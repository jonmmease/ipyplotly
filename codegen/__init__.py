from io import StringIO

import json
from yapf.yapflib.yapf_api import FormatCode
import os
import os.path as opath
import shutil

from codegen.datatypes import build_datatypes_py
from codegen.utils import get_trace_prop_paths
from codegen.validators import write_validator_py

if __name__ == '__main__':

    # Create output directory
    # -----------------------
    outdir = 'ipyplotly/'
    if opath.exists(outdir):
        shutil.rmtree(outdir)

    os.mkdir(outdir)

    # Load plotly schema
    # ------------------
    with open('codegen/resources/plotly-schema-v2.json', 'r') as f:
        plotly_schema = json.load(f)

    # Compute property paths
    # ----------------------
    prop_paths = get_trace_prop_paths(plotly_schema)

    # Write out validators
    # --------------------
    for prop_path in prop_paths:
        res = build_datatypes_py(plotly_schema, prop_path)
        print(res)

    # Write out validators
    # --------------------
    # for prop_path in prop_paths:
    #     write_validator_py(outdir, plotly_schema, prop_path)

