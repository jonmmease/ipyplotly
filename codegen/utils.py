from typing import List
from yapf.yapflib.yapf_api import FormatCode


def format_source(validator_source):
    formatted_source, _ = FormatCode(validator_source,
                                     style_config={'based_on_style': 'google',
                                                   'DEDENT_CLOSING_BRACKETS': True,
                                                   'COLUMN_LIMIT': 119})
    return formatted_source


class TraceNode:

    @staticmethod
    def get_all_compound_datatype_nodes(plotly_schema) -> List['TraceNode']:
        nodes = []
        nodes_to_process = [TraceNode(plotly_schema)]

        while nodes_to_process:
            node = nodes_to_process.pop()
            nodes.append(node)
            nodes_to_process.extend(node.child_compound_datatypes)

        return nodes

    def __init__(self, plotly_schema, trace_path=()):
        self.plotly_schema = plotly_schema
        if isinstance(trace_path, str):
            trace_path = (trace_path,)
        self.trace_path = trace_path

        # Compute children
        if self.is_datatype:
            self._children = [TraceNode(self.plotly_schema, self.trace_path + (c,)) for c in self.node_data]
        else:
            self._children = []

    @property
    def node_data(self) -> dict:
        if not self.trace_path:
            node_data = self.plotly_schema['schema']['traces']
        else:
            node_data = self.plotly_schema['schema']['traces'][self.trace_path[0]]['attributes']
            for prop_name in self.trace_path[1:]:
                node_data = node_data[prop_name]

        return node_data

    @property
    def name(self) -> str:
        if len(self.trace_path) == 0:
            'trace'
        else:
            return self.trace_path[-1]

    @property
    def name_pascal_case(self) -> str:
        return self.name.title().replace('_', '')

    @property
    def name_undercase(self) -> str:
        # Lowercase leading char
        # ----------------------
        name1 = self.name[0].lower() + self.name[1:]

        # Replace capital chars by underscore-lower
        # -----------------------------------------
        name2 = ''.join([('' if not c.isupper() else '_') + c.lower() for c in name1])

        return name2

    @property
    def description(self) -> str:
        if len(self.trace_path) == 0:
            return ""
        elif len(self.trace_path) == 1:
            return self.plotly_schema['schema']['traces'][self.trace_path[0]]['meta'].get('description', '')
        else:
            return self.node_data.get('description', '')

    @property
    def datatype(self) -> str:
        if self.is_compound:
            return 'compound'
        elif self.is_simple:
            return self.node_data.get('valType')
        else:
            return 'literal'

    @property
    def datatype_pascal_case(self) -> str:
        return self.datatype.title().replace('_', '')

    @property
    def is_compound(self) -> bool:
        if len(self.trace_path) < 2:
            return True
        else:
            return isinstance(self.node_data, dict) and self.node_data.get('role', '') == 'object'

    @property
    def is_simple(self) -> bool:
        return isinstance(self.node_data, dict) and 'valType' in self.node_data

    @property
    def is_datatype(self) -> bool:
        return self.is_simple or self.is_compound

    @property
    def trace_path_str(self) -> str:
        return '.'.join(self.trace_path)

    @property
    def parent_path_str(self) -> str:
        return '.'.join(self.trace_path[:-1])

    @property
    def trace_pkg_str(self) -> str:
        path_str = ''
        for p in self.trace_path:
            path_str += '.' + p
        return path_str

    @property
    def simple_attrs(self) -> List['TraceNode']:
        if not self.is_simple:
            raise ValueError(f"Cannot get simple attributes trace object '{self.trace_path_str}'")

        return [n for n in self.children if n.name not in ['valType', 'description', 'role']]

    @property
    def children(self) -> List['TraceNode']:
        return self._children

    @property
    def child_datatypes(self) -> List['TraceNode']:
        """
        Returns
        -------
        children: list of TraceNode
        """
        return [n for n in self.children if n.is_datatype]

    @property
    def child_compound_datatypes(self) -> List['TraceNode']:
        """
        Returns
        -------
        children: list of TraceNode
        """
        return [n for n in self.children if n.is_compound]

    @property
    def child_simple_datatypes(self) -> List['TraceNode']:
        """
        Returns
        -------
        children: list of TraceNode
        """
        return [n for n in self.children if n.is_simple]