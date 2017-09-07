import typing as typ

from ipyplotly.basedatatypes import BaseTraceType
from ipyplotly.validators.scatter import OpacityValidator, XValidator, YValidator, NameValidator, LineValidator


class Scatter(BaseTraceType):

    # opacity
    # -------
    @property
    def opacity(self) -> float:
        """
        The opacity of the trace
        Returns
        -------
        float:
            The opacity of the trace
        """
        return self._data['opacity']

    @opacity.setter
    def opacity(self, val):
        # Validate type
        self._set_prop('opacity', val)

    # x
    # -
    @property
    def x(self) -> typ.List:
        """
        The x coordinates
        Returns
        -------
        list:
            The x coordinates
        """
        return self._data['x']

    @x.setter
    def x(self, val):
        self._set_prop('x', val)

    # y
    # -
    @property
    def y(self) -> typ.List:
        """
        The y coordinates
        Returns
        -------
        list:
            The y coordinates
        """
        return self._data['y']

    @y.setter
    def y(self, val):
        self._set_prop('y', val)

    # name
    # ----
    @property
    def name(self):
        return self._data['name']

    @name.setter
    def name(self, val):
        self._set_prop('name', val)

    # line
    # ----
    @property
    def line(self):
        return self._line

    @line.setter
    def line(self, val):
        new_line = self._set_prop('line', val)

        # TODO: make separate _set_prop method for compound props that handles parenting
        curr_line = self._line
        if curr_line is not None and curr_line is not new_line:
            # Unparent current line
            curr_line.parent = None

        self._line = new_line

    def __init__(self,
                 x,
                 y,
                 opacity=1.0,
                 name=None,
                 line=None,
                 parent=None):
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

        super().__init__('scatter')

        # Initialize data dict
        # --------------------
        self._data['type'] = 'scatter'

        # Initialize validators
        # ---------------------
        self._validators['opacity'] = OpacityValidator()
        self._validators['x'] = XValidator()
        self._validators['y'] = YValidator()
        self._validators['name'] = NameValidator()
        self._validators['line'] = LineValidator()

        # Init compound prop properties
        # -----------------------------
        self._line = None

        # Populate data dict with properties
        # ----------------------------------
        self.x = x
        self.y = y
        self.opacity = opacity
        self.name = name
        self.line = line

        # Set parent
        # ----------
        # Do this last so we don't send parent messages before construction
        self.parent = parent
