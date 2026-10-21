# Phase 2: Cửa tự động, thanh chắn barrier (kèm FSM: CLOSED -> OPENING -> OPEN -> CLOSING)
# objects/semi_static_object.py
from enum import Enum
import math
from .base_object import BaseObject, ObjectType


class SemiStaticState(Enum):
    CLOSED = "CLOSED"       # Không thể đi qua
    OPENING = "OPENING"     # Đang mở - Chưa an toàn để đi qua
    OPEN = "OPEN"           # Có thể đi qua an toàn
    CLOSING = "CLOSING"     # Đang đóng - Nguy hiểm, không nên đi qua


class SemiStaticObject(BaseObject):
    """
    Vật thể bán tĩnh (Semi-static Object): Cửa tự động, thanh chắn barrier, cổng kiểm soát.
    Vị trí cố định nhưng trạng thái thông hành (passable) biến thiên theo FSM.
    """

    def __init__(
        self,
        obj_id: int,
        x: float,
        y: float,
        width: float,
        height: float,
        initial_state: SemiStaticState = SemiStaticState.CLOSED,
        closed_duration: float = 5.0,
        opening_duration: float = 1.5,
        open_duration: float = 6.0,
        closing_duration: float = 1.5,
        trigger_distance: float = 0.0,  # > 0 nếu là cửa cảm biến tự mở khi robot lại gần
        name: str = "auto_door",
    ):
        self.rect_x = float(x)
        self.rect_y = float(y)
        self.width = float(width)
        self.height = float(height)
        center_x = self.rect_x + self.width / 2.0
        center_y = self.rect_y + self.height / 2.0
        bounding_radius = math.hypot(self.width / 2.0, self.height / 2.0)

        super().__init__(
            obj_id=obj_id,
            x=center_x,
            y=center_y,
            radius=bounding_radius,
            obj_type=ObjectType.SEMI_STATIC,
            name=name,
        )

        self.state = initial_state
        self.timer = 0.0
        self.closed_duration = float(closed_duration)
        self.opening_duration = float(opening_duration)
        self.open_duration = float(open_duration)
        self.closing_duration = float(closing_duration)
        self.trigger_distance = float(trigger_distance)

    @property
    def passable(self) -> bool:
        """Chỉ cho phép đi qua khi cửa ở trạng thái OPEN hoàn toàn."""
        return self.state == SemiStaticState.OPEN

    @property
    def bbox(self) -> tuple[float, float, float, float]:
        return (self.rect_x, self.rect_y, self.width, self.height)

    @property
    def open_ratio(self) -> float:
        """Tỉ lệ mở cửa từ 0.0 (đóng kín) đến 1.0 (mở hoàn toàn) để hiển thị trực quan."""
        if self.state == SemiStaticState.CLOSED:
            return 0.0
        if self.state == SemiStaticState.OPEN:
            return 1.0
        if self.state == SemiStaticState.OPENING:
            return min(1.0, self.timer / max(1e-6, self.opening_duration))
        if self.state == SemiStaticState.CLOSING:
            return max(0.0, 1.0 - (self.timer / max(1e-6, self.closing_duration)))
        return 0.0

    def update(self, dt: float, robot_pos: tuple[float, float] | None = None):
        """
        Cập nhật máy trạng thái (FSM) ở mỗi bước thời gian dt:
        CLOSED -> OPENING -> OPEN -> CLOSING -> CLOSED
        """
        self.timer += dt

        # Nếu là cửa cảm biến tiệm cận (trigger_distance > 0)
        if self.trigger_distance > 0.0 and robot_pos is not None:
            dist = math.hypot(robot_pos[0] - self.x, robot_pos[1] - self.y)
            if self.state == SemiStaticState.CLOSED and dist <= self.trigger_distance:
                self.state = SemiStaticState.OPENING
                self.timer = 0.0
                return

        # Chuyển trạng thái theo chu kỳ thời gian
        if self.state == SemiStaticState.CLOSED:
            if self.timer >= self.closed_duration:
                self.state = SemiStaticState.OPENING
                self.timer = 0.0
        elif self.state == SemiStaticState.OPENING:
            if self.timer >= self.opening_duration:
                self.state = SemiStaticState.OPEN
                self.timer = 0.0
        elif self.state == SemiStaticState.OPEN:
            if self.timer >= self.open_duration:
                self.state = SemiStaticState.CLOSING
                self.timer = 0.0
        elif self.state == SemiStaticState.CLOSING:
            if self.timer >= self.closing_duration:
                self.state = SemiStaticState.CLOSED
                self.timer = 0.0