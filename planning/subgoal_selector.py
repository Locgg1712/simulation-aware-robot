# Phase 4: Trích xuất Local Sub-goal trượt dọc đường A* (Có kiểm tra Line-of-Sight chống cắt góc)
# planning/subgoal_selector.py
import math
from typing import Sequence
import numpy as np


class SubgoalSelector:
    """
    Trích xuất Local Sub-goal trượt dọc theo đường dẫn toàn cục A* (Sliding Local Sub-goal).
    Ở mỗi bước, lấy điểm p_k nằm trên đường A* cách vị trí hiện tại của Robot
    một khoảng nhìn trước L_lookahead (mặc định 1.8m), đồng thời kiểm tra Line-of-Sight
    trên `static_grid` để không bao giờ cắt chéo qua góc cầu, bờ sông hoặc tường nhà.
    """

    def __init__(self, lookahead_dist: float = 1.8):
        self.lookahead_dist = float(lookahead_dist)

    @staticmethod
    def _has_line_of_sight(
        x0: float,
        y0: float,
        x1: float,
        y1: float,
        static_grid: np.ndarray,
        grid_res: float,
    ) -> bool:
        rows, cols = static_grid.shape
        dist = math.hypot(x1 - x0, y1 - y0)
        steps = max(2, int(dist / (grid_res * 0.45)))
        for s in range(1, steps + 1):
            t = s / float(steps)
            px = x0 + (x1 - x0) * t
            py = y0 + (y1 - y0) * t
            c = min(cols - 1, max(0, int(px / grid_res)))
            r = min(rows - 1, max(0, int(py / grid_res)))
            if static_grid[r, c] == 1:
                return False
        return True

    def get_subgoal(
        self,
        robot_x: float,
        robot_y: float,
        robot_theta: float,
        global_path: Sequence[tuple[float, float]],
        goal_x: float,
        goal_y: float,
        static_grid: np.ndarray | None = None,
        grid_res: float = 0.25,
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

            # 2. Trượt dọc theo đường A* từ closest_idx cho tới khi đạt L_lookahead,
            #    nhưng dừng tại đỉnh khúc cua nếu đường nối thẳng cắt qua vật cản trong static_grid.
            sg_x, sg_y = global_path[min(len(global_path) - 1, closest_idx + 1)]
            acc_dist = 0.0
            prev_x, prev_y = robot_x, robot_y
            eff_lookahead = min(self.lookahead_dist, 1.85)

            for idx in range(closest_idx, len(global_path)):
                px, py = global_path[idx]
                seg_d = math.hypot(px - prev_x, py - prev_y)
                acc_dist += seg_d
                prev_x, prev_y = px, py

                if (
                    static_grid is not None
                    and idx > closest_idx + 1
                    and acc_dist > 0.45
                    and not self._has_line_of_sight(
                        robot_x, robot_y, px, py, static_grid, grid_res
                    )
                ):
                    break

                sg_x, sg_y = px, py
                if acc_dist >= eff_lookahead:
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