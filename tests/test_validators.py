import pytest
from pytest import approx

from ipyplotly.basevalidators import *
import numpy as np


# Enumerated Validator
# ====================

# Array not ok
# ------------
@pytest.fixture(params=['first', 'forth'])
def enumerated_validator(request):
    values = ['first', 'second', 'third', 4]
    return EnumeratedValidator('prop', 'parent', values, dflt=request.param, array_ok=False)


@pytest.fixture
def enumerated_validator_no_dflt():
    values = ['first', 'second', 'third', 4]
    return EnumeratedValidator('prop', 'parent', values, array_ok=False)


# ### Acceptance ###
@pytest.mark.parametrize('val',
                         ['first', 'second', 'third', 4])
def test_enumeration_validator_acceptance(val, enumerated_validator):
    # Values should be accepted and returned unchanged
    assert enumerated_validator.validate_coerce(val) == val


# ### Value Rejection ###
@pytest.mark.parametrize('val',
                         [True, 0, 1, 23, np.inf, set()])
def test_enumeratored_validator_rejection_by_value(val, enumerated_validator):
    with pytest.raises(ValueError) as validation_failure:
        enumerated_validator.validate_coerce(val)

    assert 'Invalid enumeration value' in str(validation_failure.value)


# ### Array Rejection ###
@pytest.mark.parametrize('val',
                         [['first', 'second'], [True], ['third', 4], [4]])
def test_enumeratored_validator_rejection_by_array(val, enumerated_validator):
    with pytest.raises(ValueError) as validation_failure:
        enumerated_validator.validate_coerce(val)

    assert 'Invalid enumeration value' in str(validation_failure.value)


# ### Default value ###
def test_enumeratored_validator_default(enumerated_validator: EnumeratedValidator):
    assert enumerated_validator.default is not None
    assert enumerated_validator.default == enumerated_validator.validate_coerce(None)


# ### No default value ###
def test_enumeratored_validator_no_default(enumerated_validator_no_dflt: EnumeratedValidator):
    assert enumerated_validator_no_dflt.default is None
    assert enumerated_validator_no_dflt.validate_coerce(None) is None


# Array ok
# --------
@pytest.fixture(params=['first', 'forth'])
def enumerated_validator_aok(request):
    values = ['first', 'second', 'third', 4]
    return EnumeratedValidator('prop', 'parent', values, request.param, array_ok=True)


# ### Acceptance ###
@pytest.mark.parametrize('val',
                         ['first', 'second', 'third', 4,
                          [], ['first', 4], [4], ['third', 'first'],
                          ['first', 'second', 'third', 4]])
def test_enumeration_validator_acceptance_aok(val, enumerated_validator_aok):
    # Values should be accepted and returned unchanged
    assert enumerated_validator_aok.validate_coerce(val) == val


# ### Rejection by value ###
@pytest.mark.parametrize('val',
                         [True, 0, 1, 23, np.inf, set()])
def test_enumeratored_validator_rejection_by_value_aok(val, enumerated_validator_aok):
    with pytest.raises(ValueError) as validation_failure:
        enumerated_validator_aok.validate_coerce(val)

    assert 'Invalid enumeration value' in str(validation_failure.value)


# ### Reject by elements ###
@pytest.mark.parametrize('val',
                         [[True], [0], [1, 23], [np.inf, set()],
                          ['ffirstt', 'second', 'third']])
def test_enumeratored_validator_rejection_by_element_aok(val, enumerated_validator_aok):
    with pytest.raises(ValueError) as validation_failure:
        enumerated_validator_aok.validate_coerce(val)

    assert 'Invalid enumeration element(s)' in str(validation_failure.value)


# Boolean Validator
# =================

# ### Fixtures ###
@pytest.fixture(params=[True, False])
def boolean_validator(request):
    return BooleanValidator('prop', 'parent', dflt=request.param)


@pytest.fixture
def boolean_validator_no_dflt(request):
    return BooleanValidator('prop', 'parent')


# ### Acceptance ###
@pytest.mark.parametrize('val', [True, False])
def test_boolean_validator_acceptance(val, boolean_validator):
    assert val == boolean_validator.validate_coerce(val)


# ### Rejection ###
@pytest.mark.parametrize('val',
                         [1.0, 0.0, 'True', 'False', [], 0, np.nan])
def test_boolean_validator_rejection(val, boolean_validator):
    with pytest.raises(ValueError) as validation_failure:
        boolean_validator.validate_coerce(val)

    assert 'must be a bool' in str(validation_failure.value)


# ### Default ###
def test_boolean_validator_default(boolean_validator: BooleanValidator):
    assert boolean_validator.default is not None
    assert boolean_validator.default == boolean_validator.validate_coerce(None)


# ### No Default###
def test_boolean_validator_no_default(boolean_validator_no_dflt: BooleanValidator):
    assert boolean_validator_no_dflt.default is None
    assert boolean_validator_no_dflt.validate_coerce(None) is None


# Number Validator
# ================

# Array not ok
# ------------

# ### Fixtures ###
@pytest.fixture(params=[0, 1, np.nan, 99999999, -1234])
def number_validator(request):
    return NumberValidator('prop', 'parent', dflt=request.param)


# ### Acceptance ###
@pytest.mark.parametrize('val',
                         [1.0, 0.0, 1, -1234.5678, 54321, np.pi, np.nan, np.inf, -np.inf])
def test_number_validator_acceptance(val, number_validator: NumberValidator):
    assert number_validator.validate_coerce(val) == approx(val, nan_ok=True)


# ### Rejection by value ###
@pytest.mark.parametrize('val',
                         ['hello', (), [], [1, 2, 3], set(), '34'])
def test_number_validator_rejection_by_value(val, number_validator: NumberValidator):
    with pytest.raises(ValueError) as validation_failure:
        number_validator.validate_coerce(val)

    assert 'must be a number' in str(validation_failure.value)


# ### Default ###
def test_number_validator_default(number_validator: NumberValidator):
    assert number_validator.default is not None
    assert number_validator.default == approx(number_validator.validate_coerce(None), nan_ok=True)


# ### No default value ###
@pytest.fixture
def number_validator_no_dflt():
    return NumberValidator('prop', 'parent')


def test_number_validator_no_default(number_validator_no_dflt: NumberValidator):
    assert number_validator_no_dflt.default is None
    assert number_validator_no_dflt.validate_coerce(None) is None


# ### With min/max ###
@pytest.fixture
def number_validator_min_max(request):
    return NumberValidator('prop', 'parent', dflt=0.5, min=-1.0, max=2.0)


@pytest.mark.parametrize('val',
                         [0, 0.0, -0.5, 1, 1.0, 2, 2.0, np.pi/2.0])
def test_number_validator_min_max_accepted(val, number_validator_min_max: NumberValidator):
    assert number_validator_min_max.validate_coerce(val) == approx(val)


@pytest.mark.parametrize('val',
                         [-1.01, -10, 2.1, 234, -np.inf, np.nan, np.inf])
def test_number_validator_min_max_rejection(val, number_validator_min_max: NumberValidator):
    with pytest.raises(ValueError) as validation_failure:
        number_validator_min_max.validate_coerce(val)

    assert 'must be in the range [-1.0, 2.0]' in str(validation_failure.value)


# Array ok
# --------
@pytest.fixture
def number_validator_aok(request):
    return NumberValidator('prop', 'parent', min=-1, max=1, array_ok=True)


# ### Acceptance ###
@pytest.mark.parametrize('val',
                         [1.0, 0.0, 1, 0.4])
def test_number_validator_acceptance_aok_scalars(val, number_validator_aok: NumberValidator):
    assert number_validator_aok.validate_coerce(val) == val


@pytest.mark.parametrize('val',
                         [[1.0, 0.0], [1], [-0.1234, .41, -1.0]])
def test_number_validator_acceptance_aok_list(val, number_validator_aok: NumberValidator):
    assert number_validator_aok.validate_coerce(val) == val


# ### Coerce ###
#     Coerced to general consistent numeric type
@pytest.mark.parametrize('val,expected',
                         [([1.0, 0], [1.0, 0.0]), ([1, -1], [1.0, -1.0]), ([-0.1234, 0, -1], [-0.1234, 0.0, -1.0])])
def test_number_validator_acceptance_aok_list(val, expected, number_validator_aok: NumberValidator):
    for v, e in zip(number_validator_aok.validate_coerce(val), expected):
        assert type(v) == type(e)
        assert v == e


# ### Rejection ###
#
@pytest.mark.parametrize('val',
                         [['a', 4]])
def test_number_validator_rejection_aok(val, number_validator_aok: NumberValidator):
    with pytest.raises(ValueError) as validation_failure:
        number_validator_aok.validate_coerce(val)

    assert 'must be numbers' in str(validation_failure.value)


# Integer Validator
# =================

# Array not ok
# ------------

# ### Fixtures ###
@pytest.fixture(params=[0, 1, -10])
def integer_validator(request):
    return IntegerValidator('prop', 'parent', dflt=request.param)


# ### Acceptance ###
@pytest.mark.parametrize('val',
                         [1, -19, 0, -1234])
def test_integer_validator_acceptance(val, integer_validator: IntegerValidator):
    assert integer_validator.validate_coerce(val) == val


# ### Rejection by value ###
@pytest.mark.parametrize('val',
                         ['hello', (), [], [1, 2, 3], set(), '34', np.nan, np.inf, -np.inf])
def test_integer_validator_rejection_by_value(val, integer_validator: IntegerValidator):
    with pytest.raises(ValueError) as validation_failure:
        integer_validator.validate_coerce(val)

    assert 'must be a number that can be converted to an integer' in str(validation_failure.value)


# ### Default ###
def test_integer_validator_default(integer_validator: IntegerValidator):
    assert integer_validator.default is not None
    assert integer_validator.default == integer_validator.validate_coerce(None)


# ### No default value ###
@pytest.fixture
def integer_validator_no_dflt():
    return NumberValidator('prop', 'parent')


def test_integer_validator_no_default(integer_validator_no_dflt: IntegerValidator):
    assert integer_validator_no_dflt.default is None
    assert integer_validator_no_dflt.validate_coerce(None) is None


# ### With min/max ###
@pytest.fixture
def integer_validator_min_max():
    return IntegerValidator('prop', 'parent', dflt=0, min=-1, max=2)


@pytest.mark.parametrize('val',
                         [0, 1, -1, 2])
def test_integer_validator_min_max_accepted(val, integer_validator_min_max: IntegerValidator):
    assert integer_validator_min_max.validate_coerce(val) == approx(val)


@pytest.mark.parametrize('val',
                         [-1.01, -10, 2.1, 3])
def test_integer_validator_min_max_rejection(val, integer_validator_min_max: NumberValidator):
    with pytest.raises(ValueError) as validation_failure:
        integer_validator_min_max.validate_coerce(val)

    assert 'must be in the range [-1, 2]' in str(validation_failure.value)


# Array ok
# --------
@pytest.fixture
def integer_validator_aok(request):
    return IntegerValidator('prop', 'parent', min=-2, max=10, array_ok=True)


# ### Acceptance ###
@pytest.mark.parametrize('val',
                         [-2, 1, 0, 1, 10])
def test_integer_validator_acceptance_aok_scalars(val, integer_validator_aok: IntegerValidator):
    assert integer_validator_aok.validate_coerce(val) == val


@pytest.mark.parametrize('val',
                         [[1, 0], [1], [-2, 1, 8]])
def test_integer_validator_acceptance_aok_list(val, integer_validator_aok: IntegerValidator):
    assert integer_validator_aok.validate_coerce(val) == val


# ### Coerce ###
#     Coerced to general consistent numeric type
@pytest.mark.parametrize('val,expected',
                         [([1.0, 0], [1, 0]), ([1, -1], [1, -1]), ([-1.9, 0, 5.1], [-1, 0, 5])])
def test_integer_validator_acceptance_aok_list(val, expected, integer_validator_aok: IntegerValidator):
    for v, e in zip(integer_validator_aok.validate_coerce(val), expected):
        assert type(v) == type(e)
        assert v == e


# ### Rejection ###
#
@pytest.mark.parametrize('val',
                         [['a', 4], [[], 3, 4]])
def test_integer_validator_rejection_aok(val, integer_validator_aok: IntegerValidator):
    with pytest.raises(ValueError) as validation_failure:
        integer_validator_aok.validate_coerce(val)

    assert 'must be convertible to integers' in str(validation_failure.value)


# String Validator
# ================
# Array not ok
# ------------

# ### Fixtures ###
@pytest.fixture(params=['foo', 'BAR', ''])
def string_validator(request):
    return StringValidator('prop', 'parent', dflt=request.param)


# ### Acceptance ###
@pytest.mark.parametrize('val',
                         ['bar', 'HELLO!!!', 'world!@#$%^&*()', ''])
def test_string_validator_acceptance(val, string_validator: StringValidator):
    assert string_validator.validate_coerce(val) == val


# ### Rejection by value ###
@pytest.mark.parametrize('val',
                         [(), [], [1, 2, 3], set(), np.nan, np.pi])
def test_string_validator_rejection(val, string_validator: StringValidator):
    with pytest.raises(ValueError) as validation_failure:
        string_validator.validate_coerce(val)

    assert 'must be a string' in str(validation_failure.value)


# ### Default ###
def test_string_validator_default(string_validator: StringValidator):
    assert string_validator.default is not None
    assert string_validator.default == string_validator.validate_coerce(None)


# ### No default value ###
@pytest.fixture
def string_validator_no_dflt():
    return NumberValidator('prop', 'parent')


def test_string_validator_no_default(string_validator_no_dflt: StringValidator):
    assert string_validator_no_dflt.default is None
    assert string_validator_no_dflt.validate_coerce(None) is None


# Valid values
# ------------
@pytest.fixture(params=['foo', 'BAR', ''])
def string_validator_values(request):
    return StringValidator('prop', 'parent', dflt=request.param, values=['foo', 'BAR', ''])


@pytest.mark.parametrize('val',
                         ['foo', 'BAR', ''])
def test_string_validator_acceptance_values(val, string_validator_values: StringValidator):
    assert string_validator_values.validate_coerce(val) == val


@pytest.mark.parametrize('val',
                         ['FOO', 'bar', 'other', '1234'])
def test_string_validator_rejection_values(val, string_validator_values: StringValidator):
    with pytest.raises(ValueError) as validation_failure:
        string_validator_values.validate_coerce(val)

    assert 'Invalid string value "{val}"'.format(val=val) in str(validation_failure.value)


# ### No blanks ###
@pytest.fixture(params=['foo', 'BAR'])
def string_validator_no_blanks(request):
    return StringValidator('prop', 'parent', dflt=request.param, no_blank=True)


@pytest.mark.parametrize('val',
                         ['bar', 'HELLO!!!', 'world!@#$%^&*()'])
def test_string_validator_acceptance_no_blanks(val, string_validator_no_blanks: StringValidator):
    assert string_validator_no_blanks.validate_coerce(val) == val


@pytest.mark.parametrize('val',
                         [''])
def test_string_validator_rejection_no_blanks(val, string_validator_no_blanks: StringValidator):
    with pytest.raises(ValueError) as validation_failure:
        string_validator_no_blanks.validate_coerce(val)

    assert 'may not be blank' in str(validation_failure.value)


# Array ok
# --------
@pytest.fixture
def string_validator_aok_values(request):
    return StringValidator('prop', 'parent', values=['foo', 'BAR', '', 'baz'], array_ok=True)


@pytest.fixture
def string_validator_aok(request):
    return StringValidator('prop', 'parent', array_ok=True)


# ### Acceptance ###
@pytest.mark.parametrize('val',
                         ['foo', 'BAR', '', 'baz'])
def test_string_validator_acceptance_aok_scalars(val, string_validator_aok: StringValidator):
    assert string_validator_aok.validate_coerce(val) == val


@pytest.mark.parametrize('val',
                         [['foo'], ['BAR', ''], ['baz', 'baz', 'baz']])
def test_string_validator_acceptance_aok_list(val, string_validator_aok: StringValidator):
    assert string_validator_aok.validate_coerce(val) == val


# ### Rejection by type ###
@pytest.mark.parametrize('val',
                         [['foo', ()], ['foo', 3, 4], [3, 2, 1]])
def test_string_validator_rejection_aok(val, string_validator_aok: StringValidator):
    with pytest.raises(ValueError) as validation_failure:
        string_validator_aok.validate_coerce(val)

    assert 'must be strings' in str(validation_failure.value)


# ### Rejection by value ###
@pytest.mark.parametrize('val',
                         [['foo', 'bar'], ['3', '4'], ['BAR', 'BAR', 'hello!']])
def test_string_validator_rejection_aok_values(val, string_validator_aok_values: StringValidator):
    with pytest.raises(ValueError) as validation_failure:
        string_validator_aok_values.validate_coerce(val)

    assert 'Invalid string element' in str(validation_failure.value)


# ### No blanks ###
@pytest.fixture(params=['foo', 'BAR'])
def string_validator_no_blanks_aok(request):
    return StringValidator('prop', 'parent', dflt=request.param, no_blank=True, array_ok=True)


@pytest.mark.parametrize('val',
                         [['bar', 'HELLO!!!'], ['world!@#$%^&*()']])
def test_string_validator_acceptance_no_blanks_aok(val, string_validator_no_blanks_aok: StringValidator):
    assert string_validator_no_blanks_aok.validate_coerce(val) == val


@pytest.mark.parametrize('val',
                         ['', ['foo', 'bar', ''], ['']])
def test_string_validator_rejection_no_blanks_aok(val, string_validator_no_blanks_aok: StringValidator):
    with pytest.raises(ValueError) as validation_failure:
        string_validator_no_blanks_aok.validate_coerce(val)

    assert 'may not be blank' in str(validation_failure.value)


# ColorValidator
# ==============
# Array not ok
# ------------

# ### Fixtures ###
@pytest.fixture(params=['green', 'rgb(255, 0, 0)'])
def color_validator(request):
    return ColorValidator('prop', 'parent', dflt=request.param)


# ### Acceptance ###
@pytest.mark.parametrize('val',
                         ['red', 'rgb(255, 0, 0)', 'hsl(0, 100%, 50%)', 'hsla(0, 100%, 50%, 100%)',
                          'hsv(0, 100%, 100%)', 'hsva(0, 100%, 100%, 50%)'])
def test_color_validator_acceptance(val, color_validator: StringValidator):
    assert color_validator.validate_coerce(val) == val


# ### Rejection by value ###
@pytest.mark.parametrize('val',
                         ['redd', 'rgbbb(255, 0, 0)', 'hsl(0, 10000%, 50%)'])
def test_color_validator_rejection(val, color_validator: StringValidator):
    with pytest.raises(ValueError) as validation_failure:
        color_validator.validate_coerce(val)

    assert 'must be a valid color' in str(validation_failure.value)


# Array ok
# --------
@pytest.fixture(params=['green', 'rgb(255, 0, 0)'])
def color_validator_aok(request):
    return ColorValidator('prop', 'parent', dflt=request.param, array_ok=True)


# ### Acceptance ###
@pytest.mark.parametrize('val',
                         [['red', 'rgb(255, 0, 0)'],
                          ['hsl(0, 100%, 50%)', 'hsla(0, 100%, 50%, 100%)', 'hsv(0, 100%, 100%)'],
                          ['hsva(0, 100%, 100%, 50%)']])
def test_color_validator_acceptance(val, color_validator_aok: StringValidator):
    assert color_validator_aok.validate_coerce(val) == val


# ### Rejection ###
@pytest.mark.parametrize('val',
                         [['redd', 'rgb(255, 0, 0)'],
                          ['hsl(0, 100%, 5000%)', 'hsla(0, 100%, 50%, 100%)', 'hsv(0, 100%, 100%)'],
                          ['hsva(0, 1%00%, 100%, 50%)']])
def test_color_validator_acceptance(val, color_validator_aok: StringValidator):
    with pytest.raises(ValueError) as validation_failure:
        color_validator_aok.validate_coerce(val)

    assert 'must be valid colors' in str(validation_failure.value)



# FlaglistValidator
# =================


# DataArrayValidator
# ==================





# ColorscaleValidator
# ===================


# AngleValidator
# ==============


# SubplotidValidator
# ==================


# AnyValidator
# ============


# SubplotidValidator
# ==================


# InfoArrayValidator
# ==================


# CompoundValidator
# =================
