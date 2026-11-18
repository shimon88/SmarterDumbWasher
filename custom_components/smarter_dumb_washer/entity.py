from homeassistant.helpers.device_registry import DeviceInfo

from .const import DOMAIN


def washer_device_info(coordinator):
    return DeviceInfo(
        identifiers={(DOMAIN, coordinator.entry.entry_id)},
        name=coordinator.entry.title,
    )
