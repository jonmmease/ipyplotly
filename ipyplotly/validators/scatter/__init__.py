import ipyplotly.basevalidators as bv
from ipyplotly.datatypes.trace.scatter import *


# class OpacityValidator(bv.NumberValidator):
#     def __init__(self):
#         super().__init__(name='opacity',
#                          parent_name='Scatter',
#                          dflt=1.0,
#                          min=0.0,
#                          max=1.0,
#                          arrayOk=False)
class OpacityValidator(bv.NumberValidator):
    def __init__(self):
        super().__init__(name='opacity',
                         parent_name='Scatter',
                         valType='number',
                         role='style',
                         min=0,
                         max=1,
                         dflt=1,
                         description='Sets the opacity of the trace.')

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
                         dflt=None)


class LineValidator(bv.CompoundValidator):
    def __init__(self):
        super().__init__(name='line',
                         parent_name='Scatter',
                         data_class=Line)
