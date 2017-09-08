from io import StringIO

import json
from yapf.yapflib.yapf_api import FormatCode

def to_pascal_case(s: str):
    return s.title().replace('_', '')


def build_validators_py(parent_name, props_info):

    buffer = StringIO()

    # Imports
    # -------
    buffer.write('import ipyplotly.basevalidators as bv\n')

    # ### Compute compound types
    compound_types = [to_pascal_case(name) for name in props_info
                      if isinstance(props_info[name], dict) and 'valType' not in props_info[name]]
    buffer.write(f'from ipyplotly.datatypes.trace.{parent_name} import {", ".join(compound_types)}')
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
                         parent_name='{parent_name}'""")

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


if __name__ == '__main__':

    with open('resources/plotly-schema-v2.json', 'r') as f:
        plotly_schema = json.load(f)

    parent_name = 'scatter'
    pkg = 'trace'
    props_info = plotly_schema['schema']['traces'][parent_name]['attributes']

    validator_source = build_validators_py(parent_name, props_info)
    formatted_source, _ = FormatCode(validator_source,
                                     style_config={'based_on_style': 'google',
                                                   'DEDENT_CLOSING_BRACKETS': True})
    print(formatted_source)
