# game/stardew_systems.py
"""
Mục 8.4, 8.5 & 8.7: Mini-game Thanh Câu Cá Stardew Valley, Thùng Giao Hàng Nông Trại
(Shipping Bin) tích lũy Vàng (G), Chất Lượng Nông Sản (Sao Bạc/Vàng/Iridium),
và Xưởng Nâng Cấp Robot Của Thợ Mộc Robin (Đặc quyền 3♥ & Radar An Toàn HRI).

Module này cung cấp:
1. FishingBarMinigame: Mini-game giữ thanh xanh lá bám theo con cá kiểu Stardew Valley,
   tính chất lượng cá (Sao Bạc ★, Sao Vàng ★★), phát âm thanh SFX và thông báo Popup Toast.
2. ShippingBin: Thùng giao hàng tại Map 2 giúp Robot bán nông sản dư thừa lấy Vàng (G) và Điểm,
   nhân hệ số Chất Lượng Sao (★ x1.25, ★★ x1.5, ★★★ x2.0) và cộng doanh thu ngày.
3. RobinWorkshopManager: Bảng Xưởng Nâng Cấp Robot (phím [U] hoặc tại nhà Robin):
   - Mốc 3 ♥ với Thợ mộc Robin: Giảm giá 20% toàn bộ gói nâng cấp.
   - Radar An Toàn HRI Phân Biệt Người Già & Trẻ Nhỏ: tự động phanh đi chậm ở khoảng cách 1.65m
     (thay vì 1.25m của người lớn), bảo vệ tuyệt đối cư dân dễ tổn thương.
"""

from __future__ import annotations

import math
import random
from typing import Any
import pygame

from .constants import (
    ITEM_NAMES_VI,
    SCORE_CATCH_FISH,
    SCREEN_H,
    SCREEN_W,
    m_to_px,
)
from .game_state import InventorySlot


# ==============================================================================
# MỤC 8.5: MINI-GAME THANH CÂU CÁ STARDEW VALLEY (FishingBarMinigame)
# ==============================================================================

class FishingBarMinigame:
    """
    Mini-game Thanh Câu Cá phong cách Stardew Valley (Mục 8.5).
    Người chơi giữ [SPACE]/[E]/[W]/[UP] hoặc Click Chuột Trái để đẩy thanh xanh lá lên,
    thả phím để thanh rơi xuống do trọng lực. Khi giữ con cá nằm trong thanh xanh lá,
    cột tiến độ (progress) sẽ tăng dần lên 1.0 để bắt trúng cá!
    Khi bắt trúng, đánh giá Chất Lượng Cá (Sao Bạc ★, Sao Vàng ★★) dựa trên tốc độ và nâng cấp.
    """

    def __init__(self) -> None:
        self.active: bool = False
        self.fish_pos: float = 0.5        # Vị trí cá từ 0.0 (đáy) lên 1.0 (đỉnh)
        self.fish_vel: float = 0.0        # Vận tốc tức thời con cá
        self.fish_target: float = 0.7     # Mục tiêu con cá đang bơi tới
        self.fish_timer: float = 0.0      # Đếm thời gian trước khi đổi hướng bơi
        self.bar_pos: float = 0.25        # Tâm thanh xanh lá trong [0.0, 1.0]
        self.bar_vel: float = 0.0         # Vận tốc của thanh xanh lá
        self.bar_half_size: float = 0.18  # Độ rộng nửa thanh xanh lá
        self.progress: float = 0.38       # Tiến độ bắt cá (0.0 -> 1.0)
        self.elapsed_time: float = 0.0    # Đếm thời gian mini-game để đánh giá chất lượng

    def start(self) -> None:
        """Khởi động mini-game khi có cá cắn câu."""
        self.active = True
        self.fish_pos = 0.35
        self.fish_target = 0.65
        self.fish_vel = 0.0
        self.fish_timer = 0.8
        self.bar_pos = 0.30
        self.bar_vel = 0.0
        self.progress = 0.45
        self.elapsed_time = 0.0

    def boost_bar(self) -> None:
        """Đẩy thanh xanh lá lên khi người chơi bấm nhấp liên tục phím [E]/[SPACE]/[W] hoặc Click chuột."""
        if not self.active:
            return
        self.bar_vel = max(self.bar_vel + 0.68, 0.90)
        self.bar_pos = min(1.0 - self.bar_half_size, self.bar_pos + 0.04)

    def update(self, game: Any, dt: float) -> None:
        """
        Cập nhật logic mini-game theo từng khung hình:
        - Con cá di chuyển mượt về fish_target, đổi hướng ngẫu nhiên mỗi 0.6..1.3s.
        - Thanh bắt cá chịu lực nâng khi người chơi giữ phím/chuột (hoặc bấm nhấp [E]) và trọng lực rơi tự do.
        - Tăng/giảm tiến độ progress và xử lý kết quả thắng/thua.
        - Khi thắng: tính Chất lượng cá (*, **), ghi InventorySlot vào slot_meta, phát SFX 'gold' và đẩy Toast!
        """
        if not self.active:
            return

        self.elapsed_time += dt

        # 1. Cập nhật chuyển động con cá
        self.fish_timer -= dt
        if self.fish_timer <= 0.0:
            self.fish_target = random.uniform(0.14, 0.86)
            self.fish_timer = random.uniform(0.65, 1.35)

        # Di chuyển mượt về fish_target
        diff = self.fish_target - self.fish_pos
        move_speed = 2.2 + abs(diff) * 1.6
        if abs(diff) > 0.005:
            step = math.copysign(min(abs(diff), move_speed * dt), diff)
            self.fish_pos += step
        self.fish_pos = max(0.06, min(0.94, self.fish_pos))

        # 2. Điều khiển thanh xanh lá (bar_pos)
        if getattr(game, "autopilot_enabled", False):
            # Chế độ AI Auto-pilot: tự động bám sát con cá để luôn câu thành công
            bar_diff = self.fish_pos - self.bar_pos
            self.bar_pos += bar_diff * min(1.0, 8.5 * dt)
            self.bar_vel = 0.0
        else:
            keys = pygame.key.get_pressed()
            mouse_held = pygame.mouse.get_pressed()[0]
            is_pulling = (
                keys[pygame.K_SPACE]
                or keys[pygame.K_e]
                or keys[pygame.K_w]
                or keys[pygame.K_UP]
                or mouse_held
            )

            if is_pulling:
                self.bar_vel += 2.5 * dt
            else:
                self.bar_vel -= 1.95 * dt

            # Giới hạn gia tốc tối đa và lực cản nước
            self.bar_vel = max(-2.2, min(2.4, self.bar_vel))
            self.bar_pos += self.bar_vel * dt

        # Giới hạn vị trí thanh trong [bar_half_size, 1.0 - bar_half_size]
        min_pos = self.bar_half_size
        max_pos = 1.0 - self.bar_half_size
        if self.bar_pos < min_pos:
            self.bar_pos = min_pos
            self.bar_vel = max(0.0, -self.bar_vel * 0.22)  # Nảy nhẹ ở đáy
        elif self.bar_pos > max_pos:
            self.bar_pos = max_pos
            self.bar_vel = min(0.0, -self.bar_vel * 0.22)  # Nảy nhẹ ở đỉnh

        # 3. Kiểm tra con cá có nằm trong vùng thanh xanh lá không (Lv.3 fast_harvest hỗ trợ giữ thanh dễ hơn)
        ws_fish = getattr(game, "workshop", None)
        fh_lv_fish = int(getattr(ws_fish, "upgrade_levels", {}).get("fast_harvest", 0)) if ws_fish is not None else 0
        extra_margin = 0.08 if fh_lv_fish >= 3 else 0.04
        gain_rate = 0.68 if fh_lv_fish >= 3 else 0.54
        loss_rate = 0.13 if fh_lv_fish >= 3 else 0.18
        in_range = abs(self.fish_pos - self.bar_pos) <= (self.bar_half_size + extra_margin)
        if in_range:
            self.progress += gain_rate * dt
        else:
            self.progress -= loss_rate * dt

        self.progress = max(0.0, min(1.0, self.progress))

        # 4. Kiểm tra kết quả
        if self.progress >= 1.0:
            # Bắt thành công cá!
            self.active = False
            game.robot.fishing_state = "idle"
            game.robot.fishing_spot = None

            # Tính Chất Lượng Cá (Quality):
            ws = getattr(game, "workshop", None)
            has_upgrade = False
            fast_lv = 0
            if ws is not None:
                if hasattr(ws, "_sync_levels_from_bought"):
                    ws._sync_levels_from_bought()
                b_status = getattr(ws, "bought_status", {})
                u_levels = getattr(ws, "upgrade_levels", {})
                has_upgrade = b_status.get("fast_harvest", False) or b_status.get("cargo_lv2", False)
                fast_lv = int(u_levels.get("fast_harvest", 0))

            roll = random.random()
            star_bonus = 0.12 if fast_lv >= 2 else 0.0
            if has_upgrade or self.elapsed_time < 3.2:
                if roll < (0.55 + star_bonus):
                    quality = 2
                    stars = "**"
                    star_name = "Sao Vàng"
                else:
                    quality = 1
                    stars = "*"
                    star_name = "Sao Bạc"
            else:
                if roll < (0.35 + star_bonus):
                    quality = 2
                    stars = "**"
                    star_name = "Sao Vàng"
                elif roll < 0.80:
                    quality = 1
                    stars = "*"
                    star_name = "Sao Bạc"
                else:
                    quality = 0
                    stars = ""
                    star_name = "Thường"

            # Thêm "fish" vào khay chứa đồ thông qua GameState (đồng bộ chuẩn InventorySlot)
            state = getattr(game, "state", None)
            if state is not None and hasattr(state, "add_inventory_item"):
                added = state.add_inventory_item(game, "fish", quality=quality)
            else:
                added = game.robot.add_item("fish")
                if added and state is not None and hasattr(state, "slot_meta"):
                    if isinstance(state.slot_meta, list):
                        state.slot_meta.append(InventorySlot(item_key="fish", quality=quality))

            if added:
                slot_idx = len(game.robot.inventory) - 1
                if not hasattr(game.robot, "slot_meta"):
                    game.robot.slot_meta = {}
                game.robot.slot_meta[slot_idx] = {
                    "quality": quality,
                    "stars": stars,
                    "item": "fish",
                    "name": star_name,
                }

            # Khởi tạo và cộng Vàng có hệ số chất lượng (★ x1.25, ★★ x1.5)
            gold_multiplier = 1.5 if quality == 2 else (1.25 if quality == 1 else 1.0)
            base_reward_gold = 45
            reward_gold = int(base_reward_gold * gold_multiplier)

            if not hasattr(game, "gold"):
                game.gold = 0
            game.gold += reward_gold
            if state is not None:
                state.daily_gold_earned = getattr(state, "daily_gold_earned", 0) + reward_gold
                state.total_fish_caught = getattr(state, "total_fish_caught", 0) + 1
                if hasattr(state, "check_achievements_and_certifications"):
                    state.check_achievements_and_certifications(game)

            # Cộng điểm SCORE_CATCH_FISH (+50đ)
            if hasattr(game, "add_score"):
                score_tag = f"Câu được Cá Hồ Tươi {stars}! (+{reward_gold}G)" if stars else f"Câu được Cá Hồ Tươi! (+{reward_gold}G)"
                game.add_score(
                    SCORE_CATCH_FISH,
                    score_tag,
                    game.robot.x,
                    game.robot.y,
                )

            # Phát âm thanh SFX "gold" nếu hệ thống audio có sẵn
            audio = getattr(game, "audio", None)
            if audio is not None and hasattr(audio, "play_sfx"):
                audio.play_sfx("gold")

            # Đẩy popup Toast thông báo câu cá thành công
            vfx = getattr(game, "vfx", None)
            if vfx is not None and hasattr(vfx, "push_toast"):
                toast_title = f"Câu Được Cá Hồ Tươi {stars}!".strip()
                vfx.push_toast(toast_title, f"+{reward_gold}G & +50đ", "fish")

            # Hiển thị banner chúc mừng
            star_label = f" {stars} ({star_name})" if stars else ""
            if hasattr(game, "set_banner"):
                if added:
                    game.set_banner(
                        f"BẮT ĐƯỢC CÁ HỒ TƯƠI{star_label}! (+50đ, +{reward_gold}G Vàng vào túi). Cá đã vào Khay Chứa Đồ!",
                        (98, 255, 142),
                    )
                else:
                    game.set_banner(
                        f"BẮT ĐƯỢC CÁ HỒ TƯƠI{star_label}! (+50đ, +{reward_gold}G Vàng). Khay đã đầy nên bạn tự động thả cá lại hồ.",
                        (140, 245, 185),
                    )

        elif self.progress <= 0.0:
            # Cá vùng thoát!
            self.active = False
            game.robot.fishing_state = "idle"
            game.robot.fishing_spot = None
            if hasattr(game, "set_banner"):
                game.set_banner(
                    "Cá đã vùng thoát mất rồi! Hãy bấm [E] tại điểm câu để thả cần câu lại.",
                    (255, 140, 105),
                )

    def render(self, screen: pygame.Surface, game: Any) -> None:
        """
        Vẽ khung Thanh Câu Cá Stardew Valley thẳng đứng ngay cạnh Robot.
        Kích thước chuẩn w = 48, h = 176 gồm:
        - Khung gỗ viền vàng Stardew Valley.
        - Cột nước xanh dương bên trái (26px) chứa thanh xanh lá và biểu tượng cá.
        - Cột tiến độ (progress) bên phải (10px) chuyển màu Đỏ -> Vàng -> Xanh Lá.
        - Nhãn hướng dẫn nhỏ phía trên: 'Giữ [SPACE]/[E]/Chuột để giữ cá!'.
        """
        if not self.active:
            return

        w, h = 48, 176
        bx = min(SCREEN_W - 70, int(game.robot.x + 34))
        by = max(90, min(SCREEN_H - 240, int(game.robot.y - 120)))

        # 1. Khung hộp gỗ viền vàng ngoài cùng
        box_rect = pygame.Rect(bx, by, w, h)
        pygame.draw.rect(screen, (48, 30, 20), box_rect, border_radius=6)
        pygame.draw.rect(screen, (222, 172, 48), box_rect, width=2, border_radius=6)

        # 2. Cột nước xanh dương bên trái (26px)
        water_x = bx + 4
        water_y = by + 4
        water_w = 26
        water_h = h - 8
        water_rect = pygame.Rect(water_x, water_y, water_w, water_h)
        pygame.draw.rect(screen, (16, 56, 96), water_rect, border_radius=3)
        pygame.draw.rect(screen, (10, 36, 68), water_rect, width=1, border_radius=3)

        # Thanh bắt cá màu xanh lá sáng (bar_pos, bar_half_size)
        bar_h_px = int(self.bar_half_size * 2.0 * water_h)
        bar_center_y = (water_y + water_h) - self.bar_pos * water_h
        bar_top_y = int(bar_center_y - self.bar_half_size * water_h)
        bar_rect = pygame.Rect(water_x + 1, bar_top_y, water_w - 2, bar_h_px)
        pygame.draw.rect(screen, (82, 222, 92), bar_rect, border_radius=3)
        pygame.draw.rect(screen, (38, 142, 48), bar_rect, width=1, border_radius=3)

        # Biểu tượng con cá tại fish_pos
        fish_center_y = int((water_y + water_h) - self.fish_pos * water_h)
        fish_icon = game.vault.get_item_icon("fish", 20)
        if fish_icon is not None:
            screen.blit(fish_icon, (water_x + (water_w - 20) // 2, fish_center_y - 10))
        else:
            pygame.draw.ellipse(
                screen,
                (255, 235, 75),
                (water_x + 3, fish_center_y - 6, water_w - 6, 12),
            )

        # 3. Cột tiến độ (progress) bên phải (10px)
        prog_x = bx + 33
        prog_y = by + 4
        prog_w = 11
        prog_h = h - 8
        prog_rect = pygame.Rect(prog_x, prog_y, prog_w, prog_h)
        pygame.draw.rect(screen, (24, 16, 12), prog_rect, border_radius=3)

        fill_h = max(2, int(self.progress * prog_h))
        # Chuyển màu tiến độ: Đỏ (thấp) -> Vàng (trung bình) -> Xanh Lá (cao)
        if self.progress < 0.5:
            ratio = self.progress / 0.5
            col_r = int(240 * (1.0 - ratio) + 245 * ratio)
            col_g = int(55 * (1.0 - ratio) + 215 * ratio)
            col_b = int(45 * (1.0 - ratio) + 35 * ratio)
        else:
            ratio = (self.progress - 0.5) / 0.5
            col_r = int(245 * (1.0 - ratio) + 55 * ratio)
            col_g = int(215 * (1.0 - ratio) + 235 * ratio)
            col_b = int(35 * (1.0 - ratio) + 95 * ratio)

        fill_rect = pygame.Rect(prog_x, prog_y + prog_h - fill_h, prog_w, fill_h)
        pygame.draw.rect(screen, (col_r, col_g, col_b), fill_rect, border_radius=2)
        pygame.draw.rect(screen, (108, 78, 52), prog_rect, width=1, border_radius=3)

        # 4. Nhãn hướng dẫn nhỏ phía trên
        font = getattr(game, "font_xs", None) or pygame.font.SysFont("Segoe UI", 12, bold=True)
        lbl = font.render("Giữ [SPACE]/[E]/Chuột để giữ cá!", True, (255, 245, 185))
        lx = max(6, min(SCREEN_W - lbl.get_width() - 14, bx + w // 2 - lbl.get_width() // 2 - 4))
        ly = max(6, by - 22)
        bg_w = lbl.get_width() + 8
        bg_rect = pygame.Rect(lx, ly, bg_w, 18)

        pygame.draw.rect(screen, (34, 22, 14, 225), bg_rect, border_radius=4)
        pygame.draw.rect(screen, (222, 172, 48), bg_rect, width=1, border_radius=4)
        screen.blit(lbl, (lx + 4, ly + 2))


# ==============================================================================
# MỤC 8.4: THÙNG GIAO HÀNG NÔNG TRẠI (SHIPPING BIN) TÍCH LŨY VÀNG (G)
# ==============================================================================

ITEM_GOLD_PRICES: dict[str, int] = {
    "wheat": 20,
    "carrot": 22,
    "corn": 24,
    "apple": 25,
    "tomato": 26,
    "orange": 28,
    "cabbage": 30,
    "strawberry": 32,
    "bread": 30,
    "peach": 35,
    "fish": 38,
    "pumpkin": 42,
    "parcel": 45,
    "wild_berry": 28,
    "mushroom": 36,
    "golden_flower": 48,
    "iridium_ore": 95,
}

# Vị trí Thùng Giao Hàng ở Map 2 (ngay cạnh Nhà Chính Nông Trại)
SHIPPING_BIN_POS: tuple[float, float] = (29.8 * 32.0, 8.2 * 32.0)


def try_use_shipping_bin(game: Any) -> bool:
    """
    Kiểm tra và thực hiện hành động bán nông sản vào Thùng Giao Hàng (Mục 8.4):
    - Chỉ áp dụng ngoài trời Map 2 trong khoảng cách <= 68.0 pixel.
    - Ưu tiên bán nông sản không trùng với mục tiêu nhiệm vụ đang thực hiện.
    - Nhân hệ số Chất Lượng Sao (★ Bạc x1.25, ★★ Vàng x1.5, ★★★ Iridium x2.0) từ slot_meta.
    - Cộng doanh thu vào game.state.daily_gold_earned và tăng game.state.daily_crops_shipped += 1.
    - Phát SFX 'gold', đẩy Popup Toast thông báo và cộng điểm kinh nghiệm.
    """
    if getattr(game, "in_interior", False) or getattr(game, "current_map_id", 1) != 2:
        return False

    dist = math.hypot(
        game.robot.x - SHIPPING_BIN_POS[0],
        game.robot.y - SHIPPING_BIN_POS[1],
    )
    if dist > 68.0:
        return False

    # Nếu khay đồ của Robot đang trống -> kiểm tra xem Xe AGV đi theo có đang chở hàng không
    from_agv = False
    agv_source = None
    if not game.robot.inventory:
        for a in getattr(game, "agvs", []):
            if getattr(a, "cargo", None) and (
                getattr(a, "mode", "patrol") == "follow"
                or math.hypot(a.x - game.robot.x, a.y - game.robot.y) <= 105.0
                or math.hypot(a.x - SHIPPING_BIN_POS[0], a.y - SHIPPING_BIN_POS[1]) <= 120.0
            ):
                agv_source = a
                from_agv = True
                break
        if not from_agv:
            if hasattr(game, "set_banner"):
                game.set_banner(
                    "Khay chứa đồ đang trống! Hãy thu hoạch nông sản rồi bỏ vào Thùng Giao Hàng để bán lấy Vàng (G).",
                    (255, 185, 95),
                )
            return True

    # Tìm vật phẩm để bán (ưu tiên vật phẩm không trùng với quest hiện tại)
    quest_item_key = ""
    if hasattr(game, "active_quest") and game.active_quest is not None:
        quest_item_key = getattr(game.active_quest, "item_key", "")

    if from_agv and agv_source is not None:
        entry = agv_source.cargo.pop(0)
        sold_item = str(entry.get("item_key", "apple"))
        quality_stars = int(entry.get("quality", 0))
        star_str = "**" if quality_stars >= 2 else ("*" if quality_stars == 1 else "")
        state_obj = getattr(game, "state", None)
        if state_obj is not None and getattr(agv_source, "mode", "") in ("follow", "parked"):
            state_obj.agv_cargo = list(agv_source.cargo)
        base_price = ITEM_GOLD_PRICES.get(sold_item, 25)
    else:
        target_idx = -1
        for i in range(len(game.robot.inventory) - 1, -1, -1):
            if game.robot.inventory[i] != quest_item_key:
                target_idx = i
                break

        # Nếu tất cả đều trùng quest_item_key thì bán phần tử cuối cùng
        if target_idx == -1:
            target_idx = len(game.robot.inventory) - 1

        sold_item = game.robot.inventory.pop(target_idx)
        base_price = ITEM_GOLD_PRICES.get(sold_item, 25)

        # Đọc và lấy Chất Lượng Sao từ game.state.slot_meta hoặc game.robot.slot_meta
        quality_stars = 0
        star_str = ""
        slot_meta = getattr(getattr(game, "state", None), "slot_meta", None)
        if slot_meta is None:
            slot_meta = getattr(getattr(game, "robot", None), "slot_meta", None)

        if isinstance(slot_meta, dict):
            meta_entry = slot_meta.pop(target_idx, {})
            if isinstance(meta_entry, dict):
                quality_stars = meta_entry.get("quality", 0)
                star_str = meta_entry.get("stars", "")
            elif isinstance(meta_entry, InventorySlot):
                quality_stars = meta_entry.quality
                star_str = meta_entry.stars_label
            # Dịch chuyển chỉ số của các slot nằm sau target_idx
            shifted_meta = {}
            for k, v in slot_meta.items():
                if isinstance(k, int):
                    if k < target_idx:
                        shifted_meta[k] = v
                    elif k > target_idx:
                        shifted_meta[k - 1] = v
                else:
                    shifted_meta[k] = v
            if getattr(game, "state", None) is not None and hasattr(game.state, "slot_meta"):
                game.state.slot_meta = shifted_meta
            if hasattr(game.robot, "slot_meta"):
                game.robot.slot_meta = shifted_meta
        elif isinstance(slot_meta, list) and 0 <= target_idx < len(slot_meta):
            meta_entry = slot_meta.pop(target_idx)
            if isinstance(meta_entry, dict):
                quality_stars = meta_entry.get("quality", 0)
                star_str = meta_entry.get("stars", "")
            elif isinstance(meta_entry, InventorySlot):
                quality_stars = meta_entry.quality
                star_str = meta_entry.stars_label

    # Hệ số Chất Lượng Sao: * Bạc x1.25, ** Vàng x1.5, *** Iridium x2.0
    if quality_stars == 1 or star_str in ("★", "*"):
        multiplier = 1.25
        star_str = "*"
    elif quality_stars == 2 or star_str in ("★★", "**"):
        multiplier = 1.50
        star_str = "**"
    elif quality_stars >= 3 or star_str in ("★★★", "***"):
        multiplier = 2.00
        star_str = "***"
    else:
        multiplier = 1.00

    # Cộng thưởng Khoang Lạnh (cargo_lv2 Lv.2 -> x1.10, Lv.3 -> x1.25), Logistics AGV và Chứng nhận Cấp III (+15%)
    ws = getattr(game, "workshop", None)
    cargo_lv = 0
    agv_lv = 0
    if ws is not None:
        if hasattr(ws, "_sync_levels_from_bought"):
            ws._sync_levels_from_bought()
        u_levels = getattr(ws, "upgrade_levels", {})
        cargo_lv = int(u_levels.get("cargo_lv2", 0))
        agv_lv = int(u_levels.get("agv_upgrade", 0))

    fresh_mult = 1.25 if cargo_lv >= 3 else (1.10 if cargo_lv == 2 else 1.0)
    state = getattr(game, "state", None)
    cert_mult = 1.15 if (state is not None and getattr(state, "certification_level", 0) >= 3) else 1.0
    if from_agv:
        if agv_lv >= 3:
            agv_mult = 1.45
        elif agv_lv == 2:
            agv_mult = 1.30
        elif agv_lv == 1:
            agv_mult = 1.20
        else:
            agv_mult = 1.15
    else:
        agv_mult = 1.0
    final_price = int(round(base_price * multiplier * fresh_mult * cert_mult * agv_mult))

    if not hasattr(game, "gold"):
        game.gold = 0
    game.gold += final_price

    # Cập nhật thống kê kinh tế ngày trên game.state nếu có
    if state is not None:
        state.daily_gold_earned = getattr(state, "daily_gold_earned", 0) + final_price
        state.daily_crops_shipped = getattr(state, "daily_crops_shipped", 0) + 1
        state.total_crops_shipped = getattr(state, "total_crops_shipped", 0) + 1
        if hasattr(state, "check_achievements_and_certifications"):
            state.check_achievements_and_certifications(game)

    # Phát âm thanh SFX "gold"
    audio = getattr(game, "audio", None)
    if audio is not None and hasattr(audio, "play_sfx"):
        audio.play_sfx("gold")

    if state is not None and hasattr(state, "get_item_name"):
        name_vi = state.get_item_name(sold_item)
    else:
        name_vi = ITEM_NAMES_VI.get(sold_item, sold_item)
    display_item_name = f"{name_vi} {star_str}".strip()

    # Đẩy Popup Toast thông báo bán hàng
    vfx = getattr(game, "vfx", None)
    if vfx is not None and hasattr(vfx, "push_toast"):
        vfx.push_toast(f"Đã Bán {display_item_name}!", f"+{final_price}G & +35đ", sold_item)

    if hasattr(game, "add_score"):
        game.add_score(
            35,
            f"Bán {display_item_name} (+{final_price}G)",
            SHIPPING_BIN_POS[0],
            SHIPPING_BIN_POS[1],
        )

    if hasattr(game, "set_banner"):
        star_note = f" (Chất lượng {star_str} x{multiplier:.2f})" if multiplier > 1.0 else ""
        game.set_banner(
            f"Đã bỏ {display_item_name} vào Thùng Giao Hàng! Nhận được +{final_price}G Vàng{star_note} (Tổng: {game.gold}G) và +35 điểm.",
            (125, 255, 145),
        )
    return True


def render_shipping_bin_overlay(screen: pygame.Surface, game: Any) -> None:
    """
    Vẽ lớp phủ trực quan cho Thùng Giao Hàng ở Map 2 ngoài trời:
    - Biểu tượng đồng tiền vàng [icon_coin] + nhãn 'Thùng Bán Nông Sản (+G)'.
    - Khi Robot đứng gần <= 72px, hiện nhắc tương tác '[E] Bán Nông Sản lấy Vàng (G)'.
    """
    if getattr(game, "in_interior", False) or getattr(game, "current_map_id", 1) != 2:
        return

    sx = int(SHIPPING_BIN_POS[0])
    sy = int(SHIPPING_BIN_POS[1])
    dist = math.hypot(
        game.robot.x - SHIPPING_BIN_POS[0],
        game.robot.y - SHIPPING_BIN_POS[1],
    )

    font = getattr(game, "font_xs", None) or pygame.font.SysFont("Segoe UI", 13, bold=True)
    sim_t = getattr(game, "sim_time", 0.0)

    # 0. Vẽ Thùng Gỗ Giao Hàng Nông Trại (Shipping Bin Sprite/Box) ngay tại (sx, sy)
    bin_w, bin_h = 44, 34
    bin_rect = pygame.Rect(sx - bin_w // 2, sy - bin_h // 2, bin_w, bin_h)
    pygame.draw.ellipse(screen, (18, 26, 14, 110), (bin_rect.x - 3, bin_rect.bottom - 7, bin_w + 6, 12))
    pygame.draw.rect(screen, (124, 76, 36), bin_rect, border_radius=5)
    pygame.draw.rect(screen, (88, 52, 22), bin_rect, 2, border_radius=5)
    lid_rect = pygame.Rect(bin_rect.x - 2, bin_rect.y - 4, bin_w + 4, 11)
    pygame.draw.rect(screen, (156, 98, 46), lid_rect, border_radius=4)
    pygame.draw.rect(screen, (232, 182, 62), lid_rect, 2, border_radius=4)
    pygame.draw.circle(screen, (245, 205, 68), (sx, bin_rect.centery + 3), 6)
    pygame.draw.circle(screen, (120, 78, 18), (sx, bin_rect.centery + 3), 6, 1)

    # 1. Chỉ hiện nhãn trên Thùng Giao Hàng khi Robot đứng gần <= 115px để không che ruộng lúa bên cạnh
    if dist <= 115.0:
        title_text = "[E] Thùng Bán Nông Sản (+G)" if dist <= 72.0 else "Thùng Bán Nông Sản"
        t_col = (132, 255, 150) if dist <= 72.0 else (255, 235, 110)
        t_surf = font.render(title_text, True, t_col)
        badge_w = t_surf.get_width() + 12
        badge_h = 18
        bx = sx - badge_w // 2
        by = sy - 36
        badge_surf = pygame.Surface((badge_w, badge_h), pygame.SRCALPHA)
        badge_surf.fill((28, 20, 14, 195))
        pygame.draw.rect(badge_surf, (222, 168, 52), (0, 0, badge_w, badge_h), 1, border_radius=4)
        screen.blit(badge_surf, (bx, by))
        screen.blit(t_surf, (bx + 6, by + 1))


# ==============================================================================
# MỤC 8.7: XƯỞNG NÂNG CẤP ĐA CẤP ĐỘ CỦA THỢ MỘC ROBIN (RobinWorkshopManager)
# ==============================================================================

class RobinWorkshopManager:
    """
    Quản lý Xưởng Nâng Cấp Robot Của Thợ Mộc Robin (Mục 8.7).
    Hệ thống nâng cấp Đa Cấp Độ (5 Hạng Mục × 3 Cấp Lv.1 -> Lv.2 -> Lv.3 + Gói Bảo Dưỡng/Siêu Nạp Lặp Lại):
    1. cargo_lv2: Khay Hàng & Khoang Lạnh Mở Rộng (6/7/8 ô & +10%/+25% giá bán nông sản).
    2. fast_harvest: Cánh Tay Thu Hoạch & Câu Cá Siêu Tốc (0.75s/0.50s/0.35s & hỗ trợ câu cá).
    3. social_radar: Radar An Toàn HRI & Đệm Từ Trường (phanh an toàn 1.25m/1.65m & tự hồi An Tâm HRI).
    4. battery_pack: Lõi Pin Năng Lượng Cao & Pin Mặt Trời (130%/160%/200% Pin & tự sạc ban ngày).
    5. agv_upgrade: Mô-đun Đồng Hành Xe Kéo AGV Turbo (6/8/10 ô chứa & thưởng Logistics +20%/+30%/+45%).
    """

    UPGRADES_CONFIG = [
        {
            "id": "cargo_lv2",
            "name": "Khay Hàng & Khoang Lạnh Mở Rộng",
            "price": 110,
            "prices": [110, 240, 420],
            "max_level": 3,
            "desc": "Mở rộng khay chứa đồ từ 4 lên 6/7/8 ô & Khoang lạnh bảo quản tăng giá bán.",
            "level_descs": [
                "Lv.1: Mở rộng khay chứa đồ từ 4 lên 6 ô.",
                "Lv.2: Mở rộng khay chứa đồ lên 7 ô + Khoang mát (+10% giá bán nông sản).",
                "Lv.3: Mở rộng khay chứa đồ lên 8 ô + Khoang lạnh (+25% giá bán nông sản).",
            ],
            "icon": "icon_parcel",
            "key_str": "1",
        },
        {
            "id": "fast_harvest",
            "name": "Cánh Tay Thu Hoạch & Câu Cá Siêu Tốc",
            "price": 130,
            "prices": [130, 260, 450],
            "max_level": 3,
            "desc": "Giảm thời gian thu hoạch từ 1.5s xuống 0.75s/0.50s/0.35s & hỗ trợ câu cá.",
            "level_descs": [
                "Lv.1: Giảm thời gian thu hoạch từ 1.5s xuống 0.75s.",
                "Lv.2: Thu hoạch siêu tốc 0.50s + tăng nhẹ tỉ lệ nông sản đạt Sao.",
                "Lv.3: Thu hoạch tức thì 0.35s + hỗ trợ giữ thanh câu cá dễ hơn.",
            ],
            "icon": "strawberry",
            "key_str": "2",
        },
        {
            "id": "social_radar",
            "name": "Radar An Toàn HRI & Đệm Từ Trường",
            "price": 150,
            "prices": [150, 300, 480],
            "max_level": 3,
            "desc": "Tự động đi chậm cách người lớn 1.25m (người già & trẻ nhỏ 1.65m) & hồi An Tâm HRI.",
            "level_descs": [
                "Lv.1: Tự động đi chậm cách người lớn 1.25m (người già & trẻ nhỏ 1.65m).",
                "Lv.2: Cảm biến HRI nhạy hơn + duy trì độ An Tâm HRI cao khi đi gần dân làng.",
                "Lv.3: Phanh Đệm Từ Trường tối tân + hồi phục nhẹ độ An Tâm HRI theo thời gian.",
            ],
            "icon": "icon_warning",
            "key_str": "3",
        },
        {
            "id": "battery_pack",
            "name": "Lõi Pin Năng Lượng Cao & Pin Mặt Trời",
            "price": 160,
            "prices": [160, 320, 520],
            "max_level": 3,
            "desc": "Tăng dung lượng Pin tối đa lên 130%/160%/200% & tự sạc năng lượng mặt trời.",
            "level_descs": [
                "Lv.1: Tăng dung lượng Pin tối đa lên 130% & sạc dự phòng ngay +30% Pin.",
                "Lv.2: Tăng dung lượng Pin tối đa lên 160% & sạc dự phòng ngay +40% Pin.",
                "Lv.3: Pin Mặt Trời Nano: Dung lượng Pin 200% & tự hồi nhẹ Pin ban ngày!",
            ],
            "icon": "iridium_ore",
            "key_str": "4",
        },
        {
            "id": "agv_upgrade",
            "name": "Mô-đun Đồng Hành Xe Kéo AGV Turbo",
            "price": 180,
            "prices": [180, 350, 550],
            "max_level": 3,
            "desc": "Mở rộng thùng Xe Kéo AGV từ 4 lên 6/8/10 ô chứa & tăng thưởng Logistics.",
            "level_descs": [
                "Lv.1: Mở rộng thùng Xe Kéo AGV từ 4 lên 6 ô chứa & thưởng Logistics +20%.",
                "Lv.2: Mở rộng thùng Xe Kéo AGV lên 8 ô chứa & thưởng Logistics +30%.",
                "Lv.3: Mở rộng thùng Xe Kéo AGV lên 10 ô chứa & thưởng Logistics +45%.",
            ],
            "icon": "carrot",
            "key_str": "5",
        },
    ]

    def __init__(self) -> None:
        self.open: bool = False
        self.bought_status: dict[str, bool] = {
            "cargo_lv2": False,
            "fast_harvest": False,
            "social_radar": False,
            "battery_pack": False,
            "agv_upgrade": False,
        }
        self.upgrade_levels: dict[str, int] = {k: 0 for k in self.bought_status}
        self.row_rects: list[pygame.Rect] = []
        self.close_btn_rect: pygame.Rect = pygame.Rect(0, 0, 0, 0)

    def _sync_levels_from_bought(self) -> None:
        """
        Đồng bộ tương thích ngược hai chiều giữa bought_status (bool) và upgrade_levels (int 0..3):
        - Nếu code bên ngoài hoặc file save/test gán trực tiếp bought_status[k] = True mà upgrade_levels[k] == 0,
          tự động coi upgrade_levels[k] = 1.
        - Ngược lại, nếu upgrade_levels[k] >= 1 thì bought_status[k] = True.
        """
        all_keys = set(self.bought_status.keys()) | set(self.upgrade_levels.keys())
        for k in all_keys:
            if self.bought_status.get(k, False) and self.upgrade_levels.get(k, 0) == 0:
                self.upgrade_levels[k] = 1
            elif self.upgrade_levels.get(k, 0) >= 1:
                self.bought_status[k] = True

    def toggle(self) -> None:
        """Đóng/Mở bảng nâng cấp Xưởng Robin."""
        self.open = not self.open

    def get_discount_ratio(self, game: Any) -> float:
        """
        Đặc quyền Mốc 3 ♥ với Thợ mộc Robin:
        Nếu game.dialogue.get_hearts('Thợ mộc Robin') >= 3, tự động giảm giá 20% (hệ số 0.8).
        """
        dialogue = getattr(game, "dialogue", None)
        if dialogue is not None and hasattr(dialogue, "get_hearts"):
            try:
                if dialogue.get_hearts("Thợ mộc Robin") >= 3:
                    return 0.80
            except Exception:
                pass
        return 1.00

    def get_upgrade_price(self, game: Any, base_price: int) -> int:
        """Tính giá bán nâng cấp sau khi áp dụng giảm giá 20% của Robin (nếu có)."""
        ratio = self.get_discount_ratio(game)
        return int(round(base_price * ratio))

    def buy_maintenance_pack(self, game: Any) -> bool:
        """
        Thực hiện 'Gói Bảo Dưỡng & Siêu Nạp Pin Toàn Diện (100G)' lặp lại không giới hạn:
        - Trừ 100G, hồi ngay +50% Pin cho game.robot.battery, hồi comfort_score = 100.0,
          cộng +35đ điểm cống hiến, báo banner nâng cấp bảo dưỡng thành công!
        """
        maint_price = 100
        current_gold = getattr(game, "gold", 0)
        if current_gold < maint_price:
            if hasattr(game, "set_banner"):
                game.set_banner(
                    f"Không đủ Vàng để Bảo Dưỡng & Siêu Nạp Pin! Cần {maint_price}G (Hiện có: {current_gold}G).",
                    (255, 135, 100),
                )
            return False

        game.gold -= maint_price
        if hasattr(game, "robot") and hasattr(game.robot, "battery"):
            max_bat = float(getattr(game.robot, "max_battery", 100.0))
            game.robot.battery = min(max_bat, float(game.robot.battery) + 50.0)
        if hasattr(game, "comfort_score"):
            game.comfort_score = 100.0
        if hasattr(game, "add_score"):
            game.add_score(35, "Bảo dưỡng & Siêu nạp Pin Toàn Diện")

        audio = getattr(game, "audio", None)
        if audio is not None and hasattr(audio, "play_sfx"):
            audio.play_sfx("gold")

        if hasattr(game, "set_banner"):
            game.set_banner(
                "BẢO DƯỠNG & SIÊU NẠP PIN THÀNH CÔNG (-100G): Hồi ngay +50% Pin, 100% An Tâm HRI & +35đ Cống hiến!",
                (96, 255, 162),
            )
        return True

    def buy_upgrade(self, game: Any, idx: int) -> bool:
        """
        Thực hiện mua gói nâng cấp theo chỉ số idx (0..4) từ Lv.0 -> Lv.1 -> Lv.2 -> Lv.3,
        hoặc Gói Bảo Dưỡng & Siêu Nạp Pin Toàn Diện (100G) khi đã đạt Max (Lv.3) hoặc bấm phím [6] (idx == 5).
        """
        self._sync_levels_from_bought()

        if idx == 5:
            return self.buy_maintenance_pack(game)

        if idx < 0 or idx >= len(self.UPGRADES_CONFIG):
            return False

        up = self.UPGRADES_CONFIG[idx]
        item_id = up["id"]
        max_lv = int(up.get("max_level", 3))
        cur_lv = int(self.upgrade_levels.get(item_id, 0))

        # Nếu hạng mục đã đạt Lv.3 (Max) -> chuyển sang Gói Bảo Dưỡng & Siêu Nạp Pin Toàn Diện (100G)
        if cur_lv >= max_lv:
            return self.buy_maintenance_pack(game)

        next_lv = cur_lv + 1
        prices_list = up.get("prices", [up["price"]] * max_lv)
        base_price = int(prices_list[cur_lv])
        current_gold = getattr(game, "gold", 0)
        price = self.get_upgrade_price(game, base_price)

        if current_gold < price:
            if hasattr(game, "set_banner"):
                game.set_banner(
                    f"Không đủ Vàng để nâng cấp {up['name']} (Lv.{next_lv})! Cần {price}G (Hiện có: {current_gold}G).",
                    (255, 115, 100),
                )
            return False

        # Trừ Vàng & nâng cấp cấp độ
        game.gold -= price
        self.upgrade_levels[item_id] = next_lv
        self.bought_status[item_id] = True

        # Áp dụng hiệu ứng nội tại ngay lập tức
        self.apply_passive_effects(game)

        # Thưởng sạc dự phòng tức thì khi mua nâng cấp Lõi Pin (battery_pack)
        if item_id == "battery_pack" and hasattr(game, "robot") and hasattr(game.robot, "battery"):
            instant_charge = 30.0 if next_lv == 1 else (40.0 if next_lv == 2 else 50.0)
            max_bat = float(getattr(game.robot, "max_battery", 130.0))
            game.robot.battery = min(max_bat, float(game.robot.battery) + instant_charge)

        if hasattr(game, "add_score"):
            game.add_score(60 * next_lv, f"Nâng cấp Lv.{next_lv}: {up['name']}")

        audio = getattr(game, "audio", None)
        if audio is not None and hasattr(audio, "play_sfx"):
            audio.play_sfx("gold")

        state_obj = getattr(game, "state", None)
        if state_obj is not None and hasattr(state_obj, "check_achievements_and_certifications"):
            state_obj.check_achievements_and_certifications(game)

        if hasattr(game, "set_banner"):
            lv_descs = up.get("level_descs", [up["desc"]] * max_lv)
            effect_txt = lv_descs[min(next_lv - 1, len(lv_descs) - 1)]
            game.set_banner(
                f"NÂNG CẤP THÀNH CÔNG [{up['name']} — Lv.{next_lv}/{max_lv}]: {effect_txt}",
                (96, 255, 142),
            )
        return True

    def apply_passive_effects(self, game: Any) -> None:
        """
        Duy trì các hiệu ứng nội tại của các gói nâng cấp đa cấp độ (Lv.1 -> Lv.3):
        - Gọi _sync_levels_from_bought() để tương thích ngược tuyệt đối.
        - cargo_lv2: Lv.1 -> max_inventory = 6, Lv.2 -> 7, Lv.3 -> 8.
        - fast_harvest: Lv.1 -> harvest_duration = 0.75, Lv.2 -> 0.50, Lv.3 -> 0.35.
        - social_radar: Lv.1+ bật radar_slow_active khi gần NPC; Lv.3 hồi nhẹ comfort_score +0.02 mỗi frame.
        - battery_pack: Lv.1 -> max_battery = 130.0, Lv.2 -> 160.0, Lv.3 -> 200.0 (& tự hồi nhẹ Pin ban ngày).
        - agv_upgrade: Lv.1 -> agv.max_cargo = 6, Lv.2 -> 8, Lv.3 -> 10.
        """
        self._sync_levels_from_bought()

        cargo_lv = int(self.upgrade_levels.get("cargo_lv2", 0))
        if cargo_lv >= 1:
            target_inv = 8 if cargo_lv >= 3 else (7 if cargo_lv == 2 else 6)
            if game.robot.max_inventory < target_inv:
                game.robot.max_inventory = target_inv

        fast_lv = int(self.upgrade_levels.get("fast_harvest", 0))
        if fast_lv >= 1:
            target_dur = 0.35 if fast_lv >= 3 else (0.50 if fast_lv == 2 else 0.75)
            if game.robot.harvest_duration > target_dur:
                game.robot.harvest_duration = target_dur

        radar_lv = int(self.upgrade_levels.get("social_radar", 0))
        if radar_lv >= 1:
            setattr(game, "has_social_radar", True)
            active_npcs = (
                game.interior_npcs
                if getattr(game, "in_interior", False)
                else getattr(game, "npcs", [])
            )
            near_npc = False

            # Danh sách dự phòng Người Cao Tuổi & Trẻ Nhỏ nếu thiếu dữ liệu JSON
            vulnerable_names = {
                "Bà Evelyn",
                "Ông George",
                "Thị trưởng Lewis",
                "Ngư phủ Willy",
                "Bé Jas",
                "Chàng mèo Leo",
            }
            npcs_db = getattr(getattr(game, "state", None), "npcs_db", {})

            for npc in active_npcs:
                if not getattr(game, "in_interior", False) and getattr(npc, "is_home_at_night", False):
                    continue
                npc_name = getattr(npc, "name", "")
                age_group = ""
                db_radius_m = 0.0
                if isinstance(npcs_db, dict) and npc_name in npcs_db:
                    npc_info = npcs_db[npc_name]
                    if isinstance(npc_info, dict):
                        age_group = str(npc_info.get("age_group", ""))
                        db_radius_m = float(npc_info.get("safety_radius_m", 0.0) or 0.0)

                is_vulnerable = (
                    (npc_name in vulnerable_names)
                    or (age_group in ("elder", "child", "Người Cao Tuổi", "Trẻ Nhỏ"))
                )

                # Đọc bán kính an toàn từ npcs.json (cộng biên phanh sớm 0.30m), ưu tiên 1.65m cho người già/trẻ nhỏ
                base_safe_m = 1.65 if is_vulnerable else 1.25
                safe_dist_m = max(base_safe_m, db_radius_m + 0.30) if db_radius_m > 0.0 else base_safe_m
                safe_dist_px = m_to_px(safe_dist_m)

                if math.hypot(npc.x - game.robot.x, npc.y - game.robot.y) < safe_dist_px:
                    near_npc = True
                    break

            game.robot.radar_slow_active = near_npc
            if near_npc:
                game.robot.is_slow_active = True
                if radar_lv >= 2 and hasattr(game, "comfort_score"):
                    game.comfort_score = min(100.0, float(getattr(game, "comfort_score", 100.0)) + 0.01)
            if radar_lv >= 3 and hasattr(game, "comfort_score"):
                game.comfort_score = min(100.0, float(getattr(game, "comfort_score", 100.0)) + 0.02)
        else:
            game.robot.radar_slow_active = False

        bat_lv = int(self.upgrade_levels.get("battery_pack", 0))
        if bat_lv >= 1:
            target_max_bat = 200.0 if bat_lv >= 3 else (160.0 if bat_lv == 2 else 130.0)
            if getattr(game.robot, "max_battery", 100.0) < target_max_bat:
                game.robot.max_battery = target_max_bat
            if bat_lv >= 3 and not getattr(game, "in_interior", False):
                is_daytime = not bool(getattr(game, "is_night", False))
                if is_daytime and hasattr(game.robot, "battery"):
                    game.robot.battery = min(
                        float(game.robot.max_battery),
                        float(game.robot.battery) + 0.003,
                    )

        agv_lv = int(self.upgrade_levels.get("agv_upgrade", 0))
        if agv_lv >= 1:
            target_cargo = 10 if agv_lv >= 3 else (8 if agv_lv == 2 else 6)
            for agv in getattr(game, "agvs", []):
                if getattr(agv, "max_cargo", 4) < target_cargo:
                    agv.max_cargo = target_cargo

    def handle_event(self, event: pygame.event.Event, game: Any) -> bool:
        """
        Bắt sự kiện bàn phím và chuột khi tương tác với Xưởng Robin:
        - Bấm [U] để đóng/mở bảng nâng cấp.
        - Khi mở: [1..5] để mua nâng cấp tương ứng, [6] để mua gói Bảo Dưỡng & Siêu Nạp Pin, [ESC] để đóng.
        - Trả về True nếu sự kiện được modal xử lý (nuốt sự kiện).
        """
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_u:
                self.toggle()
                return True

            if self.open:
                if event.key == pygame.K_ESCAPE:
                    self.open = False
                    return True
                if event.key in (pygame.K_1, pygame.K_KP1):
                    self.buy_upgrade(game, 0)
                    return True
                if event.key in (pygame.K_2, pygame.K_KP2):
                    self.buy_upgrade(game, 1)
                    return True
                if event.key in (pygame.K_3, pygame.K_KP3):
                    self.buy_upgrade(game, 2)
                    return True
                if event.key in (pygame.K_4, pygame.K_KP4):
                    self.buy_upgrade(game, 3)
                    return True
                if event.key in (pygame.K_5, pygame.K_KP5):
                    self.buy_upgrade(game, 4)
                    return True
                if event.key in (pygame.K_6, pygame.K_KP6):
                    self.buy_maintenance_pack(game)
                    return True
                return True  # Nuốt phím để robot không di chuyển khi đang mở modal

        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1 and self.open:
            mx, my = event.pos
            if self.close_btn_rect.collidepoint(mx, my):
                self.open = False
                return True

            for idx, rect in enumerate(self.row_rects):
                if rect.collidepoint(mx, my):
                    self.buy_upgrade(game, idx)
                    return True
            return True

        return False

    def render_modal(self, screen: pygame.Surface, game: Any) -> None:
        """
        Vẽ bảng Xưởng Nâng Cấp Robot Đa Cấp Độ giữa màn hình khi self.open == True.
        Thiết kế bảng gỗ Robin chuẩn phong cách Stardew Valley (700x520):
        - Header: Tiêu đề xưởng, nhãn giảm giá 20% khi 3♥ với Robin, và Vàng hiện có.
        - Body: 5 dòng nâng cấp đa cấp độ (Lv.0/3 -> Lv.3/3) có phím tắt [1]..[5], icon, mô tả, nút nâng cấp / bảo dưỡng.
        - Footer: Hướng dẫn nâng cấp, Gói Bảo Dưỡng [6] (100G) và đóng bằng [U] hoặc [ESC].
        """
        if not self.open:
            return

        self._sync_levels_from_bought()

        # Kiểm tra đặc quyền mốc 3 ♥ với Thợ mộc Robin
        has_discount = (self.get_discount_ratio(game) < 1.0)

        # 1. Lớp phủ tối mờ toàn màn hình
        overlay = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
        overlay.fill((12, 10, 16, 175))
        screen.blit(overlay, (0, 0))

        # 2. Khung hộp thoại chính giữa màn hình (700x520)
        mw, mh = 700, 520
        mx = (SCREEN_W - mw) // 2
        my = (SCREEN_H - mh) // 2
        modal_rect = pygame.Rect(mx, my, mw, mh)

        # Nền gỗ ấm viền vàng đôi
        pygame.draw.rect(screen, (46, 28, 18), modal_rect, border_radius=10)
        pygame.draw.rect(screen, (222, 168, 52), modal_rect, width=3, border_radius=10)
        pygame.draw.rect(
            screen,
            (95, 62, 38),
            (mx + 4, my + 4, mw - 8, mh - 8),
            width=1,
            border_radius=8,
        )

        font_sm = getattr(game, "font_sm", None) or pygame.font.SysFont("Segoe UI", 15, bold=True)
        font_md = getattr(game, "font_md", None) or pygame.font.SysFont("Segoe UI", 18, bold=True)
        font_xs = getattr(game, "font_xs", None) or pygame.font.SysFont("Segoe UI", 13, bold=True)

        # 3. Header: Tiêu đề xưởng & Nhãn giảm giá 20% khi 3♥
        header_surf = font_md.render(
            "XƯỞNG NÂNG CẤP CÔNG NGHỆ ĐA CẤP — THỢ MỘC ROBIN",
            True,
            (255, 228, 85),
        )
        screen.blit(header_surf, (mx + 24, my + 16))

        if has_discount:
            discount_lbl = font_xs.render("[Đã giảm 20% nhờ 3♥ với Robin!]", True, (120, 255, 140))
            sub_text = "Đặc quyền bạn thân Robin: Giảm 20% mọi cấp nâng cấp!"
            screen.blit(discount_lbl, (mx + 24, my + 42))
            sub_surf = font_xs.render(sub_text, True, (215, 245, 220))
            screen.blit(sub_surf, (mx + 24 + discount_lbl.get_width() + 10, my + 42))
        else:
            sub_surf = font_xs.render(
                "Nâng cấp 5 hạng mục (Lv.1 -> Lv.3) hoặc Bảo dưỡng Siêu nạp Pin [6] (100G)",
                True,
                (215, 195, 175),
            )
            screen.blit(sub_surf, (mx + 24, my + 42))

        # Badge số Vàng hiện có
        current_gold = getattr(game, "gold", 0)
        gold_txt = f"{current_gold} G"
        g_val_surf = font_sm.render(gold_txt, True, (255, 235, 110))
        coin_ico = game.vault.scaled("icon_coin", 20, 20)
        gw = g_val_surf.get_width() + 40
        gx = mx + mw - gw - 58
        gy = my + 18
        g_badge = pygame.Rect(gx, gy, gw, 26)
        pygame.draw.rect(screen, (28, 18, 12), g_badge, border_radius=6)
        pygame.draw.rect(screen, (218, 165, 32), g_badge, width=1, border_radius=6)
        if coin_ico is not None:
            screen.blit(coin_ico, (gx + 6, gy + 3))
        screen.blit(g_val_surf, (gx + 30, gy + 4))

        # Nút đóng [X]
        self.close_btn_rect = pygame.Rect(mx + mw - 44, my + 16, 28, 28)
        pygame.draw.rect(screen, (168, 42, 42), self.close_btn_rect, border_radius=6)
        pygame.draw.rect(screen, (235, 95, 95), self.close_btn_rect, width=2, border_radius=6)
        x_lbl = font_sm.render("X", True, (255, 255, 255))
        screen.blit(
            x_lbl,
            (
                self.close_btn_rect.centerx - x_lbl.get_width() // 2,
                self.close_btn_rect.centery - x_lbl.get_height() // 2 - 1,
            ),
        )

        # Đường kẻ phân cách
        pygame.draw.line(screen, (120, 82, 50), (mx + 20, my + 70), (mx + mw - 20, my + 70), 2)

        # 4. Body: 5 dòng nâng cấp đa cấp độ (Lv.0/3 -> Lv.3/3)
        self.row_rects.clear()
        start_y = my + 80
        row_h = 68
        row_gap = 8

        mouse_pos = pygame.mouse.get_pos()

        for idx, up in enumerate(self.UPGRADES_CONFIG):
            ry = start_y + idx * (row_h + row_gap)
            r_rect = pygame.Rect(mx + 20, ry, mw - 40, row_h)
            self.row_rects.append(r_rect)

            item_id = up["id"]
            max_lv = int(up.get("max_level", 3))
            cur_lv = int(self.upgrade_levels.get(item_id, 0))
            is_maxed = (cur_lv >= max_lv)
            prices_list = up.get("prices", [up["price"]] * max_lv)
            lv_descs = up.get("level_descs", [up["desc"]] * max_lv)

            if is_maxed:
                base_next_price = 100
                price = 100
                desc_text = lv_descs[-1]
            else:
                base_next_price = int(prices_list[cur_lv])
                price = self.get_upgrade_price(game, base_next_price)
                desc_text = lv_descs[cur_lv]
                if has_discount:
                    desc_text += f" (Giảm 20%: {base_next_price}G->{price}G)"

            can_afford = current_gold >= price
            is_hover = r_rect.collidepoint(mouse_pos)

            # Nền hàng theo cấp độ
            if is_maxed:
                row_bg = (30, 50, 34) if not is_hover else (38, 64, 42)
                row_border = (82, 198, 102)
            elif cur_lv > 0:
                row_bg = (42, 34, 22) if not is_hover else (58, 44, 28)
                row_border = (218, 175, 62) if not is_hover else (250, 210, 82)
            elif is_hover:
                row_bg = (58, 38, 24)
                row_border = (245, 195, 68)
            else:
                row_bg = (36, 24, 16)
                row_border = (112, 76, 46)

            pygame.draw.rect(screen, row_bg, r_rect, border_radius=8)
            pygame.draw.rect(screen, row_border, r_rect, width=2, border_radius=8)

            # Phím tắt [1]..[5]
            key_rect = pygame.Rect(r_rect.x + 10, r_rect.y + 10, 26, 26)
            pygame.draw.rect(screen, (22, 14, 10), key_rect, border_radius=4)
            pygame.draw.rect(screen, (218, 165, 32), key_rect, width=1, border_radius=4)
            k_lbl = font_xs.render(f"[{up['key_str']}]", True, (255, 235, 110))
            screen.blit(
                k_lbl,
                (
                    key_rect.centerx - k_lbl.get_width() // 2,
                    key_rect.centery - k_lbl.get_height() // 2,
                ),
            )

            # Thanh 3 nấc cấp độ dưới phím tắt
            for lv_i in range(max_lv):
                pip_rect = pygame.Rect(r_rect.x + 9 + lv_i * 10, r_rect.y + 42, 8, 14)
                pip_col = (95, 235, 125) if lv_i < cur_lv else (55, 42, 32)
                pygame.draw.rect(screen, pip_col, pip_rect, border_radius=2)
                pygame.draw.rect(screen, (165, 130, 85), pip_rect, width=1, border_radius=2)

            # Biểu tượng nâng cấp
            icon_ico = game.vault.scaled(up["icon"], 34, 34)
            if icon_ico is not None:
                screen.blit(icon_ico, (r_rect.x + 46, r_rect.y + 16))
            else:
                pygame.draw.circle(
                    screen,
                    (218, 165, 32),
                    (r_rect.x + 63, r_rect.y + 33),
                    15,
                )

            # Tên và cấp độ nâng cấp
            lv_badge = f"Lv.{cur_lv}/{max_lv} (MAX)" if is_maxed else f"Lv.{cur_lv}/{max_lv}"
            name_color = (155, 250, 175) if is_maxed else ((255, 238, 150) if cur_lv > 0 else (255, 248, 225))
            name_surf = font_sm.render(f"{up['name']}  [{lv_badge}]", True, name_color)
            screen.blit(name_surf, (r_rect.x + 88, r_rect.y + 10))

            desc_surf = font_xs.render(desc_text, True, (205, 192, 175))
            screen.blit(desc_surf, (r_rect.x + 88, r_rect.y + 36))

            # Nút trạng thái bên phải
            btn_w, btn_h = 152, 34
            btn_x = r_rect.right - btn_w - 12
            btn_y = r_rect.centery - btn_h // 2
            btn_rect = pygame.Rect(btn_x, btn_y, btn_w, btn_h)

            if is_maxed:
                b_col = (28, 102, 55) if can_afford else (42, 62, 46)
                pygame.draw.rect(screen, b_col, btn_rect, border_radius=6)
                pygame.draw.rect(screen, (98, 235, 132), btn_rect, width=2, border_radius=6)
                status_lbl = font_xs.render("BẢO DƯỠNG (100G)", True, (220, 255, 230))
            elif can_afford:
                b_color = (195, 125, 24) if not is_hover else (225, 148, 32)
                pygame.draw.rect(screen, b_color, btn_rect, border_radius=6)
                pygame.draw.rect(screen, (255, 218, 88), btn_rect, width=2, border_radius=6)
                status_lbl = font_xs.render(f"NÂNG CẤP Lv.{cur_lv + 1} ({price}G)", True, (255, 255, 255))
            else:
                pygame.draw.rect(screen, (58, 48, 42), btn_rect, border_radius=6)
                pygame.draw.rect(screen, (98, 88, 80), btn_rect, width=1, border_radius=6)
                status_lbl = font_xs.render(f"Lv.{cur_lv + 1}: CẦN {price}G", True, (175, 165, 155))

            screen.blit(
                status_lbl,
                (
                    btn_rect.centerx - status_lbl.get_width() // 2,
                    btn_rect.centery - status_lbl.get_height() // 2,
                ),
            )

        # 5. Footer: Dòng hướng dẫn
        guide_text = "Phím [1]..[5] / Click: Nâng cấp (Lv.1->3) | Phím [6]: Bảo dưỡng & Siêu nạp Pin (100G) | [U]/[ESC]: Đóng"
        guide_surf = font_xs.render(guide_text, True, (225, 195, 145))
        screen.blit(
            guide_surf,
            (mx + mw // 2 - guide_surf.get_width() // 2, my + mh - 26),
        )
