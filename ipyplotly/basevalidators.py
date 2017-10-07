import base64
import numbers
import collections
import pathlib
import textwrap
import uuid

import io
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
from PIL import Image

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
        elif DataArrayValidator.is_array(v):
            v = DataArrayValidator.copy_to_contiguous_readonly_numpy_array(v)
        else:
            raise ValueError(("The {name} property of {parent_name} must be array like. "
                              "Received value of type {typ}").format(name=self.name,
                                                                     parent_name=self.parent_name,
                                                                     typ=type(v)))
        return v

    @staticmethod
    def is_array(v):
        return isinstance(v, (list, type)) or (isinstance(v, np.ndarray) and v.ndim == 1)

    @staticmethod
    def copy_to_contiguous_readonly_numpy_array(v, dtype=None, force_numeric=False):

        # Copy to numpy array and handle dtype param
        # ------------------------------------------
        # If dtype was not specified then it will be passed to the numpy array constructor as None and the data type
        # will be inferred automatically
        if not isinstance(v, np.ndarray):
            new_v = np.array(v, order='C', dtype=dtype)
        else:
            new_v = v.astype(dtype, order='C')

        # Handle force numeric param
        # --------------------------
        if force_numeric and new_v.dtype.kind not in ['u', 'i', 'f']:  # (un)signed int, or float
            raise ValueError('Input value is not numeric and force_numeric parameter set to True')

        if dtype != 'unicode':
            # Force non-numeric arrays to have object type
            # --------------------------------------------
            # Here we make sure that non-numeric arrays have the object datatype. This works around cases like
            # np.array([1, 2, '3']) where numpy converts the integers to strings and returns array of dtype '<U21'
            if new_v.dtype.kind not in ['u', 'i', 'f', 'O']:  # (un)signed int, float, or object
                new_v = np.array(v, dtype='object')

        # Set new array to be read-only
        # -----------------------------
        new_v.flags['WRITEABLE'] = False

        return new_v


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

        # compile regexes
        self.val_regexs = []
        for v in self.values:
            if v and isinstance(v, str) and v[0] == '/' and v[-1] == '/':
                # String is regex with leading and trailing '/' character
                self.val_regexs.append(re.compile(v[1:-1]))
            else:
                self.val_regexs.append(None)

        self.array_ok = array_ok

    def in_values(self, e):
        is_str = isinstance(e, str)
        for v, regex in zip(self.values, self.val_regexs):
            if is_str and regex:
                in_values = regex.fullmatch(e) is not None
            else:
                in_values = e == v

            if in_values:
                return True

        return False

    def validate_coerce(self, v):
        if v is None:
            v = self.default

        elif self.array_ok and DataArrayValidator.is_array(v):
            invalid_els = [e for e in v if (not self.in_values(e))]
            if invalid_els:
                valid_str = '\n'.join(textwrap.wrap(repr(self.values),
                                                    subsequent_indent=' ' * 8,
                                                    break_on_hyphens=False))

                raise ValueError(('Invalid enumeration element(s) received for {name} property of {parent_name}.\n'
                                  '    Invalid elements include: {invalid_els}\n'
                                  '    Valid values are:\n'
                                  '        {valid_str}').format(
                    name=self.name,
                    parent_name=self.parent_name,
                    invalid_els=invalid_els[:10],
                    valid_str=valid_str
                ))
            v = DataArrayValidator.copy_to_contiguous_readonly_numpy_array(v)
        else:
            if not self.in_values(v):
                valid_str = '\n'.join(textwrap.wrap(repr(self.values),
                                                    subsequent_indent=' ' * 8,
                                                    break_on_hyphens=False))
                raise ValueError(
                    ('Invalid enumeration value received for {name} property of {parent_name}: "{v}"\n' +
                     '    Valid values are:\n'
                     '        {valid_str}').format(
                        v=v,
                        name=self.name,
                        parent_name=self.parent_name,
                        valid_str=valid_str
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
        self.min_val = min if min is not None else -np.inf
        self.max_val = max if max is not None else np.inf
        self.array_ok = array_ok

    def validate_coerce(self, v):
        if v is None:
            v = self.default

        elif self.array_ok and DataArrayValidator.is_array(v):

            try:
                v_array = DataArrayValidator.copy_to_contiguous_readonly_numpy_array(v, force_numeric=True)
            except ValueError as ve:
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
                # Grab up to the first 10 invalid values
                some_invalid_els = np.array(v, dtype='object')[np.logical_not(v_valid)][:10].tolist()
                raise ValueError(("All elements of the {name} property of {parent_name} must be in the range "
                                  "[{min_val}, {max_val}]. \n"
                                  "    Invalid elements include: {v}").format(name=self.name,
                                                                              parent_name=self.parent_name,
                                                                              min_val=self.min_val,
                                                                              max_val=self.max_val,
                                                                              v=some_invalid_els))
            v = v_array  # Always numpy array of float64
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
                v_array = DataArrayValidator.copy_to_contiguous_readonly_numpy_array(v, dtype='int32')

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
            v = v_array
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
            v = DataArrayValidator.copy_to_contiguous_readonly_numpy_array(v, dtype='unicode')

            if self.no_blank:
                invalid_els = v[v == ''][:10].tolist()
                if invalid_els:
                    raise ValueError(('Elements of the {name} property of {parent_name} may not be blank\n'
                                      '    Invalid elements include: {invalid}').format(name=self.name,
                                                                                        parent_name=self.parent_name,
                                                                                        invalid=invalid_els[:10]))

            if self.values:
                invalid_els = v[np.logical_not(np.isin(v, self.values))][:10].tolist()
                if invalid_els:
                    valid_str = '\n'.join(textwrap.wrap(repr(self.values),
                                                        subsequent_indent=' ' * 8,
                                                        break_on_hyphens=False))

                    raise ValueError(('Invalid string element(s) received for {name} property of {parent_name}\n'
                                      '    Invalid elements include: {invalid}\n'  
                                      '    Valid values are:\n'
                                      '        {valid_str}').format(
                        name=self.name,
                        parent_name=self.parent_name,
                        invalid=invalid_els[:10],
                        valid_str=valid_str
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
                valid_str = '\n'.join(textwrap.wrap(repr(self.values),
                                                    subsequent_indent=' ' * 8,
                                                    break_on_hyphens=False))
                raise ValueError(
                    ('Invalid string value "{v}" received for {name} property of {parent_name}\n' +
                     '    Valid values are:\n'
                     '        {valid_str}').format(
                        v=v,
                        name=self.name,
                        parent_name=self.parent_name,
                        valid_str=valid_str
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
    re_rgb_etc = re.compile('(rgb|hsl|hsv)a?\([\d.]{1,4}%?(,[\d.]{1,4}%?){2,3}\)')

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
            v_array = DataArrayValidator.copy_to_contiguous_readonly_numpy_array(v)
            if v_array.dtype.kind in ['u', 'i', 'f']:  # (un)signed int or float
                # All good
                v = v_array
            else:
                # ### Check that strings are valid colors ###
                invalid_els = [e for e in v if not (isinstance(e, str) or isinstance(e, numbers.Number))]
                if invalid_els:
                    raise ValueError(('All elements of the {name} property of {parent_name} must be strings or '
                                      'numbers\n'
                                      '    Invalid elements include: {invalid}').format(name=self.name,
                                                                                        parent_name=self.parent_name,
                                                                                        invalid=invalid_els[:10]))

                invalid_els = [c for c in v if not ColorValidator.is_valid_color(c)]
                if invalid_els:
                    raise ValueError(('All elements of the {name} property of {parent_name} must be numbers or valid '
                                      'colors\n'
                                      '    Invalid elements include: {invalid}\n'
                                      '{vald_clr_desc}').format(name=self.name,
                                                                parent_name=self.parent_name,
                                                                invalid=invalid_els[:10],
                                                                vald_clr_desc=ColorValidator.valid_color_description))

                v = DataArrayValidator.copy_to_contiguous_readonly_numpy_array(v, dtype='unicode')

        else:
            if not isinstance(v, str):
                raise ValueError(("The {name} property of {parent_name} must be a string.\n"
                                  "    Received value of type {typ}").format(name=self.name,
                                                                             parent_name=self.parent_name,
                                                                             typ=type(v)))

            if not ColorValidator.is_valid_color(v):
                raise ValueError(("The {name} property of {parent_name} must be a valid color.\n"
                                  "    Received: {v}\n"
                                  "{vald_clr_desc}\n"
                                  "").format(name=self.name,
                                             parent_name=self.parent_name,
                                             v=v,
                                             vald_clr_desc=ColorValidator.valid_color_description))

        return v

    @staticmethod
    def is_valid_color(v: str, allow_number=True):

        if isinstance(v, numbers.Number) and allow_number:
            return True

        # Remove spaces so regexes don't need to bother with them.
        v = v.replace(' ', '')
        v = v.lower()

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

    named_colorscales = ['Greys', 'YlGnBu', 'Greens', 'YlOrRd', 'Bluered', 'RdBu', 'Reds', 'Blues', 'Picnic',
                         'Rainbow', 'Portland', 'Jet', 'Hot', 'Blackbody', 'Earth', 'Electric', 'Viridis']

    valid_colorscale_description = """\
        Colorscales may be specified as:
          - A list of 2-element lists where the first element is the normalized color level value 
            (starting at 0 and ending at 1), and the second item is a valid color string. 
            (e.g. [[0.5, 'red'], [1.0, 'blue']])
          - One of the following named colorscales:
                ['Greys', 'YlGnBu', 'Greens', 'YlOrRd', 'Bluered', 'RdBu', 'Reds', 'Blues', 'Picnic', 
                 'Rainbow', 'Portland', 'Jet', 'Hot', 'Blackbody', 'Earth', 'Electric', 'Viridis']
        """

    def __init__(self, name, parent_name, dflt=None, **_):
        super().__init__(name=name, parent_name=parent_name)
        self.default = dflt

    def validate_coerce(self, v):
        v_valid = False

        if v is None:
            v = self.default

        if v is None:
            v_valid = True
        elif isinstance(v, str):
            if v in ColorscaleValidator.named_colorscales:
                v_valid = True

        elif DataArrayValidator.is_array(v) and len(v) > 0:
            invalid_els = [e for e in v
                           if not DataArrayValidator.is_array(e) or
                           len(e) != 2 or
                           not isinstance(e[0], numbers.Number) or
                           not (0 <= e[0] <= 1) or
                           not isinstance(e[1], str) or
                           not ColorValidator.is_valid_color(e[1])]
            if len(invalid_els) == 0:
                v_valid = True

        if not v_valid:
            raise ValueError(("The {name} property of {parent_name} must be a valid colorscale.\n"
                              "    Received value: {v}\n"
                              "{valid_desc}").format(name=self.name,
                                                     parent_name=self.parent_name,
                                                     v=v,
                                                     valid_desc=ColorscaleValidator.valid_colorscale_description))
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
    def __init__(self, name, parent_name, dflt, **_):
        super().__init__(name=name, parent_name=parent_name)
        self.default = dflt
        self.regex = dflt + "(\d*)"

    def validate_coerce(self, v):
        if v is None:
            v = self.default
        elif not isinstance(v, str):
            raise ValueError(("The {name} property of {parent_name} must be a string. "
                              "Received value of type {typ}").format(name=self.name,
                                                                     parent_name=self.parent_name,
                                                                     typ=type(v)))
        elif not re.fullmatch(self.regex, v):
            raise ValueError(("The {name} property of {parent_name} must be a string prefixed by '{default}', "
                              "optionally followed by an integer > 1\n"
                              "Received '{v}'").format(name=self.name,
                                                       parent_name=self.parent_name,
                                                       default=self.default, v=v))
        else:
            digit_str = re.fullmatch(self.regex, v).group(1)
            if len(digit_str) > 0 and int(digit_str) in [0, 1]:
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
        self.extras = extras if extras is not None else []
        self.array_ok = array_ok

        self.all_flags = self.flags + self.extras

        if self.extras:
            extras_line = """\
      - OR exactly one of {extras} (e.g. '{eg_extra}')""".format(extras=self.extras, eg_extra=self.extras[-1])
        else:
            extras_line = ''

        self.valid_description = """\
    Value must be a string containing:
      - Any combination of {flags} joined with '+' characters (e.g. '{eg_flag}')
{extras_line}
        """.format(flags=self.flags, eg_flag='+'.join(self.flags[:2]), extras_line=extras_line)

    def is_flaglist_valid(self, v):
        if not isinstance(v, str):
            return True

        split_vals = v.split('+')
        all_flags_valid = [f for f in split_vals if f not in self.all_flags] == []
        has_extras = [f for f in split_vals if f in self.extras] != []
        return all_flags_valid and (not has_extras or len(split_vals) == 1)

    def validate_coerce(self, v):
        if v is None:
            v = self.default

        elif self.array_ok and DataArrayValidator.is_array(v):
            invalid_els = [e for e in v if not isinstance(e, str)]
            if invalid_els:
                raise ValueError(('All elements of the {name} property of {parent_name} must be strings\n'
                                  '    Invalid elements include: {invalid}').format(name=self.name,
                                                                                    parent_name=self.parent_name,
                                                                                    invalid=invalid_els[:10]))

            invalid_els = [e for e in v if not self.is_flaglist_valid(e)]
            if invalid_els:
                raise ValueError(('Invalid flaglist element(s) received for {name} property of {parent_name}\n'
                                  '    Invalid elements include: {invalid}\n'  
                                  '{valid_desc}').format(
                    name=self.name,
                    parent_name=self.parent_name,
                    invalid=invalid_els[:10],
                    valid_desc=self.valid_description
                ))

            v = DataArrayValidator.copy_to_contiguous_readonly_numpy_array(v, dtype='unicode')
        else:
            if not isinstance(v, str):
                raise ValueError(("The {name} property of {parent_name} must be a string.\n"
                                  "    Received value of type {typ}").format(name=self.name,
                                                                             parent_name=self.parent_name,
                                                                             typ=type(v)))

            if not self.is_flaglist_valid(v):
                raise ValueError(('Invalid flaglist received for {name} property of {parent_name}\n'
                                  '    Received value: {v}\n'
                                  '{valid_desc}').format(
                    name=self.name,
                    parent_name=self.parent_name,
                    v=repr(v),
                    valid_desc=self.valid_description
                ))

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

        if self.array_ok and DataArrayValidator.is_array(v):
            v = DataArrayValidator.copy_to_contiguous_readonly_numpy_array(v, dtype='object')

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
    def __init__(self, name, parent_name, items, dflt=None, free_length=None):
        super().__init__(name=name, parent_name=parent_name)
        self.items = items

        self.item_validators = []
        for i, item in enumerate(self.items):
            item_validator = InfoArrayValidator.build_validator(item, '{name}[{i}]'.format(name=name, i=i), parent_name)
            self.item_validators.append(item_validator)

        self.default = dflt
        self.free_length = free_length

    @staticmethod
    def build_validator(validator_info, name, parent_name):
        datatype = validator_info['valType']  # type: str
        validator_classname = datatype.title().replace('_', '') + 'Validator'
        validator_class = eval(validator_classname)

        kwargs = {k: validator_info[k] for k in validator_info
                  if k not in ['valType', 'description', 'role']}

        return validator_class(name=name, parent_name=parent_name, **kwargs)

    def validate_coerce(self, v):
        if v is None:
            v = self.default
        elif not isinstance(v, (list, tuple)):
            raise ValueError(('The {name} property of {parent_name} must be a list or tuple.\n'
                              'Received value of type {typ}: {v}').format(name=self.name,
                                                                          parent_name=self.parent_name,
                                                                          typ=type(v),
                                                                          v=v))
        elif not self.free_length and len(v) != len(self.item_validators):
            raise ValueError(('The {name} property of {parent_name} must be a list or tuple of length {N}.\n'
                              'Received a {in_cls} of length {in_N}: {v}').format(name=self.name,
                                                                                  parent_name=self.parent_name,
                                                                                  N=len(self.item_validators),
                                                                                  in_cls=type(v),
                                                                                  in_N=len(v),
                                                                                  v=v))
        else:
            # We have a list or tuple of the correct length
            v = list(v)
            for i, (el, validator) in enumerate(zip(v, self.item_validators)):
                # Validate coerce elements
                v[i] = validator.validate_coerce(el)

        return v


class ImageUriValidator(BaseValidator):
    def __init__(self, name, parent_name):
        super().__init__(name=name, parent_name=parent_name)

    def validate_coerce(self, v):
        if v is None:
            pass
        elif isinstance(v, str):
            # Future possibilities:
            #   - Detect filesystem system paths and convert to URI
            #   - Validate either url or data uri
            pass
        elif isinstance(v, Image.Image):
            # Convert PIL image to png data uri string
            in_mem_file = io.BytesIO()
            v.save(in_mem_file, format="PNG")
            in_mem_file.seek(0)
            img_bytes = in_mem_file.read()
            base64_encoded_result_bytes = base64.b64encode(img_bytes)
            base64_encoded_result_str = base64_encoded_result_bytes.decode('ascii')
            v = f'data:image/png;base64,{base64_encoded_result_str}'
        else:
            raise ValueError(("The {name} property of {parent_name} must be a string or a PIL.image \n"
                              "    Received value of type {typ}: {v}").format(name=self.name,
                                                                              parent_name=self.parent_name,
                                                                              typ=type(v),
                                                                              v=v))
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
        v._prop_name = self.name
        return v


class ArrayValidator(BaseValidator):
    def __init__(self, name, parent_name, element_class):
        super().__init__(name=name, parent_name=parent_name)
        self.data_class = element_class

    def validate_coerce(self, v):
        if v is None:
            v = ()

        elif isinstance(v, (list, tuple)):
            res = []
            for v_el in v:
                if isinstance(v_el, self.data_class):
                    res.append(v_el)
                elif isinstance(v_el, dict):
                    res.append(self.data_class(**v_el))
                else:
                    raise ValueError(("The {name} property of {parent_name} must be a list or tuple "
                                      "of {cls_name} instances.\n"
                                      "Received {col_type} with an instance of type {typ}"
                                      ).format(name=self.name,
                                               parent_name=self.parent_name,
                                               cls_name=self.data_class.__name__,
                                               col_type=type(v),
                                               typ=type(v_el)))
            v = tuple(res)

        elif not isinstance(v, str):
            raise ValueError(("The {name} property of {parent_name} must be a list or tuple "
                              "of {cls_name} instances.\n"
                              "Received value of type {typ}").format(name=self.name,
                                                                     parent_name=self.parent_name,
                                                                     cls_name=self.data_class.__name__,
                                                                     typ=type(v)))

        return v


class BaseTracesValidator:
    def __init__(self, class_map):
        self.class_map = class_map

    def validate_coerce(self, v):

        if v is None:
            v = ()
        elif isinstance(v, (list, tuple)):
            trace_classes = tuple(self.class_map.values())

            res = []
            for v_el in v:
                if isinstance(v_el, trace_classes):
                    res.append(v_el)
                elif isinstance(v_el, dict):
                    if 'type' in v_el:
                        trace_type = v_el.pop('type')
                    else:
                        trace_type = 'scatter'

                    trace = self.class_map[trace_type](**v_el)
                    res.append(trace)
                else:
                    raise ValueError(("The traces property of a Figure must be a list or tuple "
                                      "of traces.\n"
                                      "Received {col_typ} with an instance of type {typ}"
                                      ).format(col_type=type(v),
                                               typ=type(v_el)))
            v = tuple(res)

            # Add UIDs if not set
            for trace in v:
                if trace.uid is None:
                    trace.uid = str(uuid.uuid1())

        elif not isinstance(v, str):
            raise ValueError(("The traces property of a Figure must be a list or tuple "
                              "of traces.\n"
                              "Received value of type {typ}").format(typ=type(v)))

        return v
