import os
import os.path as opath
import shutil
from io import StringIO
from codegen.utils import TraceNode, format_source
import textwrap

def build_validators_py(parent_node: TraceNode):
    buffer = StringIO()

    # Imports
    # -------
    buffer.write('import ipyplotly.basevalidators as bv\n')

    # Compound datatypes loop
    # -----------------------
    datatype_nodes = parent_node.child_datatypes
    for datatype_node in datatype_nodes:

        buffer.write(f"""
        
class {datatype_node.name_pascal_case}Validator(bv.{datatype_node.datatype_pascal_case}Validator):
    def __init__(self):""")

        # Add import
        if datatype_node.is_compound:
            buffer.write(f"""
        from ipyplotly.datatypes.trace{parent_node.trace_pkg_str} import {datatype_node.name_pascal_case}""")

        buffer.write(f"""
        super().__init__(name='{datatype_node.name}',
                         parent_name='{datatype_node.parent_path_str}'""")

        if datatype_node.is_compound:
            buffer.write(f""",
                         data_class={datatype_node.name_pascal_case}""")
        else:
            assert datatype_node.is_simple

            attr_nodes = [n for n in datatype_node.simple_attrs
                          if n.name not in ['valType', 'description', 'role']]
            for i, attr_node in enumerate(attr_nodes):
                is_last = i == len(attr_nodes) - 1
                buffer.write(f""",
                         {attr_node.name_undercase}={repr(attr_node.node_data)}""")

        buffer.write(')')

    return buffer.getvalue()


def write_validator_py(outdir, node: TraceNode):

    # Generate source code
    # --------------------
    validator_source = build_validators_py(node)

    formatted_source = format_source(validator_source)

    # Write file
    # ----------
    filedir = opath.join(outdir, 'validators', 'trace', *node.trace_path)

    # ### Create output directory
    if opath.exists(filedir):
        shutil.rmtree(filedir)
    os.makedirs(filedir)

    filepath = opath.join(filedir, '__init__.py')
    os.makedirs(filedir, exist_ok=True)
    with open(filepath, 'wt') as f:
        f.write(formatted_source)


