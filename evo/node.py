import random
import itertools
import collections
import pygame
from evo import utils
from evo.dna import Size, Speed, Perception, Digestion


# Initialize
pygame.init()


class Node(pygame.sprite.Sprite):

    id_counter = itertools.count()

    def __init__(self, engine, pos:pygame.math.Vector2=None):
        # Parent
        super().__init__()
        # Engine
        self.engine = engine
        # Variables
        self.pos = self.engine.random_map_position() if pos is None else self.validate_pos(pos)
        # Characteristics
        self.name = "{}-{}".format(self.__class__.__name__, next(Node.id_counter))

    def __repr__(self):
        return "{}({},{})".format(
            self.name,
            round(self.pos.y),
            round(self.pos.x)
        )

    def validate_pos(self, pos):
        return self.engine.clamp_map_position(pos)

    def vector_to(self, other):
        return other.pos - self.pos

 
class Exploration(Node):
    pass


class Escape(Node):

    def validate_pos(self, pos):
        return self.engine.bounce_map_position(pos)


class PhysicalNode(Node):
    
    def __init__(self, engine, pos=None):
        # Parent
        super().__init__(engine=engine, pos=pos)
        # Image
        self.image = None
        self.rect = None
        # Initialize
        self.load_image()
        self.refresh()

    def get_image(self):
        image = pygame.Surface((10, 10))
        image.fill((0,0,255))
        return image

    def load_image(self):
        self.image = self.get_image()
        self.rect = self.image.get_rect()

    def refresh(self):
        self.rect.centerx = self.pos.x
        self.rect.centery = self.pos.y


class LifeForm(PhysicalNode):

    def __init__(self, engine, pos=None):
        super().__init__(engine=engine, pos=pos)
        self.consume_value = 0
        self.consume_time = 0
        self.add(self.engine.lifeforms)

    def die(self):
        self.kill()


class Fruit(LifeForm):
    
    def __init__(self, engine, pos=None):
        super().__init__(engine=engine, pos=pos)
        self.consume_time = 15
        self.add(self.engine.fruits)

    @classmethod
    def spawn(cls, engine):
        fruit_class = random.choice(cls.__subclasses__())
        return fruit_class(engine)
 

class Cherry(Fruit):

    def __init__(self, engine, pos=None):
        super().__init__(engine=engine, pos=pos)
        self.consume_value = 1000

    def get_image(self):
        return self.engine.images_fruits['cherry']


class Banana(Fruit):

    def __init__(self, engine, pos=None):
        super().__init__(engine=engine, pos=pos)
        self.consume_value = 2000

    def get_image(self):
        return self.engine.images_fruits['banana']


class Pineapple(Fruit):

    def __init__(self, engine, pos=None):
        super().__init__(engine=engine, pos=pos)
        self.consume_value = 3000

    def get_image(self):
        return self.engine.images_fruits['pineapple']


class Creature(LifeForm):

    DECAY = 0.00075

    def __init__(self, engine, pos=None, parent=None):
        # Parent
        self.parent = parent
        # Specs
        if self.parent is None:
            self.size = Size()
            self.speed = Speed()
            self.perception = Perception()
            self.digestion = Digestion()
            self.generation = 1
        else:
            pos = self.parent.pos
            self.size = self.parent.size.mutate()
            self.speed = self.parent.speed.mutate()
            self.perception = self.parent.perception.mutate()
            self.digestion = self.parent.digestion.mutate()
            self.generation = self.parent.generation + 1
        # LifeForm
        super().__init__(engine=engine, pos=pos)
        self.consume_value = self.size.cost * 2000
        self.consume_time = 30 + self.size.value * 5
        # PyGame
        self.add(self.engine.creatures)
        # Variables
        self.age = 0
        self.energy = self.consume_value  # Start_energy = Consumption value
        self.target = None
        self.waypoints = collections.deque(maxlen=10)
        self.action = None
        self.pinner = None


    @property
    def reproduction_cost(self):
        return self.consume_value * 0.5

    def get_image(self):
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
        return super().get_image()

    def reproduce(self):
        self.energy -= self.reproduction_cost
        Creature(engine=self.engine, parent=self)

    def get_consume_value(self, other):
        if isinstance(other, Creature):
            return self.digestion.carnivore * other.consume_value
        else:
            return self.digestion.herbivore * other.consume_value

    def is_related(self, other):
        return (self.parent == other) or (other.parent == self) or (self.parent == other.parent)

    def look_nearby(self):
        # Min bounds
        xmin, ymin = self.engine.get_grid_xy(
            self.pos.x - self.perception.distance, 
            self.pos.y - self.perception.distance
        )
        # Max bounds
        xmax, ymax = self.engine.get_grid_xy(
            self.pos.x + self.perception.distance, 
            self.pos.y + self.perception.distance
        )
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
                if lf is self or self.is_related(lf):
                    continue
                # Smaller creatures are a prey
                if self.size.value > lf.size.value * 1.25:
                    yield lf, False
                # Bigger creatures are a predator
                elif lf.size.value > self.size.value * 1.25:
                    yield lf, True

    def check_target(self):
        if self.target:
            return self.target.alive()
        return False

    def select_target(self):
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
                    score = self.get_consume_value(lf) / max(1, distance**2)
                    if score > prey_score:
                        prey, prey_score = lf, score
        # Did we spot a predator?
        if predator:
            try:
                target_pos = self.pos-predator_vector.normalize()*self.perception.distance*0.5
            except ValueError:
                # Cannot determine feeing direction, can happen if vector is (0,0)
                # Just pass pos=None to make it random....
                target_pos = None
            self.set_target(Escape(self.engine, pos=target_pos))
        # Did we post a prey?
        elif prey:
            self.set_target(prey)
        # Otherwise, continue exploring
        elif not self.target:
            self.set_target(Exploration(self.engine))

    def pin_target(self):
        if isinstance(self.target, Creature):
            self.target.pinner = self

    def consume_target(self):
        # Is target still alive?
        if self.target.alive():
            # Add energy
            self.energy += self.get_consume_value(self.target)
            # Kill target
            self.target.die()
            self.set_target(None)

    def set_target(self, target):
        self.waypoints.append(self.pos.xy)
        self.target = target

    def refresh_target(self):
        # If target is a prey, check it
        if isinstance(self.target, LifeForm):
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
            self.pos.update(self.target.pos)
            if isinstance(self.target, LifeForm):
                # If target is a LifeForm, pin it and try consuming it.
                self.pin_target()
                self.action = utils.Task(
                    timer=self.target.consume_time, 
                    action=self.consume_target, 
                    validate=self.check_target
                )
            else:
                # Otherwise, just unset it.
                self.set_target(None)
        # Else, move towards tagret
        else:
            self.pos += vector.normalize() * self.speed.value
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
                    pygame.draw.line(self.engine.map, (160,192,160), wp0, wp1, 2)
                    wp0 = wp1
                pygame.draw.line(self.engine.map, (160,192,160), wp0, self.pos, 2)
            # Draw a circle for perception
            pygame.draw.circle(self.engine.map, (96,96,96), self.pos, self.perception.distance, 1)
            # Draw a line for target (if any)
            if self.target:
                pygame.draw.line(self.engine.map, (96,96,96), self.pos, self.target.pos, 1)

    def update(self):
        # Time passes...
        self.age += 1
        self.energy -= self.age * self.DECAY + self.perception.cost
        # Check if we ran out of energy.
        if self.energy <= 0:
            self.die()
        # Do we have an ongoing action?
        if self.action:
            self.action.tick()
        elif self.pinner:
            # If pinner is dead, drop it.
            if not self.pinner.alive():
                self.pinner = None
        else:
            # Check if we can reproduce.
            if self.energy >= self.consume_value + self.reproduction_cost:
                self.action = utils.Task(timer=30, action=self.reproduce)
            # If our prey is dead, drop it.
            self.refresh_target() 
            # Lastly, move - if possible.
            self.move()
        # Either way, refresh sprite(s).
        self.refresh()
