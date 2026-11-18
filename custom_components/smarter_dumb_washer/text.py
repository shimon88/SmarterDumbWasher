from homeassistant.components.text import TextEntity, TextMode

from .entity import washer_device_info


async def async_setup_entry(hass, entry, async_add_entities):
    async_add_entities([ProgramNameText(entry.runtime_data)])


class ProgramNameText(TextEntity):
    _attr_has_entity_name = True
    _attr_translation_key = "program_name"
    _attr_icon = "mdi:form-textbox"
    _attr_mode = TextMode.TEXT
    _attr_native_min = 0
    _attr_native_max = 64

    def __init__(self, coordinator):
        self.coordinator = coordinator
        self._attr_unique_id = f"{coordinator.entry.entry_id}-program-name"
        self._attr_device_info = washer_device_info(coordinator)

    async def async_added_to_hass(self):
        self.async_on_remove(
            self.coordinator.async_add_listener(self.async_write_ha_state)
        )

    @property
    def native_value(self):
        return self.coordinator.draft_name

    async def async_set_value(self, value):
        self.coordinator.set_draft_name(value)
