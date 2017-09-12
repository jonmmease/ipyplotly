import shutil
from io import StringIO
import os
import os.path as opath
from typing import List

from yapf.yapflib.yapf_api import FormatCode
from codegen.utils import to_pascal_case, to_undercase, trace_index, is_trace_prop, is_trace_prop_compound, \
    is_trace_prop_simple, TraceNode
import textwrap

def get_typing_type(plotly_type, array_ok=False):
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


def build_datatypes_py(parent_node: TraceNode):

    buffer = StringIO()

    # Imports
    # -------
    buffer.write('from typing import *\n')
    buffer.write('from numbers import Number\n')
    buffer.write('from ipyplotly.basedatatypes import BaseTraceType\n')

    compound_nodes = parent_node.child_compound_datatypes

    if compound_nodes:
        datatypes_csv = ', '.join([n.name for n in compound_nodes])
        validators_csv = ', '.join([f'{n.name} as v_{n.name}' for n in compound_nodes])

        buffer.write(f'from ipyplotly.validators.trace{parent_node.trace_pkg_str} import ({validators_csv})\n')
        buffer.write(f'from ipyplotly.datatypes.trace{parent_node.trace_pkg_str} import ({datatypes_csv})\n')

    # Properties loop
    # ---------------
    for compound_node in compound_nodes:

        # ### Class definition ###
        buffer.write(f"""

class {compound_node.name_pascal_case}(BaseTraceType):\n""")

        # ### Property definitions ###
        for subtype_node in compound_node.child_datatypes:
            if subtype_node.is_compound:
                prop_type = f'{compound_node.name}.{subtype_node.name_pascal_case}'
            else:
                prop_type = get_typing_type(subtype_node.datatype)

            raw_description = subtype_node.description

            subtype_description = '\n'.join(textwrap.wrap(raw_description,
                                                          subsequent_indent=' ' * 8,
                                                          width=119 - 8))
            under_name = subtype_node.name_undercase
            if subtype_node.is_simple:
                buffer.write(f"""\

    # {under_name}
    # {'-' * len(under_name)}
    @property
    def {under_name}(self) -> {prop_type}:
        \"\"\"
        {subtype_description}
        \"\"\"
        return self._data['{under_name}']
        
    @{under_name}.setter
    def {under_name}(self, val):
        self._set_prop('{under_name}', val)\n""")

            else:
                buffer.write(f"""\

    # {under_name}
    # {'-' * len(under_name)}
    @property
    def {under_name}(self) -> {prop_type}:
        \"\"\"
        {subtype_description}
        \"\"\"
        return self._{under_name}

    @{under_name}.setter
    def {under_name}(self, val):
        self._{under_name} = self._set_compound_prop('{under_name}', val, self._{under_name})\n""")

        # ### Constructor ###
        buffer.write(f"""
    def __init__(self,""")
        for i, subtype_node in enumerate(compound_node.child_datatypes):
            under_name = subtype_node.name_undercase
            dflt = subtype_node.node_data.get('dflt', None)
            is_last = i == len(compound_node.child_datatypes) - 1
            buffer.write(f"""
            {under_name}={repr(dflt)}{',' if not is_last else ''} """)
        buffer.write("""
        ):""")

        # ### Docstring ###
        buffer.write(f"""
        \"\"\"
        Construct a new {compound_node.name_pascal_case} object
        
        Parameters
        ----------""")
        for subtype_node in compound_node.child_datatypes:
            under_name = subtype_node.name_undercase
            raw_description = subtype_node.description
            subtype_description = '\n'.join(textwrap.wrap(raw_description,
                                                          subsequent_indent=' ' * 12,
                                                          width=119 - 12))

            buffer.write(f"""
        {under_name}
            {subtype_description}""")

        # #### close docstring ####
        buffer.write(f"""

        Returns
        -------
        {compound_node.name_pascal_case}
        \"\"\"""")

        buffer.write(f"""
        super().__init__('{compound_node.parent_path_str}')

        # Initialize data dict
        # --------------------
        self._data['type'] = '{compound_node.trace_path_str}'
        
        # Initialize validators
        # ---------------------""")
        for subtype_node in compound_node.child_datatypes:
            under_name = subtype_node.name_undercase

            buffer.write(f"""
        self._validators['{under_name}'] = v_{compound_node.name}.{subtype_node.name_pascal_case}Validator()""")

        compound_subtype_nodes = compound_node.child_compound_datatypes
        if compound_subtype_nodes:
            buffer.write(f"""
        
        # Init compound properties
        # ------------------------""")
            for compound_subtype_node in compound_subtype_nodes:
                under_name = compound_subtype_node.name_undercase
                buffer.write(f"""
        self._{under_name} = None""")

        buffer.write(f"""
        
        # Populate data dict with properties
        # ----------------------------------""")
        for subtype_node in compound_node.child_datatypes:
            under_name = subtype_node.name_undercase
            buffer.write(f"""
        self.{under_name} = {under_name}""")

    return buffer.getvalue()


def write_datatypes_py(outdir, node: TraceNode):

    # Generate source code
    # --------------------
    datatype_source = build_datatypes_py(node)

    formatted_source, _ = FormatCode(datatype_source,
                                     style_config={'based_on_style': 'google',
                                                   'DEDENT_CLOSING_BRACKETS': True})

    # Write file
    # ----------
    filedir = opath.join(outdir, 'datatypes', 'trace', *node.trace_path)
    filepath = opath.join(filedir, '__init__.py')

    os.makedirs(filedir, exist_ok=True)
    with open(filepath, 'wt') as f:
        f.write(formatted_source)



