# game/vfx.py
"""
Mô-đun Quản lý Hiệu ứng Hình ảnh (VFX), Cảm giác Chơi (Game Feel) & Hướng dẫn Tân thủ:
- Hiệu ứng Chuyển Vùng Mượt Mà (Screen Fade In / Out Transition).
- Rung Màn Hình (Screen Shake) khi va chạm / kéo cá lớn & Hạt Bụi Bánh Xe (Dust Puff) khi Robot lăn bánh.
- Hệ thống Thông Báo Popup Góc Dưới Màn Hình (Stardew Toast Notifications).
- Checklist Hướng Dẫn Tân Thủ Tương Tác 5 Bước (Interactive Tutorial Checklist) kèm thưởng nóng +50G & +50đ.
"""

from __future__ import annotations

from dataclasses import dataclass
import math
import random
from typing import Any, Callable
import pygame

from .constants import SCREEN_H, SCREEN_W


@dataclass
class DustParticle:
    """Hạt bụi đất nhỏ mờ dần dưới bánh xe Robot."""

    x: float
    y: float
    vx: float
    vy: float
    radius: float
    max_life: float
    life: float
    color: tuple[int, int, int]


@dataclass
class ToastNotification:
    """Thẻ thông báo popup phong cách Stardew Valley xếp chồng ở góc màn hình."""

    title: str
    subtitle: str
    icon_key: str
    border_col: tuple[int, int, int]
    timer: float = 3.8
    total_time: float = 3.8


class VFXAndTutorialManager:
    """Quản lý các hiệu ứng đồ họa VFX, camera shake, toast notifications và bảng hướng dẫn tân thủ."""

    def __init__(self) -> None:
        # A. Hiệu ứng Chuyển Vùng Mượt (Screen Fade Transition)
        self.fade_alpha: float = 0.0
        self.fade_mode: str = "idle"  # "idle" | "out" | "in"
        self._fade_callback: Callable[[], Any] | None = None
        self.fade_speed: float = 480.0

        # B. Rung Màn Hình (Screen Shake) & Hạt Bụi Bánh Xe (Dust Puff)
        self.shake_timer: float = 0.0
        self.shake_duration: float = 0.35
        self.shake_intensity: float = 6.0
        self.shake_ox: float = 0.0
        self.shake_oy: float = 0.0

        self.dust_particles: list[DustParticle] = []
        self.dust_spawn_timer: float = 0.0

        # C. Thông Báo Popup Góc Màn Hình (Stardew Toast Notifications)
        self.toasts: list[ToastNotification] = []

        # D. Hướng Dẫn Tân Thủ Tương Tác (Interactive Tutorial Checklist)
        self.tutorial_visible: bool = True
        self.collapsed: bool = True
        self.tutorial_completed: bool = False
        self.tutorial_reward_claimed: bool = False

        self.steps: list[dict[str, Any]] = [
            {
                "id": "move_and_slow",
                "text": "Bước 1: Di chuyển [WASD] & bật Đi Chậm An Toàn [X]",
                "done": False,
            },
            {
                "id": "accept_order",
                "text": "Bước 2: Đứng vào Quạt Xanh trước NPC bấm [E] nhận đơn",
                "done": False,
            },
            {
                "id": "gather_item",
                "text": "Bước 3: Hái quả / Thu hoạch / Câu cá bằng phím [E]",
                "done": False,
            },
            {
                "id": "earn_gold",
                "text": "Bước 4: Giao hàng cho NPC hoặc Bán tại Thùng (Map 2)",
                "done": False,
            },
            {
                "id": "open_menus",
                "text": "Bước 5: Mở Sổ Tay [J], Xưởng [U] hoặc Tặng Quà [G]",
                "done": False,
            },
        ]

        self._has_moved: bool = False
        self._has_slowed: bool = False
        self._start_gold: int | None = None

        # Fallback fonts phòng khi chạy kiểm thử độc lập
        self._font_cache: dict[str, pygame.font.Font] = {}

    # ==================================================================
    # A. HIỆU ỨNG CHUYỂN VÙNG (SCREEN FADE TRANSITION)
    # ==================================================================
    def start_transition(
        self,
        callback: Callable[[], Any] | None = None,
        delay_exec: bool = False,
    ) -> None:
        """
        Bắt đầu chuyển cảnh làm tối màn hình rồi mở sáng mượt mà.
        Nếu delay_exec=False (mặc định), callback được thực thi ngay lập tức để code test
        và gameplay không phải chờ đợi qua frame, đồng thời fade_alpha được đặt = 210 để
        mở sáng dần (fade_mode = "in") tạo hiệu ứng thị giác mượt mà nhất!
        """
        if delay_exec:
            self._fade_callback = callback
            self.fade_mode = "out"
            self.fade_alpha = max(self.fade_alpha, 30.0)
        else:
            if callback is not None:
                try:
                    callback()
                except Exception:
                    pass
            self._fade_callback = None
            self.fade_mode = "in"
            self.fade_alpha = 210.0

    def update_fade(self, dt: float) -> None:
        """Cập nhật tiến trình tối dần (fade out) và sáng dần (fade in)."""
        if self.fade_mode == "out":
            self.fade_alpha += self.fade_speed * dt
            if self.fade_alpha >= 255.0:
                self.fade_alpha = 255.0
                if self._fade_callback is not None:
                    cb = self._fade_callback
                    self._fade_callback = None
                    try:
                        cb()
                    except Exception:
                        pass
                self.fade_mode = "in"
        elif self.fade_mode == "in":
            self.fade_alpha -= self.fade_speed * dt
            if self.fade_alpha <= 0.0:
                self.fade_alpha = 0.0
                self.fade_mode = "idle"

    def draw_screen_fade(self, screen: pygame.Surface) -> None:
        """Vẽ lớp màn tối chuyển tiếp phủ lên toàn màn hình."""
        if self.fade_alpha > 1.0:
            fade_surf = pygame.Surface(screen.get_size(), pygame.SRCALPHA)
            alpha_int = max(0, min(255, int(self.fade_alpha)))
            fade_surf.fill((16, 12, 10, alpha_int))
            screen.blit(fade_surf, (0, 0))

    # ==================================================================
    # B. RUNG MÀN HÌNH (SCREEN SHAKE) & HẠT BỤI ĐẤT (DUST PUFF)
    # ==================================================================
    def trigger_shake(self, intensity: float = 6.0, duration: float = 0.35) -> None:
        """Kích hoạt rung màn hình khi va chạm Cấp 2 hoặc khi cá lớn cắn câu."""
        self.shake_intensity = max(self.shake_intensity, intensity)
        self.shake_duration = max(self.shake_duration, duration)
        self.shake_timer = self.shake_duration

    def get_shake_offset(self) -> tuple[int, int]:
        """Trả về độ lệch camera (ox, oy) để áp dụng vào vị trí kết xuất."""
        return int(round(self.shake_ox)), int(round(self.shake_oy))

    def update_shake(self, dt: float) -> None:
        """Cập nhật độ lệch rung màn hình giảm dần theo thời gian."""
        if self.shake_timer > 0.0:
            self.shake_timer = max(0.0, self.shake_timer - dt)
            ratio = self.shake_timer / max(0.001, self.shake_duration)
            cur_amp = self.shake_intensity * ratio
            self.shake_ox = random.uniform(-cur_amp, cur_amp)
            self.shake_oy = random.uniform(-cur_amp, cur_amp)
        else:
            self.shake_ox = 0.0
            self.shake_oy = 0.0
            self.shake_intensity = 0.0

    def update_dust(self, game: Any, dt: float) -> None:
        """Sinh và cập nhật các hạt bụi đất dưới chân Robot khi di chuyển ngoài trời."""
        robot = getattr(game, "robot", None)
        in_interior = getattr(game, "in_interior", False)

        # 1. Sinh hạt bụi mới khi Robot chạy ngoài trời
        if robot is not None and not in_interior:
            v_mps = float(getattr(robot, "v_mps", 0.0))
            if v_mps > 0.15:
                self.dust_spawn_timer -= dt
                if self.dust_spawn_timer <= 0.0:
                    self.dust_spawn_timer = random.uniform(0.07, 0.11)
                    theta = float(getattr(robot, "theta", 0.0))
                    # Vị trí đuôi xe/chân sau Robot
                    bx = robot.x - math.cos(theta) * 12.0 + random.uniform(-3.5, 3.5)
                    by = robot.y - math.sin(theta) * 12.0 + 8.0 + random.uniform(-2.0, 2.0)
                    # Vận tốc tản nhẹ về phía sau
                    vx = -math.cos(theta) * random.uniform(8.0, 18.0) + random.uniform(-6.0, 6.0)
                    vy = -math.sin(theta) * random.uniform(8.0, 18.0) + random.uniform(-6.0, 6.0)
                    col = random.choice(
                        [
                            (198, 172, 134),
                            (182, 154, 118),
                            (215, 192, 152),
                        ]
                    )
                    life = random.uniform(0.35, 0.50)
                    self.dust_particles.append(
                        DustParticle(
                            x=bx,
                            y=by,
                            vx=vx,
                            vy=vy,
                            radius=random.uniform(2.4, 3.8),
                            max_life=life,
                            life=life,
                            color=col,
                        )
                    )

        # 2. Cập nhật vị trí và thời gian sống của các hạt bụi
        for p in list(self.dust_particles):
            p.x += p.vx * dt
            p.y += p.vy * dt
            p.life -= dt
            if p.life <= 0.0:
                self.dust_particles.remove(p)

    def draw_world_vfx(self, screen: pygame.Surface, game: Any) -> None:
        """Vẽ các hạt bụi đất trên mặt đất (gọi trước khi vẽ nhân vật/vật thể)."""
        if not self.dust_particles:
            return

        for p in self.dust_particles:
            ratio = max(0.0, min(1.0, p.life / p.max_life))
            alpha = int(185 * ratio)
            cur_r = max(1.0, p.radius * (1.0 + 0.35 * (1.0 - ratio)))
            size = int(cur_r * 2.0 + 4)
            surf = pygame.Surface((size, size), pygame.SRCALPHA)
            pygame.draw.circle(
                surf,
                (*p.color, alpha),
                (size // 2, size // 2),
                int(cur_r),
            )
            screen.blit(surf, (int(p.x - size // 2), int(p.y - size // 2)))

    # ==================================================================
    # C. HỆ THỐNG POPUP THÔNG BÁO (STARDEW TOAST NOTIFICATIONS)
    # ==================================================================
    def push_toast(
        self,
        title: str,
        subtitle: str = "",
        icon_key: str = "icon_coin",
        border_col: tuple[int, int, int] = (235, 190, 68),
    ) -> None:
        """Đẩy một thông báo mới vào góc màn hình (tối đa hiển thị 3 thông báo xếp chồng)."""
        if len(self.toasts) >= 3:
            self.toasts.pop(0)

        self.toasts.append(
            ToastNotification(
                title=title,
                subtitle=subtitle,
                icon_key=icon_key,
                border_col=border_col,
                timer=3.8,
                total_time=3.8,
            )
        )

    def update_toasts(self, dt: float) -> None:
        """Cập nhật đếm lùi thời gian hiển thị popup."""
        for t in list(self.toasts):
            t.timer -= dt
            if t.timer <= 0.0:
                self.toasts.remove(t)

    def _get_font(self, game: Any, size_key: str) -> pygame.font.Font:
        """Lấy font từ game hoặc tạo font dự phòng nếu chưa có."""
        if hasattr(game, f"font_{size_key}"):
            return getattr(game, f"font_{size_key}")
        if size_key not in self._font_cache:
            pt = 13 if size_key == "xs" else (15 if size_key == "sm" else 18)
            self._font_cache[size_key] = pygame.font.SysFont("Segoe UI", pt, bold=True)
        return self._font_cache[size_key]

    def _draw_toast_fallback_icon(
        self,
        surf: pygame.Surface,
        icon_key: str,
        cx: int,
        cy: int,
        r: int = 11,
    ) -> None:
        """Vẽ biểu tượng dự phòng nếu sprite PNG chưa nạp."""
        if icon_key == "icon_coin":
            pygame.draw.circle(surf, (255, 222, 64), (cx, cy), r)
            pygame.draw.circle(surf, (198, 142, 28), (cx, cy), r, 2)
            pygame.draw.circle(surf, (255, 245, 160), (cx - 2, cy - 2), max(2, r // 3))
        elif icon_key == "icon_heart":
            pygame.draw.circle(surf, (235, 48, 64), (cx - 4, cy - 3), 6)
            pygame.draw.circle(surf, (235, 48, 64), (cx + 4, cy - 3), 6)
            pygame.draw.polygon(
                surf,
                (235, 48, 64),
                [(cx - 10, cy - 1), (cx + 10, cy - 1), (cx, cy + 9)],
            )
        elif icon_key == "icon_warning":
            pts = [(cx, cy - r), (cx - r, cy + r), (cx + r, cy + r)]
            pygame.draw.polygon(surf, (255, 175, 42), pts)
            pygame.draw.polygon(surf, (84, 42, 12), pts, 2)
        elif icon_key in ("apple", "strawberry", "tomato"):
            pygame.draw.circle(surf, (224, 48, 48), (cx, cy), r)
            pygame.draw.circle(surf, (120, 24, 24), (cx, cy), r, 1)
        else:
            pygame.draw.rect(
                surf,
                (225, 182, 84),
                (cx - r, cy - r, r * 2, r * 2),
                border_radius=3,
            )

    def draw_toasts(self, screen: pygame.Surface, game: Any) -> None:
        """
        Vẽ tối đa 3 thẻ thông báo xếp chồng gọn gàng ở góc dưới bên trái màn hình.
        Tọa độ chuẩn theo yêu cầu: x = 12, y = SCREEN_H - 108 - i * 48 (ngay trên Khay Đồ).
        """
        if not self.toasts:
            return

        font_sm = self._get_font(game, "sm")
        font_xs = self._get_font(game, "xs")
        card_w = 316
        card_h = 42

        for i, toast in enumerate(self.toasts):
            base_x = 12
            base_y = SCREEN_H - 108 - i * 48

            # Hiệu ứng trượt vào (slide-in) 0.2s đầu & mờ dần (fade-out) 0.4s cuối
            t_elapsed = toast.total_time - toast.timer
            if t_elapsed < 0.20:
                p = t_elapsed / 0.20
                cur_x = int(base_x - (1.0 - p) * 90.0)
                alpha = int(255 * p)
            elif toast.timer < 0.40:
                cur_x = base_x
                alpha = int(255 * (toast.timer / 0.40))
            else:
                cur_x = base_x
                alpha = 255
            alpha = max(0, min(255, alpha))

            card_surf = pygame.Surface((card_w, card_h), pygame.SRCALPHA)
            # Nền gỗ sẫm Stardew Valley
            pygame.draw.rect(
                card_surf,
                (34, 22, 14, int(alpha * 0.94)),
                (0, 0, card_w, card_h),
                border_radius=8,
            )
            # Khung viền màu đặc trưng
            pygame.draw.rect(
                card_surf,
                (*toast.border_col, alpha),
                (0, 0, card_w, card_h),
                2,
                border_radius=8,
            )

            # Icon bên trái thẻ
            icon_drawn = False
            vault = getattr(game, "vault", None)
            if vault is not None:
                spr = (
                    vault.get_item_icon(toast.icon_key, 26)
                    if hasattr(vault, "get_item_icon")
                    else vault.scaled(toast.icon_key, 26, 26)
                )
                if spr is not None:
                    card_surf.blit(spr, (8, (card_h - 26) // 2))
                    icon_drawn = True

            if not icon_drawn:
                self._draw_toast_fallback_icon(card_surf, toast.icon_key, 21, card_h // 2)

            # Văn bản Title & Subtitle
            text_x = 42
            if toast.subtitle:
                t_lbl = font_xs.render(toast.title, True, (255, 246, 220))
                s_lbl = font_xs.render(toast.subtitle, True, (215, 230, 245))
                card_surf.blit(t_lbl, (text_x, 4))
                card_surf.blit(s_lbl, (text_x, 21))
            else:
                t_lbl = font_sm.render(toast.title, True, (255, 246, 220))
                card_surf.blit(t_lbl, (text_x, (card_h - t_lbl.get_height()) // 2))

            screen.blit(card_surf, (cur_x, base_y))

    # ==================================================================
    # D. HƯỚNG DẪN TÂN THỦ TƯƠNG TÁC (INTERACTIVE TUTORIAL CHECKLIST)
    # ==================================================================
    def _mark_step_done(self, idx: int) -> None:
        """Đánh dấu một bước trong checklist đã hoàn thành."""
        if 0 <= idx < len(self.steps) and not self.steps[idx]["done"]:
            self.steps[idx]["done"] = True

    def toggle_tutorial(self) -> bool:
        """Bật/tắt thu gọn bảng Hướng dẫn Tân thủ bằng phím tắt [H]."""
        self.collapsed = not self.collapsed
        return not self.collapsed

    def update_tutorial(self, game: Any, dt: float) -> None:
        """Tự động kiểm tra hành vi người chơi và cập nhật tiến độ 5 bước hướng dẫn."""
        robot = getattr(game, "robot", None)

        # 1. Bước 1: Di chuyển [WASD] & thử bật Đi Chậm An Toàn [X]
        if robot is not None:
            if float(getattr(robot, "v_mps", 0.0)) > 0.05:
                self._has_moved = True
            if getattr(robot, "is_slow_active", False) or getattr(robot, "slow_mode_toggle", False):
                self._has_slowed = True
            if self._has_moved and self._has_slowed:
                self._mark_step_done(0)

        # 2. Bước 2: Đứng vào Vùng Quạt Xanh trước mặt NPC bấm [E] nhận đơn
        quests = getattr(game, "quests", [])
        if any(getattr(q, "status", "") == "accepted" for q in quests) or getattr(game, "completed_quests_count", 0) > 0:
            self._mark_step_done(1)

        # 3. Bước 3: Thu hoạch Nông sản / Câu cá / Nhặt vật phẩm bằng [E]
        inv = getattr(robot, "inventory", []) if robot is not None else []
        if len(inv) > 0 or (robot is not None and getattr(robot, "harvest_timer", 0.0) > 0.0):
            self._mark_step_done(2)

        # 4. Bước 4: Giao hàng cho NPC hoặc Bán tại Thùng Giao Hàng (Map 2)
        if self._start_gold is None:
            self._start_gold = int(getattr(game, "gold", 60))
        cur_gold = int(getattr(game, "gold", 60))
        if cur_gold > self._start_gold or getattr(game, "completed_quests_count", 0) > 0:
            self._mark_step_done(3)

        # 5. Bước 5: Mở Sổ Tay [J] hoặc Xưởng Nâng Cấp [U] hoặc Tặng Quà [G]
        workshop = getattr(game, "workshop", None)
        if workshop is not None and getattr(workshop, "open", False):
            self._mark_step_done(4)

        # Kiểm tra hoàn thành toàn bộ 5 bước -> Trao thưởng nóng +50G & +50đ
        if not self.tutorial_reward_claimed and all(s["done"] for s in self.steps):
            self.tutorial_reward_claimed = True
            self.tutorial_completed = True
            self.collapsed = True

            # Thưởng nóng +50 Vàng & +50 Điểm
            if hasattr(game, "gold"):
                game.gold += 50
            if hasattr(game, "add_score"):
                game.add_score(50, "Hoàn thành Hướng Dẫn Tân Thủ")

            self.push_toast(
                title="HOÀN THÀNH TÂN THỦ!",
                subtitle="+50G Vàng & +50 Điểm Thưởng",
                icon_key="icon_coin",
                border_col=(255, 218, 54),
            )

            audio = getattr(game, "audio", None)
            if audio is not None and hasattr(audio, "play_sfx"):
                audio.play_sfx("gold")

    def draw_tutorial(self, screen: pygame.Surface, game: Any) -> None:
        """Vẽ bảng checklist hướng dẫn tân thủ (hỗ trợ thu gọn/mở rộng bằng phím [H])."""
        if not self.tutorial_visible:
            return

        font_sm = self._get_font(game, "sm")
        font_xs = self._get_font(game, "xs")

        done_count = sum(1 for s in self.steps if s["done"])
        panel_w = 396
        panel_x = SCREEN_W - panel_w - 10
        panel_y = getattr(game, "_tutorial_top_y", 142)

        if self.collapsed:
            # Dạng thu gọn: một thanh nhỏ gọn gàng ngay dưới bảng Nhiệm vụ
            bar_h = 28
            bar_surf = pygame.Surface((panel_w, bar_h), pygame.SRCALPHA)
            pygame.draw.rect(bar_surf, (34, 22, 14, 232), (0, 0, panel_w, bar_h), border_radius=6)
            b_col = (92, 245, 130) if self.tutorial_completed else (215, 162, 78)
            pygame.draw.rect(bar_surf, b_col, (0, 0, panel_w, bar_h), 2, border_radius=6)

            tag_txt = (
                f"[H] Tân Thủ: {done_count}/5 Hoàn Thành (+50G)"
                if self.tutorial_completed
                else f"[H] Hướng Dẫn Tân Thủ: {done_count}/5 Bước (Bấm [H] Mở)"
            )
            lbl = font_xs.render(tag_txt, True, (255, 238, 175))
            bar_surf.blit(lbl, (12, 5))
            screen.blit(bar_surf, (panel_x, panel_y))
            return

        # Dạng mở rộng: Bảng chi tiết 5 bước
        panel_h = 42 + len(self.steps) * 22 + 26
        panel_surf = pygame.Surface((panel_w, panel_h), pygame.SRCALPHA)
        pygame.draw.rect(panel_surf, (32, 20, 12, 238), (0, 0, panel_w, panel_h), border_radius=9)
        pygame.draw.rect(panel_surf, (215, 162, 78), (0, 0, panel_w, panel_h), 2, border_radius=9)

        # Tiêu đề bảng
        head_txt = f"HƯỚNG DẪN TÂN THỦ [H]  ({done_count}/5 HOÀN THÀNH)"
        h_lbl = font_sm.render(head_txt, True, (255, 228, 110))
        panel_surf.blit(h_lbl, (12, 10))

        # Danh sách 5 bước
        for i, step in enumerate(self.steps):
            row_y = 38 + i * 22
            box_r = pygame.Rect(12, row_y + 2, 16, 16)
            if step["done"]:
                pygame.draw.rect(panel_surf, (42, 168, 68), box_r, border_radius=3)
                pygame.draw.rect(panel_surf, (168, 255, 178), box_r, 1, border_radius=3)
                pygame.draw.lines(
                    panel_surf,
                    (255, 255, 255),
                    False,
                    [(box_r.x + 3, box_r.y + 8), (box_r.x + 7, box_r.y + 12), (box_r.x + 13, box_r.y + 4)],
                    2,
                )
                txt_col = (185, 225, 190)
            else:
                pygame.draw.rect(panel_surf, (54, 42, 34), box_r, border_radius=3)
                pygame.draw.rect(panel_surf, (155, 140, 120), box_r, 1, border_radius=3)
                txt_col = (255, 246, 225)

            s_lbl = font_xs.render(step["text"], True, txt_col)
            panel_surf.blit(s_lbl, (34, row_y + 1))

        # Dòng ghi chú phần thưởng dưới cùng
        foot_txt = (
            "Đã nhận thưởng nóng: +50G Vàng & +50 Điểm Thưởng!"
            if self.tutorial_reward_claimed
            else "Hoàn thành cả 5 bước để nhận ngay: +50G & +50 Điểm!"
        )
        foot_col = (110, 245, 145) if self.tutorial_reward_claimed else (255, 215, 95)
        f_lbl = font_xs.render(foot_txt, True, foot_col)
        panel_surf.blit(f_lbl, (12, panel_h - 22))

        screen.blit(panel_surf, (panel_x, panel_y))

    # ==================================================================
    # ĐIỀU PHỐI TỔNG THỂ (UPDATE & RENDER)
    # ==================================================================
    def update(self, game: Any, dt: float) -> None:
        """Cập nhật toàn bộ các hệ thống VFX, camera shake, toast và tutorial."""
        self.update_fade(dt)
        self.update_shake(dt)
        self.update_dust(game, dt)
        self.update_toasts(dt)
        self.update_tutorial(game, dt)

    def draw_hud_vfx(self, screen: pygame.Surface, game: Any) -> None:
        """Vẽ các thành phần giao diện HUD: Toast popup, Bảng Tutorial và Màn đen chuyển tiếp."""
        self.draw_toasts(screen, game)
        self.draw_tutorial(screen, game)
        self.draw_screen_fade(screen)
