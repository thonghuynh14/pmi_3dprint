"""Pytest config + shared fixtures.

Pytest tự load file này ở mọi level. Các fixture cụ thể của từng app
đặt trong apps/<name>/tests/conftest.py.
"""

import pytest


@pytest.fixture
def api_client():
    """DRF APIClient. Lazy import để conftest này không phụ thuộc Django setup."""
    from rest_framework.test import APIClient

    return APIClient()
