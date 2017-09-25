import os
import os.path as opath
import shutil
from io import StringIO
from codegen.utils import format_source, PlotlyNode, TraceNode
import textwrap

def build_validators_py(parent_node: PlotlyNode):
    datatype_nodes = parent_node.child_datatypes
    if not datatype_nodes:
        return None

    buffer = StringIO()

    # Imports
    # -------
    buffer.write('import ipyplotly.basevalidators as bv\n')

    # Compound datatypes loop
    # -----------------------
    for datatype_node in datatype_nodes:

        buffer.write(f"""
        
class {datatype_node.name_validator}(bv.{datatype_node.datatype_pascal_case}Validator):
    def __init__(self):""")

        # Add import
        if datatype_node.is_compound:
            buffer.write(f"""
        from ipyplotly.datatypes{parent_node.pkg_str} import {datatype_node.name_pascal_case}""")

        buffer.write(f"""
        super().__init__(name='{datatype_node.name_property}',
                         parent_name='{datatype_node.parent_dir_str}'""")

        if datatype_node.is_array_element:
            buffer.write(f""",
                         element_class={datatype_node.name_class}""")
        elif datatype_node.is_compound:
            buffer.write(f""",
                         data_class={datatype_node.name_class}""")
        else:
            assert datatype_node.is_simple

            attr_nodes = [n for n in datatype_node.simple_attrs
                          if n.name not in ['valType', 'description', 'role', 'dflt']]
            for i, attr_node in enumerate(attr_nodes):
                buffer.write(f""",
                         {attr_node.name_undercase}={repr(attr_node.node_data)}""")

        buffer.write(')')

    return buffer.getvalue()


def write_validator_py(outdir, node: PlotlyNode):

    # Generate source code
    # --------------------
    validator_source = build_validators_py(node)
    if validator_source:
        formatted_source = format_source(validator_source)

        # Write file
        # ----------
        filedir = opath.join(outdir, 'validators', *node.dir_path)

        # ### Create output directory
        if opath.exists(filedir):
            shutil.rmtree(filedir)
        os.makedirs(filedir)

        filepath = opath.join(filedir, '__init__.py')
        os.makedirs(filedir, exist_ok=True)
        with open(filepath, 'wt') as f:
            f.write(formatted_source)


def build_traces_validator_py(base_node: TraceNode):
    tracetype_nodes = base_node.child_compound_datatypes
    buffer = StringIO()

    import_csv = ', '.join([tracetype_node.name_class for tracetype_node in tracetype_nodes])

    buffer.write(f"""
class TracesValidator(bv.BaseTracesValidator):

    def __init__(self):
        from ipyplotly.datatypes import ({import_csv})
        super().__init__(class_map={{
    """)

    for i, tracetype_node in enumerate(tracetype_nodes):
        sfx = ',' if i < len(tracetype_nodes) else ''

        buffer.write(f"""
            '{tracetype_node.name_property}': {tracetype_node.name_class}{sfx}""")

    buffer.write("""
        })""")

    return buffer.getvalue()


def append_traces_validator_py(outdir, base_node: TraceNode):

    if base_node.trace_path:
        raise ValueError('Expected root trace node. Received node with path "%s"' % base_node.dir_str)

    source = build_traces_validator_py(base_node)
    formatted_source = format_source(source)

    # Append to file
    # --------------
    filepath = opath.join(outdir, '__init__.py')

    with open(filepath, 'a') as f:
        f.write('\n\n')
        f.write(formatted_source)
