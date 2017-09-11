import shutil
from io import StringIO
import os
import os.path as opath
from yapf.yapflib.yapf_api import FormatCode
from codegen.utils import to_pascal_case, to_undercase, trace_index, is_trace_prop, is_trace_prop_compound, \
    is_trace_prop_simple
import textwrap


_plotly_to_pytypes = {
    'data_array': 'typ.List',
    'enumerated': 'str',

}
def get_typing_type(plotly_type, array_ok=False):
    pytype = None
    if plotly_type in ('data_array', 'info_array'):
        pytype = 'List'
    elif plotly_type in ('string', 'color', 'colorscale', 'subplotid'):
        pytype = 'str'
    elif plotly_type in ('enumerated', 'flaglist', 'any'):
        pytype = 'Any'
    elif plotly_type in ('number', 'angle'):
        pytype = 'Number'
    elif plotly_type == 'integer':
        pytype = 'int'
    elif plotly_type == 'boolean':
        pytype = 'bool'
    else:
        raise ValueError('Unknown plotly type: %s' % plotly_type)

    if array_ok:
        return f'Union[{pytype}, List[{pytype}]]'
    else:
        return pytype


def build_datatypes_py(plotly_schema, prop_path):
    buffer = StringIO()

    # Lookup props info
    # -----------------
    props_info = trace_index(plotly_schema, prop_path)

    # Imports
    # -------
    buffer.write('from typing import *\n')
    buffer.write('from numbers import Number\n')
    buffer.write('from ipyplotly.basedatatypes import BaseTraceType\n')

    # ### Validators
    compound_props = [prop for prop in props_info if is_trace_prop_compound(props_info[prop])]
    if compound_props:
        datatypes_csv = ', '.join([p for p in compound_props])
        validators_csv = ', '.join([f'{p} as v_{p}' for p in compound_props])
        buffer.write(f'from ipyplotly.validators.trace.{".".join(prop_path)} import ({validators_csv})\n')
        buffer.write(f'from ipyplotly.datatypes.trace.{".".join(prop_path)} import ({datatypes_csv})\n')

    # Properties loop
    # ---------------
    for prop in props_info:
        prop_info = props_info[prop]
        if not is_trace_prop_compound(prop_info):
            continue

        prop_path_str = '.'.join(prop_path + [prop])

        # ### Class definition ###
        buffer.write(f"""

class {to_pascal_case(prop)}(BaseTraceType):\n""")

        # ### Property definitions ###
        subprops = [p for p in prop_info if is_trace_prop(prop_info[p])]
        compound_subprops = [p for p in prop_info
                             if is_trace_prop_compound(prop_info[p])]
        for subprop in subprops:
            subprop_info = prop_info[subprop]
            under_subprop = to_undercase(subprop)

            if is_trace_prop_compound(subprop_info):
                prop_type = f'{prop}.{to_pascal_case(subprop)}'
            else:
                prop_type = get_typing_type(subprop_info.get('valType'))

            raw_description = subprop_info.get('description', '')
            subprop_description = '\n'.join(textwrap.wrap(raw_description,
                                                          subsequent_indent=' ' * 8,
                                                          width=80 - 8))

            if is_trace_prop_simple(subprop_info):
                buffer.write(f"""\

    # {under_subprop}
    # {'-' * len(under_subprop)}
    @property
    def {under_subprop}(self) -> {prop_type}:
        \"\"\"
        {subprop_description}
        \"\"\"
        return self._data['{under_subprop}']
        
    @{under_subprop}.setter
    def {under_subprop}(self, val):
        self._set_prop('{under_subprop}', val)\n""")

            else:
                buffer.write(f"""\

    # {under_subprop}
    # {'-' * len(under_subprop)}
    @property
    def {under_subprop}(self) -> {prop_type}:
        \"\"\"
        {subprop_description}
        \"\"\"
        return self._{under_subprop}

    @{under_subprop}.setter
    def {under_subprop}(self, val):
        self._{under_subprop} = self._set_compound_prop('{under_subprop}', val, self._{under_subprop})\n""")

        # ### Constructor ###
        buffer.write(f"""
    def __init__(self,""")
        for i, subprop in enumerate(subprops):
            subprop_info = prop_info[subprop]
            under_subprop = to_undercase(subprop)
            dflt = subprop_info.get('dflt', None)
            is_last = i == len(subprops) - 1
            buffer.write(f"""
            {under_subprop}={repr(dflt)}{',' if not is_last else ''} """)
        buffer.write("""
        ):""")

        # ### Docstring ###
        buffer.write(f"""
        \"\"\"
        Construct a new {to_pascal_case(prop)} object
        
        Parameters
        ----------""")
        for i, subprop in enumerate(subprops):
            subprop_info = prop_info[subprop]
            under_subprop = to_undercase(subprop)
            raw_description = subprop_info.get('description', '')
            subprop_description = '\n'.join(textwrap.wrap(raw_description,
                                                          subsequent_indent=' ' * 12,
                                                          width=80 - 12))

            buffer.write(f"""
        {subprop}
            {subprop_description}""")

        # #### close docstring ####
        buffer.write(f"""

        Returns
        -------
        {to_pascal_case(prop)}
        \"\"\"""")

        buffer.write(f"""
        super().__init__('{prop_path_str}')

        # Initialize data dict
        # --------------------
        self._data['type'] = '{prop_path_str}'
        
        # Initialize validators
        # ---------------------""")
        for i, subprop in enumerate(subprops):
            subprop_info = prop_info[subprop]
            under_subprop = to_undercase(subprop)

            buffer.write(f"""
        self._validators['{under_subprop}'] = v_{prop}.{to_pascal_case(subprop)}Validator()""")

        if compound_subprops:
            buffer.write(f"""
        
        # Init compound properties
        # ------------------------""")
            for subprop in compound_subprops:
                under_subprop = to_undercase(subprop)
                buffer.write(f"""
        self._{under_subprop} = None""")

        buffer.write(f"""
        
        # Populate data dict with properties
        # ----------------------------------""")
        for i, subprop in enumerate(subprops):
            subprop_info = prop_info[subprop]
            under_subprop = to_undercase(subprop)
            buffer.write(f"""
        self.{under_subprop} = {under_subprop}""")

    return buffer.getvalue()


def write_datatypes_py(outdir, plotly_schema, prop_path):

    # Generate source code
    # --------------------
    datatype_source = build_datatypes_py(plotly_schema, prop_path)

    formatted_source, _ = FormatCode(datatype_source,
                                     style_config={'based_on_style': 'google',
                                                   'DEDENT_CLOSING_BRACKETS': True})

    # Write file
    # ----------
    filedir = opath.join(outdir, 'datatypes', 'trace', *prop_path)
    filepath = opath.join(filedir, '__init__.py')

    os.makedirs(filedir, exist_ok=True)
    with open(filepath, 'wt') as f:
        f.write(formatted_source)



