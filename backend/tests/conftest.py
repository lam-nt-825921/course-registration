import pytest


@pytest.fixture(autouse=True)
def restore_dependency_overrides():
    # Older API test modules install overrides at collection time.
    from main import app

    saved = app.dependency_overrides.copy()
    yield
    app.dependency_overrides = saved
