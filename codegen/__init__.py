import json
import os.path as opath
import shutil

from codegen.datatypes import build_datatypes_py, write_datatypes_py, append_figure_class
from codegen.utils import TraceNode
from codegen.validators import write_validator_py


if __name__ == '__main__':

    # outdir = 'ipyplotly/'
    outdir = 'codegen/output'

    # Load plotly schema
    # ------------------
    with open('codegen/resources/plotly-schema-v2.json', 'r') as f:
        plotly_schema = json.load(f)

    # Compute property paths
    # ----------------------
    compound_nodes = TraceNode.get_all_compound_datatype_nodes(plotly_schema)

    # Write out datatypes
    # -------------------
    datatypes_pkgdir = opath.join(outdir, 'datatypes')
    if opath.exists(datatypes_pkgdir):
        shutil.rmtree(datatypes_pkgdir)

    for node in compound_nodes:
        write_datatypes_py(outdir, node)

    # Append figure class to datatypes
    # --------------------------------
    base_node = TraceNode(plotly_schema)
    append_figure_class(datatypes_pkgdir, base_node)

    # Write out validators
    # --------------------
    validators_pkgdir = opath.join(outdir, 'validators')
    if opath.exists(validators_pkgdir):
        shutil.rmtree(validators_pkgdir)

    for node in compound_nodes:
        write_validator_py(outdir, node)



