# Phase 3: Di chuyển theo Waypoint + Social Force tránh va chạm
# human/motion_model.py
import math
from typing import Sequence
from .human_agent import HumanAgent
from .groups import HumanGroup


def update_humans_motion(
    humans: Sequence[HumanAgent],
    groups: Sequence[HumanGroup],
    static_objects: Sequence[object],
    semi_static_objects: Sequence[object],
    robot: object,
    dt: float,
    world_width: float,
    world_height: float,
) -> None:
    """Advance humans toward their waypoints while keeping them in the world."""
    del static_objects, semi_static_objects, robot

    for human in humans:
        if human.is_interacting_member or not human.waypoints:
            human.set_velocity(0.0, 0.0)
            continue

        target = human.waypoints[human.current_wp_idx % len(human.waypoints)]
        dx = target[0] - human.x
        dy = target[1] - human.y
        distance = math.hypot(dx, dy)
        if distance < max(0.15, human.desired_speed * dt):
            human.current_wp_idx = (human.current_wp_idx + 1) % len(human.waypoints)
            target = human.waypoints[human.current_wp_idx]
            dx = target[0] - human.x
            dy = target[1] - human.y
            distance = math.hypot(dx, dy)

        if distance < 1e-6:
            human.set_velocity(0.0, 0.0)
            continue

        speed = min(human.desired_speed, distance / max(dt, 1e-6))
        vx = speed * dx / distance
        vy = speed * dy / distance
        human.set_velocity(vx, vy)
        human.x = min(world_width - human.radius, max(human.radius, human.x + vx * dt))
        human.y = min(world_height - human.radius, max(human.radius, human.y + vy * dt))

    for group in groups:
        group.update_geometry()
