import collections
import uuid

import ipywidgets as widgets
from traitlets import List, Unicode, Dict, Tuple, default, observe, validate, TraitError
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
    _plotly_restyle = List(allow_none=True).tag(sync=True)

    _plotly_deleteTraces = List(allow_none=True).tag(sync=True)
    _plotly_moveTraces = List(allow_none=True).tag(sync=True)

    # JS -> Python message properties
    _plotly_addTraceDeltas = List(allow_none=True).tag(sync=True)

    # Non-sync properties
    traces = Tuple(())

    @default('_plotly_addTraces')
    def _plotly_addTraces_default(self):
        return None

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

    @validate('traces')
    def handle_traces_update(self, proposal):
        new_traces = proposal['value']

        # Validate new_traces
        orig_uids = [_trace['uid'] for _trace in self._traces]
        new_uids = [trace.uid for trace in new_traces]

        invalid_uids = set(new_uids).difference(set(orig_uids))
        if invalid_uids:
            raise TraitError(('The trace property of a figure may only be assigned to '
                              'a permutation of a subset of itself\n'
                              '    Invalid trace(s) with uid(s): {invalid_uids}').format(invalid_uids=invalid_uids))

        # Check for duplicates
        uid_counter = collections.Counter(new_uids)
        duplicate_uids = [uid for uid, count in uid_counter.items() if count > 1]
        if duplicate_uids:
            raise TraitError(('The trace property of a figure may not be assigned '
                              'multiple copies of a trace\n'
                              '    Duplicate trace uid(s): {duplicate_uids}'
                              ).format(duplicate_uids=duplicate_uids))

        # Compute traces to remove
        remove_uids = set(orig_uids).difference(set(new_uids))
        remove_inds = []
        for i, _trace in enumerate(self._traces):
            if _trace['uid'] in remove_uids:
                remove_inds.append(i)

                # Unparent trace object to be removed
                self.traces[i].parent = None

        # Compute trace data list after removal
        traces_data_post_removal = [t for t in self._traces]
        for i in reversed(remove_inds):
            del traces_data_post_removal[i]

        if remove_inds:
            self._plotly_deleteTraces = remove_inds
            self._plotly_deleteTraces = None

        # Compute move traces
        new_inds = []

        for uid in [t['uid'] for t in traces_data_post_removal]:
            new_inds.append(new_uids.index(uid))

        current_inds = list(range(len(traces_data_post_removal)))

        if not all([i1 == i2 for i1, i2 in zip(new_inds, current_inds)]):
            self._plotly_moveTraces = [current_inds, new_inds]

        # Update _traces order
        self._traces = [_trace for i, _trace in sorted(zip(new_inds, traces_data_post_removal))]

        return new_traces

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

        # Add UID if not set
        if not trace._data.get('uid', None):
            trace._data['uid'] = str(uuid.uuid1())

        # Update python side
        self._traces = self._traces + [trace._data]
        self.traces = self.traces + (trace,)

        # Send to front end
        add_traces_msg = [trace._data]
        self._plotly_addTraces = add_traces_msg
        self._plotly_addTraces = None

        return trace


class BaseTraceType:

    def __init__(self, type_name):
        self.type_name = type_name
        self._data = {}
        self._validators = {}
        self.parent = None

    def _send_restyle(self, prop, val):
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
