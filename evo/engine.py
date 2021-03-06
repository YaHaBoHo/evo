import random
import pygame
from evo import utils
from evo.node import Creature, Fruit
from evo.dna import Size, Speed, Perception, Digestion
from evo.chart import Chart


# Constants and Defaults
SCREEN_DEFAULT = (1024, 768)
SCREEN_BACKGROUND = (27, 104, 143)
ENGINE_SPEED = (1, 200)
WORLD_SCALE = (0.25, 1)
MAP_DEFAULT = (6, 4)
MAP_TILE_SIZE = 256
MAP_MARGIN = 20
GRID_CELL_SIZE = 128


# Initialize
pygame.init()
pygame.display.set_caption("eVo")


class Engine():

    def __init__(self, map_tiles=None, screen_resolution=None, fullscreen=False, display=0):
        # Screen
        if fullscreen:
            self.screen = pygame.display.set_mode(display=display, flags=pygame.FULLSCREEN)
            self.screen_size = utils.Int2D(*self.screen.get_size())
        else:
            screen_size = SCREEN_DEFAULT if screen_resolution is None else screen_resolution
            self.screen_size = utils.Int2D(*screen_size)
            self.screen = pygame.display.set_mode(self.screen_size.xy)
        self.screen_offset = pygame.math.Vector2(0)
        self.screen_drag = False
        # Images
        self.images_map = utils.load_map_images()
        self.images_ponds = utils.load_pond_images()
        self.images_fruits = utils.load_fruit_images()
        self.images_creatures = utils.load_creature_images((Size.VMIN, Size.VMAX))
        # Map
        if map_tiles is None:
            self.map_tiles = utils.Int2D(*MAP_DEFAULT)
        else:
            self.map_tiles = utils.Int2D(x=max(map_tiles[0], 2), y=max(map_tiles[1], 2))
        self.map_size = self.map_tiles * MAP_TILE_SIZE
        self.map = pygame.Surface(self.map_size.xy)
        self.map.set_colorkey(utils.ALPHA_COLOR)
        # World
        self.world_tiles = self.map_tiles + 2
        self.world_size = self.world_tiles * 256
        self.world_background = self.load_world()
        self.world = pygame.Surface(self.world_size.xy)
        self.world_scale = 1
        # - Update screen offset to match world center.
        self.screen_offset -= pygame.math.Vector2((self.world_size - self.screen_size).xy) / 2
        # Grid
        self.grid_cells = utils.Int2D(
            x=utils.ceildiv(self.map_size.x,  GRID_CELL_SIZE),
            y=utils.ceildiv(self.map_size.y, GRID_CELL_SIZE)
        )
        self.grid = None
        self.clear_grid()
        # Chart
        # - Chart config
        chart_size = (min(self.screen_size.x/2, 640), min(self.screen_size.y/2, 480))
        self.chart = Chart(size=chart_size, history=250)
        self.chart_position = self.screen_size - self.chart.size
        self.chart_active = next(self.chart.active)
        self.chart_interval = 150  # TODO : Configurable
        # - Chart metrics
        self.chart.add_metric("cps", 0)
        self.chart.add_metric("creatures", 0)
        self.chart.add_metric("fruits", 0)
        self.chart.add_metric("size", Size.VMIN, Size.VMAX)
        self.chart.add_metric("speed", Speed.VMIN, Speed.VMAX)
        self.chart.add_metric("perception", Perception.VMIN, Perception.VMAX)
        self.chart.add_metric("digestion", Digestion.VMIN, Perception.VMAX)
        # Node groups
        self.fruits = pygame.sprite.Group()
        self.creatures = pygame.sprite.Group()
        self.lifeforms = pygame.sprite.Group()
        # Internals
        self.clock = pygame.time.Clock()
        self.selected = None
        self.speed = 30
        self.time = 0
        self.running = False

    def load_world(self):
        background = pygame.Surface(self.world_size.xy)
        # Background tiles
        for tile_x in range(self.world_tiles.x):
            for tile_y in range(self.world_tiles.y):
                # Tile coordinates
                tile_pos = (MAP_TILE_SIZE*tile_x, MAP_TILE_SIZE*tile_y)
                background.blit(self.load_grass_tile(tile_x, tile_y), tile_pos)
                # Pond tile?
                if 1 < tile_x < self.world_tiles.x-1 and 1 < tile_y < self.world_tiles.y-1:
                    if random.random() > 0.66:
                        pond_tile = self.load_pond_tile()
                        pond_tile_pos = (
                            tile_pos[0] + random.uniform(0, MAP_TILE_SIZE-pond_tile.get_width()),
                            tile_pos[1] + random.uniform(0, MAP_TILE_SIZE-pond_tile.get_height())
                        )
                        background.blit(pond_tile, pond_tile_pos)
        return background

    def load_pond_tile(self):
        pond_tile = random.choice(self.images_ponds)
        return pygame.transform.rotate(pond_tile, random.randint(0, 3) * 90)

    def load_grass_tile(self, x, y):
        # Tile type?
        if x == 0:
            if y == 0:
                # Top-left corner
                return random.choice(self.images_map['corner'])
            elif y == self.world_tiles.y - 1:
                # Bottom-left corner
                return pygame.transform.rotate(random.choice(self.images_map['corner']), 90)
            else:
                # Left edge
                return random.choice(self.images_map['edge'])
        elif x == self.world_tiles.x - 1:
            if y == 0:
                # Top-right corner
                return pygame.transform.rotate(random.choice(self.images_map['corner']), -90)
            elif y == self.world_tiles.y - 1:
                # Bottom-right corner
                return pygame.transform.rotate(random.choice(self.images_map['corner']), 180)
            else:
                # Right edge
                return pygame.transform.rotate(random.choice(self.images_map['edge']), 180)
        elif y == 0:
            # Top edge
            return pygame.transform.rotate(random.choice(self.images_map['edge']), -90)
        elif y == self.world_tiles.y - 1:
            # Bottom edge
            return pygame.transform.rotate(random.choice(self.images_map['edge']), 90)
        else:
            # Center / main tile
            return random.choice(self.images_map['center'])

    def screen_to_map(self, position: pygame.math.Vector2) -> pygame.math.Vector2:
        return pygame.math.Vector2(
            position/self.world_scale
            - self.screen_offset
            - pygame.math.Vector2(MAP_TILE_SIZE)
        )

    def random_map_position(self) -> pygame.math.Vector2:
        return pygame.Vector2(
            random.uniform(MAP_MARGIN, self.map_size.x - MAP_MARGIN),
            random.uniform(MAP_MARGIN, self.map_size.y - MAP_MARGIN)
        )

    def clamp_map_position(self, position: pygame.math.Vector2) -> pygame.math.Vector2:
        return pygame.math.Vector2(
            utils.clamp(position.x, MAP_MARGIN, self.map_size.x-MAP_MARGIN),
            utils.clamp(position.y, MAP_MARGIN, self.map_size.y-MAP_MARGIN)
        )

    def bounce_map_position(self, position: pygame.math.Vector2) -> pygame.math.Vector2:
        # If X is out of range, randomize it.
        if position.x < MAP_MARGIN:
            pos_x = random.uniform(MAP_MARGIN, MAP_TILE_SIZE)
        elif position.x > self.map_size.x-MAP_MARGIN:
            pos_x = random.uniform(self.map_size.x-MAP_TILE_SIZE, self.map_size.x-MAP_MARGIN)
        else:
            pos_x = position.x
        # If Y is out of range, randomize it.
        if position.y < MAP_MARGIN:
            pos_y = random.uniform(MAP_MARGIN, MAP_TILE_SIZE)
        elif position.y > self.map_size.y-MAP_MARGIN:
            pos_y = random.uniform(self.map_size.y-MAP_TILE_SIZE, self.map_size.y-MAP_MARGIN)
        else:
            pos_y = position.y
        # Return
        return pygame.Vector2(pos_x, pos_y)

    def map_to_grid(self, position) -> tuple:
        return (
            int(utils.clamp(position.x, MAP_TILE_SIZE, self.map_size.x-MAP_TILE_SIZE-1) / GRID_CELL_SIZE),
            int(utils.clamp(position.y, MAP_TILE_SIZE, self.map_size.y-MAP_TILE_SIZE-1) / GRID_CELL_SIZE)
        )

    def clear_grid(self):
        self.grid = [[[] for _y in range(self.grid_cells.y)] for _x in range(self.grid_cells.x)]

    def update_grid(self):
        # First, clear.
        self.clear_grid()
        # Then, fill.
        for lf in self.lifeforms:
            cx, cy = self.map_to_grid(position=lf.position)
            self.grid[cx][cy].append(lf)

    def clear_selected(self):
        self.selected = None

    def handle_mouse(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN:
            # Right button (1) : Drag map
            if event.button == 3:
                self.screen_drag = True
                pygame.mouse.get_rel()
            # Left button (3) : Select creature
            if event.button == 1:
                click_pos = pygame.math.Vector2(pygame.mouse.get_pos())
                selection_pos = self.screen_to_map(click_pos)
                selection_rect = pygame.Rect(selection_pos - (8, 8), (16, 16))
                for c in self.creatures:
                    if c.rect.colliderect(selection_rect):
                        self.selected = c
        elif event.type == pygame.MOUSEBUTTONUP:
            if event.button == 3:
                self.screen_drag = False
        elif event.type == pygame.MOUSEMOTION:
            if self.screen_drag:
                self.screen_offset += pygame.math.Vector2(pygame.mouse.get_rel()) / self.world_scale
        # Zoom
        elif event.type == pygame.MOUSEWHEEL:
            focus = self.screen_to_map((self.screen_size/2).vector2)
            self.world_scale = utils.clamp(self.world_scale + 0.05 * event.y, *WORLD_SCALE)
            self.screen_offset += self.screen_to_map((self.screen_size/2).vector2) - focus

    def handle_keyboard(self, event):
        # http://thepythongamebook.com/en:glossary:p:pygame:keycodes
        if event.type == pygame.KEYDOWN:
            # Simulation speed
            # - Faster
            if event.key == pygame.K_UP:
                self.speed = utils.clamp(self.speed+1, *ENGINE_SPEED)
            if event.key == pygame.K_PAGEUP:
                self.speed = utils.clamp(self.speed+10, *ENGINE_SPEED)
            # - Slower
            if event.key == pygame.K_DOWN:
                self.speed = utils.clamp(self.speed-1, *ENGINE_SPEED)
            if event.key == pygame.K_PAGEDOWN:
                self.speed = utils.clamp(self.speed-10, *ENGINE_SPEED)
            # - Reset
            if event.key == pygame.K_SPACE:
                self.speed = 30
            # Chart selection
            if event.key in (pygame.K_LSHIFT, pygame.K_RSHIFT):
                self.chart_active = next(self.chart.active)
            # Quit
            if event.key == pygame.K_ESCAPE:
                self.running = False

    def draw_world(self):
        # Blit map on world
        self.world.blit(self.map, (MAP_TILE_SIZE, MAP_TILE_SIZE))
        # Scale world?
        if self.world_scale < 1:
            scaled_world = pygame.transform.smoothscale(self.world, (self.world_size * self.world_scale).xy)
            self.screen.blit(scaled_world, self.screen_offset * self.world_scale)
        else:
            self.screen.blit(self.world, self.screen_offset)

    def draw_ui(self):
        # TODO : Dynamic placement...
        # Engine info
        self.draw_text("Time: {}".format(self.time), (20, 20))
        self.draw_text("CPS: {}".format(round(self.clock.get_fps(), 2)), (20, 40))
        self.draw_text("Population: {}".format(len(self.creatures)), (20, 60))
        self.draw_text("Fruits: {}".format(len(self.fruits)), (20, 80))
        # Simulation info
        self.draw_text("Speed: {}".format(self.speed), (self.screen_size.x-80, 20))
        # Creature info
        if self.selected:
            sc = self.selected
            self.draw_text("[{}]".format(sc.name), (20, self.screen_size.y-160))
            self.draw_text("Gen: {}".format(sc.generation), (20, self.screen_size.y-140))
            self.draw_text("Age: {}".format(sc.age), (20, self.screen_size.y-120))
            self.draw_text("Energy: {}".format(int(sc.energy)), (20, self.screen_size.y-100))
            self.draw_text("Size: {}".format(round(sc.size.value, 2)), (20, self.screen_size.y-80))
            self.draw_text("Speed: {}".format(round(sc.speed.value, 2)), (20, self.screen_size.y-60))
            self.draw_text("Perception: {}".format(round(sc.perception.value, 2)), (20, self.screen_size.y-40))
            self.draw_text("Action: {}".format(sc.action), (20, self.screen_size.y-20))
        # Chart
        if self.chart_active:
            self.screen.blit(self.chart_active, self.chart_position.xy)

    def draw_text(self, text, position, color=None):
        self.screen.blit(utils.gui_text(text=text, fg=color), position)

    def simulate(self,
                 creatures_start=None, fruits_start=None,
                 fruits_chance=None, fruits_max=None,
                 quit_on_extinct=False):

        # Creature / fruit generation is bound to tile count
        tile_count = self.map_tiles.x * self.map_tiles.y

        # Defaults
        # TODO : Configureable
        if creatures_start is None:
            creatures_start = tile_count * 2
        if fruits_start is None:
            fruits_start = tile_count * 5
        if fruits_max is None:
            fruits_max = tile_count * 8
        if fruits_chance is None:
            fruits_chance = 0.01

        # Creatures
        for _ in range(creatures_start):
            Creature(self)

        # Fruits
        for _ in range(fruits_start):
            Fruit.spawn(self)

        self.running = True
        while self.running:

            # Data...
            if not self.time % self.chart_interval:
                # Compute metrics
                # TODO : Optimize....
                new_data = {
                    'cps': (round(self.clock.get_fps(), 2),),
                    'creatures': (len(self.creatures),),
                    'fruits': (len(self.fruits),),
                    'size': utils.stat_quantiles([c.size.value for c in self.creatures]),
                    'speed': utils.stat_quantiles([c.speed.value for c in self.creatures]),
                    'perception': utils.stat_quantiles([c.perception.value for c in self.creatures]),
                    'digestion': utils.stat_quantiles([c.digestion.value for c in self.creatures])
                }
                # Push to chart
                self.chart.add_data(data=new_data)

            # Clear screen, world and map
            self.screen.fill(SCREEN_BACKGROUND)
            self.world.blit(self.world_background, (0, 0))
            self.map.fill(utils.ALPHA_COLOR)

            # Clear selection?
            if self.selected and not self.selected.alive():
                self.clear_selected()

            # Spawn fruits?
            for _ in range(tile_count):
                if len(self.fruits) < fruits_max:
                    if random.random() <= fruits_chance:
                        Fruit.spawn(self)

            # Handle events
            for event in pygame.event.get():
                # Mouse
                self.handle_mouse(event)
                # Keyboard
                self.handle_keyboard(event)
                # Exit
                if event.type == pygame.QUIT:
                    self.running = False

            # Update
            self.update_grid()
            self.fruits.update()
            self.creatures.update()

            # Draw
            self.fruits.draw(self.map)
            self.creatures.draw(self.map)
            self.draw_world()
            self.draw_ui()

            # Flip the display
            pygame.display.flip()

            # Time is passing...
            self.time += 1
            self.clock.tick(self.speed)

            # Creatures extinct?
            if not self.creatures and quit_on_extinct:
                self.running = False

        # Simulation done, exit
        return self.time  # TODO : Return actual stats

    def cleanup(self):
        # TODO: Anything else to cleanup?
        pygame.quit()
