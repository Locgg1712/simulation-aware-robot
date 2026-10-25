# game/safety_hri.py
"""
Mô-đun HRI & An toàn Vật lý (Human-Robot Interaction & 4-Level Safety System):
1. Kiểm tra và vẽ Vùng Quạt Xanh Lá Trước Mặt NPC (Front Interaction Zone - Mục 3.2).
2. Xử lý 4 cấp độ va chạm & điều kiện thua (Safety & Die Rules - Mục 4):
   - Cấp 1: Đi/Đứng quá sát (d < 0.70m) -> NPC giật mình '!' bước lùi nhẹ (-5 điểm/giây).
   - Cấp 2: Đâm ngã (Bump / Knockdown) -> NPC ngã ngồi 3.0s hiện sao choáng, Robot bật lùi 0.4m khóa 1.0s (-100đ, -1 Mạng).
   - Cấp 3: Tái phạm đâm ngã đủ 3 lần (Mất hết 3 Trái Tim) -> Ngắt nguồn Robot, GAME OVER (-250đ).
   - Cấp 4: Cán thẳng qua người (Run Over ở tốc độ cao v >= 0.85*v_max góc < 20°, hoặc đi đè lên NPC đang ngã) -> INSTANT DIE (-500đ).
"""

from __future__ import annotations

import math
import pygame

from .constants import (
    HITBOX_TOUCH_M,
    INTERACT_MAX_M,
    INTERACT_MIN_M,
    INTERACT_NPC_FAN_DEG,
    INTERACT_ROBOT_FACE_DEG,
    INTERACT_STOP_SPEED_MPS,
    PENALTY_KNOCKDOWN,
    PENALTY_MULTI_HIT_DIE,
    PENALTY_PERSONAL_SPACE_PER_SEC,
    PENALTY_RUN_OVER_DIE,
    PERSONAL_SPACE_M,
    ROBOT_V_MAX_MPS,
    SCORE_SMART_YIELD,
    SCREEN_H,
    SCREEN_W,
    angle_diff_deg,
    m_to_px,
    px_to_m,
)
from .entities import RobotPlayer, VillagerNPC


def check_front_interaction(robot: RobotPlayer, npc: VillagerNPC) -> tuple[bool, dict]:
    """
    Kiểm tra đồng thời 4 điều kiện toán học của Vùng Quạt Trước Mặt NPC:
    1. Khoảng cách lịch sự: 0.75m <= d <= 1.45m
    2. Đứng đúng phía trước mặt NPC: |atan2(y_r - y_n, x_r - x_n) - theta_npc| <= 35°
    3. Hướng mặt Robot nhìn về NPC: |atan2(y_n - y_r, x_n - x_r) - theta_robot| <= 45°
    4. Dừng hẳn trước khi giao tiếp: v < 0.05 m/s
    """
    dx = robot.x - npc.x
    dy = robot.y - npc.y
    d_m = px_to_m(math.hypot(dx, dy))

    ang_npc_to_robot = math.atan2(dy, dx)
    ang_robot_to_npc = math.atan2(-dy, -dx)

    delta_npc_deg = angle_diff_deg(ang_npc_to_robot, npc.theta)
    delta_robot_deg = angle_diff_deg(ang_robot_to_npc, robot.theta)

    ok_dist = INTERACT_MIN_M <= d_m <= INTERACT_MAX_M
    ok_front = delta_npc_deg <= INTERACT_NPC_FAN_DEG
    ok_face = delta_robot_deg <= INTERACT_ROBOT_FACE_DEG
    ok_stop = robot.v_mps < INTERACT_STOP_SPEED_MPS

    details = {
        "d_m": d_m,
        "delta_npc_deg": delta_npc_deg,
        "delta_robot_deg": delta_robot_deg,
        "v_mps": robot.v_mps,
        "ok_dist": ok_dist,
        "ok_front": ok_front,
        "ok_face": ok_face,
        "ok_stop": ok_stop,
        "dist_ok": ok_dist,
        "in_front_ok": ok_front,
        "facing_npc_ok": ok_face,
        "stopped_ok": ok_stop,
    }
    return (ok_dist and ok_front and ok_face and ok_stop), details


def draw_npc_interaction_fan(
    screen: pygame.Surface,
    npc: VillagerNPC,
    robot: RobotPlayer,
    is_quest_target: bool = False,
    show_always: bool = True,
):
    """Vẽ hình quạt sáng màu xanh lá trước mặt NPC (d in [0.75m, 1.45m], góc +-35°)."""
    if npc.knockdown_timer > 0.0 or npc.is_run_over_dead:
        return

    dist_m = px_to_m(math.hypot(robot.x - npc.x, robot.y - npc.y))
    if not show_always and not is_quest_target and dist_m > 2.6:
        return

    r_min_px = m_to_px(INTERACT_MIN_M)
    r_max_px = m_to_px(INTERACT_MAX_M)
    half_rad = math.radians(INTERACT_NPC_FAN_DEG)

    ok_all, _ = check_front_interaction(robot, npc)

    fan_surf = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
    num_steps = 18
    outer_pts = []
    inner_pts = []
    for i in range(num_steps + 1):
        ang = (npc.theta - half_rad) + (2.0 * half_rad * i / num_steps)
        outer_pts.append((npc.x + r_max_px * math.cos(ang), npc.y + r_max_px * math.sin(ang)))
    for i in range(num_steps, -1, -1):
        ang = (npc.theta - half_rad) + (2.0 * half_rad * i / num_steps)
        inner_pts.append((npc.x + r_min_px * math.cos(ang), npc.y + r_min_px * math.sin(ang)))

    poly = outer_pts + inner_pts
    if ok_all:
        fill_col = (46, 235, 98, 135)
        border_col = (145, 255, 165, 245)
    elif is_quest_target:
        fill_col = (72, 215, 112, 85)
        border_col = (110, 245, 138, 198)
    else:
        fill_col = (88, 205, 122, 52)
        border_col = (110, 225, 140, 135)

    pygame.draw.polygon(fan_surf, fill_col, poly)
    pygame.draw.polygon(fan_surf, border_col, poly, 2)
    screen.blit(fan_surf, (0, 0))


def update_safety_and_collisions(game, dt: float):
    """Kiểm tra và xử phạt 4 cấp độ an toàn giữa Robot và các NPC."""
    if game.game_over:
        return

    if not hasattr(game, "comfort_score"):
        game.comfort_score = 100.0

    active_npcs = game.interior_npcs if game.in_interior else game.npcs
    any_discomfort = False

    for npc in active_npcs:
        if npc.is_run_over_dead or (not game.in_interior and getattr(npc, "is_home_at_night", False)):
            continue

        dx = game.robot.x - npc.x
        dy = game.robot.y - npc.y
        dist_px = math.hypot(dx, dy)
        dist_m = px_to_m(dist_px)

        # ------------------------------------------------------------------
        # TRƯỜNG HỢP NPC ĐANG NGÃ TRÊN ĐẤT -> KIỂM TRA CẤP 4 (CÁN ĐÈ QUA NGƯỜI)
        # ------------------------------------------------------------------
        if npc.knockdown_timer > 0.0:
            if (
                npc.knockdown_grace <= 0.0
                and dist_m < 0.65 * HITBOX_TOUCH_M
                and game.robot.v_mps > 0.08
            ):
                _trigger_instant_run_over(
                    game,
                    npc,
                    f"VI PHẠM CẤP 4: CỐ TÌNH ĐI ĐÈ QUA CƯ DÂN ({npc.name}) ĐANG NGÃ TRÊN ĐẤT!",
                )
                return
            continue

        # ------------------------------------------------------------------
        # KIỂM TRA CHẠM HITBOX (d <= R_robot + r_npc = 0.65m) -> CẤP 2, 3, 4
        # ------------------------------------------------------------------
        if dist_m <= HITBOX_TOUCH_M and game.robot.stun_timer <= 0.0:
            vec_to_npc = math.atan2(npc.y - game.robot.y, npc.x - game.robot.x)
            impact_angle_deg = angle_diff_deg(game.robot.theta, vec_to_npc)

            # CẤP ĐỘ 4: CÁN THẲNG QUA NGƯỜI Ở TỐC ĐỘ CAO (v >= 0.85 * v_max, góc < 20°)
            if game.robot.v_mps >= 0.85 * ROBOT_V_MAX_MPS and impact_angle_deg < 20.0:
                _trigger_instant_run_over(
                    game,
                    npc,
                    f"VI PHẠM NGHIÊM TRỌNG CẤP 4: PHÓNG TỐC ĐỘ CAO ({game.robot.v_mps:.2f}m/s) CÁN TRỰC DIỆN QUA {npc.name.upper()}!",
                )
                return

            # CẤP ĐỘ 2: ĐÂM NGÃ (BUMP / KNOCKDOWN)
            npc.knockdown_timer = 3.0
            npc.knockdown_grace = 0.65
            npc.trigger_emote("💫", 3.0)
            game.robot.apply_knockback(npc.x, npc.y, game)

            game.total_knockdowns += 1
            game.hearts = max(0, game.hearts - 1)
            game.comfort_score = max(0.0, getattr(game, "comfort_score", 100.0) - 25.0)
            any_discomfort = True
            game.emergency_flash_timer = 1.0
            game.add_score(PENALTY_KNOCKDOWN, f"Đâm ngã {npc.name}! (-1 Mạng)")
            if getattr(game, "dialogue", None) is not None:
                game.dialogue.adjust_friendship(npc.name, -150)
            if getattr(game, "audio", None) is not None:
                game.audio.play_sfx("bump")
            if getattr(game, "vfx", None) is not None:
                game.vfx.trigger_shake(7.0, 0.4)
            if getattr(game, "state", None) is not None:
                game.state.daily_collisions += 1
                game.state.handle_robot_knockdown_drop(game)

            # CẤP ĐỘ 3: ĐÂM NGÃ ĐỦ 3 LẦN (HẾT 3 TRÁI TIM -> MULTI-HIT DIE)
            if game.hearts <= 0 or game.total_knockdowns >= 3:
                game.add_score(PENALTY_MULTI_HIT_DIE, "Mất hết 3 Trái Tim An Toàn -> Ngắt nguồn!")
                game.game_over = True
                game.game_over_reason = (
                    f"CẤP ĐỘ 3 (MULTI-HIT DIE): Đã làm ngã cư dân {game.total_knockdowns} lần "
                    "(Mất hết 3 Trái Tim An Toàn)! Hệ thống tự động ngắt nguồn Robot (-250 điểm)."
                )
                game.emergency_flash_timer = 1.5
                return
            else:
                game.set_banner(
                    f"CẢNH BÁO CẤP 2: Bạn vừa đâm ngã {npc.name} (-100đ, mất 1 Trái Tim)! "
                    f"Còn {game.hearts}/3 Mạng. Tuyệt đối không đi đè lên người đang ngã!",
                    (255, 115, 115),
                )
            continue

        # ------------------------------------------------------------------
        # CẤP ĐỘ 1 & VÙNG XÃ HỘI: XÂM PHẠM VÙNG CÁ NHÂN + CẢNH BÁO SỚM THANG ĐO COMFORT HRI (L4, D6, Pha 2)
        # ------------------------------------------------------------------
        npcs_db = getattr(getattr(game, "state", None), "npcs_db", {})
        npc_info = npcs_db.get(npc.name, {}) if isinstance(npcs_db, dict) else {}
        db_safety_r = float(npc_info.get("safety_radius_m", 1.25) or 1.25) if isinstance(npc_info, dict) else 1.25
        personal_space_limit_m = max(PERSONAL_SPACE_M, min(1.05, db_safety_r * 0.74))

        if HITBOX_TOUCH_M < dist_m < personal_space_limit_m:
            any_discomfort = True
            npc.trigger_emote("!", 1.0)
            if dist_px > 1e-3 and npc.intrusion_step_cooldown <= 0.0:
                step_bx = npc.x - (dx / dist_px) * 6.0
                step_by = npc.y - (dy / dist_px) * 6.0
                if not game.is_circle_blocked(step_bx, step_by, npc.radius):
                    npc.x, npc.y = step_bx, step_by
                npc.intrusion_step_cooldown = 0.25

            # Phạt mượt theo mức độ tiến sát vào vùng cá nhân + giảm Thang đo Comfort HRI
            proximity_weight = 1.0 + max(
                0.0,
                (personal_space_limit_m - dist_m) / max(0.1, personal_space_limit_m - HITBOX_TOUCH_M),
            )
            game.comfort_score = max(0.0, game.comfort_score - 12.0 * dt * proximity_weight)
            game.intrusion_accum += dt * proximity_weight
            if game.intrusion_accum >= 1.0:
                game.intrusion_accum -= 1.0
                game.add_score(
                    PENALTY_PERSONAL_SPACE_PER_SEC, f"Đi quá sát {npc.name} (<{personal_space_limit_m:.2f}m)"
                )
        elif personal_space_limit_m <= dist_m < db_safety_r and game.robot.v_mps > 0.38:
            # Cảnh báo sớm trong vùng xã hội khi Robot phóng nhanh qua gần cư dân
            any_discomfort = True
            game.comfort_score = max(0.0, game.comfort_score - 3.8 * dt)
            if npc.emote_timer <= 0.0:
                npc.trigger_emote("?", 0.8)

        # ------------------------------------------------------------------
        # THƯỞNG NHƯỜNG ĐƯỜNG VĂN MINH (+5 ĐIỂM DỰA TRÊN VẬN TỐC TIẾN LẠI GẦN TTC & VẬN TỐC THỰC <= 0.35 m/s - L1, Pha 2)
        # ------------------------------------------------------------------
        if (
            not npc.is_stationary
            and npc.speed_mps > 0.15
            and 1.05 <= dist_m <= 2.35
            and npc.yield_reward_cooldown <= 0.0
        ):
            ang_to_npc = math.atan2(npc.y - game.robot.y, npc.x - game.robot.x)
            if angle_diff_deg(game.robot.theta, ang_to_npc) <= 45.0:
                # Tính vận tốc tiến lại gần (closing speed) giữa NPC và Robot theo trục nối tâm
                ux = (npc.x - game.robot.x) / max(1.0, dist_px)
                uy = (npc.y - game.robot.y) / max(1.0, dist_px)
                npc_vx = math.cos(npc.theta) * npc.speed_mps
                npc_vy = math.sin(npc.theta) * npc.speed_mps
                rob_vx = math.cos(game.robot.theta) * game.robot.v_mps
                rob_vy = math.sin(game.robot.theta) * game.robot.v_mps
                closing_mps = (rob_vx - npc_vx) * ux + (rob_vy - npc_vy) * uy
                if (
                    game.robot.v_mps <= 0.35
                    and (game.robot.is_slow_active or game.robot.v_mps > 0.02)
                    and closing_mps >= -0.15
                ):
                    npc.yield_reward_cooldown = 12.0
                    npc.trigger_emote("♥", 2.2)
                    game.comfort_score = min(100.0, game.comfort_score + 4.0)
                    game.add_score(SCORE_SMART_YIELD, f"Nhường đường cho {npc.name}!")
                    if getattr(game, "state", None) is not None:
                        game.state.total_yields = getattr(game.state, "total_yields", 0) + 1
                        if hasattr(game.state, "check_achievements_and_certifications"):
                            game.state.check_achievements_and_certifications(game)
                    if getattr(game, "dialogue", None) is not None:
                        game.dialogue.adjust_friendship(npc.name, 15)

    # Hồi phục chậm Thang đo Comfort HRI khi giữ khoảng cách an toàn, hoặc phạt khi chạm đáy
    if not any_discomfort:
        game.comfort_score = min(100.0, game.comfort_score + 2.2 * dt)
    elif game.comfort_score <= 0.0:
        game.comfort_score = 45.0
        game.add_score(-35, "Chỉ số An Tâm HRI chạm đáy (0%)!")
        game.set_banner(
            "CẢNH BÁO HRI: Chỉ số An Tâm cư dân chạm đáy (0%)! Bị trừ -35đ uy tín. Hãy đi chậm [X] khi gần người!",
            (255, 130, 95),
        )

    # ------------------------------------------------------------------
    # TƯƠNG TÁC ĐẨY NHẸ HOẶC VA CHẠM VỚI XE KÉO NÔNG SẢN AGV (V4 + Cơ chế Đẩy AGV)
    # ------------------------------------------------------------------
    if not game.in_interior and game.robot.stun_timer <= 0.0:
        for agv in getattr(game, "agvs", []):
            dist_agv = math.hypot(game.robot.x - agv.x, game.robot.y - agv.y)
            touch_d = agv.radius + game.robot.radius - 2.0
            if dist_agv <= touch_d:
                ux = (agv.x - game.robot.x) / max(1.0, dist_agv)
                uy = (agv.y - game.robot.y) / max(1.0, dist_agv)
                if abs(ux) + abs(uy) < 1e-3:
                    ux, uy = math.cos(game.robot.theta), math.sin(game.robot.theta)

                # Nếu Robot đi chậm (<= 0.65 m/s) hoặc AGV đang ở chế độ đi theo/đỗ -> Đẩy nhẹ AGV dịch đi mượt mà
                is_gentle_push = (
                    getattr(agv, "mode", "patrol") in ("follow", "parked")
                    or (0.02 < game.robot.v_mps <= 0.65)
                    or getattr(game.robot, "is_slow_active", False)
                )
                if is_gentle_push:
                    if hasattr(agv, "apply_push"):
                        agv.apply_push(ux, uy, strength=130.0)
                    step_push = max(6.0, touch_d - dist_agv + 4.0)
                    nx = agv.x + ux * step_push
                    ny = agv.y + uy * step_push
                    if not game.is_circle_blocked(nx, ny, agv.radius * 0.85):
                        agv.x, agv.y = nx, ny
                    if getattr(agv, "mode", "patrol") == "patrol":
                        agv.mode = "parked"
                    if getattr(game, "state", None) is not None and hasattr(game.state, "unlock_achievement"):
                        game.state.unlock_achievement(game, "agv_partner")
                    game.set_banner(
                        "Đã đẩy nhẹ Xe Kéo AGV sang một bên! Bấm [E] hoặc [C] cạnh AGV để gọi đi theo làm việc.",
                        (165, 240, 195),
                    )
                else:
                    # Phóng tốc độ cao đâm trực diện vào AGV đang chạy tuần tra -> Phạt -15đ
                    if hasattr(agv, "apply_push"):
                        agv.apply_push(ux, uy, strength=95.0)
                    game.robot.apply_knockback(agv.x, agv.y, game)
                    game.add_score(-15, "Va chạm mạnh Xe Kéo Nông Sản AGV!")
                    if getattr(game, "audio", None) is not None:
                        game.audio.play_sfx("bump")
                    if getattr(game, "vfx", None) is not None:
                        game.vfx.trigger_shake(4.5, 0.25)
                    game.set_banner(
                        "Cẩn thận! Bạn vừa phóng nhanh đâm vào Xe Kéo AGV (-15đ). Hãy đi chậm [X] để đẩy nhẹ hoặc bấm [E]/[C] gọi AGV đi theo!",
                        (255, 175, 95),
                    )
                break


def _trigger_instant_run_over(game, npc: VillagerNPC, reason_text: str):
    npc.is_run_over_dead = True
    npc.knockdown_timer = 0.0
    game.robot.v_mps = 0.0
    game.robot.vx, game.robot.vy = 0.0, 0.0
    game.hearts = 0
    game.add_score(PENALTY_RUN_OVER_DIE, "VI PHẠM CẤP 4: CÁN QUA CƯ DÂN!")
    game.game_over = True
    game.game_over_reason = reason_text + " (Phạt -500 điểm • Xử thua ngay lập tức!)"
    game.emergency_flash_timer = 1.8

