import numbers
import collections
import textwrap

import numpy as np
import re
# Notes: These become base validator classes, one for each value type. The code-gen validators for primitive types
# subclass these (hand written) base validator types. compound validators are composed of other compound validators
# and primitive validators
#
# The code gen process will input a property json specification and produce source code for:
#  - a validator class.
#  - A data class for compound types. These hold references to validators for all of their properties
#
# I write a TraceObjBase class that implements the idea of receiving and passing restyle events up the chain
# I write a FigureBase that has current figure logic
#
# I code gen the figure subclass that has all of the add_scatter, add_bar, etc. methods.
#
# I think that's all of the code gen tasks. Validators, Data Classes, and Figure methods

class _NoDefault(object):
    def __repr__(self):
        return '(no default)'
NoDefault = _NoDefault()
del _NoDefault


class BaseValidator:
    def __init__(self, name, parent_name):
        self.parent_name = parent_name
        self.name = name

    def validate_coerce(self, v):
        raise NotImplemented()


class DataArrayValidator(BaseValidator):
    """
        "data_array": {
            "description": "An {array} of data. The value MUST be an {array}, or we ignore it.",
            "requiredOpts": [],
            "otherOpts": [
                "dflt"
            ]
        },
    """
    def __init__(self, name, parent_name, dflt=None, **_):
        super().__init__(name=name, parent_name=parent_name)
        self.default = dflt

    def validate_coerce(self, v):

        if v is None:
            if self.default is NoDefault:
                raise ValueError(('The {name} property of {parent_name} has no default value '
                                  'and may not be set to None.'.format(name=self.name, parent_name=self.parent_name)))
            else:
                v = self.default
        else:
            if not DataArrayValidator.is_array(v):
                raise ValueError(("The {name} property of {parent_name} must be array like. "
                                 "Received value of type {typ}").format(name=self.name,
                                                                        parent_name=self.parent_name,
                                                                        typ=type(v)))
        return v

    @staticmethod
    def is_array(v):
        return isinstance(v, (list, type))


class EnumeratedValidator(BaseValidator):
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
    def __init__(self, name, parent_name, values, dflt=None, array_ok=False, coerce_number=False, **_):
        super().__init__(name=name, parent_name=parent_name)

        # coerce_number is rarely used and not implemented
        self.coerce_number = coerce_number
        self.default = dflt
        self.values = values
        self.array_ok = array_ok

    def validate_coerce(self, v):
        if v is None:
            v = self.default

        elif self.array_ok and DataArrayValidator.is_array(v):
            invalid_vals = [e for e in v if (not isinstance(e, collections.Hashable)) or (e not in self.values)]
            if invalid_vals:
                raise ValueError(('Invalid enumeration element(s) received for {name} '
                                  'property of {parent_name}: [{csv}]\n'
                                  '     Valid values are: {valid_vals}').format(
                    csv=", ".join([repr(v) for v in invalid_vals]),
                    name=self.name,
                    parent_name=self.parent_name,
                    valid_vals=self.values
                ))
        else:
            if v not in self.values:
                raise ValueError(
                    ('Invalid enumeration value received for {name} property of {parent_name}: "{v}"\n' +
                     '    Valid values are: {valid_vals}').format(
                        v=v,
                        name=self.name,
                        parent_name=self.parent_name,
                        valid_vals=self.values
                    ))

        return v


class BooleanValidator(BaseValidator):
    """
        "boolean": {
            "description": "A boolean (true/false) value.",
            "requiredOpts": [],
            "otherOpts": [
                "dflt"
            ]
        },
    """
    def __init__(self, name, parent_name, dflt=None, **_):
        super().__init__(name=name, parent_name=parent_name)
        self.default = dflt

    def validate_coerce(self, v):
        if v is None:
            v = self.default

        elif not isinstance(v, bool):
            raise ValueError(("The {name} property of {parent_name} must be a bool. "
                              "Received value of type {typ}: {v}").format(name=self.name,
                                                                          parent_name=self.parent_name,
                                                                          typ=type(v),
                                                                          v=repr(v)))
        return v


class NumberValidator(BaseValidator):
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
    def __init__(self, name, parent_name, dflt=None, min=None, max=None, array_ok=False, **_):
        super().__init__(name=name, parent_name=parent_name)
        self.default = dflt
        self.min_val = min
        self.max_val = max
        self.array_ok = array_ok

    def validate_coerce(self, v):
        if v is None:
            v = self.default

        elif self.array_ok and DataArrayValidator.is_array(v):

            try:
                v_array = np.array(v, dtype='float64')
            except (ValueError, TypeError, OverflowError) as ve:
                raise ValueError(('All elements of the {name} property of {parent_name} must be numbers.\n'
                                  '    Error: {msg}').format(name=self.name,
                                                          parent_name=self.parent_name,
                                                          msg=ve.args[0]))
            v_valid = np.ones(v_array.shape, dtype='bool')
            if self.min_val is not None:
                v_valid = np.logical_and(v_valid, v_array >= self.min_val)

            if self.max_val is not None:
                v_valid = np.logical_and(v_valid, v_array <= self.max_val)

            if not np.all(v_valid):
                invalid_els = np.array(v, dtype='object')[np.logical_not(v_valid)][:10].tolist()
                raise ValueError(("All elements of the {name} property of {parent_name} must be in the range "
                                  "[{min_val}, {max_val}]. \n"
                                  "    Invalid elements include: {v}").format(name=self.name,
                                                                          parent_name=self.parent_name,
                                                                          min_val=self.min_val,
                                                                          max_val=self.max_val,
                                                                          v=invalid_els))

            v = v_array.tolist()
        else:
            if not isinstance(v, numbers.Number):
                raise ValueError(("The {name} property of {parent_name} must be a number. "
                                  "Received value of type {typ}: {v}").format(name=self.name,
                                                                              parent_name=self.parent_name,
                                                                              typ=type(v),
                                                                              v=repr(v)))
            if (self.min_val is not None and not v >= self.min_val) or \
                    (self.max_val is not None and not v <= self.max_val):
                raise ValueError(("The {name} property of {parent_name} must be in the range "
                                  "[{min_val}, {max_val}]. Received: {v}").format(name=self.name,
                                                                                  parent_name=self.parent_name,
                                                                                  min_val=self.min_val,
                                                                                  max_val=self.max_val,
                                                                                  v=repr(v)))

        return v


class IntegerValidator(BaseValidator):
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
    def __init__(self, name, parent_name, dflt=None, min=None, max=None, array_ok=False, **_):
        super().__init__(name=name, parent_name=parent_name)
        self.default = int(dflt) if dflt is not None else None
        self.min_val = int(min) if min is not None else None
        self.max_val = int(max) if max is not None else None
        self.array_ok = array_ok

    def validate_coerce(self, v):
        if v is None:
            v = self.default

        elif self.array_ok and DataArrayValidator.is_array(v):

            try:
                v_array = np.array(v, dtype='int64')
            except (ValueError, TypeError, OverflowError) as ve:
                raise ValueError(('All elements of the {name} property of {parent_name} must be '
                                  'convertible to integers.\n'
                                  '    Error: {msg}').format(name=self.name,
                                                          parent_name=self.parent_name,
                                                          msg=ve.args[0]))

            v_valid = np.ones(v_array.shape, dtype='bool')
            if self.min_val is not None:
                v_valid = np.logical_and(v_valid, v_array >= self.min_val)

            if self.max_val is not None:
                v_valid = np.logical_and(v_valid, v_array <= self.max_val)

            if not np.all(v_valid):
                invalid_els = np.array(v, dtype='object')[np.logical_not(v_valid)][:10].tolist()
                raise ValueError(("All elements of the {name} property of {parent_name} must be in the range "
                                  "[{min_val}, {max_val}]. \n"
                                  "    Invalid elements include: {v}").format(name=self.name,
                                                                          parent_name=self.parent_name,
                                                                          min_val=self.min_val,
                                                                          max_val=self.max_val,
                                                                          v=invalid_els))

            v = v_array.tolist()
        else:
            try:
                if not isinstance(v, numbers.Number):
                    # don't let int() cast strings to ints
                    raise ValueError('')

                v_int = int(v)
            except (ValueError, TypeError, OverflowError) as ve:
                raise ValueError(("The {name} property of {parent_name} must be a number that can be converted "
                                  "to an integer.\n"
                                  "    Received value of type {typ}: {v}").format(name=self.name,
                                                                                  parent_name=self.parent_name,
                                                                                  typ=type(v),
                                                                                  v=repr(v)))

            if (self.min_val is not None and not v >= self.min_val) or \
                    (self.max_val is not None and not v <= self.max_val):
                raise ValueError(("The {name} property of {parent_name} must be in the range "
                                  "[{min_val}, {max_val}]. Received: {v}").format(name=self.name,
                                                                                  parent_name=self.parent_name,
                                                                                  min_val=self.min_val,
                                                                                  max_val=self.max_val,
                                                                                  v=repr(v)))
            v = v_int

        return v


class StringValidator(BaseValidator):
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
    def __init__(self, name, parent_name, dflt=None, no_blank=False, strict=False, array_ok=False, values=None, **_):
        super().__init__(name=name, parent_name=parent_name)
        self.default = dflt
        self.no_blank = no_blank
        self.strict = strict        # Not implemented. We're always strict
        self.array_ok = array_ok
        self.values = values

    def validate_coerce(self, v):
        if v is None:
            if self.default is NoDefault:
                raise ValueError(('The {name} property of {parent_name} has no default value '
                                  'and may not be set to None.'.format(name=self.name, parent_name=self.parent_name)))
            else:
                v = self.default

        elif self.array_ok and DataArrayValidator.is_array(v):
            invalid_els = [e for e in v if not isinstance(e, str)]
            if invalid_els:
                raise ValueError(('All elements of the {name} property of {parent_name} must be strings\n'
                                  '    Invalid elements include: {invalid}').format(name=self.name,
                                                                                    parent_name=self.parent_name,
                                                                                    invalid=invalid_els[:10]))

            if self.no_blank:
                invalid_els = [e for e in v if len(e) == 0]
                if invalid_els:
                    raise ValueError(('Elements of the {name} property of {parent_name} may not be blank\n'
                                      '    Invalid elements include: {invalid}').format(name=self.name,
                                                                                        parent_name=self.parent_name,
                                                                                        invalid=invalid_els[:10]))

            if self.values:
                invalid_els = [e for e in v if e not in self.values]
                if invalid_els:
                    raise ValueError(('Invalid string element(s) received for {name} '
                                      'property of {parent_name}\n'
                                      '    Invalid elements include: {invalid}\n'  
                                      '    Valid values are:         {valid_vals}').format(
                        name=self.name,
                        parent_name=self.parent_name,
                        invalid=invalid_els[:10],
                        valid_vals=self.values
                    ))

        else:
            if not isinstance(v, str):
                raise ValueError(("The {name} property of {parent_name} must be a string. \n"
                                  "    Received value of type {typ}: {v}").format(name=self.name,
                                                                                  parent_name=self.parent_name,
                                                                                  typ=type(v),
                                                                                  v=v))

            if self.no_blank and len(v) == 0:
                raise ValueError(("The {name} property of {parent_name} may not be blank.\n"
                                  "    Received: {v}").format(name=self.name,
                                                              parent_name=self.parent_name,
                                                              v=v))

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


class ColorValidator(BaseValidator):
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
    re_hex = re.compile('#([A-Fa-f0-9]{6}|[A-Fa-f0-9]{3})')
    re_rgb_etc = re.compile('(rgb|hsl|hsv)a?\(\d{1,3}%?(,\d{1,3}%?){2,3}\)')

    named_colors = [
        "aliceblue", "antiquewhite", "aqua", "aquamarine", "azure", "beige", "bisque", "black", "blanchedalmond",
        "blue", "blueviolet", "brown", "burlywood", "cadetblue", "chartreuse", "chocolate", "coral", "cornflowerblue",
        "cornsilk", "crimson", "cyan", "darkblue", "darkcyan", "darkgoldenrod", "darkgray", "darkgrey", "darkgreen",
        "darkkhaki", "darkmagenta", "darkolivegreen", "darkorange", "darkorchid", "darkred", "darksalmon",
        "darkseagreen", "darkslateblue", "darkslategray", "darkslategrey", "darkturquoise", "darkviolet", "deeppink",
        "deepskyblue", "dimgray", "dimgrey", "dodgerblue", "firebrick", "floralwhite", "forestgreen", "fuchsia",
        "gainsboro", "ghostwhite", "gold", "goldenrod", "gray", "grey", "green", "greenyellow", "honeydew", "hotpink",
        "indianred", "indigo", "ivory", "khaki", "lavender", "lavenderblush", "lawngreen", "lemonchiffon", "lightblue",
        "lightcoral", "lightcyan", "lightgoldenrodyellow", "lightgray", "lightgrey", "lightgreen", "lightpink",
        "lightsalmon", "lightseagreen", "lightskyblue", "lightslategray", "lightslategrey", "lightsteelblue",
        "lightyellow", "lime", "limegreen", "linen", "magenta", "maroon", "mediumaquamarine", "mediumblue",
        "mediumorchid", "mediumpurple", "mediumseagreen", "mediumslateblue", "mediumspringgreen", "mediumturquoise",
        "mediumvioletred", "midnightblue", "mintcream", "mistyrose", "moccasin", "navajowhite", "navy", "oldlace",
        "olive", "olivedrab", "orange", "orangered", "orchid", "palegoldenrod", "palegreen", "paleturquoise",
        "palevioletred", "papayawhip", "peachpuff", "peru", "pink", "plum", "powderblue", "purple", "red", "rosybrown",
        "royalblue", "saddlebrown", "salmon", "sandybrown", "seagreen", "seashell", "sienna", "silver", "skyblue",
        "slateblue", "slategray", "slategrey", "snow", "springgreen", "steelblue", "tan", "teal", "thistle", "tomato",
        "turquoise", "violet", "wheat", "white", "whitesmoke", "yellow", "yellowgreen"]

    valid_color_description = """\
    Colors may be specified as:
      - Hex strings (e.g. '#ff0000')
      - rgb/rgba strings (e.g. 'rgb(255, 0, 0)')
      - hsl/hsla strings (e.g. 'hsl(0, 100%, 50%)')
      - hsv/hsva strings (e.g. 'hsv(0, 100%, 100%)')
      - Named CSS colors: 
            {clrs} 
    """.format(clrs='\n'.join(textwrap.wrap(', '.join(named_colors), width=80, subsequent_indent=' ' * 12)))

    def __init__(self, name, parent_name, dflt=None, array_ok=False, **_):
        super().__init__(name=name, parent_name=parent_name)
        self.default = dflt
        self.array_ok = array_ok

    def validate_coerce(self, v):
        if v is None:
            if self.default is NoDefault:
                raise ValueError(('The {name} property of {parent_name} has no default value '
                                  'and may not be set to None.'.format(name=self.name, parent_name=self.parent_name)))
            else:
                v = self.default
        elif self.array_ok and DataArrayValidator.is_array(v):
            invalid_els = [e for e in v if not isinstance(e, str)]
            if invalid_els:
                raise ValueError(('All elements of the {name} property of {parent_name} must be strings\n'
                                  '    Invalid elements include: {invalid}').format(name=self.name,
                                                                                    parent_name=self.parent_name,
                                                                                    invalid=invalid_els[:10]))

            invalid_els = [c for c in v if not ColorValidator.is_valid_color(c)]
            if invalid_els:
                raise ValueError(('All elements of the {name} property of {parent_name} must be valid colors\n'
                                  '    Invalid elements include: {invalid}\n'
                                  '{vald_clr_desc}').format(name=self.name,
                                                            parent_name=self.parent_name,
                                                            invalid=invalid_els[:10],
                                                            vald_clr_desc=ColorValidator.valid_color_description))

        else:
            if not isinstance(v, str):
                raise ValueError(("The {name} property of {parent_name} must be a string.\n"
                                  "    Received value of type {typ}").format(name=self.name,
                                                                         parent_name=self.parent_name,
                                                                         typ=type(v)))

            if not ColorValidator.is_valid_color(v):
                raise ValueError(("The {name} property of {parent_name} must be a valid colors.\n"
                                  "    Received: {v}\n"
                                  "{vald_clr_desc}\n"
                                  "").format(name=self.name,
                                             parent_name=self.parent_name,
                                             v=v,
                                             vald_clr_desc=ColorValidator.valid_color_description))

        return v

    @staticmethod
    def is_valid_color(v: str):

        # Remove spaces so regexes don't need to bother with them.
        v = v.replace(' ', '')

        if ColorValidator.re_hex.fullmatch(v):
            # valid hex color (e.g. #f34ab3)
            return True
        elif ColorValidator.re_rgb_etc.fullmatch(v):
            # Valid rgb(a), hsl(a), hsv(a) color (e.g. rgba(10, 234, 200, 50%)
            return True
        elif v in ColorValidator.named_colors:
            # Valid named color (e.g. 'coral')
            return True
        else:
            # Not a valid color
            return False



class ColorscaleValidator(BaseValidator):
    """
        "colorscale": {
            "description": "A Plotly colorscale either picked by a name: (any of Greys, YlGnBu, Greens, YlOrRd, Bluered, RdBu, Reds, Blues, Picnic, Rainbow, Portland, Jet, Hot, Blackbody, Earth, Electric, Viridis ) customized as an {array} of 2-element {arrays} where the first element is the normalized color level value (starting at *0* and ending at *1*), and the second item is a valid color string.",
            "requiredOpts": [],
            "otherOpts": [
                "dflt"
            ]
        },
    """
    def __init__(self, name, parent_name, dflt=None, **_):
        super().__init__(name=name, parent_name=parent_name)
        self.default = dflt

    def validate_coerce(self, v):
        if v is None:
            v = self.default
        elif not isinstance(v, str):
            raise ValueError(("The {name} property of {parent_name} must be a string. "
                              "Received value of type {typ}").format(name=self.name,
                                                                     parent_name=self.parent_name,
                                                                     typ=type(v)))
        return v


class AngleValidator(BaseValidator):
    """
        "angle": {
            "description": "A number (in degree) between -180 and 180.",
            "requiredOpts": [],
            "otherOpts": [
                "dflt"
            ]
        },
    """
    def __init__(self, name, parent_name, dflt=None, **_):
        super().__init__(name=name, parent_name=parent_name)
        self.default = dflt

    def validate_coerce(self, v):
        if v is None:
            v = self.default

        return v


class SubplotidValidator(BaseValidator):
    """
        "subplotid": {
            "description": "An id string of a subplot type (given by dflt), optionally followed by an integer >1. e.g. if dflt='geo', we can have 'geo', 'geo2', 'geo3', ...",
            "requiredOpts": [
                "dflt"
            ],
            "otherOpts": []
        },
    """
    def __init__(self, name, parent_name, dflt=None, **_):
        super().__init__(name=name, parent_name=parent_name)
        self.default = dflt

    def validate_coerce(self, v):
        if v is None:
            v = self.default
        elif not isinstance(v, str):
            raise ValueError(("The {name} property of {parent_name} must be a string. "
                              "Received value of type {typ}").format(name=self.name,
                                                                     parent_name=self.parent_name,
                                                                     typ=type(v)))
        elif not v.startswith(self.default):
            raise ValueError(("The {name} property of {parent_name} must be a string prefixed by '{default}', "
                              "optionally followed by an integer > 1\n"
                              "Received '{v}'").format(name=self.name,
                                                       parent_name=self.parent_name,
                                                       default=self.default, v=v))
        return v


class FlaglistValidator(BaseValidator):
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
    def __init__(self, name, parent_name, flags, dflt=None, extras=None, array_ok=False, **_):
        super().__init__(name=name, parent_name=parent_name)
        self.flags = flags
        self.default = dflt
        self.extras = extras
        self.array_ok = array_ok

    def validate_coerce(self, v):
        if v is None:
            v = self.default

        elif not isinstance(v, str):
            raise ValueError(("The {name} property of {parent_name} must be a string. "
                              "Received value of type {typ}").format(name=self.name,
                                                                     parent_name=self.parent_name,
                                                                     typ=type(v)))

        # TODO: validate flag type
        return v


class AnyValidator(BaseValidator):
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
    def __init__(self, name, parent_name, dflt=None, values=None, array_ok=False):
        super().__init__(name=name, parent_name=parent_name)
        self.default = dflt
        self.values = values
        self.array_ok = array_ok

    def validate_coerce(self, v):
        if v is None:
            v = self.default

        # TODO: Validate array_ok
        return v


class InfoArrayValidator(BaseValidator):
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
    def __init__(self, name, parent_name, items, dflt=None, freeLength=None):
        super().__init__(name=name, parent_name=parent_name)
        self.items = items
        self.default = dflt
        self.free_length = freeLength

    def validate_coerce(self, v):
        if v is None:
            v = self.default

        # TODO: Validate items
        return v


class CompoundValidator(BaseValidator):
    def __init__(self, name, parent_name, data_class):
        super().__init__(name=name, parent_name=parent_name)
        self.data_class = data_class

    def validate_coerce(self, v):
        if v is None:
            v = self.data_class()

        elif isinstance(v, dict):
            v = self.data_class(**v)
        elif isinstance(v, self.data_class):
            # Leave unchanged
            pass
        elif not isinstance(v, str):
            raise ValueError(("The {name} property of {parent_name} must be a dict or instance of {cls_name}.\n"
                              "Received value of type {typ}").format(name=self.name,
                                                                     parent_name=self.parent_name,
                                                                     cls_name=self.data_class.__name__,
                                                                     typ=type(v)))

        return v
