# Smarter Dumb Washer

Home Assistant custom integration. It watches a smart-plug power sensor and a door sensor, learns named wash programs from power traces, and reports the running program, stage, and progress.

## Install

HACS: add this repository as a custom repository (Integration), then install **Smarter Dumb Washer**.

Manual: copy `custom_components/smarter_dumb_washer` into `config/custom_components` and restart Home Assistant.

Requires Home Assistant 2025.1.0 or newer.

## Setup

Settings → Devices & services → Add integration → **Smarter Dumb Washer**.

- **Power sensor** — plug power, in watts
- **Door sensor** — washer door
- Start threshold, idle threshold, end delay, minimum cycle, and whether the door must be closed to start

Change those thresholds later under the device's **Configure** button. Saving reloads the device. A cycle already running starts its trace over.

## Sensors

| Sensor | Values |
| --- | --- |
| State | `idle`, `running`, `finished` |
| Program | Learned name, or `unknown` until the live trace matches |
| Stage | `fill`, `wash`, `heat`, `rinse`, `spin`, or `unknown` |
| Progress | Percent through the matched program. Attribute `eta` is the remaining seconds |

Runs shorter than the minimum cycle are ignored. Opening the door after a finished cycle returns State to `idle` and clears the match. The State sensor attributes `programs` and `learning` list saved names and the program currently being learned.

## Learn a program

Call the services on the State sensor (or any sensor from this device).

1. **Start learning** with a program name. The next full cycle is recorded.
2. Close the door and run that wash. When power stays under the idle threshold for the end delay, the trace is stored.
3. Stages are split from the power level. Learning the same name again averages the new run into the saved program.
4. **Cancel learning** drops a recording in progress. **Delete program** and **Rename program** change the saved list.

```yaml
action: smarter_dumb_washer.learn_start
target:
  entity_id: sensor.washer_state
data:
  program_name: Cotton
```

Repeat for each wash you want recognized. A later cycle of the same shape reports that program, its stage, and progress.

## Validation

Pull requests run three checks:

- pytest, in `.github/workflows/test.yml`
- [HACS validation](https://github.com/hacs/action) for an integration (`hacs.json`, manifest, README)
- [hassfest](https://developers.home-assistant.io/docs/development_validation/) for the manifest, translations, and services

`hacs.json` sets `homeassistant` to `2025.1.0` and `render_readme` so HACS shows this file.

## License

MIT. See [LICENSE](LICENSE).
