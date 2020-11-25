import argparse
from evo.engine import Engine

parser = argparse.ArgumentParser()
parser.add_argument("--display", required=False, type=int, default=0, help='Display ID')
args = parser.parse_args()

engine = Engine(fullscreen=True, display=args.display)
engine.simulate()
engine.cleanup()
