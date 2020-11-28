import pathlib
import pygame


pygame.init()


# ----- Constants ----- #

HOMEDIR = pathlib.Path(__file__).parent.absolute()
IMAGEDIR = HOMEDIR / "img"
TEXT_FONT = pygame.font.SysFont(None, 16)
TEXT_COLOR = (0,0,0)
ALPHA_COLOR = (255,0,255)


# ----- Classes ----- #

class Task():

    # timer [int] : Time before executing action.
    # action [function] : Callback, executed when timer expires.
    # validate [function] : Callback, executed every tick. If returns false, abort action.
    # update [function] : Callback, executed every tick, with timer value as an arg.

    def __init__(self, timer, action=None, validate=None, update=None):
        # Config
        self.timer = timer
        self._action = action
        self._validate = validate
        self._update = update
        # Internals
        self.aborted = False

    def __bool__(self):
        return self.running 

    @property
    def running(self):
        return (self.timer > 0) and (not self.aborted)

    def action(self):
        if self._action and not self.aborted:
            self._action()

    def validate(self):
        # If function exists, run it.
        if self._validate:
            return self._validate()
        # Otherwise just return True.
        return True

    def update(self):
        if self._update and not self.aborted:
            self._update(self.timer)

    def tick(self):
        # Only take action if not aborted
        if not self.aborted:
            # Validate ...
            if not self.validate():
                self.aborted = True
            # ... and tick/execute.
            else:
                # Uodate
                self.timer -= 1
                self.update()
                # Execute action if done
                if self.timer <= 0:
                    self.action()


class Int2D():

    def __init__(self, x, y):
        self._x = x
        self._y = y

    def __repr__(self):
        return "<Int2D({},{})>".format(self.x, self.y)

    def __add__(self, other):
        if isinstance(other, (int, float)):
            return Int2D(self.x + other, self.y + other)
        if isinstance(other, Int2D):
            return Int2D(self.x + other.x, self.y + other.y)
        # Unsupported... 
        Int2D._unsupported("+", other)

    def __sub__(self, other):
        if isinstance(other, (int, float)):
            return Int2D(self.x - other, self.y - other)
        if isinstance(other, Int2D):
            return Int2D(self.x - other.x, self.y - other.y)
        # Unsupported... 
        Int2D._unsupported("-", other)

    def __mul__(self, other):
        if isinstance(other, (int, float)):
            return Int2D(self.x * other, self.y * other)
        # Unsupported... 
        Int2D._unsupported("*", other)

    def __truediv__(self, other):
        if isinstance(other, (int, float)):
            return Int2D(self.x / other, self.y / other)
        # Unsupported... 
        Int2D._unsupported("/ or //", other)

    def __floordiv__(self, other):
        return self.__truediv__(other)

    @property
    def x(self):
        return int(self._x)
    
    @property
    def y(self):
        return int(self._y)

    @property
    def xy(self):
        return (int(self.x), int(self.y))

    @classmethod
    def _unsupported(cls, op, other):
        raise TypeError("Unsupported operation: {} {} {}".format(cls, op, type(other)))


# ----- Helpers ----- #

def avg(values):
    if len(values) > 0:
        return sum(values)/len(values)
    return 0

def stat_amima(values):
    if len(values) > 0:
        return (avg(values), min(values), max(values))
    return (0,)*3

def stat_quantiles(values, mid=0.5, low=0.1, high=0.9):
    value_count = len(values)
    if value_count > 0:
        values_sorted = sorted(values)
        return (
            values_sorted[int(value_count*mid)],
            values_sorted[int(value_count*low)],
            values_sorted[int(value_count*high)]
        )
    return (0,)*3


def ceildiv(a, b):
    return -(-a // b)


def clamp(v, vmin, vmax):
    return min(max(v, vmin), vmax)


def scale(v, old_min, old_max, new_min, new_max):
    if old_max == old_min:
        return new_min
    return new_min + (new_max - new_min) * (v - old_min) / (old_max - old_min)


def gui_text(text, fg=None, bg=None):
    if fg is None:
        fg = TEXT_COLOR
    return TEXT_FONT.render(str(text), True, fg, bg)


def load_image_file(file_name, alpha=True) -> pygame.Surface:
    with open(IMAGEDIR / file_name, "r") as f:
        img = pygame.image.load(f)
        if alpha:
            img.set_colorkey(ALPHA_COLOR)
        return img.convert()


def load_image_strip(file_name, alpha=True):
    img_list = list()
    img_strip = load_image_file(file_name, alpha=False)
    img_size = img_strip.get_height()
    for posx in range(0, img_strip.get_width(), img_size):
        img = pygame.Surface((img_size, img_size)).convert()
        img.set_colorkey(ALPHA_COLOR)
        img.blit(img_strip, (0, 0), (posx, 0, img_size, img_size))
        img_list.append(img.convert())
    return img_size, img_list
   

def load_image_files(file_pattern, alpha=True):
    return [ load_image_file(p.name, alpha) for p in IMAGEDIR.glob(file_pattern) if p.is_file() ]


def load_image_strips(file_pattern, alpha=True):
    return sorted(
        [load_image_strip(f.name, alpha=True) for f in IMAGEDIR.glob(file_pattern) if f.is_file()],
        key=lambda x: x[0], 
        reverse=True
    )

def load_map_images():
    return {
        'center': load_image_files("bg_center_*.bmp", alpha=False),
        'edge': load_image_files("bg_edge_*.bmp", alpha=False),
        'corner': load_image_files("bg_corner_*.bmp", alpha=False)
    }


def load_pond_images():
    return load_image_files("bg_pond_*.bmp")


def load_creature_images(scale_to):
    # Load
    images_creatures = load_image_strips("sp_creature_*.bmp")
    # Scale
    scale_from = (images_creatures[-1][0], images_creatures[0][0])
    return [
        (scale(img_size, *scale_from, *scale_to), img_list)
    for img_size, img_list in images_creatures]


def load_fruit_images():
    sprites = dict()
    for item in IMAGEDIR.glob("sp_fruit_*.bmp"):
        if item.is_file():
            _, _, fruit_type = item.stem.split("_")
            fruit_image = load_image_file(item.name)
            sprites[fruit_type] = fruit_image
    return sprites
