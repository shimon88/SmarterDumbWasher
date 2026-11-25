DOMAIN = "smarter_dumb_washer"

CONF_POWER_SENSOR = "power_sensor"
CONF_DOOR_SENSOR = "door_sensor"
CONF_START_THRESHOLD = "start_power_threshold"
CONF_IDLE_THRESHOLD = "idle_power_threshold"
CONF_END_DELAY = "end_delay"
CONF_MIN_CYCLE = "min_cycle"
CONF_DOOR_CLOSED_START = "door_closed_start"
CONF_TTS_ENTITY = "tts_entity"
CONF_MEDIA_PLAYERS = "media_players"
CONF_NOTIFY_SERVICES = "notify_services"
CONF_ANNOUNCE_MESSAGE = "announce_message"
CONF_REPEAT_MINUTES = "repeat_minutes"
CONF_QUIET_ENABLED = "quiet_enabled"
CONF_QUIET_START = "quiet_start"
CONF_QUIET_END = "quiet_end"

DEFAULT_ANNOUNCE_MESSAGE = "The washer is done"
DEFAULT_REPEAT_MINUTES = 10
DEFAULT_QUIET_ENABLED = False
DEFAULT_QUIET_START = "22:00:00"
DEFAULT_QUIET_END = "07:00:00"
MAX_ANNOUNCEMENTS = 6

DEFAULT_START_THRESHOLD = 10.0
DEFAULT_IDLE_THRESHOLD = 2.0
DEFAULT_END_DELAY = 180
DEFAULT_MIN_CYCLE = 600
DEFAULT_DOOR_CLOSED_START = True

ON_POWER = 4.0
RUN_WINDOW = 20.0
RUN_AVERAGE = 20.0

STATE_IDLE = "idle"
STATE_MACHINE_ON = "on"
STATE_RUNNING = "running"
STATE_FINISHED = "finished"

SERVICE_LEARN_START = "learn_start"
SERVICE_LEARN_CANCEL = "learn_cancel"
SERVICE_DELETE_PROGRAM = "delete_program"
SERVICE_RENAME_PROGRAM = "rename_program"

ATTR_PROGRAM_NAME = "program_name"
ATTR_NEW_NAME = "new_name"
ATTR_PROGRAMS = "programs"
ATTR_LEARNING = "learning"
ATTR_LEARN_PROGRAM = "program"
ATTR_SAMPLES = "samples"
ATTR_LAST_RESULT = "last_result"
ATTR_LAST_PROGRAM = "last_program"

LEARN_IDLE = "idle"
LEARN_WAITING = "waiting"
LEARN_RECORDING = "recording"

LEARN_STORED = "stored"
LEARN_TOO_SHORT = "too_short"
LEARN_EMPTY = "empty"

STAGE_FILL = "fill"
STAGE_WASH = "wash"
STAGE_HEAT = "heat"
STAGE_RINSE = "rinse"
STAGE_SPIN = "spin"
STAGE_UNKNOWN = "unknown"

PROGRAM_UNKNOWN = "unknown"

SAMPLE_SECONDS = 10
CONFIDENCE_MIN = 0.7

ATTR_ETA = "eta"
