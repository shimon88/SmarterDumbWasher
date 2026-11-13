# Smarter Dumb Washer

Home Assistant custom integration. It watches a smart-plug power sensor and a door sensor, learns named wash programs from power traces, and reports the running program, stage, and progress.

## Install

HACS: add this repository as a custom repository (Integration), then install **Smarter Dumb Washer**.

Manual: copy `custom_components/smarter_dumb_washer` into `config/custom_components` and restart Home Assistant.

## Setup

Settings → Devices & services → Add integration → **Smarter Dumb Washer**.

- **Power sensor** — plug power, in watts
- **Door sensor** — washer door
- Start threshold, idle threshold, end delay, minimum cycle, and whether the door must be closed to start

A State sensor reports `idle`, `running`, or `finished`. Runs shorter than the minimum cycle are ignored. Opening the door after a finished cycle returns the sensor to `idle`.

## License

MIT. See [LICENSE](LICENSE).
