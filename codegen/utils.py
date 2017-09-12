
class TraceNode:

    @staticmethod
    def get_all_compound_datatype_nodes(plotly_schema):
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
    def name(self):
        if len(self.trace_path) == 0:
            'trace'
        elif len(self.trace_path) == 1:
            # Use {"trace_name": {"meta": {"hrName": "hr_name"}}} if available
            return self.plotly_schema['schema']['traces'][self.trace_path[0]]['meta'].get('hrName', self.trace_path[0])
        else:
            return self.trace_path[-1]

    @property
    def name_pascal_case(self):
        return self.name.title().replace('_', '')

    @property
    def name_undercase(self):
        # Lowercase leading char
        # ----------------------
        name1 = self.name[0].lower() + self.name[1:]

        # Replace capital chars by underscore-lower
        # -----------------------------------------
        name2 = ''.join([('' if not c.isupper() else '_') + c.lower() for c in name1])

        return name2

    @property
    def description(self):
        if len(self.trace_path) == 0:
            return ""
        elif len(self.trace_path) == 1:
            return self.plotly_schema['schema']['traces'][self.trace_path[0]]['meta'].get('description', '')
        else:
            return self.node_data.get('description', '')

    @property
    def datatype(self):
        if self.is_compound:
            return 'compound'
        elif self.is_simple:
            return self.node_data.get('valType')
        else:
            return 'literal'

    @property
    def is_compound(self):
        if len(self.trace_path) < 2:
            return True
        else:
            return isinstance(self.node_data, dict) and self.node_data.get('role', '') == 'object'

    @property
    def is_simple(self):
        return isinstance(self.node_data, dict) and 'valType' in self.node_data

    @property
    def is_datatype(self):
        return self.is_simple or self.is_compound

    @property
    def trace_path_str(self, leading_dot=True):
        return '.'.join(self.trace_path)

    @property
    def parent_path_str(self, leading_dot=True):
        return '.'.join(self.trace_path[:-1])

    @property
    def trace_pkg_str(self):
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
