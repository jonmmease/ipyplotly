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

        _traces: [],
        _layout: {},

        // Message properties
        _plotly_addTraces: null,
        _plotly_restyle: null,
        _plotly_addTraceDeltas: []
    })
});


// Figure View
// ===========
var FigureView = widgets.DOMWidgetView.extend({

    render: function() {

        // Initialize empty figure
        console.log('render');

        // Clone traces and layout so plotly instances in the views don't mutate the model
        var initial_traces = JSON.parse(JSON.stringify(this.model.get('_traces')));
        var initial_layout = JSON.parse(JSON.stringify(this.model.get('_layout')));
        Plotly.plot(this.el, initial_traces, initial_layout);
        console.log(this.el._fullData);

        this.model.on('change:_plotly_addTraces', this.do_addTraces, this);
        this.model.on('change:_plotly_restyle', this.do_restyle, this);

        // Plotly events
        this.el.on('plotly_restyle', this.handle_restyle, this);
    },

    handle_restyle: function (update, inds) {
        console.log("plotly_restyle");
        console.log(update);
        console.log(inds);
    },

    do_addTraces: function () {
        // add trace to plot

        var data = this.model.get('_plotly_addTraces');
        console.log('do_addTraces');

        if (data !== null) {
            var prev_num_traces = this.el._fullData.length;
            console.log(data);
            Plotly.addTraces(this.el, data);
            console.log(this.el._fullData);

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

    do_restyle: function () {
        console.log('do_restyle');
        var data = this.model.get('_plotly_restyle');
        if (data !== null) {
            var style = data[0];
            var idx = data[1];
            if (idx !== null) {
                Plotly.restyle(this.el, style, idx);
            } else {
                Plotly.restyle(this.el, style);
            }
        }
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
