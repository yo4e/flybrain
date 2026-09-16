# Browser 2D world

Interactive browser wrapper around the repository's point-world example.

The browser UI is an observation tool:

- drag one light source around a bounded 2D world;
- advance the selected FlyBrain dataset in discrete simulated-time steps;
- inspect encoded bilateral visual input and annotation-derived descending activity;
- move the on-screen fly with an explicit application-level speed/rotation decoder;
- use only the latest integration interval for movement while keeping cumulative activity as telemetry.

The movement decoder is **not** a validated biological locomotion model. It uses
descending-neuron spike-count differences from only the latest requested brain step;
rates reported by the core SDK since reset are retained separately as cumulative telemetry.

## Quick check with synthetic data

From the repository root:

```bash
python examples/browser_2d_world/app.py --dataset synthetic --port 8000
```

Open the forwarded/local port in a browser.

## Run with MaleCNS in Codespaces

First complete the Codespaces first boot so the real dataset is cached:

```bash
bash scripts/codespaces_first_boot.sh
```

Then launch:

```bash
python examples/browser_2d_world/app.py --dataset malecns --port 8000
```

In GitHub Codespaces, use the normal forwarded-port link that VS Code offers. Keep the port **private**. The app serves HTML and JSON from the same origin, so a public port and cross-origin API access are unnecessary.

The app never downloads MaleCNS on page load. If the dataset is not cached, startup fails with the normal `flybrain pull malecns` guidance.

## Public sharing boundary

A future GitHub Pages site may explain or preview this experiment, but it must remain static. It must not call a maintainer-owned Codespace.

Anyone who wants to run the real simulation should create and use a Codespace on their own GitHub account.

## Scientific boundary

- reconstructed connectome topology and synapse counts come from the selected dataset;
- LIF dynamics are modeled;
- the bilateral brightness/bearing encoder is modeled;
- `speed` and `rotation` are engineered application outputs;
- motion on the canvas must not be described as a measured fly action, preference, intent, or validated biological motor command.
