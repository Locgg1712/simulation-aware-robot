# Phase 5: Tính toán chi tiết từng thành phần Reward
# rl/reward_calculator.py
import math
from environment.world import World
from objects.robot import RobotAction
from objects.semi_static_object import SemiStaticState
from human.human_agent import SocialContext


class RewardCalculator:
    """
    Tính toán hàm phần thưởng đa mục tiêu tại mỗi bước thời gian t (Mục 9.3):
        R_t = R_terminal + R_progress + R_time + R_social + R_context
    """

    def __init__(self, reward_cfg: dict | None = None):
        cfg = reward_cfg or {}
        self.goal_reward: float = float(cfg.get("goal_reward", 100.0))
        self.collision_penalty: float = float(cfg.get("collision_penalty", -100.0))
        self.progress_weight: float = float(cfg.get("progress_weight", 2.5))
        self.time_penalty: float = float(cfg.get("time_penalty", -0.05))
        self.smart_wait_bonus: float = float(cfg.get("smart_wait_bonus", 0.2))
        self.use_social_reward: bool = bool(cfg.get("use_social_reward", True))

    def compute(
        self,
        world: World,
        action: int | RobotAction | None,
        prev_goal_dist: float,
        prev_subgoal_dist: float,
    ) -> tuple[float, dict]:
        """
        Trả về:
        - total_reward (float): Tổng phần thưởng ở bước hiện tại.
        - breakdown (dict): Chi tiết từng hạng mục thưởng/phạt để hiển thị Debug và ghi log.
        """
        robot = world.robot
        if robot is None:
            return 0.0, {}

        # 1. Terminal Reward (Chạm đích +100.0 hoặc Va chạm -100.0)
        r_terminal = 0.0
        if world.is_collision:
            r_terminal = self.collision_penalty
        elif world.is_goal_reached:
            r_terminal = self.goal_reward

        # 2. Progress Reward: w_p * (d_{t-1} - d_t)
        # Kết hợp độ tiến gần tới Local Sub-goal và Global Goal để tránh nhảy bước khi Sub-goal trượt
        curr_goal_dist = robot.distance_to_goal()
        curr_subgoal_dist = world.subgoal_info["dist_to_subgoal"]
        delta_goal = prev_goal_dist - curr_goal_dist
        delta_subgoal = prev_subgoal_dist - curr_subgoal_dist

        # Khi Sub-goal trượt dọc đường A*, delta_subgoal có thể âm nhẹ dù robot đang tiến về Goal;
        # lấy trung bình có trọng số với delta_goal và giới hạn biên theo vận tốc tối đa
        max_step_dist = robot.v_max * world.dt * 1.2
        clamped_delta_sg = max(-max_step_dist, min(max_step_dist, delta_subgoal))
        clamped_delta_g = max(-max_step_dist, min(max_step_dist, delta_goal))
        effective_progress = 0.6 * clamped_delta_sg + 0.4 * clamped_delta_g
        r_progress = self.progress_weight * effective_progress

        # 3. Time Penalty (-0.05 mỗi bước dt)
        r_time = self.time_penalty

        # 4. Social Space Penalty & Group Splitting Penalty
        r_social = 0.0
        r_group = 0.0
        if self.use_social_reward:
            soc = world.social_status
            r_social = float(soc.get("social_penalty", 0.0))
            r_group = float(soc.get("group_penalty", 0.0))

        # 5. Context Behavior Reward (Smart Wait Bonus: +0.2 / bước)
        # Khuyến khích chọn WAIT hoặc SLOW_DOWN khi có người đang CROSSING hoặc cửa đang OPENING trước mặt
        r_context = 0.0
        if self.use_social_reward and action is not None:
            try:
                act_enum = RobotAction(int(action))
            except ValueError:
                act_enum = None

            if act_enum in (RobotAction.WAIT, RobotAction.SLOW_DOWN, RobotAction.STOP):
                if self._has_valid_wait_context(world):
                    r_context = self.smart_wait_bonus

        total_reward = (
            r_terminal + r_progress + r_time + r_social + r_group + r_context
        )

        breakdown = {
            "r_total": round(float(total_reward), 3),
            "r_terminal": round(float(r_terminal), 2),
            "r_progress": round(float(r_progress), 3),
            "r_time": round(float(r_time), 3),
            "r_social": round(float(r_social), 3),
            "r_group": round(float(r_group), 2),
            "r_context": round(float(r_context), 2),
        }
        return float(total_reward), breakdown

    @staticmethod
    def _has_valid_wait_context(world: World) -> bool:
        """
        Kiểm tra xem phía trước mặt Robot có thực sự tồn tại tình huống cần nhường đường / chờ đợi:
        1. Cửa bán tĩnh đang ở trạng thái OPENING hoặc CLOSED trong bán kính 2.2m phía trước.
        2. Con người mang ngữ cảnh CROSSING hoặc APPROACHING trong bán kính 3.8m phía trước.
        """
        robot = world.robot
        if robot is None:
            return False

        for door in world.local_perception.get("semi_static", []):
            if door.state in (SemiStaticState.OPENING, SemiStaticState.CLOSED):
                dist = math.hypot(door.x - robot.x, door.y - robot.y)
                ang = math.atan2(door.y - robot.y, door.x - robot.x) - robot.theta
                ang = math.atan2(math.sin(ang), math.cos(ang))
                if dist < 2.2 and abs(ang) < math.radians(60.0):
                    return True

        for h in world.local_perception.get("humans", []):
            if h.social_context in (SocialContext.CROSSING, SocialContext.APPROACHING):
                dist = math.hypot(h.x - robot.x, h.y - robot.y)
                ang = math.atan2(h.y - robot.y, h.x - robot.x) - robot.theta
                ang = math.atan2(math.sin(ang), math.cos(ang))
                if dist < 3.8 and abs(ang) < math.radians(65.0):
                    return True

        return False