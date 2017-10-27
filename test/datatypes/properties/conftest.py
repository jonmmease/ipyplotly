from unittest import mock
import pytest


@pytest.fixture(scope="module")
def parent():
    parent_obj = mock.Mock()
    parent_data = {'plotly_obj': {}}
    parent_delta = {'plotly_obj': {}}
    parent_obj._get_child_data.return_value = parent_data['plotly_obj']
    parent_obj._get_child_delta.return_value = parent_delta['plotly_obj']
    parent_obj._in_batch_mode = False
    return parent_obj
