import argparse
from evo.engine import Engine


def int_tuple(argument):
    res = str(argument).split(",")
    return (int(res[0]), int(res[1]))


# Basic arguments
parser = argparse.ArgumentParser()
# Map size
parser.add_argument(
    "--map", 
    required=False, 
    default="6,4", 
    type=int_tuple, 
    help='Map size in TILES: width,height')
# Screen resolution
parser.add_argument(
    "--resolution", 
    required=False, 
    default="1024,768", 
    type=int_tuple, 
    help='Screen resolution in PIXELS: width,height')
# Fullscreen switch
parser.add_argument(
    "--fullscreen", 
    required=False, 
    default=False, 
    action='store_true', 
    help='Enables fullscreen mode')
# Disaply selection (fullscreen only)
parser.add_argument(
    "--display", 
    required=False, 
    default=0, 
    type=int, 
    help='Display ID (fullscreen only)')
# Parse
args = parser.parse_args()


# Run simulation
engine = Engine(
    map_tiles=args.map,
    screen_resolution=args.resolution,
    fullscreen=args.fullscreen, 
    display=args.display
)
engine.simulate()
engine.cleanup()
