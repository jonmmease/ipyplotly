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
        _plotly_restyle: null
    })
});


// Figure View
// ===========
var FigureView = widgets.DOMWidgetView.extend({

    render: function() {

        // Initialize empty figure
        Plotly.plot(this.el, this.model.get('_traces'), this.model.get('_layout'));

        this.model.on('change:_plotly_addTraces', this.do_addTraces, this);
        this.model.on('change:_plotly_restyle', this.do_restyle, this);
    },

    do_addTraces: function () {
        // add trace to plot

        var data = this.model.get('_plotly_addTraces');
        if (data !== null) {
            Plotly.addTraces(this.el, data);

            // this.model.set('_plotly_addTraces', null);
            // this.model.save_changes();
        }
    },

    do_restyle: function () {
        var data = this.model.get('_plotly_restyle');
        if (data !== null) {
            var style = data[0];
            var idx = data[1];
            if (idx !== null) {
                Plotly.restyle(this.el, style, idx)
            } else {
                Plotly.restyle(this.el, style)
            }

            // this.model.set('_plotly_restyle', null);
            // this.model.save_changes();
        }
    },
});


module.exports = {
    FigureView : FigureView,
    FigureModel: FigureModel,
};
