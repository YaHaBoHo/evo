import random
from evo import utils

# TODO : Type hints

class Gene():

    VMIN = 0.5
    VMAX = 10
    DEFAULT = 1
    SIGMA = 0.03
    COST_RATIO = 0.5

    def __init__(self, value=None):
        if value is None:
            value = self.DEFAULT
        self.value = utils.clamp(value, self.VMIN, self.VMAX)
        self.cost = self._cost() * self.COST_RATIO

    def _cost(self):
        return self.value

    def mutate(self):
        vrange = (self.VMAX - self.VMIN) * self.SIGMA
        return self.__class__(utils.clamp(self.value + random.uniform(-vrange, vrange), self.VMIN, self.VMAX))


class Size(Gene):

    def _cost(self):
        return 4.189 * self.value**3
        # Volume of the creature (phere)

class Speed(Gene):

    def _cost(self):
        return 0.5 * self.value**2
        # Speed portion of kinetic energy

class Perception(Gene):

    def _cost(self):
        return 6.284 * self.value**2
        # Area to survey (disc)
