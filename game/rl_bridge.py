# game/rl_bridge.py
"""
Cầu nối tích hợp Mô hình Học Tăng Cường (RLPolicyAgent - PPO/DQN 106 chiều)
và Bộ lập kế hoạch A* Toàn cục vào chế độ AI Auto-Pilot [P] của FarmBot Town.
Thực hiện đúng kiến trúc Hierarchical RL (Mục 12.4):
1. High-Level Meta-Controller (`autopilot.py`): Chọn mục tiêu chiến lược `(tx, ty)`.
2. Global A* Planner & Sliding Sub-goal Selector: Tìm đường vòng qua sông, cầu, hàng rào, nhà cửa.
3. Low-Level Context-Aware RL Policy (`RLPolicyAgent`): Quan sát vector 106 chiều (LiDAR 16 tia,
   AGV/Thú nuôi, Top-5 NPC + Ngữ cảnh xã hội) để quyết định hành động điều hướng an toàn.
"""

from __future__ import annotations

import heapq
import math
import numpy as np

from .constants import (
    GRID_COLS,
    GRID_ROWS,
    ROBOT_V_MAX_MPS,
    SCREEN_H,
    SCREEN_W,
    T_GRASS,
    TILE_SIZE,
    m_to_px,
    px_to_m,
)
from .entities import (
    FarmAnimal,
    FarmCartAGV,
    FishingSpot,
    HarvestSpot,
    MapPortal,
    PropObject,
    RobotPlayer,
    VillagerNPC,
)
from .maps import is_circle_blocked, load_outdoor_map
from .schedules import MinimapAndScheduleSystem
from .sprite_vault import SpriteVault


class _HeadlessAtmosphere:
    def __init__(self):
        self.current_weather: str = "sunny"
        self.season_idx: int = 0


class HeadlessGameSession:
    """
    Phiên bản Headless của FarmBot Town chạy trực tiếp logic thực tế của `game/`
    (bản đồ `game/maps.py`, lộ trình tuần tra `VillagerNPC`, lịch trình theo giờ `game/schedules.py`,
    xe kéo `FarmCartAGV`, thú nuôi `FarmAnimal`) mà không cần mở cửa sổ Pygame hay nạp file ảnh `.png`.
    """

    def __init__(self):
        self.headless = True
        self.vault = SpriteVault(headless=True)
        self.schedules = MinimapAndScheduleSystem()
        self.atmosphere = _HeadlessAtmosphere()
        self.sim_time: float = 0.0
        self.current_map_id: int = 1
        self.in_interior: bool = False
        self.current_interior = None
        self.tiles: list[list[int]] = [
            [T_GRASS for _ in range(GRID_COLS)] for _ in range(GRID_ROWS)
        ]
        self.terrain_surface = None
        self.props: list[PropObject] = []
        self.npcs: list[VillagerNPC] = []
        self.interior_npcs: list[VillagerNPC] = []
        self.portals: list[MapPortal] = []
        self.harvest_spots: list[HarvestSpot] = []
        self.deco_fields: list[HarvestSpot] = []
        self.fishing_spots: list[FishingSpot] = []
        self.agvs: list[FarmCartAGV] = []
        self.animals: list[FarmAnimal] = []
        self.extra_blockers: list = []
        self.decals: list = []
        self.ground_props: list = []
        self.robot = RobotPlayer(SCREEN_W * 0.5, SCREEN_H * 0.5)

    def set_banner(self, text: str, color: tuple[int, int, int] = (255, 255, 255)):
        pass

    def is_circle_blocked(self, cx: float, cy: float, radius: float) -> bool:
        return is_circle_blocked(self, cx, cy, radius)

    def reset_map(self, map_id: int, sim_time_offset: float = 0.0):
        self.sim_time = float(sim_time_offset)
        load_outdoor_map(self, int(map_id))
        self.schedules.update_schedules(self, 0.0)

    @staticmethod
    def to_world_coords(
        px_x: float, px_y: float, world_w: float = 20.0, world_h: float = 20.0
    ) -> tuple[float, float]:
        return (
            float(px_x) * (world_w / float(SCREEN_W)),
            float(px_y) * (world_h / float(SCREEN_H)),
        )

    def step_entities(
        self, dt: float, robot_world_x: float, robot_world_y: float, world_w: float = 20.0, world_h: float = 20.0
    ):
        """Cập nhật lịch trình & chuyển động thực của toàn bộ NPC, AGV, Thú nuôi trong `game/`."""
        self.sim_time += dt
        self.robot.x = robot_world_x * (SCREEN_W / world_w)
        self.robot.y = robot_world_y * (SCREEN_H / world_h)

        self.schedules.update_schedules(self, dt)
        for npc in self.npcs:
            npc.update(dt, self)
        for agv in self.agvs:
            agv.update(dt, self.robot.x, self.robot.y, self)
        for anim in self.animals:
            anim.update(dt)


class GameRLNavigator:
    """Bộ điều hướng kết hợp A* trên bản đồ Game và Policy RL 106 chiều."""

    def __init__(self):
        self._rl_agent = None
        self._load_attempted = False
        self._cached_path: list[tuple[float, float]] = []
        self._last_plan_time: float = -999.0
        self._last_goal_px: tuple[float, float] = (-1.0, -1.0)
        self._last_map_key: tuple = (-1, False)
        self.last_rl_action_name: str = "IDLE"

    @property
    def rl_agent(self):
        if not self._load_attempted:
            self._load_attempted = True
            try:
                from rl.train_eval import RLPolicyAgent

                agent = RLPolicyAgent(include_social_context=True, deterministic=True)
                if agent.auto_load_default(mode="full_context"):
                    self._rl_agent = agent
            except Exception:
                self._rl_agent = None
        return self._rl_agent

    def reload_model(self) -> bool:
        self._load_attempted = False
        return self.rl_agent is not None and self.rl_agent.is_loaded

    @staticmethod
    def _rotate_to_robot_frame(
        dx_w: float, dy_w: float, rob_theta: float
    ) -> tuple[float, float]:
        c = math.cos(rob_theta)
        s = math.sin(rob_theta)
        return dx_w * c + dy_w * s, -dx_w * s + dy_w * c

    def _plan_astar_px(
        self, game, start_px: tuple[float, float], goal_px: tuple[float, float]
    ) -> list[tuple[float, float]]:
        """Tìm đường A* trên lưới ô vuông 16px (72x48) của bản đồ Game hiện tại."""
        cell = 24
        cols = SCREEN_W // cell
        rows = SCREEN_H // cell

        sc = max(0, min(cols - 1, int(start_px[0]) // cell))
        sr = max(0, min(rows - 1, int(start_px[1]) // cell))
        gc = max(0, min(cols - 1, int(goal_px[0]) // cell))
        gr = max(0, min(rows - 1, int(goal_px[1]) // cell))

        if (sc, sr) == (gc, gr):
            return [goal_px]

        rob_r = max(10.0, game.robot.radius * 0.88)
        active_npcs = game.interior_npcs if game.in_interior else game.npcs

        def is_free(c: int, r: int) -> bool:
            if (c, r) in ((sc, sr), (gc, gr)):
                return True
            px = (c + 0.5) * cell
            py = (r + 0.5) * cell
            return not game.is_circle_blocked(px, py, rob_r)

        def social_cost(c: int, r: int) -> float:
            px = (c + 0.5) * cell
            py = (r + 0.5) * cell
            pen = 0.0
            for n in active_npcs:
                if math.hypot(n.x - goal_px[0], n.y - goal_px[1]) < 64.0:
                    continue
                d = math.hypot(px - n.x, py - n.y)
                if d < 56.0:
                    pen += 3.5 * (56.0 - d) / 56.0
            return pen

        open_heap: list[tuple[float, float, int, int]] = []
        heapq.heappush(open_heap, (0.0, 0.0, sc, sr))
        came_from: dict[tuple[int, int], tuple[int, int]] = {}
        g_score: dict[tuple[int, int], float] = {(sc, sr): 0.0}

        neighbors = [
            (1, 0, 1.0),
            (-1, 0, 1.0),
            (0, 1, 1.0),
            (0, -1, 1.0),
            (1, 1, 1.414),
            (1, -1, 1.414),
            (-1, 1, 1.414),
            (-1, -1, 1.414),
        ]

        max_iter = 2200
        it = 0
        found = False
        while open_heap and it < max_iter:
            it += 1
            _, g_curr, cc, cr = heapq.heappop(open_heap)
            if (cc, cr) == (gc, gr):
                found = True
                break
            if g_curr > g_score.get((cc, cr), 1e9):
                continue

            for dc, dr, step_c in neighbors:
                nc, nr = cc + dc, cr + dr
                if not (0 <= nc < cols and 0 <= nr < rows):
                    continue
                if not is_free(nc, nr):
                    continue
                ng = g_curr + step_c + social_cost(nc, nr)
                if ng < g_score.get((nc, nr), 1e9):
                    g_score[(nc, nr)] = ng
                    came_from[(nc, nr)] = (cc, cr)
                    h = math.hypot(gc - nc, gr - nr)
                    heapq.heappush(open_heap, (ng + h, ng, nc, nr))

        if not found:
            return [goal_px]

        path_px: list[tuple[float, float]] = [goal_px]
        curr = (gc, gr)
        while curr in came_from:
            curr = came_from[curr]
            if curr == (sc, sr):
                break
            path_px.append(((curr[0] + 0.5) * cell, (curr[1] + 0.5) * cell))
        path_px.reverse()
        return path_px

    def _get_subgoal_px(
        self, game, tx: float, ty: float
    ) -> tuple[float, float, float, float]:
        """Trả về (subgoal_x, subgoal_y, dist_to_subgoal_m, angle_to_subgoal_rad)."""
        rx, ry = game.robot.x, game.robot.y
        map_key = (game.current_map_id, game.in_interior)
        goal_moved = (
            math.hypot(tx - self._last_goal_px[0], ty - self._last_goal_px[1]) > 28.0
        )

        if (
            not self._cached_path
            or map_key != self._last_map_key
            or goal_moved
            or (game.sim_time - self._last_plan_time) >= 0.65
        ):
            self._cached_path = self._plan_astar_px(game, (rx, ry), (tx, ty))
            self._last_plan_time = game.sim_time
            self._last_goal_px = (tx, ty)
            self._last_map_key = map_key

        lookahead_px = m_to_px(2.1)
        sub_x, sub_y = tx, ty
        best_idx = 0
        best_d = 1e9
        for i, (px, py) in enumerate(self._cached_path):
            d = math.hypot(px - rx, py - ry)
            if d < best_d:
                best_d = d
                best_idx = i

        for px, py in self._cached_path[best_idx:]:
            if math.hypot(px - rx, py - ry) >= lookahead_px:
                sub_x, sub_y = px, py
                break

        dist_sg_m = px_to_m(math.hypot(sub_x - rx, sub_y - ry))
        ang_world = math.atan2(sub_y - ry, sub_x - rx)
        ang_rel = math.atan2(
            math.sin(ang_world - game.robot.theta),
            math.cos(ang_world - game.robot.theta),
        )
        return sub_x, sub_y, dist_sg_m, ang_rel

    def _cast_lidar_16(self, game, r_sensor_m: float = 6.0) -> np.ndarray:
        """Bắn 16 tia LiDAR 360 độ trong không gian Game và chuẩn hóa về [0, 1]."""
        rx, ry = game.robot.x, game.robot.y
        r_theta = game.robot.theta
        max_px = m_to_px(r_sensor_m)
        step_px = 14.0
        dists = np.ones(16, dtype=np.float32)

        for i in range(16):
            ang = r_theta + i * (math.tau / 16.0)
            ca, sa = math.cos(ang), math.sin(ang)
            d_px = step_px
            while d_px <= max_px:
                px = rx + ca * d_px
                py = ry + sa * d_px
                if game.is_circle_blocked(px, py, 4.0):
                    dists[i] = min(1.0, d_px / max_px)
                    break
                d_px += step_px
        return dists

    def build_observation(
        self,
        game,
        tx: float,
        ty: float,
        dist_sg_m: float,
        ang_sg: float,
        target_npc=None,
    ) -> np.ndarray:
        """Xây dựng vector trạng thái mở rộng 128 chiều trực tiếp từ thế giới FarmBot Town."""
        d_max = 28.28
        r_sensor = 6.0
        v_max = max(0.1, float(ROBOT_V_MAX_MPS))
        omega_max = math.pi / 3.0

        rx_m = px_to_m(game.robot.x)
        ry_m = px_to_m(game.robot.y)
        r_theta = game.robot.theta
        rob_v = float(game.robot.v_mps)
        rob_vx = rob_v * math.cos(r_theta)
        rob_vy = rob_v * math.sin(r_theta)

        dist_goal_m = px_to_m(math.hypot(tx - game.robot.x, ty - game.robot.y))

        # Khối 1: Robot & Sub-goal (6 chiều)
        robot_goal_vec = np.array(
            [
                min(1.0, dist_sg_m / d_max),
                math.sin(ang_sg),
                math.cos(ang_sg),
                min(1.0, dist_goal_m / d_max),
                np.clip(rob_v / v_max, 0.0, 1.0),
                0.0,
            ],
            dtype=np.float32,
        )

        # Khối 2: 16 tia LiDAR (16 chiều)
        lidar_vec = self._cast_lidar_16(game, r_sensor_m=r_sensor)

        # Khối 3: Top-3 Vật thể Động (AGV & Thú nuôi, 24 chiều)
        objects_vec = np.zeros(24, dtype=np.float32)
        dyn_candidates: list[tuple[float, float, float, float, float, float]] = []
        if not game.in_interior:
            for agv in getattr(game, "agvs", []):
                ax_m, ay_m = px_to_m(agv.x), px_to_m(agv.y)
                dist_m = math.hypot(ax_m - rx_m, ay_m - ry_m)
                if dist_m <= r_sensor:
                    spd_m = (
                        px_to_m(agv.speed)
                        if getattr(agv, "mode", "patrol") == "patrol"
                        else 0.0
                    )
                    avx = spd_m * math.cos(agv.theta)
                    avy = spd_m * math.sin(agv.theta)
                    dyn_candidates.append(
                        (dist_m, ax_m, ay_m, avx, avy, px_to_m(agv.radius))
                    )
            for anim in getattr(game, "animals", []):
                ax_m, ay_m = px_to_m(anim.x), px_to_m(anim.y)
                dist_m = math.hypot(ax_m - rx_m, ay_m - ry_m)
                if dist_m <= r_sensor:
                    dyn_candidates.append(
                        (
                            dist_m,
                            ax_m,
                            ay_m,
                            px_to_m(anim.vx),
                            px_to_m(anim.vy),
                            0.30,
                        )
                    )

        dyn_candidates.sort(key=lambda item: item[0])
        for i, (_, ox, oy, ovx, ovy, orad) in enumerate(dyn_candidates[:3]):
            dx_rel, dy_rel = self._rotate_to_robot_frame(
                ox - rx_m, oy - ry_m, r_theta
            )
            dvx_rel, dvy_rel = self._rotate_to_robot_frame(
                ovx - rob_vx, ovy - rob_vy, r_theta
            )
            base = i * 8
            objects_vec[base : base + 8] = [
                np.clip(dx_rel / r_sensor, -1.5, 1.5),
                np.clip(dy_rel / r_sensor, -1.5, 1.5),
                np.clip(dvx_rel / v_max, -2.5, 2.5),
                np.clip(dvy_rel / v_max, -2.5, 2.5),
                np.clip(orad / r_sensor, 0.0, 1.0),
                0.0,
                1.0,
                0.0,
            ]

        # Khối 4: Top-5 Con người / NPC Cư dân (60 chiều)
        humans_vec = np.zeros(60, dtype=np.float32)
        active_npcs = game.interior_npcs if game.in_interior else game.npcs
        npc_candidates = []
        for n in active_npcs:
            if getattr(n, "is_home_at_night", False) and not game.in_interior:
                continue
            nx_m, ny_m = px_to_m(n.x), px_to_m(n.y)
            d_m = math.hypot(nx_m - rx_m, ny_m - ry_m)
            if d_m <= r_sensor:
                npc_candidates.append((d_m, n, nx_m, ny_m))

        npc_candidates.sort(key=lambda item: item[0])
        for j, (d_m, n, nx_m, ny_m) in enumerate(npc_candidates[:5]):
            dx_rel, dy_rel = self._rotate_to_robot_frame(
                nx_m - rx_m, ny_m - ry_m, r_theta
            )
            nvx = n.speed_mps * math.cos(n.theta)
            nvy = n.speed_mps * math.sin(n.theta)
            dvx_rel, dvy_rel = self._rotate_to_robot_frame(
                nvx - rob_vx, nvy - rob_vy, r_theta
            )
            rel_theta = math.atan2(
                math.sin(n.theta - r_theta), math.cos(n.theta - r_theta)
            )

            # Phân loại Activity & Social Context trực tiếp từ chuyển động NPC
            if n.speed_mps > 0.08:
                act_onehot = [0.0, 1.0, 0.0]  # WALKING
                if abs(math.cos(rel_theta)) > 0.7 and dx_rel > 0.0:
                    ctx_onehot = [1.0, 0.0, 0.0]  # APPROACHING
                else:
                    ctx_onehot = [0.0, 1.0, 0.0]  # CROSSING
            else:
                act_onehot = [1.0, 0.0, 0.0]  # STANDING
                ctx_onehot = [0.0, 0.0, 1.0] if d_m < 2.5 else [0.0, 0.0, 0.0]

            base = j * 12
            humans_vec[base : base + 12] = [
                np.clip(dx_rel / r_sensor, -1.5, 1.5),
                np.clip(dy_rel / r_sensor, -1.5, 1.5),
                np.clip(dvx_rel / v_max, -3.5, 3.5),
                np.clip(dvy_rel / v_max, -3.5, 3.5),
                math.sin(rel_theta),
                math.cos(rel_theta),
                *act_onehot,
                *ctx_onehot,
            ]

        # Khối 5: Trạng thái Vùng Quạt Tương tác HRI với NPC Mục tiêu / Gần nhất (4 chiều)
        ref_npc = target_npc if target_npc is not None else (npc_candidates[0][1] if npc_candidates else None)
        if ref_npc is not None:
            dx_n = game.robot.x - ref_npc.x
            dy_n = game.robot.y - ref_npc.y
            d_npc_m = px_to_m(math.hypot(dx_n, dy_n))
            ang_npc_to_rob = math.atan2(dy_n, dx_n)
            ang_rob_to_npc = math.atan2(-dy_n, -dx_n)
            d_alpha_npc = math.atan2(
                math.sin(ang_npc_to_rob - ref_npc.theta),
                math.cos(ang_npc_to_rob - ref_npc.theta),
            )
            d_alpha_rob = math.atan2(
                math.sin(ang_rob_to_npc - r_theta),
                math.cos(ang_rob_to_npc - r_theta),
            )
            in_fan_ok = (
                0.75 <= d_npc_m <= 1.45
                and abs(d_alpha_npc) <= math.radians(35.0)
                and abs(d_alpha_rob) <= math.radians(45.0)
                and rob_v < 0.05
            )
            fan_vec = np.array(
                [
                    float(np.clip(d_npc_m / 5.0, 0.0, 1.0)),
                    float(np.clip(d_alpha_npc / math.pi, -1.0, 1.0)),
                    float(np.clip(d_alpha_rob / math.pi, -1.0, 1.0)),
                    1.0 if in_fan_ok else 0.0,
                ],
                dtype=np.float32,
            )

            # Khối 6: Nhóm tuổi & Radar an toàn của NPC gần nhất (4 chiều)
            npcs_db = getattr(getattr(game, "state", None), "npcs_db", {})
            npc_meta = npcs_db.get(ref_npc.name, {}) if isinstance(npcs_db, dict) else {}
            age_grp = str(npc_meta.get("age_group", "adult")) if isinstance(npc_meta, dict) else "adult"
            r_safe = float(npc_meta.get("safety_radius_m", 1.65 if age_grp in ("elder", "child") else 1.25))
            age_vec = np.array(
                [
                    1.0 if age_grp == "adult" else 0.0,
                    1.0 if age_grp == "elder" else 0.0,
                    1.0 if age_grp == "child" else 0.0,
                    float(np.clip(r_safe / 2.0, 0.0, 1.0)),
                ],
                dtype=np.float32,
            )
        else:
            fan_vec = np.array([1.0, 0.0, 0.0, 0.0], dtype=np.float32)
            age_vec = np.array([1.0, 0.0, 0.0, 1.25 / 2.0], dtype=np.float32)

        # Khối 7: Trạng thái Khay đồ, Đồng hồ, Thời tiết/Tối, Mùa & Trái Tim An Toàn (6 chiều)
        inv_items = getattr(getattr(game, "state", None), "inventory", [])
        inv_ratio = float(np.clip(len(inv_items) / 4.0, 0.0, 1.0))
        sched = getattr(game, "schedules", None)
        sim_t = float(getattr(game, "sim_time", 0.0))
        hour_f = float(sched.get_time_info(sim_t)[0]) if sched and hasattr(sched, "get_time_info") else 8.0
        clock_norm = float(np.clip((hour_f - 6.0) / 18.0, 0.0, 1.0))
        atmos = getattr(game, "atmosphere", None)
        is_rain = getattr(atmos, "current_weather", "") == "rain"
        is_rain_or_night = 1.0 if (is_rain or hour_f >= 19.0) else 0.0
        season_idx = int(getattr(atmos, "season_idx", 0)) if atmos else 0
        hearts_norm = float(np.clip(getattr(game, "hearts", 3) / 3.0, 0.0, 1.0))
        farm_env_vec = np.array(
            [
                inv_ratio,
                1.0 if len(inv_items) > 0 else 0.0,
                clock_norm,
                is_rain_or_night,
                float(np.clip(season_idx / 3.0, 0.0, 1.0)),
                hearts_norm,
            ],
            dtype=np.float32,
        )

        # Khối 8: Vector Sự Kiện Ngẫu Nhiên Động CMDP (8 chiều)
        ev_mgr = getattr(game, "events", None)
        act_ev = getattr(ev_mgr, "active_event", None) if ev_mgr else None
        if isinstance(act_ev, dict):
            ev_x_m = float(act_ev.get("x_tile", 16.0)) * (20.0 / 36.0)
            ev_y_m = float(act_ev.get("y_tile", 12.0)) * (20.0 / 24.0)
            ex_rel, ey_rel = self._rotate_to_robot_frame(ev_x_m - rx_m, ev_y_m - ry_m, r_theta)
            d_ev = math.hypot(ev_x_m - rx_m, ev_y_m - ry_m)
            dur = max(1.0, float(act_ev.get("duration", 90.0)))
            rem = float(getattr(ev_mgr, "event_timer", 0.0))
            ev_id_str = str(act_ev.get("id", "spontaneous_gathering"))
            is_haz = 1.0 if ev_id_str in ("spontaneous_gathering", "runaway_animals") else 0.0
            rew_pts = float(act_ev.get("reward_gold", 90)) + float(act_ev.get("reward_score", 70))
            events_vec = np.array(
                [
                    1.0,
                    0.5,
                    float(np.clip(ex_rel / 20.0, -1.0, 1.0)),
                    float(np.clip(ey_rel / 20.0, -1.0, 1.0)),
                    float(np.clip(d_ev / 20.0, 0.0, 1.0)),
                    float(np.clip(rem / dur, 0.0, 1.0)),
                    float(np.clip(rew_pts / 300.0, 0.0, 1.0)),
                    is_haz,
                ],
                dtype=np.float32,
            )
        else:
            events_vec = np.zeros(8, dtype=np.float32)

        return np.concatenate(
            [
                robot_goal_vec,
                lidar_vec,
                objects_vec,
                humans_vec,
                fan_vec,
                age_vec,
                farm_env_vec,
                events_vec,
            ],
            axis=0,
        ).astype(np.float32)

    def compute_motion(
        self, game, tx: float, ty: float, target_npc=None
    ) -> tuple[float, float, bool]:
        """
        Kết hợp đường dẫn A* + Chính sách RL (PPO/DQN) + Lá chắn An toàn HRI 4 cấp độ
        để trả về (ux, uy, slow_flag) cho Robot trong FarmBot Town.
        """
        from objects.robot import RobotAction

        sub_x, sub_y, dist_sg_m, ang_sg = self._get_subgoal_px(game, tx, ty)
        dx = sub_x - game.robot.x
        dy = sub_y - game.robot.y
        dist = math.hypot(dx, dy)
        if dist < 4.0:
            return 0.0, 0.0, True

        ux, uy = dx / dist, dy / dist
        slow = bool(game.in_interior)

        # Gọi RL Policy nếu đã nạp thành công model
        agent = self.rl_agent
        if agent is not None and agent.is_loaded:
            obs = self.build_observation(
                game, tx, ty, dist_sg_m, ang_sg, target_npc=target_npc
            )
            rl_act = agent.select_action_from_obs(obs)
            self.last_rl_action_name = rl_act.name

            if rl_act == RobotAction.SLOW_DOWN:
                slow = True
            elif rl_act == RobotAction.TURN_LEFT:
                rot = 0.35
                c, s = math.cos(rot), math.sin(rot)
                ux, uy = ux * c - uy * s, ux * s + uy * c
            elif rl_act == RobotAction.TURN_RIGHT:
                rot = -0.35
                c, s = math.cos(rot), math.sin(rot)
                ux, uy = ux * c - uy * s, ux * s + uy * c
            elif rl_act in (RobotAction.STOP, RobotAction.WAIT):
                # Chỉ dừng hẳn khi có cư dân ở gần phía trước để tránh kẹt đường trống
                active_npcs = game.interior_npcs if game.in_interior else game.npcs
                has_nearby_npc = any(
                    math.hypot(n.x - game.robot.x, n.y - game.robot.y) < 110.0
                    for n in active_npcs
                )
                if has_nearby_npc:
                    return 0.0, 0.0, True
                slow = True

        # Lá chắn An toàn HRI (Safety Shield) đảm bảo không bao giờ đâm ngã hoặc cán qua NPC
        active_npcs = game.interior_npcs if game.in_interior else game.npcs
        for n in active_npcs:
            if getattr(n, "is_home_at_night", False) and not game.in_interior:
                continue
            nd = math.hypot(game.robot.x - n.x, game.robot.y - n.y)
            if nd < 92.0:
                slow = True
                if nd < 38.0 and (target_npc is None or n is not target_npc):
                    # Phanh nhường đường khẩn cấp nếu NPC cắt ngang quá sát
                    ang_to_n = math.atan2(n.y - game.robot.y, n.x - game.robot.x)
                    heading = math.atan2(uy, ux)
                    diff = abs(
                        math.atan2(
                            math.sin(ang_to_n - heading), math.cos(ang_to_n - heading)
                        )
                    )
                    if diff < math.radians(55.0) and n.speed_mps > 0.05:
                        return 0.0, 0.0, True
                if nd > 1e-3 and (target_npc is None or n is not target_npc or nd < 44.0):
                    rep = (92.0 - nd) / 92.0
                    ux += ((game.robot.x - n.x) / nd) * rep * 1.65
                    uy += ((game.robot.y - n.y) / nd) * rep * 1.65

        norm = math.hypot(ux, uy)
        if norm > 1e-4:
            ux, uy = ux / norm, uy / norm
        return ux, uy, slow


GAME_RL_NAVIGATOR = GameRLNavigator()

