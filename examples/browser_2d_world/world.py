"""Pure point-world math for the browser demo; movement is an engineered decoder."""
from dataclasses import asdict, dataclass
import math


WORLD_MIN = -12.0
WORLD_MAX = 12.0


@dataclass
class WorldState:
    x: float = 0.0
    y: float = 0.0
    heading: float = 0.0
    light_x: float = 10.0
    light_y: float = 5.0

    def as_dict(self):
        return asdict(self)


class WorldAdapter:
    """Encode light bearing and decode descending rates into application motion."""

    def encode(self, environment):
        bearing = math.atan2(
            environment["light_y"] - environment["y"],
            environment["light_x"] - environment["x"],
        )
        difference = math.atan2(
            math.sin(bearing - environment["heading"]),
            math.cos(bearing - environment["heading"]),
        )
        return {
            "vision": {
                "left": max(0.0, math.cos(difference - 0.5)),
                "right": max(0.0, math.cos(difference + 0.5)),
            }
        }

    def decode(self, brain_output):
        left = brain_output["left_rate_hz"] or 0.0
        right = brain_output["right_rate_hz"] or 0.0
        return {
            "speed": min(brain_output["mean_rate_hz"] / 100.0, 1.0),
            "rotation": (left - right) / 100.0,
        }


def advance_world(world: WorldState, action: dict, *, scale=0.1):
    """Apply the explicit application decoder; this is not biological locomotion."""
    world.heading += float(action["rotation"]) * scale
    world.heading = math.atan2(math.sin(world.heading), math.cos(world.heading))
    world.x += float(action["speed"]) * math.cos(world.heading) * scale
    world.y += float(action["speed"]) * math.sin(world.heading) * scale
    world.x = min(max(world.x, WORLD_MIN), WORLD_MAX)
    world.y = min(max(world.y, WORLD_MIN), WORLD_MAX)
    return world
