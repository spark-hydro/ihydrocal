"""Basic tests for iHydroCal."""

import ihydrocal


def test_version():
    """Test that version is defined."""
    assert hasattr(ihydrocal, "__version__")
    assert ihydrocal.__version__ == "0.0.0"


def test_import():
    """Test that package can be imported."""
    assert ihydrocal is not None
