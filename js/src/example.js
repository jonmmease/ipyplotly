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
        _layout_data: {},

        // Message properties
        _plotly_addTraces: null,
        _plotly_deleteTraces: null,
        _plotly_moveTraces: null,
        _plotly_restyle: null,

        // JS -> Python
        _plotly_addTraceDeltas: [],
        _plotly_restylePython: []
    })
});


// Figure View
// ===========
var FigureView = widgets.DOMWidgetView.extend({

    render: function() {

        // Initialize empty figure
        console.log('render');

        // Clone traces and layout so plotly instances in the views don't mutate the model
        var initial_traces = JSON.parse(JSON.stringify(this.model.get('_traces_data')));
        var initial_layout = JSON.parse(JSON.stringify(this.model.get('_layout_data')));
        Plotly.plot(this.el, initial_traces, initial_layout);

        // Plotly.plot(this.el, this.model.get('_traces_data'), this.model.get('_layout_data'));
        console.log(this.el._fullData);

        // Python -> JS event properties
        this.model.on('change:_plotly_addTraces', this.do_addTraces, this);
        this.model.on('change:_plotly_deleteTraces', this.do_deleteTraces, this);
        this.model.on('change:_plotly_moveTraces', this.do_moveTraces, this);
        this.model.on('change:_plotly_restyle', this.do_restyle, this);

        // Plotly events
        var that = this;
        this.el.on('plotly_restyle', function(update, inds) {that.handle_restyle(update, inds)});
    },

    handle_restyle: function (data) {
        console.log("plotly_restyle");
        console.log(data);
        this.model.set('_plotly_restylePython', data);
        this.touch();
    },

    do_addTraces: function () {
        // add trace to plot

        var data = this.model.get('_plotly_addTraces');
        console.log('do_addTraces');

        if (data !== null) {
            var prev_num_traces = this.el._fullData.length;
            // console.log(data);
            Plotly.addTraces(this.el, data);
            // console.log(this.el._fullData);

            // Loop over new traces
            var traceDeltas = new Array(data.length);
            for(var i=0; i < data.length; i++) {
                var fullTraceData = this.el._fullData[i + prev_num_traces];
                var traceData = data[i];
                traceDeltas[i] = this.create_delta_object(traceData, fullTraceData);
            }

            this.model.set('_plotly_addTraceDeltas', traceDeltas);
            this.touch();
        }
    },

    do_deleteTraces: function () {
        var delete_inds = this.model.get('_plotly_deleteTraces');
        console.log('do_deleteTraces');
        if (delete_inds !== null){
            console.log(delete_inds);
            Plotly.deleteTraces(this.el, delete_inds)
        }
    },

    do_moveTraces: function () {
        var move_data = this.model.get('_plotly_moveTraces');
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
        var data = this.model.get('_plotly_restyle');
        if (data !== null) {
            var style = data[0];
            var idx = data[1];

            if (idx === null || idx === undefined) {
                idx = Array.apply(null, Array(self.el.data.length)).map(function (_, i) {return i;});
            }
            if (!Array.isArray(idx)) {
                // Make sure idx is an array
                idx = [idx];
            }

            var fullDataPres = Array(idx.length);
            for (var i = 0; i < idx.length; i++) {
                fullDataPres[i] = this.clone_fullData_metadata(this.el._fullData[idx[i]]);
            }

            Plotly.restyle(this.el, style, idx);

            var traceDeltas = Array(idx.length);
            for (i = 0; i < idx.length; i++) {
                traceDeltas[i] = this.create_delta_object(fullDataPres[i], this.el._fullData[idx[i]]);
            }

            this.model.set('_plotly_addTraceDeltas', traceDeltas);
            this.touch();
        }
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
        for (var p in data) {
            if (data.hasOwnProperty(p) && p in fullData && fullData[p] !== null)
                if (data[p] !== fullData[p] || p === 'uid') {  // Let uids through
                    // property has non-null value in fullData that doesn't match the value in
                    var full_val = fullData[p];
                    if (typeof full_val === 'object') {
                        var full_obj = this.create_delta_object(data[p], full_val);
                        if (Object.keys(full_obj).length > 0) {
                            // new object is not empty
                            res[p] = full_obj;
                        }
                    } else {
                        res[p] = full_val;
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
