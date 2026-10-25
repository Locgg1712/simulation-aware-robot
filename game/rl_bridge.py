# game/rl_bridge.py
"""
Cầu nối tích hợp Mô hình Học Tăng Cường (RLPolicyAgent - PPO/DQN 128 chiều)
và Bộ lập kế hoạch A* Toàn cục vào chế độ AI Auto-Pilot [P] của FarmBot Town.
Thực hiện đúng kiến trúc Hierarchical RL (Mục 12.4):
1. High-Level Meta-Controller (`autopilot.py`): Chọn mục tiêu chiến lược `(tx, ty)`.
2. Global A* Planner & Sliding Sub-goal Selector: Tìm đường vòng qua sông, cầu, hàng rào, nhà cửa.
3. Low-Level Context-Aware RL Policy (`RLPolicyAgent`): Quan sát vector 128 chiều đồng nhất 100%
   với `StateBuilder.build()` để quyết định hành động điều hướng an toàn.
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
        self,
        dt: float,
        robot_world_x: float,
        robot_world_y: float,
        world_w: float = 20.0,
        world_h: float = 20.0,
        entity_dt_scale: float = 0.31,
    ):
        """
        Cập nhật lịch trình & chuyển động thực của toàn bộ NPC, AGV, Thú nuôi trong `game/`.
        - `self.sim_time` giữ nguyên theo `dt` để đồng hồ game chạy đúng chuẩn.
        - `edt = dt * entity_dt_scale` (~0.31 * dt) giúp tốc độ dịch chuyển thực của NPC/AGV
          trong hệ mét `World` (20x20m) khớp đúng tỉ lệ 0.25–0.40 tốc độ tối đa của Robot (1.0 m/s).
        """
        self.sim_time += dt
        edt = dt * float(entity_dt_scale)
        self.robot.x = robot_world_x * (SCREEN_W / world_w)
        self.robot.y = robot_world_y * (SCREEN_H / world_h)

        self.schedules.update_schedules(self, dt)
        for npc in self.npcs:
            npc.update(edt, self)
        for agv in self.agvs:
            agv.update(edt, self.robot.x, self.robot.y, self)
        for anim in self.animals:
            anim.update(edt)


class _GameWorldProxy:
    """Đối tượng trung gian nhẹ giúp `GameRLNavigator` tái sử dụng trực tiếp `StateBuilder.build(world)`."""

    def __init__(self):
        self.width: float = 20.0
        self.height: float = 20.0
        self.robot = None
        self.subgoal_info: dict = {}
        self.lidar_distances: list[float] = []
        self.local_perception: dict = {"semi_static": [], "dynamic": [], "humans": []}
        self.hri_status: dict = {}
        self.clock_hour: float = 8.0
        self.is_rain: bool = False
        self.season_idx: int = 0
        self.inv_ratio: float = 0.0
        self.has_quest_item: bool = False
        self.safety_hearts: int = 3
        self.active_event: dict | None = None


class GameRLNavigator:
    """Bộ điều hướng kết hợp A* trên bản đồ Game và Policy RL 128 chiều (dùng chung StateBuilder)."""

    ENTITY_DT_SCALE: float = 0.31

    def __init__(self):
        self._rl_agent = None
        self._state_builder = None
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
        """
        Xây dựng vector trạng thái mở rộng 128 chiều bằng cách ánh xạ trạng thái thực của `game`
        sang hệ quy chiếu `World` (20.0m x 20.0m, `entity_dt_scale = 0.31`) và gọi trực tiếp
        `StateBuilder.build(proxy)` — đảm bảo 100% đồng nhất toán học giữa lúc Train và Deploy.
        """
        from behavior.context_classifier import classify_all_humans_context
        from environment.world import EVENT_TYPE_IDS
        from human.human_agent import HumanAgent
        from objects.dynamic_object import DynamicObject
        from objects.robot import Robot
        from rl.state_builder import StateBuilder

        if self._state_builder is None:
            self._state_builder = StateBuilder(include_social_context=True)

        sx_scale = 20.0 / float(SCREEN_W)
        sy_scale = 20.0 / float(SCREEN_H)
        dt_scale = self.ENTITY_DT_SCALE
        r_sensor = 6.0

        rx_w = float(game.robot.x) * sx_scale
        ry_w = float(game.robot.y) * sy_scale
        gx_w = float(tx) * sx_scale
        gy_w = float(ty) * sy_scale
        r_theta = float(game.robot.theta)
        rob_v = float(np.clip(game.robot.v_mps, 0.0, 1.0))

        proxy = _GameWorldProxy()
        proxy.robot = Robot(
            x=rx_w,
            y=ry_w,
            theta=r_theta,
            radius=0.35,
            v_max=1.0,
            omega_max=math.pi / 3.0,
            sensor_radius=r_sensor,
            goal_x=gx_w,
            goal_y=gy_w,
            goal_radius=0.70,
        )
        proxy.robot.v = rob_v
        proxy.robot.omega = 0.0

        proxy.subgoal_info = {
            "subgoal_x": rx_w + dist_sg_m * math.cos(r_theta + ang_sg),
            "subgoal_y": ry_w + dist_sg_m * math.sin(r_theta + ang_sg),
            "dist_to_subgoal": float(dist_sg_m),
            "angle_to_subgoal": float(ang_sg),
        }

        lidar_norm = self._cast_lidar_16(game, r_sensor_m=r_sensor)
        proxy.lidar_distances = [float(d * r_sensor) for d in lidar_norm]

        # 1. Ánh xạ Vật thể động (AGV & Thú nuôi) theo đúng thang đo dịch chuyển thực của World
        dyn_objs: list[DynamicObject] = []
        if not game.in_interior:
            obj_id = 500
            for agv in getattr(game, "agvs", []):
                ax_w = float(agv.x) * sx_scale
                ay_w = float(agv.y) * sy_scale
                if math.hypot(ax_w - rx_w, ay_w - ry_w) <= r_sensor + 0.35:
                    if getattr(agv, "mode", "patrol") == "patrol":
                        vx_w = float(agv.speed) * math.cos(agv.theta) * sx_scale * dt_scale
                        vy_w = float(agv.speed) * math.sin(agv.theta) * sy_scale * dt_scale
                        spd_w = math.hypot(vx_w, vy_w)
                        th_w = math.atan2(vy_w, vx_w) if spd_w > 1e-4 else float(agv.theta)
                    else:
                        spd_w = 0.0
                        th_w = float(agv.theta)
                    dyn_objs.append(
                        DynamicObject(
                            obj_id=obj_id,
                            x=ax_w,
                            y=ay_w,
                            radius=0.35,
                            speed=spd_w,
                            theta=th_w,
                            waypoints=[],
                            name=f"game_agv_{obj_id}",
                        )
                    )
                    obj_id += 1

            for anim in getattr(game, "animals", []):
                ax_w = float(anim.x) * sx_scale
                ay_w = float(anim.y) * sy_scale
                if math.hypot(ax_w - rx_w, ay_w - ry_w) <= r_sensor + 0.28:
                    vx_w = float(getattr(anim, "vx", 0.0)) * sx_scale * dt_scale
                    vy_w = float(getattr(anim, "vy", 0.0)) * sy_scale * dt_scale
                    spd_w = math.hypot(vx_w, vy_w)
                    th_w = math.atan2(vy_w, vx_w) if spd_w > 1e-4 else 0.0
                    dyn_objs.append(
                        DynamicObject(
                            obj_id=obj_id,
                            x=ax_w,
                            y=ay_w,
                            radius=0.28,
                            speed=spd_w,
                            theta=th_w,
                            waypoints=[],
                            name=f"game_animal_{obj_id}",
                        )
                    )
                    obj_id += 1

        dyn_objs.sort(key=lambda d: math.hypot(d.x - rx_w, d.y - ry_w))

        # 2. Ánh xạ Con người / NPC Cư dân và phân loại ngữ cảnh bằng `classify_all_humans_context`
        npcs_db = getattr(getattr(game, "state", None), "npcs_db", {})
        if not isinstance(npcs_db, dict):
            npcs_db = {}

        active_npcs = game.interior_npcs if game.in_interior else game.npcs
        all_humans: list[HumanAgent] = []
        npc_to_human: dict[int, HumanAgent] = {}
        hid = 200
        for n in active_npcs:
            if getattr(n, "is_home_at_night", False) and not game.in_interior:
                continue
            nx_w = float(n.x) * sx_scale
            ny_w = float(n.y) * sy_scale
            vx_w = float(getattr(n, "vx", 0.0)) * sx_scale * dt_scale
            vy_w = float(getattr(n, "vy", 0.0)) * sy_scale * dt_scale
            npc_meta = npcs_db.get(n.name, {}) if isinstance(npcs_db.get(n.name), dict) else {}
            age_grp = str(npc_meta.get("age_group", "adult"))
            safe_r = float(
                npc_meta.get(
                    "safety_radius_m",
                    1.65 if age_grp in ("elder", "child") else 1.25,
                )
            )
            h_agent = HumanAgent(
                obj_id=hid,
                x=nx_w,
                y=ny_w,
                theta=float(n.theta),
                desired_speed=max(0.25, float(getattr(n, "base_speed", 60.0)) * sx_scale * dt_scale),
                radius=0.30,
                waypoints=[],
                name=n.name,
                age_group=age_grp,
                safety_radius=safe_r,
            )
            h_agent.set_velocity(vx_w, vy_w)
            if h_agent.speed < 0.05:
                h_agent.theta = float(n.theta)
            all_humans.append(h_agent)
            npc_to_human[id(n)] = h_agent
            hid += 1

        classify_all_humans_context(all_humans, [], proxy.robot)
        detected_humans = [
            h
            for h in all_humans
            if math.hypot(h.x - rx_w, h.y - ry_w) <= r_sensor + h.radius
        ]
        detected_humans.sort(key=lambda h: math.hypot(h.x - rx_w, h.y - ry_w))

        proxy.local_perception = {
            "semi_static": [],
            "dynamic": dyn_objs,
            "humans": detected_humans,
        }

        # 3. Khối 5 & Khối 6: HRI Vùng Quạt & Radar Độ Tuổi của NPC mục tiêu / gần nhất
        ref_h = None
        if target_npc is not None and id(target_npc) in npc_to_human:
            ref_h = npc_to_human[id(target_npc)]
        elif all_humans:
            ref_h = min(all_humans, key=lambda h: math.hypot(h.x - rx_w, h.y - ry_w))

        if ref_h is not None:
            dx_n = rx_w - ref_h.x
            dy_n = ry_w - ref_h.y
            d_npc = math.hypot(dx_n, dy_n)
            ang_npc_to_rob = math.atan2(dy_n, dx_n)
            ang_rob_to_npc = math.atan2(-dy_n, -dx_n)
            d_alpha_npc = math.atan2(
                math.sin(ang_npc_to_rob - ref_h.theta),
                math.cos(ang_npc_to_rob - ref_h.theta),
            )
            d_alpha_rob = math.atan2(
                math.sin(ang_rob_to_npc - r_theta),
                math.cos(ang_rob_to_npc - r_theta),
            )
            in_fan_ok = (
                0.75 <= d_npc <= 1.45
                and abs(d_alpha_npc) <= math.radians(35.0)
                and abs(d_alpha_rob) <= math.radians(45.0)
                and rob_v < 0.05
            )
            proxy.hri_status = {
                "d_npc": d_npc,
                "delta_alpha_npc": d_alpha_npc,
                "delta_alpha_robot": d_alpha_rob,
                "in_fan_ok": in_fan_ok,
                "nearest_age_radar": ref_h.age_radar_vector(),
            }
        else:
            proxy.hri_status = {
                "d_npc": 5.0,
                "delta_alpha_npc": 0.0,
                "delta_alpha_robot": 0.0,
                "in_fan_ok": False,
                "nearest_age_radar": [1.0, 0.0, 0.0, 1.25 / 2.0],
            }

        # 4. Khối 7: Trạng thái Khay đồ, Đồng hồ, Thời tiết/Tối, Mùa & Trái Tim An Toàn
        inv_items = getattr(getattr(game, "state", None), "inventory", [])
        proxy.inv_ratio = float(np.clip(len(inv_items) / 4.0, 0.0, 1.0))
        proxy.has_quest_item = len(inv_items) > 0
        sched = getattr(game, "schedules", None)
        sim_t = float(getattr(game, "sim_time", 0.0))
        proxy.clock_hour = (
            float(sched.get_time_info(sim_t)[0])
            if sched and hasattr(sched, "get_time_info")
            else 8.0
        )
        atmos = getattr(game, "atmosphere", None)
        proxy.is_rain = getattr(atmos, "current_weather", "") == "rain"
        proxy.season_idx = int(getattr(atmos, "season_idx", 0)) if atmos else 0
        proxy.safety_hearts = int(getattr(game, "hearts", 3))

        # 5. Khối 8: Vector Sự Kiện Ngẫu Nhiên Động CMDP (8 chiều) trong cùng hệ tọa độ 20x20m
        ev_mgr = getattr(game, "events", None)
        act_ev = getattr(ev_mgr, "active_event", None) if ev_mgr else None
        if isinstance(act_ev, dict):
            ev_id_str = str(act_ev.get("id", "spontaneous_gathering"))
            ev_type_id = EVENT_TYPE_IDS.get(ev_id_str, 1)
            ev_x_w = float(act_ev.get("x_tile", 16.0)) * (20.0 / 36.0)
            ev_y_w = float(act_ev.get("y_tile", 12.0)) * (20.0 / 24.0)
            dur = max(1.0, float(act_ev.get("duration", 90.0)))
            rem = float(getattr(ev_mgr, "event_timer", 0.0))
            rew_pts = float(act_ev.get("reward_gold", 90)) + float(
                act_ev.get("reward_score", 70)
            )
            is_haz = (
                1.0
                if ev_id_str in ("spontaneous_gathering", "runaway_animals")
                else 0.0
            )
            proxy.active_event = {
                "id": ev_id_str,
                "type_id": ev_type_id,
                "x": ev_x_w,
                "y": ev_y_w,
                "duration": dur,
                "time_left": rem,
                "reward_norm": min(1.0, rew_pts / 300.0),
                "is_ospace_hazard": is_haz,
            }
        else:
            proxy.active_event = None

        return self._state_builder.build(proxy)

    def compute_motion(
        self, game, tx: float, ty: float, target_npc=None
    ) -> tuple[float, float, bool]:
        """
        Kết hợp đường dẫn A* + Chính sách RL (PPO/DQN 128 chiều) + Lá chắn Khẩn cấp
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

        # Gọi RL Policy làm lớp điều hướng né người và vật cản cục bộ
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
                rot = 0.62
                c, s = math.cos(rot), math.sin(rot)
                ux, uy = ux * c - uy * s, ux * s + uy * c
                slow = True
            elif rl_act == RobotAction.TURN_RIGHT:
                rot = -0.62
                c, s = math.cos(rot), math.sin(rot)
                ux, uy = ux * c - uy * s, ux * s + uy * c
                slow = True
            elif rl_act in (RobotAction.STOP, RobotAction.WAIT):
                active_npcs = game.interior_npcs if game.in_interior else game.npcs
                has_nearby_npc = any(
                    not (getattr(n, "is_home_at_night", False) and not game.in_interior)
                    and math.hypot(n.x - game.robot.x, n.y - game.robot.y) < 120.0
                    for n in active_npcs
                )
                if has_nearby_npc:
                    return 0.0, 0.0, True
                slow = True

        # Lá chắn An toàn Khẩn cấp (chỉ can thiệp ở cự ly rất gần < 46px ~ 0.95m để RL tự chủ né tránh)
        active_npcs = game.interior_npcs if game.in_interior else game.npcs
        for n in active_npcs:
            if getattr(n, "is_home_at_night", False) and not game.in_interior:
                continue
            nd = math.hypot(game.robot.x - n.x, game.robot.y - n.y)
            if nd < 46.0:
                slow = True
                if nd < 34.0 and (target_npc is None or n is not target_npc):
                    ang_to_n = math.atan2(n.y - game.robot.y, n.x - game.robot.x)
                    heading = math.atan2(uy, ux)
                    diff = abs(
                        math.atan2(
                            math.sin(ang_to_n - heading), math.cos(ang_to_n - heading)
                        )
                    )
                    if diff < math.radians(55.0):
                        return 0.0, 0.0, True
                if nd > 1e-3 and (target_npc is None or n is not target_npc or nd < 38.0):
                    rep = (46.0 - nd) / 46.0
                    ux += ((game.robot.x - n.x) / nd) * rep * 1.35
                    uy += ((game.robot.y - n.y) / nd) * rep * 1.35

        norm = math.hypot(ux, uy)
        if norm > 1e-4:
            ux, uy = ux / norm, uy / norm
        return ux, uy, slow


GAME_RL_NAVIGATOR = GameRLNavigator()

