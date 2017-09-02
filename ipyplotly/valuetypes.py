import numbers


class _NoDefault(object):
    def __repr__(self):
        return '(no default)'
NoDefault = _NoDefault()
del _NoDefault


class DataArray:
    """
        "data_array": {
            "description": "An {array} of data. The value MUST be an {array}, or we ignore it.",
            "requiredOpts": [],
            "otherOpts": [
                "dflt"
            ]
        },
    """
    def __init__(self, name, parent_name, default=NoDefault):
        self.name = name
        self.parent_name = parent_name
        self.default = default

    def validate_coerce(self, v):

        if v is None:
            if self.default is NoDefault:
                raise ValueError(('The {name} property of {parent_name} has no default value '
                                  'and may not be set to None.'.format(name=self.name, parent_name=self.parent_name)))
            else:
                v = self.default
        else:
            if not DataArray.is_array(v):
                raise ValueError(("The {name} property of {parent_name} must be a list. "
                                 "Received value of type {typ}").format(name=self.name,
                                                                        parent_name=self.parent_name,
                                                                        typ=type(v)))
        return list(v)

    @staticmethod
    def is_array(v):
        return isinstance(v, (list, type))


class Enumerated:
    """
        "enumerated": {
            "description": "Enumerated value type. The available values are listed in `values`.",
            "requiredOpts": [
                "values"
            ],
            "otherOpts": [
                "dflt",
                "coerceNumber",
                "arrayOk"
            ]
        },
    """
    def __init__(self, name, parent_name, default, values, array_ok=False):
        self.name = name
        self.parent_name = parent_name
        self.default = default
        self.values = values
        self.array_ok = array_ok

    def validate_coerce(self, v):
        if v is None:
            v = self.default

        elif DataArray.is_array(v):
            if not self.array_ok:
                raise ValueError(('The {name} property of {parent_name} must be a scalar value. '
                                  'Received value of type "{typ}"'.format(name=self.name,
                                                                          parent_name=self.parent_name,
                                                                          typ=type(v))))

            invalid_vals = [e for e in v if e not in self.values]
            if invalid_vals:
                raise ValueError(('Invalid enumeration value(s) "{csv}" received for {name} property of {parent_name}\n' +
                                  'Valid values are: {valid_vals}').format(
                    csv=", ".join(invalid_vals),
                    name=self.name,
                    parent_name=self.parent_name,
                    valid_vals=self.values
                ))
        else:
            if v not in self.values:
                raise ValueError(
                    ('Invalid enumeration value "{v}" received for {name} property of {parent_name}\n' +
                     'Valid values are: {valid_vals}').format(
                        v=v,
                        name=self.name,
                        parent_name=self.parent_name,
                        valid_vals=self.values
                    ))
        return v


class Boolean:
    """
        "boolean": {
            "description": "A boolean (true/false) value.",
            "requiredOpts": [],
            "otherOpts": [
                "dflt"
            ]
        },
    """
    def __init__(self, name, parent_name, default):
        self.name = name
        self.parent_name = parent_name
        self.default = default

    def validate_coerce(self, v):
        if v is None:
            v = self.default

        elif not isinstance(v, bool):
            raise ValueError(("The {name} property of {parent_name} must be a bool. "
                              "Received value of type {typ}").format(name=self.name,
                                                                     parent_name=self.parent_name,
                                                                     typ=type(v)))
        return v


class Number:
    """
        "number": {
            "description": "A number or a numeric value (e.g. a number inside a string). When applicable, values greater (less) than `max` (`min`) are coerced to the `dflt`.",
            "requiredOpts": [],
            "otherOpts": [
                "dflt",
                "min",
                "max",
                "arrayOk"
            ]
        },
    """
    def __init__(self, name, parent_name, default, min_val=None, max_val=None, array_ok=False):
        self.name = name
        self.parent_name = parent_name
        self.default = default
        self.min = min_val
        self.max = max_val
        self.array_ok = array_ok

    def validate_coerce(self, v):
        if v is None:
            if self.default is None:
                raise ValueError(('The {name} property of {parent_name} has no default value '
                                  'and may not be set to None.'.format(name=self.name, parent_name=self.parent_name)))
            else:
                v = self.default

        elif DataArray.is_array(v):
            if not self.array_ok:
                raise ValueError(('The {name} property of {parent_name} must be a scalar value. '
                                  'Received value of type "{typ}"'.format(name=self.name,
                                                                          parent_name=self.parent_name,
                                                                          typ=type(v))))
            # Add array element validation
        else:
            if not isinstance(v, numbers.Number):
                raise ValueError(("The {name} property of {parent_name} must be a number. "
                                  "Received value of type {typ}").format(name=self.name,
                                                                         parent_name=self.parent_name,
                                                                         typ=type(v)))
            if self.min is not None and v < self.min:
                v = self.default

            if self.max is not None and v > self.max:
                v = self.default

        return v


class Integer:
    """
        "integer": {
            "description": "An integer or an integer inside a string. When applicable, values greater (less) than `max` (`min`) are coerced to the `dflt`.",
            "requiredOpts": [],
            "otherOpts": [
                "dflt",
                "min",
                "max",
                "arrayOk"
            ]
        },
    """
    def __init__(self, name, parent_name, default, min_val=None, max_val=None, array_ok=False):
        self.name = name
        self.parent_name = parent_name
        self.default = default
        self.min = min_val
        self.max = max_val
        self.array_ok = array_ok

    def validate_coerce(self, v):
        if v is None:
            v = self.default

        elif DataArray.is_array(v):
            if not self.array_ok:
                raise ValueError(('The {name} property of {parent_name} must be a scalar value. '
                                  'Received value of type "{typ}"'.format(name=self.name,
                                                                          parent_name=self.parent_name,
                                                                          typ=type(v))))
            # Add array element validation
        else:
            if not isinstance(v, int):
                raise ValueError(("The {name} property of {parent_name} must be an integer. "
                                  "Received value of type {typ}").format(name=self.name,
                                                                         parent_name=self.parent_name,
                                                                         typ=type(v)))

            if self.min is not None and v < self.min:
                v = self.default

            if self.max is not None and v > self.max:
                v = self.default

        return v


class String:
    """
        "string": {
            "description": "A string value. Numbers are converted to strings except for attributes with `strict` set to true.",
            "requiredOpts": [],
            "otherOpts": [
                "dflt",
                "noBlank",
                "strict",
                "arrayOk",
                "values"
            ]
        },
    """
    def __init__(self, name, parent_name, default=NoDefault, no_blank=False, strict=False, array_ok=False, values=None):
        self.name = name
        self.parent_name = parent_name
        self.default = default
        self.no_blank = no_blank
        self.strict = strict
        self.array_ok = array_ok
        self.values = values

    def validate_coerce(self, v):
        if v is None:
            if self.default is NoDefault:
                raise ValueError(('The {name} property of {parent_name} has no default value '
                                  'and may not be set to None.'.format(name=self.name, parent_name=self.parent_name)))
            else:
                v = self.default

        elif DataArray.is_array(v):
            if not self.array_ok:
                raise ValueError(('The {name} property of {parent_name} must be a scalar value. '
                                  'Received value of type "{typ}"'.format(name=self.name,
                                                                          parent_name=self.parent_name,
                                                                          typ=type(v))))
            # Add array element validation
        else:
            if not isinstance(v, str):
                raise ValueError(("The {name} property of {parent_name} must be a string. "
                                  "Received value of type {typ}").format(name=self.name,
                                                                         parent_name=self.parent_name,
                                                                         typ=type(v)))

            if self.no_blank:
                pass

            if self.strict:
                pass

            if self.values and v not in self.values:
                raise ValueError(
                    ('Invalid string value "{v}" received for {name} property of {parent_name}\n' +
                     'Valid values are: {valid_vals}').format(
                        v=v,
                        name=self.name,
                        parent_name=self.parent_name,
                        valid_vals=self.values
                    ))

        return v


class Color:
    """
        "color": {
            "description": "A string describing color. Supported formats: - hex (e.g. '#d3d3d3') - rgb (e.g. 'rgb(255, 0, 0)') - rgba (e.g. 'rgb(255, 0, 0, 0.5)') - hsl (e.g. 'hsl(0, 100%, 50%)') - hsv (e.g. 'hsv(0, 100%, 100%)') - named colors (full list: http://www.w3.org/TR/css3-color/#svg-color)",
            "requiredOpts": [],
            "otherOpts": [
                "dflt",
                "arrayOk"
            ]
        },
    """
    def __init__(self, name, parent_name, default=None):
        self.name = name
        self.parent_name = parent_name
        self.default = default

    def validate_coerce(self, v):
        if v is None:
            v = self.default

        elif not isinstance(v, str):
            raise ValueError(("The {name} property of {parent_name} must be a string. "
                              "Received value of type {typ}").format(name=self.name,
                                                                     parent_name=self.parent_name,
                                                                     typ=type(v)))

        # TODO: validate color types
        return v


    """
        "colorscale": {
            "description": "A Plotly colorscale either picked by a name: (any of Greys, YlGnBu, Greens, YlOrRd, Bluered, RdBu, Reds, Blues, Picnic, Rainbow, Portland, Jet, Hot, Blackbody, Earth, Electric, Viridis ) customized as an {array} of 2-element {arrays} where the first element is the normalized color level value (starting at *0* and ending at *1*), and the second item is a valid color string.",
            "requiredOpts": [],
            "otherOpts": [
                "dflt"
            ]
        },
    """

    """
        "angle": {
            "description": "A number (in degree) between -180 and 180.",
            "requiredOpts": [],
            "otherOpts": [
                "dflt"
            ]
        },
    """

    """
        "subplotid": {
            "description": "An id string of a subplot type (given by dflt), optionally followed by an integer >1. e.g. if dflt='geo', we can have 'geo', 'geo2', 'geo3', ...",
            "requiredOpts": [
                "dflt"
            ],
            "otherOpts": []
        },
    """

    """
        "flaglist": {
            "description": "A string representing a combination of flags (order does not matter here). Combine any of the available `flags` with *+*. (e.g. ('lines+markers')). Values in `extras` cannot be combined.",
            "requiredOpts": [
                "flags"
            ],
            "otherOpts": [
                "dflt",
                "extras",
                "arrayOk"
            ]
        },
    """

    """
        "any": {
            "description": "Any type.",
            "requiredOpts": [],
            "otherOpts": [
                "dflt",
                "values",
                "arrayOk"
            ]
        },
    """

    """
        "info_array": {
            "description": "An {array} of plot information.",
            "requiredOpts": [
                "items"
            ],
            "otherOpts": [
                "dflt",
                "freeLength"
            ]
        }
    """