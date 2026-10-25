# Phase 4: Baseline 1 & 2 (A* + Collision Avoidance / Social Rules + Kinematic Lookahead Filter)
# behavior/rule_based_agent.py
import math
from environment.physics import check_circle_circle_collision, check_circle_rect_collision, check_robot_static_collision
from objects.robot import RobotAction
from objects.semi_static_object import SemiStaticState
from human.human_agent import SocialContext


class RuleBasedAgent:
    """
    Cài đặt 2 phương pháp Baseline truyền thống theo Mục 12 (Phase 4 & Phase 7):
    - Baseline 1 (mode='basic') : A* + Basic Collision Avoidance (chỉ tránh va chạm vật lý).
    - Baseline 2 (mode='social'): A* + Handcrafted Social Rules (dừng chờ khi có người CROSSING,
      giảm tốc/nhường đường khi APPROACHING, chờ cửa OPENING/CLOSING, đi vòng qua O-Space,
      và kiểm tra an toàn động học 2 bước trước khi thực thi).
    """

    def __init__(self, mode: str = "basic"):
        assert mode in ("basic", "social"), "mode phải là 'basic' hoặc 'social'"
        self.mode = mode

    def _action_velocities(self, robot, action: RobotAction) -> tuple[float, float]:
        if action == RobotAction.FORWARD:
            return robot.v_max, 0.0
        if action == RobotAction.TURN_LEFT:
            return 0.5 * robot.v_max, +robot.omega_max
        if action == RobotAction.TURN_RIGHT:
            return 0.5 * robot.v_max, -robot.omega_max
        if action == RobotAction.SLOW_DOWN:
            return 0.3 * robot.v_max, 0.0
        return 0.0, 0.0

    def _simulate_pose(
        self, x: float, y: float, theta: float, v: float, omega: float, dt: float, steps: int = 1
    ) -> list[tuple[float, float, float]]:
        poses: list[tuple[float, float, float]] = []
        cx, cy, cth = x, y, theta
        for _ in range(steps):
            cx = cx + v * math.cos(cth) * dt
            cy = cy + v * math.sin(cth) * dt
            cth = math.atan2(math.sin(cth + omega * dt), math.cos(cth + omega * dt))
            poses.append((cx, cy, cth))
        return poses

    def _is_action_safe(
        self, world, action: RobotAction, horizon_steps: int = 3, margin: float = 0.05
    ) -> bool:
        """Kiểm tra động học ngắn hạn (1..horizon_steps bước dt) xem hành động `action` có gây va chạm không."""
        robot = world.robot
        if robot is None:
            return False
        v, omega = self._action_velocities(robot, action)
        dt = world.dt
        eff_r = robot.radius + margin
        poses = self._simulate_pose(robot.x, robot.y, robot.theta, v, omega, dt, steps=horizon_steps)

        for step_idx, (nx, ny, _) in enumerate(poses, start=1):
            t_ahead = step_idx * dt
            hit_static, _ = check_robot_static_collision(
                nx, ny, eff_r, world.static_objects, world.width, world.height
            )
            if hit_static:
                return False

            for door in world.semi_static_objects:
                almost_closing = (
                    door.state == SemiStaticState.OPEN
                    and (door.open_duration - door.timer) < 0.8
                )
                if not door.passable or almost_closing:
                    rx, ry, rw, rh = door.bbox
                    if check_circle_rect_collision(nx, ny, eff_r, rx, ry, rw, rh):
                        return False

            for dyn in world.dynamic_objects:
                dx_p = dyn.x + dyn.vx * t_ahead
                dy_p = dyn.y + dyn.vy * t_ahead
                if check_circle_circle_collision(nx, ny, eff_r, dx_p, dy_p, dyn.radius):
                    return False

            for h in world.humans:
                if h.x < 0.0 or h.y < 0.0:
                    continue
                hx_p = h.x + h.vx * t_ahead
                hy_p = h.y + h.vy * t_ahead
                if check_circle_circle_collision(nx, ny, eff_r, hx_p, hy_p, h.radius):
                    return False

        return True

    def _pick_safe_fallback(self, world, preferred: RobotAction) -> RobotAction:
        if self._is_action_safe(world, preferred, horizon_steps=3, margin=0.05):
            return preferred
        if self._is_action_safe(world, preferred, horizon_steps=1, margin=0.01):
            # Nếu bước 1 hoàn toàn an toàn nhưng bước 2-3 hơi sát, thử giảm tốc hoặc rẽ
            robot = world.robot
            angle_err = world.subgoal_info["angle_to_subgoal"]
            turn_order = (
                [RobotAction.TURN_LEFT, RobotAction.TURN_RIGHT]
                if angle_err >= 0.0
                else [RobotAction.TURN_RIGHT, RobotAction.TURN_LEFT]
            )
            for cand in [*turn_order, RobotAction.SLOW_DOWN, preferred, RobotAction.WAIT]:
                if self._is_action_safe(world, cand, horizon_steps=3, margin=0.03):
                    return cand

        robot = world.robot
        angle_err = world.subgoal_info["angle_to_subgoal"]
        turn_order = (
            [RobotAction.TURN_LEFT, RobotAction.TURN_RIGHT]
            if angle_err >= 0.0
            else [RobotAction.TURN_RIGHT, RobotAction.TURN_LEFT]
        )
        candidates = [*turn_order, RobotAction.SLOW_DOWN, RobotAction.FORWARD, RobotAction.WAIT, RobotAction.STOP]
        for margin in (0.04, 0.01, 0.0):
            for h_steps in (2, 1):
                for cand in candidates:
                    if self._is_action_safe(world, cand, horizon_steps=h_steps, margin=margin):
                        return cand
        return RobotAction.STOP

    def select_action(self, world) -> RobotAction:
        """
        Chọn 1 trong 6 hành động rời rạc (FORWARD, TURN_LEFT, TURN_RIGHT, SLOW_DOWN, STOP, WAIT)
        dựa trên trạng thái hiện tại của `world`.
        """
        robot = world.robot
        if robot is None or world.is_collision or world.is_goal_reached:
            return RobotAction.STOP

        # ----------------------------------------------------------------------
        # 1. XỬ LÝ CỬA BÁN TĨNH (SEMI-STATIC DOOR) PHÍA TRƯỚC MẶT
        # ----------------------------------------------------------------------
        for door in world.local_perception.get("semi_static", []):
            dist_door = self._distance_to_rect(robot.x, robot.y, *door.bbox)
            ang_door = self._relative_angle(robot.x, robot.y, robot.theta, door.x, door.y)
            about_to_close = (
                door.state == SemiStaticState.OPEN
                and (door.open_duration - door.timer) < 1.1
                and dist_door > 0.45
            )
            if (not door.passable or about_to_close) and dist_door < 1.35 and abs(ang_door) < math.radians(60.0):
                return self._pick_safe_fallback(world, RobotAction.WAIT)

        # ----------------------------------------------------------------------
        # 2. LUẬT XÃ HỘI CỨNG (CHỈ ÁP DỤNG CHO BASELINE 2: mode == 'social')
        # ----------------------------------------------------------------------
        if self.mode == "social":
            for h in world.local_perception.get("humans", []):
                if h.x < 0.0 or h.y < 0.0:
                    continue
                dist_h = math.hypot(h.x - robot.x, h.y - robot.y)
                rel_ang = self._relative_angle(robot.x, robot.y, robot.theta, h.x, h.y)

                # Luật 1: Nếu có người đang CROSSING (cắt ngang mũi robot) trong bán kính 3.2m phía trước
                if (
                    h.social_context == SocialContext.CROSSING
                    and dist_h < 3.2
                    and abs(rel_ang) < math.radians(60.0)
                ):
                    if dist_h < 2.1:
                        return self._pick_safe_fallback(world, RobotAction.WAIT)
                    return self._pick_safe_fallback(world, RobotAction.SLOW_DOWN)

                # Luật 2: Nếu có người đang APPROACHING (đi ngược chiều về phía robot)
                d_perp_h = dist_h * abs(math.sin(rel_ang))
                if (
                    h.social_context == SocialContext.APPROACHING
                    and dist_h < 2.6
                    and abs(rel_ang) < math.radians(40.0)
                    and d_perp_h < (robot.radius + h.radius + 0.28)
                ):
                    turn_act = (
                        RobotAction.TURN_RIGHT
                        if rel_ang >= -0.15
                        else RobotAction.TURN_LEFT
                    )
                    return self._pick_safe_fallback(world, turn_act)

                # Luật 3: Giữ khoảng cách với người đứng gần phía trước mũi (chỉ rẽ khi hướng mũi thực sự vướng)
                if (
                    dist_h < 1.25
                    and abs(rel_ang) < math.radians(42.0)
                    and d_perp_h < (robot.radius + h.radius + 0.16)
                ):
                    turn_act = (
                        RobotAction.TURN_RIGHT
                        if rel_ang >= 0.0
                        else RobotAction.TURN_LEFT
                    )
                    return self._pick_safe_fallback(world, turn_act)

            # 2b. Luật tránh đi xuyên qua vùng O-Space của nhóm INTERACTING
            for grp in world.human_groups:
                dist_grp = math.hypot(grp.center_x - robot.x, grp.center_y - robot.y)
                rel_ang_grp = self._relative_angle(
                    robot.x, robot.y, robot.theta, grp.center_x, grp.center_y
                )
                d_perp_grp = dist_grp * abs(math.sin(rel_ang_grp))
                if (
                    dist_grp < grp.radius + robot.radius + 0.40
                    and abs(rel_ang_grp) < math.radians(45.0)
                    and d_perp_grp < (grp.radius + robot.radius + 0.15)
                ):
                    turn_act = (
                        RobotAction.TURN_RIGHT
                        if rel_ang_grp >= 0.0
                        else RobotAction.TURN_LEFT
                    )
                    return self._pick_safe_fallback(world, turn_act)

        # ----------------------------------------------------------------------
        # 3. TRÁNH VA CHẠM VẬT LÝ CỤC BỘ DỰA TRÊN TIA LIDAR & VẬT THỂ ĐỘNG
        # ----------------------------------------------------------------------
        moving_entities = list(world.local_perception.get("dynamic", [])) + [
            h for h in world.local_perception.get("humans", []) if h.x >= 0.0 and h.y >= 0.0
        ]
        for ent in moving_entities:
            raw_d = math.hypot(ent.x - robot.x, ent.y - robot.y)
            dist_e = raw_d - (robot.radius + ent.radius)
            rel_ang = self._relative_angle(robot.x, robot.y, robot.theta, ent.x, ent.y)
            d_perp_e = raw_d * abs(math.sin(rel_ang))
            if dist_e < 0.38 and abs(rel_ang) < math.radians(45.0) and d_perp_e < (robot.radius + ent.radius + 0.12):
                turn_act = (
                    RobotAction.TURN_RIGHT if rel_ang >= 0.0 else RobotAction.TURN_LEFT
                )
                if self._is_action_safe(world, turn_act, horizon_steps=2, margin=0.02):
                    return turn_act
                return self._pick_safe_fallback(world, RobotAction.STOP)
            if dist_e < 0.78 and abs(rel_ang) < math.radians(42.0) and d_perp_e < (robot.radius + ent.radius + 0.14):
                turn_act = (
                    RobotAction.TURN_RIGHT if rel_ang >= 0.0 else RobotAction.TURN_LEFT
                )
                return self._pick_safe_fallback(world, turn_act)

        # Kiểm tra các tia LiDAR phía trước mũi Robot (tia 0, 1, 2, 14, 15 trong 16 tia)
        if len(world.lidar_distances) >= 16:
            front_dist = world.lidar_distances[0]
            front_left = min(world.lidar_distances[1], world.lidar_distances[2])
            front_right = min(world.lidar_distances[15], world.lidar_distances[14])
            min_front = min(front_dist, front_left * 1.05, front_right * 1.05)

            if min_front < robot.radius + 0.34:
                turn_act = (
                    RobotAction.TURN_LEFT
                    if front_left > front_right
                    else RobotAction.TURN_RIGHT
                )
                return self._pick_safe_fallback(world, turn_act)

        # ----------------------------------------------------------------------
        # 4. ĐIỀU HƯỚNG BÁM THEO ĐIỂM DẪN ĐƯỜNG CỤC BỘ (LOCAL SUB-GOAL)
        # ----------------------------------------------------------------------
        angle_err = world.subgoal_info["angle_to_subgoal"]
        dist_goal = robot.distance_to_goal()

        if abs(angle_err) > 0.28:
            turn_act = (
                RobotAction.TURN_LEFT
                if angle_err > 0.0
                else RobotAction.TURN_RIGHT
            )
            return self._pick_safe_fallback(world, turn_act)

        if dist_goal < 0.90 and abs(angle_err) > 0.16:
            return self._pick_safe_fallback(world, RobotAction.SLOW_DOWN)

        return self._pick_safe_fallback(world, RobotAction.FORWARD)

    @staticmethod
    def _relative_angle(
        rx: float, ry: float, r_theta: float, tx: float, ty: float
    ) -> float:
        ang = math.atan2(ty - ry, tx - rx) - r_theta
        return math.atan2(math.sin(ang), math.cos(ang))

    @staticmethod
    def _distance_to_rect(
        px: float, py: float, rx: float, ry: float, rw: float, rh: float
    ) -> float:
        cx = max(rx, min(px, rx + rw))
        cy = max(ry, min(py, ry + rh))
        return math.hypot(px - cx, py - cy)