
# Create sentinal Undefined object
from traitlets import Undefined


def _py_to_js(x, widget_manager):
    # print('_py_to_js')
    # print(x)
    if isinstance(x, dict):
        return {k: _py_to_js(v, widget_manager) for k, v in x.items()}
    elif isinstance(x, (list, tuple)):
        return [_py_to_js(v, widget_manager) for v in x]
    else:
        if x is Undefined:
            return '_undefined_'
        else:
            return x


def _js_to_py(x, widget_manager):
    # print('_js_to_py')
    # print(x)
    if isinstance(x, dict):
        return {k: _js_to_py(v, widget_manager) for k, v in x.items()}
    elif isinstance(x, (list, tuple)):
        return [_js_to_py(v, widget_manager) for v in x]
    elif isinstance(x, str) and x == '_undefined_':
        return Undefined
    else:
        return x


custom_serializers = {
    'from_json': _js_to_py,
    'to_json': _py_to_js
}