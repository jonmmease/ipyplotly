from ipyplotly.valuetypes import Number, String, DataArray
import typing as typ


class Scatter:
    _names = dict(name='opacity', parent_name='scatter')
    _types = {}

    # opacity
    # -------
    _types['opacity'] = Number(**_names, default=1.0, min_val=0.0, max_val=1.0)

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
    _types['x'] = DataArray(**_names)

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
    _types['y'] = DataArray(**_names)

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
    _types['name'] = String(**_names, default=None)

    @property
    def name(self):
        return self._data['name']

    @name.setter
    def name(self, val):
        self._set_prop('name', val)

    def __init__(self,
                 x,
                 y,
                 opacity=1.0,
                 name=None,
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
        # Initialize data dict
        # --------------------
        self._data = {}

        # Init parent to None
        # -------------------
        # Passed value will be set at the end of constructor
        self.parent = None

        # Populate data dict with properties
        # ----------------------------------
        self.x = x
        self.y = y
        self.opacity = opacity
        self.name = name

        # Set parent
        # ----------
        # Do this last so we don't send parent messages before construction
        self.parent = parent

    def _send_restyle(self, prop, val):
        if self.parent:
            send_val = [val] if isinstance(val, list) else val
            self.parent._restyle_child(self, prop, send_val)

    def _set_prop(self, prop, val):
        val = self._types[prop].validate_coerce(val)
        if prop not in self._data or self._data[prop] != val:
            self._data[prop] = val
            self._send_restyle(prop, val)