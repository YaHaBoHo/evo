import random
from evo import utils

# TODO : Type hints

class Gene():

    VMIN = 0
    VMAX = 1
    DEFAULT = 0.5
    SIGMA = 0.033

    def __init__(self, value=None):
        if value is None:
            value = self.DEFAULT
        self.value = utils.clamp(value, self.VMIN, self.VMAX)
        self.cost = self._cost()

    def _cost(self):
        return self.value

    def mutate(self):
        vrange = (self.VMAX - self.VMIN) * self.SIGMA
        return self.__class__(utils.clamp(self.value + random.uniform(-vrange, vrange), self.VMIN, self.VMAX))


class Size(Gene):
    VMIN = 0.8
    VMAX = 4
    DEFAULT = 1

    def _cost(self):
        return 4.189 * self.value**3
        # Volume of the creature (phere)

class Speed(Gene):
    VMIN = 0.8
    VMAX = 6
    DEFAULT = 1

    def _cost(self):
        return 0.5 * self.value**2
        # Speed portion of kinetic energy

class Perception(Gene):
    VMIN = 0.4
    VMAX = 3
    DEFAULT = 0.5

    def _cost(self):
        return 3.142 * self.value**2
        # 1/2 of area to survey (disc)
