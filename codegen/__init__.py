import mako
from mako.template import Template

from mako.template import Template
from mako.lookup import TemplateLookup

import json

def to_pascal_case(s: str):
    return s.title().replace('_', '')


if __name__ == '__main__':
    lookup = TemplateLookup(directories=['templates'])
    template = lookup.get_template('validators/validator.mako')

    with open('resources/plotly-schema-v2.json', 'r') as f:
        plotly_schema = json.load(f)

    name = 'opacity'
    trace_type = 'scatter'
    params = plotly_schema['schema']['traces'][trace_type]['attributes'][name]

    kwargs = {'name': name,
              'base': params['valType'],
              'parent_name': trace_type,
              'params': params}
    print(template.render(**kwargs))


    # Notes: Build mapping from json names to python names (dflt -> default, freeLength -> free_length, arrayOk ->
    # array_ok)
    #        Validator constructors ignore extra parameters
    #
    # construct validator from all json params
    # "showticklabels": {
    #     "valType": "enumerated",
    #     "values": [
    #         "start",
    #         "end",
    #         "both",
    #         "none"
    #     ],
    #     "dflt": "start",
    #     "role": "style",
    #     "description": "Determines whether axis labels are drawn on the low side, the high side, both, or neither side of the axis."
    # },
