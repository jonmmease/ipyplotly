from ipyplotly.basevalidators import CompoundValidator


class BaseDataType:

    def __init__(self, type_name):
        self.type_name = type_name
        self._data = {}
        self._validators = {}
        self.parent = None

    def _send_restyle(self, prop, val):
        if self.parent:
            send_val = [val] if isinstance(val, list) else val
            self.parent._restyle_child(self, prop, send_val)

    def _set_prop(self, prop, val):
        validator = self._validators.get(prop)
        val = validator.validate_coerce(val)

        if isinstance(validator, CompoundValidator):
            # Reparent
            val.parent = self
            dict_val = val._data
        else:
            dict_val = val

        if prop not in self._data or self._data[prop] != dict_val:
            self._data[prop] = dict_val
            self._send_restyle(prop, dict_val)

        return val

    def _restyle_child(self, child, prop, val):
        self._send_restyle('{child_name}.{prop}'.format(child_name=child.type_name, prop=prop), val)