import pytest

from ipyplotly.basedatatypes import BasePlotlyType
from unittest import mock


# Methods that code_gen depend on
from ipyplotly.basevalidators import StringValidator, CompoundValidator


# Fixtures
# --------
@pytest.fixture()
def plotly_obj_simple():
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
def plotly_obj_compound():
    # ### Setup plotly obj (make fixture eventually) ###
    plotly_obj = BasePlotlyType('plotly_obj')

    # Add validator
    validator = mock.Mock(spec=CompoundValidator,
                          wraps=CompoundValidator('prop1', 'plotly_obj', data_class=mock.Mock, data_docs=''))
    plotly_obj._validators['prop1'] = validator

    # Mock out _send_update
    plotly_obj._send_update = mock.Mock()

    return plotly_obj


# Validation
# ----------
def test_set_invalid_property(plotly_obj_simple):
    with pytest.raises(KeyError) as failure:
        plotly_obj_simple['bogus'] = 'Hello'


def test_get_invalid_property(plotly_obj_simple):
    with pytest.raises(KeyError) as failure:
        p = plotly_obj_simple['bogus']


# Simple properties
# -----------------
def test_set_get_simple_property(plotly_obj_simple):
    # Perform set_prop
    # ----------------
    plotly_obj_simple['prop1'] = 'Hello'

    # Assertions
    # ----------
    # ### test get ###
    assert plotly_obj_simple['prop1'] == 'Hello'

    # ### _send_update sent ###
    plotly_obj_simple._send_update.assert_called_once_with('prop1', 'Hello')

    # ### _orphan_data configured properly ###
    assert plotly_obj_simple._orphan_data == {'prop1': 'Hello'}

    # ### _data is mapped to _orphan_data
    assert plotly_obj_simple._data is plotly_obj_simple._orphan_data

    # ### validator called properly ###
    plotly_obj_simple._validators['prop1'].validate_coerce.assert_called_once_with('Hello')


def test_set_get_simple_property_with_parent(plotly_obj_simple):

    # Setup parent
    # ------------
    parent = mock.Mock()
    parent_data = {'A': {}}
    parent_delta = {'A': {}}
    parent._get_child_data.return_value = parent_data['A']
    parent._get_child_delta.return_value = parent_delta['A']
    parent._in_batch_mode = False
    plotly_obj_simple._parent = parent

    # Perform set_prop
    # ----------------
    plotly_obj_simple['prop1'] = 'Hello'

    # Parent Assertions
    # -----------------
    parent._get_child_data.assert_called_with(plotly_obj_simple)

    # Child Assertions
    # ----------------
    # ### test get ###
    assert plotly_obj_simple['prop1'] == 'Hello'

    # ### _data ### bound to parent dict
    assert parent_data['A'] is plotly_obj_simple._data

    # ### _send_update sent ###
    plotly_obj_simple._send_update.assert_called_once_with('prop1', 'Hello')

    # ### Orphan data cleared ###
    assert plotly_obj_simple._orphan_data == {}

    # ### validator called properly ###
    plotly_obj_simple._validators['prop1'].validate_coerce.assert_called_once_with('Hello')


# Compound properties
# -------------------
def test_set_get_compound_property(plotly_obj_compound):
    # Setup value
    # -----------
    v = mock.Mock()
    d = {'a': 23}
    type(v)._data = mock.PropertyMock(return_value=d)

    # Perform set_prop
    # ----------------
    plotly_obj_compound['prop1'] = v

    # Mutate d
    # --------
    # Just to make sure we copy data on assignment
    d['a'] = 1

    # Parent Assertions
    # -----------------
    # ### test get ###
    assert plotly_obj_compound['prop1'] is v

    # ### _send_update sent ###
    plotly_obj_compound._send_update.assert_called_once_with('prop1', {'a': 23})

    # ### _orphan_data configured properly ###
    assert plotly_obj_compound._orphan_data == {'prop1': {'a': 23}}

    # ### _data is mapped to _orphan_data
    assert plotly_obj_compound._data is plotly_obj_compound._orphan_data

    # ### validator called properly ###
    plotly_obj_compound._validators['prop1'].validate_coerce.assert_called_once_with(v)

    # Child Assertions
    # ----------------
    # ### Parent set to plotly_obj
    assert v._parent is plotly_obj_compound

    # ### Orphan data cleared ###
    v._orphan_data.clear.assert_called_once()


# Primitives
#
# Get from _orphan_data or from parent data
#
# Set: Sets _orphan_data or parent
#
# Test several levels of parent nesting
#
# 'Set' propagates _send_update to parent


# test _in_batch_mode propagates but doesn't update parent dict


# Compound (array)
#
# Set: Orphan data transferred and cleared
#      Reparenting
#
#      Get on set object maps to parent dict
#
#
# __getitem__
#
#



#
# : Gets primitives from orphan data or parent
# : Gets compound from _compound_props with proper parent
# :      array

# Set
#
# _set_prop
# _set_compound_prop
# _set_array_prop
#

#
# That validators are called when _set_prop methods are called
#
