import json
import os.path as opath
import shutil

from codegen.datatypes import build_datatypes_py, write_datatypes_py, append_figure_class
from codegen.utils import TraceNode, PlotlyNode, LayoutNode
from codegen.validators import write_validator_py, append_traces_validator_py


def perform_codegen():
    outdir = 'ipyplotly/'
    # outdir = 'codegen/output'
    # Load plotly schema
    # ------------------
    with open('../plotly.js/dist/plot-schema.json', 'r') as f:
        plotly_schema = json.load(f)

    # Compute property paths
    # ----------------------
    compound_trace_nodes = PlotlyNode.get_all_compound_datatype_nodes(plotly_schema, TraceNode)
    compound_layout_nodes = PlotlyNode.get_all_compound_datatype_nodes(plotly_schema, LayoutNode)
    extra_layout_nodes = PlotlyNode.get_all_trace_layout_nodes(plotly_schema)
    # Write out validators
    # --------------------
    validators_pkgdir = opath.join(outdir, 'validators')
    if opath.exists(validators_pkgdir):
        shutil.rmtree(validators_pkgdir)
    for node in compound_layout_nodes:
        write_validator_py(outdir, node, extra_layout_nodes)
    for node in compound_trace_nodes:
        write_validator_py(outdir, node)

    # Write out datatypes
    # -------------------
    datatypes_pkgdir = opath.join(outdir, 'datatypes')
    if opath.exists(datatypes_pkgdir):
        shutil.rmtree(datatypes_pkgdir)
    for node in compound_layout_nodes:
        write_datatypes_py(outdir, node, extra_layout_nodes)
    for node in compound_trace_nodes:
        write_datatypes_py(outdir, node)

    # Append figure class to datatypes
    # --------------------------------
    base_node = TraceNode(plotly_schema)
    append_figure_class(datatypes_pkgdir, base_node)
    # Append traces validator class
    # -----------------------------
    append_traces_validator_py(validators_pkgdir, base_node)


if __name__ == '__main__':
    perform_codegen()
