import collections
import uuid
import re

import ipywidgets as widgets
from traitlets import List, Unicode, Dict, Tuple, default, observe

@widgets.register
class BaseFigureWidget(widgets.DOMWidget):

    # Traits
    # ------
    _view_name = Unicode('FigureView').tag(sync=True)
    _view_module = Unicode('ipyplotly').tag(sync=True)
    _model_name = Unicode('FigureModel').tag(sync=True)
    _model_module = Unicode('ipyplotly').tag(sync=True)

    # Data properties for front end
    _layout_data = Dict()  # .tag(sync=True)
    _traces_data = List().tag(sync=True)

    # Python -> JS message properties
    _plotly_addTraces = List(trait=Dict(),
                             allow_none=True).tag(sync=True)

    _plotly_restyle = List(allow_none=True).tag(sync=True)
    _plotly_relayout = Dict(allow_none=True).tag(sync=True)

    _plotly_deleteTraces = List(allow_none=True).tag(sync=True)
    _plotly_moveTraces = List(allow_none=True).tag(sync=True)

    # JS -> Python message properties
    _plotly_restyleDelta = List(allow_none=True).tag(sync=True)
    _plotly_relayoutDelta = Dict(allow_none=True).tag(sync=True)
    _plotly_restylePython = List(allow_none=True).tag(sync=True)
    _plotly_relayoutPython = Dict(allow_none=True).tag(sync=True)

    # Constructor
    # -----------
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        # Initialize backing property for trace objects
        self._traces = ()
        self._layout = None

        from ipyplotly.datatypes import Layout
        self._layout = Layout()
        self._layout.parent = self
        self._layout_data = self._layout._data

    # ### Trait methods ###
    @default('_plotly_addTraces')
    def _plotly_addTraces_default(self):
        return None

    @default('_plotly_restyle')
    def _plotly_restyle_default(self):
        return None

    @observe('_plotly_restyleDelta')
    def handler_plotly_restyleDelta(self, change):
        deltas = change['new']
        if not deltas:
            return

        # print('addTraceDeltas msg: {deltas}'.format(deltas=deltas))
        for delta in deltas:
            uid = delta['uid']
            uid_traces = [trace for trace in self.traces if trace._data.get('uid', None) == uid]
            assert len(uid_traces) == 1
            uid_trace = uid_traces[0]
            BaseFigureWidget.apply_dict_delta(uid_trace._data, delta)

        # Remove processed trace delta data
        self._plotly_restyleDelta = None

    @observe('_plotly_restylePython')
    def handler_plotly_restylePython(self, change):
        restyle_msg = change['new']
        if not restyle_msg:
            return

        restyle_data = restyle_msg[0]
        # print('delta restyle: {restyle_data}'.format(restyle_data=restyle_data))
        if len(restyle_msg) > 1 and restyle_msg[1] is not None:
            trace_inds = restyle_msg[1]
        else:
            trace_inds = None

        self.restyle(restyle_data, trace_inds)

    # Traces
    # ------
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

    def restyle(self, style, trace_indexes=None):
        if trace_indexes is None:
            trace_indexes = list(range(len(self.traces)))

        if not isinstance(trace_indexes, (list, tuple)):
            trace_indexes = [trace_indexes]

        restyle_msg = self._perform_restyle(style, trace_indexes)
        if restyle_msg:
            self._send_restyle_msg(restyle_msg, trace_indexes=trace_indexes)

    def _perform_restyle(self, style, trace_indexes):
        # Make sure trace_indexes is an array
        if not isinstance(trace_indexes, list):
            trace_indexes = [trace_indexes]

        restyle_data = {}  # Resytyle data to send to JS side as Plotly.restylePlot()

        for raw_key, v in style.items():
            # kstr may have periods. e.g. foo.bar
            key_path = self._str_to_dict_path(raw_key)

            if not isinstance(v, list):
                v = [v]

            if isinstance(v, dict):
                raise ValueError('Restyling objects not supported, only individual properties\n'
                                 '    Received: {{k}: {v}}'.format(k=raw_key, v=v))
            else:
                restyle_msg_vs = []
                any_vals_changed = False
                for i, trace_ind in enumerate(trace_indexes):
                    if trace_ind >= len(self._traces_data):
                        raise ValueError('Trace index {trace_ind} out of range'.format(trace_ind=trace_ind))
                    trace_data = self._traces_data[trace_ind]
                    for key_path_el in key_path[:-1]:
                        trace_data = trace_data[key_path_el]

                    last_key = key_path[-1]

                    trace_v = v[i % len(v)]

                    restyle_msg_vs.append(trace_v)

                    if last_key not in trace_data or trace_data[last_key] != trace_v:
                        trace_data[last_key] = trace_v
                        any_vals_changed = True

                if any_vals_changed:
                    # At lease on of the values for one of the traces has changed. Update them all
                    restyle_data[raw_key] = restyle_msg_vs

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

    # Layout
    # ------
    @observe('_plotly_relayoutDelta')
    def handler_plotly_relayoutDelta(self, change):
        delta = change['new']

        if not delta:
            return

        # print('relayoutDelta msg: {deltas}'.format(deltas=delta))
        BaseFigureWidget.apply_dict_delta(self.layout._data, delta)

        # Remove processed trace delta data
        self._plotly_relayoutDelta = None

    @property
    def layout(self):
        return self._layout

    @layout.setter
    def layout(self, new_layout):
        # TODO: validate layout
        self._layout_data = new_layout._data

        # Unparent current layout
        if self._layout:
            self._layout.parent = None

        # Parent new layout
        new_layout.parent = self
        self._layout = new_layout

    def _relayout_child(self, child, prop, val):
        send_val = val  # Don't wrap in a list for relayout
        self._send_relayout_msg({prop: send_val})

    def _send_relayout_msg(self, layout):
        # print('relayout: {layout}'.format(layout=layout))
        self._plotly_relayout = layout
        self._plotly_relayout = None

    @observe('_plotly_relayoutPython')
    def handler_plotly_relayoutPython(self, change):
        relayout_data = change['new']
        if not relayout_data:
            return

        self.relayout(relayout_data)

    def relayout(self, relayout_data):
        relayout_msg = self._perform_relayout(relayout_data)
        if relayout_msg:
            self._send_relayout_msg(relayout_msg)

    def _perform_relayout(self, relayout_data):
        relayout_msg = {}  # relayout data to send to JS side as Plotly.relayout()

        for raw_key, v in relayout_data.items():
            # kstr may have periods. e.g. foo.bar
            key_path = self._str_to_dict_path(raw_key)

            val_parent = self._layout_data
            for key_path_el in key_path[:-1]:
                val_parent = val_parent[key_path_el]

            last_key = key_path[-1]
            # print(f'{key_path}, {last_key}, {v}')
            if last_key not in val_parent or val_parent[last_key] != v:
                val_parent[last_key] = v
                relayout_msg[raw_key] = v

        return relayout_msg

    @staticmethod
    def _str_to_dict_path(raw_key):

        # Split string on periods. e.g. 'foo.bar[0]' -> ['foo', 'bar[0]']
        key_path = raw_key.split('.')

        # Split out bracket indexes. e.g. ['foo', 'bar[0]'] -> ['foo', 'bar', '0']
        bracket_re = re.compile('(.*)\[(\d+)\]')
        key_path2 = []
        for key in key_path:
            match = bracket_re.fullmatch(key)
            if match:
                key_path2.extend(match.groups())
            else:
                key_path2.append(key)

        # Convert elements to ints if possible. e.g. e.g. ['foo', 'bar', '0'] -> ['foo', 'bar', 0]
        for i in range(len(key_path2)):
            try:
                key_path2[i] = int(key_path2[i])
            except ValueError as _:
                pass

        return key_path2

    # Static helpers
    # --------------
    @staticmethod
    def _is_object_list(v):
        return isinstance(v, list) and len(v) > 0 and isinstance(v[0], dict)

    @staticmethod
    def apply_dict_delta(trace_data, delta_data):

        if isinstance(trace_data, dict):
            assert isinstance(delta_data, dict)

            for p, delta_val in delta_data.items():
                if p not in trace_data:
                    continue

                trace_val = trace_data[p]
                if isinstance(delta_val, dict) or BaseFigureWidget._is_object_list(delta_val):
                    BaseFigureWidget.apply_dict_delta(trace_val, delta_val)
                else:
                    trace_data[p] = delta_val
        elif isinstance(trace_data, list):
            assert isinstance(delta_data, list)

            for i, delta_val in enumerate(delta_data):
                trace_val = trace_data[i]
                if isinstance(delta_val, dict) or BaseFigureWidget._is_object_list(delta_val):
                    BaseFigureWidget.apply_dict_delta(trace_val, delta_val)
                else:
                    trace_data[i] = delta_val


class BasePlotlyType:
    def __init__(self, type_name):
        self.type_name = type_name
        self._data = {}
        self._validators = {}
        self.parent = None

    def _set_prop(self, prop, val):
        validator = self._validators.get(prop)
        val = validator.validate_coerce(val)

        if prop not in self._data or self._data[prop] != val:
            self._data[prop] = val
            self._send_update(prop, val)

    def _set_compound_prop(self, prop, val, curr_val):
        validator = self._validators.get(prop)
        val = validator.validate_coerce(val)

        # Reparent
        val.parent = self
        dict_val = val._data
        if curr_val is not None and curr_val is not val:
            curr_val.parent = None

        # Update data dict
        if prop not in self._data or self._data[prop] != dict_val:
            self._data[prop] = dict_val
            self._send_update(prop, dict_val)

        return val

    def _set_array_prop(self, prop, val, curr_val):
        validator = self._validators.get(prop)
        val = validator.validate_coerce(val)  # type: tuple

        # Reparent
        if curr_val:
            for cv in curr_val:
                cv.parent = None

        for v in val:
            v.parent = self

        # Update data dict
        dict_val = [v._data for v in val]
        if prop not in self._data or self._data[prop] != dict_val:
            self._data[prop] = dict_val
            self._send_update(prop, dict_val)

        return val

    def _send_update(self, prop, val):
        raise NotImplementedError()

    def _update_child(self, child, prop, val):
        child_prop_val = getattr(self, child.type_name)
        if isinstance(child_prop_val, (list, tuple)):
            child_ind = child_prop_val.index(child)
            obj_path = '{child_name}.{child_ind}.{prop}'.format(
                child_name=child.type_name,
                child_ind=child_ind,
                prop=prop)
        else:
            obj_path = '{child_name}.{prop}'.format(child_name=child.type_name, prop=prop)

        self._send_update(obj_path, val)

    def _restyle_child(self, child, prop, val):
        self._update_child(child, prop, val)

    def _relayout_child(self, child, prop, val):
        self._update_child(child, prop, val)


class BaseTraceType(BasePlotlyType):

    def __init__(self, type_name):
        super().__init__(type_name)

    def _send_update(self, prop, val):
        if self.parent:
            self.parent._restyle_child(self, prop, val)


class BaseLayoutType(BasePlotlyType):

    # _send_relayout analogous to _send_restyle above
    def __init__(self, type_name):
        super().__init__(type_name)

    def _send_update(self, prop, val):
        if self.parent:
            self.parent._relayout_child(self, prop, val)
