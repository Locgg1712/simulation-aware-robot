# environment/world.py
import math
import random
import numpy as np

from objects.static_object import StaticObject, ShapeType
from objects.semi_static_object import SemiStaticObject
from objects.dynamic_object import DynamicObject
from objects.robot import Robot, RobotAction
from human.human_agent import HumanAgent, HumanActivity, SocialContext
from human.groups import HumanGroup
from human.motion_model import update_humans_motion
from human.social_space import evaluate_social_violations
from behavior.context_classifier import classify_all_humans_context
from perception.ground_truth import extract_local_perception
from planning.astar import AStarPlanner
from planning.subgoal_selector import SubgoalSelector
from .physics import check_robot_full_collision, cast_lidar_rays
from .topology import TOPOLOGY_NAMES
from .map_generator import MapGenerator
from .spawn_manager import SpawnManager


class World:
    """
    Quản lý môi trường 2D hỗ trợ 4 Bản đồ Stardew Valley & Chế độ Vào Nhà (Indoor House Mode):
    - Khi ở ngoài trời (in_indoor_house=False): Robot di chuyển trên bản đồ nông trại/thị trấn,
      có thể đi vào bất kỳ cửa nhà nào (thảm đỏ trước cửa) hoặc bấm phím [E].
    - Khi vào trong nhà (in_indoor_house=True): Vùng bên ngoài căn phòng được làm tối đen,
      Robot di chuyển bên trong phòng nội thất, giao hàng cho NPC trong nhà rồi đi ra cửa Exit.
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

        # Khởi động mặc định ở Map 1 (Beach & Island Farm)
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

        # Trạng thái Hệ thống Vào Nhà (Indoor / Outdoor Transition)
        self.in_indoor_house: bool = False
        self.current_house_name: str = ""
        self.indoor_room_bounds: tuple[float, float, float, float] = (4.5, 4.0, 11.0, 12.0)
        self.indoor_exit_portal: tuple[float, float] = (10.0, 15.4)
        self.indoor_delivered: bool = False
        self.portal_cooldown: float = 0.0
        self.house_portals: list[dict] = []
        self._saved_outdoor_state: dict | None = None

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

    def _detect_house_portals(self):
        """Tìm tất cả các ngôi nhà trên bản đồ và gắn tọa độ Cửa Vào Nhà (Portal Mat)."""
        self.house_portals.clear()
        for obj in self.static_objects:
            if obj.shape != ShapeType.RECTANGLE:
                continue
            rx, ry, rw, rh = obj.bbox
            is_house = obj.name.startswith("house_") or (
                not obj.name.startswith("wall_")
                and not obj.name.startswith("water_")
                and not obj.name.startswith("fence_")
                and not obj.name.startswith("greenhouse_")
                and rw >= 1.75
                and rh >= 1.75
            )
            if is_house:
                door_x = rx + rw / 2.0
                door_y = ry + rh + 0.42
                if 0.8 < door_x < self.width - 0.8 and 0.8 < door_y < self.height - 0.8:
                    clean_name = (
                        obj.name.replace("house_", "")
                        .split("_")[0]
                        .replace("Pierres", "Pierre's Store")
                        .replace("Mayors", "Mayor's Manor")
                        .replace("Stardrop", "Stardrop Saloon")
                    )
                    self.house_portals.append(
                        {
                            "id": obj.id,
                            "name": f"{clean_name} House",
                            "door_x": door_x,
                            "door_y": door_y,
                            "bbox": (rx, ry, rw, rh),
                        }
                    )

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
        self.in_indoor_house = False
        self.indoor_delivered = False
        self.portal_cooldown = 0.0
        self._saved_outdoor_state = None

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

        self._detect_house_portals()

        # Đặt Goal ngay tại Cửa một Ngôi Nhà để Robot tự động đi vào nhà giao hàng rồi đi ra!
        if self.house_portals and self.current_topology_id in (1, 2, 3, 4):
            target_portal = random.choice(self.house_portals)
            cand_goal = (target_portal["door_x"], target_portal["door_y"])
            if self.spawn_manager.check_path_feasibility(
                start_pos, cand_goal, self.static_grid
            ):
                goal_pos = cand_goal

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
            num_objects=self.num_dynamic_objects,
            robot=self.robot,
            static_objects=self.static_objects,
            semi_static_objects=self.semi_static_objects,
        )

        self.humans, self.human_groups = self.spawn_manager.spawn_humans_and_groups(
            robot=self.robot,
            static_objects=self.static_objects,
            semi_static_objects=self.semi_static_objects,
            dynamic_objects=self.dynamic_objects,
            num_individual_humans=self.num_individual_humans,
            num_interacting_groups=self.num_interacting_groups,
            num_walking_groups=self.num_walking_groups,
        )

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

    def enter_house(self, portal: dict):
        """Chuyển từ Bản đồ Ngoài trời vào Không gian Nội thất bên trong Ngôi nhà."""
        if self.in_indoor_house or self.robot is None:
            return

        # Lưu lại toàn bộ trạng thái ngoài trời để khi ra khỏi nhà sẽ khôi phục
        self._saved_outdoor_state = {
            "static_objects": list(self.static_objects),
            "semi_static_objects": list(self.semi_static_objects),
            "dynamic_objects": list(self.dynamic_objects),
            "humans": list(self.humans),
            "human_groups": list(self.human_groups),
            "return_pos": (portal["door_x"], min(self.height - 1.0, portal["door_y"] + 0.35)),
            "start_origin": self.robot.trajectory[0] if self.robot.trajectory else (3.5, 9.5),
        }

        self.in_indoor_house = True
        self.indoor_delivered = False
        self.current_house_name = portal["name"]
        self.portal_cooldown = 1.2

        (
            interior_objs,
            room_bounds,
            entry_spawn,
            exit_portal,
            indoor_goal,
        ) = self.map_generator.generate_house_interior(portal["id"], portal["name"])

        self.static_objects = interior_objs
        self.semi_static_objects = []
        self.dynamic_objects = []
        self.indoor_room_bounds = room_bounds
        self.indoor_exit_portal = exit_portal

        # Tạo NPC Chủ nhà đứng đón bên trong phòng
        host_npc = HumanAgent(
            obj_id=99,
            x=indoor_goal[0],
            y=max(room_bounds[1] + 1.2, indoor_goal[1] - 0.85),
            theta=math.pi / 2.0,
            radius=0.32,
            speed=0.0,
            activity=HumanActivity.STANDING,
            social_context=SocialContext.ALONE,
            waypoints=[],
        )
        self.humans = [host_npc]
        self.human_groups = []

        # Đặt Robot ở cửa trong nhà, hướng mặt lên phía bàn giao hàng
        self.robot.x, self.robot.y = entry_spawn
        self.robot.theta = -math.pi / 2.0
        self.robot.goal_x, self.robot.goal_y = indoor_goal
        self.robot.trajectory.clear()
        self.robot.trajectory.append(entry_spawn)

        self._build_static_grid()
        self.update_occupancy_grid()
        classify_all_humans_context(self.humans, self.human_groups, self.robot)
        self.replan_global_path()
        self._update_subgoal()
        self._update_perception()

    def exit_house(self):
        """Bước từ Cửa phòng Nội thất ra lại Bản đồ Thị trấn/Nông trại bên ngoài."""
        if not self.in_indoor_house or self._saved_outdoor_state is None or self.robot is None:
            return

        saved = self._saved_outdoor_state
        self.static_objects = saved["static_objects"]
        self.semi_static_objects = saved["semi_static_objects"]
        self.dynamic_objects = saved["dynamic_objects"]
        self.humans = saved["humans"]
        self.human_groups = saved["human_groups"]

        self.in_indoor_house = False
        self.current_house_name = ""
        self.portal_cooldown = 1.5

        ret_x, ret_y = saved["return_pos"]
        self.robot.x, self.robot.y = ret_x, ret_y
        self.robot.theta = math.pi / 2.0

        # Sau khi giao hàng trong nhà xong và bước ra ngoài -> Điểm đích tiếp theo là quay về điểm xuất phát
        orig_x, orig_y = saved["start_origin"]
        if math.hypot(orig_x - ret_x, orig_y - ret_y) > 2.5:
            self.robot.goal_x, self.robot.goal_y = orig_x, orig_y
        else:
            self.is_goal_reached = True

        self._build_static_grid()
        self.update_occupancy_grid()
        classify_all_humans_context(self.humans, self.human_groups, self.robot)
        self.replan_global_path()
        self._update_subgoal()
        self._update_perception()

    def toggle_indoor_house(self):
        """Phím tắt [E]: Vào ngay ngôi nhà gần nhất hoặc Đi ra khỏi nhà hiện tại."""
        if self.in_indoor_house:
            self.exit_house()
        elif self.house_portals and self.robot is not None:
            nearest = min(
                self.house_portals,
                key=lambda p: math.hypot(p["door_x"] - self.robot.x, p["door_y"] - self.robot.y),
            )
            self.enter_house(nearest)

    def next_topology(self):
        """Chuyển vòng tròn qua 4 Map Stardew Valley (1 -> 2 -> 3 -> 4 -> 1)."""
        next_id = (self.current_topology_id % 4) + 1
        self.reset(topology_id=next_id)

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

        for r in range(self.grid_rows):
            cy = (r + 0.5) * self.grid_res
            for c in range(self.grid_cols):
                cx = (c + 0.5) * self.grid_res
                for obj in self.static_objects:
                    if obj.shape == ShapeType.RECTANGLE:
                        rx, ry, rw, rh = obj.bbox
                        if (rx <= cx <= rx + rw) and (ry <= cy <= ry + rh):
                            self.static_grid[r, c] = 1
                            break
                    elif obj.shape == ShapeType.CIRCLE:
                        if math.hypot(cx - obj.x, cy - obj.y) <= (
                            obj.radius + half_res * 0.5
                        ):
                            self.static_grid[r, c] = 1
                            break

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

    def step(self, action: int | RobotAction | None = None) -> dict:
        if self.robot is None:
            raise RuntimeError("Robot chưa được khởi tạo trong World.")

        if self.is_collision or self.is_goal_reached:
            return self.get_info()

        if self.portal_cooldown > 0.0:
            self.portal_cooldown = max(0.0, self.portal_cooldown - self.dt)

        for door in self.semi_static_objects:
            door.update(self.dt, robot_pos=self.robot.position)
        self.update_occupancy_grid()

        for dyn in self.dynamic_objects:
            dyn.update(self.dt, self.static_objects, self.width, self.height)

        update_humans_motion(
            humans=self.humans,
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
            self.robot.set_discrete_action(RobotAction.STOP)
        else:
            self.robot.apply_pose(next_x, next_y, next_theta)

        self.step_count += 1
        self.sim_time += self.dt

        # ------------------------------------------------------------------
        # KIỂM TRA CHUYỂN CẢNH VÀO NHÀ / RA KHỎI NHÀ & NHIỆM VỤ GIAO HÀNG
        # ------------------------------------------------------------------
        if not self.in_indoor_house and self.portal_cooldown <= 0.0:
            for portal in self.house_portals:
                if math.hypot(self.robot.x - portal["door_x"], self.robot.y - portal["door_y"]) <= 0.65:
                    self.enter_house(portal)
                    return self.get_info()

        if self.in_indoor_house:
            # Nếu đã giao hàng xong tới bàn/NPC trong nhà -> Đổi Goal ra Cửa Thoát (Exit Mat)
            if not self.indoor_delivered and self.robot.has_reached_goal():
                self.indoor_delivered = True
                self.robot.goal_x, self.robot.goal_y = self.indoor_exit_portal
                self.replan_global_path()
                self._update_subgoal()
            # Nếu đi tới Thảm Cửa Ra (Exit Mat) -> Bước ra lại bản đồ lớn
            elif self.portal_cooldown <= 0.0 and math.hypot(
                self.robot.x - self.indoor_exit_portal[0],
                self.robot.y - self.indoor_exit_portal[1],
            ) <= 0.68:
                self.exit_house()
                return self.get_info()
        else:
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
        if self.in_indoor_house:
            topo_name = f"INDOOR: {self.current_house_name}"
        return {
            "topology": topo_name,
            "in_indoor_house": self.in_indoor_house,
            "step": self.step_count,
            "sim_time": round(self.sim_time, 2),
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
        }