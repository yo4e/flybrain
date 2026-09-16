# Browser 2D world plan

Status: implementation plan for the first browser-hosted MaleCNS closed-loop experiment.

## Goal

Run the existing FlyBrain point-world idea as an interactive browser experiment inside GitHub Codespaces, without requiring a local Python installation.

The first version is an **observation box**, not a real-time game:

- a 2D canvas shows one fly and one movable light source;
- the world is encoded into bilateral visual stimulus;
- MaleCNS + the current LIF model advances in discrete steps;
- annotation-derived descending activity is decoded into engineered speed/rotation;
- the browser displays both the fly motion and the raw modeled measurements.

This remains an engineering demo. It must not describe decoded movement as a validated biological motor command.

## Existing pieces to reuse

The repository already contains most of the backend concepts:

- `examples/simple_2d_world/main.py` contains a headless closed-loop world and `WorldAdapter`;
- `flybrain.adapters.interact` defines the encode → brain step → decode boundary;
- `flybrain.server` already provides a local FastAPI pattern;
- Codespaces support is available on `experiment/initial-validation`;
- MaleCNS has been verified in Codespaces with 166,700 retained neurons and 25,582,938 directed edges.

Do not duplicate core connectome or LIF logic in browser code.

## Observed model behavior to account for

Initial Codespaces experiments on the current defaults showed:

| Side | Intensity | Total spikes | Descending mean Hz |
| --- | ---: | ---: | ---: |
| left | 0.50 | 0 | 0 |
| left | 0.75 | 404,585 | 35.819 |
| left | 1.00 | 453,068 | 39.569 |
| right | 0.50 | 0 | 0 |
| right | 0.75 | 413,537 | 40.300 |
| right | 1.00 | 469,539 | 42.873 |

The visual input therefore has a strong model-dependent threshold under the current LIF parameters. The browser must show the actual encoded left/right intensities so the dead zone is visible rather than hidden.

For MVP, keep the existing encoder mathematically explicit. Do **not** silently tune or calibrate the biological interpretation. A later experiment can compare raw and remapped encoders.

## Architecture

Use one FastAPI process for both the page and JSON API.

```text
Browser Canvas
    │
    │ world state / step request
    ▼
FastAPI example app (same origin)
    │
    ├─ WorldAdapter.encode(...)
    ▼
FlyBrain("malecns")
    │
    ├─ brain.step(ms)
    ▼
descending population summary
    │
    ├─ WorldAdapter.decode(...)
    ▼
updated world state + measurements
    │
    └──────────────► Browser Canvas / telemetry
```

Serving the HTML and API from the same origin preserves the current security choice in `flybrain.server`: browser cross-origin access does not need to be enabled globally.

Keep this as an example application rather than expanding the core REST API until the interaction model proves useful.

## MVP UI

One page is enough.

### Canvas

- fly position and heading;
- draggable light source;
- short motion trail;
- fixed world bounds.

### Controls

- **Step**: advance one closed-loop tick;
- **Run / Pause**: repeatedly request ticks at a conservative cadence;
- **Reset**: reset brain and world;
- brain-step duration selector, initially 10 ms;
- optional trail toggle.

Do not promise real-time simulation. The first real-data run measured about 3.3 seconds for 100 simulated ms in Codespaces.

### Telemetry

Always expose:

- encoded visual input: left / right;
- simulated brain time;
- total spikes;
- descending mean Hz;
- descending left Hz / right Hz;
- engineered speed;
- engineered rotation;
- labels stating that topology is reconstructed data while dynamics, sensory encoding, and motor decoding are modeled.

## Proposed API

Example-local endpoints, not core SDK endpoints:

### `POST /api/world/step`

Request:

```json
{
  "light_x": 8.0,
  "light_y": 4.0,
  "brain_ms": 10
}
```

The server owns fly position/heading and one `FlyBrain` instance.

Response:

```json
{
  "world": {
    "x": 0.1,
    "y": 0.0,
    "heading": 0.02,
    "light_x": 8.0,
    "light_y": 4.0
  },
  "input": {
    "left": 0.82,
    "right": 0.31
  },
  "brain": {
    "time_ms": 10.0,
    "spikes": 12345,
    "mean_rate_hz": 38.2,
    "left_rate_hz": 40.1,
    "right_rate_hz": 35.8
  },
  "action": {
    "speed": 0.382,
    "rotation": 0.043
  },
  "modeled": true
}
```

### `POST /api/world/reset`

Reset the LIF state and restore the default world.

### `GET /api/world/state`

Return current world state and provenance/assumption labels without stepping.

## Work units

### 1. Extract the point-world logic for reuse

- move or copy the pure world/adapter math into an importable example-local module;
- preserve current formulas and labels;
- add deterministic unit tests using `synthetic` data;
- keep application actions outside neuron mapping code.

Done when the existing headless example still works and tests cover encode/decode/world update separately.

### 2. Add the browser example backend

Create `examples/browser_2d_world/` with a FastAPI app that:

- loads `malecns` explicitly;
- serves frontend assets and API from the same origin;
- serializes state-changing requests;
- bounds `brain_ms` and validates light coordinates;
- fails clearly if MaleCNS has not been pulled;
- exposes reset/state/step endpoints.

Done when API tests run with `synthetic` and no real download in CI.

### 3. Add the Canvas frontend

Use plain HTML/CSS/JavaScript for the first version.

- no React/Vite build pipeline yet;
- draw fly, light and trail on `<canvas>`;
- drag the light with pointer input;
- implement Step, Run/Pause, Reset;
- display telemetry from every response;
- visibly label modeled vs reconstructed quantities.

Done when the page can drive the synthetic backend end-to-end in a browser.

### 4. Make Codespaces launch simple

Add one explicit launcher, for example:

```bash
python examples/browser_2d_world/app.py --dataset malecns --port 8000
```

Document Codespaces port forwarding and the expected browser flow.

Do not automatically make the port public. Do not auto-download MaleCNS from page load.

Done when an existing Codespace with the cached MaleCNS can launch the page with one command.

### 5. Real MaleCNS smoke test and observations

In Codespaces:

- reset;
- place light left, right, ahead and behind;
- execute several fixed 10 ms steps per condition;
- record encoded input, spikes, descending activity and resulting motion;
- verify that reset reproduces deterministic runs;
- note dead-zone/threshold behavior instead of hiding it.

Do not treat movement direction as validated fly behavior.

Done when a short observation log is checked into `docs/` with exact parameters and provenance.

## Out of scope for the first browser version

- calibrated retina or locomotion;
- WebGPU/CUDA;
- morphology/3D rendering;
- plasticity or learning;
- multiple simultaneous brains;
- public internet hosting;
- authentication;
- React/game-engine migration;
- claims about preference, intent, consciousness, or biological motor correctness.

## Implementation order

Implement units 1 → 2 → 3 → 4 in one small feature branch, then perform unit 5 manually in Codespaces.

Only after the real-data smoke test should we decide whether to:

1. improve the visual encoder;
2. add richer sensory channels;
3. add obstacles/food/odor;
4. attempt a more game-like continuous loop.
