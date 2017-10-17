import pytest
from ipyplotly.basevalidators import ColorValidator
import numpy as np


# Fixtures
# --------
@pytest.fixture()
def validator():
    return ColorValidator('prop', 'parent')


@pytest.fixture()
def validator_aok():
    return ColorValidator('prop', 'parent', array_ok=True)


# Array not ok
# ------------
# ### Acceptance ###
@pytest.mark.parametrize('val',
                         ['red', 'BLUE', 23, 15, 'rgb(255, 0, 0)', 'hsl(0, 100%, 50%)', 'hsla(0, 100%, 50%, 100%)',
                          'hsv(0, 100%, 100%)', 'hsva(0, 100%, 100%, 50%)'])
def test_acceptance(val, validator: ColorValidator):
    if isinstance(val, str):
        assert validator.validate_coerce(val) == str.replace(val.lower(), ' ', '')
    else:
        assert validator.validate_coerce(val) == val


# ### Rejection by value ###
@pytest.mark.parametrize('val',
                         ['redd', 'rgbbb(255, 0, 0)', 'hsl(0, 1%0000%, 50%)'])
def test_rejection(val, validator: ColorValidator):
    with pytest.raises(ValueError) as validation_failure:
        validator.validate_coerce(val)

    assert 'must be a valid color' in str(validation_failure.value)


# Array ok
# --------
# ### Acceptance ###
@pytest.mark.parametrize('val',
                         ['blue', 23, [0, 1, 2],
                          ['red', 'rgb(255, 0, 0)'],
                          ['hsl(0, 100%, 50%)', 'hsla(0, 100%, 50%, 100%)', 'hsv(0, 100%, 100%)'],
                          ['hsva(0, 100%, 100%, 50%)']])
def test_acceptance_aok(val, validator_aok: ColorValidator):
    coerce_val = validator_aok.validate_coerce(val)
    if isinstance(val, (list, np.ndarray)):
        expected = np.array(
            [str.replace(v.lower(), ' ', '') if isinstance(v, str) else v for v in val],
            dtype=coerce_val.dtype)
        assert np.array_equal(coerce_val, expected)
    else:
        expected = str.replace(val.lower(), ' ', '') if isinstance(val, str) else val
        assert coerce_val == val


# ### Rejection ###
@pytest.mark.parametrize('val',
                         [['redd', 'rgb(255, 0, 0)'],
                          ['hsl(0, 100%, 50_00%)', 'hsla(0, 100%, 50%, 100%)', 'hsv(0, 100%, 100%)'],
                          ['hsva(0, 1%00%, 100%, 50%)']])
def test_rejection_aok(val, validator_aok: ColorValidator):
    with pytest.raises(ValueError) as validation_failure:
        validator_aok.validate_coerce(val)

    assert 'must be numbers or valid colors' in str(validation_failure.value)
