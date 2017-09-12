from io import StringIO
import os
import os.path as opath
import textwrap

from codegen.utils import TraceNode, format_source


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
    buffer.write('from ipyplotly.basedatatypes import (BaseTraceType, BaseFigureWidget)\n')

    compound_nodes = parent_node.child_compound_datatypes

    if compound_nodes:
        datatypes_csv = ', '.join([f'{n.name} as d_{n.name}' for n in compound_nodes])
        validators_csv = ', '.join([f'{n.name} as v_{n.name}' for n in compound_nodes])

        buffer.write(f'from ipyplotly.validators.trace{parent_node.trace_pkg_str} import ({validators_csv})\n')
        buffer.write(f'from ipyplotly.datatypes.trace{parent_node.trace_pkg_str} import ({datatypes_csv})\n')

    # Compound datatypes loop
    # -----------------------
    for compound_node in compound_nodes:

        # ### Class definition ###
        buffer.write(f"""

class {compound_node.name_pascal_case}(BaseTraceType):\n""")

        # ### Property definitions ###
        for subtype_node in compound_node.child_datatypes:
            if subtype_node.is_compound:
                prop_type = f'd_{compound_node.name}.{subtype_node.name_pascal_case}'
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
    def __init__(self""")

        add_constructor_params(buffer, compound_node)
        add_docstring(buffer, compound_node)

        buffer.write(f"""
        super().__init__('{compound_node.name}')

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


def add_constructor_params(buffer, compound_node, colon=True):
    for i, subtype_node in enumerate(compound_node.child_datatypes):
        under_name = subtype_node.name_undercase
        dflt = subtype_node.node_data.get('dflt', None)
        is_last = i == len(compound_node.child_datatypes) - 1
        buffer.write(f""",
            {under_name}={repr(dflt)}""")
    buffer.write(f"""
        ){':' if colon else ''}""")


def add_docstring(buffer, compound_node):
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


def write_datatypes_py(outdir, node: TraceNode):

    # Generate source code
    # --------------------
    datatype_source = build_datatypes_py(node)
    formatted_source = format_source(datatype_source)

    # Write file
    # ----------
    filedir = opath.join(outdir, 'datatypes', 'trace', *node.trace_path)
    filepath = opath.join(filedir, '__init__.py')

    os.makedirs(filedir, exist_ok=True)
    with open(filepath, 'wt') as f:
        f.write(formatted_source)


def build_figure_py(base_node: TraceNode):
    buffer = StringIO()
    trace_nodes = base_node.child_compound_datatypes

    # Imports
    # -------
    buffer.write('from ipyplotly.basedatatypes import BaseFigureWidget\n')

    trace_types_csv = ', '.join([n.name_pascal_case for n in trace_nodes])
    buffer.write(f'from ipyplotly.datatypes.trace import ({trace_types_csv})\n')

    buffer.write("""
    
class Figure(BaseFigureWidget):\n""")

    for trace_node in trace_nodes:

        # Function signature
        # ------------------
        buffer.write(f"""
    def add_{trace_node.name}(self""")

        add_constructor_params(buffer, trace_node)
        add_docstring(buffer, trace_node)

        # Function body
        # -------------
        buffer.write(f"""
        new_trace = {trace_node.name_pascal_case}(
        """)

        for i, subtype_node in enumerate(trace_node.child_datatypes):
            under_name = subtype_node.name_undercase
            is_last = i == len(trace_node.child_datatypes) - 1
            buffer.write(f"""
                {under_name}={under_name}{'' if is_last else ','}""")

        buffer.write(f"""
            )""")

        buffer.write(f"""
        new_trace.parent = self
        return self._add_trace(new_trace)""")

    buffer.write('\n')
    return buffer.getvalue()


def append_figure_class(outdir, base_node: TraceNode):

    if base_node.trace_path:
        raise ValueError('Expected root trace node. Received node with path "%s"' % base_node.trace_path_str)

    figure_source = build_figure_py(base_node)
    formatted_source = format_source(figure_source)

    # Append to file
    # --------------
    filepath = opath.join(outdir, '__init__.py')

    with open(filepath, 'w') as f:
        f.write(formatted_source)

