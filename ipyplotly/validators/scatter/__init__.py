import ipyplotly.basevalidators as bv
from ipyplotly.datatypes.scatter import Line


class OpacityValidator(bv.NumberValidator):
    def __init__(self):
        super().__init__(name='opacity',
                         parent_name='Scatter',
                         default=1.0,
                         min_val=0.0,
                         max_val=1.0,
                         array_ok=False)


class XValidator(bv.DataArrayValidator):
    def __init__(self):
        super().__init__(name='x',
                         parent_name='Scatter')


class YValidator(bv.DataArrayValidator):
    def __init__(self):
        super().__init__(name='y',
                         parent_name='Scatter')


class NameValidator(bv.StringValidator):
    def __init__(self):
        super().__init__(name='name',
                         parent_name='Scatter',
                         default=None)


class LineValidator(bv.CompoundValidator):
    def __init__(self):
        super().__init__(name='line', parent_name='Scatter', data_class=Line)
        pass
