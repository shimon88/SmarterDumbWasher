DOMAIN = "smarter_dumb_washer"

CONF_POWER_SENSOR = "power_sensor"
CONF_DOOR_SENSOR = "door_sensor"
CONF_START_THRESHOLD = "start_power_threshold"
CONF_IDLE_THRESHOLD = "idle_power_threshold"
CONF_END_DELAY = "end_delay"
CONF_MIN_CYCLE = "min_cycle"
CONF_DOOR_CLOSED_START = "door_closed_start"

DEFAULT_START_THRESHOLD = 10.0
DEFAULT_IDLE_THRESHOLD = 2.0
DEFAULT_END_DELAY = 180
DEFAULT_MIN_CYCLE = 600
DEFAULT_DOOR_CLOSED_START = True

STATE_IDLE = "idle"
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
