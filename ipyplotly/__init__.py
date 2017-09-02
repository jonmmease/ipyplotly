from traitlets import Instance, List, Unicode, Float, TraitError, validate, \
    Dict, Tuple, Int, default
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
class Figure(widgets.DOMWidget):

    _view_name = Unicode('FigureView').tag(sync=True)
    _view_module = Unicode('ipyplotly').tag(sync=True)
    _model_name = Unicode('FigureModel').tag(sync=True)
    _model_module = Unicode('ipyplotly').tag(sync=True)

    # Data properties
    _layout = Dict().tag(sync=True)
    _traces = List().tag(sync=True)

    # Python -> JS message properties
    _plotly_addTraces = List(trait=Dict(),
                             allow_none=True).tag(sync=True)

    @default('_plotly_addTraces')
    def _plotly_addTraces_default(self):
        return None

    _plotly_restyle = List(allow_none=True).tag(sync=True)

    @default('_plotly_restyle')
    def _plotly_restyle_default(self):
        return None

    def add_scatter(self, x: ty.List, y: ty.List, opacity: float):
        new_trace = dict(opacity=opacity, x=x, y=y)
        self._plotly_addTraces = [new_trace]
        self._plotly_addTraces = None

        # Update python side
        self._traces.append(new_trace)

    def restyle(self, style, trace_index=None):
        self._plotly_restyle = (style, trace_index)
        self._plotly_restyle = None

        # TODO: update self._traces with new style


class Scatter:

    def __init__(self, **kwargs):
        self._data = {}
        self._reset_defaults()
        # Add kwargs and defaults

    def _reset_defaults(self):
        self._data.clear()

        self._data['opacity'] = 1.0

    @property
    def opacity(self):
        return self._data['opacity']

    @opacity.setter
    def opacity(self, val):
        # Validate type
        self._data['opacity'] = val


# class Scatter():
#     """The scatter trace type encompasses line charts, scatter charts, text charts, and bubble charts.
#     The data visualized as scatter point or lines is set in `x` and `y`. Text (appearing either on the chart or on
#     hover only) is via `text`. Bubble charts are achieved by setting `marker.size` and/or `marker.color` to numerical
#     arrays."""
#     _model_name = Unicode('ScatterModel').tag(sync=True)
#     _model_module = Unicode('ipyplotly').tag(sync=True)
#
#     # parent figure
#     # -------------
#     figure = Instance(Figure, allow_none=True).tag(sync=True,
#                                                    **widget_serialization)
#
#     # trace type
#     # ----------
#     type = Unicode("scatter", read_only=True).tag(sync=True)
#
#     # opacity
#     # -------
#     opacity = Float(1.0).tag(sync=True)
#     """Sets the opacity of the trace."""
#
#     @validate('opacity')
#     def _valid_value(self, proposal):
#         val = proposal['value']
#         if val < 0 or val > 1:
#             raise TraitError(f"Value of 'opacity' must fall between 0 and 1. Received value of {val}")
#         return val
#
#     # x
#     # -
#     x = List(default_value=[]).tag(sync=True)
#     """Sets the x coordinates."""
#
#     # y
#     # -
#     y = List(default_value=[]).tag(sync=True)
#     """Sets the Y coordinates."""
#
#     def __init__(self, x: ty.List, y: ty.List, opacity: float):
#         """
#         The scatter trace type encompasses line charts, scatter charts, text charts, and bubble charts.
#         The data visualized as scatter point or lines is set in `x` and `y`. Text (appearing either on the chart or on
#         hover only) is via `text`. Bubble charts are achieved by setting `marker.size` and/or `marker.color` to
#         numerical arrays.
#
#         Parameters
#         ----------
#         opacity: float
#             Sets the opacity of the trace.
#         x: List
#             Sets the x coordinates.
#         y: List
#             Sets the Y coordinates.
#         """
#         super().__init__(opacity=opacity, x=x, y=y)
#
#



