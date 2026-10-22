# Phase 4: Baseline 1 & 2 (A* + Collision Avoidance / Social Rules)
# behavior/rule_based_agent.py
import math
from objects.robot import RobotAction
from objects.semi_static_object import SemiStaticState
from human.human_agent import SocialContext


class RuleBasedAgent:
    """
    Cài đặt 2 phương pháp Baseline truyền thống theo Mục 12 (Phase 4 & Phase 7):
    - Baseline 1 (mode='basic') : A* + Basic Collision Avoidance (chỉ tránh va chạm vật lý).
    - Baseline 2 (mode='social'): A* + Handcrafted Social Rules (dừng chờ khi có người CROSSING,
      giảm tốc/nhường đường khi APPROACHING, chờ cửa OPENING, và đi vòng qua O-Space).
    """

    def __init__(self, mode: str = "basic"):
        assert mode in ("basic", "social"), "mode phải là 'basic' hoặc 'social'"
        self.mode = mode

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
            if not door.passable:
                dist_door = self._distance_to_rect(robot.x, robot.y, *door.bbox)
                ang_door = self._relative_angle(robot.x, robot.y, robot.theta, door.x, door.y)
                if dist_door < 1.25 and abs(ang_door) < math.radians(55.0):
                    # Đứng chờ có chủ đích (WAIT) trước cửa đang đóng / đang mở
                    return RobotAction.WAIT

        # ----------------------------------------------------------------------
        # 2. LUẬT XÃ HỘI CỨNG (CHỈ ÁP DỤNG CHO BASELINE 2: mode == 'social')
        # ----------------------------------------------------------------------
        if self.mode == "social":
            # 2a. Kiểm tra con người trong vùng cảm biến
            for h in world.local_perception.get("humans", []):
                dist_h = math.hypot(h.x - robot.x, h.y - robot.y)
                rel_ang = self._relative_angle(robot.x, robot.y, robot.theta, h.x, h.y)

                # Luật 1: Nếu có người đang CROSSING (cắt ngang mũi robot) trong bán kính 3.6m phía trước
                if (
                    h.social_context == SocialContext.CROSSING
                    and dist_h < 3.6
                    and abs(rel_ang) < math.radians(65.0)
                ):
                    if dist_h < 2.4:
                        return RobotAction.WAIT
                    return RobotAction.SLOW_DOWN

                # Luật 2: Nếu có người đang APPROACHING (đi ngược chiều về phía robot)
                if (
                    h.social_context == SocialContext.APPROACHING
                    and dist_h < 3.2
                    and abs(rel_ang) < math.radians(45.0)
                ):
                    # Chủ động rẽ phải nhường hành lang hoặc giảm tốc
                    return (
                        RobotAction.TURN_RIGHT
                        if rel_ang >= -0.15
                        else RobotAction.TURN_LEFT
                    )

                # Luật 3: Giữ khoảng cách với người đang chạy (RUNNING) hoặc đứng gần
                if dist_h < 1.65 and abs(rel_ang) < math.radians(50.0):
                    return (
                        RobotAction.TURN_RIGHT
                        if rel_ang >= 0.0
                        else RobotAction.TURN_LEFT
                    )

            # 2b. Luật tránh đi xuyên qua vùng O-Space của nhóm INTERACTING
            for grp in world.human_groups:
                dist_grp = math.hypot(grp.center_x - robot.x, grp.center_y - robot.y)
                rel_ang_grp = self._relative_angle(
                    robot.x, robot.y, robot.theta, grp.center_x, grp.center_y
                )
                if (
                    dist_grp < grp.radius + robot.radius + 0.55
                    and abs(rel_ang_grp) < math.radians(60.0)
                ):
                    return (
                        RobotAction.TURN_RIGHT
                        if rel_ang_grp >= 0.0
                        else RobotAction.TURN_LEFT
                    )

        # ----------------------------------------------------------------------
        # 3. TRÁNH VA CHẠM VẬT LÝ CỤC BỘ DỰA TRÊN TIA LIDAR & VẬT THỂ ĐỘNG
        # ----------------------------------------------------------------------
        # Kiểm tra vật thể động / con người ở quá sát phía trước (< 1.1m)
        moving_entities = list(world.local_perception.get("dynamic", [])) + list(
            world.local_perception.get("humans", [])
        )
        for ent in moving_entities:
            dist_e = math.hypot(ent.x - robot.x, ent.y - robot.y) - (
                robot.radius + ent.radius
            )
            rel_ang = self._relative_angle(robot.x, robot.y, robot.theta, ent.x, ent.y)
            if dist_e < 0.45 and abs(rel_ang) < math.radians(45.0):
                return RobotAction.STOP
            if dist_e < 0.95 and abs(rel_ang) < math.radians(50.0):
                return (
                    RobotAction.TURN_RIGHT
                    if rel_ang >= 0.0
                    else RobotAction.TURN_LEFT
                )

        # Kiểm tra các tia LiDAR phía trước mũi Robot (tia 0, 1, 15 trong 16 tia)
        if len(world.lidar_distances) >= 16:
            front_dist = world.lidar_distances[0]
            front_left = min(world.lidar_distances[1], world.lidar_distances[2])
            front_right = min(world.lidar_distances[15], world.lidar_distances[14])
            min_front = min(front_dist, front_left * 1.05, front_right * 1.05)

            if min_front < robot.radius + 0.32:
                # Chướng ngại vật tĩnh ngay sát mũi -> Rẽ về phía rộng hơn
                if front_left > front_right:
                    return RobotAction.TURN_LEFT
                return RobotAction.TURN_RIGHT

        # ----------------------------------------------------------------------
        # 4. ĐIỀU HƯỚNG BÁM THEO ĐIỂM DẪN ĐƯỜNG CỤC BỘ (LOCAL SUB-GOAL)
        # ----------------------------------------------------------------------
        angle_err = world.subgoal_info["angle_to_subgoal"]
        dist_goal = robot.distance_to_goal()

        if abs(angle_err) > 0.32:
            return (
                RobotAction.TURN_LEFT
                if angle_err > 0.0
                else RobotAction.TURN_RIGHT
            )

        if dist_goal < 0.90 and abs(angle_err) > 0.18:
            return RobotAction.SLOW_DOWN

        return RobotAction.FORWARD

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