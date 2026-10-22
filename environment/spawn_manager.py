# environment/spawn_manager.py
from collections import deque
import math
import random
import numpy as np

from objects.static_object import StaticObject
from objects.semi_static_object import SemiStaticObject
from objects.dynamic_object import DynamicObject
from objects.robot import Robot
from human.human_agent import HumanAgent
from human.groups import HumanGroup, GroupType
from .physics import check_robot_static_collision


class SpawnManager:
    """
    Quản lý việc sinh tự động Robot, Goal, Dynamic Objects, Humans & Groups
    kèm kiểm tra 3 điều kiện (Collision Check, Safe Margin >= 2.0m, Path Feasibility).
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
        dyn_objects: list[DynamicObject] = []

        for idx in range(num_objects):
            radius = 0.35
            for _ in range(120):
                x = random.uniform(1.5, self.width - 1.5)
                y = random.uniform(1.5, self.height - 1.5)

                if math.hypot(x - robot.x, y - robot.y) < safe_margin:
                    continue
                if math.hypot(x - robot.goal_x, y - robot.goal_y) < 1.2:
                    continue
                if any(math.hypot(x - d.x, y - d.y) < d.radius + 0.6 for d in semi_static_objects):
                    continue

                collided, _ = check_robot_static_collision(
                    x, y, radius + 0.2, static_objects, self.width, self.height
                )
                if collided:
                    continue
                if any(math.hypot(x - o.x, y - o.y) < (radius + o.radius + 0.4) for o in dyn_objects):
                    continue

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
                break

        return dyn_objects

    def spawn_humans_and_groups(
        self,
        robot: Robot,
        static_objects: list[StaticObject],
        semi_static_objects: list[SemiStaticObject],
        dynamic_objects: list[DynamicObject],
        num_individual_humans: int = 3,
        num_interacting_groups: int = 1,
        num_walking_groups: int = 1,
        start_human_id: int = 200,
        safe_margin: float = 2.0,
    ) -> tuple[list[HumanAgent], list[HumanGroup]]:
        """
        Sinh đa dạng các thực thể Con người & Nhóm xã hội:
        1. Nhóm đứng nói chuyện (INTERACTING - tạo O-Space).
        2. Nhóm đi bộ cùng nhau (GROUP).
        3. Người đi bộ (WALKING) và người chạy (RUNNING).
        """
        humans: list[HumanAgent] = []
        groups: list[HumanGroup] = []
        next_hid = start_human_id
        next_gid = 1

        def is_spot_free(px: float, py: float, rad: float = 0.35) -> bool:
            if math.hypot(px - robot.x, py - robot.y) < safe_margin:
                return False
            if math.hypot(px - robot.goal_x, py - robot.goal_y) < 1.2:
                return False
            if any(math.hypot(px - d.x, py - d.y) < d.radius + 0.6 for d in semi_static_objects):
                return False
            collided, _ = check_robot_static_collision(
                px, py, rad + 0.15, static_objects, self.width, self.height
            )
            if collided:
                return False
            if any(math.hypot(px - o.x, py - o.y) < (rad + o.radius + 0.35) for o in dynamic_objects):
                return False
            if any(math.hypot(px - h.x, py - h.y) < (rad + h.radius + 0.35) for h in humans):
                return False
            return True

        # 1. Sinh nhóm đứng nói chuyện (INTERACTING Group: 2 - 3 người)
        for _ in range(num_interacting_groups):
            for _attempt in range(100):
                # Ưu tiên đặt gần khu vực trung tâm bản đồ để Robot có cơ hội gặp và học cách tránh O-Space
                cx = random.uniform(5.0, self.width - 5.0)
                cy = random.uniform(5.0, self.height - 5.0)
                if not is_spot_free(cx, cy, rad=1.1):
                    continue

                num_members = random.choice([2, 3])
                ring_r = 0.62
                base_ang = random.uniform(0.0, 2.0 * math.pi)
                candidate_members: list[HumanAgent] = []
                valid_group = True

                for m_idx in range(num_members):
                    ang = base_ang + (2.0 * math.pi * m_idx) / num_members
                    mx = cx + ring_r * math.cos(ang)
                    my = cy + ring_r * math.sin(ang)
                    if not is_spot_free(mx, my, rad=0.30):
                        valid_group = False
                        break
                    look_theta = math.atan2(cy - my, cx - mx)
                    candidate_members.append(
                        HumanAgent(
                            obj_id=next_hid + m_idx,
                            x=mx,
                            y=my,
                            theta=look_theta,
                            desired_speed=0.0,
                            radius=0.30,
                            waypoints=[],
                            group_id=next_gid,
                            is_interacting_member=True,
                            name=f"human_talk_{next_hid + m_idx}",
                        )
                    )

                if valid_group and len(candidate_members) >= 2:
                    humans.extend(candidate_members)
                    groups.append(
                        HumanGroup(
                            group_id=next_gid,
                            group_type=GroupType.INTERACTING_GROUP,
                            members=candidate_members,
                            margin=0.45,
                        )
                    )
                    next_hid += len(candidate_members)
                    next_gid += 1
                    break

        # 2. Sinh nhóm đi bộ cùng nhau (WALKING GROUP: 2 người đi song hành)
        for _ in range(num_walking_groups):
            for _attempt in range(100):
                cx = random.uniform(2.5, self.width - 2.5)
                cy = random.uniform(2.5, self.height - 2.5)
                if not is_spot_free(cx, cy, rad=0.9):
                    continue

                wp_end = self.sample_free_point(
                    (
                        max(2.0, min(self.width - 2.0, cx + random.uniform(-6.5, 6.5))),
                        max(2.0, min(self.height - 2.0, cy + random.uniform(-6.5, 6.5))),
                    ),
                    0.8,
                    static_objects,
                    jitter=2.5,
                )
                move_theta = math.atan2(wp_end[1] - cy, wp_end[0] - cx)
                perp_x = -math.sin(move_theta) * 0.42
                perp_y = math.cos(move_theta) * 0.42

                p1_pos = (cx + perp_x, cy + perp_y)
                p2_pos = (cx - perp_x, cy - perp_y)
                if not (is_spot_free(*p1_pos) and is_spot_free(*p2_pos)):
                    continue

                grp_speed = random.uniform(0.85, 1.15)
                h1 = HumanAgent(
                    obj_id=next_hid,
                    x=p1_pos[0],
                    y=p1_pos[1],
                    theta=move_theta,
                    desired_speed=grp_speed,
                    waypoints=[p1_pos, (wp_end[0] + perp_x, wp_end[1] + perp_y)],
                    group_id=next_gid,
                    name=f"human_grp_{next_hid}",
                )
                h2 = HumanAgent(
                    obj_id=next_hid + 1,
                    x=p2_pos[0],
                    y=p2_pos[1],
                    theta=move_theta,
                    desired_speed=grp_speed,
                    waypoints=[p2_pos, (wp_end[0] - perp_x, wp_end[1] - perp_y)],
                    group_id=next_gid,
                    name=f"human_grp_{next_hid + 1}",
                )
                humans.extend([h1, h2])
                groups.append(
                    HumanGroup(
                        group_id=next_gid,
                        group_type=GroupType.WALKING_GROUP,
                        members=[h1, h2],
                        margin=0.40,
                    )
                )
                next_hid += 2
                next_gid += 1
                break

        # 3. Sinh các cá nhân độc lập (WALKING hoặc RUNNING)
        for idx in range(num_individual_humans):
            # Ít nhất 1 người chạy nhanh (RUNNING: 2.0 - 2.5 m/s), còn lại đi bộ (WALKING: 0.9 - 1.35 m/s)
            is_runner = idx == 0
            desired_v = random.uniform(2.0, 2.5) if is_runner else random.uniform(0.9, 1.35)

            for _attempt in range(100):
                hx = random.uniform(1.8, self.width - 1.8)
                hy = random.uniform(1.8, self.height - 1.8)
                if not is_spot_free(hx, hy):
                    continue

                wp2 = self.sample_free_point(
                    (
                        max(1.8, min(self.width - 1.8, hx + random.uniform(-7.0, 7.0))),
                        max(1.8, min(self.height - 1.8, hy + random.uniform(-7.0, 7.0))),
                    ),
                    0.35,
                    static_objects,
                    jitter=2.5,
                )
                theta = math.atan2(wp2[1] - hy, wp2[0] - hx)
                humans.append(
                    HumanAgent(
                        obj_id=next_hid,
                        x=hx,
                        y=hy,
                        theta=theta,
                        desired_speed=desired_v,
                        waypoints=[(hx, hy), wp2],
                        group_id=None,
                        name=f"human_{'run' if is_runner else 'walk'}_{next_hid}",
                    )
                )
                next_hid += 1
                break

        return humans, groups