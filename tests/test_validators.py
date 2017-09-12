import pytest
from ipyplotly.basevalidators import *
import numpy as np


# Enumerated Validator
# ====================
@pytest.fixture(params=['first', 'forth'])
def enumerated_validator_anok(request):
    values = ['first', 'second', 'third', 'forth']
    return EnumeratedValidator('prop', 'parent', values, request.param, array_ok=False)


@pytest.mark.parametrize('val',
                         [True, 0, 1, 23, np.inf, ['first']])
def test_enumeratored_validator_rejection_by_type(val, enumerated_validator_anok):
    with pytest.raises(ValueError) as validation_failure:
        enumerated_validator_anok.validate_coerce(val)

    assert 'must be a string' in str(validation_failure.value)

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


