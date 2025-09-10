"""
Basic tests to verify EasyPay setup is working correctly.
"""
import pytest
import sys
from pathlib import Path


def test_python_version():
    """Test that Python version is compatible."""
    assert sys.version_info >= (3, 8), "Python 3.8 or higher is required"


def test_fastapi_import():
    """Test that FastAPI can be imported."""
    try:
        import fastapi
        assert fastapi.__version__ is not None
    except ImportError:
        pytest.fail("FastAPI could not be imported")


def test_pydantic_import():
    """Test that Pydantic can be imported."""
    try:
        import pydantic
        assert pydantic.__version__ is not None
    except ImportError:
        pytest.fail("Pydantic could not be imported")


def test_uvicorn_import():
    """Test that Uvicorn can be imported."""
    try:
        import uvicorn
        assert uvicorn.__version__ is not None
    except ImportError:
        pytest.fail("Uvicorn could not be imported")


def test_project_structure():
    """Test that basic project structure exists."""
    project_root = Path(__file__).parent.parent
    
    # Check that key directories exist
    assert (project_root / "src").exists(), "src directory should exist"
    assert (project_root / "tests").exists(), "tests directory should exist"
    assert (project_root / "docs").exists(), "docs directory should exist"
    assert (project_root / "requirements.txt").exists(), "requirements.txt should exist"


def test_environment_file():
    """Test that environment configuration exists."""
    project_root = Path(__file__).parent.parent
    env_file = project_root / ".env"
    env_example = project_root / "env.example"
    
    # Either .env or env.example should exist
    assert env_file.exists() or env_example.exists(), "Either .env or env.example should exist"


if __name__ == "__main__":
    pytest.main([__file__])
