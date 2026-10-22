# environment/world.py
import math
import random
import numpy as np

from objects.static_object import StaticObject, ShapeType
from objects.semi_static_object import SemiStaticObject
from objects.dynamic_object import DynamicObject
from objects.robot import Robot, RobotAction
from human.human_agent import HumanAgent
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
    Quản lý môi trường 2D kết hợp Bản đồ lưới (Occupancy Grid),
    15 Topology Procedural, Semi-static Doors, Dynamic Objects, Humans,
    Global A* Path Planner & Sliding Local Sub-goal (Phase 4).
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

        self.current_topology_id: int = 8
        self.num_dynamic_objects: int = int(world_cfg.get("num_dynamic_objects", 2))
        self.num_individual_humans: int = int(world_cfg.get("num_individual_humans", 3))
        self.num_interacting_groups: int = int(world_cfg.get("num_interacting_groups", 1))
        self.num_walking_groups: int = int(world_cfg.get("num_walking_groups", 1))

        # Cờ cho phép A* tính cả chi phí vùng O-Space khi chạy Baseline 2 (Social A*)
        self.use_social_astar: bool = False
        self.replan_interval: int = 8

        self.static_objects: list[StaticObject] = []
        self.semi_static_objects: list[SemiStaticObject] = []
        self.dynamic_objects: list[DynamicObject] = []
        self.humans: list[HumanAgent] = []
        self.human_groups: list[HumanGroup] = []
        self.robot: Robot | None = None

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

        # Hướng mũi Robot ban đầu về phía Sub-goal đầu tiên để di chuyển mượt ngay từ t=0
        if self.global_path:
            self.robot.theta = math.atan2(
                self.robot.subgoal_y - self.robot.y,
                self.robot.subgoal_x - self.robot.x,
            )
            self._update_subgoal()
            self._update_perception()

    def next_topology(self):
        next_id = (self.current_topology_id % 15) + 1
        self.reset(topology_id=next_id)

    def replan_global_path(self):
        """Chạy A* để cập nhật Global Path từ vị trí hiện tại của Robot tới Goal."""
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
        """Cập nhật tọa độ Local Sub-goal trượt dọc theo đường A*."""
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

        # 1. Cập nhật FSM của các Semi-static Objects
        for door in self.semi_static_objects:
            door.update(self.dt, robot_pos=self.robot.position)
        self.update_occupancy_grid()

        # 2. Cập nhật chuyển động của các Dynamic Objects
        for dyn in self.dynamic_objects:
            dyn.update(self.dt, self.static_objects, self.width, self.height)

        # 3. Cập nhật chuyển động của Con người & Nhóm
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

        # 4. Cập nhật vận tốc và vị trí dự kiến của Robot
        if action is not None:
            self.robot.set_discrete_action(action)

        next_x, next_y, next_theta = self.robot.compute_next_pose(self.dt)

        # 5. Kiểm tra va chạm
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

        if self.robot.has_reached_goal():
            self.is_goal_reached = True
            self.robot.set_discrete_action(RobotAction.STOP)

        # 6. Định kỳ lập lại đường đi A* và cập nhật Sliding Local Sub-goal
        classify_all_humans_context(self.humans, self.human_groups, self.robot)
        if self.step_count % self.replan_interval == 0:
            self.replan_global_path()
        self._update_subgoal()
        self._update_perception()
        return self.get_info()

    def get_info(self) -> dict:
        return {
            "topology": TOPOLOGY_NAMES.get(
                self.current_topology_id, str(self.current_topology_id)
            ),
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