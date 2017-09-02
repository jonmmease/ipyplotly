from ipyplotly.validators import Number, String, DataArray, Color
import typing as typ


class Scatter:
    _types = {}

    # opacity
    # -------
    _types['opacity'] = Number(name='opacity', parent_name='Scatter', default=1.0, min_val=0.0, max_val=1.0)

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
    _types['x'] = DataArray(name='x', parent_name='Scatter')

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
    _types['y'] = DataArray(name='y', parent_name='Scatter')

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
    _types['name'] = String(name='name', parent_name='Scatter', default=None)

    @property
    def name(self):
        return self._data['name']

    @name.setter
    def name(self, val):
        self._set_prop('name', val)

    # line
    # ----
    # TODO: validate line
    # _types['line'] = Line(name='name', parent_name='Scatter')

    @property
    def line(self):
        return self._line

    @line.setter
    def line(self, val):
        if val:
            self._line = val
            self._set_prop('line', val._data)

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
        # Initialize data dict
        # --------------------
        self._data = {'type': 'scatter'}

        # Init parent to None
        # -------------------
        # Passed value will be set at the end of constructor
        self.parent = None

        # Init compound prop properties
        # -----------------------------
        self._line = None

        # Populate data dict with properties
        # ----------------------------------
        self.x = x
        self.y = y
        self.opacity = opacity
        self.name = name
        self.line = line if line else Line(parent=self)

        # Set parent
        # ----------
        # Do this last so we don't send parent messages before construction
        self.parent = parent

    def _send_restyle(self, prop, val):
        if self.parent:
            send_val = [val] if isinstance(val, list) else val
            self.parent._restyle_child(self, prop, send_val)

    def _set_prop(self, prop, val):
        plotly_type = self._types.get(prop, None)
        if plotly_type:
            val = plotly_type.validate_coerce(val)
        if prop not in self._data or self._data[prop] != val:
            self._data[prop] = val
            self._send_restyle(prop, val)

    def _restyle_child(self, child, prop, val):
        if child is self.line:
            self._send_restyle('line.{prop}'.format(prop=prop), val)


class Line:
    _types = {}

    # color
    # -----
    _types['color'] = Color(name='color', parent_name='Line')

    @property
    def color(self) -> float:
        return self._data['color']

    @color.setter
    def color(self, val):
        self._set_prop('color', val)

    # width
    # -----
    _types['width'] = Number(name='width', parent_name='Line', default=2, min_val=0)

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
        # Initialize data dict
        # --------------------
        self._data = {}

        # Init parent to None
        # -------------------
        # Passed value will be set at the end of constructor
        self.parent = None

        # Populate data dict with properties
        # ----------------------------------
        self.color = color
        self.width = width

        # Set parent
        # ----------
        # Do this last so we don't send parent messages before construction
        self.parent = parent


    def _set_prop(self, prop, val):
        val = self._types[prop].validate_coerce(val)
        if prop not in self._data or self._data[prop] != val:
            self._data[prop] = val
            self._send_restyle(prop, val)

    def _send_restyle(self, prop, val):
        if self.parent:
            send_val = [val] if isinstance(val, list) else val
            self.parent._restyle_child(self, prop, send_val)