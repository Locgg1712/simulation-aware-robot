# Phase 5 & Mục 12.2: Tính toán chi tiết từng thành phần Hàm Phần Thưởng Mở Rộng FarmBot Town (128 Chiều)
# rl/reward_calculator.py
import math
from environment.world import World
from objects.robot import RobotAction
from objects.semi_static_object import SemiStaticState
from human.human_agent import SocialContext


class RewardCalculator:
    """
    Tính toán hàm phần thưởng mở rộng đa mục tiêu tại mỗi bước thời gian t (Mục 6.2 & Mục 12.2):
        R_t^ext = R_terminal + R_progress + R_time + R_social + R_group + R_context
                  + R_fan + R_elder_safe + R_knockdown + R_run_over + R_event
    """

    def __init__(self, reward_cfg: dict | None = None):
        cfg = reward_cfg or {}
        self.goal_reward: float = float(cfg.get("goal_reward", 100.0))
        self.collision_penalty: float = float(cfg.get("collision_penalty", -100.0))
        self.progress_weight: float = float(cfg.get("progress_weight", 3.5))
        self.time_penalty: float = float(cfg.get("time_penalty", -0.05))
        self.smart_wait_bonus: float = float(cfg.get("smart_wait_bonus", 0.25))
        self.fan_hri_bonus: float = float(cfg.get("fan_hri_bonus", 15.0))
        self.rear_approach_penalty: float = float(cfg.get("rear_approach_penalty", -3.0))
        self.elder_speed_weight: float = float(cfg.get("elder_speed_weight", -4.0))
        self.elder_slow_bonus: float = float(cfg.get("elder_slow_bonus", 1.0))
        self.event_bypass_bonus: float = float(cfg.get("event_bypass_bonus", 5.0))
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

        # 1. Terminal Reward & 4-Tier Safety Penalties (R_knockdown / R_run_over - Mục 12.2)
        r_terminal = 0.0
        r_knockdown = 0.0
        r_run_over = 0.0
        if world.is_collision:
            tier = int(getattr(world, "last_collision_tier", 1))
            if tier == 4:
                # Cấp 4: Cán qua người ở tốc độ cao (Lethal Run-Over -> -500.0)
                r_run_over = -500.0
                r_terminal = r_run_over
            elif tier == 3:
                # Cấp 3: Tái phạm đâm ngã mất hết 3 Tim (Multi-Hit -> -250.0)
                r_knockdown = -250.0
                r_terminal = r_knockdown
            elif tier == 2:
                # Cấp 2: Đâm ngã NPC lần 1 hoặc lần 2 (Knockdown -> -100.0)
                r_knockdown = -100.0
                r_terminal = r_knockdown
            else:
                r_terminal = self.collision_penalty
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

        # 4. Social Space, Group Splitting & Mở rộng FarmBot Town (Mục 12.2)
        r_social = 0.0
        r_group = 0.0
        r_context = 0.0
        r_fan = 0.0
        r_elder_safe = 0.0
        r_event = 0.0

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

            # 5a. Phần thưởng Định hướng Vùng Quạt HRI (R_fan - Mục 12.2.1):
            #     +15.0 khi thỏa mãn trọn vẹn 4 điều kiện vùng quạt (nhận 1 lần/episode tránh farm điểm),
            #     +2.0 * cos(delta_alpha_npc) * dt khi tiếp cận từ phía trước mặt,
            #     -3.0 khi áp sát NPC từ sau lưng (delta_alpha_npc > 110 deg, d < 1.0m).
            hri = getattr(world, "hri_status", {})
            d_npc = float(hri.get("d_npc", 5.0))
            d_alpha_npc = float(hri.get("delta_alpha_npc", 0.0))

            if hri.get("in_fan_ok", False) and not getattr(world, "fan_reward_claimed", False):
                r_fan += self.fan_hri_bonus
                world.fan_reward_claimed = True
            elif hri.get("rear_approach", False):
                r_fan += self.rear_approach_penalty * world.dt
            elif (
                d_npc <= 1.85
                and abs(d_alpha_npc) <= math.radians(35.0)
                and 0.05 <= robot.v <= 0.60
                and delta_subgoal > 0.0
            ):
                r_fan += (2.0 * math.cos(d_alpha_npc)) * world.dt

            # 5b. Thưởng/Phạt An toàn Đối tượng Nhạy cảm (R_elder_safe - Mục 12.2.2):
            #     -4.0 * (v/v_max) * ((R_safe - d)/R_safe) nếu v > 0.30 m/s trong vùng nhạy cảm,
            #     +1.0 * dt nếu chủ động SLOW_DOWN khi đi qua vùng nhạy cảm của người già / trẻ nhỏ.
            age_radar = hri.get("nearest_age_radar", [1.0, 0.0, 0.0, 0.625])
            is_sensitive = len(age_radar) >= 3 and (age_radar[1] > 0.5 or age_radar[2] > 0.5)
            r_safe = float(age_radar[3]) * 2.0 if len(age_radar) >= 4 else 1.25
            if is_sensitive and d_npc <= r_safe:
                if robot.v > 0.30:
                    ratio = max(0.0, (r_safe - d_npc) / max(0.1, r_safe))
                    r_elder_safe += (
                        self.elder_speed_weight
                        * (robot.v / max(0.1, robot.v_max))
                        * ratio
                        * world.dt
                    )
                elif act_enum == RobotAction.SLOW_DOWN and delta_subgoal >= -0.01:
                    r_elder_safe += self.elder_slow_bonus * world.dt

            # 5c. Phần thưởng Thích ứng Sự kiện Ngẫu nhiên (R_event - Mục 12.2.5):
            #     +5.0 khi vòng tránh thành công cụm O-Space / sự kiện nguy hiểm mà không va chạm.
            ev = getattr(world, "active_event", None)
            if ev is not None:
                d_ev = math.hypot(robot.x - float(ev["x"]), robot.y - float(ev["y"]))
                if (
                    float(ev.get("is_ospace_hazard", 0.0)) > 0.5
                    and d_ev < 2.2
                    and not soc.get("group_splitting", False)
                    and not soc.get("ospace_intrusion", False)
                    and not getattr(world, "event_bypass_claimed", False)
                    and delta_goal > 0.01
                ):
                    r_event += self.event_bypass_bonus
                    world.event_bypass_claimed = True

        r_hri_ext = r_fan + r_elder_safe + r_event
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
            "r_fan": round(float(r_fan), 3),
            "r_elder_safe": round(float(r_elder_safe), 3),
            "r_event": round(float(r_event), 3),
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
