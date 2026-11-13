from homeassistant.helpers.storage import Store

from .const import DOMAIN

_VERSION = 1


class ProgramStore:
    def __init__(self, hass, entry_id):
        self._store = Store(hass, _VERSION, f"{DOMAIN}.{entry_id}")
        self.programs = {}

    async def async_load(self):
        data = await self._store.async_load()
        programs = {}
        if isinstance(data, dict) and isinstance(data.get("programs"), dict):
            programs = data["programs"]
        self.programs = programs

    async def async_put(self, program):
        self.programs[program["name"]] = program
        await self._save()

    async def async_delete(self, name):
        if name not in self.programs:
            return False
        del self.programs[name]
        await self._save()
        return True

    async def async_rename(self, name, new_name):
        program = self.programs.pop(name)
        program["name"] = new_name
        self.programs[new_name] = program
        await self._save()

    async def _save(self):
        await self._store.async_save({"programs": self.programs})
