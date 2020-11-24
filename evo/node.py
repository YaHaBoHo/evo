import random
import itertools
import collections
import pygame
from evo import utils
from evo.dna import Size, Speed, Perception

# TODO : Fleeing from carnivores
# TODO : Poison fruits 
# TODO : Memory and fruit identification
# TODO : Type hints

# Initialize
pygame.init()

class Node(pygame.sprite.Sprite):

    id_counter = itertools.count()

    def __init__(self, world, pos:pygame.math.Vector2=None):
        # Parent
        super().__init__()
        # World
        self.world = world 
        # Image
        self.image = None
        self.rect = None
        # Characteristics
        self.name = "{}-{}".format(self.__class__.__name__, next(Node.id_counter))
        # Variables
        self.pos = self.world.randomize_position() if pos is None else self.world.clamp_position(pos)
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

    def __init__(self, world, pos=None):
        super().__init__(world=world, pos=pos)
        self.nutrition = 0
        self.add(self.world.lifeforms)

    def die(self):
        self.kill()


class Fruit(LifeForm):
    
    def __init__(self, world, pos=None):
        super().__init__(world=world, pos=pos)
        self.add(self.world.fruits)

    @classmethod
    def spawn(cls, world):
        fruit_class = random.choice(cls.__subclasses__())
        return fruit_class(world)
 

class Cherry(Fruit):

    def __init__(self, world, pos=None):
        super().__init__(world=world, pos=pos)
        self.nutrition = 750

    def get_image(self):
        return self.world.images['sprites']['fruit']['cherry']


class Banana(Fruit):

    def __init__(self, world, pos=None):
        super().__init__(world=world, pos=pos)
        self.nutrition = 2000

    def get_image(self):
        return self.world.images['sprites']['fruit']['banana']


class Creature(LifeForm):

    AGE_MALUS = 0.00075

    def __init__(self, world, pos=None, parent=None):
        # Parent
        self.parent = parent
        self.carnivore = False
        # Specs
        if self.parent is None:
            self.size = Size()
            self.speed = Speed()
            self.perception = Perception()
            self.generation = 1
        else:
            pos = self.parent.pos
            self.size = self.parent.size.mutate()
            self.speed = self.parent.speed.mutate()
            self.perception = self.parent.perception.mutate()
            self.generation = self.parent.generation + 1
        # LifeForm
        super().__init__(world=world, pos=pos)
        self.nutrition = self.size.cost * 700
        # PyGame
        self.add(self.world.creatures)
        # Variables
        self.age = 0
        self.energy = self.nutrition  # Start_energy = Nutrition value
        self.target = None
        self.waypoints = collections.deque(maxlen=10)

    def get_image(self):
        # Color
        idx = 1 if self.carnivore else 0
        # Size
        for s in self.world.creature_sizes:
            if self.size.value * 10 >= s:
                return self.world.images['sprites']['creature'][s][idx]
        # Fallback on smallest sprite
        return self.world.images['sprites']['creature'][self.world.creature_sizes[-1]][idx]

    def reproduce(self):
        self.energy -= self.nutrition * 0.5
        Creature(world=self.world, parent=self)

    def is_related(self, other):
        return (self.parent == other) or (other.parent == self) or (self.parent == other.parent)

    def look(self):
        # Look for lifeforms in range
        for lf in self.world.lifeforms:
            # Fruits are never a predator
            if isinstance(lf, Fruit):
                yield lf, False
            # Creatures can be prey or predator, depending on size diff
            elif isinstance(lf, Creature) and not self.is_related(lf):
                if self.size.value > lf.size.value * 1.1:
                    yield lf, False
                elif lf.size.value > self.size.value * 1.1:
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
                if distance <= self.perception.value * 100:
                    score = 1 / max(1, distance)
                    if score > predator_score:
                        predator, predator_score, predator_vector = lf, score, vector
            # If target is a prey, and no predator was spotted
            elif not predator:
                distance = vector.magnitude()
                if distance <= self.perception.value * 100:
                    score = lf.nutrition / max(1, distance**2)
                    if score > prey_score:
                        prey, prey_score = lf, score
        # Did we spot a predator?
        if predator:
            try:
                target_pos = self.pos-predator_vector.normalize()*self.perception.value*100
            except ValueError:
                # Cannot determine feeing direction, can happen if vector is (0,0)
                # Just pass pos=None to make it random....
                target_pos = None
            self.set_target(Escape(self.world, pos=target_pos))
        # Did we post a prey?
        elif prey:
            self.set_target(prey)
        # Otherwise, continue exploring
        elif not self.target:
            self.set_target(Exploration(self.world))
    
    def consume_target(self):
        # Add energy
        self.energy += self.target.nutrition
        # Carnivore?
        if isinstance(self.target, Creature):
            self.carnivore = True
            self.load_image()
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
                if self.vector_to(self.target).magnitude() > self.perception.value * 100:
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
            if self.world.selected is self:
                # Past waypoints
                if len(self.waypoints) > 0:
                    wp0 = self.waypoints[0]
                    for i in range(1, len(self.waypoints)):
                        wp1 = self.waypoints[i]
                        pygame.draw.line(self.world.map, (160,192,160), wp0, wp1, 2)
                        wp0 = wp1
                    pygame.draw.line(self.world.map, (160,192,160), wp0, self.pos, 2)
                # Current perception and target
                pygame.draw.circle(self.world.map, (0,0,255), self.pos, self.perception.value*100, 1)
                pygame.draw.line(self.world.map, (0,0,255), self.pos, self.target.pos, 1)

    def update(self):
        # Time passes...
        self.age += 1
        self.energy -= self.age * self.AGE_MALUS + self.perception.cost
        # Check if we ran out of energy
        if self.energy <= 0:
            self.die()
        # Check if we can reproduce
        if self.energy >= self.nutrition * 1.5:
            self.reproduce()
        # If our prey is dead, drop it.
        self.refresh_target()         
        # Either way, move and update
        self.move()
        self.update_rect()

