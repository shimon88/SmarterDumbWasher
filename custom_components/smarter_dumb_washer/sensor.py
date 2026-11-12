from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
from homeassistant.helpers.device_registry import DeviceInfo

from .const import DOMAIN, STATE_FINISHED, STATE_IDLE, STATE_RUNNING


async def async_setup_entry(hass, entry, async_add_entities):
    async_add_entities([WasherStateSensor(entry.runtime_data)])


class WasherStateSensor(SensorEntity):
    _attr_should_poll = False
    _attr_has_entity_name = True
    _attr_translation_key = "state"
    _attr_device_class = SensorDeviceClass.ENUM
    _attr_options = [STATE_IDLE, STATE_RUNNING, STATE_FINISHED]
    _attr_icon = "mdi:washing-machine"

    def __init__(self, coordinator):
        self.coordinator = coordinator
        self._attr_unique_id = f"{coordinator.entry.entry_id}-state"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, coordinator.entry.entry_id)},
            name=coordinator.entry.title,
        )

    async def async_added_to_hass(self):
        self.async_on_remove(
            self.coordinator.async_add_listener(self.async_write_ha_state)
        )

    @property
    def native_value(self):
        return self.coordinator.state
