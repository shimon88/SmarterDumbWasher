from homeassistant.components.button import ButtonEntity

from .entity import washer_device_info


async def async_setup_entry(hass, entry, async_add_entities):
    coordinator = entry.runtime_data
    async_add_entities(
        [
            StartLearningButton(coordinator),
            CancelLearningButton(coordinator),
            DeleteProgramButton(coordinator),
            RenameProgramButton(coordinator),
        ]
    )


class _WasherButton(ButtonEntity):
    _attr_has_entity_name = True

    def __init__(self, coordinator, key):
        self.coordinator = coordinator
        self._attr_unique_id = f"{coordinator.entry.entry_id}-{key}"
        self._attr_device_info = washer_device_info(coordinator)


class StartLearningButton(_WasherButton):
    _attr_translation_key = "start_learning"
    _attr_icon = "mdi:book-plus"

    def __init__(self, coordinator):
        super().__init__(coordinator, "start-learning")

    async def async_press(self):
        self.coordinator.press_learn_start()


class CancelLearningButton(_WasherButton):
    _attr_translation_key = "cancel_learning"
    _attr_icon = "mdi:book-remove"

    def __init__(self, coordinator):
        super().__init__(coordinator, "cancel-learning")

    async def async_press(self):
        self.coordinator.learn_cancel()


class DeleteProgramButton(_WasherButton):
    _attr_translation_key = "delete_program"
    _attr_icon = "mdi:delete"

    def __init__(self, coordinator):
        super().__init__(coordinator, "delete-program")

    async def async_press(self):
        await self.coordinator.press_delete_program()


class RenameProgramButton(_WasherButton):
    _attr_translation_key = "rename_program"
    _attr_icon = "mdi:rename"

    def __init__(self, coordinator):
        super().__init__(coordinator, "rename-program")

    async def async_press(self):
        await self.coordinator.press_rename_program()
