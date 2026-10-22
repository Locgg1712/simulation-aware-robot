# Phase 4: Trích xuất Local Sub-goal trượt dọc đường A*
# planning/subgoal_selector.py
import math
from typing import Sequence


class SubgoalSelector:
    """
    Trích xuất Local Sub-goal trượt dọc theo đường dẫn toàn cục A* (Sliding Local Sub-goal).
    Ở mỗi bước, lấy điểm p_k nằm trên đường A* cách vị trí hiện tại của Robot
    một khoảng nhìn trước L_lookahead = 2.5m.
    """

    def __init__(self, lookahead_dist: float = 2.5):
        self.lookahead_dist = float(lookahead_dist)

    def get_subgoal(
        self,
        robot_x: float,
        robot_y: float,
        robot_theta: float,
        global_path: Sequence[tuple[float, float]],
        goal_x: float,
        goal_y: float,
    ) -> dict:
        """
        Trả về:
        - subgoal_x, subgoal_y: tọa độ thực của Local Sub-goal (m).
        - dist_to_subgoal: khoảng cách Euclid từ tâm Robot tới Sub-goal (m).
        - angle_to_subgoal: góc lệch (rad) từ mũi Robot tới Sub-goal trong đoạn [-pi, pi].
        """
        if not global_path:
            sg_x, sg_y = goal_x, goal_y
        else:
            # 1. Tìm chỉ số điểm gần Robot nhất trên đường A*
            closest_idx = 0
            min_dist = float("inf")
            for idx, (px, py) in enumerate(global_path):
                d = math.hypot(px - robot_x, py - robot_y)
                if d < min_dist:
                    min_dist = d
                    closest_idx = idx

            # 2. Trượt dọc theo đường A* từ closest_idx cho tới khi đạt khoảng cách >= L_lookahead
            sg_x, sg_y = global_path[-1]
            acc_dist = 0.0
            prev_x, prev_y = robot_x, robot_y

            for idx in range(closest_idx, len(global_path)):
                px, py = global_path[idx]
                seg_d = math.hypot(px - prev_x, py - prev_y)
                acc_dist += seg_d
                prev_x, prev_y = px, py
                if acc_dist >= self.lookahead_dist:
                    sg_x, sg_y = px, py
                    break

        dx = sg_x - robot_x
        dy = sg_y - robot_y
        dist = math.hypot(dx, dy)
        target_angle = math.atan2(dy, dx)
        angle_diff = math.atan2(
            math.sin(target_angle - robot_theta),
            math.cos(target_angle - robot_theta),
        )

        return {
            "subgoal_x": float(sg_x),
            "subgoal_y": float(sg_y),
            "dist_to_subgoal": float(dist),
            "angle_to_subgoal": float(angle_diff),
        }