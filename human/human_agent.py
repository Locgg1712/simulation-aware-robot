# Phase 3: Lớp con người (Physical + Activity + Social Context)
# human/human_agent.py
from enum import Enum
import math
from objects.base_object import BaseObject, ObjectType


class HumanActivity(Enum):
    """Hành vi cá nhân của con người dựa trên vận tốc."""
    STANDING = "STANDING"  # v ~ 0.0 m/s
    WALKING = "WALKING"    # v ~ 0.8 - 1.4 m/s
    RUNNING = "RUNNING"    # v ~ 2.0 - 3.0 m/s


class SocialContext(Enum):
    """Ngữ cảnh tương tác xã hội của con người với Robot và người xung quanh."""
    ALONE = "ALONE"              # Đi hoặc đứng độc lập
    APPROACHING = "APPROACHING"  # Đang tiến thẳng về phía robot
    CROSSING = "CROSSING"        # Đang cắt ngang mũi di chuyển của robot
    GROUP = "GROUP"              # Di chuyển cùng nhau thành nhóm
    INTERACTING = "INTERACTING"  # Đang đứng nói chuyện / tương tác nhóm (O-Space)


class HumanAgent(BaseObject):
    """
    Thực thể Con người (Human Entity) cấu trúc 3 tầng:
    1. Physical State: (x, y), (vx, vy), speed, theta, radius = 0.3m
    2. Activity: STANDING, WALKING, RUNNING
    3. Social Context: ALONE, APPROACHING, CROSSING, GROUP, INTERACTING
    """

    def __init__(
        self,
        obj_id: int,
        x: float,
        y: float,
        theta: float = 0.0,
        desired_speed: float = 1.1,
        radius: float = 0.30,
        waypoints: list[tuple[float, float]] | None = None,
        group_id: int | None = None,
        is_interacting_member: bool = False,
        name: str = "",
        age_group: str = "adult",
        safety_radius: float | None = None,
    ):
        super().__init__(
            obj_id=obj_id,
            x=x,
            y=y,
            radius=radius,
            obj_type=ObjectType.HUMAN,
            name=name or f"human_{obj_id}",
        )
        self.theta = math.atan2(math.sin(theta), math.cos(theta))
        self.desired_speed = float(desired_speed)
        self.vx = 0.0
        self.vy = 0.0
        self.speed = 0.0

        self.waypoints: list[tuple[float, float]] = waypoints or []
        self.current_wp_idx: int = 0

        self.group_id: int | None = group_id
        self.is_interacting_member: bool = is_interacting_member

        self.age_group: str = age_group if age_group in ("adult", "elder", "child") else "adult"
        if safety_radius is not None:
            self.safety_radius: float = float(safety_radius)
        else:
            self.safety_radius = 1.65 if self.age_group in ("elder", "child") else 1.25

        self.activity: HumanActivity = HumanActivity.STANDING
        self.social_context: SocialContext = SocialContext.ALONE

        self.update_activity_from_speed()

    def update_activity_from_speed(self):
        """Tự động cập nhật nhãn Activity dựa trên vận tốc thực tế ||v||."""
        if self.speed < 0.20:
            self.activity = HumanActivity.STANDING
        elif self.speed < 1.65:
            self.activity = HumanActivity.WALKING
        else:
            self.activity = HumanActivity.RUNNING

    def set_velocity(self, vx: float, vy: float):
        """Cập nhật vector vận tốc, tốc độ dài, góc hướng và nhãn Activity."""
        self.vx = float(vx)
        self.vy = float(vy)
        self.speed = math.hypot(self.vx, self.vy)
        if self.speed > 0.05:
            self.theta = math.atan2(self.vy, self.vx)
        self.update_activity_from_speed()

    def predict_trajectory(
        self, dt: float = 0.1, horizon_sec: float = 3.0, step_stride: int = 3
    ) -> list[tuple[float, float]]:
        """Dự đoán quỹ đạo ngắn hạn của người với vận tốc hiện tại trong T_pred."""
        if self.speed < 0.10:
            return []
        num_steps = int(round(horizon_sec / dt))
        preds: list[tuple[float, float]] = []
        for k in range(step_stride, num_steps + 1, step_stride):
            t_future = k * dt
            preds.append((self.x + self.vx * t_future, self.y + self.vy * t_future))
        return preds

    def activity_one_hot(self) -> list[float]:
        """Mã hóa One-Hot 3 chiều cho Activity: [STANDING, WALKING, RUNNING]."""
        return [
            1.0 if self.activity == HumanActivity.STANDING else 0.0,
            1.0 if self.activity == HumanActivity.WALKING else 0.0,
            1.0 if self.activity == HumanActivity.RUNNING else 0.0,
        ]

    def context_one_hot_3(self) -> list[float]:
        """
        Mã hóa One-Hot 3 chiều gọn cho RL State (Mục 9.1):
        - Chiều 0: ALONE
        - Chiều 1: APPROACHING hoặc CROSSING (nguy cơ giao cắt động với Robot)
        - Chiều 2: GROUP hoặc INTERACTING (ràng buộc nhóm xã hội / O-Space)
        """
        is_alone = 1.0 if self.social_context == SocialContext.ALONE else 0.0
        is_motion_conflict = (
            1.0
            if self.social_context in (SocialContext.APPROACHING, SocialContext.CROSSING)
            else 0.0
        )
        is_group_context = (
            1.0
            if self.social_context in (SocialContext.GROUP, SocialContext.INTERACTING)
            else 0.0
        )
        return [is_alone, is_motion_conflict, is_group_context]

    def age_radar_vector(self) -> list[float]:
        """
        Mã hóa 4 chiều Nhóm Tuổi & Bán kính Radar An toàn (Mục 12.1 - Khối 6):
        [is_adult, is_elder, is_child, R_safe / 2.0]
        """
        return [
            1.0 if self.age_group == "adult" else 0.0,
            1.0 if self.age_group == "elder" else 0.0,
            1.0 if self.age_group == "child" else 0.0,
            min(1.0, self.safety_radius / 2.0),
        ]