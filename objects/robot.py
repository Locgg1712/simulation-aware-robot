from enum import IntEnum
import math
from .base_object import BaseObject, ObjectType


class RobotAction(IntEnum):
    """6 hành động rời rạc chuẩn trong Discrete Action Space."""
    FORWARD = 0      # v = v_max (1.0 m/s), omega = 0
    TURN_LEFT = 1    # v = 0.5 m/s, omega = +pi/3 rad/s
    TURN_RIGHT = 2   # v = 0.5 m/s, omega = -pi/3 rad/s
    SLOW_DOWN = 3    # v = 0.3 m/s, omega = 0
    STOP = 4         # v = 0.0 m/s, omega = 0 (phanh khẩn cấp)
    WAIT = 5         # v = 0.0 m/s, omega = 0 (chờ có chủ đích)


class Robot(BaseObject):
    """Mô hình Robot hình tròn với động học 2D liên tục."""

    def __init__(
        self,
        x: float,
        y: float,
        theta: float = 0.0,
        radius: float = 0.35,
        v_max: float = 1.0,
        omega_max: float = math.pi / 3.0,
        sensor_radius: float = 6.0,
        goal_x: float = 18.0,
        goal_y: float = 18.0,
        goal_radius: float = 0.45,
    ):
        super().__init__(
            obj_id=0,
            x=x,
            y=y,
            radius=radius,
            obj_type=ObjectType.ROBOT,
            name="robot",
        )
        self.theta = self._normalize_angle(theta)
        self.v = 0.0
        self.omega = 0.0
        self.v_max = float(v_max)
        self.omega_max = float(omega_max)
        self.sensor_radius = float(sensor_radius)

        self.goal_x = float(goal_x)
        self.goal_y = float(goal_y)
        self.goal_radius = float(goal_radius)
        self.subgoal_x = float(goal_x)
        self.subgoal_y = float(goal_y)

        self.trajectory: list[tuple[float, float]] = [(self.x, self.y)]

    @staticmethod
    def _normalize_angle(angle: float) -> float:
        return math.atan2(math.sin(angle), math.cos(angle))

    def set_discrete_action(self, action: int | RobotAction):
        act = RobotAction(action)
        if act == RobotAction.FORWARD:
            self.v = self.v_max
            self.omega = 0.0
        elif act == RobotAction.TURN_LEFT:
            self.v = 0.5 * self.v_max
            self.omega = +self.omega_max
        elif act == RobotAction.TURN_RIGHT:
            self.v = 0.5 * self.v_max
            self.omega = -self.omega_max
        elif act == RobotAction.SLOW_DOWN:
            self.v = 0.3 * self.v_max
            self.omega = 0.0
        elif act in (RobotAction.STOP, RobotAction.WAIT):
            self.v = 0.0
            self.omega = 0.0

    def set_continuous_velocity(self, v: float, omega: float):
        self.v = max(0.0, min(float(v), self.v_max))
        self.omega = max(-self.omega_max, min(float(omega), self.omega_max))

    def compute_next_pose(self, dt: float) -> tuple[float, float, float]:
        next_x = self.x + self.v * math.cos(self.theta) * dt
        next_y = self.y + self.v * math.sin(self.theta) * dt
        next_theta = self._normalize_angle(self.theta + self.omega * dt)
        return next_x, next_y, next_theta

    def apply_pose(self, x: float, y: float, theta: float):
        self.x = float(x)
        self.y = float(y)
        self.theta = self._normalize_angle(theta)
        if not self.trajectory or math.hypot(
            self.x - self.trajectory[-1][0], self.y - self.trajectory[-1][1]
        ) > 0.05:
            self.trajectory.append((self.x, self.y))

    def distance_to_goal(self) -> float:
        return math.hypot(self.goal_x - self.x, self.goal_y - self.y)

    def has_reached_goal(self) -> bool:
        return self.distance_to_goal() < (self.radius + self.goal_radius)
