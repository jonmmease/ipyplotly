import collections
import datetime
import re
import typing as typ
import uuid
from copy import deepcopy
from pprint import pprint

import ipywidgets as widgets
from traitlets import List, Unicode, Dict, default, observe, Integer, Bool

from ipyplotly.callbacks import Points, BoxSelector, LassoSelector, InputState
from ipyplotly.validators.layout import XaxisValidator, YaxisValidator, GeoValidator, TernaryValidator, SceneValidator

from selenium import webdriver
from plotly.offline import plot as plotlypy_plot
from PIL import Image, ImageOps
import io
import tempfile
import os
import pathlib

# TODO:
# Callbacks
# ---------
# - Add base class for traces
# - Trace point callbacks
#    - on_hover, on_unhover, on_click, on_select,
#    - on_reconstrain for parcoords
#
# - Figure (or Layout) level callbacks
#    - on_panzoom (pan/zoom)
#    - on_doubleclick ()
#    - on_plotly_afterplot
#
# - Property callbacks (every plotly datatype)
#   - on_change('property', listener())
#   Triggering these could be tricky for events that originate on JS side
#



@widgets.register
class BaseFigureWidget(widgets.DOMWidget):

    # Traits
    # ------
    _view_name = Unicode('FigureView').tag(sync=True)
    _view_module = Unicode('ipyplotly').tag(sync=True)
    _model_name = Unicode('FigureModel').tag(sync=True)
    _model_module = Unicode('ipyplotly').tag(sync=True)

    # Data properties for front end
    # Note: These are only automatically synced on full assignment, not on mutation
    _layout_data = Dict().tag(sync=True)
    _traces_data = List().tag(sync=True)

    # Python -> JS message properties
    _py2js_addTraces = List(trait=Dict(),
                            allow_none=True).tag(sync=True)

    _py2js_restyle = List(allow_none=True).tag(sync=True)
    _py2js_relayout = Dict(allow_none=True).tag(sync=True)

    _py2js_deleteTraces = Dict(allow_none=True).tag(sync=True)
    _py2js_moveTraces = List(allow_none=True).tag(sync=True)

    _py2js_removeLayoutProps = List(allow_none=True).tag(sync=True)
    _py2js_removeStyleProps = List(allow_none=True).tag(sync=True)

    # JS -> Python message properties
    _js2py_styleDelta = List(allow_none=True).tag(sync=True)
    _js2py_layoutDelta = Dict(allow_none=True).tag(sync=True)
    _js2py_restyle = List(allow_none=True).tag(sync=True)
    _js2py_relayout = Dict(allow_none=True).tag(sync=True)

    # For plotly_select/hover/unhover/click
    _js2py_pointsCallback = Dict(allow_none=True).tag(sync=True)

    # Message tracking
    _last_relayout_msg_id = Integer(0).tag(sync=True)
    _last_restyle_msg_id = Integer(0).tag(sync=True)

    # Constructor
    # -----------
    def __init__(self, traces=None, layout=None, loop=None, **kwargs):
        super().__init__(**kwargs)

        # Traces
        # ------
        from ipyplotly.validators import TracesValidator
        self._traces_validator = TracesValidator()

        if traces is None:
            self._traces = ()  # type: typ.Tuple[BaseTraceHierarchyType]
            self._traces_deltas = []
        else:
            traces = self._traces_validator.validate_coerce(traces)

            self._traces = traces
            self._traces_deltas = [{} for trace in traces]
            self._traces_data = [deepcopy(trace._data) for trace in traces]
            for trace in traces:
                trace._orphan_data.clear()
                trace._parent = self

        # Layout
        # ------
        from ipyplotly.validators import LayoutValidator
        self._layout_validator = LayoutValidator()

        from ipyplotly.datatypes import Layout

        if layout is None:
            layout = Layout()  # type: Layout
        else:
            layout = self._layout_validator.validate_coerce(layout)

        self._layout = layout
        self._layout_data = deepcopy(self._layout._data)
        self._layout._parent = self
        self._layout_delta = {}

        # Process messagas
        self._relayout_in_process = False
        self._waiting_relayout_callbacks = []

        self._restyle_in_process = False
        self._waiting_restyle_callbacks = []

        self._view_count = 0

    # ### Trait methods ###
    @observe('_js2py_styleDelta')
    def handler_plotly_styleDelta(self, change):
        deltas = change['new']
        self._js2py_styleDelta = None

        if not deltas:
            return

        msg_id = deltas[0].get('_restyle_msg_id', None)
        # print(f'styleDelta: {msg_id} == {self._last_restyle_msg_id}')
        if msg_id == self._last_restyle_msg_id:
            for delta in deltas:
                trace_uid = delta['uid']

                # Remove message id
                # pprint(delta)

                # print('Processing styleDelta')
                trace_uids = [trace.uid for trace in self.traces]
                trace_index = trace_uids.index(trace_uid)
                uid_trace = self.traces[trace_index]
                delta_transform = BaseFigureWidget.transform_data(uid_trace._delta, delta)

                removed_props = self.remove_overlapping_props(uid_trace._data, uid_trace._delta)

                if removed_props:
                    # print(f'Removed_props: {removed_props}')
                    self._py2js_removeStyleProps = [removed_props, trace_index]
                    self._py2js_removeStyleProps = None

                # print(delta_transform)
                self._dispatch_change_callbacks_restyle(delta_transform, [trace_index])

            self._restyle_in_process = False
            while self._waiting_restyle_callbacks:
                # Call callbacks
                self._waiting_restyle_callbacks.pop()()

    @observe('_js2py_restyle')
    def handler_plotly_restylePython(self, change):
        restyle_msg = change['new']
        self._js2py_restyle = None

        if not restyle_msg:
            return

        restyle_data = restyle_msg[0]
        # print('Restyle (JS->Py):')
        # pprint(restyle_data)

        if len(restyle_msg) > 1 and restyle_msg[1] is not None:
            trace_inds = restyle_msg[1]
            if not isinstance(trace_inds, (list, tuple)):
                trace_inds = [trace_inds]
        else:
            trace_inds = list(range(len(self.traces)))

        self.restyle(restyle_data, trace_inds)
        self._js2py_restyle = None

    # Traces
    # ------
    @property
    def traces(self) -> typ.Tuple['BaseTraceType']:
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
        delete_inds = []
        for i, _trace in enumerate(self._traces_data):
            if _trace['uid'] in remove_uids:
                delete_inds.append(i)

                # Unparent trace object to be removed
                old_trace = self.traces[i]
                old_trace._orphan_data.update(deepcopy(self.traces[i]._data))
                old_trace._parent = None

        # Compute trace data list after removal
        traces_data_post_removal = [t for t in self._traces_data]
        traces_deltas_post_removal = [t for t in self._traces_deltas]
        for i in reversed(delete_inds):
            del traces_data_post_removal[i]
            del traces_deltas_post_removal[i]

        if delete_inds:
            relayout_msg_id = self._last_relayout_msg_id + 1
            self._last_relayout_msg_id = relayout_msg_id
            self._relayout_in_process = True

            self._py2js_deleteTraces = {'delete_inds': delete_inds,
                                        '_relayout_msg_id ': relayout_msg_id}
            self._py2js_deleteTraces = None

        # Compute move traces
        new_inds = []

        for uid in [t['uid'] for t in traces_data_post_removal]:
            new_inds.append(new_uids.index(uid))

        current_inds = list(range(len(traces_data_post_removal)))

        if not all([i1 == i2 for i1, i2 in zip(new_inds, current_inds)]):
            self._py2js_moveTraces = [current_inds, new_inds]

        # Update _traces order
        self._traces_data = [_trace for i, _trace in sorted(zip(new_inds, traces_data_post_removal))]
        self._traces_deltas = [_trace for i, _trace in sorted(zip(new_inds, traces_deltas_post_removal))]

        self._traces = new_traces

    def restyle(self, style, trace_indexes=None):
        if trace_indexes is None:
            trace_indexes = list(range(len(self.traces)))

        if not isinstance(trace_indexes, (list, tuple)):
            trace_indexes = [trace_indexes]

        restyle_msg = self._perform_restyle(style, trace_indexes)
        if restyle_msg:
            self._dispatch_change_callbacks_restyle(restyle_msg, trace_indexes)
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
                    val_parent = self._traces_data[trace_ind]
                    for kp, key_path_el in enumerate(key_path[:-1]):

                        # Extend val_parent list if needed
                        if isinstance(val_parent, list) and isinstance(key_path_el, int):
                            while len(val_parent) <= key_path_el:
                                val_parent.append(None)

                        elif isinstance(val_parent, dict) and key_path_el not in val_parent:
                            if isinstance(key_path[kp + 1], int):
                                val_parent[key_path_el] = []
                            else:
                                val_parent[key_path_el] = {}

                        val_parent = val_parent[key_path_el]

                    last_key = key_path[-1]

                    trace_v = v[i % len(v)]

                    restyle_msg_vs.append(trace_v)

                    if trace_v is None:
                        if isinstance(val_parent, dict) and last_key in val_parent:
                            val_parent.pop(last_key)
                            any_vals_changed = True
                    elif isinstance(val_parent, dict):
                        if last_key not in val_parent or val_parent[last_key] != trace_v:
                            val_parent[last_key] = trace_v
                            any_vals_changed = True

                if any_vals_changed:
                    # At lease one of the values for one of the traces has changed. Update them all
                    restyle_data[raw_key] = restyle_msg_vs

        return restyle_data

    def _dispatch_change_callbacks_restyle(self, style, trace_indexes):
        if not isinstance(trace_indexes, list):
            trace_indexes = [trace_indexes]

        dispatch_plan = {t: {} for t in trace_indexes}
        # e.g. {0: {(): {'obj': layout,
        #            'changed_paths': [('xaxis', 'range')]}}}

        for raw_key, v in style.items():
            key_path = self._str_to_dict_path(raw_key)

            # Test whether we should remove trailing integer in path
            # e.g. ('xaxis', 'range', '1') -> ('xaxis', 'range')
            # We only do this if the trailing index is an integer that references a primitive value
            if isinstance(key_path[-1], int) and not isinstance(v, dict):
                key_path = key_path[:-1]

            for trace_ind in trace_indexes:

                parent_obj = self.traces[trace_ind]
                key_path_so_far = ()
                keys_left = key_path

                # Iterate down the key path
                for next_key in key_path:
                    if isinstance(parent_obj, BasePlotlyType):
                        if key_path_so_far not in dispatch_plan[trace_ind]:
                            dispatch_plan[trace_ind][key_path_so_far] = {'obj': parent_obj, 'changed_paths': set()}

                        dispatch_plan[trace_ind][key_path_so_far]['changed_paths'].add(keys_left)

                        next_val = parent_obj.__getitem__(next_key)
                    elif isinstance(parent_obj, (list, tuple)):
                        next_val = parent_obj[next_key]
                    else:
                        break

                    key_path_so_far = key_path_so_far + (next_key,)
                    keys_left = keys_left[1:]
                    parent_obj = next_val

        # pprint(dispatch_plan)
        for trace_ind in trace_indexes:
            for p in dispatch_plan[trace_ind].values():
                obj = p['obj']
                changed_paths = p['changed_paths']
                obj._dispatch_change_callbacks(changed_paths)

    def _send_restyle_msg(self, style, trace_indexes=None):
        if not isinstance(trace_indexes, (list, tuple)):
            trace_indexes = [trace_indexes]

        # Add and update message ids
        relayout_msg_id = self._last_relayout_msg_id + 1
        style['_relayout_msg_id'] = relayout_msg_id
        self._last_relayout_msg_id = relayout_msg_id
        self._relayout_in_process = True

        restyle_msg_id = self._last_restyle_msg_id + 1
        style['_restyle_msg_id'] = restyle_msg_id
        self._last_restyle_msg_id = restyle_msg_id
        self._restyle_in_process = True

        restype_msg = (style, trace_indexes)
        # print('Restyle (Py->JS)')
        # pprint(restype_msg)

        self._py2js_restyle = restype_msg
        self._py2js_restyle = None

    def _restyle_child(self, child, prop, val):

        send_val = [val]
        trace_index = self.traces.index(child)
        restyle = {prop: send_val}

        self._dispatch_change_callbacks_restyle(restyle, trace_index)
        self._send_restyle_msg(restyle, trace_indexes=trace_index)

    def add_traces(self, traces: typ.List['BaseTraceHierarchyType']):

        if not isinstance(traces, (list, tuple)):
            traces = [traces]

        # Validate
        traces = self._traces_validator.validate_coerce(traces)

        # Make deep copy of trace data (Optimize later if needed)
        new_traces_data = [deepcopy(trace._data) for trace in traces]

        # Update trace parent
        for trace in traces:
            trace._parent = self
            trace._orphan_data.clear()

        # Update python side
        self._traces_data = self._traces_data + new_traces_data
        self._traces_deltas = self._traces_deltas + [{} for trace in traces]
        self._traces = self._traces + traces

        # Update messages
        relayout_msg_id = self._last_relayout_msg_id + 1
        self._last_relayout_msg_id = relayout_msg_id
        self._relayout_in_process = True

        restyle_msg_id = self._last_restyle_msg_id + 1
        self._last_restyle_msg_id = restyle_msg_id
        self._restyle_in_process = True

        for traces_data in new_traces_data:
            traces_data['_relayout_msg_id'] = relayout_msg_id
            traces_data['_restyle_msg_id'] = restyle_msg_id

        # Send to front end
        # print(f'addTraces: {traces_data}')
        add_traces_msg = new_traces_data
        self._py2js_addTraces = add_traces_msg
        self._py2js_addTraces = None

        return traces

    def _get_child_data(self, child):
        try:
            trace_index = self.traces.index(child)
        except ValueError as _:
            trace_index = None

        if trace_index is not None:
            return self._traces_data[trace_index]
        elif child is self.layout:
            return self._layout_data
        else:
            raise ValueError('Unrecognized child: %s' % child)

    def _get_child_delta(self, child):
        try:
            trace_index = self.traces.index(child)
        except ValueError as _:
            trace_index = None

        if trace_index is not None:
            return self._traces_deltas[trace_index]
        elif child is self.layout:
            return self._layout_delta
        else:
            raise ValueError('Unrecognized child: %s' % child)

    def _init_child_data(self, child):
        # layout and traces dict are never None
        return

    # Layout
    # ------
    @observe('_js2py_layoutDelta')
    def handler_plotly_layoutDelta(self, change):
        delta = change['new']
        self._js2py_layoutDelta = None

        if not delta:
            return

        msg_id = delta.get('_relayout_msg_id')
        print(f'layoutDelta: {msg_id} == {self._last_relayout_msg_id}')
        if msg_id == self._last_relayout_msg_id:
            # print('Processing layoutDelta')
            # print('layoutDelta: {deltas}'.format(deltas=delta))
            delta_transform = self.transform_data(self._layout_delta, delta)
            # print(f'delta_transform: {delta_transform}')

            # No relayout messages in process. Handle removing overlapping properties
            removed_props = self.remove_overlapping_props(self._layout_data, self._layout_delta)
            if removed_props:
                # print(f'Removed_props: {removed_props}')
                self._py2js_removeLayoutProps = removed_props
                self._py2js_removeLayoutProps = None

            self._dispatch_change_callbacks_relayout(delta_transform)
            self._relayout_in_process = False
            print('gets here at ' + datetime.datetime.now().strftime("%H:%M:%S"))
            while self._waiting_relayout_callbacks:
                # Call callbacks
                self._waiting_relayout_callbacks.pop()()

    @property
    def layout(self):
        return self._layout

    @layout.setter
    def layout(self, new_layout):
        # Validate layout
        new_layout = self._layout_validator.validate_coerce(new_layout)
        new_layout_data = deepcopy(new_layout._data)

        # Unparent current layout
        if self._layout:
            old_layout_data = deepcopy(self._layout._data)
            self._layout._orphan_data.update(old_layout_data)
            self._layout._parent = None

        # Parent new layout
        self._layout_data = new_layout_data
        new_layout._parent = self
        self._layout = new_layout

        # Notify JS side
        self._send_relayout_msg(new_layout_data)

    def _relayout_child(self, child, prop, val):
        send_val = val  # Don't wrap in a list for relayout
        relayout_msg = {prop: send_val}

        self._dispatch_change_callbacks_relayout(relayout_msg)
        self._send_relayout_msg(relayout_msg)

    def _send_relayout_msg(self, layout):
        # print('Relayout (Py->JS): {layout}'.format(layout=layout))


        msg_id = self._last_relayout_msg_id + 1
        layout['_relayout_msg_id'] = msg_id
        self._last_relayout_msg_id = msg_id

        self._py2js_relayout = layout
        self._py2js_relayout = None

    @observe('_js2py_relayout')
    def handler_plotly_relayoutPython(self, change):
        relayout_data = change['new']
        self._js2py_relayout = None

        if not relayout_data:
            return

        if 'lastInputTime' in relayout_data:
            # Remove 'lastInputTime'. Seems to be an internal plotly property that is introduced for some plot types
            relayout_data.pop('lastInputTime')

        self.relayout(relayout_data)


    def relayout(self, relayout_data):
        # print(f'Relayout: {relayout_data}')
        relayout_msg = self._perform_relayout(relayout_data)
        if relayout_msg:

            self._dispatch_change_callbacks_relayout(relayout_msg)
            self._send_relayout_msg(relayout_msg)

    def _perform_relayout(self, relayout_data):
        relayout_msg = {}  # relayout data to send to JS side as Plotly.relayout()

        # Update layout_data
        # print('_perform_relayout')
        for raw_key, v in relayout_data.items():
            # kstr may have periods. e.g. foo.bar
            key_path = self._str_to_dict_path(raw_key)

            val_parent = self._layout_data
            for kp, key_path_el in enumerate(key_path[:-1]):
                if key_path_el not in val_parent:

                    # Extend val_parent list if needed
                    if isinstance(val_parent, list) and isinstance(key_path_el, int):
                        while len(val_parent) <= key_path_el:
                            val_parent.append(None)

                    elif isinstance(val_parent, dict) and key_path_el not in val_parent:
                        if isinstance(key_path[kp+1], int):
                            val_parent[key_path_el] = []
                        else:
                            val_parent[key_path_el] = {}

                val_parent = val_parent[key_path_el]

            last_key = key_path[-1]
            # print(f'{val_parent}, {key_path}, {last_key}, {v}')

            if v is None:
                if isinstance(val_parent, dict) and last_key in val_parent:
                    val_parent.pop(last_key)
                    relayout_msg[raw_key] = None
            else:
                if isinstance(val_parent, list):
                    if isinstance(last_key, int):
                        while(len(val_parent) <= last_key):
                            val_parent.append(None)
                        val_parent[last_key] = v
                        relayout_msg[raw_key] = v
                elif isinstance(val_parent, dict):
                    if last_key not in val_parent or val_parent[last_key] != v:
                        val_parent[last_key] = v
                        relayout_msg[raw_key] = v

        return relayout_msg

    def _dispatch_change_callbacks_relayout(self, relayout_msg):
        dispatch_plan = {}  # e.g. {(): {'obj': layout,
                            #            'changed_paths': [('xaxis', 'range')]}}
        for raw_key, v in relayout_msg.items():
            # kstr may have periods. e.g. foo.bar
            key_path = self._str_to_dict_path(raw_key)

            # Test whether we should remove trailing integer in path
            # e.g. ('xaxis', 'range', '1') -> ('xaxis', 'range')
            # We only do this if the trailing index is an integer that references a primitive value
            if isinstance(key_path[-1], int) and not isinstance(v, dict):
                key_path = key_path[:-1]

            parent_obj = self.layout
            key_path_so_far = ()
            keys_left = key_path

            # Iterate down the key path
            for next_key in key_path:
                if isinstance(parent_obj, BasePlotlyType):
                    if key_path_so_far not in dispatch_plan:
                        dispatch_plan[key_path_so_far] = {'obj': parent_obj, 'changed_paths': set()}
                    dispatch_plan[key_path_so_far]['changed_paths'].add(keys_left)

                    next_val = parent_obj.__getitem__(next_key)
                    # parent_obj._dispatch_change_callbacks(next_key, next_val)
                elif isinstance(parent_obj, (list, tuple)):
                    next_val = parent_obj[next_key]
                else:
                    break

                key_path_so_far = key_path_so_far + (next_key,)
                keys_left = keys_left[1:]
                parent_obj = next_val

        # pprint(dispatch_plan)
        for p in dispatch_plan.values():
            obj = p['obj']
            changed_paths = p['changed_paths']
            obj._dispatch_change_callbacks(changed_paths)

    @staticmethod
    def _str_to_dict_path(raw_key):

        if isinstance(raw_key, tuple):
            # Nothing to do
            return raw_key
        else:
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

            return tuple(key_path2)

    # Callbacks
    # ---------
    @observe('_js2py_pointsCallback')
    def handler_plotly_pointsCallback(self, change):
        callback_data = change['new']
        self._js2py_pointsCallback = None

        if not callback_data:
            return

        # TODO: bail if no callbacks are registered

        # Get event type
        # --------------
        event_type = callback_data['event_type']

        # Build Selector Object
        # ---------------------
        if callback_data.get('selector', None):
            selector_data = callback_data['selector']
            selector_type = selector_data['type']
            if selector_type == 'box':
                selector = BoxSelector(**selector_data)
            elif selector_type == 'lasso':
                selector = LassoSelector(**selector_data)
            else:
                raise ValueError('Unsupported selector type: %s' % selector_type)
        else:
            selector = None

        # Build State Object
        # ------------------
        if callback_data.get('state', None):
            state_data = callback_data['state']
            state = InputState(**state_data)
        else:
            state = None

        # Build Trace Points Dictionary
        # -----------------------------
        points_data = callback_data['points']
        trace_points = {}
        for x, y, point_ind, trace_ind in zip(points_data['xs'],
                                                  points_data['ys'],
                                                  points_data['pointNumbers'],
                                                  points_data['curveNumbers']):
            if trace_ind not in trace_points:
                trace_points[trace_ind] = {'point_inds': [],
                                           'xs': [],
                                           'ys': [],
                                           'trace_name': self._traces[trace_ind].name,
                                           'trace_index': trace_ind}

            trace_dict = trace_points[trace_ind]
            trace_dict['xs'].append(x)
            trace_dict['ys'].append(y)
            trace_dict['point_inds'].append(point_ind)

        # Dispatch callbacks
        # ------------------
        for trace_ind, trace_points_data in trace_points.items():
            points = Points(**trace_points_data)
            trace = self.traces[trace_ind]  # type: BaseTraceType

            if event_type == 'plotly_click':
                trace._dispatch_on_click(points, state)
            elif event_type == 'plotly_hover':
                trace._dispatch_on_hover(points, state)
            elif event_type == 'plotly_unhover':
                trace._dispatch_on_unhover(points, state)
            elif event_type == 'plotly_selected':
                trace._dispatch_on_selected(points, selector)

    def on_relayout_completed(self, fn):
        if self._relayout_in_process:
            self._waiting_relayout_callbacks.append(fn)
        else:
            fn()

    def on_restyle_completed(self, fn):
        if self._restyle_in_process:
            self._waiting_restyle_callbacks.append(fn)
        else:
            fn()

    # Exports
    # -------
    def to_dict(self):
        data = deepcopy(self._traces_data)
        # BaseFigureWidget.transform_data(data, deepcopy(self._traces_deltas), should_remove=False)
        layout = deepcopy(self._layout_data)
        # BaseFigureWidget.transform_data(layout, deepcopy(self._layout_delta), should_remove=False)
        return {'data': data, 'layout': layout}

    def save_html(self, filename, auto_open=False, responsive=False):
        data = self.to_dict()
        if responsive:
            if 'height' in data['layout']:
                data['layout'].pop('height')
            if 'width' in data['layout']:
                data['layout'].pop('width')
        else:
            # Assign width/height explicitly in case these were defaults
            data['layout']['height'] = self.layout.height
            data['layout']['width'] = self.layout.width

        plotlypy_plot(data, filename=filename, show_link=False, auto_open=auto_open, validate=False)

    def save_png(self, filename=None, scale_factor=2, border=20):
        temp_filename = tempfile.mktemp() + '.html'
        opts = webdriver.ChromeOptions()
        opts.add_argument('headless')
        browser = webdriver.Chrome(chrome_options=opts)

        try:
            self.save_html(filename=temp_filename, responsive=False)
            browser.get(pathlib.Path(temp_filename).as_uri())

            # Pixel ratio (2 for retina Macbook)
            pixel_ratio = browser.execute_script("return window.devicePixelRatio")
            browser.execute_script(f'document.body.style.webkitTransform = "scale({scale_factor/pixel_ratio})"')
            browser.execute_script(f'document.body.style.webkitTransformOrigin = "0% 0%"')

            browser.set_window_size((scale_factor / pixel_ratio) * self.layout.width + 16,
                                    (scale_factor / pixel_ratio) * self.layout.height + 16)
            png = browser.get_screenshot_as_png()

            b_rect = browser.execute_script(
                "return document.getElementsByClassName('plot-container')[0].getBoundingClientRect()")

            # Process image
            image = Image.open(io.BytesIO(png))

            crop_rect = tuple([pixel_ratio * b_rect[c] for c in ['left', 'top', 'right', 'bottom']])
            image = image.crop(crop_rect)
            image = ImageOps.expand(image, border=border, fill='white')

            if filename:
                image.save(filename)
                return image
        finally:
            os.remove(temp_filename)
            browser.quit()

    # Static helpers
    # --------------
    @staticmethod
    def _is_object_list(v):
        return isinstance(v, list) and len(v) > 0 and isinstance(v[0], dict)

    @staticmethod
    def remove_overlapping_props(input_data, delta_data, prop_path=()):
        """
        Remove properties in data that are also into delta. Do so recursively.

        Except, never remove uid from input_data

        Parameters
        ----------
        data :
        delta :

        Returns
        -------
        List of removed property path tuples
        """
        removed = []
        if isinstance(input_data, dict):
            assert isinstance(delta_data, dict)

            for p, delta_val in delta_data.items():
                if isinstance(delta_val, dict) or BaseFigureWidget._is_object_list(delta_val):
                    if p in input_data:
                        input_val = input_data[p]
                        removed.extend(
                            BaseFigureWidget.remove_overlapping_props(
                                input_val,
                                delta_val,
                                prop_path + (p,)))
                elif p in input_data and p != 'uid':
                    input_data.pop(p)
                    removed.append(prop_path + (p,))

        elif isinstance(input_data, list):
            assert isinstance(delta_data, list)

            for i, delta_val in enumerate(delta_data):
                if i >= len(input_data):
                    break

                input_val = input_data[i]
                if input_val is not None and isinstance(delta_val, dict) or BaseFigureWidget._is_object_list(delta_val):
                    removed.extend(
                        BaseFigureWidget.remove_overlapping_props(
                            input_val,
                            delta_val,
                            prop_path + (i,)))

        return removed

    @staticmethod
    def transform_data(to_data, from_data, should_remove=True, relayout_path=()):
        """
        Transform to_data into from_data and return relayout style description of transformation

        Parameters
        ----------
        to_data :
        from_data :

        Returns
        -------

        """
        relayout_terms = {}
        if isinstance(to_data, dict):
            if not isinstance(from_data, dict):
                raise ValueError('Mismatched data types: to_data: {to_dict} {from_data}'.format(
                    to_dict=to_data, from_data=from_data))

            # Handle addition / modification of terms
            for from_prop, from_val in from_data.items():
                if isinstance(from_val, dict) or BaseFigureWidget._is_object_list(from_val):
                    if from_prop not in to_data:
                        to_data[from_prop] = {} if isinstance(from_val, dict) else []

                    input_val = to_data[from_prop]
                    relayout_terms.update(
                        BaseFigureWidget.transform_data(
                            input_val,
                            from_val,
                            should_remove=should_remove,
                            relayout_path=relayout_path + (from_prop,)))
                else:
                    if from_prop not in to_data or to_data[from_prop] != from_val:
                        # if from_prop in to_data:
                        #     print(f'to_data[from_prop] != from_val -- {to_data}[{from_prop}] != {from_val}:')
                        to_data[from_prop] = from_val
                        relayout_terms[relayout_path + (from_prop,)] = from_val

            # Handle removal of terms
            if should_remove:
                for remove_prop in set(to_data.keys()).difference(set(from_data.keys())):
                    to_data.pop(remove_prop)

        elif isinstance(to_data, list):
            if not isinstance(from_data, list):
                raise ValueError('Mismatched data types: to_data: {to_data} {from_data}'.format(
                    to_data=to_data, from_data=from_data))

            for i, from_val in enumerate(from_data):
                if i >= len(to_data):
                    to_data.append(None)

                input_val = to_data[i]
                if input_val is not None and isinstance(from_val, dict) or BaseFigureWidget._is_object_list(from_val):
                    relayout_terms.update(
                        BaseFigureWidget.transform_data(
                            input_val,
                            from_val,
                            should_remove=should_remove,
                            relayout_path=relayout_path + (i,)))
                else:
                    if to_data[i] != from_val:
                        to_data[i] = from_val
                        relayout_terms[relayout_path + (i,)] = from_val

        return relayout_terms

class BasePlotlyType:
    def __init__(self, prop_name):
        self._prop_name = prop_name
        # self._data = {}
        self._validators = {}
        self._compound_props = {}
        self._orphan_data = {}  # properties dict for use while object has no parent
        self._parent = None
        self._change_callbacks = {}  # type: typ.Dict[typ.Tuple, typ.Callable]

    @property
    def prop_name(self):
        return self._prop_name

    @property
    def _data(self):
        if self.parent is None:
            # Use orphan data
            return self._orphan_data
        else:
            # Get data from parent's dict
            return self.parent._get_child_data(self)

    def _init_data(self):
        # Ensure that _data is initialized.
        if self._data is not None:
            pass
        else:
            self._parent._init_child_data(self)

    def _init_child_data(self, child):
        self.parent._init_child_data(self)
        self_data = self.parent._get_child_data(self)

        child_or_children = self._compound_props[child.prop_name]
        if child is child_or_children:
            if child.prop_name not in self_data:
                self_data[child.prop_name] = {}
        elif isinstance(child_or_children, (list, tuple)):
            child_ind = child_or_children.index(child)
            if child.prop_name not in self_data:
                # Initialize list
                self_data[child.prop_name] = []

            # Make sure list is long enough for child
            child_list = self_data[child.prop_name]
            while(len(child_list) <= child_ind):
                child_list.append({})

    def _get_child_data(self, child):
        self_data = self.parent._get_child_data(self)
        if self_data is None:
            return None
        else:
            child_or_children = self._compound_props[child.prop_name]
            if child is child_or_children:
                return self_data.get(child.prop_name, None)
            elif isinstance(child_or_children, (list, tuple)):
                child_ind = child_or_children.index(child)
                children_data = self_data.get(child.prop_name, None)
                return children_data[child_ind] \
                    if children_data is not None and len(children_data) > child_ind \
                    else None
            else:
                ValueError('Unexpected child: %s' % child_or_children)

    @property
    def _delta(self):
        if self.parent is None:
            return None
        else:
            return self.parent._get_child_delta(self)

    def _get_child_delta(self, child):
        self_delta = self.parent._get_child_delta(self)
        if self_delta is None:
            return None
        else:
            child_or_children = self._compound_props[child.prop_name]
            if child is child_or_children:
                return self_delta.get(child.prop_name, None)
            elif isinstance(child_or_children, (list, tuple)):
                child_ind = child_or_children.index(child)
                children_data = self_delta.get(child.prop_name, None)
                return children_data[child_ind] if children_data is not None else None
            else:
                ValueError('Unexpected child: %s' % child_or_children)

    @property
    def parent(self):
        return self._parent

    def __getitem__(self, prop):
        if isinstance(prop, tuple):
            res = self
            for p in prop:
                res = res[p]

            return res
        else:
            if prop in self._compound_props:
                return self._compound_props[prop]
            elif self._data is not None and prop in self._data:
                return self._data[prop]
            elif self._delta is not None:
                return self._delta.get(prop, None)
            else:
                # TODO: Only None if this is a valid path. ValueError otherwise
                return None

    def _set_prop(self, prop, val):
        validator = self._validators.get(prop)
        val = validator.validate_coerce(val)

        if val is None:
            # Check if we should send null update
            if self._data and prop in self._data:
                self._data.pop(prop)
                self._send_update(prop, val)
        else:
            self._init_data()
            if prop not in self._data or self._data[prop] != val:
                self._data[prop] = val
                self._send_update(prop, val)

    def _set_compound_prop(self, prop, val):
        # Validate coerce new value
        validator = self._validators.get(prop)
        val = validator.validate_coerce(val)  # type: BasePlotlyType

        # Grab deep copies of current and new states
        curr_val = self._compound_props.get(prop, None)
        if curr_val is not None:
            curr_dict_val = deepcopy(curr_val._data)
        else:
            curr_dict_val = None

        if val is not None:
            new_dict_val = deepcopy(val._data)
        else:
            new_dict_val = None

        # Update data dict
        if not new_dict_val:
            if prop in self._data:
                self._data.pop(prop)
        else:
            self._data[prop] = new_dict_val

        # Send update if there was a change in value
        if curr_dict_val != new_dict_val:
            self._send_update(prop, new_dict_val)

        # Reparent new value and clear orphan data
        val._parent = self
        val._orphan_data.clear()

        # Reparent old value and update orphan data
        if curr_val is not None and curr_val is not val:
            if curr_dict_val is not None:
                curr_val._orphan_data.update(curr_dict_val)
            curr_val._parent = None

        self._compound_props[prop] = val
        return val

    def _set_array_prop(self, prop, val):
        # Validate coerce new value
        validator = self._validators.get(prop)
        val = validator.validate_coerce(val)  # type: tuple

        # Update data dict
        curr_val = self._compound_props.get(prop, None)
        if curr_val is not None:
            curr_dict_vals = [deepcopy(cv._data) for cv in curr_val]
        else:
            curr_dict_vals = None

        if val is not None:
            new_dict_vals = [deepcopy(nv._data) for nv in val]
        else:
            new_dict_vals = None

        # Update data dict
        if not new_dict_vals:
            if prop in self._data:
                self._data.pop(prop)
        else:
            self._data[prop] = new_dict_vals

        # Send update if there was a change in value
        if curr_dict_vals != new_dict_vals:
            self._send_update(prop, new_dict_vals)

        # Reparent new values and clear orphan data
        if val is not None:
            for v in val:
                v._orphan_data.clear()
                v._parent = self

        # Reparent
        if curr_val is not None:
            for cv, cv_dict in zip(curr_val, curr_dict_vals):
                if cv_dict is not None:
                    cv._orphan_data.update(cv_dict)
                cv._parent = None
        self._compound_props[prop] = val
        return val

    def _send_update(self, prop, val):
        raise NotImplementedError()

    def _update_child(self, child, prop, val):
        child_prop_val = getattr(self, child.prop_name)
        if isinstance(child_prop_val, (list, tuple)):
            child_ind = child_prop_val.index(child)
            obj_path = '{child_name}.{child_ind}.{prop}'.format(
                child_name=child.prop_name,
                child_ind=child_ind,
                prop=prop)
        else:
            obj_path = '{child_name}.{prop}'.format(child_name=child.prop_name, prop=prop)

        self._send_update(obj_path, val)

    def _restyle_child(self, child, prop, val):
        self._update_child(child, prop, val)

    def _relayout_child(self, child, prop, val):
        self._update_child(child, prop, val)

    # Callbacks
    # ---------
    def _dispatch_change_callbacks(self, changed_paths):
        # print(f'Change callback: {self.prop_name} - {changed_paths}')
        changed_paths = set(changed_paths)
        # pprint(changed_paths)
        for callback_paths, callback in self._change_callbacks.items():
            # pprint(set(callback_paths))
            common_paths = changed_paths.intersection(set(callback_paths))
            if common_paths:
                # Invoke callback
                callback_args = [self.__getitem__(cb_path) for cb_path in callback_paths]
                callback(self, *callback_args)

    def on_change(self, callback, *args):
        """
        Register callback function to be called with a properties or subproperties of this object are modified

        Parameters
        ----------
        callback : function
            Function that accepts 1 + len(args) parameters. First parameter is this object. Second throug last
            parameters are the values referenced by args
        args : str or tuple(str)
            Property name (for direct properties) or tuple of property names / indices (for sub properties). Callback
            will be invoked whenever ANY of these properties is modified. Furthermore. The callback will only be
            invoked once even if multiple properties are modified during the same restyle operation.

        Returns
        -------

        """

        if len(args) == 0:
            raise ValueError('At least one property/subproperty must be specified')

        # TODO: Validate that args valid properties / subproperties
        validated_args = tuple([a if isinstance(a, tuple) else (a,) for a in args])

        # TODO: add append arg and store list of callbacks
        self._change_callbacks[validated_args] = callback


class BaseLayoutHierarchyType(BasePlotlyType):

    # _send_relayout analogous to _send_restyle above
    def __init__(self, prop_name):
        super().__init__(prop_name)

    def _send_update(self, prop, val):
        if self.parent:
            self.parent._relayout_child(self, prop, val)


class BaseLayoutType(BaseLayoutHierarchyType):
    _subplotid_prop_names = ['xaxis', 'yaxis', 'geo', 'ternary', 'scene']
    _subplotid_validators = {'xaxis': XaxisValidator,
                            'yaxis': YaxisValidator,
                            'geo': GeoValidator,
                            'ternary': TernaryValidator,
                            'scene': SceneValidator}

    _subplotid_prop_re = re.compile('(' + '|'.join(_subplotid_prop_names) + ')(\d+)')

    def __init__(self, prop_name, **kwargs):
        super().__init__(prop_name)
        self._subplotid_props = {}
        for prop, value in kwargs.items():
            self._set_subplotid_prop(prop, value)

    def _set_subplotid_prop(self, prop, value):
        match = self._subplotid_prop_re.fullmatch(prop)
        if match is None:
            raise TypeError('Invalid Layout keyword argument {k}'.format(k=prop))

        subplot_prop = match.group(1)
        suffix_digit = int(match.group(2))
        if suffix_digit in [0, 1]:
            raise TypeError('Subplot properties may only be suffixed by an integer > 1\n'
                            'Received {k}'.format(k=prop))

        # Add validator
        if prop not in self._validators:
            validator = self._subplotid_validators[subplot_prop](prop_name=prop)
            self._validators[prop] = validator

        # Import value
        self._subplotid_props[prop] = self._set_compound_prop(prop, value)

    def __getattr__(self, item):
        # Check for subplot access (e.g. xaxis2)
        # Validate then call self._get_prop(item)
        if item in self._subplotid_props:
            return self._subplotid_props[item]

        raise AttributeError("'Layout' object has no attribute '{item}'".format(item=item))

    def __setattr__(self, prop, value):
        # Check for subplot assignment (e.g. xaxis2)
        # Call _set_compound_prop with the xaxis validator
        match = self._subplotid_prop_re.fullmatch(prop)
        if match is None:
            # Try setting as ordinary property
            super().__setattr__(prop, value)
        else:
            self._set_subplotid_prop(prop, value)

    def __dir__(self):
        # Include any active subplot values (xaxis2 etc.)
        return super().__dir__() + list(self._subplotid_props.keys())


class BaseTraceHierarchyType(BasePlotlyType):

    def __init__(self, prop_name):
        super().__init__(prop_name)

    def _send_update(self, prop, val):
        if self.parent:
            self.parent._restyle_child(self, prop, val)


class BaseTraceType(BaseTraceHierarchyType):
    def __init__(self, prop_name):
        super().__init__(prop_name)

        self._hover_callbacks = []
        self._unhover_callbacks = []
        self._click_callbacks = []
        self._select_callbacks = []

    # uid
    # ---
    @property
    def uid(self) -> str:
        raise NotImplementedError

    @uid.setter
    def uid(self, val):
        raise NotImplementedError

    # Hover
    # -----
    def on_hover(self,
                 callback: typ.Callable[['BaseTraceType', Points, InputState], None],
                 append=False):
        """
        Register callback to be called when the user hovers over a point from this trace

        Parameters
        ----------
        callback
            Callable that accepts 3 arguments

            - This trace
            - Points object
            - InputState object

        append :

        Returns
        -------
        None
        """
        if not append:
            self._hover_callbacks.clear()

        if callback:
            self._hover_callbacks.append(callback)

    def _dispatch_on_hover(self, points: Points, state: InputState):
        for callback in self._hover_callbacks:
            callback(self, points, state)

    # Unhover
    # -------
    def on_unhover(self, callback: typ.Callable[['BaseTraceType', Points, InputState], None], append=False):
        if not append:
            self._unhover_callbacks.clear()

        if callback:
            self._unhover_callbacks.append(callback)

    def _dispatch_on_unhover(self, points: Points, state: InputState):
        for callback in self._unhover_callbacks:
            callback(self, points, state)

    # Click
    # -----
    def on_click(self, callback: typ.Callable[['BaseTraceType', Points, InputState], None], append=False):
        if not append:
            self._click_callbacks.clear()
        if callback:
            self._click_callbacks.append(callback)

    def _dispatch_on_click(self, points: Points, state: InputState):
        for callback in self._click_callbacks:
            callback(self, points, state)

    # Select
    # ------
    def on_selected(self,
                    callback: typ.Callable[['BaseTraceType', Points, typ.Union[BoxSelector, LassoSelector]], None],
                    append=False):
        if not append:
            self._select_callbacks.clear()

        if callback:
            self._select_callbacks.append(callback)

    def _dispatch_on_selected(self, points: Points, selector: typ.Union[BoxSelector, LassoSelector]):
        for callback in self._select_callbacks:
            callback(self, points, selector)
