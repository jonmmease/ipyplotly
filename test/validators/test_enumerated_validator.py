import pytest
import numpy as np
from ipyplotly.basevalidators import EnumeratedValidator


# Fixtures
# --------
@pytest.fixture()
def validator():
    values = ['first', 'second', 'third', 4]
    return EnumeratedValidator('prop', 'parent', values, array_ok=False)


@pytest.fixture()
def validator_aok():
    values = ['first', 'second', 'third', 4]
    return EnumeratedValidator('prop', 'parent', values, array_ok=True)


# Array not ok
# ------------
# ### Acceptance ###
@pytest.mark.parametrize('val',
                         ['first', 'second', 'third', 4])
def test_acceptance(val, validator):
    # Values should be accepted and returned unchanged
    assert validator.validate_coerce(val) == val


# ### Value Rejection ###
@pytest.mark.parametrize('val',
                         [True, 0, 1, 23, np.inf, set()])
def test_rejection_by_value(val, validator):
    with pytest.raises(ValueError) as validation_failure:
        validator.validate_coerce(val)

    assert 'Invalid enumeration value' in str(validation_failure.value)


# ### Array Rejection ###
@pytest.mark.parametrize('val',
                         [['first', 'second'], [True], ['third', 4], [4]])
def test_rejection_by_array(val, validator):
    with pytest.raises(ValueError) as validation_failure:
        validator.validate_coerce(val)

    assert 'Invalid enumeration value' in str(validation_failure.value)


# Array ok
# --------
# ### Acceptance ###
@pytest.mark.parametrize('val',
                         ['first', 'second', 'third', 4,
                          [], ['first', 4], [4], ['third', 'first'],
                          ['first', 'second', 'third', 4]])
def test_acceptance_aok(val, validator_aok):
    # Values should be accepted and returned unchanged
    coerce_val = validator_aok.validate_coerce(val)
    if isinstance(val, (list, np.ndarray)):
        assert np.array_equal(coerce_val, np.array(val, dtype=coerce_val.dtype))
    else:
        assert coerce_val == val


# ### Rejection by value ###
@pytest.mark.parametrize('val',
                         [True, 0, 1, 23, np.inf, set()])
def test_rejection_by_value_aok(val, validator_aok):
    with pytest.raises(ValueError) as validation_failure:
        validator_aok.validate_coerce(val)

    assert 'Invalid enumeration value' in str(validation_failure.value)


# ### Reject by elements ###
@pytest.mark.parametrize('val',
                         [[True], [0], [1, 23], [np.inf, set()],
                          ['ffirstt', 'second', 'third']])
def test_rejection_by_element_aok(val, validator_aok):
    with pytest.raises(ValueError) as validation_failure:
        validator_aok.validate_coerce(val)

    assert 'Invalid enumeration element(s)' in str(validation_failure.value)
