"""Same-origin browser observation box for FlyBrain closed-loop experiments."""
from argparse import ArgumentParser
from pathlib import Path
from threading import RLock
from urllib.parse import urlsplit

import numpy as np
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel, ConfigDict, Field
from starlette.middleware.trustedhost import TrustedHostMiddleware

from flybrain import FlyBrain
from flybrain.brain import population

try:
    from .world import WORLD_MAX, WORLD_MIN, WorldAdapter, WorldState, advance_world
except ImportError:  # Allows: python examples/browser_2d_world/app.py
    from world import WORLD_MAX, WORLD_MIN, WorldAdapter, WorldState, advance_world


HERE = Path(__file__).resolve().parent


class StepRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)
    light_x: float = Field(ge=WORLD_MIN, le=WORLD_MAX)
    light_y: float = Field(ge=WORLD_MIN, le=WORLD_MAX)
    brain_ms: int = Field(default=10, ge=1, le=100)


def interval_descending_output(brain, before_counts, after_counts, ms):
    """Compute rates for only this integration interval, not since reset."""
    if ms <= 0:
        raise ValueError("Interval duration must be positive")

    indices = np.array(
        [i for i, neuron in enumerate(brain.connectome.neurons) if population(neuron, "descending")],
        dtype=np.int64,
    )
    if not len(indices):
        raise ValueError("No descending neurons annotated in this dataset")

    delta = after_counts - before_counts
    rates = delta.astype(np.float64) * (1000.0 / float(ms))

    def side_mean(side):
        selected = np.array(
            [i for i in indices if brain.connectome.neurons[i].get("side") == side],
            dtype=np.int64,
        )
        return float(rates[selected].mean()) if len(selected) else None

    return {
        "population": "descending",
        "time_ms": brain.engine.time_ms,
        "window": f"last {ms:g} ms",
        "units": "Hz",
        "modeled": True,
        "count": int(len(indices)),
        "mean_rate_hz": float(rates[indices].mean()),
        "left_rate_hz": side_mean("left"),
        "right_rate_hz": side_mean("right"),
        "interpretation": (
            "Activity during only the latest integration interval of the "
            "annotation-derived descending population, not an action command."
        ),
        "source": brain.connectome.provenance.get("source"),
        "step_spikes": int(delta.sum()),
    }


def create_app(dataset="malecns", brain=None):
    brain = brain if brain is not None else FlyBrain(dataset)
    app = FastAPI(title="FlyBrain browser 2D world", version="0.1.0")
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=["localhost", "127.0.0.1", "[::1]", "testserver", "*.app.github.dev"],
    )
    app.state.brain = brain
    app.state.world = WorldState()
    app.state.adapter = WorldAdapter()
    lock = RLock()

    @app.middleware("http")
    async def same_origin_and_size(request: Request, call_next):
        try:
            length = int(request.headers.get("content-length", "0"))
        except ValueError:
            return JSONResponse({"detail": "Invalid content length"}, status_code=400)
        if length > 65536:
            return JSONResponse({"detail": "Request too large"}, status_code=413)

        origin = request.headers.get("origin")
        if origin:
            origin_host = urlsplit(origin).netloc
            request_host = request.headers.get("host", "")
            if origin_host != request_host:
                return JSONResponse(
                    {"detail": "Cross-origin requests are disabled for this example"},
                    status_code=403,
                )
        return await call_next(request)

    def snapshot(*, encoded=None, step_output=None, cumulative_output=None, action=None, step_ms=None):
        result = {
            "dataset": brain.connectome.provenance.get("dataset", dataset),
            "world": app.state.world.as_dict(),
            "modeled": True,
            "labels": {
                "topology": "Reconstructed connectome topology/synapse counts from the selected dataset.",
                "dynamics": "LIF dynamics and sensory encoding are modeled assumptions.",
                "action": "Speed/rotation are engineered application decoding, not validated biological motor commands.",
                "window": "Movement uses only the latest brain step; cumulative rates are telemetry only.",
            },
        }
        if encoded is not None:
            result["input"] = encoded["vision"]
        if step_output is not None and cumulative_output is not None:
            result["brain"] = {
                "time_ms": cumulative_output["time_ms"],
                "step_ms": step_ms,
                "step_spikes": step_output["step_spikes"],
                "cumulative_spikes": int(brain.engine.counts.sum()),
                "step_mean_rate_hz": step_output["mean_rate_hz"],
                "step_left_rate_hz": step_output["left_rate_hz"],
                "step_right_rate_hz": step_output["right_rate_hz"],
                "cumulative_mean_rate_hz": cumulative_output["mean_rate_hz"],
                "cumulative_left_rate_hz": cumulative_output["left_rate_hz"],
                "cumulative_right_rate_hz": cumulative_output["right_rate_hz"],
            }
        if action is not None:
            result["action"] = action
        return result

    @app.get("/", response_class=HTMLResponse)
    def index():
        return (HERE / "index.html").read_text(encoding="utf-8")

    @app.get("/api/world/state")
    def state():
        with lock:
            return snapshot()

    @app.post("/api/world/reset")
    def reset():
        with lock:
            brain.reset()
            app.state.world = WorldState()
            return snapshot()

    @app.post("/api/world/step")
    def step(payload: StepRequest):
        with lock:
            app.state.world.light_x = payload.light_x
            app.state.world.light_y = payload.light_y
            encoded = app.state.adapter.encode(app.state.world.as_dict())
            brain.stimulus(encoded)

            before_counts = brain.engine.counts.copy()
            brain.step(payload.brain_ms)
            after_counts = brain.engine.counts.copy()

            step_output = interval_descending_output(
                brain, before_counts, after_counts, payload.brain_ms
            )
            cumulative_output = brain.output("descending")

            # Movement is intentionally based on only the latest interval.
            action = app.state.adapter.decode(step_output)
            advance_world(app.state.world, action)

            return snapshot(
                encoded=encoded,
                step_output=step_output,
                cumulative_output=cumulative_output,
                action=action,
                step_ms=payload.brain_ms,
            )

    return app


def main():
    parser = ArgumentParser(description="Run the FlyBrain browser 2D world.")
    parser.add_argument("--dataset", default="malecns", choices=("malecns", "flywire", "synthetic"))
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()

    try:
        application = create_app(dataset=args.dataset)
    except FileNotFoundError as error:
        parser.error(str(error))

    import uvicorn

    uvicorn.run(application, host=args.host, port=args.port)


if __name__ == "__main__":
    main()
