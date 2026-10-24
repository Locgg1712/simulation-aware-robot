# game/dialogue.py
"""
Hộp Thoại Chân Dung Nhân Vật & Hệ Thống Tim Thiện Cảm (Portrait Dialogue & Friendship Hearts)
theo Mục 8.2 & Mục 8.3:
- Quản lý điểm thiện cảm (0..500 điểm, tương ứng 0..5 ♥) của cư dân trong thị trấn FarmBot Town.
- Hiển thị hộp thoại phong cách Stardew Valley cổ điển:
  * Khung gỗ trầm ấm, viền vàng đồng & viền con dấu gỗ.
  * Nhãn nhóm tuổi cư dân ([Người Cao Tuổi] / [Trẻ Nhỏ] / [Cư Dân]) ngay cạnh tên nhân vật.
  * Khung chân dung NPC lớn với Biểu Cảm Chân Dung (Portrait Expression):
    - 'love': Viền hồng ánh kim + 2 trái tim nhỏ bay bổng quanh má.
    - 'happy': Viền vàng sáng + nốt nhạc vui tươi ♪.
    - 'surprised': Dấu chấm than sáng !.
    - 'sad': Giọt mồ hôi xanh nhạt khi bị đâm hoặc nhận món quà ghét.
  * 5 biểu tượng tim thiện cảm hiển thị trực quan dưới chân dung.
  * Hiệu ứng chữ chạy Typewriter mượt mà.
  * Huy hiệu phần thưởng nhiệm vụ và mốc tim.
  * Dòng gợi ý tương tác: '[E]/[Space]: Tiếp tục  |  [G]: Tặng vật phẩm đang cầm  |  [J]: Sổ tay NPC'.
- Hàm try_give_gift(game) -> bool:
  * Cho phép Robot tặng vật phẩm đang cầm cho NPC khi đứng trong Quạt Xanh trước mặt (phím [G]).
  * Tự động tra cứu sở thích (Loved / Liked / Hated items), cộng/trừ thiện cảm và điểm số.
  * Tặng thưởng Vàng tri ân (+50G ở Mốc 3 ♥, +120G ở Mốc 5 ♥) và thông báo mở khóa đặc quyền!
"""

from __future__ import annotations

import math
from typing import TYPE_CHECKING, Any
import pygame

from .constants import ITEM_NAMES_VI, SCREEN_H, SCREEN_W, px_to_m
from .journal_ui import DEFAULT_NPCS_DB, ensure_game_state, get_npc_age_group
from .safety_hri import check_front_interaction

if TYPE_CHECKING:
    from .entities import VillagerNPC


def _draw_music_note(screen: pygame.Surface, x: int, y: int, col: tuple[int, int, int], s: float = 1.0) -> None:
    """Vẽ nốt nhạc bằng hình học (font Segoe UI không có ký tự ♪ nên sẽ hiện ô vuông)."""
    head_r = max(2, int(3 * s))
    stem_h = int(11 * s)
    hx, hy = x + head_r, y + stem_h
    pygame.draw.circle(screen, col, (hx, hy), head_r)
    pygame.draw.line(screen, col, (hx + head_r - 1, hy), (hx + head_r - 1, y), max(1, int(2 * s)))
    pygame.draw.line(screen, col, (hx + head_r - 1, y), (hx + head_r + int(5 * s), y + int(4 * s)), max(1, int(2 * s)))


def _wrap_text(font: pygame.font.Font, text: str, max_width: int) -> list[str]:
    """Tự động ngắt dòng văn bản theo độ rộng tối đa tính bằng pixel."""
    if not text:
        return []
    lines: list[str] = []
    paragraphs = text.split("\n")
    for para in paragraphs:
        if not para:
            lines.append("")
            continue
        words = para.split(" ")
        current_line = ""
        for word in words:
            test_line = f"{current_line} {word}".strip() if current_line else word
            if font.size(test_line)[0] <= max_width:
                current_line = test_line
            else:
                if current_line:
                    lines.append(current_line)
                current_line = word
        if current_line:
            lines.append(current_line)
    return lines


class DialogueManager:
    """Quản lý lời thoại nhân vật và hệ thống thiện cảm cư dân."""

    def __init__(self) -> None:
        # Điểm thiện cảm của từng NPC theo npc.name (mặc định 200 điểm = 2 ♥, thang điểm 0..500)
        self.friendship: dict[str, int] = {}
        self.active: bool = False
        self.npc_name: str = ""
        self.npc_role: str = ""
        self.npc_folder: str = "npc_01_orange_boy"
        self.title: str = ""
        self.full_text: str = ""
        self.char_progress: float = 0.0
        self.auto_close_timer: float = 0.0
        self.reward_badge: str = ""
        self.expression: str = "happy"  # "happy" | "love" | "surprised" | "sad"

    def get_hearts(self, npc_name: str) -> int:
        """Trả về số tim thiện cảm nguyên (0..5 ♥) của NPC."""
        pts = self.friendship.get(npc_name, 200)
        return max(0, min(5, pts // 100))

    def adjust_friendship(self, npc_name: str, delta_points: int) -> int:
        """
        Cộng/trừ điểm thiện cảm của NPC trong khoảng [0, 500] và trả về số tim mới.
        Mỗi 100 điểm tương ứng 1 ♥.
        """
        current_pts = self.friendship.get(npc_name, 200)
        new_pts = max(0, min(500, current_pts + delta_points))
        self.friendship[npc_name] = new_pts
        return self.get_hearts(npc_name)

    def open_dialogue(
        self,
        npc: Any,
        title: str,
        text: str,
        reward_badge: str = "",
        duration: float = 5.5,
        expression: str = "happy",
    ) -> None:
        """Kích hoạt và mở hộp thoại nhân vật với hiệu ứng gõ chữ typewriter và biểu cảm."""
        self.active = True
        self.npc_name = getattr(npc, "name", "Dân Làng")
        self.npc_role = getattr(npc, "role", "Cư Dân")
        self.npc_folder = getattr(npc, "folder", "npc_01_orange_boy")
        self.title = title
        self.full_text = text
        self.reward_badge = reward_badge
        self.char_progress = 0.0
        self.auto_close_timer = duration
        self.expression = expression

    def close(self) -> None:
        """Đóng hộp thoại ngay lập tức."""
        self.active = False

    def advance_or_close(self) -> bool:
        """
        Xử lý khi người chơi ấn [E], [Space] hoặc click chuột:
        - Nếu hộp thoại chưa kích hoạt: trả về False.
        - Nếu chữ đang chạy typewriter: hiện hết chữ ngay lập tức và trả về True.
        - Nếu chữ đã hiện hết: đóng hộp thoại và trả về True.
        """
        if not self.active:
            return False
        if int(self.char_progress) < len(self.full_text):
            self.char_progress = float(len(self.full_text))
            return True
        self.active = False
        return True

    def update(self, dt: float) -> None:
        """Cập nhật tiến trình gõ chữ và bộ đếm thời gian tự động đóng."""
        if not self.active:
            return

        # Tốc độ gõ chữ khoảng 58 ký tự/giây
        self.char_progress += dt * 58.0
        if self.char_progress > len(self.full_text):
            self.char_progress = float(len(self.full_text))

        self.auto_close_timer -= dt
        if self.auto_close_timer <= 0.0:
            self.active = False

    def render(self, screen: pygame.Surface, game: Any) -> None:
        """Vẽ hộp thoại gỗ cổ điển phong cách Stardew Valley lên màn hình."""
        if not self.active:
            return

        box_w = 760
        box_h = 138
        box_x = (SCREEN_W - box_w) // 2
        box_y = SCREEN_H - 198
        box = pygame.Rect(box_x, box_y, box_w, box_h)

        # 1. Nền gỗ trầm ấm (48, 30, 18, 244)
        bg_surf = pygame.Surface((box.width, box.height), pygame.SRCALPHA)
        pygame.draw.rect(bg_surf, (48, 30, 18, 244), (0, 0, box.width, box.height), border_radius=8)
        screen.blit(bg_surf, box.topleft)

        # 2. Viền ngoài vàng đồng (222, 168, 82) dày 3px & Viền trong (128, 84, 44) dày 2px
        pygame.draw.rect(screen, (222, 168, 82), box, width=3, border_radius=8)
        inner_rect = box.inflate(-8, -8)
        pygame.draw.rect(screen, (128, 84, 44), inner_rect, width=2, border_radius=6)

        # 3. Khung Chân Dung NPC bên phải
        portrait_rect = pygame.Rect(box.right - 152, box.y + 10, 140, 118)
        pygame.draw.rect(screen, (72, 46, 28), portrait_rect, border_radius=6)

        # Màu viền và hiệu ứng biểu cảm chân dung (Portrait Expression)
        sim_t = getattr(game, "sim_time", 0.0)
        font_sm = getattr(game, "font_sm", None) or pygame.font.SysFont("Segoe UI", 15, bold=True)
        font_xs = getattr(game, "font_xs", None) or pygame.font.SysFont("Segoe UI", 13, bold=True)

        expr = getattr(self, "expression", "happy")
        if expr == "love":
            # "love": Viền hồng ánh kim + 2 trái tim nhỏ bay cạnh má chân dung
            p_border_col = (255, 140, 190)
            pygame.draw.rect(screen, p_border_col, portrait_rect, width=3, border_radius=6)

            h1_x = portrait_rect.centerx - 38
            h1_y = portrait_rect.y + 26 + int(math.sin(sim_t * 5.0) * 4)
            h2_x = portrait_rect.centerx + 22
            h2_y = portrait_rect.y + 22 + int(math.cos(sim_t * 5.0) * 4)
            h_ico = game.vault.scaled("icon_heart", 15, 14) if hasattr(game, "vault") else None
            if h_ico is not None:
                screen.blit(h_ico, (h1_x, h1_y))
                screen.blit(h_ico, (h2_x, h2_y))
            else:
                pygame.draw.circle(screen, (255, 110, 160), (h1_x + 6, h1_y + 6), 5)
                pygame.draw.circle(screen, (255, 110, 160), (h2_x + 6, h2_y + 6), 5)

        elif expr == "surprised":
            # "surprised": Viền vàng cam sáng + Dấu chấm than sáng '!'
            p_border_col = (255, 190, 45)
            pygame.draw.rect(screen, p_border_col, portrait_rect, width=3, border_radius=6)

            em_rect = pygame.Rect(portrait_rect.right - 24, portrait_rect.y + 8, 16, 22)
            pygame.draw.rect(screen, (255, 215, 50), em_rect, border_radius=4)
            pygame.draw.rect(screen, (120, 60, 15), em_rect, 1, border_radius=4)
            em_lbl = font_xs.render("!", True, (45, 25, 10))
            screen.blit(em_lbl, (em_rect.centerx - em_lbl.get_width() // 2, em_rect.centery - em_lbl.get_height() // 2))

        elif expr == "sad":
            # "sad": Viền lam trầm + Giọt mồ hôi xanh nhạt khi bị đâm hoặc nhận món ghét
            p_border_col = (95, 160, 225)
            pygame.draw.rect(screen, p_border_col, portrait_rect, width=3, border_radius=6)

            sw_x = portrait_rect.right - 24
            sw_y = portrait_rect.y + 22
            pygame.draw.polygon(screen, (130, 215, 255), [(sw_x + 5, sw_y), (sw_x, sw_y + 9), (sw_x + 10, sw_y + 9)])
            pygame.draw.circle(screen, (130, 215, 255), (sw_x + 5, sw_y + 9), 5)
            pygame.draw.circle(screen, (230, 250, 255), (sw_x + 4, sw_y + 8), 2)

        else:
            # "happy": Viền vàng sáng + Nốt nhạc vui tươi ♪
            p_border_col = (255, 225, 75)
            pygame.draw.rect(screen, p_border_col, portrait_rect, width=3, border_radius=6)

            n1_x = portrait_rect.right - 24
            n1_y = portrait_rect.y + 8 + int(math.sin(sim_t * 6.0) * 3)
            _draw_music_note(screen, n1_x, n1_y, (255, 245, 120), 1.0)
            n2_x = portrait_rect.left + 8
            n2_y = portrait_rect.y + 16 + int(math.cos(sim_t * 6.0) * 3)
            _draw_music_note(screen, n2_x, n2_y, (255, 235, 95), 0.8)

        # Vẽ chân dung lớn NPC (cao 72px) — hỗ trợ cả NPC nhiều hướng lẫn NPC 1 hướng (npc_*.png)
        portrait = None
        if hasattr(game, "vault") and game.vault is not None:
            portrait = game.vault.get_npc_portrait(self.npc_folder, 72)

        if portrait is not None:
            px = portrait_rect.centerx - portrait.get_width() // 2
            py = portrait_rect.y + 8
            screen.blit(portrait, (px, py))
        else:
            pygame.draw.circle(screen, (225, 138, 102), (portrait_rect.centerx, portrait_rect.y + 42), 26)

        # Dưới chân dung: 5 biểu tượng Trái Tim Thiện Cảm (0..5 ♥)
        current_hearts = self.get_hearts(self.npc_name)
        heart_spacing = 20
        total_hearts_w = 4 * heart_spacing + 16
        start_hx = portrait_rect.centerx - total_hearts_w // 2
        heart_y = portrait_rect.bottom - 22

        heart_spr = None
        if hasattr(game, "vault") and game.vault is not None:
            heart_spr = game.vault.scaled("icon_heart", 16, 15)

        for i in range(5):
            hx = start_hx + i * heart_spacing
            if i < current_hearts:
                if heart_spr is not None:
                    screen.blit(heart_spr, (hx, heart_y))
                else:
                    pygame.draw.circle(screen, (235, 55, 65), (hx + 8, heart_y + 8), 6)
            else:
                pygame.draw.circle(screen, (85, 58, 48), (hx + 8, heart_y + 8), 6)
                pygame.draw.circle(screen, (145, 108, 88), (hx + 8, heart_y + 8), 6, width=1)

        # 4. Vùng Văn Bản bên trái (x = box.x + 18, rộng tối đa 570 px)
        text_x = box.x + 18
        max_text_w = 570

        # Huy hiệu phần thưởng ở góc trên bên phải vùng chữ nếu có
        avail_title_w = max_text_w
        if self.reward_badge:
            clean_badge = self.reward_badge.replace("♥", "Tim")
            badge_surf = font_xs.render(clean_badge, True, (115, 255, 155))
            badge_x = text_x + max_text_w - badge_surf.get_width()
            badge_y = box.y + 10
            badge_bg = pygame.Rect(
                badge_x - 6, badge_y - 2, badge_surf.get_width() + 12, badge_surf.get_height() + 4
            )
            avail_title_w = max(200, max_text_w - badge_bg.width - 14)
            badge_layer = pygame.Surface((badge_bg.width, badge_bg.height), pygame.SRCALPHA)
            pygame.draw.rect(badge_layer, (30, 75, 45, 225), (0, 0, badge_bg.width, badge_bg.height), border_radius=4)
            screen.blit(badge_layer, badge_bg.topleft)
            pygame.draw.rect(screen, (90, 215, 135), badge_bg, width=1, border_radius=4)
            screen.blit(badge_surf, (badge_x, badge_y))

        # Hiển thị Tên NPC và Nhãn Nhóm Tuổi ([Người Cao Tuổi] / [Trẻ Nhỏ] / [Cư Dân])
        age_group = get_npc_age_group(game, self.npc_name)
        age_colors = {
            "Người Cao Tuổi": ((255, 185, 110), (75, 45, 20)),
            "Trẻ Nhỏ": ((135, 235, 255), (20, 50, 70)),
            "Cư Dân": ((150, 245, 150), (25, 65, 30)),
        }
        tag_fg, tag_bg = age_colors.get(age_group, ((220, 220, 220), (50, 50, 50)))

        name_surf = font_sm.render(self.npc_name, True, (255, 232, 125))
        screen.blit(name_surf, (text_x, box.y + 11))
        nx = text_x + name_surf.get_width() + 6

        age_lbl = font_xs.render(f"[{age_group}]", True, tag_fg)
        tag_rect = pygame.Rect(nx, box.y + 11, age_lbl.get_width() + 8, age_lbl.get_height() + 2)
        pygame.draw.rect(screen, tag_bg, tag_rect, border_radius=4)
        pygame.draw.rect(screen, tag_fg, tag_rect, width=1, border_radius=4)
        screen.blit(age_lbl, (nx + 4, box.y + 12))

        # Tiêu đề sau nhãn nhóm tuổi
        tx = tag_rect.right + 8
        sep_surf = font_sm.render(f"— {self.title}", True, (240, 220, 180))
        avail_sub_w = avail_title_w - (tx - text_x)
        if sep_surf.get_width() > avail_sub_w:
            t_clip = self.title
            while len(t_clip) > 6 and font_sm.size(f"— {t_clip}...")[0] > avail_sub_w:
                t_clip = t_clip[:-1]
            sep_surf = font_sm.render(f"— {t_clip}...", True, (240, 220, 180))
        screen.blit(sep_surf, (tx, box.y + 11))

        # Nội dung văn bản với hiệu ứng gõ chữ Typewriter
        visible_count = max(0, min(len(self.full_text), int(self.char_progress)))
        visible_text = self.full_text[:visible_count]
        wrapped_lines = _wrap_text(font_sm, visible_text, max_text_w)

        line_y = box.y + 36
        for line in wrapped_lines[:3]:  # Giới hạn tối đa dòng vừa vặn hộp thoại
            line_surf = font_sm.render(line, True, (255, 248, 230))
            screen.blit(line_surf, (text_x, line_y))
            line_y += 21

        # Dòng nhắc tương tác chuẩn theo đặc tả ở dòng dưới cùng của hộp thoại
        hint_surf = font_xs.render(
            "[E]/[Space]: Tiếp tục  |  [G]: Tặng vật phẩm đang cầm  |  [J]: Sổ tay NPC",
            True,
            (215, 195, 155),
        )
        screen.blit(hint_surf, (text_x, box.bottom - 22))


# ==============================================================================
# HÀM XỬ LÝ TẶNG QUÀ CHO NPC KHI BẤM PHÍM [G] (try_give_gift)
# ==============================================================================
def try_give_gift(game: Any) -> bool:
    """
    Xử lý tặng quà cho cư dân khi người chơi bấm phím [G]:
    1. Kiểm tra Robot đang đứng gần một NPC (khoảng cách <= 2.4m) và có ít nhất 1 vật phẩm trong khay.
    2. Kiểm tra Robot đứng đúng phía trước NPC (check_front_interaction hoặc dung sai d_m <= 1.65 và delta_npc_deg <= 50°).
    3. Lấy vật phẩm tại ô đang chọn (selected_slot = getattr(game, 'selected_slot', 0)) và xóa khỏi khay đồ.
    4. Tra cứu sở thích quà tặng của NPC từ game.state.npcs_db (hoặc fallback DEFAULT_NPCS_DB):
       - Loved items: +120 điểm thiện cảm, +40đ thưởng, mở hộp thoại expression='love'.
       - Liked items: +65 điểm thiện cảm, +25đ thưởng, mở hộp thoại expression='happy'.
       - Hated items: -50 điểm thiện cảm, mở hộp thoại expression='sad'.
    5. Kiểm tra mốc tim: nếu vừa đạt Mốc 3 ♥ (+50G, giảm 20% Xưởng) hoặc Mốc 5 ♥ (+120G, mở Đơn đặc biệt),
       thưởng ngay Vàng tri ân và gửi thông báo mở khóa đặc quyền!
    """
    if getattr(game, "game_over", False):
        return False
    if not hasattr(game, "robot") or getattr(game.robot, "stun_timer", 0.0) > 0.0:
        return False

    ensure_game_state(game)

    # 1. Tìm NPC gần nhất trong bản đồ hiện tại
    active_npcs = (
        game.interior_npcs
        if getattr(game, "in_interior", False)
        else getattr(game, "npcs", [])
    )
    if not active_npcs:
        if hasattr(game, "set_banner"):
            game.set_banner("Không có cư dân nào ở gần để tặng quà!", (235, 215, 155))
        return False

    nearest_npc = min(active_npcs, key=lambda n: math.hypot(n.x - game.robot.x, n.y - game.robot.y))
    dist_m = px_to_m(math.hypot(nearest_npc.x - game.robot.x, nearest_npc.y - game.robot.y))

    if dist_m > 2.40:
        if hasattr(game, "set_banner"):
            game.set_banner(
                f"Hãy tiến lại gần {nearest_npc.name} (khoảng cách <= 2.4m) rồi bấm [G] để tặng quà!",
                (235, 215, 155),
            )
        return False

    # Kiểm tra trạng thái NPC không bị choáng
    if nearest_npc.knockdown_timer > 0.0 or getattr(nearest_npc, "is_run_over_dead", False):
        if hasattr(game, "set_banner"):
            game.set_banner(
                f"{nearest_npc.name} đang bị choáng sau va chạm, không thể nhận quà lúc này!",
                (255, 120, 120),
            )
        return False

    # 2. Kiểm tra Khay Chứa Đồ có vật phẩm không
    inventory = getattr(game.robot, "inventory", [])
    if not inventory:
        if hasattr(game, "set_banner"):
            game.set_banner(
                "Khay Chứa Đồ đang trống! Hãy thu hoạch nông sản hoặc câu cá trước khi tặng quà [G].",
                (255, 185, 120),
            )
        return False

    # Tự động xoay mặt Robot nhìn vào NPC
    game.robot.theta = math.atan2(nearest_npc.y - game.robot.y, nearest_npc.x - game.robot.x)
    game.robot.v_mps = 0.0
    game.robot.vx = 0.0
    game.robot.vy = 0.0

    # 3. Kiểm tra đứng phía trước NPC (check_front_interaction hoặc dung sai d_m <= 1.65 và delta_npc_deg <= 50)
    ok_all, details = check_front_interaction(game.robot, nearest_npc)
    lenient_front = (details.get("d_m", 99.0) <= 1.65 and details.get("delta_npc_deg", 99.0) <= 50.0)

    if not (ok_all or lenient_front):
        if hasattr(game, "set_banner"):
            game.set_banner(
                f"Hãy bước vào Quạt Xanh phía trước mặt {nearest_npc.name} (d <= 1.65m, góc <= 50°) rồi bấm [G]!",
                (255, 195, 95),
            )
        return False

    # 4. Lấy vật phẩm ở ô đang chọn (selected_slot) và xóa khỏi khay đồ
    selected_slot = getattr(game, "selected_slot", 0)
    if selected_slot < 0 or selected_slot >= len(inventory):
        selected_slot = 0
    gift_key = inventory[selected_slot]
    game.robot.remove_item(gift_key)
    item_vi = ITEM_NAMES_VI.get(gift_key, gift_key)

    # 5. Tra cứu sở thích quà tặng của NPC
    npcs_db = getattr(game.state, "npcs_db", DEFAULT_NPCS_DB)
    npc_info = npcs_db.get(nearest_npc.name, DEFAULT_NPCS_DB.get(nearest_npc.name, {}))
    loved_items = npc_info.get("loved_items", ["bread", "apple", "peach", "strawberry"])
    liked_items = npc_info.get("liked_items", ["orange", "corn", "carrot", "tomato", "cabbage"])
    hated_items = npc_info.get("hated_items", ["fish", "parcel"])

    old_hearts = game.dialogue.get_hearts(nearest_npc.name)

    if gift_key in loved_items:
        pts_delta = 120
        score_delta = 40
        expression = "love"
        emote = "♥"
        speech = (
            f"Ôi tuyệt vời quá! Món [{item_vi}] này chính là thứ mình yêu thích nhất! "
            f"Cảm ơn FarmBot tốt bụng nhiều lắm, bạn thật chu đáo ♥!"
        )
    elif gift_key in hated_items:
        pts_delta = -50
        score_delta = 0
        expression = "sad"
        emote = "!"
        speech = (
            f"Ơ kìa... Thật ra mình không thích món [{item_vi}] này chút nào... "
            f"Nhưng dù sao cũng cảm ơn bạn đã ghé thăm."
        )
    else:
        pts_delta = 65
        score_delta = 25
        expression = "happy"
        emote = "♪"
        speech = (
            f"Cảm ơn FarmBot nhé! Món [{item_vi}] tươi ngon này rất hợp ý mình ♪!"
        )

    # 6. Điều chỉnh thiện cảm, điểm số và hiệu ứng
    new_hearts = game.dialogue.adjust_friendship(nearest_npc.name, pts_delta)
    nearest_npc.handoff_timer = 1.4
    nearest_npc.trigger_emote(emote, 3.0)

    if score_delta > 0 and hasattr(game, "add_score"):
        game.add_score(score_delta, f"Tặng {item_vi} cho {nearest_npc.name}")

    # 7. Kiểm tra Mốc 3 ♥ và Mốc 5 ♥
    milestone_rewards = []
    bonus_gold = 0

    if old_hearts < 3 <= new_hearts:
        bonus_gold += 50
        milestone_rewards.append("Mốc 3 ♥ (+50G & Giảm giá 20% Xưởng Robin)")
    if old_hearts < 5 <= new_hearts:
        bonus_gold += 120
        milestone_rewards.append("Mốc 5 ♥ (+120G & Mở Đơn Đặt Hàng Đặc Biệt)")

    if bonus_gold > 0:
        game.gold = getattr(game, "gold", 0) + bonus_gold
        reward_desc = " & ".join(milestone_rewards)
        speech += f"\n★ [TRI ÂN]: {nearest_npc.name} gửi tặng bạn {bonus_gold}G và mở khóa đặc quyền mới!"
        if hasattr(game, "set_banner"):
            game.set_banner(
                f"CHÚC MỪNG! Đạt {reward_desc} cùng {nearest_npc.name}!",
                (255, 230, 95),
            )
    else:
        sign = "+" if pts_delta > 0 else ""
        if hasattr(game, "set_banner"):
            b_col = (125, 245, 155) if pts_delta > 0 else (255, 135, 135)
            game.set_banner(
                f"Đã tặng [{item_vi}] cho {nearest_npc.name} ({sign}{pts_delta} thiện cảm, {new_hearts}/5 ♥)!",
                b_col,
            )

    badge_sign = f"+{pts_delta}" if pts_delta > 0 else f"{pts_delta}"
    reward_badge = f"{badge_sign} Tim | {new_hearts}/5 ♥"
    if bonus_gold > 0:
        reward_badge += f" | +{bonus_gold}G"

    game.dialogue.open_dialogue(
        nearest_npc,
        f"Tặng Quà — {item_vi}",
        speech,
        reward_badge=reward_badge,
        expression=expression,
    )
    return True
