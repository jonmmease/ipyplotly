from io import StringIO

import json
from yapf.yapflib.yapf_api import FormatCode
import os
import os.path as opath
import shutil

def to_pascal_case(s: str):
    return s.title().replace('_', '')


def build_validators_py(prop_path, props_info):

    buffer = StringIO()
    prop_path_str = '.'.join(prop_path)

    # Imports
    # -------
    buffer.write('import ipyplotly.basevalidators as bv\n')

    # ### Compute compound types
    compound_types = [to_pascal_case(name) for name in props_info
                      if isinstance(props_info[name], dict) and 'valType' not in props_info[name]]
    if compound_types:
        buffer.write(f'from ipyplotly.datatypes.trace.{prop_path_str} import {", ".join(compound_types)}')
    buffer.write('\n\n')
    # Validator classes
    # -----------------
    for name, prop_info in props_info.items():
        if not isinstance(prop_info, dict):
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

    # Lookup props info
    # -----------------
    props_info = trace_index(plotly_schema, prop_path)

    # Generate source code
    # --------------------
    validator_source = build_validators_py(prop_path, props_info)
    formatted_source, _ = FormatCode(validator_source,
                                     style_config={'based_on_style': 'google',
                                                   'DEDENT_CLOSING_BRACKETS': True})

    # Write file
    # ----------
    filedir = opath.join(outdir, 'validators', *prop_path)
    filepath = opath.join(filedir, '__init__.py')
    os.makedirs(filedir, exist_ok=True)
    with open(filepath, 'wt') as f:
        f.write(formatted_source)


def trace_index(plotly_schema, prop_path):
    props_info = plotly_schema['schema']['traces'][prop_path[0]]['attributes']
    for prop_name in prop_path[1:]:
        props_info = props_info[prop_name]
    return props_info


def is_trace_prop_compound(prop_info):
    return isinstance(prop_info, dict) and 'valType' not in prop_info


def get_trace_prop_paths(plotly_schema):
    prop_paths = []
    to_process = [[p] for p in plotly_schema['schema']['traces']]

    while to_process:
        prop_path = to_process.pop()
        props_info = trace_index(plotly_schema, prop_path)

        prop_paths.append(prop_path)
        compound_paths = [prop_path + [prop] for prop in props_info if is_trace_prop_compound(props_info[prop])]
        to_process.extend(compound_paths)

    return prop_paths

if __name__ == '__main__':

    # Create output directory
    # -----------------------
    outdir = 'output/'
    if opath.exists(outdir):
        shutil.rmtree(outdir)

    os.mkdir(outdir)

    # Load plotly schema
    # ------------------
    with open('resources/plotly-schema-v2.json', 'r') as f:
        plotly_schema = json.load(f)

    # Compute property paths
    # ----------------------
    prop_paths = get_trace_prop_paths(plotly_schema)

    # Write out validators
    # --------------------
    for prop_path in prop_paths:
        write_validator_py(outdir, plotly_schema, prop_path)

