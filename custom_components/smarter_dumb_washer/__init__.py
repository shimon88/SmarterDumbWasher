from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

from .const import DOMAIN
from .coordinator import WasherCoordinator
from .services import async_setup_services, async_unload_services

PLATFORMS = [Platform.SENSOR]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    coordinator = WasherCoordinator(hass, entry)
    await coordinator.async_setup()
    entry.runtime_data = coordinator
    try:
        await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    except Exception:
        coordinator.async_shutdown()
        raise
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator
    async_setup_services(hass)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if not unload_ok:
        return False
    entry.runtime_data.async_shutdown()
    loaded = hass.data.get(DOMAIN)
    if loaded is not None:
        loaded.pop(entry.entry_id, None)
        if not loaded:
            hass.data.pop(DOMAIN, None)
    async_unload_services(hass)
    return True
