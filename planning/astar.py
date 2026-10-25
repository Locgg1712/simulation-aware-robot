# Phase 4: Tìm đường toàn cục trên Occupancy Grid
# planning/astar.py
import heapq
import math
from typing import Sequence
import numpy as np

from objects.semi_static_object import SemiStaticObject
from human.human_agent import HumanAgent
from human.groups import HumanGroup
from human.social_space import compute_personal_space_cost


class AStarPlanner:
    """
    Bộ tìm đường toàn cục A* trên lưới Occupancy Grid (80x80).
    - Hỗ trợ làm phồng biên an toàn (Wall Clearance Cost) để Robot không quẹt tường.
    - Cho phép đi xuyên qua Semi-static Door đang đóng với trọng số phạt nhẹ để Robot
      biết tiến tới trước cửa và chờ mở (theo Mục 8 của Đặc tả).
    - Hỗ trợ tích hợp chi phí O-Space / Social Space cho Baseline 2 (A* + Social Rules).
    """

    def __init__(self, width: float, height: float, grid_res: float):
        self.width = float(width)
        self.height = float(height)
        self.grid_res = float(grid_res)
        self.cols = int(round(self.width / self.grid_res))
        self.rows = int(round(self.height / self.grid_res))

    def world_to_grid(self, x: float, y: float) -> tuple[int, int]:
        c = min(self.cols - 1, max(0, int(x / self.grid_res)))
        r = min(self.rows - 1, max(0, int(y / self.grid_res)))
        return (r, c)

    def grid_to_world(self, r: int, c: int) -> tuple[float, float]:
        x = (c + 0.5) * self.grid_res
        y = (r + 0.5) * self.grid_res
        return (x, y)

    def _build_inflated_and_cost_grids(
        self,
        static_grid: np.ndarray,
        semi_static_objects: Sequence[SemiStaticObject],
        use_social_cost: bool = False,
        humans: Sequence[HumanAgent] = (),
        groups: Sequence[HumanGroup] = (),
        goal_pos: tuple[float, float] | None = None,
    ) -> tuple[np.ndarray, np.ndarray]:
        """
        Tạo:
        - hard_grid: Ma trận vật cản cứng (1 = tường tĩnh đã inflate bán kính Robot).
        - penalty_grid: Ma trận chi phí phụ trội (gần tường, cửa đang đóng, NPC tĩnh, vùng O-Space).
        """
        hard_grid = static_grid.copy()
        penalty_grid = np.zeros((self.rows, self.cols), dtype=np.float32)

        # 1. Tạo lớp đệm chi phí quanh tường tĩnh (bán kính 1-2 ô lưới = 0.25m - 0.50m)
        # giúp đường A* luôn nằm giữa hành lang/cầu thay vì sát mép nước/tường
        occupied_r, occupied_c = np.where(static_grid == 1)
        for r, c in zip(occupied_r, occupied_c):
            r_min = max(0, r - 2)
            r_max = min(self.rows - 1, r + 2)
            c_min = max(0, c - 2)
            c_max = min(self.cols - 1, c + 2)
            for nr in range(r_min, r_max + 1):
                for nc in range(c_min, c_max + 1):
                    if static_grid[nr, nc] == 0:
                        dist_cells = max(abs(nr - r), abs(nc - c))
                        if dist_cells == 1:
                            penalty_grid[nr, nc] = max(penalty_grid[nr, nc], 6.5)
                        elif dist_cells == 2:
                            penalty_grid[nr, nc] = max(penalty_grid[nr, nc], 2.0)

        # 2. Trọng số cho cửa bán tĩnh (Semi-static Doors) đang đóng / đang chuyển trạng thái
        for door in semi_static_objects:
            if not door.passable:
                rx, ry, rw, rh = door.bbox
                c_min = max(0, int(rx / self.grid_res))
                c_max = min(self.cols - 1, int((rx + rw) / self.grid_res))
                r_min = max(0, int(ry / self.grid_res))
                r_max = min(self.rows - 1, int((ry + rh) / self.grid_res))
                penalty_grid[r_min : r_max + 1, c_min : c_max + 1] += 2.5

        # 3. Luôn tránh đâm xuyên qua thân vật lý của các NPC đứng yên trên đường
        for h in humans:
            if h.x < 0.0 or h.y < 0.0:
                continue
            if goal_pos is not None and math.hypot(h.x - goal_pos[0], h.y - goal_pos[1]) < 0.95:
                continue
            if h.speed < 0.08 or use_social_cost:
                c_h = int(h.x / self.grid_res)
                r_h = int(h.y / self.grid_res)
                body_rad = h.radius + 0.38
                rad_cells = int(math.ceil(body_rad / self.grid_res)) + 1
                r_min = max(0, r_h - rad_cells)
                r_max = min(self.rows - 1, r_h + rad_cells)
                c_min = max(0, c_h - rad_cells)
                c_max = min(self.cols - 1, c_h + rad_cells)
                for nr in range(r_min, r_max + 1):
                    for nc in range(c_min, c_max + 1):
                        wx, wy = self.grid_to_world(nr, nc)
                        d_h = math.hypot(wx - h.x, wy - h.y)
                        if d_h <= body_rad:
                            penalty_grid[nr, nc] += 45.0

        # 4. Nếu bật chế độ Social Cost: đưa vùng O-Space và elip Gaussian vào penalty_grid
        if use_social_cost:
            for grp in groups:
                c_center = int(grp.center_x / self.grid_res)
                r_center = int(grp.center_y / self.grid_res)
                rad_cells = int(math.ceil((grp.radius + 0.4) / self.grid_res))
                r_min = max(0, r_center - rad_cells)
                r_max = min(self.rows - 1, r_center + rad_cells)
                c_min = max(0, c_center - rad_cells)
                c_max = min(self.cols - 1, c_center + rad_cells)
                for nr in range(r_min, r_max + 1):
                    for nc in range(c_min, c_max + 1):
                        wx, wy = self.grid_to_world(nr, nc)
                        if grp.is_robot_inside_ospace(wx, wy, robot_radius=0.35):
                            penalty_grid[nr, nc] += 18.0

            for h in humans:
                if h.x < 0.0 or h.y < 0.0:
                    continue
                c_h = int(h.x / self.grid_res)
                r_h = int(h.y / self.grid_res)
                rad_cells = 6
                r_min = max(0, r_h - rad_cells)
                r_max = min(self.rows - 1, r_h + rad_cells)
                c_min = max(0, c_h - rad_cells)
                c_max = min(self.cols - 1, c_h + rad_cells)
                for nr in range(r_min, r_max + 1):
                    for nc in range(c_min, c_max + 1):
                        wx, wy = self.grid_to_world(nr, nc)
                        sc = compute_personal_space_cost(wx, wy, h)
                        if sc > 0.25:
                            penalty_grid[nr, nc] += float(sc * 8.0)

        return hard_grid, penalty_grid

    def _find_nearest_free_cell(
        self, r: int, c: int, hard_grid: np.ndarray
    ) -> tuple[int, int]:
        if hard_grid[r, c] == 0:
            return (r, c)
        for radius in range(1, 10):
            for dr in range(-radius, radius + 1):
                for dc in range(-radius, radius + 1):
                    nr, nc = r + dr, c + dc
                    if 0 <= nr < self.rows and 0 <= nc < self.cols:
                        if hard_grid[nr, nc] == 0:
                            return (nr, nc)
        return (r, c)

    def plan(
        self,
        start_pos: tuple[float, float],
        goal_pos: tuple[float, float],
        static_grid: np.ndarray,
        semi_static_objects: Sequence[SemiStaticObject] = (),
        use_social_cost: bool = False,
        humans: Sequence[HumanAgent] = (),
        groups: Sequence[HumanGroup] = (),
    ) -> list[tuple[float, float]]:
        """
        Chạy thuật toán A* 8 hướng từ `start_pos` tới `goal_pos`.
        Trả về danh sách các điểm tọa độ thực [(x_0, y_0), (x_1, y_1), ..., (x_N, y_N)].
        """
        hard_grid, penalty_grid = self._build_inflated_and_cost_grids(
            static_grid=static_grid,
            semi_static_objects=semi_static_objects,
            use_social_cost=use_social_cost,
            humans=humans,
            groups=groups,
            goal_pos=goal_pos,
        )

        sr, sc = self.world_to_grid(*start_pos)
        gr, gc = self.world_to_grid(*goal_pos)
        sr, sc = self._find_nearest_free_cell(sr, sc, hard_grid)
        gr, gc = self._find_nearest_free_cell(gr, gc, hard_grid)

        if (sr, sc) == (gr, gc):
            return [goal_pos]

        # 8 hướng lân cận: (dr, dc, step_cost)
        neighbors = [
            (-1, 0, 1.0),
            (1, 0, 1.0),
            (0, -1, 1.0),
            (0, 1, 1.0),
            (-1, -1, 1.41421356),
            (-1, 1, 1.41421356),
            (1, -1, 1.41421356),
            (1, 1, 1.41421356),
        ]

        def heuristic(r1: int, c1: int, r2: int, c2: int) -> float:
            dr = abs(r1 - r2)
            dc = abs(c1 - c2)
            return (dr + dc) + (1.41421356 - 2.0) * min(dr, dc)

        open_heap: list[tuple[float, int, int]] = []
        heapq.heappush(open_heap, (heuristic(sr, sc, gr, gc), sr, sc))

        g_score = np.full((self.rows, self.cols), np.inf, dtype=np.float64)
        g_score[sr, sc] = 0.0
        came_from: dict[tuple[int, int], tuple[int, int]] = {}
        closed = np.zeros((self.rows, self.cols), dtype=bool)

        found = False
        while open_heap:
            _, r, c = heapq.heappop(open_heap)
            if closed[r, c]:
                continue
            closed[r, c] = True

            if (r, c) == (gr, gc):
                found = True
                break

            for dr, dc, move_cost in neighbors:
                nr, nc = r + dr, c + dc
                if not (0 <= nr < self.rows and 0 <= nc < self.cols):
                    continue
                if hard_grid[nr, nc] == 1 or closed[nr, nc]:
                    continue

                # Không đi chéo cắt góc vuông qua khe tường hẹp
                if dr != 0 and dc != 0:
                    if hard_grid[r + dr, c] == 1 or hard_grid[r, c + dc] == 1:
                        continue

                tentative_g = (
                    g_score[r, c] + move_cost + float(penalty_grid[nr, nc])
                )
                if tentative_g < g_score[nr, nc]:
                    g_score[nr, nc] = tentative_g
                    came_from[(nr, nc)] = (r, c)
                    f_val = tentative_g + heuristic(nr, nc, gr, gc)
                    heapq.heappush(open_heap, (f_val, nr, nc))

        if not found:
            return [start_pos, goal_pos]

        # Truy vết lại đường đi từ Goal về Start
        grid_path: list[tuple[int, int]] = []
        curr = (gr, gc)
        while curr in came_from:
            grid_path.append(curr)
            curr = came_from[curr]
        grid_path.reverse()

        world_path = [self.grid_to_world(r, c) for r, c in grid_path]
        if world_path:
            world_path[-1] = goal_pos
        else:
            world_path = [goal_pos]

        return world_path