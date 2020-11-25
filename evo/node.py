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
        # Image
        self.image = None
        self.rect = None
        # Characteristics
        self.name = "{}-{}".format(self.__class__.__name__, next(Node.id_counter))
        # Variables
        self.pos = self.engine.random_map_position() if pos is None else self.engine.clamp_map_position(pos)
        # Initialize
        self.load_image()
        self.update_rect()

    def __repr__(self):
        return "{}({},{})".format(
            self.__class__.__name__,
            round(self.pos.y),
            round(self.pos.x)
        )

    def vector_to(self, other):
        return other.pos - self.pos

    def get_image(self):
        image = pygame.Surface((1, 1))
        image.fill((0, 0, 1))
        return image

    def load_image(self):
        self.image = self.get_image()
        self.rect = self.image.get_rect()

    def update_rect(self):
        self.rect.centerx = self.pos.x
        self.rect.centery = self.pos.y

 
class Exploration(Node):
    pass


class Escape(Node):
    pass


class LifeForm(Node):

    def __init__(self, engine, pos=None):
        super().__init__(engine=engine, pos=pos)
        self.nutrition = 0
        self.add(self.engine.lifeforms)

    def die(self):
        self.kill()


class Fruit(LifeForm):
    
    def __init__(self, engine, pos=None):
        super().__init__(engine=engine, pos=pos)
        self.add(self.engine.fruits)

    @classmethod
    def spawn(cls, engine):
        fruit_class = random.choice(cls.__subclasses__())
        return fruit_class(engine)
 

class Cherry(Fruit):

    def __init__(self, engine, pos=None):
        super().__init__(engine=engine, pos=pos)
        self.nutrition = 750

    def get_image(self):
        return self.engine.images_fruits['cherry']


class Banana(Fruit):

    def __init__(self, engine, pos=None):
        super().__init__(engine=engine, pos=pos)
        self.nutrition = 2000

    def get_image(self):
        return self.engine.images_fruits['banana']


class Creature(LifeForm):

    AGE_COST = 0.00075

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
        self.nutrition = self.size.cost * 2000
        # PyGame
        self.add(self.engine.creatures)
        # Variables
        self.age = 0
        self.energy = self.nutrition  # Start_energy = Nutrition value
        self.target = None
        self.waypoints = collections.deque(maxlen=10)

    def get_image(self):
        # Color
        if self.digestion.value >= 5.5:
            # Carnivore
            color = 2
        elif self.digestion.value <= 4.5:
            # Herbivore
            color = 0
        else:
            # Omnivore
            color = 1
        # Size
        for images_size, images in self.engine.images_creatures:
            if self.size.value >= images_size:
                return images[color]
        # Fallback on custom surface
        fallback = pygame.Surface((10, 10))
        fallback.fill((255,255,0))
        return fallback

    def reproduce(self):
        self.energy -= self.nutrition * 0.5
        Creature(engine=self.engine, parent=self)

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
                if self.size.value > lf.size.value * 1.2:
                    yield lf, False
                # Bigger creatures are a predator
                elif lf.size.value > self.size.value * 1.2:
                    yield lf, True

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
                    score = self.get_nutrition(lf) / max(1, distance**2)
                    if score > prey_score:
                        prey, prey_score = lf, score
        # Did we spot a predator?
        if predator:
            try:
                target_pos = self.pos-predator_vector.normalize()*self.perception.distance
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

    def get_nutrition(self, other):
        if isinstance(other, Creature):
            return self.digestion.carnivore * other.nutrition
        else:
            return self.digestion.herbivore * other.nutrition

    def consume_target(self):
        # Add energy
        self.energy += self.get_nutrition(self.target)
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
            if isinstance(self.target, LifeForm) and self.target.alive():
                # If target is a LifeForm and alive, consume it.
                self.consume_target()
            else:
                # Otherwise, just unset it.
                self.set_target(None)
        # Else, move towards tagret
        else:
            self.pos += vector.normalize() * self.speed.value
            self.energy -= self.speed.cost * self.size.cost  # Energy to move (volume of creature * speed**2)
            if self.engine.selected is self:
                # Past waypoints
                if len(self.waypoints) > 0:
                    wp0 = self.waypoints[0]
                    for i in range(1, len(self.waypoints)):
                        wp1 = self.waypoints[i]
                        pygame.draw.line(self.engine.map, (160,192,160), wp0, wp1, 2)
                        wp0 = wp1
                    pygame.draw.line(self.engine.map, (160,192,160), wp0, self.pos, 2)
                # Current perception and target
                pygame.draw.circle(self.engine.map, (96,96,96), self.pos, self.perception.distance, 1)
                pygame.draw.line(self.engine.map, (96,96,96), self.pos, self.target.pos, 1)

    def update(self):
        # Time passes...
        self.age += 1
        self.energy -= self.age * self.AGE_COST + self.perception.cost
        # Check if we ran out of energy
        if self.energy <= 0:
            self.die()
        # Check if we can reproduce
        if self.energy >= self.nutrition * 1.5:
            self.reproduce()
        # If our prey is dead, drop it.
        self.refresh_target()         
        # Lastly, move.
        self.move()
        self.update_rect()

