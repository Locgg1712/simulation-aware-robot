# environment/world.py
import json
import math
from pathlib import Path
import random
import numpy as np

from objects.static_object import StaticObject, ShapeType
from objects.semi_static_object import SemiStaticObject
from objects.dynamic_object import DynamicObject
from objects.robot import Robot, RobotAction
from human.human_agent import HumanAgent, HumanActivity, SocialContext
from human.groups import HumanGroup, GroupType
from human.motion_model import update_humans_motion
from human.social_space import evaluate_social_violations
from behavior.context_classifier import classify_all_humans_context
from perception.ground_truth import extract_local_perception
from planning.astar import AStarPlanner
from planning.subgoal_selector import SubgoalSelector
from .physics import (
    check_robot_full_collision,
    check_robot_static_collision,
    cast_lidar_rays,
)
from .topology import TOPOLOGY_NAMES
from .map_generator import MapGenerator
from .spawn_manager import SpawnManager

EVENT_TYPE_IDS: dict[str, int] = {
    "spontaneous_gathering": 1,
    "runaway_animals": 2,
    "sudden_squall": 3,
    "flash_express_order": 4,
    "lost_item_search": 5,
    "iridium_meteor": 6,
    "traveling_merchant": 7,
}


def _load_npcs_metadata() -> dict[str, dict]:
    npcs_path = Path(__file__).resolve().parent.parent / "game" / "data" / "npcs.json"
    if npcs_path.is_file():
        try:
            with open(npcs_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, dict):
                return data
        except Exception:
            pass
    return {}


class World:
    """
    Môi trường mô phỏng 2D tích hợp trực tiếp hệ sinh thái FarmBot Town (Maps 1–4)
    và 11 kịch bản xã hội chuẩn hóa (Topologies 5–15) phục vụ huấn luyện RL 128 chiều:
    - Đồng bộ trực tiếp lộ trình tuần tra `VillagerNPC`, lịch trình ngày/đêm `game/schedules.py`,
      xe kéo `FarmCartAGV`, thú nuôi `FarmAnimal` thông qua `HeadlessGameSession`.
    - Mô phỏng đầy đủ Nhóm tuổi (`elder`, `child`, `adult`), Bán kính Radar An toàn (`1.65m` / `1.25m`),
      Vùng Quạt Tương tác Trước Mặt (`Front Interaction Fan`), Chu kỳ Ngày-Đêm, Thời tiết Mưa/Trơn,
      3 Trái Tim An Toàn và 7 Sự kiện Ngẫu nhiên Động (`Stochastic World Events CMDP`).
    """

    def __init__(self, config: dict):
        world_cfg = config["world"]
        robot_cfg = config["robot"]

        self.width: float = float(world_cfg["width"])
        self.height: float = float(world_cfg["height"])
        self.dt: float = float(world_cfg["dt"])
        self.grid_res: float = float(world_cfg["grid_resolution"])
        self.max_steps: int = int(world_cfg["max_steps"])

        self.grid_cols: int = int(round(self.width / self.grid_res))
        self.grid_rows: int = int(round(self.height / self.grid_res))
        self.static_grid = np.zeros((self.grid_rows, self.grid_cols), dtype=np.int8)
        self.occupancy_grid = np.zeros((self.grid_rows, self.grid_cols), dtype=np.int8)

        self.robot_cfg = robot_cfg
        self.lookahead_dist: float = float(robot_cfg.get("lookahead_dist", 2.5))

        self.map_generator = MapGenerator(self.width, self.height)
        self.spawn_manager = SpawnManager(self.width, self.height, self.grid_res)
        self.astar_planner = AStarPlanner(self.width, self.height, self.grid_res)
        self.subgoal_selector = SubgoalSelector(lookahead_dist=self.lookahead_dist)

        self.npcs_db: dict[str, dict] = _load_npcs_metadata()

        self.current_topology_id: int = 1
        self.num_dynamic_objects: int = int(world_cfg.get("num_dynamic_objects", 2))
        self.num_individual_humans: int = int(world_cfg.get("num_individual_humans", 3))
        self.num_interacting_groups: int = int(world_cfg.get("num_interacting_groups", 1))
        self.num_walking_groups: int = int(world_cfg.get("num_walking_groups", 1))

        self.use_social_astar: bool = False
        self.replan_interval: int = 8

        self.static_objects: list[StaticObject] = []
        self.semi_static_objects: list[SemiStaticObject] = []
        self.dynamic_objects: list[DynamicObject] = []
        self.humans: list[HumanAgent] = []
        self.human_groups: list[HumanGroup] = []
        self.robot: Robot | None = None

        self._headless_game = None
        self._game_npc_bindings: list[tuple[HumanAgent, object]] = []
        self._game_dyn_bindings: list[tuple[DynamicObject, object, str]] = []

        # Trạng thái mở rộng FarmBot Town (Khối 5, 6, 7, 8 trong Vector 128 chiều)
        self.clock_hour: float = 8.0
        self.is_rain: bool = False
        self.season_idx: int = 0
        self.inv_ratio: float = 0.5
        self.has_quest_item: bool = True
        self.safety_hearts: int = 3
        self.active_event: dict | None = None
        self.hri_status: dict = {
            "d_npc": 5.0,
            "delta_alpha_npc": 0.0,
            "delta_alpha_robot": 0.0,
            "in_fan_ok": False,
            "rear_approach": False,
            "elder_speed_violation": 0.0,
            "elder_smart_yield": False,
            "nearest_age_radar": [1.0, 0.0, 0.0, 1.25 / 2.0],
        }

        self.global_path: list[tuple[float, float]] = []
        self.subgoal_info: dict = {
            "subgoal_x": 0.0,
            "subgoal_y": 0.0,
            "dist_to_subgoal": 0.0,
            "angle_to_subgoal": 0.0,
        }

        self.step_count: int = 0
        self.sim_time: float = 0.0
        self.is_collision: bool = False
        self.is_goal_reached: bool = False
        self.collided_object_name: str = ""
        self.lidar_distances: list[float] = []
        self.lidar_hit_points: list[tuple[float, float]] = []
        self.local_perception: dict = {"semi_static": [], "dynamic": [], "humans": []}
        self.social_status: dict = {
            "personal_intrusion": False,
            "intruded_human_ids": [],
            "max_social_cost": 0.0,
            "social_penalty": 0.0,
            "ospace_intrusion": False,
            "group_splitting": False,
            "group_penalty": 0.0,
        }

        self.reset(topology_id=self.current_topology_id)

    def reset(self, seed: int | None = None, topology_id: int | None = None):
        if seed is not None:
            random.seed(seed)
            np.random.seed(seed)

        if topology_id is not None:
            self.current_topology_id = int(topology_id)

        self.step_count = 0
        self.sim_time = 0.0
        self.is_collision = False
        self.is_goal_reached = False
        self.collided_object_name = ""

        # Khởi tạo ngẫu nhiên ngữ cảnh nông trại cho Episode mới
        self.clock_hour = random.uniform(6.5, 20.5)
        self.season_idx = random.randint(0, 3)
        self.is_rain = random.random() < 0.22
        self.inv_ratio = random.choice([0.0, 0.25, 0.50, 0.75, 1.0])
        self.has_quest_item = random.random() < 0.75
        self.safety_hearts = 3
        self.active_event = None

        for _ in range(15):
            (
                self.static_objects,
                self.semi_static_objects,
                start_hint,
                goal_hint,
            ) = self.map_generator.generate(self.current_topology_id)

            self._build_static_grid()

            start_pos = self.spawn_manager.sample_free_point(
                start_hint, self.robot_cfg["radius"], self.static_objects
            )
            goal_pos = self.spawn_manager.sample_free_point(
                goal_hint, self.robot_cfg["goal_radius"], self.static_objects
            )

            if self.spawn_manager.check_path_feasibility(
                start_pos, goal_pos, self.static_grid
            ):
                break

        init_theta = math.atan2(goal_pos[1] - start_pos[1], goal_pos[0] - start_pos[0])
        self.robot = Robot(
            x=start_pos[0],
            y=start_pos[1],
            theta=init_theta,
            radius=self.robot_cfg["radius"],
            v_max=self.robot_cfg["v_max"],
            omega_max=self.robot_cfg["omega_max"],
            sensor_radius=self.robot_cfg["sensor_radius"],
            goal_x=goal_pos[0],
            goal_y=goal_pos[1],
            goal_radius=self.robot_cfg["goal_radius"],
        )

        self.dynamic_objects = self.spawn_manager.spawn_dynamic_objects(
            num_objects=0 if self.current_topology_id in (1, 2, 3, 4) else self.num_dynamic_objects,
            robot=self.robot,
            static_objects=self.static_objects,
            semi_static_objects=self.semi_static_objects,
        )

        self.humans, self.human_groups = self.spawn_manager.spawn_humans_and_groups(
            robot=self.robot,
            static_objects=self.static_objects,
            semi_static_objects=self.semi_static_objects,
            dynamic_objects=self.dynamic_objects,
            num_individual_humans=0 if self.current_topology_id in (1, 2, 3, 4) else self.num_individual_humans,
            num_interacting_groups=self.num_interacting_groups,
            num_walking_groups=0 if self.current_topology_id in (1, 2, 3, 4) else self.num_walking_groups,
        )

        self._game_npc_bindings.clear()
        self._game_dyn_bindings.clear()
        if self.current_topology_id in (1, 2, 3, 4):
            self._setup_headless_game_entities()

        self._setup_stochastic_world_event()

        classify_all_humans_context(self.humans, self.human_groups, self.robot)
        self.update_occupancy_grid()
        self.replan_global_path()
        self._update_subgoal()
        self._update_perception()

        if self.global_path:
            self.robot.theta = math.atan2(
                self.robot.subgoal_y - self.robot.y,
                self.robot.subgoal_x - self.robot.x,
            )
            self._update_subgoal()
            self._update_perception()

    def _setup_headless_game_entities(self):
        """Khởi tạo và gắn kết trực tiếp toàn bộ VillagerNPC, lịch trình schedules.py, AGV và Thú nuôi từ `game/`."""
        if self.robot is None:
            return
        from game.rl_bridge import HeadlessGameSession
        from game.constants import px_to_m, SCREEN_W, SCREEN_H

        if self._headless_game is None:
            self._headless_game = HeadlessGameSession()

        sim_offset = ((self.clock_hour - 6.0) / 18.0) * 225.0
        self._headless_game.atmosphere.current_weather = "rain" if self.is_rain else "sunny"
        self._headless_game.atmosphere.season_idx = self.season_idx
        self._headless_game.reset_map(
            self.current_topology_id, sim_time_offset=max(0.0, sim_offset)
        )
        self.clock_hour = float(
            self._headless_game.schedules.get_time_info(self._headless_game.sim_time)[0]
        )

        sx_scale = self.width / float(SCREEN_W)
        sy_scale = self.height / float(SCREEN_H)

        # 1. Gắn kết các Xe kéo AGV & Thú nuôi thực từ `game/`
        base_dyn_id = 500
        for agv in self._headless_game.agvs:
            wx, wy = agv.x * sx_scale, agv.y * sy_scale
            if math.hypot(wx - self.robot.x, wy - self.robot.y) < 1.35 and agv.waypoints:
                best_i, best_d = 0, -1.0
                for idx, (px, py) in enumerate(agv.waypoints):
                    d = math.hypot(px * sx_scale - self.robot.x, py * sy_scale - self.robot.y)
                    if d > best_d:
                        best_d = d
                        best_i = idx
                agv.x, agv.y = agv.waypoints[best_i]
                agv.wp_idx = (best_i + 1) % len(agv.waypoints)
                wx, wy = agv.x * sx_scale, agv.y * sy_scale

            wx, wy = self.spawn_manager.sample_free_point((wx, wy), 0.35, self.static_objects)
            agv.x, agv.y = wx / sx_scale, wy / sy_scale
            dyn_obj = DynamicObject(
                obj_id=base_dyn_id,
                x=wx,
                y=wy,
                radius=0.35,
                speed=px_to_m(agv.speed),
                theta=agv.theta,
                waypoints=[],
                name=f"game_agv_{base_dyn_id}",
            )
            dyn_obj._from_game_entity = True
            self.dynamic_objects.append(dyn_obj)
            self._game_dyn_bindings.append((dyn_obj, agv, "agv"))
            base_dyn_id += 1

        for anim in self._headless_game.animals[:3]:
            wx, wy = anim.x * sx_scale, anim.y * sy_scale
            if math.hypot(wx - self.robot.x, wy - self.robot.y) < 1.25:
                continue
            wx, wy = self.spawn_manager.sample_free_point((wx, wy), 0.28, self.static_objects)
            anim.x, anim.y = wx / sx_scale, wy / sy_scale
            anim_spd_px = math.hypot(getattr(anim, "vx", 0.0), getattr(anim, "vy", 0.0))
            anim_theta = math.atan2(getattr(anim, "vy", 0.0), getattr(anim, "vx", 0.0))
            dyn_obj = DynamicObject(
                obj_id=base_dyn_id,
                x=wx,
                y=wy,
                radius=0.28,
                speed=px_to_m(anim_spd_px),
                theta=anim_theta,
                waypoints=[],
                name=f"game_{getattr(anim, 'sprite_key', 'animal')}_{base_dyn_id}",
            )
            dyn_obj._from_game_entity = True
            self.dynamic_objects.append(dyn_obj)
            self._game_dyn_bindings.append((dyn_obj, anim, "animal"))
            base_dyn_id += 1

        # 2. Gắn kết toàn bộ VillagerNPC thực tế từ `game/maps.py`, `game/schedules.py` & `game/data/npcs.json`
        base_npc_id = 200
        for npc in self._headless_game.npcs:
            wx, wy = npc.x * sx_scale, npc.y * sy_scale
            if math.hypot(wx - self.robot.x, wy - self.robot.y) < 1.35:
                if npc.patrol_points:
                    best_i, best_d = 0, -1.0
                    for idx, (px, py) in enumerate(npc.patrol_points):
                        d = math.hypot(px * sx_scale - self.robot.x, py * sy_scale - self.robot.y)
                        if d > best_d:
                            best_d = d
                            best_i = idx
                    npc.x, npc.y = npc.patrol_points[best_i]
                    npc.wp_idx = (best_i + 1) % len(npc.patrol_points)
                    wx, wy = npc.x * sx_scale, npc.y * sy_scale
                else:
                    continue

            wx, wy = self.spawn_manager.sample_free_point((wx, wy), 0.30, self.static_objects)
            npc.x, npc.y = wx / sx_scale, wy / sy_scale
            wps_world = [
                (px * sx_scale, py * sy_scale) for (px, py) in (npc.patrol_points or [])
            ]
            npc_meta = self.npcs_db.get(npc.name, {})
            age_grp = str(npc_meta.get("age_group", "adult"))
            safe_r = float(npc_meta.get("safety_radius_m", 1.65 if age_grp in ("elder", "child") else 1.25))

            h_agent = HumanAgent(
                obj_id=base_npc_id,
                x=wx,
                y=wy,
                theta=npc.theta,
                desired_speed=max(0.4, px_to_m(npc.base_speed)),
                radius=0.30,
                waypoints=wps_world,
                name=npc.name,
                age_group=age_grp,
                safety_radius=safe_r,
            )
            h_agent._from_game_npc = True
            vx_m = px_to_m(npc.vx)
            vy_m = px_to_m(npc.vy)
            h_agent.set_velocity(vx_m, vy_m)
            if h_agent.speed < 0.05:
                h_agent.theta = npc.theta
            self.humans.append(h_agent)
            self._game_npc_bindings.append((h_agent, npc))
            base_npc_id += 1

    def _setup_stochastic_world_event(self):
        """
        Kích hoạt ngẫu nhiên 1 trong 7 Sự kiện Thế giới Động (Mục 11 & Mục 12.1 - Khối 8)
        từ `game/random_events.py` để huấn luyện RL thích ứng môi trường Non-Stationary CMDP.
        """
        if self.robot is None:
            return
        from game.random_events import FALLBACK_EVENTS

        trigger_prob = 0.75 if self.current_topology_id in (1, 2, 3, 4) else 0.50
        if random.random() > trigger_prob:
            self.active_event = None
            return

        ev_key = random.choice(list(FALLBACK_EVENTS.keys()))
        ev_raw = FALLBACK_EVENTS[ev_key]
        ev_type_id = EVENT_TYPE_IDS.get(ev_key, 1)

        # Chuyển tọa độ tile (36x24) sang hệ mét (20x20) và lấy điểm hợp lệ trên bản đồ
        raw_x = float(ev_raw.get("x_tile", 16.0)) * (self.width / 36.0)
        raw_y = float(ev_raw.get("y_tile", 12.0)) * (self.height / 24.0)
        ex, ey = self.spawn_manager.sample_free_point((raw_x, raw_y), 0.55, self.static_objects)

        duration = float(ev_raw.get("duration", 85.0))
        reward_pts = float(ev_raw.get("reward_gold", 90)) + float(ev_raw.get("reward_score", 70))
        is_hazard = ev_key in ("spontaneous_gathering", "runaway_animals")

        self.active_event = {
            "id": ev_key,
            "type_id": ev_type_id,
            "x": ex,
            "y": ey,
            "duration": duration,
            "time_left": duration,
            "reward_norm": min(1.0, reward_pts / 300.0),
            "is_ospace_hazard": 1.0 if is_hazard else 0.0,
        }

        if ev_key == "sudden_squall":
            self.is_rain = True
        elif ev_key == "runaway_animals" and math.hypot(ex - self.robot.x, ey - self.robot.y) > 1.8:
            wp_alt = self.spawn_manager.sample_free_point(
                (max(2.0, min(self.width - 2.0, ex + 3.0)), ey), 0.35, self.static_objects
            )
            sheep = DynamicObject(
                obj_id=880,
                x=ex,
                y=ey,
                radius=0.32,
                speed=0.55,
                theta=0.0,
                waypoints=[(ex, ey), wp_alt],
                name="event_runaway_sheep",
            )
            self.dynamic_objects.append(sheep)

    def _sync_headless_game_entities(self):
        """Đồng bộ vị trí, vận tốc và hướng nhìn từ `HeadlessGameSession` sang `World` ở mỗi bước `step()`."""
        if self._headless_game is None or self.robot is None:
            return
        from game.constants import px_to_m, SCREEN_W, SCREEN_H

        sx_scale = self.width / float(SCREEN_W)
        sy_scale = self.height / float(SCREEN_H)

        self._headless_game.atmosphere.current_weather = "rain" if self.is_rain else "sunny"
        self._headless_game.step_entities(
            self.dt, self.robot.x, self.robot.y, self.width, self.height
        )
        self.clock_hour = float(
            self._headless_game.schedules.get_time_info(self._headless_game.sim_time)[0]
        )

        for dyn_obj, ent, kind in self._game_dyn_bindings:
            wx = ent.x * sx_scale
            wy = ent.y * sy_scale
            collided, _ = check_robot_static_collision(
                x=wx,
                y=wy,
                radius=dyn_obj.radius,
                static_objects=self.static_objects,
                world_width=self.width,
                world_height=self.height,
            )
            if not collided:
                dyn_obj.x = wx
                dyn_obj.y = wy
            else:
                ent.x = dyn_obj.x / sx_scale
                ent.y = dyn_obj.y / sy_scale
            if kind == "agv":
                dyn_obj.theta = ent.theta
                dyn_obj.speed = (
                    px_to_m(ent.speed) if getattr(ent, "mode", "patrol") == "patrol" else 0.0
                )
            else:
                anim_vx = getattr(ent, "vx", 0.0)
                anim_vy = getattr(ent, "vy", 0.0)
                anim_spd_px = math.hypot(anim_vx, anim_vy)
                if anim_spd_px > 1e-3:
                    dyn_obj.theta = math.atan2(anim_vy, anim_vx)
                dyn_obj.speed = px_to_m(anim_spd_px)

        for h_agent, npc in self._game_npc_bindings:
            wx = npc.x * sx_scale
            wy = npc.y * sy_scale
            collided, _ = check_robot_static_collision(
                x=wx,
                y=wy,
                radius=h_agent.radius,
                static_objects=self.static_objects,
                world_width=self.width,
                world_height=self.height,
            )
            if not collided:
                h_agent.x = wx
                h_agent.y = wy
            else:
                npc.x = h_agent.x / sx_scale
                npc.y = h_agent.y / sy_scale
                if npc.patrol_points:
                    npc.wp_idx = (npc.wp_idx + 1) % len(npc.patrol_points)

            vx_m = px_to_m(npc.vx)
            vy_m = px_to_m(npc.vy)
            h_agent.set_velocity(vx_m, vy_m)
            if h_agent.speed < 0.05:
                h_agent.theta = npc.theta

    def replan_global_path(self):
        if self.robot is None:
            return
        self.global_path = self.astar_planner.plan(
            start_pos=self.robot.position,
            goal_pos=(self.robot.goal_x, self.robot.goal_y),
            static_grid=self.static_grid,
            semi_static_objects=self.semi_static_objects,
            use_social_cost=self.use_social_astar,
            humans=self.humans,
            groups=self.human_groups,
        )

    def _update_subgoal(self):
        if self.robot is None:
            return
        self.subgoal_info = self.subgoal_selector.get_subgoal(
            robot_x=self.robot.x,
            robot_y=self.robot.y,
            robot_theta=self.robot.theta,
            global_path=self.global_path,
            goal_x=self.robot.goal_x,
            goal_y=self.robot.goal_y,
        )
        self.robot.subgoal_x = self.subgoal_info["subgoal_x"]
        self.robot.subgoal_y = self.subgoal_info["subgoal_y"]

    def _build_static_grid(self):
        self.static_grid.fill(0)
        half_res = self.grid_res / 2.0

        for obj in self.static_objects:
            if obj.shape == ShapeType.RECTANGLE:
                rx, ry, rw, rh = obj.bbox
                c_min = max(0, int(rx / self.grid_res))
                c_max = min(self.grid_cols - 1, int((rx + rw) / self.grid_res))
                r_min = max(0, int(ry / self.grid_res))
                r_max = min(self.grid_rows - 1, int((ry + rh) / self.grid_res))
                self.static_grid[r_min : r_max + 1, c_min : c_max + 1] = 1
            elif obj.shape == ShapeType.CIRCLE:
                rad = obj.radius + half_res * 0.5
                c_min = max(0, int((obj.x - rad) / self.grid_res))
                c_max = min(self.grid_cols - 1, int((obj.x + rad) / self.grid_res))
                r_min = max(0, int((obj.y - rad) / self.grid_res))
                r_max = min(self.grid_rows - 1, int((obj.y + rad) / self.grid_res))
                for r in range(r_min, r_max + 1):
                    cy = (r + 0.5) * self.grid_res
                    for c in range(c_min, c_max + 1):
                        cx = (c + 0.5) * self.grid_res
                        if math.hypot(cx - obj.x, cy - obj.y) <= rad:
                            self.static_grid[r, c] = 1

    def update_occupancy_grid(self):
        np.copyto(self.occupancy_grid, self.static_grid)
        for door in self.semi_static_objects:
            if not door.passable:
                rx, ry, rw, rh = door.bbox
                c_min = max(0, int(rx / self.grid_res))
                c_max = min(self.grid_cols - 1, int((rx + rw) / self.grid_res))
                r_min = max(0, int(ry / self.grid_res))
                r_max = min(self.grid_rows - 1, int((ry + rh) / self.grid_res))
                self.occupancy_grid[r_min : r_max + 1, c_min : c_max + 1] = 1

    def _update_hri_and_age_radar(self):
        """
        Cập nhật thông số Vùng Quạt Tương tác Trước Mặt (Khối 5) và
        Radar An toàn Nhận thức Độ Tuổi (Khối 6) đối với NPC gần nhất.
        """
        if self.robot is None or not self.humans:
            self.hri_status = {
                "d_npc": 5.0,
                "delta_alpha_npc": 0.0,
                "delta_alpha_robot": 0.0,
                "in_fan_ok": False,
                "rear_approach": False,
                "elder_speed_violation": 0.0,
                "elder_smart_yield": False,
                "nearest_age_radar": [1.0, 0.0, 0.0, 1.25 / 2.0],
            }
            return

        nearest_h = min(
            self.humans,
            key=lambda h: math.hypot(h.x - self.robot.x, h.y - self.robot.y),
        )
        dx = self.robot.x - nearest_h.x
        dy = self.robot.y - nearest_h.y
        d_npc = math.hypot(dx, dy)

        ang_npc_to_rob = math.atan2(dy, dx)
        ang_rob_to_npc = math.atan2(-dy, -dx)

        delta_alpha_npc = math.atan2(
            math.sin(ang_npc_to_rob - nearest_h.theta),
            math.cos(ang_npc_to_rob - nearest_h.theta),
        )
        delta_alpha_robot = math.atan2(
            math.sin(ang_rob_to_npc - self.robot.theta),
            math.cos(ang_rob_to_npc - self.robot.theta),
        )

        in_fan_ok = (
            0.75 <= d_npc <= 1.45
            and abs(delta_alpha_npc) <= math.radians(35.0)
            and abs(delta_alpha_robot) <= math.radians(45.0)
            and self.robot.v < 0.05
        )
        rear_approach = (
            d_npc < 1.05
            and abs(delta_alpha_npc) > math.radians(110.0)
            and self.robot.v > 0.25
        )

        r_safe = nearest_h.safety_radius
        elder_speed_violation = 0.0
        elder_smart_yield = False
        if d_npc <= r_safe:
            is_sensitive = nearest_h.age_group in ("elder", "child")
            if self.robot.v > 0.35:
                lam = 2.5 if is_sensitive else 1.0
                ratio = max(0.0, (r_safe - d_npc) / max(0.1, r_safe))
                elder_speed_violation = (
                    -lam * (self.robot.v / max(0.1, self.robot.v_max)) * (ratio ** 2)
                )
            elif is_sensitive and 0.01 <= self.robot.v <= 0.35:
                elder_smart_yield = True

        self.hri_status = {
            "d_npc": d_npc,
            "delta_alpha_npc": delta_alpha_npc,
            "delta_alpha_robot": delta_alpha_robot,
            "in_fan_ok": in_fan_ok,
            "rear_approach": rear_approach,
            "elder_speed_violation": elder_speed_violation,
            "elder_smart_yield": elder_smart_yield,
            "nearest_age_radar": nearest_h.age_radar_vector(),
        }

    def _update_perception(self):
        if self.robot is None:
            return
        self.lidar_distances, self.lidar_hit_points = cast_lidar_rays(
            rx=self.robot.x,
            ry=self.robot.y,
            r_theta=self.robot.theta,
            num_rays=int(self.robot_cfg["num_lidar_rays"]),
            max_range=self.robot.sensor_radius,
            static_objects=self.static_objects,
            world_width=self.width,
            world_height=self.height,
            semi_static_objects=self.semi_static_objects,
        )
        self.local_perception = extract_local_perception(
            self.robot, self.semi_static_objects, self.dynamic_objects, self.humans
        )
        self.social_status = evaluate_social_violations(
            self.robot.x,
            self.robot.y,
            self.robot.radius,
            self.humans,
            self.human_groups,
        )
        self._update_hri_and_age_radar()

    def step(self, action: int | RobotAction | None = None) -> dict:
        if self.robot is None:
            raise RuntimeError("Robot chưa được khởi tạo trong World.")

        if self.is_collision or self.is_goal_reached:
            return self.get_info()

        for door in self.semi_static_objects:
            door.update(self.dt, robot_pos=self.robot.position)
        self.update_occupancy_grid()

        if self.current_topology_id in (1, 2, 3, 4) and self._headless_game is not None:
            self._sync_headless_game_entities()
        else:
            self.clock_hour = 6.0 + ((self.clock_hour - 6.0 + self.dt * 0.075) % 18.0)

        if self.active_event is not None:
            self.active_event["time_left"] = max(
                0.0, float(self.active_event["time_left"]) - self.dt
            )
            if self.active_event["time_left"] <= 0.0:
                self.active_event = None

        for dyn in self.dynamic_objects:
            if not getattr(dyn, "_from_game_entity", False):
                dyn.update(self.dt, self.static_objects, self.width, self.height)

        non_game_humans = [
            h for h in self.humans if not getattr(h, "_from_game_npc", False)
        ]
        if non_game_humans or self.human_groups:
            update_humans_motion(
                humans=non_game_humans,
                groups=self.human_groups,
                static_objects=self.static_objects,
                semi_static_objects=self.semi_static_objects,
                robot=self.robot,
                dt=self.dt,
                world_width=self.width,
                world_height=self.height,
            )

        if action is not None:
            self.robot.set_discrete_action(action)

        next_x, next_y, next_theta = self.robot.compute_next_pose(self.dt)

        collided, hit_obj = check_robot_full_collision(
            x=next_x,
            y=next_y,
            radius=self.robot.radius,
            static_objects=self.static_objects,
            semi_static_objects=self.semi_static_objects,
            dynamic_objects=self.dynamic_objects,
            world_width=self.width,
            world_height=self.height,
            humans=self.humans,
        )

        if collided:
            self.is_collision = True
            self.collided_object_name = hit_obj.name if hit_obj else "world_boundary"
            if hit_obj is not None and isinstance(hit_obj, HumanAgent):
                if self.robot.v >= 0.85 * self.robot.v_max:
                    self.safety_hearts = 0
                else:
                    self.safety_hearts = max(0, self.safety_hearts - 1)
            self.robot.set_discrete_action(RobotAction.STOP)
        else:
            self.robot.apply_pose(next_x, next_y, next_theta)

        self.step_count += 1
        self.sim_time += self.dt

        if self.robot.has_reached_goal():
            self.is_goal_reached = True
            self.robot.set_discrete_action(RobotAction.STOP)

        classify_all_humans_context(self.humans, self.human_groups, self.robot)
        if self.step_count % self.replan_interval == 0:
            self.replan_global_path()
        self._update_subgoal()
        self._update_perception()
        return self.get_info()

    def get_info(self) -> dict:
        topo_name = TOPOLOGY_NAMES.get(
            self.current_topology_id, str(self.current_topology_id)
        )
        return {
            "topology": topo_name,
            "step": self.step_count,
            "sim_time": round(self.sim_time, 2),
            "clock_hour": round(self.clock_hour, 2),
            "is_rain": self.is_rain,
            "safety_hearts": self.safety_hearts,
            "robot_pos": (round(self.robot.x, 3), round(self.robot.y, 3)),
            "robot_theta_deg": round(math.degrees(self.robot.theta), 1),
            "robot_v": round(self.robot.v, 2),
            "robot_omega": round(self.robot.omega, 2),
            "distance_to_goal": round(self.robot.distance_to_goal(), 3),
            "subgoal_pos": (
                round(self.robot.subgoal_x, 2),
                round(self.robot.subgoal_y, 2),
            ),
            "dist_to_subgoal": round(self.subgoal_info["dist_to_subgoal"], 2),
            "is_collision": self.is_collision,
            "collided_with": self.collided_object_name,
            "is_goal_reached": self.is_goal_reached,
            "social_status": self.social_status,
            "hri_status": self.hri_status,
        }
