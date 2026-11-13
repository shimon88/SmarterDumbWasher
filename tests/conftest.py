import os
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest
from pytest_homeassistant_custom_component import common

from tests.washer import WasherClock

pytest_plugins = "pytest_homeassistant_custom_component"

_REPO = Path(__file__).resolve().parents[1]
_CONFIG = Path(tempfile.mkdtemp(prefix="smarter-dumb-washer-"))
(_CONFIG / "custom_components").symlink_to(
    _REPO / "custom_components", target_is_directory=True
)
(_CONFIG / "media").mkdir()


def _config_dir(*parts):
    return os.path.join(_CONFIG, *parts)


common.get_test_config_dir = _config_dir


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    return


@pytest.fixture
def washer_clock():
    clock = WasherClock()
    with patch(
        "custom_components.smarter_dumb_washer.coordinator.dt_util.utcnow",
        clock.utcnow,
    ):
        yield clock
