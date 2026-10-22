# Phase 3: Quản lý nhóm đi chung và nhóm đứng tương tác (O-Space)
# human/groups.py
from enum import Enum
import math
from typing import Sequence
from .human_agent import HumanAgent


class GroupType(Enum):
    WALKING_GROUP = "GROUP"            # Nhóm cùng di chuyển
    INTERACTING_GROUP = "INTERACTING"  # Nhóm đứng nói chuyện (tạo O-Space)


class HumanGroup:
    """
    Biểu diễn một nhóm M con người (INTERACTING hoặc GROUP).
    Tính toán tâm O-Space (C_x, C_y) và bán kính vùng cấm xã hội R_group theo mục 7.2:
        C_x = (1/M) * sum(x_i),  C_y = (1/M) * sum(y_i)
        R_group = max_i sqrt((x_i - C_x)^2 + (y_i - C_y)^2) + d_margin
    """

    def __init__(
        self,
        group_id: int,
        group_type: GroupType,
        members: Sequence[HumanAgent],
        margin: float = 0.45,
    ):
        self.group_id = group_id
        self.group_type = group_type
        self.members: list[HumanAgent] = list(members)
        self.margin = float(margin)

        self.center_x: float = 0.0
        self.center_y: float = 0.0
        self.radius: float = 1.0
        self.update_geometry()

    def update_geometry(self):
        """Cập nhật tâm (C_x, C_y) và bán kính R_group từ vị trí các thành viên."""
        m = len(self.members)
        if m == 0:
            return
        self.center_x = sum(h.x for h in self.members) / m
        self.center_y = sum(h.y for h in self.members) / m
        max_dist = max(
            math.hypot(h.x - self.center_x, h.y - self.center_y) for h in self.members
        )
        self.radius = max_dist + self.margin

    def is_robot_inside_ospace(
        self, robot_x: float, robot_y: float, robot_radius: float = 0.0
    ) -> bool:
        """Kiểm tra xem Robot có xâm nhập vào hình tròn O-Space của nhóm hay không."""
        dist = math.hypot(robot_x - self.center_x, robot_y - self.center_y)
        return dist < (self.radius + robot_radius * 0.5)

    def is_robot_splitting_group(
        self, robot_x: float, robot_y: float, threshold: float = 0.55
    ) -> bool:
        """
        Kiểm tra xem Robot có đang đi xuyên qua đoạn thẳng nối giữa bất kỳ 2 thành viên nào
        trong nhóm đang tương tác (Group Splitting / Crossing) hay không.
        """
        if len(self.members) < 2:
            return False

        if not self.is_robot_inside_ospace(robot_x, robot_y):
            return False

        n = len(self.members)
        for i in range(n):
            for j in range(i + 1, n):
                p1 = self.members[i]
                p2 = self.members[j]
                dist_seg = _point_to_segment_distance(
                    robot_x, robot_y, p1.x, p1.y, p2.x, p2.y
                )
                if dist_seg <= threshold:
                    return True
        return False


def _point_to_segment_distance(
    px: float, py: float, x1: float, y1: float, x2: float, y2: float
) -> float:
    """Tính khoảng cách ngắn nhất từ điểm (px, py) tới đoạn thẳng (x1, y1)-(x2, y2)."""
    dx = x2 - x1
    dy = y2 - y1
    len_sq = dx * dx + dy * dy
    if len_sq < 1e-9:
        return math.hypot(px - x1, py - y1)
    t = max(0.0, min(1.0, ((px - x1) * dx + (py - y1) * dy) / len_sq))
    proj_x = x1 + t * dx
    proj_y = y1 + t * dy
    return math.hypot(px - proj_x, py - proj_y)