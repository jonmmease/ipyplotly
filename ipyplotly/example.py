import ipywidgets as widgets
from traitlets import Unicode, Int, List, Dict


@widgets.register
class HelloWorld(widgets.DOMWidget):
    """"""
    _view_name = Unicode('HelloView').tag(sync=True)
    _model_name = Unicode('HelloModel').tag(sync=True)
    _view_module = Unicode('ipyplotly').tag(sync=True)
    _model_module = Unicode('ipyplotly').tag(sync=True)
    _view_module_version = Unicode('^0.1.0').tag(sync=True)
    _model_module_version = Unicode('^0.1.0').tag(sync=True)
    value = Unicode('Hello World!').tag(sync=True)
    count = Int(0).tag(sync=True)


class MyWidget(widgets.DOMWidget):
    _view_module = Unicode('ipyplotly').tag(sync=True)
    _view_name = Unicode('MyWidgetView').tag(sync=True)
    color = Unicode('red').tag(sync=True)
    plotly_data_str = Unicode().tag(sync=True)
    plotly_layout_str = Unicode().tag(sync=True)
