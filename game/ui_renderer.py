# game/ui_renderer.py
"""
Hệ thống Hiển thị Giao diện & Đồ họa Pixel Art (Mục 5 & Mục 6 trong Context_game_farmbot.md):
- Kết xuất cảnh Ngoài trời (Map 1..4) có Y-Sorting, ruộng cây trồng nhiều giai đoạn (stage_00..09),
  vườn cây ăn quả đính quả chín, chuồng thú nuôi chuyển động, điểm câu cá gợn sóng,
  và Quạt Tương Tác Trước Mặt NPC (Front Interaction Fan).
- Kết xuất cảnh Nội thất (Map 5): mỗi ngôi nhà có một thiết kế nội thất, tông màu sàn/tường,
  thảm trải sàn và cách bài trí đồ đạc riêng biệt.
- Tự động xuống dòng (word-wrap) cho mọi bảng thông báo, cảnh báo, HUD và Game Over để chữ
  KHÔNG BAO GIỜ bị tràn ra ngoài khung.
"""

from __future__ import annotations

import math
import pygame

from .constants import (
    CHARGING_DOCKS,
    GRID_COLS,
    GRID_ROWS,
    ITEM_NAMES_VI,
    MAP_TITLES,
    SCREEN_H,
    SCREEN_W,
    T_WATER,
    TILE_SIZE,
    px_to_m,
)
from .entities import FarmAnimal, FarmCartAGV, PropObject, RobotPlayer, VillagerNPC
from .farming import CROP_CATALOG, EQUIP_CATALOG, SEED_VENDOR_NAME, is_within_harvest_reach
from .maps import get_interior_theme
from .quests import distance_to_harvest_spot
from .safety_hri import check_front_interaction, draw_npc_interaction_fan
from .stardew_systems import render_shipping_bin_overlay


def wrap_text(font: pygame.font.Font, text: str, max_width: int) -> list[str]:
    """Tự động ngắt dòng văn bản tiếng Việt để không bao giờ tràn khỏi khung."""
    if not text:
        return []
    words = text.split(" ")
    lines: list[str] = []
    current = ""
    for w in words:
        test = f"{current} {w}".strip() if current else w
        if font.size(test)[0] <= max_width:
            current = test
        else:
            if current:
                lines.append(current)
            current = w
    if current:
        lines.append(current)
    return lines


def build_hud_buttons() -> list[dict]:
    """Khởi tạo các nút điều khiển nhanh gọn ở thanh dưới màn hình (nhường tối đa diện tích cho bản đồ)."""
    y = SCREEN_H - 34
    specs = [
        ("interact", "[E] Tương Tác", 262, 86),
        ("gift", "[G] Quà", 352, 54),
        ("agv_call", "[C] AGV", 410, 56),
        ("quest", "[TAB] Đơn", 470, 62),
        ("slow", "[X] Chậm", 536, 58),
        ("auto", "[P] AI", 598, 46),
        ("workshop", "[U] Xưởng", 648, 64),
        ("journal", "[J] Sổ Tay", 716, 66),
        ("sleep", "[N] Sạc/Ngủ", 786, 68),
        ("minimap", "[M] Radar", 858, 62),
        ("reset", "[R] Lại", 924, 54),
    ]
    buttons = []
    for btn_id, label, x, w in specs:
        buttons.append(
            {
                "id": btn_id,
                "label": label,
                "rect": pygame.Rect(x, y, w, 26),
            }
        )
    return buttons


def get_npc_quest_marker(game, npc_name: str) -> str | None:
    """Trả về dấu '!' (Giao việc) hoặc '?' (Trả hàng) trên đầu NPC."""
    q = game.active_quest
    if q.status == "accepted" and q.receiver_name == npc_name:
        in_right_place = (
            (
                q.receiver_map == 5
                and game.in_interior
                and (
                    not q.receiver_house_id
                    or getattr(getattr(game, "current_interior", None), "house_id", "") == q.receiver_house_id
                )
            )
            or (
                q.receiver_map != 5
                and not game.in_interior
                and game.current_map_id == q.receiver_map
            )
        )
        if in_right_place:
            return "?"
    if not game.in_interior and q.status != "accepted":
        if q.status == "available" and q.giver_name == npc_name and q.giver_map == game.current_map_id:
            return "!"
        for other_q in game.quests:
            if (
                other_q.status == "available"
                and other_q.giver_name == npc_name
                and other_q.giver_map == game.current_map_id
            ):
                return "!"
    return None


def render_game(game):
    """Vẽ toàn bộ khung hình của trò chơi."""
    if game.in_interior:
        _render_indoor_scene(game)
    else:
        _render_outdoor_scene(game)

    for ft in game.floating_texts:
        lbl = game.font_sm.render(ft.text, True, ft.color)
        sh = game.font_sm.render(ft.text, True, (18, 12, 8))
        x = max(8, min(SCREEN_W - lbl.get_width() - 8, int(ft.x - lbl.get_width() // 2)))
        y = max(8, int(ft.y))
        game.screen.blit(sh, (x + 1, y + 1))
        game.screen.blit(lbl, (x, y))

    if getattr(game, "fishing_minigame", None) is not None and game.fishing_minigame.active:
        game.fishing_minigame.render(game.screen, game)

    _render_hud(game)

    if getattr(game, "vfx", None) is not None:
        game.vfx.draw_hud_vfx(game.screen, game)

    if getattr(game, "dialogue", None) is not None and game.dialogue.active:
        game.dialogue.render(game.screen, game)

    if getattr(game, "workshop", None) is not None and game.workshop.open:
        game.workshop.render_modal(game.screen, game)

    if getattr(getattr(game, "farming", None), "shop_open", False):
        game.farming.render_shop(game.screen, game)

    if getattr(game, "journal", None) is not None and game.journal.open:
        game.journal.render(game.screen, game)

    if getattr(getattr(game, "state", None), "summary_open", False):
        game.state.render_end_of_day_modal(game.screen, game)

    if game.game_over:
        _render_game_over_modal(game)


def _draw_crop_field(game, hspot):
    """Vẽ một thửa ruộng đất xới với các luống cây trồng theo hàng (stage_00..09)."""
    rect: pygame.Rect | None = hspot.field_rect
    if rect is None:
        stage = f"stage_{hspot.growth_stage:02d}"
        c_spr = game.vault.scaled(f"crops/{hspot.crop_name}/{stage}", 28, 32)
        for dx in (-24, 0, 24):
            for dy in (-14, 12):
                if c_spr is not None:
                    game.screen.blit(c_spr, (int(hspot.x + dx - 14), int(hspot.y + dy - 22)))
        return

    is_deco = str(getattr(hspot, "spot_id", "")).startswith("deco_")
    c_state = getattr(hspot, "crop_state", "ripe" if hspot.has_produce else "empty")
    cols = max(1, rect.width // TILE_SIZE)
    rows = max(1, rect.height // TILE_SIZE)

    # 1. Ruộng Đất Trống (chưa gieo hạt): vẽ luống đất xới nâu đậm/nhạt, không vẽ cây
    if not is_deco and c_state == "empty":
        for r in range(rows):
            for c in range(cols):
                tx = rect.x + c * TILE_SIZE
                ty = rect.y + r * TILE_SIZE
                for fy in (6, 15, 24):
                    pygame.draw.line(game.screen, (92, 58, 34), (tx + 3, ty + fy), (tx + TILE_SIZE - 4, ty + fy), 3)
                    pygame.draw.line(game.screen, (132, 88, 54), (tx + 4, ty + fy - 1), (tx + TILE_SIZE - 5, ty + fy - 1), 1)
        if is_within_harvest_reach(game.robot.x, game.robot.y, hspot):
            pygame.draw.rect(game.screen, (185, 255, 135), rect, 2, border_radius=4)
    else:
        watered_spr = game.vault.scaled("crops/soil/watered_soil", TILE_SIZE, TILE_SIZE)
        stage_idx = hspot.growth_stage
        stage_name = f"stage_{stage_idx:02d}"
        crop_spr = game.vault.scaled(f"crops/{hspot.crop_name}/{stage_name}", 26, 30)
        is_moist = bool(getattr(hspot, "watered", False) or getattr(hspot, "has_sprinkler", False))

        for r in range(rows):
            for c in range(cols):
                tx = rect.x + c * TILE_SIZE
                ty = rect.y + r * TILE_SIZE
                if not is_deco and c_state == "growing":
                    if is_moist:
                        if watered_spr is not None:
                            game.screen.blit(watered_spr, (tx, ty))
                        else:
                            pygame.draw.rect(game.screen, (68, 42, 24), (tx + 2, ty + 2, TILE_SIZE - 4, TILE_SIZE - 4), border_radius=3)
                elif hspot.has_produce and watered_spr is not None and (r + c) % 2 == 0:
                    game.screen.blit(watered_spr, (tx, ty))

                if crop_spr is not None:
                    bob = int(math.sin(game.sim_time * 3.0 + c * 0.7 + r * 0.5) * 1.5) if hspot.has_produce else 0
                    game.screen.blit(crop_spr, (tx + 3, ty - 2 + bob))

    # Vẽ các Thiết Bị Trang Trí & Bảo Vệ Ruộng được gắn trên thửa ruộng (Sprinkler, Bù Nhìn, Cọc Cảm Biến & Hướng Dương)
    if getattr(hspot, "has_sprinkler", False):
        sp_spr = game.vault.scaled("sprinkler", 30, 30)
        if sp_spr is not None:
            game.screen.blit(sp_spr, (rect.centerx - 15, rect.centery - 15))
    if getattr(hspot, "has_scarecrow", False):
        sc_spr = game.vault.scaled("scarecrow", 34, 42)
        if sc_spr is not None:
            game.screen.blit(sc_spr, (rect.right - 22, rect.top - 18))
    if getattr(hspot, "has_bio_sensor", False):
        sf_spr = game.vault.scaled("sunflower", 28, 34)
        sn_spr = game.vault.scaled("rh_sensor_post", 20, 32)
        if sf_spr is not None:
            game.screen.blit(sf_spr, (rect.left - 8, rect.top - 12))
        if sn_spr is not None:
            game.screen.blit(sn_spr, (rect.left + 14, rect.top - 12))

    # Biểu tượng báo hiệu ruộng chín có thể thu hoạch ở mép ruộng
    if not is_deco and c_state == "ripe" and hspot.has_produce and hspot in game.harvest_spots:
        bounce = int(math.sin(game.sim_time * 5.0) * 3)
        icon = game.vault.get_item_icon(hspot.item_key, 22)
        bx = int(hspot.x - 13)
        by = int(rect.top - 14 + bounce)
        pygame.draw.circle(game.screen, (42, 28, 16, 210), (bx + 13, by + 13), 14)
        pygame.draw.circle(game.screen, (255, 225, 88), (bx + 13, by + 13), 14, 2)
        game.screen.blit(icon, (bx + 2, by + 2))


def _render_outdoor_scene(game):
    if game.terrain_surface is not None:
        game.screen.blit(game.terrain_surface, (0, 0))

    # Gợn sóng nước lấp lánh
    wave_phase = int(game.sim_time * 3.5) % 2
    for r in range(GRID_ROWS):
        for c in range(GRID_COLS):
            if game.tiles[r][c] == T_WATER and (r + c + wave_phase) % 5 == 0:
                wx = c * TILE_SIZE + 6
                wy = r * TILE_SIZE + 14
                pygame.draw.line(game.screen, (135, 208, 250), (wx, wy), (wx + 12, wy), 2)

    # Điểm thả câu cá (Map 3)
    for fspot in game.fishing_spots:
        wx, wy = int(fspot.water_x), int(fspot.water_y)
        rad = 10 + int(math.sin(game.sim_time * 4.0) * 3)
        pygame.draw.circle(game.screen, (165, 232, 255), (wx, wy), rad, 2)
        fish_ic = game.vault.get_item_icon("fish", 18)
        game.screen.blit(fish_ic, (wx - 9, wy - 9))
        sx, sy = int(fspot.stand_x), int(fspot.stand_y)
        pygame.draw.circle(game.screen, (255, 235, 110), (sx, sy), 10, 2)
        if math.hypot(game.robot.x - sx, game.robot.y - sy) <= 74.0:
            lbl = game.font_xs.render(f"[E] Câu cá: {fspot.title}", True, (255, 248, 175))
            lx = max(8, min(SCREEN_W - lbl.get_width() - 12, sx - lbl.get_width() // 2))
            ly = max(8, sy - 34)
            pygame.draw.rect(
                game.screen,
                (24, 38, 54),
                (lx - 5, ly - 2, lbl.get_width() + 10, 19),
                border_radius=5,
            )
            pygame.draw.rect(
                game.screen,
                (125, 215, 255),
                (lx - 5, ly - 2, lbl.get_width() + 10, 19),
                1,
                border_radius=5,
            )
            game.screen.blit(lbl, (lx, ly))

    # Vẽ các thửa ruộng nông sản (cả ruộng thu hoạch và ruộng trang trí)
    for hspot in getattr(game, "deco_fields", []):
        if hspot.kind == "crop_plot":
            _draw_crop_field(game, hspot)
    for hspot in game.harvest_spots:
        if hspot.kind == "crop_plot":
            _draw_crop_field(game, hspot)

    # Vẽ hạt bụi bánh xe Robot, Vật phẩm dã ngoại (Foraging), Đồ rơi & Sự kiện Ngẫu nhiên
    if getattr(game, "vfx", None) is not None:
        game.vfx.draw_world_vfx(game.screen, game)
    if getattr(game, "state", None) is not None:
        game.state.render_forage_items(game.screen, game)
        game.state.render_dropped_items(game.screen, game)
    if getattr(game, "random_events", None) is not None:
        game.random_events.render_world_event(game.screen, game)

    # Quạt Tương Tác Hợp Lệ Trước Mặt NPC (Front Interaction Fan)
    if game.show_interaction_fan:
        for npc in game.npcs:
            if getattr(npc, "is_home_at_night", False):
                continue
            marker = get_npc_quest_marker(game, npc.name)
            draw_npc_interaction_fan(
                game.screen,
                npc,
                game.robot,
                is_quest_target=(marker is not None),
                show_always=False,
            )

    # Sắp xếp Y-Sorting cho Công trình, Cây cối, Thú nuôi, AGV, NPC và Robot
    renderables = []
    for prop in game.props:
        renderables.append((prop.sort_y, "prop", prop))
    for ani in game.animals:
        sort_y = ani.sort_y if isinstance(ani, FarmAnimal) else ani["y"] + 8.0
        renderables.append((sort_y, "animal", ani))
    for agv in game.agvs:
        renderables.append((agv.sort_y, "agv", agv))
    for npc in game.npcs:
        renderables.append((npc.sort_y, "npc", npc))
    renderables.append((game.robot.sort_y, "robot", game.robot))
    renderables.sort(key=lambda item: item[0])

    for _, kind, obj in renderables:
        if kind == "prop":
            prop_obj: PropObject = obj
            prop_obj.draw(game.screen, game.vault)
            # Nếu là cây ăn quả có trái chín -> Vẽ các quả chín trên tán cây
            hspot = getattr(prop_obj, "harvest", None)
            if hspot is not None and hspot.has_produce:
                f_icon = game.vault.get_item_icon(hspot.item_key, 18)
                w, h = prop_obj.sprite.get_size()
                for ox, oy in [(int(w * 0.22), int(h * 0.22)), (int(w * 0.56), int(h * 0.18)), (int(w * 0.38), int(h * 0.38))]:
                    game.screen.blit(f_icon, (prop_obj.x + ox, prop_obj.y + oy))
        elif kind == "animal":
            if isinstance(obj, FarmAnimal):
                obj.draw(game.screen, game.vault)
            else:
                spr = game.vault.scaled(obj["sprite"], 38, 34)
                if spr is not None:
                    if obj.get("dir", 1) < 0:
                        spr = pygame.transform.flip(spr, True, False)
                    game.screen.blit(spr, (int(obj["x"]) - 19, int(obj["y"]) - 24))
        elif kind == "agv":
            agv_obj: FarmCartAGV = obj
            agv_obj.draw(game.screen, game.vault, game.font_xs, game.robot.x, game.robot.y)
        elif kind == "npc":
            npc_obj: VillagerNPC = obj
            marker = get_npc_quest_marker(game, npc_obj.name)
            npc_obj.draw(game.screen, game.vault, game.font_xs, game.sim_time, marker)
        elif kind == "robot":
            rob_obj: RobotPlayer = obj
            rob_obj.draw(game.screen, game.vault, game.font_xs, game.sim_time)

    # Nhãn nhắc bấm [E] trước cây ăn quả / thửa ruộng nông sản
    for hspot in game.harvest_spots:
        if not is_within_harvest_reach(game.robot.x, game.robot.y, hspot):
            continue

        prompt_txt = ""
        t_col = (255, 245, 150)
        b_col = (240, 200, 88)

        if hspot.kind == "crop_plot":
            c_state = getattr(hspot, "crop_state", "ripe" if hspot.has_produce else "empty")
            farming = getattr(game, "farming", None)
            sel_key = getattr(farming, "selected_seed", "wheat") if farming is not None else "wheat"
            equip_bag = getattr(farming, "equip_bag", {}) if farming is not None else {}
            if sel_key in EQUIP_CATALOG and int(equip_bag.get(sel_key, 0)) > 0:
                eq_vi = EQUIP_CATALOG[sel_key]["short_vi"]
                prompt_txt = f"[E] Lắp {eq_vi} lên ruộng | [Q] Đổi hạt/thiết bị"
                t_col = (145, 255, 225)
                b_col = (85, 225, 195)
            elif c_state == "empty":
                seed_bag = getattr(farming, "seed_bag", {}) if farming is not None else {}
                cnt = int(seed_bag.get(sel_key, 0))
                if cnt <= 0:
                    for k in CROP_CATALOG:
                        if int(seed_bag.get(k, 0)) > 0:
                            sel_key = k
                            cnt = int(seed_bag[k])
                            break
                if cnt > 0:
                    seed_vi = CROP_CATALOG.get(sel_key, {}).get("name_vi", sel_key)
                    prompt_txt = f"[E] Trồng {seed_vi} (Còn {cnt} hạt) | [Q] Đổi hạt"
                    t_col = (145, 255, 165)
                    b_col = (95, 225, 125)
                else:
                    prompt_txt = f"[E] Ruộng Trống — Mua hạt tại {SEED_VENDOR_NAME} (Map 2)"
                    t_col = (255, 212, 125)
                    b_col = (225, 168, 78)
            elif c_state == "growing" and not hspot.has_produce:
                crop_vi = CROP_CATALOG.get(hspot.crop_name, {}).get(
                    "name_vi", ITEM_NAMES_VI.get(hspot.item_key, hspot.title)
                )
                dg = int(getattr(hspot, "days_grown", 0))
                dn = max(1, int(getattr(hspot, "days_needed", 1)))
                if not getattr(hspot, "watered", False) and not getattr(hspot, "has_sprinkler", False):
                    prompt_txt = f"[E] Tưới nước ({crop_vi}: {dg}/{dn} ngày)"
                    t_col = (125, 235, 255)
                    b_col = (85, 195, 235)
                else:
                    rem = max(1, dn - dg)
                    prompt_txt = f"Đã tưới ({crop_vi}: còn {rem} ngày chín)"
                    t_col = (175, 240, 255)
                    b_col = (115, 195, 225)
            else:
                yl = max(1, int(getattr(hspot, "yield_left", 1)))
                item_vi = ITEM_NAMES_VI.get(hspot.item_key, hspot.title)
                prompt_txt = f"[E] Thu hoạch {item_vi} (Còn {yl} đợt)"
        else:
            item_vi = ITEM_NAMES_VI.get(hspot.item_key, hspot.title)
            if hspot.has_produce:
                prompt_txt = f"[E] Thu hoạch {item_vi}"
            else:
                prompt_txt = f"{item_vi}: Quả mọc lại sáng mai"
                t_col = (215, 228, 240)
                b_col = (145, 168, 192)

        if prompt_txt:
            lbl = game.font_xs.render(prompt_txt, True, t_col)
            bx = max(8, min(SCREEN_W - lbl.get_width() - 16, int(hspot.x - lbl.get_width() // 2 - 5)))
            by = max(8, int(hspot.y - 38))
            pygame.draw.rect(game.screen, (38, 26, 16), (bx, by, lbl.get_width() + 10, 19), border_radius=5)
            pygame.draw.rect(game.screen, b_col, (bx, by, lbl.get_width() + 10, 19), 1, border_radius=5)
            game.screen.blit(lbl, (bx + 5, by + 2))

    # Biển tên gọn trên mái mọi ngôi nhà + Nhãn nhắc bấm [E] vào nhà (Map 5)
    q_cur = getattr(game, "active_quest", None)
    for prop in game.props:
        if prop.door_rect is not None and prop.title:
            is_target_house = (
                q_cur is not None
                and getattr(q_cur, "status", "") == "accepted"
                and getattr(q_cur, "receiver_map", 0) == 5
                and getattr(q_cur, "receiver_house_id", "") == getattr(prop, "house_id", "")
                and (not getattr(q_cur, "receiver_name", "") or getattr(q_cur, "receiver_name", "") == getattr(prop, "owner_name", ""))
            )
            roof_text = f"[GIAO ĐƠN] {prop.title}" if is_target_house else prop.title
            roof_col = (120, 255, 145) if is_target_house else (255, 240, 200)
            border_col = (95, 245, 130) if is_target_house else (180, 140, 72)
            roof_lbl = game.font_xs.render(roof_text, True, roof_col)
            spr_w = prop.sprite.get_width() if prop.sprite is not None else 96
            rcx = prop.x + spr_w // 2
            rx_box = max(6, min(SCREEN_W - roof_lbl.get_width() - 12, rcx - roof_lbl.get_width() // 2 - 4))
            ry_box = max(4, prop.y - 8)

            roof_bg = pygame.Surface((roof_lbl.get_width() + 8, 16), pygame.SRCALPHA)
            roof_bg.fill((24, 16, 10, 168))
            game.screen.blit(roof_bg, (rx_box, ry_box))
            pygame.draw.rect(
                game.screen,
                border_col,
                (rx_box, ry_box, roof_lbl.get_width() + 8, 16),
                2 if is_target_house else 1,
                border_radius=4,
            )
            game.screen.blit(roof_lbl, (rx_box + 4, ry_box))

            # 2. Nhãn nhắc bấm [E] ngay trước thảm cửa khi Robot đứng gần <= 66px
            if math.hypot(game.robot.x - prop.door_rect.centerx, game.robot.y - prop.door_rect.centery) <= 66.0:
                lbl = game.font_xs.render(f"[E] Vào {prop.title}", True, (255, 242, 165))
                bx = max(8, min(SCREEN_W - lbl.get_width() - 16, prop.door_rect.centerx - lbl.get_width() // 2 - 6))
                by = max(8, prop.door_rect.top - 24)
                pygame.draw.rect(game.screen, (48, 28, 18), (bx, by, lbl.get_width() + 12, 19), border_radius=5)
                pygame.draw.rect(game.screen, (238, 186, 88), (bx, by, lbl.get_width() + 12, 19), 1, border_radius=5)
                game.screen.blit(lbl, (bx + 6, by + 2))

    # Các cổng chuyển tiếp bản đồ (Map Portals)
    for portal in game.portals:
        pulse = int(abs(math.sin(game.sim_time * 4.0)) * 55)
        col = (255, 225, 95, 110 + pulse)
        ov = pygame.Surface((portal.rect.width, portal.rect.height), pygame.SRCALPHA)
        pygame.draw.rect(ov, col, (0, 0, portal.rect.width, portal.rect.height), border_radius=6)
        game.screen.blit(ov, portal.rect.topleft)

        lbl = game.font_xs.render(portal.label, True, (255, 248, 210))
        lx = max(12, min(SCREEN_W - lbl.get_width() - 16, portal.rect.centerx - lbl.get_width() // 2))
        if portal.arrow_dir == "up":
            ly = portal.rect.bottom + 4
        elif portal.arrow_dir == "down":
            ly = portal.rect.top - 22
        else:
            ly = portal.rect.centery - 10
        pygame.draw.rect(game.screen, (38, 24, 14, 220), (lx - 5, ly - 2, lbl.get_width() + 10, 18), border_radius=4)
        game.screen.blit(lbl, (lx, ly))

    # Vẽ nhãn & hiệu ứng Thùng Giao Hàng Nông Trại (Shipping Bin ở Map 2)
    render_shipping_bin_overlay(game.screen, game)

    # Vẽ Trang trí Lễ Hội Hoa Anh Đào tại Quảng Trường Map 1 (nếu đang là ngày lễ hội)
    if getattr(game, "atmosphere", None) is not None and hasattr(game.atmosphere, "render_festival_decor"):
        game.atmosphere.render_festival_decor(game.screen, game)

    # Vẽ Khí quyển, Vòi tưới Sprinkler, Cánh hoa đào / Mưa rào & Ánh sáng Ngày – Đêm Stardew Valley
    if getattr(game, "atmosphere", None) is not None:
        game.atmosphere.render_lighting_and_weather(game.screen, game)


def _render_indoor_scene(game):
    """Vẽ Map 5: Không Gian Nội Thất Trong Nhà — Mỗi ngôi nhà có một thiết kế & tông màu riêng biệt."""
    game.screen.fill((10, 8, 16))
    b = game.current_interior
    is_robot_house = b is not None and getattr(b, "house_id", "") == "robot_house"
    theme = get_interior_theme(b)
    rx, ry, rw, rh = game.room_rect.x, game.room_rect.y, game.room_rect.width, game.room_rect.height

    border_col = theme.get("border_col", (142, 92, 48))
    floor_tint = theme.get("floor_tint", (238, 202, 158))
    wall_tint = theme.get("wall_tint", (250, 232, 198))
    rug_tint = theme.get("rug_tint", (235, 175, 135))

    # Đổ bóng và khung bao quanh phòng
    pygame.draw.rect(game.screen, (26, 18, 14), (rx - 14, ry - 14, rw + 28, rh + 28), border_radius=12)
    pygame.draw.rect(game.screen, border_col, (rx - 8, ry - 8, rw + 16, rh + 16), 5, border_radius=10)

    # Sàn nhà: Xưởng Robot lát gạch thép công nghiệp (rh_floor_tile), các nhà khác lát sàn gỗ nhuộm màu
    if is_robot_house:
        fl_step = 64
        fl = game.vault.scaled("rh_floor_tile", fl_step, fl_step)
        for y in range(ry + 88, ry + rh, fl_step):
            for x in range(rx, rx + rw, fl_step):
                w_clamped = min(fl_step, rx + rw - x)
                h_clamped = min(fl_step, ry + rh - y)
                if fl is not None:
                    game.screen.blit(fl, (x, y), pygame.Rect(0, 0, w_clamped, h_clamped))
                else:
                    pygame.draw.rect(game.screen, floor_tint, (x, y, w_clamped, h_clamped))
    else:
        fl = game.vault.tinted("floor_wood", TILE_SIZE, TILE_SIZE, floor_tint)
        for y in range(ry + 88, ry + rh, TILE_SIZE):
            for x in range(rx, rx + rw, TILE_SIZE):
                w_clamped = min(TILE_SIZE, rx + rw - x)
                h_clamped = min(TILE_SIZE, ry + rh - y)
                if fl is not None:
                    game.screen.blit(fl, (x, y), pygame.Rect(0, 0, w_clamped, h_clamped))
                else:
                    pygame.draw.rect(game.screen, floor_tint, (x, y, w_clamped, h_clamped))

    # Tường hậu cảnh phía Bắc nhuộm màu riêng
    wp = game.vault.tinted("wallpaper", TILE_SIZE, 88, wall_tint)
    for x in range(rx, rx + rw, TILE_SIZE):
        w_clamped = min(TILE_SIZE, rx + rw - x)
        if wp is not None:
            game.screen.blit(wp, (x, ry), pygame.Rect(0, 0, w_clamped, 88))
        else:
            pygame.draw.rect(game.screen, wall_tint, (x, ry, w_clamped, 88))
    pygame.draw.line(game.screen, border_col, (rx, ry + 88), (rx + rw, ry + 88), 4)

    if not is_robot_house:
        # Cửa sổ đón nắng & Thảm dệt trung tâm phòng cho nhà dân
        win = game.vault.scaled("furn_window", 54, 54)
        if win is not None:
            game.screen.blit(win, (rx + int(rw * 0.28) - 27, ry + 16))
            game.screen.blit(win, (rx + int(rw * 0.72) - 27, ry + 16))

        rug = game.vault.tinted("furn_rug", 220, 134, rug_tint)
        if rug is not None:
            game.screen.blit(rug, (rx + rw // 2 - 110, ry + rh // 2 - 20))

    # Đồ nội thất đặc trưng của từng căn nhà
    for fname, fx_rel, fy_rel, fw, fh in theme.get("furniture", []):
        fspr = game.vault.scaled(fname, fw, fh)
        if fspr is not None:
            fx = rx + int(rw * fx_rel) - fw // 2
            fy = ry + int(rh * fy_rel) - fh // 2
            game.screen.blit(fspr, (fx, fy))

    # Vật phẩm trưng bày trên bàn / quầy của từng căn nhà
    for item_key, ix_rel, iy_rel in theme.get("display_items", []):
        ic = game.vault.get_item_icon(item_key, 24)
        ix = rx + int(rw * ix_rel) - 12
        iy = ry + int(rh * iy_rel) - 12
        game.screen.blit(ic, (ix, iy))

    # Thảm cửa ra ngoài (Xưởng Robot dùng thảm mũi tên công nghiệp rh_exit_mat + rh_hazard_mat)
    exit_mat_rect = pygame.Rect(game.room_rect.centerx - 40, ry + rh - 34, 80, 30)
    if is_robot_house:
        haz_spr = game.vault.scaled("rh_hazard_mat", 36, 30)
        exit_spr = game.vault.scaled("rh_exit_mat", 56, 32)
        if haz_spr is not None:
            game.screen.blit(haz_spr, (game.room_rect.centerx - 66, ry + rh - 34))
            game.screen.blit(haz_spr, (game.room_rect.centerx + 30, ry + rh - 34))
        if exit_spr is not None:
            game.screen.blit(exit_spr, (game.room_rect.centerx - 28, ry + rh - 35))
        else:
            pygame.draw.rect(game.screen, (235, 162, 42), exit_mat_rect, border_radius=4)
    else:
        mat_spr = game.vault.scaled("red_mat", 80, 26)
        if mat_spr is not None:
            game.screen.blit(mat_spr, (exit_mat_rect.x, exit_mat_rect.y + 4))
        else:
            pygame.draw.rect(game.screen, (210, 56, 52), exit_mat_rect, border_radius=4)

    exit_lbl = game.font_xs.render("[E] hoặc Đi xuống Cửa Ra [▼] để Ra Ngoài", True, (255, 232, 165))
    game.screen.blit(exit_lbl, (game.room_rect.centerx - exit_lbl.get_width() // 2, ry + rh + 10))

    # Nếu ở trong Xưởng & Nhà Robot: Hiển thị nhãn tương tác cho Trạm Cải Tiến (Trái) & Đế Sạc Ngủ (Phải)
    if is_robot_house:
        pulse = (math.sin(game.sim_time * 4.5) + 1.0) * 0.5
        # 1. Trạm Cánh Tay Cải Tiến & Nâng Cấp Robot (Bên Trái)
        up_x = rx + int(rw * 0.27)
        up_y = ry + int(rh * 0.54)
        dist_up = math.hypot(game.robot.x - up_x, game.robot.y - (up_y + 16))
        up_tag = "[E] / [U] Mở Xưởng Cải Tiến Robot" if dist_up <= 86.0 else "Cánh Tay Nâng Cấp [E]/[U]"
        up_col = (120, 255, 155) if dist_up <= 86.0 else (255, 222, 125)
        up_lbl = game.font_xs.render(up_tag, True, up_col)
        ubx = up_x - up_lbl.get_width() // 2 - 5
        uby = up_y - 84
        ubg = pygame.Surface((up_lbl.get_width() + 10, 18), pygame.SRCALPHA)
        ubg.fill((28, 20, 14, 205))
        game.screen.blit(ubg, (ubx, uby))
        pygame.draw.rect(game.screen, (245, 162, 52), (ubx, uby, up_lbl.get_width() + 10, 18), 1, border_radius=4)
        game.screen.blit(up_lbl, (ubx + 5, uby + 1))

        # 2. Đế Sạc Pin & Ngủ Tia Chớp (Bên Phải)
        dock_x = rx + int(rw * 0.77)
        dock_y = ry + int(rh * 0.56)
        dist_dock = math.hypot(game.robot.x - dock_x, game.robot.y - dock_y)
        bat_val = float(getattr(game.robot, "battery", 100.0))
        glow_surf = pygame.Surface((96, 90), pygame.SRCALPHA)
        glow_col = (95, 255, 195, int(75 + pulse * 85)) if dist_dock <= 78.0 else (65, 215, 255, int(45 + pulse * 55))
        pygame.draw.rect(glow_surf, glow_col, (4, 4, 88, 82), 3, border_radius=12)
        game.screen.blit(glow_surf, (dock_x - 48, dock_y - 45))

        dock_tag = (
            f"[E] / [N] Ngủ & Sạc Đầy 100% Pin (Hiện:{bat_val:.0f}%)"
            if dist_dock <= 78.0
            else f"Đế Sạc & Ngủ [E]/[N] (Pin:{bat_val:.0f}%)"
        )
        dock_col = (115, 255, 195) if dist_dock <= 78.0 else (155, 235, 255)
        dock_lbl = game.font_xs.render(dock_tag, True, dock_col)
        dbx = min(rx + rw - dock_lbl.get_width() - 12, dock_x - dock_lbl.get_width() // 2 - 5)
        dby = dock_y - 68
        dbg = pygame.Surface((dock_lbl.get_width() + 10, 18), pygame.SRCALPHA)
        dbg.fill((16, 28, 38, 210))
        game.screen.blit(dbg, (dbx, dby))
        pygame.draw.rect(game.screen, (85, 225, 235), (dbx, dby, dock_lbl.get_width() + 10, 18), 1, border_radius=4)
        game.screen.blit(dock_lbl, (dbx + 5, dby + 1))

    # Tiêu đề ngôi nhà & Mô tả phong cách nội thất phía trên phòng
    if b is not None:
        house_ic = game.vault.scaled("icon_house", 22, 22)
        title_s = game.font_sm.render(f"{b.title} — Kỹ thuật: {b.owner_name}" if is_robot_house else f"{b.title} — Chủ nhà: {b.owner_name}", True, (255, 238, 175))
        sub_s = game.font_xs.render(theme.get("subtitle", ""), True, (210, 228, 245))
        box_w = max(title_s.get_width() + 42, sub_s.get_width() + 24)
        box_x = SCREEN_W // 2 - box_w // 2
        box_y = ry - 52
        pygame.draw.rect(game.screen, (28, 18, 12), (box_x, box_y, box_w, 40), border_radius=8)
        pygame.draw.rect(game.screen, border_col, (box_x, box_y, box_w, 40), 2, border_radius=8)
        tx = SCREEN_W // 2 - title_s.get_width() // 2 + 10
        if house_ic is not None:
            game.screen.blit(house_ic, (tx - 26, box_y + 3))
        game.screen.blit(title_s, (tx, box_y + 2))
        game.screen.blit(sub_s, (SCREEN_W // 2 - sub_s.get_width() // 2, box_y + 21))

    # Vẽ Quạt Tương Tác Trước Mặt Chủ Nhà
    if game.show_interaction_fan:
        for npc in game.interior_npcs:
            marker = get_npc_quest_marker(game, npc.name)
            draw_npc_interaction_fan(
                game.screen,
                npc,
                game.robot,
                is_quest_target=(marker is not None),
                show_always=True,
            )

    # Sắp xếp Y-sorting giữa Chủ nhà và Robot
    actors = []
    for npc in game.interior_npcs:
        actors.append((npc.sort_y, "npc", npc))
    actors.append((game.robot.sort_y, "robot", game.robot))
    actors.sort(key=lambda item: item[0])

    for _, kind, obj in actors:
        if kind == "npc":
            marker = get_npc_quest_marker(game, obj.name)
            obj.draw(game.screen, game.vault, game.font_xs, game.sim_time, marker)
        else:
            obj.draw(game.screen, game.vault, game.font_xs, game.sim_time)


def _render_charging_dock(game):
    """Vẽ Đế Trạm Sạc Pin & Ngủ (Charging Dock) tại bản đồ ngoài trời."""
    dock = CHARGING_DOCKS.get(int(getattr(game, "current_map_id", 1)), CHARGING_DOCKS[1])
    dx, dy, dock_title = int(dock[0]), int(dock[1]), dock[2]
    dist_px = math.hypot(game.robot.x - dx, game.robot.y - dy)
    pulse = (math.sin(game.sim_time * 4.5) + 1.0) * 0.5

    # 1. Đế kim loại lục giác / elip công nghệ cao kèm vòng năng lượng xanh ngọc
    pad_surf = pygame.Surface((64, 44), pygame.SRCALPHA)
    pygame.draw.ellipse(pad_surf, (28, 38, 48, 225), (2, 6, 60, 34))
    pygame.draw.ellipse(pad_surf, (75, 225, 210, 215), (2, 6, 60, 34), 2)
    inner_col = (95, 255, 185, int(115 + pulse * 95)) if dist_px <= 68.0 else (65, 195, 225, int(80 + pulse * 60))
    pygame.draw.ellipse(pad_surf, inner_col, (12, 12, 40, 22), 2)
    game.screen.blit(pad_surf, (dx - 32, dy - 20))

    # Cột trụ đèn báo trạng thái sạc phía bắc đế Dock
    pillar_rect = pygame.Rect(dx - 8, dy - 30, 16, 16)
    pygame.draw.rect(game.screen, (42, 56, 68), pillar_rect, border_radius=4)
    pygame.draw.rect(game.screen, (115, 245, 225), pillar_rect, 1, border_radius=4)
    led_col = (95, 255, 145) if dist_px <= 68.0 else (85, 225, 255)
    pygame.draw.circle(game.screen, led_col, (dx, dy - 22), 4)

    # 2. Nhãn gọn phía trên Trạm Sạc (hiện hướng dẫn [E]/[N] khi đứng gần hoặc khi Pin yếu < 35%)
    bat_val = float(getattr(game.robot, "battery", 100.0))
    if dist_px <= 78.0:
        tag = f"[E] Sạc 100% | [N] Ngủ tại {dock_title} (Pin:{bat_val:.0f}%)"
        t_col = (120, 255, 185)
    elif dist_px <= 145.0 or bat_val < 35.0:
        tag = f"[Dock Sạc & Ngủ] ({bat_val:.0f}%)"
        t_col = (145, 235, 255)
    else:
        tag = "Dock Sạc [N]"
        t_col = (195, 235, 245)

    lbl = game.font_xs.render(tag, True, t_col)
    bx = max(6, min(SCREEN_W - lbl.get_width() - 12, dx - lbl.get_width() // 2 - 4))
    by = max(6, dy - 48)
    bg = pygame.Surface((lbl.get_width() + 8, 16), pygame.SRCALPHA)
    bg.fill((18, 28, 36, 182))
    game.screen.blit(bg, (bx, by))
    pygame.draw.rect(game.screen, (85, 215, 215), (bx, by, lbl.get_width() + 8, 16), 1, border_radius=4)
    game.screen.blit(lbl, (bx + 4, by))


def _draw_panel_box(screen: pygame.Surface, vault, rect: pygame.Rect, border_col=(215, 162, 78)):
    """Vẽ khung bảng HUD bán trong suốt gọn nhẹ để không che khuất tầm nhìn bản đồ."""
    bg = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
    pygame.draw.rect(bg, (30, 18, 12, 192), (0, 0, rect.width, rect.height), border_radius=8)
    screen.blit(bg, rect.topleft)
    pygame.draw.rect(screen, border_col, rect, 1, border_radius=8)


def _render_hud(game):
    """Vẽ Bảng điều khiển HUD tối giản (Minimal HUD), giải phóng tối đa diện tích hiển thị bản đồ."""
    # ------------------------------------------------------------------
    # 1. Góc trên trái: Thanh trạng thái 2 dòng siêu gọn (272 x 46)
    #    Chỉ mở rộng dòng thứ 3 khi Robot thực sự đứng gần NPC (<= 1.95m)
    # ------------------------------------------------------------------
    active_npcs = (
        game.interior_npcs
        if game.in_interior
        else [n for n in game.npcs if not getattr(n, "is_home_at_night", False)]
    )
    nearest_npc = None
    nearest_d = 999.0
    for npc in active_npcs:
        dm = px_to_m(math.hypot(game.robot.x - npc.x, game.robot.y - npc.y))
        if dm < nearest_d:
            nearest_d = dm
            nearest_npc = npc

    show_fan_check = nearest_npc is not None and nearest_d <= 1.95
    panel_l_w = 276
    panel_l_h = 64 if show_fan_check else 46
    panel_l = pygame.Rect(8, 6, panel_l_w, panel_l_h)
    _draw_panel_box(game.screen, game.vault, panel_l)

    heart_spr = game.vault.scaled("icon_heart", 16, 15)
    for i in range(game.max_hearts):
        hx = 16 + i * 19
        hy = 11
        if i < game.hearts:
            if heart_spr is not None:
                game.screen.blit(heart_spr, (hx, hy))
            else:
                pygame.draw.circle(game.screen, (235, 52, 64), (hx + 7, hy + 7), 6)
        else:
            pygame.draw.circle(game.screen, (78, 56, 48), (hx + 7, hy + 7), 6)
            pygame.draw.circle(game.screen, (145, 112, 92), (hx + 7, hy + 7), 6, 1)

    comfort_val = max(0.0, min(100.0, float(getattr(game, "comfort_score", 100.0))))
    c_bar_col = (95, 238, 142) if comfort_val >= 70.0 else ((255, 210, 75) if comfort_val >= 35.0 else (255, 92, 82))
    bat_val = max(0.0, min(100.0, float(getattr(game.robot, "battery", 100.0))))
    bat_tag = f"Pin:{bat_val:.0f}%+" if getattr(game.robot, "is_charging", False) else f"Pin:{bat_val:.0f}%"
    cert_lvl = getattr(getattr(game, "state", None), "certification_level", 0)
    rank_letter = game.get_rank_letter()[0].split(" ")[0]
    cert_str = f"CC-{cert_lvl}" if cert_lvl > 0 else f"Hạng {rank_letter}"
    c_lbl = game.font_xs.render(f"An tâm {comfort_val:.0f}% | {bat_tag} | {cert_str}", True, c_bar_col)
    game.screen.blit(c_lbl, (76, 9))

    gold_val = getattr(game, "gold", 0)
    mode_tag = "CHẬM" if game.robot.is_slow_active else "THƯỜNG"
    agv_tag = " | AGV[C]" if getattr(getattr(game, "state", None), "agv_companion_active", False) else ""
    line2_str = f"{game.score}đ | {gold_val}G | {game.robot.v_mps:.1f}m/s [{mode_tag}]{agv_tag}"
    line2_col = (95, 235, 255) if game.robot.is_slow_active else (255, 235, 115)
    game.screen.blit(game.font_xs.render(line2_str, True, line2_col), (16, 28))

    if show_fan_check and nearest_npc is not None:
        ok, checks = check_front_interaction(game.robot, nearest_npc)
        c1 = "OK" if checks["dist_ok"] else "X"
        c2 = "OK" if checks["in_front_ok"] else "X"
        c3 = "OK" if checks["facing_npc_ok"] else "X"
        c4 = "OK" if checks["stopped_ok"] else "X"
        chk_col = (92, 245, 130) if ok else (255, 204, 108)
        chk_raw = f"Quạt Xanh ({nearest_d:.1f}m): Trước[{c2}] Cự ly[{c1}] Nhìn[{c3}] Dừng[{c4}]"
        game.screen.blit(game.font_xs.render(chk_raw, True, chk_col), (16, 45))

    # Vẽ Bản đồ thu nhỏ Radar Minimap [M] ngay dưới bảng trạng thái trái (chỉ khi người chơi bật [M])
    if getattr(game, "schedules", None) is not None:
        game.schedules.render_minimap(game.screen, game, top_y=panel_l.bottom + 4)

    # ------------------------------------------------------------------
    # 2. Góc trên phải: Đồng Hồ & Mục Tiêu Nhiệm Vụ Gọn (316 x 46)
    # ------------------------------------------------------------------
    q = game.active_quest
    if q.status == "available":
        q_step = f"NV{game.quest_idx + 1}: Tới Map {q.giver_map} gặp {q.giver_name} nhận đơn [E]"
        s_col = (255, 215, 95)
    elif q.status == "completed":
        q_step = f"NV{game.quest_idx + 1}: Đã hoàn thành! Bấm [TAB] chuyển đơn khác"
        s_col = (145, 248, 165)
    elif q.Item_in_inventory(game.robot.inventory):
        q_step = f"NV{game.quest_idx + 1}: Giao [{q.item_label}] -> {q.receiver_name} ({q.receiver_place})"
        s_col = (98, 245, 132)
    else:
        q_step = f"NV{game.quest_idx + 1}: {q.source_hint}"
        s_col = (135, 225, 255)

    panel_r_w = 324
    q_lines = wrap_text(game.font_xs, q_step, panel_r_w - 18)[:2]
    panel_r_h = 28 + len(q_lines) * 16
    panel_r = pygame.Rect(SCREEN_W - panel_r_w - 8, 6, panel_r_w, panel_r_h)
    _draw_panel_box(game.screen, game.vault, panel_r)

    if getattr(game, "atmosphere", None) is not None:
        clock_str = game.atmosphere.get_clock_string(game.sim_time)
    else:
        minutes_total = int(7 * 60 + (game.sim_time * 4.0) % (24 * 60))
        clock_str = f"{(minutes_total // 60) % 24:02d}:{(minutes_total % 60 // 10) * 10:02d}"
    map_label = MAP_TITLES[5] if game.in_interior else MAP_TITLES[game.current_map_id]
    short_map = map_label.split(":")[0] if ":" in map_label else map_label
    day_num = getattr(getattr(game, "state", None), "day", 1)
    season_vi = getattr(getattr(game, "atmosphere", None), "current_season_name", "Xuân")
    hdr_r = game.font_xs.render(
        f"Ngày {day_num} [{season_vi}] {clock_str} | {short_map} | Đã giao:{game.completed_quests_count} | [H]HD",
        True,
        (255, 228, 145),
    )
    game.screen.blit(hdr_r, (panel_r.x + 8, panel_r.y + 6))
    game._tutorial_top_y = panel_r.bottom + 4

    for idx_l, line in enumerate(q_lines):
        game.screen.blit(game.font_xs.render(line, True, s_col), (panel_r.x + 8, panel_r.y + 24 + idx_l * 16))

    # ------------------------------------------------------------------
    # 3. Khung Thông Báo Giữa Màn Hình: Thanh Pill 1 dòng gọn nhẹ (tự ẩn sau 3s)
    # ------------------------------------------------------------------
    if game.banner_timer > 0.0 and game.banner_text:
        is_warn = (
            "CẢNH BÁO" in game.banner_text
            or "VI PHẠM" in game.banner_text
            or "quá sát" in game.banner_text
            or "đang bị choáng" in game.banner_text
        )
        gap_left = panel_l.right + 6
        gap_right = panel_r.left - 6
        max_banner_w = max(220, gap_right - gap_left)
        b_lines = wrap_text(game.font_xs, game.banner_text, max_banner_w - 16)[:2]
        line_h = 15
        bh = len(b_lines) * line_h + 8
        bw = min(max_banner_w, max((game.font_xs.size(l)[0] for l in b_lines), default=180) + 20)
        bx = gap_left + (max_banner_w - bw) // 2
        by = 6

        b_rect = pygame.Rect(bx, by, bw, bh)
        bg = pygame.Surface((bw, bh), pygame.SRCALPHA)
        bg_col = (64, 18, 18, 205) if is_warn else (28, 18, 12, 195)
        pygame.draw.rect(bg, bg_col, (0, 0, bw, bh), border_radius=6)
        game.screen.blit(bg, (bx, by))
        pygame.draw.rect(game.screen, game.banner_color, b_rect, 1, border_radius=6)

        for i, line in enumerate(b_lines):
            lsurf = game.font_xs.render(line, True, game.banner_color)
            game.screen.blit(lsurf, (bx + (bw - lsurf.get_width()) // 2, by + 3 + i * line_h))

    # ------------------------------------------------------------------
    # 4. Thanh Dưới Cùng: Khay Chứa Đồ Gọn (246 x 34) + Túi Hạt [Q] + Các Nút Bấm Nhanh (h = 26)
    # ------------------------------------------------------------------
    farming = getattr(game, "farming", None)
    if farming is not None:
        sel_seed = getattr(farming, "selected_seed", "wheat")
        s_bag = getattr(farming, "seed_bag", {})
        eq_bag = getattr(farming, "equip_bag", {})
        if sel_seed in EQUIP_CATALOG and int(eq_bag.get(sel_seed, 0)) > 0:
            eq_name = EQUIP_CATALOG[sel_seed]["short_vi"]
            seed_str = f"Thiết bị [Q]: {eq_name} x{int(eq_bag[sel_seed])}"
            seed_col = (145, 255, 225)
        else:
            s_cnt = int(s_bag.get(sel_key := sel_seed, 0))
            if s_cnt <= 0:
                for k in CROP_CATALOG:
                    if int(s_bag.get(k, 0)) > 0:
                        sel_key = k
                        s_cnt = int(s_bag[k])
                        break
            if s_cnt > 0:
                s_name = CROP_CATALOG.get(sel_key, {}).get("name_vi", sel_key)
                seed_str = f"Hạt [Q]: {s_name} x{s_cnt}"
                seed_col = (155, 255, 175)
            else:
                seed_str = f"Hạt [Q]: Hết hạt (Mua ở {SEED_VENDOR_NAME})"
                seed_col = (245, 205, 125)
        seed_lbl = game.font_xs.render(seed_str, True, seed_col)
        seed_box = pygame.Rect(8, SCREEN_H - 58, seed_lbl.get_width() + 14, 18)
        _draw_panel_box(game.screen, game.vault, seed_box, border_col=(145, 195, 108))
        game.screen.blit(seed_lbl, (seed_box.x + 7, seed_box.y + 1))

    max_slots = max(4, getattr(game.robot, "max_inventory", 4))
    inv_panel = pygame.Rect(8, SCREEN_H - 38, 248, 32)
    _draw_panel_box(game.screen, game.vault, inv_panel)

    inv_lbl = game.font_xs.render(f"Khay({max_slots}):", True, (255, 238, 195))
    game.screen.blit(inv_lbl, (14, SCREEN_H - 30))

    slot_step = 30 if max_slots > 4 else 38
    slot_w = 26 if max_slots > 4 else 32
    start_sx = 72 if max_slots > 4 else 80
    sel_slot = getattr(game, "selected_slot", 0)
    if getattr(game, "state", None) is not None:
        game.state.sync_slot_meta_with_inventory(game.robot.inventory)
    for idx in range(max_slots):
        sx = start_sx + idx * slot_step
        sy = SCREEN_H - 35
        slot_r = pygame.Rect(sx, sy, slot_w, 26)
        is_sel = idx == sel_slot
        pygame.draw.rect(game.screen, (88, 60, 34) if is_sel else (62, 40, 24), slot_r, border_radius=5)
        pygame.draw.rect(
            game.screen,
            (255, 232, 85) if is_sel else (165, 120, 68),
            slot_r,
            2 if is_sel else 1,
            border_radius=5,
        )
        if idx < len(game.robot.inventory):
            item_key = game.robot.inventory[idx]
            icon = game.vault.get_item_icon(item_key, 20)
            game.screen.blit(icon, (sx + (slot_w - 20) // 2, sy + 3))
            if getattr(game, "state", None) is not None and idx < len(game.state.slot_meta):
                s_meta = game.state.slot_meta[idx]
                if s_meta.quality > 0:
                    pygame.draw.circle(
                        game.screen,
                        s_meta.quality_color,
                        (slot_r.right - 5, slot_r.bottom - 5),
                        3,
                    )

    # Vẽ các nút điều khiển nhanh nhỏ gọn
    mouse_pos = pygame.mouse.get_pos()
    for btn in game.hud_buttons:
        r: pygame.Rect = btn["rect"]
        bid = btn["id"]
        active = False
        if bid == "slow" and game.robot.is_slow_active:
            active = True
        elif bid == "agv_call" and getattr(getattr(game, "state", None), "agv_companion_active", False):
            active = True
        elif bid == "auto" and game.autopilot_enabled:
            active = True
        elif bid == "workshop" and getattr(game, "workshop", None) is not None and game.workshop.open:
            active = True
        elif bid == "journal" and getattr(game, "journal", None) is not None and game.journal.open:
            active = True
        elif bid == "minimap" and getattr(game, "schedules", None) is not None and game.schedules.show_minimap:
            active = True
        elif bid == "interact":
            active = True

        hovered = r.collidepoint(mouse_pos)
        if bid == "interact":
            bg = (42, 148, 78) if not hovered else (58, 178, 98)
            bd = (165, 255, 185)
        elif bid == "reset":
            bg = (138, 48, 42) if not hovered else (168, 64, 56)
            bd = (255, 185, 165)
        elif active:
            bg = (78, 128, 58)
            bd = (245, 215, 95)
        elif hovered:
            bg = (76, 52, 34)
            bd = (235, 195, 115)
        else:
            bg = (46, 30, 18)
            bd = (155, 115, 62)

        pygame.draw.rect(game.screen, bg, r, border_radius=5)
        pygame.draw.rect(game.screen, bd, r, 1, border_radius=5)
        lbl = game.font_xs.render(btn["label"], True, (255, 248, 225))
        game.screen.blit(lbl, (r.centerx - lbl.get_width() // 2, r.centery - lbl.get_height() // 2))

    # Thanh thông báo Sự Kiện Động (Random World Events - Phím [O])
    if getattr(game, "random_events", None) is not None:
        game.random_events.render_event_hud(game.screen, game)

    # Nháy đỏ cảnh báo va chạm
    if game.emergency_flash_timer > 0.0:
        alpha = int(min(1.0, game.emergency_flash_timer) * 105)
        red_ov = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
        red_ov.fill((225, 28, 28, alpha))
        game.screen.blit(red_ov, (0, 0))


def _render_game_over_modal(game):
    """Màn hình tổng kết khi Vi phạm An toàn Nghiêm trọng (Tự động ngắt dòng chống tràn chữ)."""
    ov = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
    ov.fill((12, 8, 14, 215))
    game.screen.blit(ov, (0, 0))

    mw, mh = 660, 350
    mx, my = SCREEN_W // 2 - mw // 2, SCREEN_H // 2 - mh // 2
    modal = pygame.Rect(mx, my, mw, mh)
    pygame.draw.rect(game.screen, (48, 24, 22), modal, border_radius=14)
    pygame.draw.rect(game.screen, (245, 92, 82), modal, 4, border_radius=14)

    warn_ic = game.vault.scaled("icon_warning", 34, 34)
    t1 = game.font_lg.render("DỪNG KHẨN CẤP — GAME OVER", True, (255, 112, 98))
    tx = SCREEN_W // 2 - t1.get_width() // 2
    if warn_ic is not None:
        game.screen.blit(warn_ic, (tx - 42, my + 22))
        game.screen.blit(warn_ic, (tx + t1.get_width() + 8, my + 22))
    game.screen.blit(t1, (tx, my + 24))

    # Tự động ngắt dòng lý do Game Over để không bao giờ tràn khỏi hộp thoại
    reason_lines = wrap_text(game.font_sm, game.game_over_reason, mw - 48)
    cur_y = my + 74
    for rline in reason_lines:
        rs = game.font_sm.render(rline, True, (255, 238, 215))
        game.screen.blit(rs, (SCREEN_W // 2 - rs.get_width() // 2, cur_y))
        cur_y += 24

    rank, r_col = game.get_rank_letter()
    stats = [
        f"Điểm tổng kết: {game.score} điểm   |   Xếp hạng: {rank}",
        f"Số đơn hàng hoàn thành: {game.completed_quests_count} đơn",
        f"Số lần va quệt làm ngã cư dân (Knockdown): {game.total_knockdowns} lần",
    ]
    cur_y = max(cur_y + 12, my + 150)
    for i, line in enumerate(stats):
        s = game.font_sm.render(line, True, r_col if i == 0 else (235, 225, 205))
        game.screen.blit(s, (SCREEN_W // 2 - s.get_width() // 2, cur_y + i * 28))

    btn_rect = pygame.Rect(SCREEN_W // 2 - 210, my + mh - 62, 420, 42)
    pygame.draw.rect(game.screen, (62, 138, 68), btn_rect, border_radius=8)
    pygame.draw.rect(game.screen, (255, 238, 95), btn_rect, 2, border_radius=8)
    restart_lbl = game.font_sm.render(
        "Bấm phím [R] hoặc Click vào đây để Chơi Lại",
        True,
        (255, 250, 220),
    )
    game.screen.blit(
        restart_lbl,
        (btn_rect.centerx - restart_lbl.get_width() // 2, btn_rect.centery - restart_lbl.get_height() // 2),
    )
