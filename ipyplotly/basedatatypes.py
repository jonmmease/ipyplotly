import uuid

import ipywidgets as widgets
from traitlets import List, Unicode, Dict, Tuple, default, observe
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

    # JS -> Python message properties
    _plotly_addTraceDeltas = List(allow_none=True).tag(sync=True)

    # Non-sync properties
    traces = Tuple(())

    @default('_plotly_addTraces')
    def _plotly_addTraces_default(self):
        return None

    _plotly_restyle = List(allow_none=True).tag(sync=True)

    @default('_plotly_restyle')
    def _plotly_restyle_default(self):
        return None

    @observe('_plotly_addTraceDeltas')
    def handler_plotly_addTraceDeltas(self, change):
        deltas = change['new']
        if not deltas:
            return

        for delta in deltas:
            uid = delta['uid']
            uid_traces = [trace for trace in self.traces if trace._data.get('uid', None) == uid]
            assert len(uid_traces) == 1
            uid_trace = uid_traces[0]
            BaseFigureWidget.apply_trace_delta(uid_trace._data, delta)

        # Remove processed trace delta data
        self._plotly_addTraceDeltas = None

    @staticmethod
    def apply_trace_delta(trace_data, delta_data):
        for p, delta_val in delta_data.items():
            assert p in trace_data

            trace_val = trace_data[p]
            if isinstance(delta_val, dict):
                assert isinstance(trace_data, dict)

                BaseFigureWidget.apply_trace_delta(trace_val, delta_val)
                pass
            else:
                trace_data[p] = delta_val

    def restyle(self, style, trace_index=None):
        restype_msg = (style, trace_index)
        print('Restyle: {msg}'.format(msg=restype_msg))
        self._plotly_restyle = restype_msg
        self._plotly_restyle = None

        # TODO: update self._traces with new style

    def _restyle_child(self, child, prop, val):

        send_val = [val]

        trace_index = self.traces.index(child)
        self.restyle({prop: send_val}, trace_index=trace_index)

    def _add_trace(self, trace):
        # Send to front end
        if not trace._data.get('uid', None):
            trace._data['uid'] = str(uuid.uuid1())

        add_traces_msg = [trace._data]
        self._plotly_addTraces = add_traces_msg
        self._plotly_addTraces = None

        # Update python side
        self._traces = self._traces + [trace._data]
        self.traces = self.traces + (trace,)

        return trace


class BaseTraceType:

    def __init__(self, type_name):
        self.type_name = type_name
        self._data = {}
        self._validators = {}
        self.parent = None

    def _send_restyle(self, prop, val):
        print('%s: _send_restyle' % self.type_name)
        if self.parent:
            self.parent._restyle_child(self, prop, val)

    def _set_prop(self, prop, val):
        validator = self._validators.get(prop)
        val = validator.validate_coerce(val)

        if prop not in self._data or self._data[prop] != val:
            self._data[prop] = val
            self._send_restyle(prop, val)

    def _set_compound_prop(self, prop, val, curr_val):
        validator = self._validators.get(prop)
        val = validator.validate_coerce(val)

        # Reparent
        val.parent = self
        dict_val = val._data
        if curr_val is not None and curr_val is not val:
            curr_val.parent = None

        if prop not in self._data or self._data[prop] != dict_val:
            self._data[prop] = dict_val
            self._send_restyle(prop, dict_val)

        return val

    def _restyle_child(self, child, prop, val):
        self._send_restyle('{child_name}.{prop}'.format(child_name=child.type_name, prop=prop), val)


class BaseLayoutType:
    # _send_relayout analogous to _send_restyle above
    pass
