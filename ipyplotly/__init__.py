import ipywidgets as widgets
from traitlets import List, Unicode, Dict, Tuple, default

from ipyplotly.datatypes import Scatter
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
        self._plotly_addTraces = add_traces_msg
        self._plotly_addTraces = None

        # Update python side
        self._traces.append(scatt._data)
        self.traces = self.traces + (scatt,)

        return scatt

    def restyle(self, style, trace_index=None):
        restype_msg = (style, trace_index)
        print('Restyle: {msg}'.format(msg=restype_msg))
        self._plotly_restyle = restype_msg
        self._plotly_restyle = None

        # TODO: update self._traces with new style


