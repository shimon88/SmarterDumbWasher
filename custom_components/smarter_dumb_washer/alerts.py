import logging
from datetime import timedelta

from homeassistant.core import callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.event import async_call_later
from homeassistant.util import dt as dt_util

from .const import (
    CONF_ANNOUNCE_MESSAGE,
    CONF_MEDIA_PLAYERS,
    CONF_NOTIFY_SERVICES,
    CONF_QUIET_ENABLED,
    CONF_QUIET_END,
    CONF_QUIET_START,
    CONF_REPEAT_MINUTES,
    CONF_TTS_ENTITY,
    DEFAULT_ANNOUNCE_MESSAGE,
    DEFAULT_QUIET_ENABLED,
    DEFAULT_QUIET_END,
    DEFAULT_QUIET_START,
    DEFAULT_REPEAT_MINUTES,
    MAX_ANNOUNCEMENTS,
)

_LOGGER = logging.getLogger(__name__)


class AlertManager:
    def __init__(self, hass, entry, data):
        self._hass = hass
        self._entry = entry
        self._tts = data.get(CONF_TTS_ENTITY)
        self._players = list(data.get(CONF_MEDIA_PLAYERS) or [])
        self._notify = list(data.get(CONF_NOTIFY_SERVICES) or [])
        self._message = data.get(CONF_ANNOUNCE_MESSAGE) or DEFAULT_ANNOUNCE_MESSAGE
        self._repeat = float(data.get(CONF_REPEAT_MINUTES, DEFAULT_REPEAT_MINUTES)) * 60
        self._quiet_start = None
        self._quiet_end = None
        if data.get(CONF_QUIET_ENABLED, DEFAULT_QUIET_ENABLED):
            self._quiet_start = dt_util.parse_time(
                data.get(CONF_QUIET_START, DEFAULT_QUIET_START)
            )
            self._quiet_end = dt_util.parse_time(
                data.get(CONF_QUIET_END, DEFAULT_QUIET_END)
            )
        self._announced = 0
        self._timer = None

    def finished(self):
        self.stop()
        self._push()
        self._remind()

    def stop(self):
        if self._timer is not None:
            self._timer()
            self._timer = None
        self._announced = 0

    def _can_speak(self):
        return bool(self._tts and self._players)

    def _quiet_now(self):
        if self._quiet_start is None or self._quiet_end is None:
            return False
        moment = dt_util.as_local(dt_util.utcnow()).time()
        if self._quiet_start < self._quiet_end:
            return self._quiet_start <= moment < self._quiet_end
        return moment >= self._quiet_start or moment < self._quiet_end

    def _seconds_until_quiet_end(self):
        now = dt_util.as_local(dt_util.utcnow())
        end = now.replace(
            hour=self._quiet_end.hour,
            minute=self._quiet_end.minute,
            second=self._quiet_end.second,
            microsecond=0,
        )
        if end <= now:
            end += timedelta(days=1)
        return (end - now).total_seconds() + 1

    def _remind(self):
        self._timer = None
        if not self._can_speak():
            return
        if self._quiet_now():
            self._schedule(self._seconds_until_quiet_end())
            return
        self._entry.async_create_task(self._hass, self._async_speak())
        self._announced += 1
        if self._repeat > 0 and self._announced < MAX_ANNOUNCEMENTS:
            self._schedule(self._repeat)

    def _schedule(self, delay):
        self._timer = async_call_later(self._hass, delay, self._on_timer)

    @callback
    def _on_timer(self, _now):
        self._remind()

    def _push(self):
        for service in self._notify:
            self._entry.async_create_task(self._hass, self._async_push(service))

    async def _async_push(self, service):
        try:
            await self._hass.services.async_call(
                "notify",
                service.removeprefix("notify."),
                {"message": self._message},
                blocking=True,
            )
        except HomeAssistantError as err:
            _LOGGER.warning("Washer notification via %s failed: %s", service, err)

    async def _async_speak(self):
        try:
            await self._hass.services.async_call(
                "tts",
                "speak",
                {
                    "entity_id": self._tts,
                    "media_player_entity_id": self._players,
                    "message": self._message,
                },
                blocking=True,
            )
        except HomeAssistantError as err:
            _LOGGER.warning("Washer announcement failed: %s", err)
