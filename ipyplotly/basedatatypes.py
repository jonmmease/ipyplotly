import collections
import uuid

import ipywidgets as widgets
from traitlets import List, Unicode, Dict, Tuple, default, observe, validate, TraitError
from ipyplotly.basevalidators import CompoundValidator

"""
Next steps:

    - Don't sync _layout_data and _traces_data
    - JS model keeps a stack of plotly commands, not layout/traces data itself
    - JS Model listens for commands and adds them to the stack
    - JS Views listen for commands and execute them (as they do now)
    - JS View renders execute commands from the beginning in order to sync up with the others.

"""

@widgets.register
class BaseFigureWidget(widgets.DOMWidget):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Initialize backing property for trace objects
        self._traces = ()

    _view_name = Unicode('FigureView').tag(sync=True)
    _view_module = Unicode('ipyplotly').tag(sync=True)
    _model_name = Unicode('FigureModel').tag(sync=True)
    _model_module = Unicode('ipyplotly').tag(sync=True)

    # Data properties for front end
    _layout_data = Dict().tag(sync=True)
    _traces_data = List().tag(sync=True)

    # Python -> JS message properties
    _plotly_addTraces = List(trait=Dict(),
                             allow_none=True).tag(sync=True)
    _plotly_restyle = List(allow_none=True).tag(sync=True)

    _plotly_deleteTraces = List(allow_none=True).tag(sync=True)
    _plotly_moveTraces = List(allow_none=True).tag(sync=True)

    # JS -> Python message properties
    _plotly_addTraceDeltas = List(allow_none=True).tag(sync=True)
    _plotly_restylePython = List(allow_none=True).tag(sync=True)

    # Non-sync properties
    traces = Tuple(allow_none=True)

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


    @observe('_plotly_restylePython')
    def handler_plotly_restylePython(self, change):
        restyle_msg = change['new']
        if not restyle_msg:
            return

        restyle_data = restyle_msg[0]
        if len(restyle_msg) > 1 and restyle_msg[1] is not None:
            trace_inds = restyle_msg[1]
        else:
            trace_inds = None

        self.restyle(restyle_data, trace_inds)

    @property
    def traces(self):
        return self._traces

    @traces.setter
    def traces(self, new_traces):

        # Validate new_traces
        orig_uids = [_trace['uid'] for _trace in self._traces_data]
        new_uids = [trace.uid for trace in new_traces]

        invalid_uids = set(new_uids).difference(set(orig_uids))
        if invalid_uids:
            raise ValueError(('The trace property of a figure may only be assigned to '
                              'a permutation of a subset of itself\n'
                              '    Invalid trace(s) with uid(s): {invalid_uids}').format(invalid_uids=invalid_uids))

        # Check for duplicates
        uid_counter = collections.Counter(new_uids)
        duplicate_uids = [uid for uid, count in uid_counter.items() if count > 1]
        if duplicate_uids:
            raise ValueError(('The trace property of a figure may not be assigned '
                              'multiple copies of a trace\n'
                              '    Duplicate trace uid(s): {duplicate_uids}'
                              ).format(duplicate_uids=duplicate_uids))

        # Compute traces to remove
        remove_uids = set(orig_uids).difference(set(new_uids))
        remove_inds = []
        for i, _trace in enumerate(self._traces_data):
            if _trace['uid'] in remove_uids:
                remove_inds.append(i)

                # Unparent trace object to be removed
                self.traces[i].parent = None

        # Compute trace data list after removal
        traces_data_post_removal = [t for t in self._traces_data]
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
        self._traces_data = [_trace for i, _trace in sorted(zip(new_inds, traces_data_post_removal))]

        self._traces = new_traces

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

    @staticmethod
    def _normalize_restyle_data(restyle_data: dict):
        """
        E.g.

        {'a.foo.bar': 3, 'a.foo.baz': ['hello!', 'world!']} ->
            {'a': {'foo': {'bar': [3], 'baz': ['hello!', 'world!']}}}

        Parameters
        ----------
        restyle_data :

        Returns
        -------

        """
        res = {}
        to_merge = []
        for k, v in restyle_data.items():
            assert isinstance(k, str)

            if not isinstance(v, list):
                v = [v]

            # Check for keys with periods
            #  e.g. marker.color.
            outer_name, *rest_names_list = k.split('.')
            if rest_names_list:
                k2 = outer_name
                v2 = {'.'.join(rest_names_list): v}
            else:
                k2 = k
                # Make sure v2 is a list
                if isinstance(v, list):
                    v2 = v
                else:
                    v2 = [v]

            if isinstance(v2, dict):
                v3 = BaseFigureWidget._normalize_restyle_data(v2)
                to_merge.append({k2: v3})
            else:
                res[k2] = v2

        # Merge dictionary properties
        for d in to_merge:
            BaseFigureWidget._merge_restyle_data(res, d)

        return res

    @staticmethod
    def _merge_restyle_data(to_data, from_data, path=None):
        if path is None:
            path = []

        for k in from_data:
            if k in to_data:
                if isinstance(to_data[k], dict) and isinstance(from_data[k], dict):
                    BaseFigureWidget._merge_restyle_data(to_data[k], from_data[k], path + [k])
                elif to_data[k] == from_data[k]:
                    pass  # Same values at leaf
                else:
                    raise ValueError('Style dictionaries conflict at {path}'.format(path=path + [k]))
            else:
                to_data[k] = from_data[k]

        return to_data

    def restyle(self, style, trace_indexes=None):
        if trace_indexes is None:
            trace_indexes = list(range(len(self.traces)))

        if not isinstance(trace_indexes, (list, tuple)):
            trace_indexes = [trace_indexes]

        style2 = BaseFigureWidget._normalize_restyle_data(style)
        restyle_msg = self._perform_restyle(style2, trace_indexes)
        if restyle_msg:
            self._send_restyle_msg(restyle_msg, trace_indexes=trace_indexes)

    def _perform_restyle(self, style, trace_indexes, path=None):
        """ This should perform the restyle but it won't trigger
        Need to return a restyle message"""
        if path is None:
            path = []

        restyle_msgs = []
        for k, v in style.items():
            if isinstance(v, dict):
                msg = self._perform_restyle(v, trace_indexes, path + [k])
                restyle_msgs.append(msg)
            else:
                restyle_msg_vs = []
                any_vals_changed = False
                for i, trace_ind in enumerate(trace_indexes):
                    trace_data = self._traces_data[trace_ind]
                    for path_el in path:
                        trace_data = trace_data[path_el]
                    trace_v = v[i % len(v)]
                    restyle_msg_vs.append(trace_v)

                    if k not in trace_data or trace_data[k] != trace_v:
                        trace_data[k] = trace_v
                        any_vals_changed = True

                if any_vals_changed:
                    # At lease on of the values for one of the traces has changed. Update them all
                    restyle_msgs.append({'.'.join(path + [k]): restyle_msg_vs})

        restyle_data = {}
        for restyle_msg in restyle_msgs:
            self._merge_restyle_data(restyle_data, restyle_msg)

        return restyle_data

    def _send_restyle_msg(self, style, trace_indexes=None):
        if not isinstance(trace_indexes, (list, tuple)):
            trace_indexes = [trace_indexes]

        restype_msg = (style, trace_indexes)
        # print('Restyle: {msg}'.format(msg=restype_msg))
        self._plotly_restyle = restype_msg
        self._plotly_restyle = None

    def _restyle_child(self, child, prop, val):

        send_val = [val]

        trace_index = self.traces.index(child)

        # # Hack to see if this triggers sync to frontend
        # tmp = [e for e in self._traces_data]
        # self._traces_data = []
        # self._traces_data = tmp

        self._send_restyle_msg({prop: send_val}, trace_indexes=trace_index)

    def _add_trace(self, trace):

        # Add UID if not set
        if not trace._data.get('uid', None):
            trace._data['uid'] = str(uuid.uuid1())

        # Update python side
        self._traces_data = self._traces_data + [trace._data]
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
