from io import StringIO

import json
from yapf.yapflib.yapf_api import FormatCode
import os
import os.path as opath
import shutil

from codegen.datatypes import build_datatypes_py, write_datatypes_py
from codegen.utils import get_trace_prop_paths
from codegen.validators import write_validator_py

if __name__ == '__main__':

    outdir = 'ipyplotly/'

    # Load plotly schema
    # ------------------
    with open('codegen/resources/plotly-schema-v2.json', 'r') as f:
        plotly_schema = json.load(f)

    # Compute property paths
    # ----------------------
    prop_paths = get_trace_prop_paths(plotly_schema)

    # Write out datatypes
    # -------------------
    filedir = opath.join(outdir, 'datatypes')
    if opath.exists(filedir):
        shutil.rmtree(filedir)

    for prop_path in prop_paths:
        write_datatypes_py(outdir, plotly_schema, prop_path)

    # Write out validators
    # --------------------
    filedir = opath.join(outdir, 'validators')
    if opath.exists(filedir):
        shutil.rmtree(filedir)

    for prop_path in prop_paths:
        write_validator_py(outdir, plotly_schema, prop_path)

