import ipywidgets as widgets
from traitlets import List, Unicode, Dict, Tuple, default
from ipyplotly.basevalidators import CompoundValidator


@widgets.register
class BaseFigureWidget(widgets.DOMWidget):
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

    def restyle(self, style, trace_index=None):
        restype_msg = (style, trace_index)
        print('Restyle: {msg}'.format(msg=restype_msg))
        self._plotly_restyle = restype_msg
        self._plotly_restyle = None

        # TODO: update self._traces with new style

    def _restyle_child(self, child, prop, val):
        trace_index = self.traces.index(child)
        self.restyle({prop: val}, trace_index=trace_index)

    def _add_trace(self, trace):
        # Send to front end
        add_traces_msg = [trace._data]
        self._plotly_addTraces = add_traces_msg
        self._plotly_addTraces = None

        # Update python side
        self._traces.append(trace._data)
        self.traces = self.traces + (trace,)

        return trace


class BaseDataType:

    def __init__(self, type_name):
        self.type_name = type_name
        self._data = {}
        self._validators = {}
        self.parent = None

    def _send_restyle(self, prop, val):
        if self.parent:
            send_val = [val] if isinstance(val, list) else val
            self.parent._restyle_child(self, prop, send_val)

    def _set_prop(self, prop, val):
        validator = self._validators.get(prop)
        val = validator.validate_coerce(val)

        if isinstance(validator, CompoundValidator):
            # Reparent
            val.parent = self
            dict_val = val._data
        else:
            dict_val = val

        if prop not in self._data or self._data[prop] != dict_val:
            self._data[prop] = dict_val
            self._send_restyle(prop, dict_val)

        return val

    def _restyle_child(self, child, prop, val):
        self._send_restyle('{child_name}.{prop}'.format(child_name=child.type_name, prop=prop), val)