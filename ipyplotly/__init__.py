from traitlets import Instance, List, Unicode, Float, TraitError, validate, \
    Dict, Tuple, Int, default
import typing as ty
from ipywidgets import DOMWidget, register, widget_serialization
import ipywidgets as widgets

from ipyplotly.compoundtypes import Scatter
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

    # Data properties for front end
    _layout = Dict().tag(sync=True)
    _traces = List().tag(sync=True)

    # Python -> JS message properties
    _plotly_addTraces = List(trait=Dict(),
                             allow_none=True).tag(sync=True)

    # Non-sync properties
    traces = Tuple(())

    @default('_plotly_addTraces')
    def _plotly_addTraces_default(self):
        return None

    _plotly_restyle = List(allow_none=True).tag(sync=True)

    @default('_plotly_restyle')
    def _plotly_restyle_default(self):
        return None

    def _restyle_child(self, child, prop, val):
        trace_index = self.traces.index(child)
        self.restyle({prop: val}, trace_index=trace_index)

    def add_scatter(self,
                    x,
                    y,
                    opacity=1.0,
                    name=None):
        """

        Parameters
        ----------
        x
            The x coordinates
        y
            The y coordinates
        opacity
            The trace opacity
        name
            The trace name
        """
        scatt = Scatter(x=x, y=y, opacity=opacity, parent=self)

        # Send to front end
        add_traces_msg = [scatt._data]
        print(add_traces_msg)
        self._plotly_addTraces = add_traces_msg
        self._plotly_addTraces = None

        # Update python side
        self._traces.append(scatt._data)
        self.traces = self.traces + (scatt,)

        return scatt

    def restyle(self, style, trace_index=None):
        restype_msg = (style, trace_index)
        print(restype_msg)
        self._plotly_restyle = restype_msg
        self._plotly_restyle = None

        # TODO: update self._traces with new style

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



