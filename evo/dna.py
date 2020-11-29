import random
from evo import utils

# TODO : Type hints

class Gene():

    VMIN = 0.5
    VMAX = 9.5
    DEFAULT = 1
    COST_RATIO = 0.5
    MUTATION_RATIO = 0.02

    def __init__(self, value=None):
        if value is None:
            value = self.DEFAULT
        self.value = utils.clamp(value, self.VMIN, self.VMAX)
        self.cost = self._cost() * self.COST_RATIO

    def __repr__(self):
        return "{}({})".format(
            self.__class__.__name__,
            round(self.value, 2),
        )

    def _cost(self):
        return self.value

    def mutate(self):
        vrange = (self.VMAX - self.VMIN) * self.MUTATION_RATIO
        return self.__class__(utils.clamp(self.value + random.uniform(-vrange, vrange), self.VMIN, self.VMAX))


class Size(Gene):

    COST_RATIO = 0.3

    def _cost(self):
        return 4.189 * self.value**3
        # Volume of the creature (phere)


class Speed(Gene):

    def _cost(self):
        return 0.5 * self.value**2
        # Speed portion of kinetic energy


class Perception(Gene):

    COST_RATIO = 0.1
    MUTATION_RATIO = 0.03

    def __init__(self, value=None):
        super().__init__(value=value)
        self.distance = self.value * 60

    def _cost(self):
        return 6.284 * self.value**2
        # Area to survey (disc)


class Digestion(Gene):

    DEFAULT = 5

    def __init__(self, value=None):
        super().__init__(value=value)
        self.carnivore, self.herbivore = self._specialization()

    def _specialization(self):
        scaled_value = utils.scale(self.value, self.VMIN, self.VMAX, -2, 2)
        # Note: Below is DivByZero-safe
        if scaled_value >= 0:
            return scaled_value+1, 1/(scaled_value+1)
        elif scaled_value < 0:
            return 1/(-scaled_value+1), -scaled_value+1
