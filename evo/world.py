import time
import random
import pygame
from evo import utils
from evo.node import Creature, Fruit
from evo.dna import  Size, Speed, Perception
from evo.chart import Chart

# TODO : Type hints


# Initialize
pygame.init()
pygame.display.set_caption("eVo")


class World():

    SPEED_RANGE = (1, 20)
    SCALE_RANGE = (0.25, 1)

    TILE_SIZE = 256
    BACKGROUND_COLOR = (92, 142, 167)


    def __init__(self, map_size=(8, 4)):
        # Screen
        self.screen_size = utils.Int2D(1024, 768)  # TODO : Custom screen size
        self.screen = pygame.display.set_mode(self.screen_size.xy)
        # Images
        self.images_tiles = utils.load_map_tiles()
        self.images_fruits = utils.load_fruit_sprites()
        self.images_creatures = utils.load_creature_sprites((Size.VMIN, Size.VMAX))
        # Map background
        self.world_tiles = utils.Int2D(*map_size) + 2
        self.map_bg = self.load_background()
        # Map surface
        self.map_size = utils.Int2D(*self.map_bg.get_size())
        self.map_pos = pygame.math.Vector2(self.screen_size.xy) / 2
        self.map_drag = None
        self.map_scale = 1
        self.map = pygame.Surface(self.map_size.xy)
        # Chart
        ## Config
        self.chart = Chart(size=(self.screen_size/3).xy, history=150)  # TODO : Dynamic
        self.chart_pos = self.screen_size - self.chart.size
        self.chart_active = next(self.chart.active)
        self.chart_interval = 100  # TODO : Configureable
        ## Metrics
        self.chart.add_metric("fps", 0)
        self.chart.add_metric("creatures", 0)
        self.chart.add_metric("fruits", 0)
        self.chart.add_metric("size", 0, Size.VMAX)
        self.chart.add_metric("speed", 0, Speed.VMAX)
        self.chart.add_metric("perception", 0, Perception.VMAX)
        # Node groups
        self.fruits = pygame.sprite.Group()
        self.creatures = pygame.sprite.Group()
        self.lifeforms = pygame.sprite.Group()
        # Internals
        self.clock = pygame.time.Clock()
        self.selected = None
        self.selected_idx = -1
        self.speed = 5
        self.time = 0   

    def load_background(self):
        background = pygame.Surface((self.world_tiles * self.TILE_SIZE).xy)
        for tile_x in range(self.world_tiles.x):
            for tile_y in range(self.world_tiles.y):
                # Tile coordinates
                tile_pos = (self.TILE_SIZE*tile_x, self.TILE_SIZE*tile_y)
                background.blit(self.load_tile(tile_x, tile_y), tile_pos)
        return background

    def load_tile(self, x, y):
        # Tile type?
        if x == 0:
            if y == 0:
                # Top-left corner
                return random.choice(self.images_tiles['corner'])
            elif y == self.world_tiles.y - 1:
                # Bottom-left corner
                return pygame.transform.rotate(random.choice(self.images_tiles['corner']), 90)
            else:
                # Left edge
                return random.choice(self.images_tiles['edge'])
        elif x == self.world_tiles.x - 1:
            if y == 0:
                # Top-right corner
                return pygame.transform.rotate(random.choice(self.images_tiles['corner']), -90)
            elif y == self.world_tiles.y - 1:
                # Bottom-right corner
                return pygame.transform.rotate(random.choice(self.images_tiles['corner']), 180)
            else:
                # Right edge
                return pygame.transform.rotate(random.choice(self.images_tiles['edge']), 180)
        elif y == 0:
            # Top edge
            return pygame.transform.rotate(random.choice(self.images_tiles['edge']), -90)
        elif y == self.world_tiles.y - 1:
            # Bottom edge
            return pygame.transform.rotate(random.choice(self.images_tiles['edge']), 90)
        else:
            # Center / main tile      
            return random.choice(self.images_tiles['center'])

    def select_next(self, clear=False):
        # TODO : Review logic
        if self.creatures and not clear:
            self.selected_idx = (self.selected_idx + 1) % len(self.creatures)
            self.selected = self.creatures.sprites()[self.selected_idx]
            return
        # If clear requested or group empty, clear selection
        self.clear_selected()

    def clear_selected(self):
        self.selected = None
        self.selected_idx = -1

    def handle_mouse(self, event):
        # Drag map
        if event.type == pygame.MOUSEBUTTONDOWN:
            self.map_drag = pygame.Vector2(event.pos) - self.map_pos
        elif event.type == pygame.MOUSEBUTTONUP:
            self.map_drag = None
        elif event.type == pygame.MOUSEMOTION:
            if isinstance(self.map_drag, pygame.math.Vector2):
                self.map_pos = pygame.math.Vector2(event.pos) - self.map_drag
        # Zoom
        elif event.type == pygame.MOUSEWHEEL:
            self.map_scale = utils.clamp(self.map_scale + 0.05 * event.y, *self.SCALE_RANGE)

    def handle_keyboard(self, event):
        if event.type == pygame.KEYDOWN:
            # Simulation speed
            ## Faster
            if event.key == pygame.K_UP:
                self.speed = utils.clamp(self.speed+1, *self.SPEED_RANGE)
            if event.key == pygame.K_PAGEUP:
                self.speed = utils.clamp(self.speed+5, *self.SPEED_RANGE)
            ## Slower
            if event.key == pygame.K_DOWN:
                self.speed = utils.clamp(self.speed-1, *self.SPEED_RANGE)
            if event.key == pygame.K_PAGEDOWN:
                self.speed = utils.clamp(self.speed-5, *self.SPEED_RANGE)
            ## Reset
            if event.key == pygame.K_SPACE:
                self.speed = 5
            # Creature selection
            if event.key == pygame.K_TAB:
                self.select_next()
            if event.key == pygame.K_ESCAPE:
                self.clear_selected()
            # Chart selection
            if event.key in (pygame.K_LSHIFT, pygame.K_RSHIFT):
                self.chart_active = next(self.chart.active)

    def draw_map(self):
        # Scale map?
        if self.map_scale < 1:
            _map = pygame.transform.smoothscale(self.map, (self.map_size * self.map_scale).xy)
        else:
            _map = self.map
        # Blit
        self.screen.blit(_map, self.map_pos - _map.get_rect().center)

    def draw_ui(self):
        # TODO : Dynamic placement...
        # World info 
        self.draw_text("Time: {}".format(self.time), (20, 20))
        self.draw_text("FPS: {}".format(round(self.clock.get_fps(), 2)), (20, 40))
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
            self.draw_text("Target: {}".format(sc.target), (20, self.screen_size.y-20))
        # Chart
        if self.chart_active:
            self.screen.blit(self.chart_active, self.chart_pos.xy)

    def draw_text(self, text, position, color=None):
        self.screen.blit(utils.gui_text(text=text, fg=color), position)

    def randomize_position(self) -> pygame.math.Vector2:
        return pygame.Vector2(
            (self.map_size.x - 512) * random.random() + 256,
            (self.map_size.y - 512) * random.random() + 256
        )

    def clamp_position(self, pos:pygame.math.Vector2) -> pygame.math.Vector2:
        return pygame.math.Vector2(
            utils.clamp(pos.x, 256, self.map_size.x-256),
            utils.clamp(pos.y, 256, self.map_size.y-256)
        )

    def simulate(self, creatures_start=None, fruits_start=None, fruits_chance=None, fruits_max=None):
      
        # Creature / fruit generation is bound to tile count
        tile_count = (self.world_tiles.x-2) * (self.world_tiles.y-2)

        # Defaults
        # TODO : Configureable
        if creatures_start is None:
            creatures_start = tile_count * 2
        if fruits_start is None:
            fruits_start = tile_count * 4  
        if fruits_max is None:
            fruits_max = tile_count * 6
        if fruits_chance is None:
            fruits_chance = 0.005

        # Creatures
        for _ in range(creatures_start):
            Creature(self)

        # Fruits
        for _ in range(fruits_start):
            Fruit.spawn(self)

        running = True
        while running:

            # Data...
            if not self.time % self.chart_interval:
                # Compute metrics 
                # TODO : Optimize....       
                new_data = {
                    'fps': (round(self.clock.get_fps(), 2),),
                    'creatures': (len(self.creatures),),
                    'fruits': (len(self.fruits),),
                    'size': utils.stat_quantiles([c.size.value for c in self.creatures]),
                    'speed': utils.stat_quantiles([c.speed.value for c in self.creatures]),
                    'perception': utils.stat_quantiles([c.perception.value for c in self.creatures])
                }
                # Push to chart
                self.chart.add_data(data=new_data)

            # Clear screen and map
            self.screen.fill(self.BACKGROUND_COLOR)
            self.map.blit(self.map_bg, (0,0))

            # Clear selection?
            if self.selected and not self.selected.alive():
                self.clear_selected()

            # Spawn fruits?
            for _ in range(tile_count):
                if len(self.fruits) < fruits_max:
                        if random.random() <= fruits_chance:
                            Fruit.spawn(self)

            # Check and dispatch events
            for event in pygame.event.get():
                # Mouse
                self.handle_mouse(event)
                # Keyboard
                self.handle_keyboard(event)
                # Exit
                if event.type == pygame.QUIT:
                    running = False

            # Update
            self.fruits.update()
            self.creatures.update()

            # Draw
            self.fruits.draw(self.map)
            self.creatures.draw(self.map)
            self.draw_map()
            self.draw_ui()

            # Flip the display
            pygame.display.flip()

            # Time is passing...
            self.time += 1
            self.clock.tick(15 + 3*self.speed)


    def cleanup(self):
        # TODO: Anything else to cleanup?
        pygame.quit()
