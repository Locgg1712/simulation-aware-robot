# game/autopilot.py
"""
Bộ điều khiển AI Tự Hành (Auto-Pilot Mode - Phím [P]) cho Robot trong thế giới FarmBot Town:
Tự động di chuyển qua các bản đồ, căn vị trí vào Vùng Quạt Xanh trước mặt NPC,
hái trái cây, câu cá, vào trong nhà và chủ động giảm tốc nhường đường cho cư dân.
"""

from __future__ import annotations

import math
import pygame

from .constants import SCREEN_H, SCREEN_W, m_to_px
from .entities import VillagerNPC
from .farming import (
    CROP_CATALOG,
    SEED_VENDOR_NAME,
    is_harvestable_plot,
    is_within_harvest_reach,
)
from .quests import distance_to_harvest_spot, handle_interact_action
from .safety_hri import check_front_interaction


def compute_autopilot_command(game, dt: float) -> tuple[float, float, bool]:
    """Trả về (ux, uy, slow_flag) cho Robot ở chế độ AI Auto-Pilot."""
    if getattr(game, "dialogue", None) is not None and game.dialogue.active:
        if game.dialogue.auto_close_timer < 3.8:
            game.dialogue.close()
        else:
            return 0.0, 0.0, True

    q = game.active_quest
    if q is None:
        return 0.0, 0.0, False

    target_map = 1
    tx, ty = SCREEN_W * 0.5, SCREEN_H * 0.5
    want_interact = False
    target_npc: VillagerNPC | None = None

    rx, ry = game.room_rect.x, game.room_rect.y
    rw, rh = game.room_rect.width, game.room_rect.height
    exit_mat_rect = pygame.Rect(game.room_rect.centerx - 36, ry + rh - 28, 72, 24)

    if q.status == "available":
        target_map = q.giver_map
        if not game.in_interior and game.current_map_id == target_map:
            for n in game.npcs:
                if n.name == q.giver_name:
                    target_npc = n
                    break
    elif q.status == "accepted":
        if q.item_key not in game.robot.inventory:
            if q.category == "harvest":
                # Kiểm tra nếu là vật phẩm dã ngoại (Forage) đang có trên bản đồ
                forage_list = [
                    f for f in getattr(getattr(game, "state", None), "forage_items", [])
                    if not f.collected and f.item_key == q.item_key
                ]
                if forage_list:
                    f_target = forage_list[0]
                    target_map = f_target.map_id
                    if game.current_map_id == target_map and not game.in_interior:
                        tx, ty = f_target.x, f_target.y
                        if math.hypot(game.robot.x - tx, game.robot.y - ty) <= 46.0:
                            want_interact = True
                else:
                    target_map = 2
                    if game.current_map_id == 2 and not game.in_interior:
                        avail = [h for h in game.harvest_spots if h.item_key == q.item_key and h.has_produce]
                        if avail:
                            hs = avail[0]
                            if hs.field_rect is not None:
                                tx = float(hs.field_rect.centerx)
                                ty = float(hs.field_rect.bottom + 14.0)
                            else:
                                tx, ty = hs.x, hs.y + 18.0
                            if is_within_harvest_reach(game.robot.x, game.robot.y, hs):
                                want_interact = True
                        elif q.item_key in CROP_CATALOG and getattr(game, "farming", None) is not None:
                            farming = game.farming
                            growing_plots = [
                                h for h in game.harvest_spots
                                if is_harvestable_plot(h)
                                and getattr(h, "crop_state", "") == "growing"
                                and h.item_key == q.item_key
                            ]
                            unwatered = [h for h in growing_plots if not getattr(h, "watered", False)]
                            if unwatered:
                                hp = unwatered[0]
                                tx = float(hp.field_rect.centerx) if hp.field_rect else hp.x
                                ty = float(hp.field_rect.bottom + 14.0) if hp.field_rect else hp.y + 18.0
                                if is_within_harvest_reach(game.robot.x, game.robot.y, hp):
                                    want_interact = True
                            elif growing_plots:
                                game.set_banner(
                                    "Ruộng đã được tưới nước! Hãy về Đế Sạc Xưởng Robot (Map 4) bấm [N] ngủ qua ngày để cây chín.",
                                    (165, 238, 255),
                                )
                                return 0.0, 0.0, False
                            elif farming.seed_bag.get(q.item_key, 0) > 0:
                                farming.selected_seed = q.item_key
                                empty_plots = [
                                    h for h in game.harvest_spots
                                    if is_harvestable_plot(h) and getattr(h, "crop_state", "") == "empty"
                                ]
                                if empty_plots:
                                    ep = empty_plots[0]
                                    tx = float(ep.field_rect.centerx) if ep.field_rect else ep.x
                                    ty = float(ep.field_rect.bottom + 14.0) if ep.field_rect else ep.y + 18.0
                                    if is_within_harvest_reach(game.robot.x, game.robot.y, ep):
                                        want_interact = True
                            else:
                                vendor = next((n for n in game.npcs if n.name == SEED_VENDOR_NAME), None)
                                if vendor is not None:
                                    ideal_dist = m_to_px(1.08)
                                    vx = vendor.x + math.cos(vendor.theta) * ideal_dist
                                    vy = vendor.y + math.sin(vendor.theta) * ideal_dist
                                    tx, ty = vx, vy
                                    if math.hypot(game.robot.x - vx, game.robot.y - vy) <= 16.0:
                                        game.robot.v_mps = 0.0
                                        game.robot.theta = math.atan2(
                                            vendor.y - game.robot.y, vendor.x - game.robot.x
                                        )
                                        ok_all, _ = check_front_interaction(game.robot, vendor)
                                        if ok_all:
                                            if farming.buy_seed(game, q.item_key, 1):
                                                farming.selected_seed = q.item_key
                                            else:
                                                return 0.0, 0.0, False
                                        return 0.0, 0.0, True
                        else:
                            game.set_banner(
                                "Cây ăn quả đã thu hoạch hết hôm nay! Hãy về Đế Sạc Xưởng Robot (Map 4) bấm [N] ngủ qua ngày.",
                                (255, 215, 125),
                            )
                            return 0.0, 0.0, False
            elif q.category == "fishing":
                target_map = 3
                if game.current_map_id == 3 and not game.in_interior and game.fishing_spots:
                    fs = game.fishing_spots[0]
                    tx, ty = fs.stand_x, fs.stand_y
                    if game.robot.fishing_state == "biting":
                        want_interact = True
                    elif game.robot.fishing_state == "idle" and math.hypot(game.robot.x - tx, game.robot.y - ty) <= 32.0:
                        want_interact = True
                    elif game.robot.fishing_state == "waiting":
                        return 0.0, 0.0, False
        else:
            if q.receiver_map == 5:
                target_map = (
                    4
                    if q.receiver_house_id in ("house_gus", "house_robin", "house_willy", "house_lewis")
                    else 1
                )
                if game.in_interior:
                    if (
                        game.current_interior is not None
                        and game.current_interior.house_id == q.receiver_house_id
                        and game.interior_npcs
                    ):
                        target_npc = game.interior_npcs[0]
                    else:
                        tx, ty = float(exit_mat_rect.centerx), float(exit_mat_rect.centery)
                elif game.current_map_id == target_map:
                    for b in game.props:
                        if b.house_id == q.receiver_house_id and b.door_rect:
                            tx, ty = float(b.door_rect.centerx), float(b.door_rect.centery)
                            if math.hypot(game.robot.x - tx, game.robot.y - ty) <= 42.0:
                                want_interact = True
                            break
            else:
                target_map = q.receiver_map
                if game.current_map_id == target_map and not game.in_interior:
                    for n in game.npcs:
                        if n.name == q.receiver_name:
                            target_npc = n
                            break

    if game.in_interior and target_npc is None:
        tx, ty = float(exit_mat_rect.centerx), float(exit_mat_rect.centery)
    elif not game.in_interior and game.current_map_id != target_map:
        next_map = 1 if game.current_map_id != 1 else target_map
        for p in game.portals:
            if p.target_map_id == next_map:
                tx, ty = float(p.rect.centerx), float(p.rect.centery)
                break

    if target_npc is not None:
        ideal_dist = m_to_px(1.08)
        tx = target_npc.x + math.cos(target_npc.theta) * ideal_dist
        ty = target_npc.y + math.sin(target_npc.theta) * ideal_dist
        if math.hypot(game.robot.x - tx, game.robot.y - ty) <= 14.0:
            game.robot.v_mps = 0.0
            game.robot.theta = math.atan2(target_npc.y - game.robot.y, target_npc.x - game.robot.x)
            ok_all, _ = check_front_interaction(game.robot, target_npc)
            if ok_all:
                handle_interact_action(game)
            return 0.0, 0.0, True

    if want_interact:
        game.robot.v_mps = 0.0
        if game.robot.harvest_target is None:
            handle_interact_action(game)
        return 0.0, 0.0, True

    dx, dy = tx - game.robot.x, ty - game.robot.y
    dist = math.hypot(dx, dy)
    if dist < 6.0:
        return 0.0, 0.0, True

    ux, uy = dx / dist, dy / dist
    slow = game.in_interior
    active_npcs = game.interior_npcs if game.in_interior else game.npcs
    for n in active_npcs:
        nd = math.hypot(game.robot.x - n.x, game.robot.y - n.y)
        if nd < 85.0:
            slow = True
            if nd > 1e-3 and (target_npc is None or n is not target_npc or nd < 44.0):
                rep = (85.0 - nd) / 85.0
                ux += ((game.robot.x - n.x) / nd) * rep * 1.6
                uy += ((game.robot.y - n.y) / nd) * rep * 1.6

    norm = math.hypot(ux, uy)
    if norm > 1e-4:
        ux, uy = ux / norm, uy / norm
    return ux, uy, slow

