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


@widgets.register
class BaseTrace(widgets.Widget):
    _model_name = Unicode('BaseTraceModel').tag(sync=True)
    _model_module = Unicode('ipyplotly').tag(sync=True)


@widgets.register
class Figure(widgets.DOMWidget):
    _view_module = Unicode('ipyplotly').tag(sync=True)
    _view_name = Unicode('FigureView').tag(sync=True)
    _view_module_version = Unicode(__frontend_version__).tag(sync=True)

    _model_name = Unicode('FigureModel').tag(sync=True)
    _model_module = Unicode('ipyplotly').tag(sync=True)

    traces = List(Instance(BaseTrace)).tag(sync=True, **widget_serialization)

    def add_scatter(self, x: ty.List, y: ty.List, opacity: float):
        new_trace = Scatter(opacity=opacity, x=x, y=y)
        new_trace.figure = self
        self.traces = self.traces + [new_trace]


@widgets.register
class Scatter(BaseTrace):
    """The scatter trace type encompasses line charts, scatter charts, text charts, and bubble charts.
    The data visualized as scatter point or lines is set in `x` and `y`. Text (appearing either on the chart or on
    hover only) is via `text`. Bubble charts are achieved by setting `marker.size` and/or `marker.color` to numerical
    arrays."""
    _model_name = Unicode('ScatterModel').tag(sync=True)
    _model_module = Unicode('ipyplotly').tag(sync=True)

    # parent figure
    # -------------
    figure = Instance(Figure, allow_none=True).tag(sync=True,
                                                   **widget_serialization)

    # trace type
    # ----------
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

    def __init__(self, x: ty.List, y: ty.List, opacity: float):
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





