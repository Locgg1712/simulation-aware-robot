# Phase 5 & Mục 12.2: Tính toán chi tiết từng thành phần Hàm Phần Thưởng Mở Rộng FarmBot Town
# rl/reward_calculator.py
import math
from environment.world import World
from objects.robot import RobotAction
from objects.semi_static_object import SemiStaticState
from human.human_agent import SocialContext


class RewardCalculator:
    """
    Tính toán hàm phần thưởng mở rộng đa mục tiêu tại mỗi bước thời gian t (Mục 6.2 & Mục 12.2):
        R_t^ext = R_terminal + R_progress + R_time + R_social + R_group + R_context + R_fan + R_elder_safe + R_event
    """

    def __init__(self, reward_cfg: dict | None = None):
        cfg = reward_cfg or {}
        self.goal_reward: float = float(cfg.get("goal_reward", 100.0))
        self.collision_penalty: float = float(cfg.get("collision_penalty", -100.0))
        self.progress_weight: float = float(cfg.get("progress_weight", 3.5))
        self.time_penalty: float = float(cfg.get("time_penalty", -0.05))
        self.smart_wait_bonus: float = float(cfg.get("smart_wait_bonus", 0.25))
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
        - total_reward (float): Tổng phần thưởng mở rộng ở bước hiện tại.
        - breakdown (dict): Chi tiết từng hạng mục thưởng/phạt để hiển thị Debug và ghi log.
        """
        robot = world.robot
        if robot is None:
            return 0.0, {}

        # 1. Terminal Reward (Chạm đích +100.0 hoặc Va chạm -100.0 / Cán tốc độ cao)
        r_terminal = 0.0
        if world.is_collision:
            r_terminal = self.collision_penalty
            if getattr(world, "safety_hearts", 3) <= 0:
                r_terminal -= 50.0
        elif world.is_goal_reached:
            r_terminal = self.goal_reward

        # 2. Progress & Heading Shaping: w_p * (d_{t-1} - d_t) + thưởng bám hướng Sub-goal
        curr_goal_dist = robot.distance_to_goal()
        curr_subgoal_dist = world.subgoal_info["dist_to_subgoal"]
        delta_goal = prev_goal_dist - curr_goal_dist
        delta_subgoal = prev_subgoal_dist - curr_subgoal_dist

        max_step_dist = robot.v_max * world.dt * 1.2
        clamped_delta_sg = max(-max_step_dist, min(max_step_dist, delta_subgoal))
        clamped_delta_g = max(-max_step_dist, min(max_step_dist, delta_goal))
        effective_progress = 0.65 * clamped_delta_sg + 0.35 * clamped_delta_g

        ang_err = abs(world.subgoal_info["angle_to_subgoal"])
        heading_bonus = 0.0
        if robot.v > 0.1 and ang_err < 0.45:
            heading_bonus = 0.06 * math.cos(ang_err) * (robot.v / max(1e-5, robot.v_max))

        r_progress = self.progress_weight * effective_progress + heading_bonus

        # 3. Time Penalty (-0.05 mỗi bước dt) + phạt nhẹ nếu đứng yên vô cớ
        r_time = self.time_penalty
        has_wait_ctx = self._has_valid_wait_context(world)
        if robot.v < 0.02 and not has_wait_ctx and not world.is_goal_reached:
            r_time -= 0.08

        # 4. Social Space Penalty & Group Splitting Penalty
        r_social = 0.0
        r_group = 0.0
        r_context = 0.0
        r_hri_ext = 0.0

        if self.use_social_reward:
            soc = world.social_status
            r_social = float(soc.get("social_penalty", 0.0))
            r_group = float(soc.get("group_penalty", 0.0))

            act_enum = None
            if action is not None:
                try:
                    act_enum = RobotAction(int(action))
                except ValueError:
                    act_enum = None

            if act_enum in (RobotAction.WAIT, RobotAction.SLOW_DOWN, RobotAction.STOP):
                if has_wait_ctx:
                    r_context = self.smart_wait_bonus

            # 5. Thành phần mở rộng FarmBot Town: Vùng Quạt HRI, Radar Độ Tuổi & Sự Kiện Động
            hri = getattr(world, "hri_status", {})
            if hri.get("rear_approach", False):
                r_hri_ext -= 0.65
            elif (
                hri.get("d_npc", 5.0) <= 1.85
                and abs(hri.get("delta_alpha_npc", math.pi)) <= math.radians(35.0)
                and robot.v <= 0.55
            ):
                r_hri_ext += 0.12 * math.cos(hri.get("delta_alpha_npc", 0.0))

            r_hri_ext += float(hri.get("elder_speed_violation", 0.0)) * 0.35
            if hri.get("elder_smart_yield", False):
                r_hri_ext += 0.30

            # Thưởng thích ứng khi đi chậm an toàn dưới trời mưa hoặc gần vùng sự kiện nguy hiểm
            ev = getattr(world, "active_event", None)
            if (
                ev is not None
                and float(ev.get("is_ospace_hazard", 0.0)) > 0.5
                and math.hypot(robot.x - float(ev["x"]), robot.y - float(ev["y"])) < 2.5
                and not soc.get("group_splitting", False)
                and robot.v > 0.1
            ):
                r_hri_ext += 0.10

        total_reward = (
            r_terminal
            + r_progress
            + r_time
            + r_social
            + r_group
            + r_context
            + r_hri_ext
        )

        breakdown = {
            "r_total": round(float(total_reward), 3),
            "r_terminal": round(float(r_terminal), 2),
            "r_progress": round(float(r_progress), 3),
            "r_time": round(float(r_time), 3),
            "r_social": round(float(r_social), 3),
            "r_group": round(float(r_group), 2),
            "r_context": round(float(r_context + r_hri_ext), 3),
        }
        return float(total_reward), breakdown

    @staticmethod
    def _has_valid_wait_context(world: World) -> bool:
        """
        Kiểm tra xem phía trước mặt Robot có thực sự tồn tại tình huống cần nhường đường / chờ đợi:
        1. Cửa bán tĩnh đang ở trạng thái OPENING hoặc CLOSED trong bán kính 2.2m phía trước.
        2. Con người mang ngữ cảnh CROSSING hoặc APPROACHING trong bán kính 3.8m phía trước.
        3. Đang ở trong bán kính an toàn của người cao tuổi / trẻ nhỏ (elder / child).
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
            dist = math.hypot(h.x - robot.x, h.y - robot.y)
            if getattr(h, "age_group", "adult") in ("elder", "child") and dist <= getattr(
                h, "safety_radius", 1.65
            ):
                return True
            if h.social_context in (SocialContext.CROSSING, SocialContext.APPROACHING):
                ang = math.atan2(h.y - robot.y, h.x - robot.x) - robot.theta
                ang = math.atan2(math.sin(ang), math.cos(ang))
                if dist < 3.8 and abs(ang) < math.radians(65.0):
                    return True

        return False
