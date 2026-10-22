# environment/physics.py
from __future__ import annotations

import math
from typing import TYPE_CHECKING, Sequence
from objects.static_object import StaticObject, ShapeType
from objects.semi_static_object import SemiStaticObject

if TYPE_CHECKING:
    from objects.dynamic_object import DynamicObject
    from objects.base_object import BaseObject
    from human.human_agent import HumanAgent


def check_circle_circle_collision(
    x1: float, y1: float, r1: float, x2: float, y2: float, r2: float
) -> bool:
    dist_sq = (x1 - x2) ** 2 + (y1 - y2) ** 2
    return dist_sq <= (r1 + r2) ** 2


def check_circle_rect_collision(
    cx: float,
    cy: float,
    radius: float,
    rect_x: float,
    rect_y: float,
    width: float,
    height: float,
) -> bool:
    closest_x = max(rect_x, min(cx, rect_x + width))
    closest_y = max(rect_y, min(cy, rect_y + height))
    dist_x = cx - closest_x
    dist_y = cy - closest_y
    return (dist_x ** 2 + dist_y ** 2) <= (radius ** 2)


def check_robot_static_collision(
    x: float,
    y: float,
    radius: float,
    static_objects: Sequence[StaticObject],
    world_width: float,
    world_height: float,
) -> tuple[bool, StaticObject | None]:
    if (
        x - radius < 0.0
        or x + radius > world_width
        or y - radius < 0.0
        or y + radius > world_height
    ):
        return True, None

    for obj in static_objects:
        if obj.shape == ShapeType.CIRCLE:
            if check_circle_circle_collision(x, y, radius, obj.x, obj.y, obj.radius):
                return True, obj
        elif obj.shape == ShapeType.RECTANGLE:
            rx, ry, rw, rh = obj.bbox
            if check_circle_rect_collision(x, y, radius, rx, ry, rw, rh):
                return True, obj

    return False, None


def check_robot_full_collision(
    x: float,
    y: float,
    radius: float,
    static_objects: Sequence[StaticObject],
    semi_static_objects: Sequence[SemiStaticObject],
    dynamic_objects: Sequence[DynamicObject],
    world_width: float,
    world_height: float,
    humans: Sequence[HumanAgent] = (),
) -> tuple[bool, BaseObject | None]:
    """
    Kiểm tra va chạm toàn diện của Robot với:
    1. Biên bản đồ & Static Objects
    2. Semi-static Objects chưa mở hoàn toàn (not passable)
    3. Dynamic Objects
    4. Humans (Con người)
    """
    collided, static_hit = check_robot_static_collision(
        x, y, radius, static_objects, world_width, world_height
    )
    if collided:
        return True, static_hit

    for door in semi_static_objects:
        if not door.passable:
            rx, ry, rw, rh = door.bbox
            if check_circle_rect_collision(x, y, radius, rx, ry, rw, rh):
                return True, door

    for dyn in dynamic_objects:
        if check_circle_circle_collision(x, y, radius, dyn.x, dyn.y, dyn.radius):
            return True, dyn

    for h in humans:
        if check_circle_circle_collision(x, y, radius, h.x, h.y, h.radius):
            return True, h

    return False, None


def _ray_circle_intersection(
    ox: float, oy: float, dx: float, dy: float, cx: float, cy: float, r: float, max_dist: float
) -> float:
    fx = ox - cx
    fy = oy - cy
    b = 2.0 * (fx * dx + fy * dy)
    c = (fx * fx + fy * fy) - r * r
    discriminant = b * b - 4.0 * c
    if discriminant < 0.0:
        return max_dist
    sqrt_disc = math.sqrt(discriminant)
    t1 = (-b - sqrt_disc) / 2.0
    t2 = (-b + sqrt_disc) / 2.0
    if 0.0 <= t1 <= max_dist:
        return t1
    if 0.0 <= t2 <= max_dist:
        return t2
    return max_dist


def _ray_rect_intersection(
    ox: float,
    oy: float,
    dx: float,
    dy: float,
    rx: float,
    ry: float,
    rw: float,
    rh: float,
    max_dist: float,
) -> float:
    t_min = 0.0
    t_max = max_dist

    if abs(dx) < 1e-9:
        if ox < rx or ox > rx + rw:
            return max_dist
    else:
        tx1 = (rx - ox) / dx
        tx2 = (rx + rw - ox) / dx
        t_min = max(t_min, min(tx1, tx2))
        t_max = min(t_max, max(tx1, tx2))

    if abs(dy) < 1e-9:
        if oy < ry or oy > ry + rh:
            return max_dist
    else:
        ty1 = (ry - oy) / dy
        ty2 = (ry + rh - oy) / dy
        t_min = max(t_min, min(ty1, ty2))
        t_max = min(t_max, max(ty1, ty2))

    if t_max >= t_min and 0.0 <= t_min <= max_dist:
        return t_min
    return max_dist


def cast_lidar_rays(
    rx: float,
    ry: float,
    r_theta: float,
    num_rays: int,
    max_range: float,
    static_objects: Sequence[StaticObject],
    world_width: float,
    world_height: float,
    semi_static_objects: Sequence[SemiStaticObject] = (),
) -> tuple[list[float], list[tuple[float, float]]]:
    distances: list[float] = []
    hit_points: list[tuple[float, float]] = []

    for i in range(num_rays):
        angle = r_theta + (2.0 * math.pi * i) / num_rays
        dx = math.cos(angle)
        dy = math.sin(angle)
        min_t = max_range

        if dx > 1e-9:
            min_t = min(min_t, (world_width - rx) / dx)
        elif dx < -1e-9:
            min_t = min(min_t, (0.0 - rx) / dx)
        if dy > 1e-9:
            min_t = min(min_t, (world_height - ry) / dy)
        elif dy < -1e-9:
            min_t = min(min_t, (0.0 - ry) / dy)

        for obj in static_objects:
            if obj.shape == ShapeType.CIRCLE:
                t = _ray_circle_intersection(rx, ry, dx, dy, obj.x, obj.y, obj.radius, min_t)
            else:
                bx, by, bw, bh = obj.bbox
                t = _ray_rect_intersection(rx, ry, dx, dy, bx, by, bw, bh, min_t)
            if t < min_t:
                min_t = t

        for door in semi_static_objects:
            if not door.passable:
                bx, by, bw, bh = door.bbox
                t = _ray_rect_intersection(rx, ry, dx, dy, bx, by, bw, bh, min_t)
                if t < min_t:
                    min_t = t

        distances.append(min_t)
        hit_points.append((rx + dx * min_t, ry + dy * min_t))

    return distances, hit_points