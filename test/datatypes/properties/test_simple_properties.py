from unittest import mock
import pytest
from ipyplotly.basedatatypes import BasePlotlyType
from ipyplotly.basevalidators import StringValidator


# Fixtures
# --------
@pytest.fixture()
def plotly_obj():
    # ### Setup plotly obj (make fixture eventually) ###
    plotly_obj = BasePlotlyType('plotly_obj')

    # Add validator
    validator = mock.Mock(spec=StringValidator,
                          wraps=StringValidator('prop1', 'plotly_obj'))
    plotly_obj._validators['prop1'] = validator

    # Mock out _send_update
    plotly_obj._send_update = mock.Mock()

    return plotly_obj


@pytest.fixture()
def parent():
    parent_obj = mock.Mock()
    parent_data = {'plotly_obj': {}}
    parent_delta = {'plotly_obj': {}}
    parent_obj._get_child_data.return_value = parent_data['plotly_obj']
    parent_obj._get_child_delta.return_value = parent_delta['plotly_obj']
    parent_obj._in_batch_mode = False
    return parent_obj

# Validation
# ----------
def test_set_invalid_property(plotly_obj):
    with pytest.raises(KeyError) as failure:
        plotly_obj['bogus'] = 'Hello'


def test_get_invalid_property(plotly_obj):
    with pytest.raises(KeyError) as failure:
        p = plotly_obj['bogus']


# Orphan
# ------
def test_set_get_property_orphan(plotly_obj):
    # Perform set_prop
    # ----------------
    plotly_obj['prop1'] = 'Hello'

    # Assertions
    # ----------
    # ### test get ###
    assert plotly_obj['prop1'] == 'Hello'

    # ### _send_update sent ###
    plotly_obj._send_update.assert_called_once_with('prop1', 'Hello')

    # ### _orphan_data configured properly ###
    assert plotly_obj._orphan_data == {'prop1': 'Hello'}

    # ### _data is mapped to _orphan_data
    assert plotly_obj._data is plotly_obj._orphan_data

    # ### validator called properly ###
    plotly_obj._validators['prop1'].validate_coerce.assert_called_once_with('Hello')


# With parent
# -----------
def test_set_get_property_with_parent(plotly_obj, parent):

    # Setup parent
    # ------------
    plotly_obj._parent = parent

    # Perform set_prop
    # ----------------
    plotly_obj['prop1'] = 'Hello'

    # Parent Assertions
    # -----------------
    parent._get_child_data.assert_called_with(plotly_obj)

    # Child Assertions
    # ----------------
    # ### test get ###
    assert plotly_obj['prop1'] == 'Hello'

    # ### _data bound to parent dict ###
    assert parent._get_child_data(plotly_obj) is plotly_obj._data

    # ### _send_update sent ###
    plotly_obj._send_update.assert_called_once_with('prop1', 'Hello')

    # ### Orphan data cleared ###
    assert plotly_obj._orphan_data == {}

    # ### validator called properly ###
    plotly_obj._validators['prop1'].validate_coerce.assert_called_once_with('Hello')
