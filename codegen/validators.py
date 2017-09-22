import os
import os.path as opath
import shutil
from io import StringIO
from codegen.utils import format_source, PlotlyNode
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



