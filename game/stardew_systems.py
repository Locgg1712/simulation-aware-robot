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

        # 3. Kiểm tra con cá có nằm trong vùng thanh xanh lá không
        in_range = abs(self.fish_pos - self.bar_pos) <= (self.bar_half_size + 0.04)
        if in_range:
            self.progress += 0.54 * dt
        else:
            self.progress -= 0.18 * dt

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
            if ws is not None:
                b_status = getattr(ws, "bought_status", {})
                has_upgrade = b_status.get("fast_harvest", False) or b_status.get("cargo_lv2", False)

            roll = random.random()
            if has_upgrade or self.elapsed_time < 3.2:
                if roll < 0.55:
                    quality = 2
                    stars = "**"
                    star_name = "Sao Vàng"
                else:
                    quality = 1
                    stars = "*"
                    star_name = "Sao Bạc"
            else:
                if roll < 0.35:
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
    "apple": 35,
    "orange": 38,
    "peach": 45,
    "strawberry": 42,
    "pumpkin": 55,
    "tomato": 36,
    "carrot": 32,
    "corn": 34,
    "cabbage": 40,
    "wheat": 30,
    "fish": 50,
    "bread": 40,
    "parcel": 60,
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

    # Nếu khay đồ đang trống
    if not game.robot.inventory:
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

    target_idx = -1
    for i in range(len(game.robot.inventory) - 1, -1, -1):
        if game.robot.inventory[i] != quest_item_key:
            target_idx = i
            break

    # Nếu tất cả đều trùng quest_item_key thì bán phần tử cuối cùng
    if target_idx == -1:
        target_idx = len(game.robot.inventory) - 1

    sold_item = game.robot.inventory.pop(target_idx)
    base_price = ITEM_GOLD_PRICES.get(sold_item, 35)

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

    final_price = int(round(base_price * multiplier))

    if not hasattr(game, "gold"):
        game.gold = 0
    game.gold += final_price

    # Cập nhật thống kê kinh tế ngày trên game.state nếu có
    state = getattr(game, "state", None)
    if state is not None:
        state.daily_gold_earned = getattr(state, "daily_gold_earned", 0) + final_price
        state.daily_crops_shipped = getattr(state, "daily_crops_shipped", 0) + 1

    # Phát âm thanh SFX "gold"
    audio = getattr(game, "audio", None)
    if audio is not None and hasattr(audio, "play_sfx"):
        audio.play_sfx("gold")

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

    # 1. Badge tiêu đề Thùng Giao Hàng
    title_text = "Thùng Bán Nông Sản (+G)"
    t_surf = font.render(title_text, True, (255, 235, 110))
    coin_ico = game.vault.scaled("icon_coin", 18, 18)

    pad_x = 8
    badge_w = t_surf.get_width() + (22 if coin_ico else 0) + pad_x * 2
    badge_h = 24
    bx = sx - badge_w // 2
    by = sy - 46

    badge_surf = pygame.Surface((badge_w, badge_h), pygame.SRCALPHA)
    badge_surf.fill((34, 24, 16, 215))
    pygame.draw.rect(badge_surf, (222, 168, 52), (0, 0, badge_w, badge_h), 2, border_radius=6)
    screen.blit(badge_surf, (bx, by))

    off_x = bx + pad_x
    if coin_ico is not None:
        screen.blit(coin_ico, (off_x, by + 3))
        off_x += 20
    screen.blit(t_surf, (off_x, by + 4))

    # 2. Khung nhắc nhở [E] khi Robot đứng gần <= 72px
    if dist <= 72.0:
        prompt_text = "[E] Bán Nông Sản lấy Vàng (G)"
        bob = int(math.sin(sim_t * 6.0) * 3)
        p_surf = font.render(prompt_text, True, (255, 255, 255))
        pw = p_surf.get_width() + 18
        ph = 22
        px = sx - pw // 2
        py = by - 26 + bob

        prompt_surf = pygame.Surface((pw, ph), pygame.SRCALPHA)
        prompt_surf.fill((28, 122, 54, 230))
        pygame.draw.rect(prompt_surf, (132, 255, 150), (0, 0, pw, ph), 2, border_radius=5)
        screen.blit(prompt_surf, (px, py))
        screen.blit(p_surf, (px + 9, py + 3))


# ==============================================================================
# MỤC 8.7: XƯỞNG NÂNG CẤP ROBOT CỦA THỢ MỘC ROBIN (RobinWorkshopManager)
# ==============================================================================

class RobinWorkshopManager:
    """
    Quản lý Xưởng Nâng Cấp Robot Của Thợ Mộc Robin (Mục 8.7).
    Cho phép Robot đầu tư Vàng (G) thu được từ Thùng Giao Hàng để mua 3 gói nâng cấp:
    1. cargo_lv2: Mở rộng khay chứa đồ từ 4 ô lên 6 ô chứa (80G -> 64G khi 3♥).
    2. fast_harvest: Cánh tay thu hoạch siêu tốc giảm từ 1.5s xuống 0.75s (100G -> 80G khi 3♥).
    3. social_radar: Radar An Toàn HRI tự động bật chế độ đi chậm khi cách người bất kỳ < 1.25m
       hoặc < 1.65m đối với Người Cao Tuổi & Trẻ Nhỏ (120G -> 96G khi 3♥).
    """

    UPGRADES_CONFIG = [
        {
            "id": "cargo_lv2",
            "name": "Khay Hàng Mở Rộng (4 -> 6 Ô)",
            "price": 80,
            "desc": "Tăng dung lượng khay chứa đồ từ 4 ô lên 6 ô chứa.",
            "icon": "icon_parcel",
            "key_str": "1",
        },
        {
            "id": "fast_harvest",
            "name": "Cánh Tay Thu Hoạch Siêu Tốc (1.5s -> 0.75s)",
            "price": 100,
            "desc": "Gia tốc cánh tay: thu hoạch nông sản & hái quả nhanh gấp đôi.",
            "icon": "strawberry",
            "key_str": "2",
        },
        {
            "id": "social_radar",
            "name": "Radar An Toàn HRI (Tự Giảm Tốc Gần Người)",
            "price": 120,
            "desc": "Tự động đi chậm cách người lớn 1.25m; mở rộng 1.65m với người già & trẻ nhỏ.",
            "icon": "icon_warning",
            "key_str": "3",
        },
    ]

    def __init__(self) -> None:
        self.open: bool = False
        self.bought_status: dict[str, bool] = {
            "cargo_lv2": False,
            "fast_harvest": False,
            "social_radar": False,
        }
        self.row_rects: list[pygame.Rect] = []
        self.close_btn_rect: pygame.Rect = pygame.Rect(0, 0, 0, 0)

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

    def buy_upgrade(self, game: Any, idx: int) -> bool:
        """
        Thực hiện mua gói nâng cấp theo chỉ số idx (0, 1, 2).
        Kiểm tra số Vàng của người chơi và áp dụng hiệu ứng vĩnh viễn (kèm giảm giá 20% nếu 3♥ với Robin).
        """
        if idx < 0 or idx >= len(self.UPGRADES_CONFIG):
            return False

        up = self.UPGRADES_CONFIG[idx]
        item_id = up["id"]

        if self.bought_status.get(item_id, False):
            if hasattr(game, "set_banner"):
                game.set_banner(
                    f"Bạn đã sở hữu nâng cấp '{up['name']}' rồi!",
                    (255, 210, 120),
                )
            return False

        current_gold = getattr(game, "gold", 0)
        price = self.get_upgrade_price(game, up["price"])

        if current_gold < price:
            if hasattr(game, "set_banner"):
                game.set_banner(
                    f"Không đủ Vàng! Cần {price}G (Hiện có: {current_gold}G). Hãy bán thêm nông sản tại Thùng Giao Hàng!",
                    (255, 115, 100),
                )
            return False

        # Trừ vàng & đánh dấu đã sở hữu
        game.gold -= price
        self.bought_status[item_id] = True

        # Áp dụng hiệu ứng ngay lập tức
        if item_id == "cargo_lv2":
            game.robot.max_inventory = 6
        elif item_id == "fast_harvest":
            game.robot.harvest_duration = 0.75
        elif item_id == "social_radar":
            setattr(game, "has_social_radar", True)

        if hasattr(game, "add_score"):
            game.add_score(60, f"Nâng cấp: {up['name']}")

        if hasattr(game, "set_banner"):
            game.set_banner(
                f"NÂNG CẤP THÀNH CÔNG: {up['name']}! Hiệu ứng đã kích hoạt vĩnh viễn.",
                (96, 255, 142),
            )
        return True

    def apply_passive_effects(self, game: Any) -> None:
        """
        Duy trì các hiệu ứng nội tại của các gói nâng cấp đã mua:
        - Giữ max_inventory = 6 nếu mua cargo_lv2.
        - Giữ harvest_duration = 0.75 nếu mua fast_harvest.
        - Radar An Toàn HRI Phân Biệt Người Già & Trẻ Nhỏ (Mục 8.7):
          Khi đã sở hữu social_radar, kiểm tra từng NPC xung quanh:
          + Người Cao Tuổi hoặc Trẻ Nhỏ ('Bà Evelyn', 'Ông George', 'Thị trưởng Lewis',
            'Ngư phủ Willy', 'Bé Jas', 'Chàng mèo Leo' hoặc age_group in ('elder', 'child')):
            khoảng cách phanh đi chậm mở rộng lên 1.65m.
          + Người lớn bình thường: khoảng cách phanh đi chậm là 1.25m.
        """
        if self.bought_status.get("cargo_lv2", False):
            if game.robot.max_inventory < 6:
                game.robot.max_inventory = 6

        if self.bought_status.get("fast_harvest", False):
            if game.robot.harvest_duration > 0.75:
                game.robot.harvest_duration = 0.75

        if self.bought_status.get("social_radar", False):
            active_npcs = (
                game.interior_npcs
                if getattr(game, "in_interior", False)
                else getattr(game, "npcs", [])
            )
            near_npc = False

            # Danh sách Người Cao Tuổi & Trẻ Nhỏ cần bảo vệ an toàn tuyệt đối
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
                npc_name = getattr(npc, "name", "")
                age_group = ""
                if isinstance(npcs_db, dict) and npc_name in npcs_db:
                    npc_info = npcs_db[npc_name]
                    if isinstance(npc_info, dict):
                        age_group = npc_info.get("age_group", "")

                is_vulnerable = (npc_name in vulnerable_names) or (age_group in ("elder", "child"))

                # Mở rộng khoảng cách an toàn: 1.65m đối với Người Già / Trẻ Nhỏ, 1.25m với người lớn
                safe_dist_m = 1.65 if is_vulnerable else 1.25
                safe_dist_px = m_to_px(safe_dist_m)

                if math.hypot(npc.x - game.robot.x, npc.y - game.robot.y) < safe_dist_px:
                    near_npc = True
                    break

            if near_npc:
                game.robot.is_slow_active = True

    def handle_event(self, event: pygame.event.Event, game: Any) -> bool:
        """
        Bắt sự kiện bàn phím và chuột khi tương tác với Xưởng Robin:
        - Bấm [U] để đóng/mở bảng nâng cấp.
        - Khi mở: [1, 2, 3] để mua tương ứng, [ESC] để đóng, click chuột vào dòng nâng cấp hoặc nút [X].
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
        Vẽ bảng Xưởng Nâng Cấp Robot giữa màn hình khi self.open == True.
        Thiết kế bảng gỗ Robin chuẩn phong cách Stardew Valley:
        - Header: Tiêu đề xưởng, nhãn giảm giá 20% khi 3♥ với Robin, và Vàng hiện có.
        - Body: 3 dòng nâng cấp có phím tắt [1], [2], [3], icon, mô tả, nút mua/đã sở hữu.
        - Footer: Hướng dẫn đóng/mở bằng [U] hoặc [ESC].
        """
        if not self.open:
            return

        # Kiểm tra đặc quyền mốc 3 ♥ với Thợ mộc Robin
        has_discount = (self.get_discount_ratio(game) < 1.0)

        # 1. Lớp phủ tối mờ toàn màn hình
        overlay = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
        overlay.fill((12, 10, 16, 175))
        screen.blit(overlay, (0, 0))

        # 2. Khung hộp thoại chính giữa màn hình (660x424)
        mw, mh = 660, 424
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
            "XƯỞNG NÂNG CẤP ROBOT — THỢ MỘC ROBIN",
            True,
            (255, 228, 85),
        )
        screen.blit(header_surf, (mx + 28, my + 18))

        if has_discount:
            discount_lbl = font_xs.render("[Đã giảm 20% nhờ 3♥ với Robin!]", True, (120, 255, 140))
            sub_text = "Đặc quyền bạn thân Robin: Giảm 20% toàn bộ gói nâng cấp công nghệ!"
            screen.blit(discount_lbl, (mx + 28, my + 44))
            sub_surf = font_xs.render(sub_text, True, (215, 245, 220))
            screen.blit(sub_surf, (mx + 28 + discount_lbl.get_width() + 10, my + 44))
        else:
            sub_surf = font_xs.render(
                "Nâng cấp công nghệ FarmBot bằng Vàng (G) thu được từ Thùng Giao Hàng",
                True,
                (215, 195, 175),
            )
            screen.blit(sub_surf, (mx + 28, my + 46))

        # Badge số Vàng hiện có
        current_gold = getattr(game, "gold", 0)
        gold_txt = f"{current_gold} G"
        g_val_surf = font_sm.render(gold_txt, True, (255, 235, 110))
        coin_ico = game.vault.scaled("icon_coin", 20, 20)
        gw = g_val_surf.get_width() + 40
        gx = mx + mw - gw - 60
        gy = my + 22
        g_badge = pygame.Rect(gx, gy, gw, 26)
        pygame.draw.rect(screen, (28, 18, 12), g_badge, border_radius=6)
        pygame.draw.rect(screen, (218, 165, 32), g_badge, width=1, border_radius=6)
        if coin_ico is not None:
            screen.blit(coin_ico, (gx + 6, gy + 3))
        screen.blit(g_val_surf, (gx + 30, gy + 4))

        # Nút đóng [X]
        self.close_btn_rect = pygame.Rect(mx + mw - 46, my + 18, 30, 30)
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
        pygame.draw.line(screen, (120, 82, 50), (mx + 20, my + 80), (mx + mw - 20, my + 80), 2)

        # 4. Body: 3 dòng nâng cấp
        self.row_rects.clear()
        start_y = my + 92
        row_h = 82
        row_gap = 12

        mouse_pos = pygame.mouse.get_pos()

        for idx, up in enumerate(self.UPGRADES_CONFIG):
            ry = start_y + idx * (row_h + row_gap)
            r_rect = pygame.Rect(mx + 24, ry, mw - 48, row_h)
            self.row_rects.append(r_rect)

            item_id = up["id"]
            is_bought = self.bought_status.get(item_id, False)
            price = self.get_upgrade_price(game, up["price"])
            can_afford = current_gold >= price
            is_hover = r_rect.collidepoint(mouse_pos)

            # Nền hàng
            if is_bought:
                row_bg = (34, 46, 32)
                row_border = (68, 158, 82)
            elif is_hover:
                row_bg = (58, 38, 24)
                row_border = (245, 195, 68)
            else:
                row_bg = (36, 24, 16)
                row_border = (112, 76, 46)

            pygame.draw.rect(screen, row_bg, r_rect, border_radius=8)
            pygame.draw.rect(screen, row_border, r_rect, width=2, border_radius=8)

            # Phím tắt [1], [2], [3]
            key_rect = pygame.Rect(r_rect.x + 12, r_rect.y + 14, 28, 28)
            pygame.draw.rect(screen, (22, 14, 10), key_rect, border_radius=4)
            pygame.draw.rect(screen, (218, 165, 32), key_rect, width=1, border_radius=4)
            k_lbl = font_sm.render(f"[{up['key_str']}]", True, (255, 235, 110))
            screen.blit(
                k_lbl,
                (
                    key_rect.centerx - k_lbl.get_width() // 2,
                    key_rect.centery - k_lbl.get_height() // 2,
                ),
            )

            # Biểu tượng nâng cấp
            icon_ico = game.vault.scaled(up["icon"], 36, 36)
            if icon_ico is not None:
                screen.blit(icon_ico, (r_rect.x + 50, r_rect.y + 10))
            else:
                pygame.draw.circle(
                    screen,
                    (218, 165, 32),
                    (r_rect.x + 68, r_rect.y + 28),
                    16,
                )

            # Tên và mô tả nâng cấp
            name_color = (255, 248, 225) if not is_bought else (168, 245, 178)
            name_surf = font_sm.render(up["name"], True, name_color)
            screen.blit(name_surf, (r_rect.x + 96, r_rect.y + 12))

            desc_text = up["desc"]
            if has_discount and not is_bought:
                desc_text += f" (Giảm 20%: {up['price']}G -> {price}G)"
            desc_surf = font_xs.render(desc_text, True, (200, 185, 168))
            screen.blit(desc_surf, (r_rect.x + 96, r_rect.y + 38))

            # Nút trạng thái bên phải
            btn_w, btn_h = 132, 34
            btn_x = r_rect.right - btn_w - 14
            btn_y = r_rect.centery - btn_h // 2
            btn_rect = pygame.Rect(btn_x, btn_y, btn_w, btn_h)

            if is_bought:
                pygame.draw.rect(screen, (28, 92, 45), btn_rect, border_radius=6)
                pygame.draw.rect(screen, (92, 228, 122), btn_rect, width=2, border_radius=6)
                status_lbl = font_xs.render("ĐÃ SỞ HỮU", True, (215, 255, 225))
            elif can_afford:
                b_color = (195, 125, 24) if not is_hover else (225, 148, 32)
                pygame.draw.rect(screen, b_color, btn_rect, border_radius=6)
                pygame.draw.rect(screen, (255, 218, 88), btn_rect, width=2, border_radius=6)
                status_lbl = font_xs.render(f"MUA ({price}G)", True, (255, 255, 255))
            else:
                pygame.draw.rect(screen, (58, 48, 42), btn_rect, border_radius=6)
                pygame.draw.rect(screen, (98, 88, 80), btn_rect, width=1, border_radius=6)
                status_lbl = font_xs.render(f"CẦN {price}G", True, (175, 165, 155))

            screen.blit(
                status_lbl,
                (
                    btn_rect.centerx - status_lbl.get_width() // 2,
                    btn_rect.centery - status_lbl.get_height() // 2,
                ),
            )

        # 5. Footer: Dòng hướng dẫn
        guide_text = "Bấm [1], [2], [3] hoặc Click Chuột để mua | Bấm phím [U] hoặc [ESC] để đóng cửa sổ"
        guide_surf = font_xs.render(guide_text, True, (225, 195, 145))
        screen.blit(
            guide_surf,
            (mx + mw // 2 - guide_surf.get_width() // 2, my + mh - 26),
        )
