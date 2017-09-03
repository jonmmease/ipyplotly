from ipyplotly.datatypes import BaseDataType
from ipyplotly.validators.scatter.line import *


class Line(BaseDataType):

    # color
    # -----
    @property
    def color(self) -> float:
        return self._data['color']

    @color.setter
    def color(self, val):
        self._set_prop('color', val)

    # width
    # -----
    @property
    def width(self) -> float:
        return self._data['width']

    @width.setter
    def width(self, val):
        # Validate type
        self._set_prop('width', val)

    def __init__(self,
                 color=None,
                 width=2,
                 parent=None):

        """

        Parameters
        ----------
        color
        width
        """
        super().__init__('line')

        # Initialize validators
        # ---------------------
        self._validators['color'] = ColorValidator()
        self._validators['width'] = WidthValidator()

        # Populate data dict with properties
        # ----------------------------------
        self.color = color
        self.width = width

        # Set parent
        # ----------
        # Do this last so we don't send parent messages before construction
        self.parent = parent
