import pytest
from ipyplotly.basevalidators import *
import numpy as np


# Enumerated Validator
# ====================

# Array not ok
# ------------
@pytest.fixture(params=['first', 'forth'])
def enumerated_validator_anok(request):
    values = ['first', 'second', 'third', 4]
    return EnumeratedValidator('prop', 'parent', values, request.param, array_ok=False)


# ### Acceptance ###
@pytest.mark.parametrize('val',
                         ['first', 'second', 'third', 4])
def test_enumeration_validator_acceptance_anok(val, enumerated_validator_anok):
    # Values should be accepted and returned unchanged
    assert enumerated_validator_anok.validate_coerce(val) == val


# ### Value Rejection ###
@pytest.mark.parametrize('val',
                         [True, 0, 1, 23, np.inf, set()])
def test_enumeratored_validator_rejection_by_value_anok(val, enumerated_validator_anok):
    with pytest.raises(ValueError) as validation_failure:
        enumerated_validator_anok.validate_coerce(val)

    assert 'Invalid enumeration value' in str(validation_failure.value)


# ### Array Rejection ###
@pytest.mark.parametrize('val',
                         [['first', 'second'], [True], ['third', 4], [4]])
def test_enumeratored_validator_rejection_by_array_anok(val, enumerated_validator_anok):
    with pytest.raises(ValueError) as validation_failure:
        enumerated_validator_anok.validate_coerce(val)

    assert 'must be a scalar value' in str(validation_failure.value)


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
@pytest.fixture(params=[True, False])
def boolean_validator(request):
    return BooleanValidator('prop', 'parent', dflt=request.param)


@pytest.mark.parametrize('val',
                         [1.0, 0.0, 'True', 'False', [], 0, np.nan])
def test_boolean_validator_rejection(val, boolean_validator):
    with pytest.raises(ValueError) as validation_failure:
        boolean_validator.validate_coerce(val)

    assert 'must be a bool' in str(validation_failure.value)


@pytest.mark.parametrize('val', [True, False])
def test_boolean_validator_acceptance(val, boolean_validator):
    assert val == boolean_validator.validate_coerce(val)


