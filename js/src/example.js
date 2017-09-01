var widgets = require('@jupyter-widgets/base');
var _ = require('underscore');
var Plotly = require('plotly.js');


// Figure View
// ===========
var FigureView = widgets.DOMWidgetView.extend({
    render: function() {

        // Initialize empty figure
        Plotly.plot(this.el, [], {});

        this.trace_views = new widgets.ViewList(this.add_trace, this.remove_trace, this);
        this.trace_views.update(this.model.get("traces"));

        that = this;
        Promise.all(this.trace_views.views).then(function(views) {
            // TODO: logic to update all views (order, etc.)
            // Plotly.addTraces(that.el, {y: [2,1,2]});
            // Plotly.deleteTraces(that.el, 0);
            // Plotly.moveTraces(that.el);
        });

        this.model.on('change:traces', this.change_traces, this);
    },
    change_traces: function () {
        this.trace_views.update(this.model.get('traces'));
    },
    add_trace: function (model) {
        // add trace to plot
        console.log('add trace');
        console.log(model);

        Plotly.addTraces(this.el, {
            x: model.get('x'),
            y: model.get('y'),
            type: model.get('type'),
            opacity: model.get('opacity')
        });
    },
    remove_trace: function (model) {
        // remove trace from plot
        Plotly.deleteTraces(this.el, 0)
    }
});

// Models
// ======
var FigureModel = widgets.DOMWidgetModel.extend({
    defaults: _.extend(widgets.DOMWidgetModel.prototype.defaults(), {
        _model_name: 'FigureModel',
        _view_name: 'FigureView',
        _model_module: 'ipyplotly',
        _view_module: 'ipyplotly',
        traces: []
    })
}, {
    serializers: _.extend({
        traces: { deserialize: widgets.unpack_models },
    }, widgets.DOMWidgetModel.serializers)
});

// Widget Models don't need views but I need some way for them to report
// changes up to the figure
var ScatterModel = widgets.WidgetModel.extend({
    defaults: _.extend(widgets.WidgetModel.prototype.defaults(), {
        _model_name: 'ScatterModel',
        _model_module: 'ipyplotly',

        opacity: 1.0,
        x: [],
        y: [],
        type: 'scatter'
    })
});

module.exports = {
    FigureView : FigureView,
    FigureModel: FigureModel,
    ScatterModel: ScatterModel
};
