import os
import os.path as opath
import shutil
from io import StringIO
from yapf.yapflib.yapf_api import FormatCode

from codegen.utils import to_pascal_case, trace_index, is_trace_prop_compound, is_trace_prop


def build_validators_py(plotly_schema, prop_path):
    buffer = StringIO()

    # Lookup props info
    # -----------------
    props_info = trace_index(plotly_schema, prop_path)
    prop_path_str = '.'.join(prop_path)

    # Imports
    # -------
    buffer.write('import ipyplotly.basevalidators as bv\n')

    # ### Compute compound types
    compound_types = [to_pascal_case(name) for name in props_info
                      if is_trace_prop_compound(props_info[name])]

    if compound_types:
        buffer.write(f'from ipyplotly.datatypes.trace.{prop_path_str} import ({", ".join(compound_types)})')
    buffer.write('\n\n')

    # Validator classes
    # -----------------
    for name, prop_info in props_info.items():
        if not is_trace_prop(prop_info):
            continue

        base = prop_info.get('valType', 'compound')
        attr_names = [k for k in prop_info if k not in ['valType', 'description', 'role']]

        buffer.write(f"""\
class {to_pascal_case(name)}Validator(bv.{to_pascal_case(base)}Validator):
    def __init__(self):
        super().__init__(name='{name}',
                         parent_name='{prop_path_str}'""")

        if base == 'compound':
            buffer.write(f""",
                         data_class={to_pascal_case(name)}""")
        else:
            for i, attr_name in enumerate(attr_names):
                is_last = i == len(attr_names) - 1
                buffer.write(f""",
                         {attr_name}={repr(prop_info[attr_name])}""")
        buffer.write(')')
        buffer.write('\n\n')

    return buffer.getvalue()


def write_validator_py(outdir, plotly_schema, prop_path):

    # Generate source code
    # --------------------
    validator_source = build_validators_py(plotly_schema, prop_path)

    formatted_source, _ = FormatCode(validator_source,
                                     style_config={'based_on_style': 'google',
                                                   'DEDENT_CLOSING_BRACKETS': True})

    # Write file
    # ----------
    filedir = opath.join(outdir, 'validators', 'trace', *prop_path)

    # ### Create output directory
    if opath.exists(filedir):
        shutil.rmtree(filedir)
    os.makedirs(filedir)

    filepath = opath.join(filedir, '__init__.py')
    os.makedirs(filedir, exist_ok=True)
    with open(filepath, 'wt') as f:
        f.write(formatted_source)



