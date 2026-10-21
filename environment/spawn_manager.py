# Phase 2: Sinh Robot, Goal, Objects, Humans & kiểm tra khả thi bằng A*
# environment/spawn_manager.py
from collections import deque
import math
import random
import numpy as np

from objects.static_object import StaticObject
from objects.semi_static_object import SemiStaticObject
from objects.dynamic_object import DynamicObject
from objects.robot import Robot
from .physics import check_robot_static_collision


class SpawnManager:
    """
    Quản lý việc sinh tự động Robot, Goal và Dynamic Objects kèm kiểm tra 3 điều kiện:
    1. Collision Check: Không đè lên tường tĩnh hoặc đè lên nhau.
    2. Safe Margin Check: Không sinh vật cản động trong bán kính 2.0m quanh Robot lúc t=0.
    3. Path Feasibility Check: Đảm bảo tồn tại đường đi trên lưới từ Start tới Goal.
    """

    def __init__(self, width: float, height: float, grid_res: float):
        self.width = float(width)
        self.height = float(height)
        self.grid_res = float(grid_res)
        self.cols = int(round(self.width / self.grid_res))
        self.rows = int(round(self.height / self.grid_res))

    def sample_free_point(
        self,
        hint: tuple[float, float],
        radius: float,
        static_objects: list[StaticObject],
        jitter: float = 1.2,
        max_attempts: int = 80,
    ) -> tuple[float, float]:
        """Tìm tọa độ trống gần điểm gợi ý `hint` mà không chạm vật cản tĩnh."""
        hx, hy = hint
        for i in range(max_attempts):
            scale = 0.0 if i == 0 else jitter
            cx = max(1.0, min(self.width - 1.0, hx + random.uniform(-scale, scale)))
            cy = max(1.0, min(self.height - 1.0, hy + random.uniform(-scale, scale)))
            collided, _ = check_robot_static_collision(
                cx, cy, radius + 0.15, static_objects, self.width, self.height
            )
            if not collided:
                return (cx, cy)

        # Fallback quét toàn bản đồ nếu vùng hint bị chật
        for _ in range(200):
            cx = random.uniform(1.2, self.width - 1.2)
            cy = random.uniform(1.2, self.height - 1.2)
            collided, _ = check_robot_static_collision(
                cx, cy, radius + 0.15, static_objects, self.width, self.height
            )
            if not collided:
                return (cx, cy)
        return hint

    def check_path_feasibility(
        self,
        start_pos: tuple[float, float],
        goal_pos: tuple[float, float],
        static_grid: np.ndarray,
    ) -> bool:
        """
        Kiểm tra xem trên bản đồ lưới tĩnh (coi cửa bán tĩnh là có thể mở)
        có đường nối thông từ Start tới Goal hay không.
        """
        sc = min(self.cols - 1, max(0, int(start_pos[0] / self.grid_res)))
        sr = min(self.rows - 1, max(0, int(start_pos[1] / self.grid_res)))
        gc = min(self.cols - 1, max(0, int(goal_pos[0] / self.grid_res)))
        gr = min(self.rows - 1, max(0, int(goal_pos[1] / self.grid_res)))

        if static_grid[sr, sc] == 1 or static_grid[gr, gc] == 1:
            return False

        visited = np.zeros_like(static_grid, dtype=bool)
        queue = deque([(sr, sc)])
        visited[sr, sc] = True

        dirs = [(-1, 0), (1, 0), (0, -1), (0, 1), (-1, -1), (-1, 1), (1, -1), (1, 1)]
        while queue:
            r, c = queue.popleft()
            if abs(r - gr) <= 1 and abs(c - gc) <= 1:
                return True
            for dr, dc in dirs:
                nr, nc = r + dr, c + dc
                if 0 <= nr < self.rows and 0 <= nc < self.cols:
                    if not visited[nr, nc] and static_grid[nr, nc] == 0:
                        visited[nr, nc] = True
                        queue.append((nr, nc))
        return False

    def spawn_dynamic_objects(
        self,
        num_objects: int,
        robot: Robot,
        static_objects: list[StaticObject],
        semi_static_objects: list[SemiStaticObject],
        start_obj_id: int = 100,
        safe_margin: float = 2.0,
    ) -> list[DynamicObject]:
        """
        Sinh `num_objects` vật thể động:
        - Cách Robot xuất phát ít nhất `safe_margin = 2.0m`.
        - Có 2-3 Waypoints hợp lệ để di chuyển qua lại.
        """
        dyn_objects: list[DynamicObject] = []

        for idx in range(num_objects):
            radius = 0.35
            placed = False
            for _ in range(120):
                x = random.uniform(1.5, self.width - 1.5)
                y = random.uniform(1.5, self.height - 1.5)

                # Safe Margin Check >= 2.0m quanh Robot
                if math.hypot(x - robot.x, y - robot.y) < safe_margin:
                    continue

                # Không đè lên Goal hoặc cửa bán tĩnh
                if math.hypot(x - robot.goal_x, y - robot.goal_y) < 1.2:
                    continue
                if any(math.hypot(x - d.x, y - d.y) < d.radius + 0.6 for d in semi_static_objects):
                    continue

                # Collision Check với tường tĩnh & các vật thể động khác
                collided, _ = check_robot_static_collision(
                    x, y, radius + 0.2, static_objects, self.width, self.height
                )
                if collided:
                    continue
                if any(math.hypot(x - o.x, y - o.y) < (radius + o.radius + 0.4) for o in dyn_objects):
                    continue

                # Sinh thêm 1 điểm đích tuần tra (Waypoint 2)
                wp2 = self.sample_free_point(
                    (
                        max(1.5, min(self.width - 1.5, x + random.uniform(-5.0, 5.0))),
                        max(1.5, min(self.height - 1.5, y + random.uniform(-5.0, 5.0))),
                    ),
                    radius,
                    static_objects,
                    jitter=2.0,
                )
                speed = random.uniform(0.45, 0.85)
                theta = math.atan2(wp2[1] - y, wp2[0] - x)
                dyn_objects.append(
                    DynamicObject(
                        obj_id=start_obj_id + idx,
                        x=x,
                        y=y,
                        radius=radius,
                        speed=speed,
                        theta=theta,
                        waypoints=[(x, y), wp2],
                        name=f"agv_{idx + 1}",
                    )
                )
                placed = True
                break
            if not placed:
                continue

        return dyn_objects