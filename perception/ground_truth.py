# Phase 2-3: Trích xuất đối tượng trong bán kính R_sensor + Raycast
# perception/ground_truth.py
import math
from typing import Sequence
from objects.robot import Robot
from objects.semi_static_object import SemiStaticObject
from objects.dynamic_object import DynamicObject


def extract_local_perception(
    robot: Robot,
    semi_static_objects: Sequence[SemiStaticObject],
    dynamic_objects: Sequence[DynamicObject],
) -> dict:
    """
    Trích xuất Ground-Truth các vật thể Semi-static và Dynamic nằm trong bán kính R_sensor.
    Sắp xếp theo khoảng cách tới tâm Robot tăng dần.
    """
    detected_semi: list[tuple[float, SemiStaticObject]] = []
    detected_dyn: list[tuple[float, DynamicObject]] = []

    for door in semi_static_objects:
        dist = math.hypot(door.x - robot.x, door.y - robot.y)
        if dist <= robot.sensor_radius + door.radius:
            detected_semi.append((dist, door))

    for dyn in dynamic_objects:
        dist = math.hypot(dyn.x - robot.x, dyn.y - robot.y)
        if dist <= robot.sensor_radius + dyn.radius:
            detected_dyn.append((dist, dyn))

    detected_semi.sort(key=lambda item: item[0])
    detected_dyn.sort(key=lambda item: item[0])

    return {
        "semi_static": [item[1] for item in detected_semi],
        "dynamic": [item[1] for item in detected_dyn],
    }