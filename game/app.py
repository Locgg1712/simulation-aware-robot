# game/app.py
"""
Điều phối chính của trò chơi FarmBot Town: Robot Nông Trại Tốt Bụng.
Kết nối tất cả các mô-đun trong gói `game/`:
- `constants.py`
- `sprite_vault.py`
- `entities.py`
- `world_builder.py` & `terrain.py` & `maps.py`
- `quests.py`
- `safety_hri.py`
- `autopilot.py`
- `ui_renderer.py`
"""

from __future__ import annotations

import math
import os
import random
import pygame

from .atmosphere import AtmosphereManager
from .audio import SoundAndMusicManager
from .autopilot import compute_autopilot_command
from .constants import (
    GRID_COLS,
    GRID_ROWS,
    ITEM_NAMES_VI,
    ROBOT_SCREEN_SPEED_SCALE,
    ROBOT_SLOW_FACTOR,
    ROBOT_V_MAX_MPS,
    SCORE_HARVEST_FRUIT,
    SCREEN_H,
    SCREEN_W,
    T_GRASS,
)
from .dialogue import DialogueManager, try_give_gift
from .farming import FarmingManager, is_within_harvest_reach, reach_distance
from .entities import (
    FarmAnimal,
    FarmCartAGV,
    FishingSpot,
    FloatingText,
    HarvestSpot,
    MapPortal,
    PropObject,
    RobotPlayer,
    VillagerNPC,
)
from .game_state import GameState
from .journal_ui import JournalAndCompendiumModal
from .maps import (
    enter_house,
    exit_house,
    is_circle_blocked,
    load_outdoor_map,
)
from .quests import Quest, build_default_quests, distance_to_harvest_spot, handle_interact_action
from .random_events import RandomEventManager
from .safety_hri import update_safety_and_collisions
from .schedules import MinimapAndScheduleSystem
from .sprite_vault import SpriteVault
from .stardew_systems import FishingBarMinigame, RobinWorkshopManager
from .ui_renderer import build_hud_buttons, render_game
from .vfx import VFXAndTutorialManager


class FarmBotTownGame:
    """Lớp điều khiển trung tâm của trò chơi FarmBot Town."""

    def __init__(self):
        pygame.init()
        pygame.display.set_caption(
            "FarmBot Town: Robot Nông Trại Tốt Bụng — Context-Aware HRI & 5-Map World"
        )
        self.screen = pygame.display.set_mode((SCREEN_W, SCREEN_H))
        # Tắt bộ gõ IME (Unikey/Telex) trong cửa sổ Pygame để các phím W, A, S, D, E, R, F, P, X luôn nhận tức thì
        try:
            pygame.key.stop_text_input()
        except Exception:
            pass

        self.clock = pygame.time.Clock()

        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        sprites_dir = os.path.join(base_dir, "sprites", "sprites")
        self.vault = SpriteVault(sprites_dir)

        self.font_xs = pygame.font.SysFont("Segoe UI", 13, bold=True)
        self.font_sm = pygame.font.SysFont("Segoe UI", 15, bold=True)
        self.font_md = pygame.font.SysFont("Segoe UI", 18, bold=True)
        self.font_lg = pygame.font.SysFont("Segoe UI", 24, bold=True)
        self.font_xl = pygame.font.SysFont("Segoe UI", 32, bold=True)

        self.sim_time = 0.0
        self.show_interaction_fan = True
        self.autopilot_enabled = False

        # Chỉ số An toàn, Điểm số & Kinh tế Vàng Stardew (Mục 4, 6 & 8)
        self.max_hearts = 3
        self.hearts = 3
        self.comfort_score = 100.0
        self.score = 0
        self.gold = 60
        self.total_knockdowns = 0
        self.completed_quests_count = 0
        self.intrusion_accum = 0.0
        self.game_over = False
        self.game_over_reason = ""
        self.emergency_flash_timer = 0.0

        # Các hệ thống mở rộng chuẩn Stardew Valley (Mục 8, Mục 9 & Mục 10)
        self.state = GameState()
        self.dialogue = DialogueManager()
        self.atmosphere = AtmosphereManager()
        self.fishing_minigame = FishingBarMinigame()
        self.workshop = RobinWorkshopManager()
        self.schedules = MinimapAndScheduleSystem()
        self.journal = JournalAndCompendiumModal()
        self.audio = SoundAndMusicManager()
        self.vfx = VFXAndTutorialManager()
        self.random_events = RandomEventManager()
        self.selected_slot = 0

        # Trạng thái Bản đồ Hiện tại (1..4 Ngoài trời, hoặc Map 5 Trong Nhà)
        self.current_map_id = 1
        self.in_interior = False
        self.current_interior: PropObject | None = None
        self.saved_outdoor_map_id = 1
        self.saved_outdoor_pos = (SCREEN_W * 0.5, SCREEN_H * 0.55)
        self.saved_outdoor_theta = math.pi / 2.0

        # Khung phòng Nội thất (Map 5)
        self.room_rect = pygame.Rect((SCREEN_W - 640) // 2, (SCREEN_H - 448) // 2, 640, 448)

        # Dữ liệu Thế giới của Map hiện tại
        self.tiles: list[list[int]] = [
            [T_GRASS for _ in range(GRID_COLS)] for _ in range(GRID_ROWS)
        ]
        self.terrain_surface: pygame.Surface | None = None
        self.props: list[PropObject] = []
        self.npcs: list[VillagerNPC] = []
        self.interior_npcs: list[VillagerNPC] = []
        self.portals: list[MapPortal] = []
        self.harvest_spots: list[HarvestSpot] = []
        self.deco_fields: list[HarvestSpot] = []
        self.fishing_spots: list[FishingSpot] = []
        self.agvs: list[FarmCartAGV] = []
        self.animals: list[FarmAnimal] = []
        self.extra_blockers: list[pygame.Rect] = []
        self.decals: list[tuple] = []
        self.floating_texts: list[FloatingText] = []

        # Nhân vật Robot
        self.robot = RobotPlayer(SCREEN_W * 0.5, SCREEN_H * 0.58)

        # Danh sách Nhiệm vụ
        self.quests: list[Quest] = build_default_quests()
        self.quest_idx = 0

        # Thông báo trạng thái ở giữa màn hình
        self.banner_text = (
            "Chào mừng tới FarmBot Town! Hãy bước vào Vùng Quạt Xanh trước mặt Bà Evelyn và bấm [E]."
        )
        self.banner_color = (255, 244, 185)
        self.banner_timer = 7.0

        # Các nút bấm nhanh trên thanh HUD
        self.hud_buttons = build_hud_buttons()

        # Hệ thống Nông Nghiệp Theo Ngày (túi hạt giống, cửa hàng Cô Caroline).
        # PHẢI khởi tạo trước khi dựng bản đồ (world_builder dùng khi tạo ruộng).
        self.farming = FarmingManager()

        # Bắt đầu trò chơi tại Đế Sạc bên trong Xưởng & Nhà Robot (Map 4 -> Nội thất robot_house)
        self.spawn_in_robot_house_dock()

    @property
    def active_quest(self) -> Quest:
        return self.quests[self.quest_idx]

    def spawn_in_robot_house_dock(self):
        """Đặt Robot bắt đầu tại Đế Sạc bên trong Xưởng & Nhà Robot (Map 4 -> Nội thất robot_house)."""
        self.load_outdoor_map(4)
        robot_b = next((p for p in self.props if getattr(p, "house_id", "") == "robot_house"), None)
        if robot_b is not None:
            enter_house(self, robot_b, spawn_on_dock=True)

    def _try_toggle_workshop(self):
        """Chỉ mở Xưởng Cải Tiến Robot khi đang đứng trong Xưởng & Nhà Robot (Map 4)."""
        if self.workshop.open:
            self.workshop.open = False
            return
        if hasattr(self.state, "is_in_robot_house") and self.state.is_in_robot_house(self):
            self.workshop.open = True
            self.vfx._mark_step_done(4)
        else:
            self.set_banner(
                "Hãy về [Xưởng & Nhà Robot (Số 5)] tại Map 4 (Khu Dân Cư) và đứng cạnh Cánh Tay Robot [E]/[U] để nâng cấp!",
                (255, 205, 105),
            )

    def load_outdoor_map(
        self,
        map_id: int,
        spawn_pos: tuple[float, float] | None = None,
        spawn_theta: float | None = None,
    ):
        if hasattr(self, "state") and (self.harvest_spots or self.deco_fields):
            self.state.save_map_harvest_to_state(self)
        load_outdoor_map(self, map_id, spawn_pos, spawn_theta)
        if hasattr(self, "state"):
            self.state.sync_map_harvest_from_state(self)
            if hasattr(self.state, "sync_companion_agv_on_map"):
                self.state.sync_companion_agv_on_map(self)

    def enter_house(self, building: PropObject):
        if hasattr(self, "state") and (self.harvest_spots or self.deco_fields):
            self.state.save_map_harvest_to_state(self)
        if hasattr(self, "audio"):
            self.audio.play_sfx("portal")
        if hasattr(self, "vfx"):
            self.vfx.start_transition(lambda: enter_house(self, building))
        else:
            enter_house(self, building)

    def exit_house(self):
        if hasattr(self, "audio"):
            self.audio.play_sfx("portal")
        if hasattr(self, "vfx"):
            self.vfx.start_transition(lambda: exit_house(self))
        else:
            exit_house(self)

    def is_circle_blocked(self, cx: float, cy: float, radius: float) -> bool:
        return is_circle_blocked(self, cx, cy, radius)

    def reset_game(self):
        """Khởi động lại ca làm việc mới khi bấm phím [R]."""
        self.hearts = self.max_hearts
        self.comfort_score = 100.0
        self.score = 0
        self.gold = 60
        self.total_knockdowns = 0
        self.completed_quests_count = 0
        self.intrusion_accum = 0.0
        self.game_over = False
        self.game_over_reason = ""
        self.emergency_flash_timer = 0.0
        self.in_interior = False
        self.current_interior = None
        self.selected_slot = 0
        self.state = GameState()
        self.random_events = RandomEventManager()
        self.dialogue.close()
        self.fishing_minigame.active = False
        self.workshop.open = False
        self.journal.open = False
        self.robot = RobotPlayer(SCREEN_W * 0.5, SCREEN_H * 0.58)
        self.quests = build_default_quests()
        self.quest_idx = 0
        self.floating_texts.clear()
        self.farming = FarmingManager()
        self.spawn_in_robot_house_dock()
        self.set_banner(
            "Đã khởi động tại Xưởng & Nhà Robot (Map 4)! Đi xuống Cửa Ra [▼] để bắt đầu ca làm việc.",
            (130, 250, 155),
        )

    def set_banner(self, text: str, color: tuple[int, int, int] = (255, 244, 185)):
        self.banner_text = text
        self.banner_color = color
        self.banner_timer = 3.0

    def add_score(self, delta: int, reason: str, x: float | None = None, y: float | None = None):
        self.score += delta
        fx = x if x is not None else self.robot.x
        fy = (y if y is not None else self.robot.y) - 42.0
        sign = "+" if delta >= 0 else ""
        col = (98, 248, 128) if delta >= 0 else (255, 88, 88)
        self.floating_texts.append(FloatingText(f"{sign}{delta}đ ({reason})", fx, fy, col))

    def get_rank_letter(self) -> tuple[str, tuple[int, int, int]]:
        if self.game_over:
            return "F (NGẮT NGUỒN)", (255, 78, 78)
        if self.score >= 700 and self.hearts == 3:
            return "S (XUẤT SẮC)", (255, 226, 68)
        if self.score >= 400 and self.hearts >= 2:
            return "A (TỐT BỤNG)", (96, 242, 132)
        if self.score >= 150:
            return "B (ĐẠT CHUẨN)", (118, 208, 255)
        return "C (TẬP SỰ)", (225, 215, 195)

    def _update_robot(self, dt: float):
        if self.robot.stun_timer > 0.0:
            self.robot.stun_timer = max(0.0, self.robot.stun_timer - dt)
            self.robot.v_mps = 0.0
            self.robot.vx, self.robot.vy = 0.0, 0.0
            return

        # Tạm dừng di chuyển khi đang chơi Mini-game Câu Cá hoặc mở các bảng Modal
        if (
            self.fishing_minigame.active
            or self.workshop.open
            or self.journal.open
            or self.state.summary_open
            or getattr(getattr(self, "farming", None), "shop_open", False)
        ):
            self.robot.v_mps = 0.0
            self.robot.vx, self.robot.vy = 0.0, 0.0
            return

        # 1. Đang thu hoạch trái cây / nông sản (1.5s hoặc 0.75s khi nâng cấp)
        if self.robot.harvest_target is not None:
            keys_now = pygame.key.get_pressed()
            wants_move = (
                keys_now[pygame.K_w]
                or keys_now[pygame.K_s]
                or keys_now[pygame.K_a]
                or keys_now[pygame.K_d]
                or keys_now[pygame.K_UP]
                or keys_now[pygame.K_DOWN]
                or keys_now[pygame.K_LEFT]
                or keys_now[pygame.K_RIGHT]
            )
            spot = self.robot.harvest_target
            if (
                wants_move
                or not spot.has_produce
                or not is_within_harvest_reach(self.robot.x, self.robot.y, spot)
            ):
                self.robot.harvest_target = None
                self.robot.harvest_timer = 0.0
            else:
                self.robot.v_mps = 0.0
                self.robot.vx, self.robot.vy = 0.0, 0.0
                self.robot.harvest_timer += dt
                if self.robot.harvest_timer >= self.robot.harvest_duration:
                    # Quay xác suất phẩm chất sao Stardew Valley (tăng tỉ lệ Sao Bạc/Vàng khi nâng cấp fast_harvest Lv.2/Lv.3 hoặc có Cọc Cảm Biến)
                    fast_lv = int(getattr(self.workshop, "upgrade_levels", {}).get("fast_harvest", 0))
                    bio_bonus = 0.25 if getattr(spot, "has_bio_sensor", False) else 0.0
                    gold_chance = min(0.85, (0.30 if fast_lv >= 3 else (0.22 if fast_lv == 2 else 0.15)) + bio_bonus)
                    silver_chance = min(0.95, (0.65 if fast_lv >= 3 else (0.52 if fast_lv == 2 else 0.40)) + bio_bonus)
                    r_val = random.random()
                    q_lvl = 2 if r_val < gold_chance else (1 if r_val < silver_chance else 0)
                    if self.state.add_inventory_item(self, spot.item_key, quality=q_lvl):
                        self.farming.on_harvested(self, spot)
                        self.robot.battery = max(0.0, getattr(self.robot, "battery", 100.0) - 2.5)
                        self.state.save_map_harvest_to_state(self)
                        item_vi = self.state.get_item_name(spot.item_key)
                        star_str = "**" if q_lvl == 2 else ("*" if q_lvl == 1 else "")
                        self.add_score(
                            SCORE_HARVEST_FRUIT,
                            f"Thu hoạch {item_vi} {star_str}".strip(),
                            spot.x,
                            spot.y,
                        )
                        self.audio.play_sfx("harvest")
                        self.vfx.push_toast(
                            f"Thu hoạch: {item_vi} {star_str}".strip(),
                            f"Phẩm chất: {'Sao Vàng' if q_lvl == 2 else ('Sao Bạc' if q_lvl == 1 else 'Thường')}",
                            spot.item_key,
                            (132, 248, 148),
                        )
                        self.set_banner(
                            f"Đã thu hoạch {item_vi} {star_str} vào Khay Chứa Đồ! Hãy mang đi giao hoặc tặng cư dân [G].".strip(),
                            (132, 248, 148),
                        )
                    else:
                        self.set_banner(
                            f"Khay Chứa Đồ đã đầy ({self.robot.max_inventory}/{self.robot.max_inventory} ô)! Hãy giao bớt hàng trước.",
                            (255, 128, 92),
                        )
                    self.robot.harvest_target = None
                return

        # 2. Đang thả cần câu cá tại Bến Hồ Map 3
        if self.robot.fishing_state in ("waiting", "biting"):
            self.robot.v_mps = 0.0
            self.robot.vx, self.robot.vy = 0.0, 0.0
            self.robot.fishing_timer -= dt
            if self.robot.fishing_state == "waiting" and self.robot.fishing_timer <= 0.0:
                self.robot.fishing_state = "biting"
                self.robot.fishing_timer = self.robot.fishing_bite_window
                self.audio.play_sfx("bite")
                self.vfx.trigger_shake(3.0, 0.2)
                self.set_banner(
                    "!! CÁ CẮN CÂU !! Bấm phím [E] ngay lập tức để kéo cá lên!",
                    (255, 238, 82),
                )
            elif self.robot.fishing_state == "biting" and self.robot.fishing_timer <= 0.0:
                self.robot.fishing_state = "idle"
                self.robot.fishing_spot = None
                self.set_banner(
                    "Cá đã đứt lưỡi câu vì kéo chậm! Bấm [E] tại điểm câu để thả cần lại.",
                    (255, 165, 105),
                )
            return

        # 3. Nhận lệnh điều khiển từ Bàn phím hoặc AI Auto-Pilot
        keys = pygame.key.get_pressed()
        brake_pressed = keys[pygame.K_SPACE]
        shift_held = keys[pygame.K_LSHIFT] or keys[pygame.K_RSHIFT]
        radar_slow = getattr(self.robot, "radar_slow_active", False)
        self.robot.is_slow_active = self.robot.slow_mode_toggle or shift_held or radar_slow

        dx_in, dy_in = 0.0, 0.0
        if not brake_pressed:
            if keys[pygame.K_w] or keys[pygame.K_UP]:
                dy_in -= 1.0
            if keys[pygame.K_s] or keys[pygame.K_DOWN]:
                dy_in += 1.0
            if keys[pygame.K_a] or keys[pygame.K_LEFT]:
                dx_in -= 1.0
            if keys[pygame.K_d] or keys[pygame.K_RIGHT]:
                dx_in += 1.0

        if dx_in != 0.0 or dy_in != 0.0:
            self.autopilot_enabled = False
        elif self.autopilot_enabled and not brake_pressed:
            dx_in, dy_in, auto_slow = compute_autopilot_command(self, dt)
            if auto_slow:
                self.robot.is_slow_active = True

        if brake_pressed or (abs(dx_in) < 1e-4 and abs(dy_in) < 1e-4):
            if brake_pressed:
                self.robot.v_mps = 0.0
            else:
                self.robot.v_mps = max(0.0, self.robot.v_mps - 4.5 * dt)
            if self.robot.v_mps <= 0.02:
                self.robot.v_mps = 0.0
                self.robot.vx, self.robot.vy = 0.0, 0.0
                return
            ux, uy = math.cos(self.robot.theta), math.sin(self.robot.theta)
        else:
            mag = math.hypot(dx_in, dy_in)
            ux, uy = dx_in / mag, dy_in / mag
            self.robot.theta = math.atan2(uy, ux)

            target_v = (
                ROBOT_V_MAX_MPS * ROBOT_SLOW_FACTOR
                if self.robot.is_slow_active
                else ROBOT_V_MAX_MPS
            )
            # Khi Pin yếu (< 20%), Robot tự động giới hạn vận tốc ở chế độ tiết kiệm điện (0.45 m/s)
            if getattr(self.robot, "battery", 100.0) < 20.0:
                target_v = min(target_v, 0.45)
            # Gia tốc / giảm tốc mượt (L3) giúp tránh vọt lên Cấp 4 ngay tức thì khi vừa nhích phím
            if self.robot.v_mps < target_v:
                self.robot.v_mps = min(target_v, max(0.28, self.robot.v_mps) + 1.65 * dt)
            elif self.robot.v_mps > target_v:
                self.robot.v_mps = max(target_v, self.robot.v_mps - 3.8 * dt)

        px_speed = self.robot.v_mps * ROBOT_SCREEN_SPEED_SCALE
        self.robot.vx = ux * px_speed
        self.robot.vy = uy * px_speed

        # Cơ chế tự thoát kẹt (Auto-Unstuck) nếu vị trí hiện tại của Robot lỡ chạm hàng rào/vật cản
        if self.is_circle_blocked(self.robot.x, self.robot.y, self.robot.radius):
            found_free = False
            for dist_step in (4.0, 8.0, 14.0, 20.0, 28.0, 36.0):
                for ang_idx in range(12):
                    ang = ang_idx * (math.tau / 12.0)
                    tx = self.robot.x + math.cos(ang) * dist_step
                    ty = self.robot.y + math.sin(ang) * dist_step
                    if not self.is_circle_blocked(tx, ty, self.robot.radius):
                        self.robot.x, self.robot.y = tx, ty
                        found_free = True
                        break
                if found_free:
                    break

        nx = self.robot.x + self.robot.vx * dt
        ny = self.robot.y + self.robot.vy * dt

        if not self.is_circle_blocked(nx, ny, self.robot.radius):
            self.robot.x, self.robot.y = nx, ny
        elif not self.is_circle_blocked(nx, self.robot.y, self.robot.radius):
            self.robot.x = nx
        elif not self.is_circle_blocked(self.robot.x, ny, self.robot.radius):
            self.robot.y = ny
        else:
            self.robot.v_mps = 0.0
            self.robot.vx, self.robot.vy = 0.0, 0.0

        self.robot.anim_timer += dt * (0.55 if self.robot.is_slow_active else 1.0)

        # Kiểm tra chạm cổng chuyển tiếp bản đồ ngoài trời (Map Portals) với Screen Fade
        if not self.in_interior:
            rob_rect = pygame.Rect(int(self.robot.x - 10), int(self.robot.y - 10), 20, 20)
            for portal in self.portals:
                if portal.rect.colliderect(rob_rect):
                    self.audio.play_sfx("portal")
                    self.vfx.start_transition(
                        lambda p=portal: self.load_outdoor_map(
                            p.target_map_id,
                            spawn_pos=(p.spawn_x, p.spawn_y),
                            spawn_theta=p.spawn_theta,
                        )
                    )
                    return
        else:
            # Nếu đi thẳng xuống mép thảm đỏ cửa phòng trong Map 5 -> Tự động bước ra ngoài
            rx, ry = self.room_rect.x, self.room_rect.y
            rw, rh = self.room_rect.width, self.room_rect.height
            exit_mat = pygame.Rect(self.room_rect.centerx - 40, ry + rh - 30, 80, 28)
            if exit_mat.collidepoint(int(self.robot.x), int(self.robot.y)) and uy > 0.3:
                self.exit_house()

    def update(self, dt: float):
        self.audio.update(self, dt)
        self.vfx.update(self, dt)

        # Nếu đang mở Bảng Tổng Kết Cuối Ngày hoặc Sổ Tay Thị Trấn [J]: tạm dừng thời gian thế giới
        if self.state.summary_open or self.journal.open:
            return

        self.sim_time += dt
        if self.banner_timer > 0.0:
            self.banner_timer = max(0.0, self.banner_timer - dt)
        if self.emergency_flash_timer > 0.0:
            self.emergency_flash_timer = max(0.0, self.emergency_flash_timer - dt)

        for ft in list(self.floating_texts):
            ft.y += ft.vy * dt
            ft.timer -= dt
            if ft.timer <= 0.0:
                self.floating_texts.remove(ft)

        # Chỉ ruộng trang trí (deco_) còn mọc lại theo giây; ruộng thật lớn theo NGÀY (farming.advance_day)
        for spot in self.deco_fields:
            if not spot.has_produce and spot.regrow_timer > 0.0:
                spot.regrow_timer = max(0.0, spot.regrow_timer - dt)
                if spot.regrow_timer <= 0.0:
                    spot.has_produce = True

        q = self.active_quest
        if q.status == "accepted" and q.bonus_time_limit > 0.0 and q.bonus_timer > 0.0:
            q.bonus_timer = max(0.0, q.bonus_timer - dt)
            if q.bonus_timer <= 0.0 and not getattr(q, "_bonus_expired_notified", False):
                q._bonus_expired_notified = True
                self.vfx.push_toast(
                    "Hết giờ thưởng nhanh!",
                    f"Đơn {q.title} mất +30đ thưởng tốc độ",
                    "icon_warning",
                    (255, 165, 85),
                )

        if self.game_over:
            return

        # Không ép đi ngủ lúc 22:00: Robot có thể làm việc xuyên đêm!
        # Tối muộn (19:30): đa số NPC về nhà nghỉ ngơi, chỉ số ít trực đêm. Khi chạm 07:00 sáng hôm sau (360s) sẽ tự chuyển ngày mới.
        full_day_seconds = (24.0 * 60.0) / 4.0  # 360.0s thực tế = 24h trong game
        cur_hour = self.atmosphere.get_clock_hour(self.sim_time)
        if 19.5 <= cur_hour < 19.8 and not getattr(self.state, "_night_notice_shown", False):
            self.state._night_notice_shown = True
            self.set_banner(
                "19:30 Tối: Đa số cư dân đã về nhà nghỉ ngơi. Bạn có thể làm việc xuyên đêm hoặc bấm [N] Đi Ngủ!",
                (185, 225, 255),
            )
        if self.sim_time >= full_day_seconds:
            self.sim_time -= full_day_seconds
            self.state._night_notice_shown = False
            if hasattr(self.state, "rollover_new_day_continuous"):
                self.state.rollover_new_day_continuous(self)

        # Cập nhật các hệ thống Stardew Valley (Hộp thoại, Khí quyển, Mini-game Câu cá, Lịch trình, Sự kiện & Xưởng Robin)
        self.dialogue.update(dt)
        self.atmosphere.update(self, dt)
        self.fishing_minigame.update(self, dt)
        self.schedules.update_schedules(self, dt)
        self.random_events.update(self, dt)

        # Áp dụng hiệu ứng thụ động (Radar HRI giảm tốc, khay đồ, thu hoạch nhanh) TRƯỚC khi tính vận tốc Robot (L1)
        self.workshop.apply_passive_effects(self)
        self._update_robot(dt)

        # Cập nhật Năng Lượng Pin (Battery): Sạc Pin gắn liền với Ngủ [E]/[N] tại Đế Sạc trong Xưởng Robot
        self.robot.is_charging = False
        in_robot_house = hasattr(self.state, "is_in_robot_house") and self.state.is_in_robot_house(self)
        if self.robot.v_mps <= 0.05:
            drain_rate = 0.0 if in_robot_house else 0.05
        else:
            drain_rate = 0.15 if self.robot.is_slow_active else 0.32
        if not in_robot_house and (cur_hour >= 18.0 or cur_hour < 6.0):
            drain_rate += 0.08
        bat_lv = int(getattr(self.workshop, "upgrade_levels", {}).get("battery_pack", 0))
        if bat_lv >= 1:
            eff_mult = 0.55 if bat_lv >= 3 else (0.70 if bat_lv == 2 else 0.82)
            drain_rate *= eff_mult
        self.robot.battery = max(0.0, self.robot.battery - drain_rate * dt)
        if 0.0 < self.robot.battery <= 18.0 and not getattr(self.robot, "_low_bat_warned", False):
            self.robot._low_bat_warned = True
            self.set_banner(
                f"CẢNH BÁO PIN YẾU ({self.robot.battery:.0f}%)! Hãy về [Xưởng & Nhà Robot] ở Map 4 để Ngủ & Sạc Pin [E]/[N]!",
                (255, 165, 85),
            )
        elif self.robot.battery <= 0.0:
            self.spawn_in_robot_house_dock()
            self.robot.battery = 60.0
            self.robot._low_bat_warned = False
            tow_fee = min(self.gold, 20)
            self.gold -= tow_fee
            self.add_score(-15, "Cạn sạch Pin (Cứu hộ về Xưởng Robot)")
            self.vfx.push_toast(
                "HẾT PIN (0%) — CỨU HỘ VỀ XƯỞNG ROBOT",
                f"-{tow_fee}G phí kéo & Nạp khẩn cấp 60% Pin",
                "icon_warning",
                (255, 145, 75),
            )
            self.set_banner(
                f"CẠN SẠCH PIN (0%)! Kỹ sư Demetrius đã kéo bạn về Đế Sạc Xưởng Robot (-{tow_fee}G, -15đ, Nạp tạm 60%). Bấm [E]/[N] để Ngủ & Sạc 100%!",
                (255, 135, 95),
            )

        active_npcs = self.interior_npcs if self.in_interior else self.npcs
        for npc in active_npcs:
            npc.update(dt, self)

        if not self.in_interior:
            for agv in self.agvs:
                agv.update(dt, self.robot.x, self.robot.y, self)
            for ani in self.animals:
                if isinstance(ani, FarmAnimal):
                    ani.update(dt)

        update_safety_and_collisions(self, dt)

    def _handle_hud_click(self, pos: tuple[int, int]) -> bool:
        if self.game_over:
            mw, mh = 660, 350
            my = SCREEN_H // 2 - mh // 2
            btn_rect = pygame.Rect(SCREEN_W // 2 - 210, my + mh - 62, 420, 42)
            if btn_rect.collidepoint(pos):
                self.reset_game()
                return True

        # Nếu đang chơi Mini-game Câu Cá -> Click chuột đẩy thanh câu cá lên
        if self.fishing_minigame.active:
            if hasattr(self.fishing_minigame, "boost_bar"):
                self.fishing_minigame.boost_bar()
            return True

        # Nếu Bảng Tổng Kết Cuối Ngày đang mở -> click bất kỳ để bắt đầu ngày mới
        if self.state.summary_open:
            self.state.close_summary_modal(self)
            return True

        # Nếu Sổ Tay Thị Trấn [J] đang mở -> xử lý click chuyển tab, chọn NPC hoặc Lưu/Tải Slot
        if self.journal.open:
            if self.journal.handle_click(pos, self):
                return True

        # Nếu Cửa Hàng Hạt Giống Cô Caroline đang mở -> ưu tiên xử lý click mua hạt giống
        if getattr(self, "farming", None) is not None and self.farming.shop_open:
            if self.farming.handle_click(pos, self):
                return True

        # Nếu Xưởng Nâng Cấp Robin đang mở -> xử lý click mua nâng cấp hoặc đóng cửa sổ
        if self.workshop.open:
            if self.workshop.close_btn_rect.collidepoint(pos):
                self.workshop.open = False
                return True
            for idx, r_rect in enumerate(self.workshop.row_rects):
                if r_rect.collidepoint(pos):
                    self.workshop.buy_upgrade(self, idx)
                    return True

        # Kiểm tra click trực tiếp vào ô trong Khay Chứa Đồ (góc dưới bên trái) để chọn vật phẩm cầm tay
        max_slots = max(4, self.robot.max_inventory)
        slot_step = 30 if max_slots > 4 else 38
        slot_w = 26 if max_slots > 4 else 32
        start_sx = 72 if max_slots > 4 else 80
        for idx in range(max_slots):
            slot_rect = pygame.Rect(start_sx + idx * slot_step, SCREEN_H - 35, slot_w, 26)
            if slot_rect.collidepoint(pos):
                self.selected_slot = idx
                if idx < len(self.robot.inventory):
                    ikey = self.robot.inventory[idx]
                    iname = self.state.get_item_name(ikey)
                    self.set_banner(
                        f"Đang chọn ô #{idx + 1}: {iname} — Đứng trước NPC và bấm [G] để tặng quà!",
                        (255, 228, 130),
                    )
                else:
                    self.set_banner(f"Đã chọn ô trống #{idx + 1} trên Khay Chứa Đồ.", (210, 225, 240))
                return True

        for btn in self.hud_buttons:
            if btn["rect"].collidepoint(pos):
                bid = btn["id"]
                if bid == "interact":
                    handle_interact_action(self)
                elif bid == "gift":
                    try_give_gift(self)
                elif bid == "journal":
                    self.journal.toggle()
                    self.vfx._mark_step_done(4)
                elif bid == "sleep":
                    self.state.try_sleep_and_advance(self)
                elif bid == "reset":
                    self.reset_game()
                elif bid == "quest":
                    for step in range(1, len(self.quests) + 1):
                        cand_idx = (self.quest_idx + step) % len(self.quests)
                        if self.quests[cand_idx].status != "completed":
                            self.quest_idx = cand_idx
                            break
                    self.set_banner(f"Đang theo dõi: {self.active_quest.title}", (255, 238, 150))
                elif bid == "slot_cycle":
                    self.selected_slot = (self.selected_slot + 1) % max(1, self.robot.max_inventory)
                    self.set_banner(f"Đã chọn ô Khay Chứa Đồ #{self.selected_slot + 1}", (235, 245, 255))
                elif bid == "slow":
                    self.robot.slow_mode_toggle = not self.robot.slow_mode_toggle
                elif bid == "fan":
                    self.show_interaction_fan = not self.show_interaction_fan
                elif bid == "auto":
                    self.autopilot_enabled = not self.autopilot_enabled
                    state_txt = "BẬT" if self.autopilot_enabled else "TẮT"
                    self.set_banner(f"Đã {state_txt} chế độ AI Tự Hành (Auto-Pilot)", (165, 245, 255))
                elif bid == "workshop":
                    self._try_toggle_workshop()
                elif bid == "weather":
                    w_name = self.atmosphere.cycle_weather()
                    self.set_banner(
                        f"Đã chuyển thời tiết sang: {w_name} (Bấm [K] đổi Mùa, [L] bật Lễ Hội)",
                        (165, 238, 255),
                    )
                elif bid == "minimap":
                    st = self.schedules.toggle_minimap()
                    self.set_banner(f"Đã {'BẬT' if st else 'TẮT'} Bản Đồ Radar Minimap [M]", (255, 235, 135))
                elif bid == "agv_call":
                    if hasattr(self.state, "call_or_toggle_agv"):
                        self.state.call_or_toggle_agv(self)
                return True

        if self.dialogue.active:
            self.dialogue.advance_or_close()
            return True

        # Hỗ trợ click chuột trực tiếp vào thế giới để tương tác [E] nếu đứng gần
        handle_interact_action(self)
        return False

    def _handle_key_command(self, key: int, scancode: int, uni: str) -> bool:
        """Xử lý phím tắt bất kể bộ gõ tiếng Việt (Unikey/Telex) đang bật hay tắt."""
        u = (uni or "").lower()

        # 0. Nếu đang chơi Mini-game Câu Cá: bấm nhấp [E], [Space], [W], [Up], [Enter] đẩy thanh câu cá lên
        if self.fishing_minigame.active:
            if key == pygame.K_ESCAPE:
                self.fishing_minigame.active = False
                self.robot.fishing_state = "idle"
                self.robot.fishing_spot = None
                return True
            if (
                key in (pygame.K_e, pygame.K_SPACE, pygame.K_w, pygame.K_UP, pygame.K_RETURN)
                or scancode in (getattr(pygame, "KSCAN_E", -1), getattr(pygame, "KSCAN_W", -1))
                or u in ("e", "ê", "w")
            ):
                if hasattr(self.fishing_minigame, "boost_bar"):
                    self.fishing_minigame.boost_bar()
                return True

        # 1. Nếu Bảng Tổng Kết Cuối Ngày đang mở: phím [E], [Space], [Enter], [N], [ESC] sẽ sang ngày mới
        if self.state.summary_open:
            if (
                key in (pygame.K_e, pygame.K_SPACE, pygame.K_RETURN, pygame.K_ESCAPE, pygame.K_n)
                or u in ("e", "ê", "n")
            ):
                self.state.close_summary_modal(self)
                return True
            return True

        # 2. Nếu Sổ Tay Thị Trấn [J] đang mở: ưu tiên xử lý phím của Sổ Tay
        if self.journal.open:
            if self.journal.handle_key(key, uni, self):
                return True

        # 2b. Nếu Cửa Hàng Hạt Giống Cô Caroline đang mở: ưu tiên xử lý phím của Cửa Hàng
        if getattr(self, "farming", None) is not None and self.farming.shop_open:
            if self.farming.handle_key(key, uni, self):
                return True

        # 3. Nếu Xưởng Nâng Cấp Robin đang mở: ưu tiên phím [U], [ESC], [1]..[5] (Nâng cấp) & [6] (Bảo dưỡng)
        if self.workshop.open:
            if key in (pygame.K_ESCAPE, pygame.K_u) or scancode == getattr(pygame, "KSCAN_U", -1) or u in ("u", "ư"):
                self.workshop.open = False
                return True
            if key in (pygame.K_1, pygame.K_KP1) or u == "1":
                self.workshop.buy_upgrade(self, 0)
                return True
            if key in (pygame.K_2, pygame.K_KP2) or u == "2":
                self.workshop.buy_upgrade(self, 1)
                return True
            if key in (pygame.K_3, pygame.K_KP3) or u == "3":
                self.workshop.buy_upgrade(self, 2)
                return True
            if key in (pygame.K_4, pygame.K_KP4) or u == "4":
                self.workshop.buy_upgrade(self, 3)
                return True
            if key in (pygame.K_5, pygame.K_KP5) or u == "5":
                self.workshop.buy_upgrade(self, 4)
                return True
            if key in (pygame.K_6, pygame.K_KP6) or u == "6":
                self.workshop.buy_maintenance_pack(self)
                return True
            return True

        if key == pygame.K_ESCAPE:
            if self.dialogue.active:
                self.dialogue.close()
                return True
            if self.in_interior:
                self.exit_house()
                return True
            return False  # Báo hiệu thoát game
        elif key == pygame.K_r or scancode == getattr(pygame, "KSCAN_R", -1) or u == "r":
            self.reset_game()
        elif (
            key in (pygame.K_e, pygame.K_RETURN)
            or scancode == getattr(pygame, "KSCAN_E", -1)
            or u in ("e", "ê")
        ):
            handle_interact_action(self)
        elif key == pygame.K_SPACE and self.dialogue.active:
            self.dialogue.advance_or_close()
        elif key == pygame.K_g or scancode == getattr(pygame, "KSCAN_G", -1) or u == "g":
            try_give_gift(self)
        elif key == pygame.K_j or scancode == getattr(pygame, "KSCAN_J", -1) or u == "j":
            self.journal.toggle()
            self.vfx._mark_step_done(4)
        elif key == pygame.K_n or scancode == getattr(pygame, "KSCAN_N", -1) or u == "n":
            self.state.try_sleep_and_advance(self)
        elif key == pygame.K_u or scancode == getattr(pygame, "KSCAN_U", -1) or u in ("u", "ư"):
            self._try_toggle_workshop()
        elif key == pygame.K_v or scancode == getattr(pygame, "KSCAN_V", -1) or u == "v":
            w_name = self.atmosphere.cycle_weather()
            self.set_banner(f"Đã chuyển thời tiết sang: {w_name}", (165, 238, 255))
        elif key == pygame.K_k or scancode == getattr(pygame, "KSCAN_K", -1) or u == "k":
            s_name = self.atmosphere.cycle_season(self)
            self.set_banner(f"Đã chuyển mùa vụ sang: {s_name}", (255, 225, 130))
        elif key == pygame.K_l or scancode == getattr(pygame, "KSCAN_L", -1) or u == "l":
            self.state.festival_active = not self.state.festival_active
            st = "BẬT" if self.state.festival_active else "TẮT"
            self.set_banner(f"Đã {st} Lễ Hội Hoa Anh Đào Thị Trấn (Map 1)!", (255, 195, 225))
        elif key == pygame.K_o or scancode == getattr(pygame, "KSCAN_O", -1) or u in ("o", "ô", "ơ"):
            self.random_events.cycle_next_event(self)
        elif key == pygame.K_h or scancode == getattr(pygame, "KSCAN_H", -1) or u == "h":
            st = self.vfx.toggle_tutorial()
            self.set_banner(f"Đã {'MỞ RỘNG' if st else 'THU GỌN'} Bảng Hướng Dẫn Tân Thủ [H]", (255, 235, 145))
        elif key == pygame.K_b or scancode == getattr(pygame, "KSCAN_B", -1) or u == "b":
            muted = self.audio.toggle_mute()
            self.set_banner(f"Âm thanh & Nhạc nền: {'ĐÃ TẮT [MUTE]' if muted else 'ĐANG BẬT'}", (185, 235, 255))
        elif key == pygame.K_c or scancode == getattr(pygame, "KSCAN_C", -1) or u == "c":
            if hasattr(self.state, "call_or_toggle_agv"):
                self.state.call_or_toggle_agv(self)
        elif key == pygame.K_z or scancode == getattr(pygame, "KSCAN_Z", -1) or u == "z":
            self.selected_slot = (self.selected_slot + 1) % max(1, self.robot.max_inventory)
            self.set_banner(f"Đã chọn ô Khay Chứa Đồ #{self.selected_slot + 1}", (235, 245, 255))
        elif key == pygame.K_q or scancode == getattr(pygame, "KSCAN_Q", -1) or u == "q":
            if getattr(self, "farming", None) is not None:
                self.farming.cycle_selected_seed(self)
        elif key == pygame.K_F5:
            self.state.save_to_slot(self, 1)
            self.vfx.push_toast("Đã Lưu Nhanh (Slot 1)", f"Ngày {self.state.day} - {self.gold}G", "icon_coin", (115, 255, 145))
        elif key == pygame.K_F9:
            self.state.load_from_slot(self, 1)
            self.vfx.push_toast("Đã Tải Nhanh (Slot 1)", f"Ngày {self.state.day} - {self.gold}G", "icon_coin", (135, 225, 255))
        elif key == pygame.K_m or scancode == getattr(pygame, "KSCAN_M", -1) or u == "m":
            st = self.schedules.toggle_minimap()
            self.set_banner(f"Đã {'BẬT' if st else 'TẮT'} Bản Đồ Radar Minimap [M]", (255, 235, 135))
        elif key == pygame.K_x or scancode == getattr(pygame, "KSCAN_X", -1) or u == "x":
            self.robot.slow_mode_toggle = not self.robot.slow_mode_toggle
            st = "BẬT" if self.robot.slow_mode_toggle else "TẮT"
            self.set_banner(f"Đã {st} Chế Độ Đi Chậm An Toàn (v = 0.30 m/s)", (130, 235, 255))
        elif key == pygame.K_f or scancode == getattr(pygame, "KSCAN_F", -1) or u == "f":
            self.show_interaction_fan = not self.show_interaction_fan
        elif key == pygame.K_p or scancode == getattr(pygame, "KSCAN_P", -1) or u == "p":
            self.autopilot_enabled = not self.autopilot_enabled
            st = "BẬT" if self.autopilot_enabled else "TẮT"
            self.set_banner(f"Đã {st} AI Tự Hành (Auto-Pilot)", (160, 245, 255))
        elif key == pygame.K_TAB:
            for step in range(1, len(self.quests) + 1):
                cand_idx = (self.quest_idx + step) % len(self.quests)
                if self.quests[cand_idx].status != "completed":
                    self.quest_idx = cand_idx
                    break
            self.set_banner(f"Đang theo dõi: {self.active_quest.title}", (255, 238, 150))
        elif key in (pygame.K_1, pygame.K_KP1) or u == "1":
            self.selected_slot = 0
            self.set_banner("Đã chọn ô Khay Chứa Đồ #1", (235, 245, 255))
        elif key in (pygame.K_2, pygame.K_KP2) or u == "2":
            self.selected_slot = 1
            self.set_banner("Đã chọn ô Khay Chứa Đồ #2", (235, 245, 255))
        elif key in (pygame.K_3, pygame.K_KP3) or u == "3":
            self.selected_slot = 2
            self.set_banner("Đã chọn ô Khay Chứa Đồ #3", (235, 245, 255))
        elif key in (pygame.K_4, pygame.K_KP4) or u == "4":
            self.selected_slot = 3
            self.set_banner("Đã chọn ô Khay Chứa Đồ #4", (235, 245, 255))
        elif key in (pygame.K_5, pygame.K_KP5) or u == "5":
            if self.robot.max_inventory >= 5:
                self.selected_slot = 4
                self.set_banner("Đã chọn ô Khay Chứa Đồ #5", (235, 245, 255))
        elif key in (pygame.K_6, pygame.K_KP6) or u == "6":
            if self.robot.max_inventory >= 6:
                self.selected_slot = 5
                self.set_banner("Đã chọn ô Khay Chứa Đồ #6", (235, 245, 255))
        return True

    def run(self):
        running = True
        while running:
            dt = min(0.05, self.clock.tick(60) / 1000.0)
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == getattr(pygame, "WINDOWFOCUSGAINED", -1):
                    try:
                        pygame.key.stop_text_input()
                    except Exception:
                        pass
                elif event.type == pygame.KEYDOWN:
                    keep = self._handle_key_command(
                        event.key,
                        getattr(event, "scancode", -1),
                        getattr(event, "unicode", ""),
                    )
                    if not keep:
                        running = False
                elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    self._handle_hud_click(event.pos)

            self.update(dt)
            render_game(self)
            pygame.display.flip()

        pygame.quit()


def main():
    game = FarmBotTownGame()
    game.run()


if __name__ == "__main__":
    main()
