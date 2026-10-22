# perception/ground_truth.py
import math
from typing import Sequence
from objects.robot import Robot
from objects.semi_static_object import SemiStaticObject
from objects.dynamic_object import DynamicObject
from human.human_agent import HumanAgent


def extract_local_perception(
    robot: Robot,
    semi_static_objects: Sequence[SemiStaticObject],
    dynamic_objects: Sequence[DynamicObject],
    humans: Sequence[HumanAgent] = (),
) -> dict:
    """
    Trích xuất Ground-Truth các đối tượng Semi-static, Dynamic và Human
    nằm trong bán kính cảm biến R_sensor = 6.0m quanh Robot.
    Sắp xếp theo khoảng cách tăng dần để phục vụ Top-K Objects và Top-M Humans.
    """
    detected_semi: list[tuple[float, SemiStaticObject]] = []
    detected_dyn: list[tuple[float, DynamicObject]] = []
    detected_humans: list[tuple[float, HumanAgent]] = []

    for door in semi_static_objects:
        dist = math.hypot(door.x - robot.x, door.y - robot.y)
        if dist <= robot.sensor_radius + door.radius:
            detected_semi.append((dist, door))

    for dyn in dynamic_objects:
        dist = math.hypot(dyn.x - robot.x, dyn.y - robot.y)
        if dist <= robot.sensor_radius + dyn.radius:
            detected_dyn.append((dist, dyn))

    for h in humans:
        dist = math.hypot(h.x - robot.x, h.y - robot.y)
        if dist <= robot.sensor_radius + h.radius:
            detected_humans.append((dist, h))

    detected_semi.sort(key=lambda item: item[0])
    detected_dyn.sort(key=lambda item: item[0])
    detected_humans.sort(key=lambda item: item[0])

    return {
        "semi_static": [item[1] for item in detected_semi],
        "dynamic": [item[1] for item in detected_dyn],
        "humans": [item[1] for item in detected_humans],
    }