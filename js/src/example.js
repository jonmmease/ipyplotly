var widgets = require('@jupyter-widgets/base');
var _ = require('underscore');
var Plotly = require('plotly.js');


// Models
// ======
var FigureModel = widgets.DOMWidgetModel.extend({

    defaults: _.extend(widgets.DOMWidgetModel.prototype.defaults(), {
        _model_name: 'FigureModel',
        _view_name: 'FigureView',
        _model_module: 'ipyplotly',
        _view_module: 'ipyplotly',

        _traces_data: [],
        _layout_data: {}, // Not synced to python side

        // Message properties
        _py2js_addTraces: null,
        _py2js_deleteTraces: null,
        _py2js_moveTraces: null,
        _py2js_restyle: null,
        _py2js_relayout: null,

        _py2js_removeLayoutProps: null,
        _py2js_removeStyleProps: null,

        // JS -> Python
        _js2py_restyle: null,
        _js2py_relayout: null,
        _js2py_layoutDelta: null,
        _js2py_tracesDelta: null,

        // callbacks
        _js2py_pointsCallback: null
    }),

    initialize: function() {
        FigureModel.__super__.initialize.apply(this, arguments);
        console.log('FigureModel: initialize');

        this.on("change:_py2js_restyle", this.do_restyle, this);
        this.on("change:_py2js_relayout", this.do_relayout, this);
        this.on("change:_py2js_removeLayoutProps", this.do_removeLayoutProps, this);
        this.on("change:_py2js_removeStyleProps", this.do_removeStyleProps, this);
    },

    _str_to_dict_path: function (rawKey) {

        // Split string on periods. e.g. 'foo.bar[0]' -> ['foo', 'bar[0]']
        var keyPath = rawKey.split('.');
        var regex = /(.*)\[(\d+)\]/;

        // Split out bracket indexes. e.g. ['foo', 'bar[0]'] -> ['foo', 'bar', '0']
        var keyPath2 = [];
        for (var k = 0; k < keyPath.length; k++) {
            var key = keyPath[k];
            var match = regex.exec(key);
            if (match === null) {
                keyPath2.push(key);
            } else {
                keyPath2.push(match[1]);
                keyPath2.push(match[2]);
            }
        }

        // Convert elements to ints if possible. e.g. e.g. ['foo', 'bar', '0'] -> ['foo', 'bar', 0]
        for (k = 0; k < keyPath2.length; k++) {
            key = keyPath2[k];
            var potentialInt = parseInt(key);
            if (!isNaN(potentialInt)) {
                keyPath2[k] = potentialInt;
            }
        }
        return keyPath2
    },

    normalize_trace_indexes: function (trace_indexes, num_traces) {
        if (trace_indexes === null || trace_indexes === undefined) {
            trace_indexes = Array.apply(null, new Array(num_traces)).map(function (_, i) {return i;});
        }
        if (!Array.isArray(trace_indexes)) {
            // Make sure idx is an array
            trace_indexes = [trace_indexes];
        }
        return trace_indexes
    },

    do_restyle: function () {
        console.log('FigureModel: do_restyle');
        var data = this.get('_py2js_restyle');
        if (data !== null) {
            var style = data[0];
            var trace_indexes = this.normalize_trace_indexes(data[1]);
            this._performRestyle(style, trace_indexes)
        }
    },

    _performRestyle: function (style, trace_indexes){

        for (var rawKey in style) {
            if (!style.hasOwnProperty(rawKey)) { continue }
            var v = style[rawKey];

            if (!Array.isArray(v)) {
                v = [v]
            }

            var keyPath = this._str_to_dict_path(rawKey);

            for (var i = 0; i < trace_indexes.length; i++) {
                var trace_ind = trace_indexes[i];
                var valParent = this.get('_traces_data')[trace_ind];

                for (var kp = 0; kp < keyPath.length-1; kp++) {
                    var keyPathEl = keyPath[kp];

                    // Extend val_parent list if needed
                    if (Array.isArray(valParent)) {
                        if (typeof keyPathEl === 'number') {
                            while (valParent.length <= keyPathEl) {
                                valParent.push(null)
                            }
                        }
                    } else { // object
                        // Initialize child if needed
                        if (valParent[keyPathEl] === undefined) {
                            if (typeof keyPath[kp + 1] === 'number') {
                                valParent[keyPathEl] = []
                            } else {
                                valParent[keyPathEl] = {}
                            }
                        }
                    }
                    valParent = valParent[keyPathEl];
                }

                var lastKey = keyPath[keyPath.length-1];
                var trace_v = v[i % v.length];

                if (trace_v === null || trace_v === undefined){
                    if(valParent.hasOwnProperty(lastKey)) {
                        delete valParent[lastKey];
                    }
                } else {
                    if (Array.isArray(valParent) && typeof lastKey === 'number') {
                        while (valParent.length <= lastKey) {
                            // Make sure array is long enough to assign into
                            valParent.push(null)
                        }
                    }
                    valParent[lastKey] = trace_v;
                }
            }
        }
    },

    do_relayout: function () {
        console.log('FigureModel: do_relayout');
        var data = this.get('_py2js_relayout');
        if (data !== null) {
            console.log(data);
            this._performRelayout(data);
            console.log(this.get('_layout_data'))
        }
    },

    _performRelayout: function (relayout_data) {
        for (var rawKey in relayout_data) {
            if (!relayout_data.hasOwnProperty(rawKey)) {
                continue
            }

            var v = relayout_data[rawKey];
            var keyPath = this._str_to_dict_path(rawKey);

            var valParent = this.get('_layout_data');

            for (var kp = 0; kp < keyPath.length-1; kp++) {
                var keyPathEl = keyPath[kp];

                // Extend val_parent list if needed
                if (Array.isArray(valParent)) {
                    if(typeof keyPathEl === 'number') {
                        while (valParent.length <= keyPathEl) {
                            valParent.push(null)
                        }
                    }
                } else {
                    // Initialize child if needed
                    if (valParent[keyPathEl] === undefined) {
                        if (typeof keyPath[kp + 1] === 'number') {
                            valParent[keyPathEl] = []
                        } else {
                            valParent[keyPathEl] = {}
                        }
                    }
                }
                valParent = valParent[keyPathEl];
            }

            var lastKey = keyPath[keyPath.length-1];

            if (v === null || v === undefined){
                if(valParent.hasOwnProperty(lastKey)) {
                    delete valParent[lastKey];
                }
            } else {
                if (Array.isArray(valParent) && typeof lastKey === 'number') {
                    while (valParent.length <= lastKey) {
                        // Make sure array is long enough to assign into
                        valParent.push(null)
                    }
                }
                valParent[lastKey] = v;
            }
        }
    },

    do_removeLayoutProps: function () {
        console.log('FigureModel:do_removeLayoutProps');
        var data = this.get('_py2js_removeLayoutProps');
        if (data !== null) {
            console.log(this.get('_layout_data'));
            for(var i=0; i < data.length; i++) {

                var keyPath = data[i];
                var valParent = this.get('_layout_data');

                for (var kp = 0; kp < keyPath.length - 1; kp++) {
                    var keyPathEl = keyPath[kp];
                    if (valParent[keyPathEl] === undefined) {
                        valParent = null;
                        break
                    }
                    valParent = valParent[keyPathEl];
                }
                if (valParent !== null) {
                    var lastKey = keyPath[keyPath.length - 1];
                    if (valParent.hasOwnProperty(lastKey)) {
                        delete valParent[lastKey];
                        console.log('Removed ' + keyPath)
                    }
                }
            }
            console.log(this.get('_layout_data'));
        }
    },

    do_removeStyleProps: function () {
        console.log('FigureModel:do_removeStyleProps');
        var data = this.get('_py2js_removeStyleProps');
        if (data !== null) {
            var keyPaths = data[0];
            var trace_indexes = this.normalize_trace_indexes(data[1]);

            for(var k=0; k < keyPaths.length; k++) {

                var keyPath = keyPaths[k];

                for (var i = 0; i < trace_indexes.length; i++) {
                    var trace_ind = trace_indexes[i];
                    var valParent = this.get('_traces_data')[trace_ind];

                    for (var kp = 0; kp < keyPath.length - 1; kp++) {
                        var keyPathEl = keyPath[kp];
                        if (valParent[keyPathEl] === undefined) {
                            valParent = null;
                            break
                        }
                        valParent = valParent[keyPathEl];
                    }
                    if (valParent !== null) {
                        var lastKey = keyPath[keyPath.length - 1];
                        if (valParent.hasOwnProperty(lastKey)) {
                            delete valParent[lastKey];
                            console.log('Removed ' + keyPath)
                        }
                    }
                }
            }
        }
    }
});


// Figure View
// ===========
var FigureView = widgets.DOMWidgetView.extend({

    render: function() {

        // Initialize empty figure
        console.log('render');
        console.log(this.model.get('_traces_data'));
        console.log(this.model.get('_layout_data'));

        // Clone traces and layout so plotly instances in the views don't mutate the model
        var initial_traces = JSON.parse(JSON.stringify(this.model.get('_traces_data')));
        var initial_layout = JSON.parse(JSON.stringify(this.model.get('_layout_data')));
        Plotly.plot(this.el, initial_traces, initial_layout);

        // Update layout
        var relayoutDelta = this.create_delta_object(this.model.get('_layout_data'), this.el._fullLayout);
        this.model.set('_js2py_layoutDelta', relayoutDelta);

        // Update traces
        // Loop over new traces
        var traceDeltas = new Array(initial_traces.length);
        for(var i=0; i < initial_traces.length; i++) {
            var fullTraceData = this.el._fullData[i];
            var traceData = initial_traces[i];
            traceDeltas[i] = this.create_delta_object(traceData, fullTraceData);
        }

        console.log(traceDeltas);
        this.model.set('_js2py_styleDelta', traceDeltas);

        // Python -> JS event properties
        this.model.on('change:_py2js_addTraces', this.do_addTraces, this);
        this.model.on('change:_py2js_deleteTraces', this.do_deleteTraces, this);
        this.model.on('change:_py2js_moveTraces', this.do_moveTraces, this);
        this.model.on('change:_py2js_restyle', this.do_restyle, this);
        this.model.on("change:_py2js_relayout", this.do_relayout, this);

        this.model.on('change:_traces_data', function () {
            console.log('change:_traces_data');
            console.log(this.model.get('_traces_data'));
        }, this);

        // Plotly events
        var that = this;
        this.el.on('plotly_restyle', function(update) {that.handle_plotly_restyle(update)});
        this.el.on('plotly_relayout', function(update) {that.handle_plotly_relayout(update)});
        this.el.on('plotly_click', function(update) {that.handle_plotly_click(update)});
        this.el.on('plotly_hover', function(update) {that.handle_plotly_hover(update)});
        this.el.on('plotly_unhover', function(update) {that.handle_plotly_unhover(update)});
        this.el.on('plotly_selected', function(update) {that.handle_plotly_selected(update)});
        this.el.on('plotly_doubleclick', function(update) {that.handle_plotly_doubleclick(update)});
        this.el.on('plotly_afterplot', function(update) {that.handle_plotly_afterplot(update)});

        // sync any/all changes back to model
        this.touch();
    },

    buildPointsObject: function (data) {

        var pointsObject;
        if (data.hasOwnProperty('points')) {
            // Most cartesian plots
            var pointObjects = data['points'];
            var numPoints = pointObjects.length;
            pointsObject = {
                'curveNumbers': new Array(numPoints),
                'pointNumbers': new Array(numPoints),
                'xs': new Array(numPoints),
                'ys': new Array(numPoints)};


                for (var p = 0; p < numPoints; p++) {
                pointsObject['curveNumbers'][p] = pointObjects[p]['curveNumber'];
                pointsObject['pointNumbers'][p] = pointObjects[p]['pointNumber'];
                pointsObject['xs'][p] = pointObjects[p]['x'];
                pointsObject['ys'][p] = pointObjects[p]['y'];
            }

            // Add z if present
            var hasZ = pointObjects[0].hasOwnProperty('z');
            if (hasZ) {
                pointsObject['zs'] = new Array(numPoints);
                for (p = 0; p < numPoints; p++) {
                    pointsObject['zs'][p] = pointObjects[p]['z'];
                }
            }

            return pointsObject
        } else {
            return null
        }
    },

    buildMouseEventObject: function (data) {
        var event = data['event'];
        if (event === undefined) {
            return {}
        } else {
            var mouseEventObject = {
                // Keyboard modifiers
                'alt': event['altKey'],
                'ctrl': event['ctrlKey'],
                'meta': event['metaKey'],
                'shift': event['shiftKey'],

                // Mouse buttons
                'button': event['button'],
                // Indicates which button was pressed on the mouse to trigger the event.
                //   0: Main button pressed, usually the left button or the un-initialized state
                //   1: Auxiliary button pressed, usually the wheel button or the middle button (if present)
                //   2: Secondary button pressed, usually the right button
                //   3: Fourth button, typically the Browser Back button
                //   4: Fifth button, typically the Browser Forward button
                'buttons': event['buttons']
                // Indicates which buttons are pressed on the mouse when the event is triggered.
                //   0  : No button or un-initialized
                //   1  : Primary button (usually left)
                //   2  : Secondary button (usually right)
                //   4  : Auxilary button (usually middle or mouse wheel button)
                //   8  : 4th button (typically the "Browser Back" button)
                //   16 : 5th button (typically the "Browser Forward" button)
            };
            return mouseEventObject
        }
    },

    buildSelectorObject: function(data) {
        var selectorObject = {};

        // Test for box select
        if (data.hasOwnProperty('range')) {
            selectorObject['type'] = 'box';
            selectorObject['xrange'] = data['range']['x'];
            selectorObject['yrange'] = data['range']['y'];
        } else if (data.hasOwnProperty('lassoPoints')) {
            selectorObject['type'] = 'lasso';
            selectorObject['xs'] = data['lassoPoints']['x'];
            selectorObject['ys'] = data['lassoPoints']['y'];
        }
        return selectorObject
    },

    handle_plotly_restyle: function (data) {
        if (data !== null && data !== undefined && data[0].hasOwnProperty('_doNotReportToPy')) {
            // Restyle originated on the Python side
            return
        }

        // Work around some plotly bugs/limitations
        if (data === null || data === undefined) {

            data = new Array(this.el.data.length);

            for (var t = 0; t < this.el.data.length; t++) {
                var traceData = this.el.data[t];
                data[t] = {'uid': traceData['uid']};
                if (traceData['type'] === 'parcoords') {

                    // Parallel coordinate diagram 'constraintrange' property not provided
                    for (var d = 0; d < traceData.dimensions.length; d++) {
                        var constraintrange = traceData.dimensions[d]['constraintrange'];
                        if (constraintrange !== undefined) {
                            data[t]['dimensions[' + d + '].constraintrange'] = [constraintrange];
                        }
                    }
                }
            }
        }

        console.log("plotly_restyle");
        console.log(data);

        this.model.set('_js2py_restyle', data);
        this.touch();
    },

    handle_plotly_relayout: function (data) {
        if (data !== null && data !== undefined && data.hasOwnProperty('_doNotReportToPy')) {
            // Relayout originated on the Python side
            return
        }

        console.log("plotly_relayout");
        console.log(data);

        // Work around some plotly bugs/limitations

        // Sometimes (in scatterGL at least) axis range isn't wrapped in range
        if ('xaxis' in data && Array.isArray(data['xaxis'])) {
            data['xaxis'] = {'range': data['xaxis']}
        }

        if ('yaxis' in data && Array.isArray(data['yaxis'])) {
            data['yaxis'] = {'range': data['yaxis']}
        }

        this.model.set('_js2py_relayout', data);
        this.touch();
    },

    handle_plotly_click: function (data) {
        console.log("plotly_click");

        if (data === null || data === undefined) return;

        var pyData = {
            'event_type': 'plotly_click',
            'points': this.buildPointsObject(data),
            'state': this.buildMouseEventObject(data)
        };

        if (pyData['points'] !== null) {
            console.log(data);
            console.log(pyData);
            this.model.set('_js2py_pointsCallback', pyData);
            this.touch();
        }
    },

    handle_plotly_hover: function (data) {
        console.log("plotly_hover");

        if (data === null || data === undefined) return;

        var pyData = {
            'event_type': 'plotly_hover',
            'points': this.buildPointsObject(data),
            'state': this.buildMouseEventObject(data)
        };

        if (pyData['points'] !== null && pyData['points'] !== undefined) {
            console.log(data);
            console.log(pyData);
            this.model.set('_js2py_pointsCallback', pyData);
            this.touch();
        }
    },

    handle_plotly_unhover: function (data) {
        console.log("plotly_unhover");

        if (data === null || data === undefined) return;

        var pyData = {
            'event_type': 'plotly_unhover',
            'points': this.buildPointsObject(data),
            'state': this.buildMouseEventObject(data)
        };

        if (pyData['points'] !== null) {
            console.log(data);
            console.log(pyData);
            this.model.set('_js2py_pointsCallback', pyData);
            this.touch();
        }
    },

    handle_plotly_selected: function (data) {
        console.log("plotly_selected");

        if (data === null ||
            data === undefined ||
            data['points'].length === 0) return;

        var pyData = {
            'event_type': 'plotly_selected',
            'points': this.buildPointsObject(data),
            'selector': this.buildSelectorObject(data),
        };

        if (pyData['points'] !== null) {
            console.log(data);
            console.log(pyData);
            this.model.set('_js2py_pointsCallback', pyData);
            this.touch();
        }
    },

    handle_plotly_doubleclick: function (data) {
        console.log("plotly_doubleclick");
        console.log(data);
    },

    handle_plotly_afterplot: function (data) {
        console.log("plotly_afterplot");
        console.log(data);
    },

    do_addTraces: function () {
        // add trace to plot

        var data = this.model.get('_py2js_addTraces');
        console.log('do_addTraces');

        if (data !== null) {
            var prev_num_traces = this.el._fullData.length;
            // console.log(data);
            Plotly.addTraces(this.el, data);
            // console.log(this.el._fullData);

            // Loop over new traces
            var traceDeltas = new Array(data.length);
            var tracesData = this.model.get('_traces_data');
            for(var i=0; i < data.length; i++) {
                var fullTraceData = this.el._fullData[i + prev_num_traces];
                var traceData = tracesData[i + prev_num_traces];
                traceDeltas[i] = this.create_delta_object(traceData, fullTraceData);
            }

            this.model.set('_js2py_styleDelta', traceDeltas);


            // Update layout
            var layoutDelta = this.create_delta_object(this.model.get('_layout_data'), this.el._fullLayout);
            this.model.set('_js2py_layoutDelta', layoutDelta);

            this.touch();
        }
    },

    do_deleteTraces: function () {
        var delete_inds = this.model.get('_py2js_deleteTraces');
        console.log('do_deleteTraces');
        if (delete_inds !== null){
            console.log(delete_inds);
            Plotly.deleteTraces(this.el, delete_inds);

            // Update layout
            var relayoutDelta = this.create_delta_object(this.model.get('_layout_data'), this.el._fullLayout);
            this.model.set('_js2py_layoutDelta', relayoutDelta);
            this.touch();
        }
    },

    do_moveTraces: function () {
        var move_data = this.model.get('_py2js_moveTraces');
        console.log('do_moveTraces');

        if (move_data !== null){
            var current_inds = move_data[0];
            var new_inds = move_data[1];

            var inds_equal = current_inds.length===new_inds.length &&
                current_inds.every(function(v,i) { return v === new_inds[i]});

            if (!inds_equal) {
                console.log(current_inds + "->" + new_inds);
                Plotly.moveTraces(this.el, current_inds, new_inds);
            }
        }
    },

    do_restyle: function () {
        console.log('do_restyle');
        var data = this.model.get('_py2js_restyle');
        if (data !== null) {
            var style = data[0];
            var idx = data[1];

            if (idx === null || idx === undefined) {
                idx = Array.apply(null, Array(this.el.data.length)).map(function (_, i) {return i;});
            }
            if (!Array.isArray(idx)) {
                // Make sure idx is an array
                idx = [idx];
            }

            style['_doNotReportToPy'] = true;
            Plotly.restyle(this.el, style, idx);

            // Send back style delta
            var traceDeltas = new Array(idx.length);
            var trace_data = this.model.get('_traces_data');
            for (var i = 0; i < idx.length; i++) {
                traceDeltas[i] = this.create_delta_object(trace_data[idx[i]], this.el._fullData[idx[i]]);
                console.log(traceDeltas[i]);
                console.log(trace_data[idx[i]]);
            }


            this.model.set('_js2py_styleDelta', traceDeltas);

            // Send back layout delta
            var relayoutDelta = this.create_delta_object(this.model.get('_layout_data'), this.el._fullLayout);
            this.model.set('_js2py_layoutDelta', relayoutDelta);

            this.touch();
        }
    },

    do_relayout: function () {
        console.log('FigureView: do_relayout');
        var data = this.model.get('_py2js_relayout');
        if (data !== null) {

            data['_doNotReportToPy'] = true;
            Plotly.relayout(this.el, data);

            var layoutDelta = this.create_delta_object(this.model.get('_layout_data'), this.el._fullLayout);
            console.log(layoutDelta);
            console.log(this.model.get('_layout_data'));
            this.model.set('_js2py_layoutDelta', layoutDelta);

            this.touch();
        }
    },

    clone_fullLayout_data: function (fullLayout) {
        var fullStr = JSON.stringify(fullLayout, function(k, v) {
            if (k.length > 0 && k[0] === '_') {
                return undefined
            }
            return v
        });
        return JSON.parse(fullStr)
    },

    clone_fullData_metadata: function (fullData) {
        var fullStr = JSON.stringify(fullData, function(k, v) {
            if (k.length > 0 && k[0] === '_') {
                return undefined
            } else if (Array.isArray(v)) {
                // For performance, we don't clone arrays
                return undefined
            }
            return v
        });
        return JSON.parse(fullStr)
    },

    create_delta_object: function(data, fullData) {
        var res = {};
        if (data === null || data === undefined) {
            data = {};
        }
        for (var p in fullData) {
            if (p[0] !== '_' && fullData.hasOwnProperty(p) && fullData[p] !== null) {

                var props_equal;
                if (data.hasOwnProperty(p) && Array.isArray(data[p]) && Array.isArray(fullData[p])) {
                    props_equal = JSON.stringify(data[p]) === JSON.stringify(fullData[p]);
                } else if (data.hasOwnProperty(p)) {
                    props_equal = data[p] === fullData[p];
                } else {
                    props_equal = false;
                }

                if (!props_equal || p === 'uid') {  // Let uids through
                    // property has non-null value in fullData that doesn't match the value in
                    var full_val = fullData[p];
                    if (data.hasOwnProperty(p) && typeof full_val === 'object') {
                        if(Array.isArray(full_val)) {
                            res[p] = new Array(full_val.length);
                            for (var i = 0; i < full_val.length; i++) {
                                if (!Array.isArray(data[p]) || data[p].length <= i) {
                                    res[p][i] = full_val[i]
                                } else {
                                    res[p][i] = this.create_delta_object(data[p][i], full_val[i]);
                                }
                            }
                        } else { // object
                            var full_obj = this.create_delta_object(data[p], full_val);
                            if (Object.keys(full_obj).length > 0) {
                                // new object is not empty
                                res[p] = full_obj;
                            }
                        }
                    } else if (typeof full_val === 'object' && !Array.isArray(full_val)) {
                        res[p] = this.create_delta_object({}, full_val);

                    } else if (full_val !== undefined) {
                        res[p] = full_val;
                    }
                }
            }
        }
        return res
    }
});


module.exports = {
    FigureView : FigureView,
    FigureModel: FigureModel,
};
