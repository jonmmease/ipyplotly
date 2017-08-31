var widgets = require('@jupyter-widgets/base');
var _ = require('underscore');
var Plotly = require('plotly.js');


// Custom Model. Custom widgets models must at least provide default values
// for model attributes, including
//
//  - `_view_name`
//  - `_view_module`
//  - `_view_module_version`
//
//  - `_model_name`
//  - `_model_module`
//  - `_model_module_version`
//
//  when different from the base class.

// When serialiazing the entire widget state for embedding, only values that
// differ from the defaults will be specified.
var HelloModel = widgets.DOMWidgetModel.extend({
    defaults: _.extend(widgets.DOMWidgetModel.prototype.defaults(), {
        _model_name : 'HelloModel',
        _view_name : 'HelloView',
        _model_module : 'ipyplotly',
        _view_module : 'ipyplotly',
        _model_module_version : '0.1.0',
        _view_module_version : '0.1.0',
        value : 'Hello World',
        count : 0
    })
});


// Custom View. Renders the widget model.
var HelloView = widgets.DOMWidgetView.extend({
    render: function() {
        this.value_changed();
        this.model.on('change:value', this.value_changed, this);
        this.model.on('change:count', this.value_changed, this);
    },

    value_changed: function() {
        this.el.textContent = this.model.get('value') + ': (' + this.model.get('count') + ')';
    }
});


var MyWidgetView = widgets.DOMWidgetView.extend({
    render: function() {
        MyWidgetView.__super__.render.apply(this, arguments);

        // Callbacks
        this.model.on('change:color', this._color_changed, this);

        // Install event handlers
        Plotly.plot( this.el, [{
                     x: [1, 2, 3, 4, 5],
                     y: [1, 2, 4, 8, 16] }], {
                     margin: { t: 0 } } );

        // Init color
        this._color_changed();

        this._install_event_handlers();
    },
    _install_event_handlers: function() {
        that = this
        this.el.on('plotly_click', function(event_data){
            console.log('plotly_click');
            console.log(event_data);
        });
        this.el.on('plotly_hover', function(event_data){
            console.log('plotly_hover');
            console.log(event_data);
        });
        this.el.on('plotly_selected', function(event_data){
            console.log('plotly_selected');
            console.log(event_data)
        });
        this.el.on('plotly_restyle', function(event_data){
            console.log('plotly_restyle');
            console.log(event_data);
            that.model.set({'plotly_data_str': JSON.stringify(that.el.data)});
            that.model.save_changes();
        });
        this.el.on('plotly_relayout', function(event_data){
            console.log('plotly_relayout');
            console.log(event_data);
            that.model.set({'plotly_layout_str': JSON.stringify(that.el.layout)});
            that.model.save_changes();
        });
    },
    _color_changed: function() {
        var new_color = this.model.get('color');
        var update = {
            // 'marker.color': new_color
            'marker': {'color': new_color}
        };
        Plotly.restyle(this.el, update);
    }
});

// Custom View. Renders the widget model.
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

        // var traceProps = _.pickBy(model.attributes, function(v, k) {return !k.startsWith('_')});
        // Plotly.addTraces(this.el, traceProps);

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


var ScatterView = widgets.WidgetView.extend({
    // Anything to add here?
    render: function() {
        console.log('ScatterView.render')
    }
});

var FigureModel = widgets.WidgetModel.extend({
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
    }, widgets.WidgetModel.serializers)
});

module.exports = {
    HelloModel : HelloModel,
    HelloView : HelloView,
    MyWidgetView: MyWidgetView,
    FigureView : FigureView,
    FigureModel: FigureModel,
    ScatterView: ScatterView
};
