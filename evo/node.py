import random
import itertools
import collections
import pygame
from evo import task
from evo import dna


# Initialize
pygame.init()


class Node(pygame.sprite.Sprite):

    id_tracker = itertools.count()

    def __init__(self, engine, position: pygame.math.Vector2 = None):
        # Parent
        super().__init__()
        # Engine
        self.engine = engine
        # Variables
        if position is None:
            self.position = self.engine.random_map_position()
        else:
            self.position = self.validate_position(position)
        # Characteristics
        self.id = next(Node.id_tracker)
        self.name = "{}-{}".format(self.__class__.__name__, self.id)

    def __repr__(self):
        return self.name

    def validate_position(self, pos):
        return self.engine.clamp_map_position(pos)

    def vector_to(self, other):
        return other.position - self.position


class Exploration(Node):
    pass


class Escape(Node):

    def validate_position(self, position):
        return self.engine.bounce_map_position(position)


class PhysicalNode(Node):

    def __init__(self, engine, position=None):
        # Parent
        super().__init__(engine=engine, position=position)
        # Image
        self.image = None
        self.rect = None
        # Initialize
        self.load_image()
        self.refresh()

    def _image(self):
        image = pygame.Surface((10, 10))
        image.fill((0, 0, 255))
        return image

    def load_image(self):
        self.image = self._image()
        self.rect = self.image.get_rect()

    def refresh(self):
        self.rect.centerx = self.position.x
        self.rect.centery = self.position.y


class Lifeform(PhysicalNode):

    def __init__(self, engine, position=None):
        super().__init__(engine=engine, position=position)
        self.nutrition = 0
        self.add(self.engine.lifeforms)

    def drain(self, amount):
        # Clamp bite amount
        amount = min(amount, self.nutrition+1)
        self.nutrition -= amount
        # Die if nutrition <= 0
        if self.nutrition <= 0:
            self.die()
        # Return bite amount
        return amount

    def die(self):
        self.kill()


class Fruit(Lifeform):

    def __init__(self, engine, position=None):
        super().__init__(engine=engine, position=position)
        self.add(self.engine.fruits)

    @classmethod
    def spawn(cls, engine):
        fruit_class = random.choice(cls.__subclasses__())
        return fruit_class(engine)


class Cherry(Fruit):

    def __init__(self, engine, position=None):
        super().__init__(engine=engine, position=position)
        self.nutrition = 1000

    def _image(self):
        return self.engine.images_fruits['cherry']


class Banana(Fruit):

    def __init__(self, engine, position=None):
        super().__init__(engine=engine, position=position)
        self.nutrition = 2000

    def _image(self):
        return self.engine.images_fruits['banana']


class Pineapple(Fruit):

    def __init__(self, engine, position=None):
        super().__init__(engine=engine, position=position)
        self.nutrition = 3000

    def _image(self):
        return self.engine.images_fruits['pineapple']


class Creature(Lifeform):

    DECAY = 0.00075

    def __init__(self, engine, position=None, parent=None):
        # Parent
        self.parent = parent
        # Specs
        if self.parent is None:
            self.size = dna.Size()
            self.speed = dna.Speed()
            self.perception = dna.Perception()
            self.digestion = dna.Digestion()
            self.generation = 1
            self.task = None
        else:
            position = self.parent.position
            self.size = self.parent.size.mutate()
            self.speed = self.parent.speed.mutate()
            self.perception = self.parent.perception.mutate()
            self.digestion = self.parent.digestion.mutate()
            self.generation = self.parent.generation + 1
            self.task = task.Wean(timer=20)
        # Lifeform
        super().__init__(engine=engine, position=position)
        self.nutrition = self.size.cost * 1800
        # PyGame
        self.add(self.engine.creatures)
        # Variables
        self.age = 0
        self.energy = self.nutrition  # Start_energy = Consumption value
        self.target = None
        self.waypoints = collections.deque(maxlen=10)
        self.incapacitated = False

    def _image(self):
        # Color
        # TODO : Should be dynamic
        if self.digestion.value >= 6:
            # Carnivore
            color = 2
        elif self.digestion.value <= 4:
            # Herbivore
            color = 0
        else:
            # Omnivore
            color = 1
        # Size
        for images_size, images in self.engine.images_creatures:
            if self.size.value >= images_size:
                return images[color]
        # If no match, fallback on parent sprite
        return super()._image()

    @property
    def reproduction_cost(self):
        return self.nutrition * 0.6  # TODO: Configureable

    @property
    def action(self):
        # Active task?
        if self.task:
            if isinstance(self.task, task.Consume):
                return "{} {}".format(self.task.VERB.capitalize(), self.target)
            return self.task.VERB.capitalize()
        # Target?
        if isinstance(self.target, Lifeform):
            return "Going after {}".format(self.target)
        if isinstance(self.target, Escape):
            return "Running away"
        if isinstance:
            return "Looking for food"  # TODO : Or water.
        # Fallback ro idle
        return "Idle"

    def digestion_ratio(self, other):
        # Return digestion ratio based on target
        if isinstance(other, Creature):
            return self.digestion.carnivore
        return self.digestion.herbivore

    def related(self, other):
        return (self.parent == other) or (other.parent == self) or (self.parent == other.parent)

    def reproduce(self):
        self.energy -= self.reproduction_cost
        Creature(engine=self.engine, parent=self)

    def look_nearby(self):
        # Min bounds
        xmin, ymin = self.engine.map_to_grid(self.position - pygame.math.Vector2(self.perception.distance))
        # Max bounds
        xmax, ymax = self.engine.map_to_grid(self.position + pygame.math.Vector2(self.perception.distance))
        # Look in cells
        for cellx in range(xmin, xmax+1):
            for celly in range(ymin, ymax+1):
                for lf in self.engine.grid[cellx][celly]:
                    yield lf

    def look(self):
        # Look for lifeforms nearby
        for lf in self.look_nearby():
            # Fruits are never a predator
            if isinstance(lf, Fruit):
                yield lf, False
            elif isinstance(lf, Creature):
                # Ignore self or related
                if lf is self or self.related(lf):
                    continue
                # Smaller creatures are a prey
                if self.size.value > lf.size.value * 1.25:
                    yield lf, False
                # Bigger creatures are a predator
                elif lf.size.value > self.size.value * 1.25:
                    yield lf, True

    def select_target(self) -> Lifeform:
        # Init
        predator, predator_score, predator_vector = None, 0, None
        prey, prey_score = None, 0
        # Look around
        for lf, is_predator in self.look():
            # Delta vector
            vector = self.vector_to(lf)
            # If target a predator
            if is_predator:
                distance = vector.magnitude()
                if distance <= self.perception.distance:
                    score = 1 / max(1, distance)
                    if score > predator_score:
                        predator, predator_score, predator_vector = lf, score, vector
            # If target is a prey, and no predator was spotted
            elif not predator:
                distance = vector.magnitude()
                if distance <= self.perception.distance:
                    score = self.digestion_ratio(lf) * lf.nutrition / max(1, distance**2)
                    if score > prey_score:
                        prey, prey_score = lf, score
        # Did we spot a predator?
        if predator:
            try:
                target_pos = self.position-predator_vector.normalize() * self.perception.distance * 0.5
            except ValueError:
                # Cannot determine feeing direction, can happen if vector is (0,0)
                # Just pass pos=None to make it random....
                target_pos = None
            self.set_target(Escape(self.engine, position=target_pos))
        # Did we post a prey?
        elif prey:
            self.set_target(prey)
        # Otherwise, continue exploring
        elif not self.target:
            self.set_target(Exploration(self.engine))

    def incapacitate_target(self):
        if isinstance(self.target, Creature):
            self.target.incapacitated = True

    def consume_target(self):
        # Is target still alive?
        if self.target and self.target.alive():
            # Take a bite
            drained_amount = self.target.drain(self.digestion_ratio(self.target) * 50)
            if drained_amount > 0:
                self.energy += drained_amount
                return True
        # Otherwise, unset target
        self.set_target(None)
        return False

    def set_target(self, target):
        self.waypoints.append(self.position.xy)
        self.target = target

    def refresh_target(self):
        # If target is a prey, check it
        if isinstance(self.target, Lifeform):
            # If prey is dead, drop it
            if not self.target.alive():
                self.set_target(None)
            # If prey alive but is is a creature, check its distance
            elif isinstance(self.target, Creature):
                # If creature-prey is too far, drop it
                if self.vector_to(self.target).magnitude() > self.perception.distance:
                    self.set_target(None)
        # Look for a new target id:
        # - We just droppped our target
        # - We had no target to start with
        # - We are exploring
        if not self.target or isinstance(self.target, Exploration):
            self.select_target()

    def move(self):
        # Compute distance vector
        vector = self.vector_to(self.target)
        # If within range, jump to tagret
        if vector.magnitude() < self.speed.value + self.size.value:
            self.position.update(self.target.position)
            if isinstance(self.target, Lifeform):
                # Incapacitate target
                self.incapacitate_target()
                # Try consuming target
                self.task = task.Consume(
                    timer=self.target.nutrition / (self.digestion_ratio(self.target) * 50),
                    update=self.consume_target
                )
            else:
                # Otherwise, just unset it.
                self.set_target(None)
        # Else, move towards tagret
        else:
            self.position += vector.normalize() * self.speed.value
            self.energy -= self.speed.cost * self.size.cost  # Energy to move (volume of creature * speed**2)

    def refresh(self):
        # Parent
        super().refresh()
        # If needed, disply extra info
        if self.engine.selected is self:
            # Draw past waypoints
            if len(self.waypoints) > 0:
                wp0 = self.waypoints[0]
                for i in range(1, len(self.waypoints)):
                    wp1 = self.waypoints[i]
                    pygame.draw.line(self.engine.map, (160, 192, 160), wp0, wp1, 2)
                    wp0 = wp1
                pygame.draw.line(self.engine.map, (160, 192, 160), wp0, self.position, 2)
            # [Debug] draw rect
            # pygame.draw.rect(self.engine.map, (0,0,0), self.rect, 1)
            # Draw a circle for perception
            pygame.draw.circle(self.engine.map, (96, 96, 96), self.position, self.perception.distance, 1)
            # Draw a line for target (if any)
            if self.target:
                pygame.draw.line(self.engine.map, (96, 96, 96), self.position, self.target.position, 1)

    def update(self):
        # Time passes...
        self.age += 1
        self.energy -= self.age * self.DECAY + self.perception.cost
        # Check if we ran out of energy.
        if self.energy <= 0:
            self.die()
        # Do we have an ongoing action?
        if self.task:
            self.task.tick()
        # Are we incapacitated?
        elif not self.incapacitated:
            # Check if we can reproduce.
            if self.energy >= self.nutrition + self.reproduction_cost:
                self.task = task.Gestate(timer=30, action=self.reproduce)
            # If our prey is dead, drop it.
            self.refresh_target()
            # Lastly, move - if possible.
            self.move()
        # Either way, refresh sprite(s).
        self.refresh()
