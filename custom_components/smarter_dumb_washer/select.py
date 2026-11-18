from homeassistant.components.select import SelectEntity

from .entity import washer_device_info


async def async_setup_entry(hass, entry, async_add_entities):
    async_add_entities([LearnedProgramSelect(entry.runtime_data)])


class LearnedProgramSelect(SelectEntity):
    _attr_has_entity_name = True
    _attr_translation_key = "learned_program"
    _attr_icon = "mdi:format-list-bulleted"

    def __init__(self, coordinator):
        self.coordinator = coordinator
        self._attr_unique_id = f"{coordinator.entry.entry_id}-learned-program"
        self._attr_device_info = washer_device_info(coordinator)

    async def async_added_to_hass(self):
        self.async_on_remove(
            self.coordinator.async_add_listener(self.async_write_ha_state)
        )

    @property
    def options(self):
        return self.coordinator.program_names

    @property
    def current_option(self):
        selected = self.coordinator.selected_program
        if selected in self.options:
            return selected
        return None

    async def async_select_option(self, option):
        self.coordinator.select_program(option)
