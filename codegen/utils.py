def to_pascal_case(s: str):
    return s.title().replace('_', '')


def to_undercase(s: str):
    if not s:
        return s

    # Lowercase leading char
    # ----------------------
    s1 = s[0].lower() + s[1:]

    # Replace capital chars by underscore-lower
    # -----------------------------------------
    s2 = ''.join([('' if not c.isupper() else '_') + c.lower() for c in s1])

    return s2


def trace_index(plotly_schema, prop_path):
    props_info = plotly_schema['schema']['traces'][prop_path[0]]['attributes']
    for prop_name in prop_path[1:]:
        props_info = props_info[prop_name]
    return props_info


def is_trace_prop_compound(prop_info):
    return isinstance(prop_info, dict) and 'valType' not in prop_info

def is_trace_prop_simple(prop_info):
    return isinstance(prop_info, dict) and 'valType' in prop_info

def is_trace_prop(prop_info):
    return isinstance(prop_info, dict)


def get_trace_prop_paths(plotly_schema):
    prop_paths = []
    to_process = [[p] for p in plotly_schema['schema']['traces']]

    while to_process:
        prop_path = to_process.pop()
        props_info = trace_index(plotly_schema, prop_path)

        prop_paths.append(prop_path)
        compound_paths = [prop_path + [prop] for prop in props_info if is_trace_prop_compound(props_info[prop])]
        to_process.extend(compound_paths)

    return prop_paths