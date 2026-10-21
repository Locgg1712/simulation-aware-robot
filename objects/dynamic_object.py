# Phase 2: Vật thể chuyển động (xe đẩy, robot khác) + dự đoán quỹ đạo ngắn hạn
# objects/dynamic_object.py
import math
from typing import Sequence
from .base_object import BaseObject, ObjectType
from .static_object import StaticObject
from environment.physics import check_robot_static_collision


class DynamicObject(BaseObject):
    """
    Vật thể động thông thường (Dynamic Object): Xe đẩy tự động, robot khác, vật nuôi.
    Di chuyển tuần hoàn qua danh sách các Waypoints hoặc bật ngược hướng khi gặp tường.
    """

    def __init__(
        self,
        obj_id: int,
        x: float,
        y: float,
        radius: float = 0.35,
        speed: float = 0.65,
        theta: float = 0.0,
        waypoints: list[tuple[float, float]] | None = None,
        name: str = "agv_cart",
    ):
        super().__init__(
            obj_id=obj_id,
            x=x,
            y=y,
            radius=radius,
            obj_type=ObjectType.DYNAMIC,
            name=name,
        )
        self.speed = float(speed)
        self.theta = float(theta)
        self.waypoints = waypoints or []
        self.current_wp_idx = 0

    @property
    def vx(self) -> float:
        return self.speed * math.cos(self.theta)

    @property
    def vy(self) -> float:
        return self.speed * math.sin(self.theta)

    def update(
        self,
        dt: float,
        static_objects: Sequence[StaticObject],
        world_width: float,
        world_height: float,
    ):
        """Cập nhật vị trí theo Waypoints hoặc đổi hướng khi chạm chướng ngại vật tĩnh."""
        if self.waypoints:
            target_x, target_y = self.waypoints[self.current_wp_idx]
            dx = target_x - self.x
            dy = target_y - self.y
            dist = math.hypot(dx, dy)
            if dist < 0.35:
                self.current_wp_idx = (self.current_wp_idx + 1) % len(self.waypoints)
                target_x, target_y = self.waypoints[self.current_wp_idx]
                dx = target_x - self.x
                dy = target_y - self.y
            self.theta = math.atan2(dy, dx)

        next_x = self.x + self.vx * dt
        next_y = self.y + self.vy * dt

        collided, _ = check_robot_static_collision(
            x=next_x,
            y=next_y,
            radius=self.radius,
            static_objects=static_objects,
            world_width=world_width,
            world_height=world_height,
        )

        if collided:
            # Đảo chiều góc di chuyển và chuyển sang waypoint tiếp theo
            self.theta = math.atan2(
                math.sin(self.theta + math.pi), math.cos(self.theta + math.pi)
            )
            if self.waypoints:
                self.current_wp_idx = (self.current_wp_idx + 1) % len(self.waypoints)
        else:
            self.x = next_x
            self.y = next_y

    def predict_trajectory(
        self, dt: float = 0.1, horizon_sec: float = 2.0, step_stride: int = 3
    ) -> list[tuple[float, float]]:
        """
        Dự đoán quỹ đạo ngắn hạn giả định vận tốc không đổi trong T_pred (1.0s - 3.0s):
        x_{t+k} = x_t + v_t * cos(theta_t) * (k * dt)
        y_{t+k} = y_t + v_t * sin(theta_t) * (k * dt)
        """
        num_steps = int(round(horizon_sec / dt))
        points: list[tuple[float, float]] = []
        for k in range(step_stride, num_steps + 1, step_stride):
            t_future = k * dt
            px = self.x + self.vx * t_future
            py = self.y + self.vy * t_future
            points.append((px, py))
        return points