from traitlets import Instance, List, Unicode, Float, TraitError, validate
import typing as ty
from ipywidgets import DOMWidget, register, widget_serialization
import ipywidgets as widgets
from ._version import version_info, __version__

def _jupyter_nbextension_paths():
    return [{
        'section': 'notebook',
        'src': 'static',
        'dest': 'ipyplotly',
        'require': 'ipyplotly/extension'
    }]

__frontend_version__ = '^0.1'


class Scatter(widgets.Widget):
    """The scatter trace type encompasses line charts, scatter charts, text charts, and bubble charts.
    The data visualized as scatter point or lines is set in `x` and `y`. Text (appearing either on the chart or on
    hover only) is via `text`. Bubble charts are achieved by setting `marker.size` and/or `marker.color` to numerical
    arrays."""

    _view_module = Unicode('ipyplotly').tag(sync=True)
    _view_name = Unicode('ScatterView').tag(sync=True)
    _view_module_version = Unicode(__frontend_version__).tag(sync=True)

    type = Unicode("scatter", read_only=True).tag(sync=True)

    # opacity
    # -------
    opacity = Float(1.0).tag(sync=True)
    """Sets the opacity of the trace."""

    @validate('opacity')
    def _valid_value(self, proposal):
        val = proposal['value']
        if val < 0 or val > 1:
            raise TraitError(f"Value of 'opacity' must fall between 0 and 1. Received value of {val}")
        return val

    # x
    # -
    x = List(default_value=[]).tag(sync=True)
    """Sets the x coordinates."""

    # y
    # -
    y = List(default_value=[]).tag(sync=True)
    """Sets the Y coordinates."""

    def __init__(self, fig, x: ty.List, y: ty.List, opacity: float):
        """
        The scatter trace type encompasses line charts, scatter charts, text charts, and bubble charts.
        The data visualized as scatter point or lines is set in `x` and `y`. Text (appearing either on the chart or on
        hover only) is via `text`. Bubble charts are achieved by setting `marker.size` and/or `marker.color` to
        numerical arrays.

        Parameters
        ----------
        opacity: float
            Sets the opacity of the trace.
        x: List
            Sets the x coordinates.
        y: List
            Sets the Y coordinates.
        """
        super().__init__(opacity=opacity, x=x, y=y)
        self.fig = fig


class Figure(widgets.DOMWidget):
    _view_module = Unicode('ipyplotly').tag(sync=True)
    _view_name = Unicode('FigureView').tag(sync=True)
    _view_module_version = Unicode(__frontend_version__).tag(sync=True)

    _model_name = Unicode('FigureModel').tag(sync=True)
    _model_module = Unicode('ipyplotly').tag(sync=True)

    # plotly_data_str = Unicode().tag(sync=True)
    # plotly_layout_str = Unicode().tag(sync=True)

    traces = List(Instance(Scatter)).tag(sync=True, **widget_serialization)

    def add_scatter(self, x: ty.List, y: ty.List, opacity: float):
        new_trace = Scatter(fig=self, opacity=opacity, x=x, y=y)
        self.traces = self.traces + [new_trace]

