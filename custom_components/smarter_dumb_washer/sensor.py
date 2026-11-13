from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
from homeassistant.const import PERCENTAGE
from homeassistant.helpers.device_registry import DeviceInfo

from .const import (
    ATTR_ETA,
    ATTR_LEARNING,
    ATTR_PROGRAMS,
    DOMAIN,
    STAGE_FILL,
    STAGE_HEAT,
    STAGE_RINSE,
    STAGE_SPIN,
    STAGE_UNKNOWN,
    STAGE_WASH,
    STATE_FINISHED,
    STATE_IDLE,
    STATE_RUNNING,
)


async def async_setup_entry(hass, entry, async_add_entities):
    coordinator = entry.runtime_data
    async_add_entities(
        [
            WasherStateSensor(coordinator),
            WasherProgramSensor(coordinator),
            WasherStageSensor(coordinator),
            WasherProgressSensor(coordinator),
        ]
    )


class _WasherSensor(SensorEntity):
    _attr_should_poll = False
    _attr_has_entity_name = True

    def __init__(self, coordinator, key):
        self.coordinator = coordinator
        self._attr_unique_id = f"{coordinator.entry.entry_id}-{key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, coordinator.entry.entry_id)},
            name=coordinator.entry.title,
        )

    async def async_added_to_hass(self):
        self.async_on_remove(
            self.coordinator.async_add_listener(self.async_write_ha_state)
        )


class WasherStateSensor(_WasherSensor):
    _attr_translation_key = "state"
    _attr_device_class = SensorDeviceClass.ENUM
    _attr_options = [STATE_IDLE, STATE_RUNNING, STATE_FINISHED]
    _attr_icon = "mdi:washing-machine"

    def __init__(self, coordinator):
        super().__init__(coordinator, "state")

    @property
    def native_value(self):
        return self.coordinator.state

    @property
    def extra_state_attributes(self):
        return {
            ATTR_PROGRAMS: self.coordinator.program_names,
            ATTR_LEARNING: self.coordinator.learning_program,
        }


class WasherProgramSensor(_WasherSensor):
    _attr_translation_key = "program"
    _attr_icon = "mdi:tshirt-crew"

    def __init__(self, coordinator):
        super().__init__(coordinator, "program")

    @property
    def native_value(self):
        return self.coordinator.program


class WasherStageSensor(_WasherSensor):
    _attr_translation_key = "stage"
    _attr_device_class = SensorDeviceClass.ENUM
    _attr_options = [
        STAGE_UNKNOWN,
        STAGE_FILL,
        STAGE_WASH,
        STAGE_HEAT,
        STAGE_RINSE,
        STAGE_SPIN,
    ]
    _attr_icon = "mdi:timeline-clock"

    def __init__(self, coordinator):
        super().__init__(coordinator, "stage")

    @property
    def native_value(self):
        return self.coordinator.stage


class WasherProgressSensor(_WasherSensor):
    _attr_translation_key = "progress"
    _attr_native_unit_of_measurement = PERCENTAGE
    _attr_suggested_display_precision = 0
    _attr_icon = "mdi:progress-clock"

    def __init__(self, coordinator):
        super().__init__(coordinator, "progress")

    @property
    def native_value(self):
        return self.coordinator.progress

    @property
    def extra_state_attributes(self):
        return {ATTR_ETA: self.coordinator.eta}
