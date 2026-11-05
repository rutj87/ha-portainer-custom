"""Test that all integration platforms import successfully."""

import importlib

from custom_components.portainer import _PLATFORMS


def test_platform_imports() -> None:
    """Verify each forwarded platform module imports properly without error."""
    for platform in _PLATFORMS:
        module = importlib.import_module(f"custom_components.portainer.{platform}")
        assert module is not None
