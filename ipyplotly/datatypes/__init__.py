from ipyplotly.datatypes.trace import *
from ipyplotly.basedatatypes import BaseFigureWidget


# To autogenerate add_trace methods with all properties listed
class Figure(BaseFigureWidget):

    def add_scatter(self,
                    x,
                    y,
                    opacity=1.0,
                    name=None):
        """

        Parameters
        ----------
        x
            The x coordinates
        y
            The y coordinates
        opacity
            The trace opacity
        name
            The trace name
        """
        trace = Scatter(x=x, y=y, opacity=opacity, name=name, parent=self)
        return self._add_trace(trace)
