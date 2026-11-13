import voluptuous as vol

from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.service import async_extract_config_entry_ids

from .const import (
    ATTR_NEW_NAME,
    ATTR_PROGRAM_NAME,
    DOMAIN,
    SERVICE_DELETE_PROGRAM,
    SERVICE_LEARN_CANCEL,
    SERVICE_LEARN_START,
    SERVICE_RENAME_PROGRAM,
)

_LEARN_START_SCHEMA = cv.make_entity_service_schema(
    {vol.Required(ATTR_PROGRAM_NAME): cv.string}
)
_DELETE_SCHEMA = cv.make_entity_service_schema(
    {vol.Required(ATTR_PROGRAM_NAME): cv.string}
)
_RENAME_SCHEMA = cv.make_entity_service_schema(
    {
        vol.Required(ATTR_PROGRAM_NAME): cv.string,
        vol.Required(ATTR_NEW_NAME): cv.string,
    }
)
_CANCEL_SCHEMA = cv.make_entity_service_schema({})


def async_setup_services(hass):
    if hass.services.has_service(DOMAIN, SERVICE_LEARN_START):
        return

    async def learn_start(call):
        name = _required_name(call, ATTR_PROGRAM_NAME)
        for coordinator in await _targets(hass, call):
            coordinator.learn_start(name)

    async def learn_cancel(call):
        for coordinator in await _targets(hass, call):
            coordinator.learn_cancel()

    async def delete_program(call):
        name = _required_name(call, ATTR_PROGRAM_NAME)
        for coordinator in await _targets(hass, call):
            if not await coordinator.async_delete_program(name):
                raise ServiceValidationError(f"Unknown program {name}")

    async def rename_program(call):
        name = _required_name(call, ATTR_PROGRAM_NAME)
        new_name = _required_name(call, ATTR_NEW_NAME)
        for coordinator in await _targets(hass, call):
            result = await coordinator.async_rename_program(name, new_name)
            if result == "missing":
                raise ServiceValidationError(f"Unknown program {name}")
            if result == "exists":
                raise ServiceValidationError(f"Program {new_name} already exists")

    hass.services.async_register(
        DOMAIN, SERVICE_LEARN_START, learn_start, schema=_LEARN_START_SCHEMA
    )
    hass.services.async_register(
        DOMAIN, SERVICE_LEARN_CANCEL, learn_cancel, schema=_CANCEL_SCHEMA
    )
    hass.services.async_register(
        DOMAIN, SERVICE_DELETE_PROGRAM, delete_program, schema=_DELETE_SCHEMA
    )
    hass.services.async_register(
        DOMAIN, SERVICE_RENAME_PROGRAM, rename_program, schema=_RENAME_SCHEMA
    )


def async_unload_services(hass):
    if hass.data.get(DOMAIN):
        return
    for service in (
        SERVICE_LEARN_START,
        SERVICE_LEARN_CANCEL,
        SERVICE_DELETE_PROGRAM,
        SERVICE_RENAME_PROGRAM,
    ):
        if hass.services.has_service(DOMAIN, service):
            hass.services.async_remove(DOMAIN, service)


def _required_name(call, key):
    name = str(call.data.get(key, "")).strip()
    if not name:
        raise ServiceValidationError("Program name is empty")
    return name


async def _targets(hass, call):
    loaded = hass.data.get(DOMAIN, {})
    found = []
    for entry_id in await async_extract_config_entry_ids(call):
        coordinator = loaded.get(entry_id)
        if coordinator is not None:
            found.append(coordinator)
    if not found:
        raise ServiceValidationError("Washer not found")
    return found
