import shutil
from io import StringIO
import os
import os.path as opath
from yapf.yapflib.yapf_api import FormatCode
from codegen.utils import to_pascal_case, to_undercase, trace_index, is_trace_prop, is_trace_prop_compound, \
    is_trace_prop_simple
import textwrap

# Not working. Need to rework what is passed in here
def build_datatypes_py(plotly_schema, prop_path):
    buffer = StringIO()

    # Lookup props info
    # -----------------
    props_info = trace_index(plotly_schema, prop_path)

    # Imports
    # -------
    buffer.write('import typing as typ\n')
    buffer.write('from ipyplotly.basedatatypes import BaseTraceType\n')

    # ### Validators
    for prop in props_info:
        prop_info = props_info[prop]
        if not is_trace_prop_compound(prop_info):
            continue
        validator_types = [f'{to_pascal_case(subprop)}Validator' for subprop in prop_info
                           if is_trace_prop(prop_info[subprop])]
        prop_path_str = '.'.join(prop_path + [prop])
        if validator_types:
            buffer.write(f'from ipyplotly.validators.trace.{prop_path_str} import ({", ".join(validator_types)})\n')

    # Properties loop
    # ---------------
    for prop in props_info:
        prop_info = props_info[prop]
        if not is_trace_prop_compound(prop_info):
            continue

        # ### Class definition ###
        buffer.write(f"""

class {to_pascal_case(prop)}(BaseTraceType):\n""")

        # ### Property definitions ###
        subprops = [p for p in prop_info if is_trace_prop(prop_info[p])]
        for subprop in subprops:
            subprop_info = prop_info[subprop]
            under_subprop = to_undercase(subprop)
            prop_type = 'typ.Any'
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
        ):
        pass""")

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



