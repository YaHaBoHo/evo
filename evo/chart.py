import collections
import pygame
from evo import utils

# Constants and Defaults
CHART_BACKGROUND = (192, 192, 192)
CHART_ALPHA = 192
CHART_LINE_COLOR = (0, 0, 255)
CHART_AREA_COLOR = (64, 128, 255)


# Initialize
pygame.init()


class Chart():

    def __init__(self, size, history=100):
        # Config
        self.size = utils.Int2D(*size)
        self.history = history
        # Internals
        self.metrics = list()
        self.data = dict()
        self.plots = dict()
        self.active = self._cycle()
        # Initialize
        self.redraw()

    def add_metric(self, name, vmin=None, vmax=None):
        self.metrics.append((name, vmin, vmax))
        self.data[name] = collections.deque(maxlen=self.history)
        self.plots[name] = pygame.Surface(self.size.xy)

    def add_data(self, data):
        for metric_name, _, _ in self.metrics:
            self.data[metric_name].append(data.get(metric_name, (0,)))
        self.redraw()

    def redraw(self):
        for metric_name, vmin, vmax in self.metrics:
            # Fetch metric data
            data = self.data[metric_name]
            # Reset background and alpha
            self.plots[metric_name].fill(CHART_BACKGROUND)
            self.plots[metric_name].set_alpha(CHART_ALPHA)
            # Not enough data, render placeholder text and quit
            if len(data) < 3:
                self.plots[metric_name].blit(
                    source=utils.gui_text("{} (not enough data)".format(metric_name), bg=CHART_BACKGROUND),
                    dest=(int(0.5*self.size.x-60), int(0.5*self.size.y)))
                continue
            # Draw chart
            # TODO : Optimize...
            # - Data bounds
            slot_x = self.size.x/(len(data)-1)
            plot_min = min(min(dp) for dp in data) if vmin is None else vmin
            plot_max = max(max(dp) for dp in data) if vmax is None else vmax
            # - Charts
            mid0 = utils.Int2D(0, self.size.y - utils.scale(data[0][0], plot_min, plot_max, 0, self.size.y))
            for i in range(1, len(data)):
                pos_x = i*slot_x
                # Area-chart
                try:
                    low1 = max(self.size.y - utils.scale(data[i][1], plot_min, plot_max, 0, self.size.y), mid0.y)
                    high1 = min(self.size.y - utils.scale(data[i][2], plot_min, plot_max, 0, self.size.y), mid0.y)
                    pygame.draw.rect(
                        self.plots[metric_name],
                        CHART_AREA_COLOR,
                        pygame.Rect((pos_x-slot_x, high1), (slot_x+1, low1-high1+1))
                    )
                except IndexError:
                    pass
                # Line-chart
                mid1 = utils.Int2D(pos_x, self.size.y - utils.scale(data[i][0], plot_min, plot_max, 0, self.size.y))
                pygame.draw.line(self.plots[metric_name], CHART_LINE_COLOR, mid0.xy, mid1.xy, 1)
                # Reset to next
                mid0 = mid1
            # Chart title
            self.plots[metric_name].blit(
                source=utils.gui_text(metric_name, bg=CHART_BACKGROUND),
                dest=(int(0.5*self.size.x-30), 10)
            )
            # Y-min
            self.plots[metric_name].blit(
                source=utils.gui_text(round(plot_min, 2), bg=CHART_BACKGROUND),
                dest=(10, self.size.y-15)
            )
            # Y-max
            self.plots[metric_name].blit(
                source=utils.gui_text(round(plot_max, 2), bg=CHART_BACKGROUND),
                dest=(10, 10)
            )
            # Y-latest
            _latest = utils.gui_text(
                text=round(data[-1][0], 2),
                fg=CHART_LINE_COLOR,
                bg=CHART_BACKGROUND
            )
            self.plots[metric_name].blit(
                source=_latest,
                dest=(self.size.x-(_latest.get_width()+5), max(mid0.y-_latest.get_height(), 5))
            )

    def _cycle(self):
        while True:
            yield None
            for metric_name, _, _ in self.metrics:
                yield self.plots[metric_name]
