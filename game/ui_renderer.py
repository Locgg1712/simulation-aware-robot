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
    """Khởi tạo các nút điều khiển nhanh ở thanh dưới màn hình (hỗ trợ cả bấm chuột lẫn phím tắt)."""
    y = SCREEN_H - 44
    specs = [
        ("interact", "[E] Tương Tác", 308, 86),
        ("gift", "[G] Quà", 397, 56),
        ("map1", "M1", 456, 32),
        ("map2", "M2", 491, 32),
        ("map3", "M3", 526, 32),
        ("map4", "M4", 561, 32),
        ("slow", "[X] Chậm", 596, 64),
        ("auto", "[P] AI", 663, 50),
        ("workshop", "[U] Xưởng", 716, 68),
        ("journal", "[J] Sổ Tay", 787, 70),
        ("weather", "[V/K] Mùa", 860, 68),
        ("sleep", "[N] Ngủ", 931, 58),
        ("minimap", "[M] Radar", 992, 68),
        ("reset", "[R] Lại", 1063, 80),
    ]
    buttons = []
    for btn_id, label, x, w in specs:
        buttons.append(
            {
                "id": btn_id,
                "label": label,
                "rect": pygame.Rect(x, y, w, 32),
            }
        )
    return buttons


def get_npc_quest_marker(game, npc_name: str) -> str | None:
    """Trả về dấu '!' (Giao việc) hoặc '?' (Trả hàng) trên đầu NPC."""
    q = game.active_quest
    if q.status == "available" and q.giver_name == npc_name:
        return "!"
    if q.status == "accepted" and q.receiver_name == npc_name:
        return "?"
    for other_q in game.quests:
        if other_q.status == "available" and other_q.giver_name == npc_name:
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

    watered = game.vault.scaled("crops/soil/watered_soil", TILE_SIZE, TILE_SIZE)
    stage_idx = hspot.growth_stage
    stage_name = f"stage_{stage_idx:02d}"
    crop_spr = game.vault.scaled(f"crops/{hspot.crop_name}/{stage_name}", 26, 30)

    cols = max(1, rect.width // TILE_SIZE)
    rows = max(1, rect.height // TILE_SIZE)
    for r in range(rows):
        for c in range(cols):
            tx = rect.x + c * TILE_SIZE
            ty = rect.y + r * TILE_SIZE
            if hspot.has_produce and watered is not None and (r + c) % 2 == 0:
                game.screen.blit(watered, (tx, ty))
            if crop_spr is not None:
                bob = int(math.sin(game.sim_time * 3.0 + c * 0.7 + r * 0.5) * 1.5) if hspot.has_produce else 0
                game.screen.blit(crop_spr, (tx + 3, ty - 2 + bob))

    # Biểu tượng báo hiệu ruộng chín có thể thu hoạch ở mép ruộng
    if hspot.has_produce and hspot in game.harvest_spots:
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
            agv_obj.draw(game.screen, game.vault)
        elif kind == "npc":
            npc_obj: VillagerNPC = obj
            marker = get_npc_quest_marker(game, npc_obj.name)
            npc_obj.draw(game.screen, game.vault, game.font_xs, game.sim_time, marker)
        elif kind == "robot":
            rob_obj: RobotPlayer = obj
            rob_obj.draw(game.screen, game.vault, game.font_xs, game.sim_time)

    # Nhãn nhắc bấm [E] trước cây ăn quả / thửa ruộng nông sản
    for hspot in game.harvest_spots:
        if hspot.has_produce and distance_to_harvest_spot(game.robot.x, game.robot.y, hspot) <= 74.0:
            lbl = game.font_xs.render(
                f"[E] Thu hoạch {ITEM_NAMES_VI.get(hspot.item_key, hspot.title)}",
                True,
                (255, 245, 150),
            )
            bx = max(8, min(SCREEN_W - lbl.get_width() - 16, int(hspot.x - lbl.get_width() // 2 - 5)))
            by = max(8, int(hspot.y - 38))
            pygame.draw.rect(game.screen, (38, 26, 16), (bx, by, lbl.get_width() + 10, 19), border_radius=5)
            pygame.draw.rect(game.screen, (240, 200, 88), (bx, by, lbl.get_width() + 10, 19), 1, border_radius=5)
            game.screen.blit(lbl, (bx + 5, by + 2))

    # Nhãn nhắc bấm [E] vào nhà (Map 5)
    for prop in game.props:
        if prop.door_rect is not None:
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
    theme = get_interior_theme(b)
    rx, ry, rw, rh = game.room_rect.x, game.room_rect.y, game.room_rect.width, game.room_rect.height

    border_col = theme.get("border_col", (142, 92, 48))
    floor_tint = theme.get("floor_tint", (238, 202, 158))
    wall_tint = theme.get("wall_tint", (250, 232, 198))
    rug_tint = theme.get("rug_tint", (235, 175, 135))

    # Đổ bóng và khung gỗ bao quanh phòng
    pygame.draw.rect(game.screen, (26, 18, 14), (rx - 14, ry - 14, rw + 28, rh + 28), border_radius=12)
    pygame.draw.rect(game.screen, border_col, (rx - 8, ry - 8, rw + 16, rh + 16), 5, border_radius=10)

    # Sàn gỗ được nhuộm màu riêng theo từng căn nhà
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

    # Cửa sổ đón nắng
    win = game.vault.scaled("furn_window", 54, 54)
    if win is not None:
        game.screen.blit(win, (rx + int(rw * 0.28) - 27, ry + 16))
        game.screen.blit(win, (rx + int(rw * 0.72) - 27, ry + 16))

    # Thảm dệt trung tâm phòng theo tông màu chủ nhà
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

    # Thảm đỏ cửa ra ngoài
    exit_mat_rect = pygame.Rect(game.room_rect.centerx - 40, ry + rh - 30, 80, 26)
    mat_spr = game.vault.scaled("red_mat", 80, 26)
    if mat_spr is not None:
        game.screen.blit(mat_spr, exit_mat_rect.topleft)
    else:
        pygame.draw.rect(game.screen, (210, 56, 52), exit_mat_rect, border_radius=4)

    exit_lbl = game.font_xs.render("[E] hoặc Đi xuống Thảm Đỏ để Ra Ngoài", True, (255, 232, 165))
    game.screen.blit(exit_lbl, (game.room_rect.centerx - exit_lbl.get_width() // 2, ry + rh + 12))

    # Tiêu đề ngôi nhà & Mô tả phong cách nội thất phía trên phòng
    if b is not None:
        house_ic = game.vault.scaled("icon_house", 22, 22)
        title_s = game.font_sm.render(f"{b.title} — Chủ nhà: {b.owner_name}", True, (255, 238, 175))
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


def _draw_panel_box(screen: pygame.Surface, vault, rect: pygame.Rect, border_col=(215, 162, 78)):
    """Vẽ khung bảng HUD có nền tối rõ chữ và viền vàng ấm."""
    bg = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
    pygame.draw.rect(bg, (36, 22, 14, 232), (0, 0, rect.width, rect.height), border_radius=10)
    screen.blit(bg, rect.topleft)
    pygame.draw.rect(screen, border_col, rect, 2, border_radius=10)


def _render_hud(game):
    """Vẽ Bảng điều khiển HUD chuẩn Stardew Valley, tự động co giãn & xuống dòng chống tràn chữ."""
    # ------------------------------------------------------------------
    # 1. Góc trên trái: 3 Trái Tim Uy Tín + Điểm Số + Vận tốc + Checklist Quạt Xanh
    # ------------------------------------------------------------------
    active_npcs = game.interior_npcs if game.in_interior else game.npcs
    nearest_npc = None
    nearest_d = 999.0
    for npc in active_npcs:
        dm = px_to_m(math.hypot(game.robot.x - npc.x, game.robot.y - npc.y))
        if dm < nearest_d:
            nearest_d = dm
            nearest_npc = npc

    if nearest_npc is not None and nearest_d <= 2.6:
        ok, checks = check_front_interaction(game.robot, nearest_npc)
        c1 = "OK" if checks["dist_ok"] else "X"
        c2 = "OK" if checks["in_front_ok"] else "X"
        c3 = "OK" if checks["facing_npc_ok"] else "X"
        c4 = "OK" if checks["stopped_ok"] else "X"
        chk_col = (92, 245, 130) if ok else (255, 204, 108)
        chk_raw = f"Gần {nearest_npc.name} ({nearest_d:.2f}m): Trước mặt[{c2}] Cự ly[{c1}] Nhìn[{c3}] Dừng[{c4}]"
    else:
        chk_col = (218, 206, 182)
        chk_raw = "Mẹo: Đứng vào Quạt Xanh trước mặt NPC rồi bấm [E]"

    chk_lines = wrap_text(game.font_xs, chk_raw, 336)
    panel_l_h = 84 + len(chk_lines) * 17
    panel_l = pygame.Rect(10, 8, 360, panel_l_h)
    _draw_panel_box(game.screen, game.vault, panel_l)

    heart_spr = game.vault.scaled("icon_heart", 22, 20)
    lbl_hp = game.font_xs.render("Uy Tín An Toàn:", True, (255, 242, 210))
    game.screen.blit(lbl_hp, (22, 16))
    for i in range(game.max_hearts):
        hx = 132 + i * 26
        hy = 14
        if i < game.hearts:
            if heart_spr is not None:
                game.screen.blit(heart_spr, (hx, hy))
            else:
                pygame.draw.circle(game.screen, (235, 52, 64), (hx + 10, hy + 10), 9)
        else:
            pygame.draw.circle(game.screen, (78, 56, 48), (hx + 10, hy + 10), 8)
            pygame.draw.circle(game.screen, (145, 112, 92), (hx + 10, hy + 10), 8, 2)

    coin_spr = game.vault.scaled("icon_coin", 18, 18)
    if coin_spr is not None:
        game.screen.blit(coin_spr, (22, 40))
    rank, rank_col = game.get_rank_letter()
    gold_val = getattr(game, "gold", 0)
    score_txt = game.font_sm.render(f"{game.score}đ  |  {gold_val}G", True, (255, 235, 95))
    rank_txt = game.font_xs.render(f"Hạng: {rank}", True, rank_col)
    game.screen.blit(score_txt, (44, 38))
    game.screen.blit(rank_txt, (202, 41))

    mode_badge = "ĐI CHẬM (0.3m/s)" if game.robot.is_slow_active else "BÌNH THƯỜNG"
    mode_col = (95, 235, 255) if game.robot.is_slow_active else (185, 235, 155)
    spd_txt = game.font_xs.render(
        f"Vận tốc: {game.robot.v_mps:.2f} m/s  |  Chế độ: {mode_badge}",
        True,
        mode_col,
    )
    game.screen.blit(spd_txt, (22, 62))

    for i, line in enumerate(chk_lines):
        game.screen.blit(game.font_xs.render(line, True, chk_col), (22, 82 + i * 17))

    # Vẽ Bản đồ thu nhỏ Radar Minimap (Mục 8.1) ngay dưới bảng Uy Tín An Toàn
    if getattr(game, "schedules", None) is not None:
        game.schedules.render_minimap(game.screen, game, top_y=panel_l.bottom + 6)

    # ------------------------------------------------------------------
    # 2. Góc trên phải: Đồng Hồ, Bản đồ & Nhiệm vụ Đang Làm (Quest Tracker tự xuống dòng)
    # ------------------------------------------------------------------
    q = game.active_quest
    if q.status == "available":
        step1 = f"Bước 1: Tới Map {q.giver_map} gặp {q.giver_name} bấm [E] nhận việc (+20đ)"
        step2 = f"Mục tiêu: Giao {q.item_label} tới {q.receiver_place}"
        s_col = (255, 215, 95)
    elif q.Item_in_inventory(game.robot.inventory):
        step1 = f"Đã có [{q.item_label}] trong Khay Chứa Đồ!"
        step2 = f"Bước 3: Tới {q.receiver_place} gặp {q.receiver_name} bấm [E] giao hàng"
        s_col = (98, 245, 132)
    else:
        step1 = f"Bước 2: {q.source_hint}"
        step2 = f"Sau đó giao cho {q.receiver_name} tại {q.receiver_place}"
        s_col = (135, 225, 255)

    panel_r_w = 396
    max_txt_w = panel_r_w - 24
    wrapped_s1 = wrap_text(game.font_xs, step1, max_txt_w)
    wrapped_s2 = wrap_text(game.font_xs, step2, max_txt_w)

    panel_r_h = 74 + (len(wrapped_s1) + len(wrapped_s2)) * 17
    panel_r = pygame.Rect(SCREEN_W - panel_r_w - 10, 8, panel_r_w, panel_r_h)
    _draw_panel_box(game.screen, game.vault, panel_r)

    minutes_total = int(7 * 60 + (game.sim_time * 4.0) % (15 * 60))
    hh = minutes_total // 60
    mm = (minutes_total % 60 // 10) * 10
    map_label = MAP_TITLES[5] if game.in_interior else MAP_TITLES[game.current_map_id]
    short_map = map_label.split(":")[0] if ":" in map_label else map_label
    day_num = getattr(getattr(game, "state", None), "day", 1)
    season_vi = getattr(getattr(game, "atmosphere", None), "current_season_name", "Xuân")
    weather_tag = ""
    if getattr(game, "atmosphere", None) is not None:
        w_mode = game.atmosphere.current_weather
        weather_tag = "/Hoa" if w_mode == "sunny_petals" else ("/Nắng" if w_mode == "clear" else "/Mưa")
    clk_ic = game.vault.scaled("icon_clock", 16, 16)
    if clk_ic is not None:
        game.screen.blit(clk_ic, (panel_r.x + 12, panel_r.y + 10))
    hdr_r = game.font_xs.render(
        f"Ngày {day_num} [{season_vi}{weather_tag}] {hh:02d}:{mm:02d} | {short_map}",
        True,
        (255, 228, 145),
    )
    game.screen.blit(hdr_r, (panel_r.x + 32, panel_r.y + 9))
    game._tutorial_top_y = panel_r.bottom + 6

    q_title = game.font_sm.render(f"{q.title} ({game.quest_idx + 1}/{len(game.quests)})", True, (255, 246, 200))
    game.screen.blit(q_title, (panel_r.x + 12, panel_r.y + 29))

    cur_y = panel_r.y + 52
    for line in wrapped_s1:
        game.screen.blit(game.font_xs.render(line, True, s_col), (panel_r.x + 12, cur_y))
        cur_y += 17
    for line in wrapped_s2:
        game.screen.blit(game.font_xs.render(line, True, (230, 222, 205)), (panel_r.x + 12, cur_y))
        cur_y += 17

    if q.status == "accepted" and q.bonus_time_limit > 0:
        t_col = (95, 245, 135) if q.bonus_timer > 15.0 else (255, 115, 95)
        timer_str = f"Thưởng Giao Nhanh (+50đ): còn {q.bonus_timer:.0f}s  |  Đã xong: {game.completed_quests_count} đơn"
    else:
        timer_str = f"Đã hoàn thành: {game.completed_quests_count} đơn  |  [TAB]: Đổi nhiệm vụ"
        t_col = (205, 195, 170)
    game.screen.blit(game.font_xs.render(timer_str, True, t_col), (panel_r.x + 12, cur_y + 2))

    # ------------------------------------------------------------------
    # 3. Khung Thông Báo / Cảnh Báo Chính Giữa (Nằm gọn giữa 2 bảng trái-phải, tự ngắt dòng)
    # ------------------------------------------------------------------
    if game.banner_timer > 0.0 and game.banner_text:
        is_warn = (
            "CẢNH BÁO" in game.banner_text
            or "VI PHẠM" in game.banner_text
            or "quá sát" in game.banner_text
            or "đang bị choáng" in game.banner_text
        )
        gap_left = panel_l.right + 8
        gap_right = panel_r.left - 8
        max_banner_w = max(260, gap_right - gap_left)
        b_lines = wrap_text(game.font_xs, game.banner_text, max_banner_w - (40 if is_warn else 20))
        line_h = 17
        bh = max(32, len(b_lines) * line_h + 12)
        bw = max_banner_w
        bx = gap_left
        by = 8

        b_rect = pygame.Rect(bx, by, bw, bh)
        bg = pygame.Surface((bw, bh), pygame.SRCALPHA)
        bg_col = (64, 18, 18, 238) if is_warn else (36, 22, 14, 235)
        pygame.draw.rect(bg, bg_col, (0, 0, bw, bh), border_radius=9)
        game.screen.blit(bg, (bx, by))
        pygame.draw.rect(game.screen, game.banner_color, b_rect, 2, border_radius=9)

        text_x = bx + 12
        if is_warn:
            warn_ic = game.vault.scaled("icon_warning", 20, 20)
            if warn_ic is not None:
                game.screen.blit(warn_ic, (bx + 8, by + (bh - 20) // 2))
                text_x = bx + 34

        for i, line in enumerate(b_lines):
            lsurf = game.font_xs.render(line, True, game.banner_color)
            game.screen.blit(lsurf, (text_x, by + 6 + i * line_h))

    # ------------------------------------------------------------------
    # 4. Thanh Dưới Cùng: Khay Chứa Đồ (4 hoặc 6 Ô) + Các Nút Bấm Nhanh
    # ------------------------------------------------------------------
    max_slots = max(4, getattr(game.robot, "max_inventory", 4))
    inv_panel = pygame.Rect(10, SCREEN_H - 52, 296, 44)
    _draw_panel_box(game.screen, game.vault, inv_panel)

    inv_lbl = game.font_xs.render(f"Khay ({max_slots}):", True, (255, 238, 195))
    game.screen.blit(inv_lbl, (16, SCREEN_H - 38))

    slot_step = 36 if max_slots > 4 else 46
    slot_w = 32 if max_slots > 4 else 40
    start_sx = 82 if max_slots > 4 else 92
    sel_slot = getattr(game, "selected_slot", 0)
    if getattr(game, "state", None) is not None:
        game.state.sync_slot_meta_with_inventory(game.robot.inventory)
    for idx in range(max_slots):
        sx = start_sx + idx * slot_step
        sy = SCREEN_H - 47
        slot_r = pygame.Rect(sx, sy, slot_w, 34)
        is_sel = idx == sel_slot
        pygame.draw.rect(game.screen, (88, 60, 34) if is_sel else (68, 44, 28), slot_r, border_radius=6)
        pygame.draw.rect(
            game.screen,
            (255, 232, 85) if is_sel else (175, 128, 72),
            slot_r,
            2,
            border_radius=6,
        )
        if idx < len(game.robot.inventory):
            item_key = game.robot.inventory[idx]
            icon = game.vault.get_item_icon(item_key, 24)
            game.screen.blit(icon, (sx + (slot_w - 24) // 2, sy + 5))
            # Vẽ ký hiệu chất lượng Sao (Bạc / Vàng / Iridium) góc dưới phải của ô
            if getattr(game, "state", None) is not None and idx < len(game.state.slot_meta):
                s_meta = game.state.slot_meta[idx]
                if s_meta.quality > 0:
                    pygame.draw.circle(
                        game.screen,
                        s_meta.quality_color,
                        (slot_r.right - 6, slot_r.bottom - 6),
                        4,
                    )
                    pygame.draw.circle(
                        game.screen,
                        (28, 18, 10),
                        (slot_r.right - 6, slot_r.bottom - 6),
                        4,
                        1,
                    )

    # Vẽ các nút điều khiển nhanh
    mouse_pos = pygame.mouse.get_pos()
    for btn in game.hud_buttons:
        r: pygame.Rect = btn["rect"]
        bid = btn["id"]
        active = False
        if bid == f"map{game.current_map_id}" and not game.in_interior:
            active = True
        elif bid == "slow" and game.robot.is_slow_active:
            active = True
        elif bid == "fan" and game.show_interaction_fan:
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
            bg = (52, 34, 22)
            bd = (168, 124, 68)

        pygame.draw.rect(game.screen, bg, r, border_radius=6)
        pygame.draw.rect(game.screen, bd, r, 2, border_radius=6)
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
