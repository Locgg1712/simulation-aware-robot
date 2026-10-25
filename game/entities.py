# game/entities.py
"""
Các thực thể trong thế giới FarmBot Town:
- RobotPlayer: Nhân vật Robot phục vụ có 4 ô chứa đồ, trạng thái đi chậm, hái quả, câu cá, bật lùi.
- VillagerNPC: Nhân vật dân làng với góc nhìn theta_npc, ngã ngồi 3.0s (Knockdown), bị cán qua (Run Over).
- FarmCartAGV: Xe kéo nông sản tự hành ở Map 2.
- PropObject, HarvestSpot, FishingSpot, MapPortal, FloatingText.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass
import pygame

from .constants import (
    NPC_RADIUS_M,
    ROBOT_RADIUS_M,
    ROBOT_SCREEN_SPEED_SCALE,
    angle_diff_deg,
    dir_from_angle,
    m_to_px,
    normalize_angle,
    px_to_m,
)
from .sprite_vault import SpriteVault


@dataclass
class FloatingText:
    text: str
    x: float
    y: float
    color: tuple[int, int, int]
    timer: float = 1.6
    vy: float = -28.0


@dataclass
class HarvestSpot:
    """Cây ăn quả hoặc Thửa ruộng nông sản có thể thu hoạch (1.5s)."""
    spot_id: str
    title: str
    item_key: str
    x: float          # Điểm Robot đứng để thu hoạch (mép ruộng / gốc cây)
    y: float
    kind: str         # "fruit_tree" | "crop_plot"
    tree_sprite: str = "tree_oak"
    crop_name: str = "strawberry"
    has_produce: bool = True
    regrow_timer: float = 0.0
    regrow_total: float = 16.0
    field_rect: pygame.Rect | None = None   # Vùng ruộng (pixel) để vẽ cây trồng theo hàng
    tree_x: float = 0.0                     # Góc trên-trái sprite cây ăn quả
    tree_y: float = 0.0
    tree_w: int = 0
    tree_h: int = 0
    crop_state: str = "ripe"                # "empty" | "growing" | "ripe"
    days_grown: int = 0
    days_needed: int = 1
    watered: bool = False
    yield_left: int = 1
    has_sprinkler: bool = False
    has_scarecrow: bool = False
    has_bio_sensor: bool = False

    @property
    def growth_stage(self) -> int:
        """Giai đoạn sinh trưởng 0..9 (0 = ruộng trống, 1..8 = đang lớn, 9 = chín)."""
        if str(self.spot_id).startswith("deco_"):
            if self.has_produce:
                return 9
            ratio = 1.0 - (self.regrow_timer / max(0.01, self.regrow_total))
            return max(1, min(8, 1 + int(ratio * 8)))
        if self.has_produce or self.crop_state == "ripe":
            return 9
        if self.kind == "crop_plot" and self.crop_state == "empty":
            return 0
        stage = 1 + int(7 * self.days_grown / max(1, self.days_needed))
        return max(1, min(8, stage))


class FarmAnimal:
    """Thú nuôi đi lại thong thả trong chuồng / đồng cỏ có hàng rào."""

    def __init__(self, sprite: str, x: float, y: float, bounds: pygame.Rect, size: int = 44):
        self.sprite = sprite
        self.x = float(x)
        self.y = float(y)
        self.bounds = bounds
        self.size = size
        self.dir_x = random.choice((-1.0, 1.0))
        self.vx = 0.0
        self.vy = 0.0
        self.timer = random.uniform(0.5, 2.5)
        self.anim = random.uniform(0.0, 6.0)

    @property
    def sort_y(self) -> float:
        return self.y + 6.0

    def update(self, dt: float):
        self.timer -= dt
        if self.timer <= 0.0:
            if random.random() < 0.45:
                self.vx, self.vy = 0.0, 0.0
                self.timer = random.uniform(1.2, 3.0)
            else:
                ang = random.uniform(0, math.tau)
                spd = random.uniform(14.0, 26.0)
                self.vx, self.vy = math.cos(ang) * spd, math.sin(ang) * spd
                self.timer = random.uniform(1.0, 2.6)
        nx = self.x + self.vx * dt
        ny = self.y + self.vy * dt
        if self.bounds.left + 18 < nx < self.bounds.right - 18:
            self.x = nx
        else:
            self.vx = -self.vx
        if self.bounds.top + 18 < ny < self.bounds.bottom - 8:
            self.y = ny
        else:
            self.vy = -self.vy
        if abs(self.vx) > 0.5:
            self.dir_x = 1.0 if self.vx > 0 else -1.0
        if abs(self.vx) + abs(self.vy) > 1.0:
            self.anim += dt * 8.0

    def draw(self, screen: pygame.Surface, vault: SpriteVault):
        moving = abs(self.vx) + abs(self.vy) > 1.0
        bob = int(abs(math.sin(self.anim)) * 2) if moving else 0
        spr = vault.scaled(self.sprite, None, self.size, flip_x=(self.dir_x > 0))
        cx, cy = int(self.x), int(self.y)
        sh = pygame.Surface((self.size, 10), pygame.SRCALPHA)
        pygame.draw.ellipse(sh, (14, 24, 12, 90), (0, 0, self.size, 10))
        screen.blit(sh, (cx - self.size // 2, cy - 4))
        if spr is not None:
            screen.blit(spr, (cx - spr.get_width() // 2, cy - spr.get_height() + 4 - bob))


@dataclass
class FishingSpot:
    """Điểm thả câu cá tại Bến Hồ Map 3."""
    spot_id: str
    title: str
    stand_x: float
    stand_y: float
    water_x: float
    water_y: float


@dataclass
class MapPortal:
    """Cổng chuyển tiếp giữa 4 Bản đồ Ngoài trời."""
    rect: pygame.Rect
    target_map_id: int
    spawn_x: float
    spawn_y: float
    spawn_theta: float
    label: str
    arrow_dir: str  # "up", "down", "left", "right"


@dataclass
class PropObject:
    """Công trình, Nhà cửa, Cây cối, Nội thất có Y-Sorting và Collider."""
    kind: str
    x: int
    y: int
    sprite: pygame.Surface
    collider: pygame.Rect
    door_rect: pygame.Rect | None = None
    house_id: str = ""
    interior_type: str = "farmhouse"
    title: str = ""
    owner_name: str = ""
    owner_folder: str = "npc_01_orange_boy"
    owner_role: str = "Cư dân"
    sort_offset: float = 0.0
    solid: bool = True
    harvest: object = None

    @property
    def sort_y(self) -> float:
        return float(self.collider.bottom) + self.sort_offset

    @property
    def view_rect(self) -> pygame.Rect:
        return pygame.Rect(self.x, self.y, self.sprite.get_width(), self.sprite.get_height())

    def draw(self, screen: pygame.Surface, vault: SpriteVault):
        if self.door_rect is not None and self.house_id != "robot_house":
            mat = vault.scaled("red_mat", self.door_rect.width + 8, 20)
            if mat is not None:
                screen.blit(mat, (self.door_rect.x - 4, self.door_rect.y + 2))
            else:
                pygame.draw.rect(screen, (208, 64, 58), self.door_rect, border_radius=3)
        screen.blit(self.sprite, (self.x, self.y))


class FarmCartAGV:
    """
    Xe đẩy nông sản tự hành (AGV) hỗ trợ Robot:
    - Chế độ 'patrol': Chạy tuần tra theo làn đường ở nông trại.
    - Chế độ 'follow': Đi theo sau Robot làm việc, mang theo thùng hàng phụ 4 ô (tự động hứng nông sản khi khay Robot đầy).
    - Chế độ 'parked': Đứng yên tại chỗ sau khi được Robot đẩy nhẹ sang một bên.
    """

    def __init__(self, x: float, y: float, waypoints: list[tuple[float, float]]):
        self.x = float(x)
        self.y = float(y)
        self.waypoints = waypoints
        self.wp_idx = 0
        self.speed = 68.0
        self.radius = 15.0
        self.theta = 0.0
        self.mode: str = "patrol"  # "patrol" | "follow" | "parked"
        self.cargo: list[dict] = []
        self.max_cargo: int = 4
        self.push_vx: float = 0.0
        self.push_vy: float = 0.0

    @property
    def sort_y(self) -> float:
        return self.y + 12.0

    def apply_push(self, ux: float, uy: float, strength: float = 115.0):
        """Nhận lực đẩy nhẹ từ Robot khi Robot chạm vào AGV."""
        self.push_vx = ux * strength
        self.push_vy = uy * strength
        if abs(ux) + abs(uy) > 1e-3:
            self.theta = math.atan2(uy, ux)

    def toggle_follow_mode(self) -> str:
        """Chuyển đổi giữa chế độ Đi Theo Robot ('follow'), Đứng Yên ('parked') và Tuần Tra ('patrol')."""
        if self.mode == "patrol":
            self.mode = "follow"
        elif self.mode == "follow":
            self.mode = "parked"
        else:
            self.mode = "patrol"
        return self.mode

    def update(self, dt: float, robot_x: float, robot_y: float, game=None):
        # 1. Xử lý quán tính khi bị Robot đẩy nhẹ (Push mechanic)
        if math.hypot(self.push_vx, self.push_vy) > 4.0:
            nx = self.x + self.push_vx * dt
            ny = self.y + self.push_vy * dt
            can_move = True
            if game is not None and hasattr(game, "is_circle_blocked"):
                can_move = not game.is_circle_blocked(nx, ny, self.radius * 0.85)
            else:
                can_move = (36.0 <= nx <= SCREEN_W - 36.0 and 48.0 <= ny <= SCREEN_H - 48.0)
            if can_move:
                self.x, self.y = nx, ny
            decay = max(0.0, 1.0 - 7.5 * dt)
            self.push_vx *= decay
            self.push_vy *= decay

        # 2. Chế độ 'parked': Đứng yên tại vị trí đã đẩy tới
        if self.mode == "parked":
            return

        # 3. Chế độ 'follow': Đi theo sau lưng Robot để hỗ trợ chở nông sản
        if self.mode == "follow":
            rob_theta = getattr(getattr(game, "robot", None), "theta", self.theta)
            target_x = robot_x - math.cos(rob_theta) * 46.0
            target_y = robot_y - math.sin(rob_theta) * 46.0
            dx, dy = target_x - self.x, target_y - self.y
            dist_to_target = math.hypot(dx, dy)
            dist_to_robot = math.hypot(robot_x - self.x, robot_y - self.y)
            if dist_to_robot <= 44.0 or dist_to_target <= 10.0:
                return
            follow_speed = 142.0 if dist_to_robot > 95.0 else 108.0
            ux, uy = dx / dist_to_target, dy / dist_to_target
            self.theta = math.atan2(uy, ux)
            nx = self.x + ux * follow_speed * dt
            ny = self.y + uy * follow_speed * dt
            if game is not None and hasattr(game, "is_circle_blocked"):
                if not game.is_circle_blocked(nx, ny, self.radius * 0.8):
                    self.x, self.y = nx, ny
                elif not game.is_circle_blocked(nx, self.y, self.radius * 0.8):
                    self.x = nx
                elif not game.is_circle_blocked(self.x, ny, self.radius * 0.8):
                    self.y = ny
            else:
                self.x, self.y = nx, ny
            return

        # 4. Chế độ 'patrol': Chạy tuần tra theo tuyến đường cố định
        if not self.waypoints:
            return
        if math.hypot(robot_x - self.x, robot_y - self.y) < 44.0:
            return
        tx, ty = self.waypoints[self.wp_idx]
        dx, dy = tx - self.x, ty - self.y
        dist = math.hypot(dx, dy)
        if dist < 8.0:
            self.wp_idx = (self.wp_idx + 1) % len(self.waypoints)
            return
        self.theta = math.atan2(dy, dx)
        self.x += (dx / dist) * self.speed * dt
        self.y += (dy / dist) * self.speed * dt

    def draw(
        self,
        screen: pygame.Surface,
        vault: SpriteVault,
        font: pygame.font.Font | None = None,
        robot_x: float = -999.0,
        robot_y: float = -999.0,
    ):
        cx, cy = int(round(self.x)), int(round(self.y))
        c, s = math.cos(self.theta), math.sin(self.theta)
        if abs(c) >= abs(s):
            rel = "Agv right" if c >= 0 else "Agv left"
            spr = vault.scaled(rel, None, 48)
        else:
            rel = "Agv front" if s >= 0 else "Agv back"
            spr = vault.scaled(rel, None, 48)
        sh = pygame.Surface((34, 12), pygame.SRCALPHA)
        pygame.draw.ellipse(sh, (14, 24, 12, 95), (0, 0, 34, 12))
        screen.blit(sh, (cx - 17, cy + 6))
        if spr is not None:
            screen.blit(spr, (cx - spr.get_width() // 2, cy - spr.get_height() + 14))

        # Vẽ các nông sản đang chất trên thùng xe AGV
        if self.cargo:
            offsets = [(-10, -18), (4, -18), (-10, -8), (4, -8)]
            for idx, entry in enumerate(self.cargo[:4]):
                ik = entry.get("item_key", "apple") if isinstance(entry, dict) else str(entry)
                ico = vault.get_item_icon(ik, 14)
                if ico is not None:
                    ox, oy = offsets[idx]
                    screen.blit(ico, (cx + ox, cy + oy))

        # Vẽ nhãn trạng thái AGV và hướng dẫn tương tác khi đứng gần
        if font is not None:
            dist_rob = math.hypot(robot_x - self.x, robot_y - self.y)
            if self.mode == "follow":
                tag = f"[AGV ĐI THEO: {len(self.cargo)}/{self.max_cargo}]"
                t_col = (115, 255, 165)
                b_col = (65, 215, 120)
            elif self.mode == "parked":
                tag = f"[AGV ĐANG ĐỖ: {len(self.cargo)}/{self.max_cargo}]"
                t_col = (255, 225, 125)
                b_col = (215, 165, 65)
            elif dist_rob <= 76.0 or self.cargo:
                tag = f"Xe Kéo AGV ({len(self.cargo)}/{self.max_cargo}) — [E]/[C] Gọi Đi Theo"
                t_col = (235, 242, 255)
                b_col = (145, 185, 225)
            else:
                tag = ""
                t_col = (255, 255, 255)
                b_col = (120, 120, 120)

            if tag:
                lbl = font.render(tag, True, t_col)
                bx = max(6, min(screen.get_width() - lbl.get_width() - 12, cx - lbl.get_width() // 2 - 4))
                by = max(6, cy - 46)
                bg = pygame.Surface((lbl.get_width() + 8, 17), pygame.SRCALPHA)
                bg.fill((22, 28, 34, 215))
                screen.blit(bg, (bx, by))
                pygame.draw.rect(screen, b_col, (bx, by, lbl.get_width() + 8, 17), 1, border_radius=4)
                screen.blit(lbl, (bx + 4, by + 1))


class VillagerNPC:
    """Nhân vật Cư dân trong thị trấn."""

    def __init__(
        self,
        name: str,
        role: str,
        x: float,
        y: float,
        folder: str,
        theta: float = math.pi / 2.0,
        patrol_points: list[tuple[float, float]] | None = None,
        is_stationary: bool = False,
    ):
        self.name = name
        self.role = role
        self.x = float(x)
        self.y = float(y)
        self.folder = folder
        self.theta = normalize_angle(theta)
        self.radius = m_to_px(NPC_RADIUS_M)

        self.patrol_points = patrol_points or []
        self.wp_idx = 0
        self.is_stationary = is_stationary
        self.default_theta = self.theta

        self.base_speed = random.uniform(54.0, 72.0)
        self.vx = 0.0
        self.vy = 0.0
        self.anim_timer = random.uniform(0.0, 6.0)
        self.pause_timer = 0.0

        self.knockdown_timer = 0.0
        self.knockdown_grace = 0.0
        self.is_run_over_dead = False
        self.handoff_timer = 0.0
        self.emote: str | None = None
        self.emote_timer = 0.0
        self.yield_reward_cooldown = 0.0
        self.intrusion_step_cooldown = 0.0
        self.is_home_at_night = False

    @property
    def sort_y(self) -> float:
        return self.y + 10.0

    @property
    def speed_mps(self) -> float:
        return math.hypot(self.vx, self.vy) / ROBOT_SCREEN_SPEED_SCALE

    def trigger_emote(self, text: str, duration: float = 1.8):
        self.emote = text
        self.emote_timer = max(self.emote_timer, duration)

    def update(self, dt: float, game):
        if getattr(self, "is_home_at_night", False):
            self.vx = 0.0
            self.vy = 0.0
            return
        if self.emote_timer > 0.0:
            self.emote_timer = max(0.0, self.emote_timer - dt)
            if self.emote_timer <= 0.0:
                self.emote = None

        if self.yield_reward_cooldown > 0.0:
            self.yield_reward_cooldown = max(0.0, self.yield_reward_cooldown - dt)
        if self.intrusion_step_cooldown > 0.0:
            self.intrusion_step_cooldown = max(0.0, self.intrusion_step_cooldown - dt)
        if self.handoff_timer > 0.0:
            self.handoff_timer = max(0.0, self.handoff_timer - dt)
        if self.knockdown_grace > 0.0:
            self.knockdown_grace = max(0.0, self.knockdown_grace - dt)

        if self.is_run_over_dead:
            self.vx = 0.0
            self.vy = 0.0
            return

        if self.knockdown_timer > 0.0:
            self.knockdown_timer = max(0.0, self.knockdown_timer - dt)
            self.vx = 0.0
            self.vy = 0.0
            return

        dist_m = px_to_m(math.hypot(game.robot.x - self.x, game.robot.y - self.y))
        angle_to_robot = math.atan2(game.robot.y - self.y, game.robot.x - self.x)
        if dist_m <= 1.85 and angle_diff_deg(angle_to_robot, self.theta) <= 55.0:
            self.vx = 0.0
            self.vy = 0.0
            return

        if self.is_stationary or not self.patrol_points:
            self.vx = 0.0
            self.vy = 0.0
            self.theta = self.default_theta
            return

        if self.pause_timer > 0.0:
            self.pause_timer = max(0.0, self.pause_timer - dt)
            self.vx = 0.0
            self.vy = 0.0
            return

        tx, ty = self.patrol_points[self.wp_idx]
        dx, dy = tx - self.x, ty - self.y
        dist = math.hypot(dx, dy)
        if dist < 10.0:
            self.wp_idx = (self.wp_idx + 1) % len(self.patrol_points)
            if random.random() < 0.35:
                self.pause_timer = random.uniform(1.0, 2.2)
            return

        self.theta = math.atan2(dy, dx)
        self.vx = (dx / dist) * self.base_speed
        self.vy = (dy / dist) * self.base_speed
        nx = self.x + self.vx * dt
        ny = self.y + self.vy * dt
        if not game.is_circle_blocked(nx, ny, self.radius):
            self.x, self.y = nx, ny
        else:
            self.wp_idx = (self.wp_idx + 1) % len(self.patrol_points)

        self.anim_timer += dt * 7.5

    def draw(
        self,
        screen: pygame.Surface,
        vault: SpriteVault,
        font_small: pygame.font.Font,
        sim_time: float,
        quest_marker: str | None = None,
    ):
        if getattr(self, "is_home_at_night", False):
            return
        cx, cy = int(round(self.x)), int(round(self.y))

        sh = pygame.Surface((28, 11), pygame.SRCALPHA)
        pygame.draw.ellipse(sh, (14, 24, 12, 105), (0, 0, 28, 11))
        screen.blit(sh, (cx - 14, cy + 5))

        facing_dir = dir_from_angle(self.theta)
        if self.is_run_over_dead:
            pose_name = "die"
            target_h = 42
        elif self.knockdown_timer > 0.0:
            pose_name = "hurt" if self.knockdown_timer > 2.1 else "sit"
            target_h = 58
        elif self.handoff_timer > 0.0:
            pose_name = "pick_up" if self.handoff_timer > 0.6 else "put_down"
            target_h = 64
        elif (
            self.pause_timer > 0.0
            and not self.is_stationary
            and any(k in self.role.lower() for k in ("vườn", "rau", "nông", "thu hoạch"))
        ):
            # NPC nông dân nhiều hướng dừng lại cúi nhặt nông sản khi nghỉ giữa tuyến tuần tra
            pose_name = "pick_up"
            target_h = 64
        else:
            pose_name = facing_dir
            target_h = 64

        spr = vault.scaled(f"characters/{self.folder}/{pose_name}", None, target_h)
        if spr is None and vault.exists(self.folder):
            # NPC 1 hướng (npc_red, npc_old, npc_green, npc_brown, npc_black, npc_blonde, npc_purple)
            if self.is_run_over_dead:
                spr = vault.scaled(self.folder, None, 52, rotate_deg=90)
            elif self.knockdown_timer > 0.0:
                spr = vault.scaled(self.folder, None, 54, rotate_deg=22)
            else:
                spr = vault.scaled(self.folder, None, target_h)
        elif spr is None and vault.npc_folders:
            fallback_folder = vault.npc_folders[sum(ord(c) for c in self.name) % len(vault.npc_folders)]
            self.folder = fallback_folder
            spr = vault.scaled(f"characters/{self.folder}/{pose_name}", None, target_h)
        is_moving = math.hypot(self.vx, self.vy) > 4.0 and self.knockdown_timer <= 0.0
        if is_moving:
            bob = int(round(abs(math.sin(self.anim_timer)) * 3.0))
        elif self.handoff_timer > 0.0 and self.knockdown_timer <= 0.0:
            bob = int(round(abs(math.sin(sim_time * 12.0)) * 3.0))
        else:
            bob = 0

        if spr is not None:
            screen.blit(spr, (cx - spr.get_width() // 2, cy - spr.get_height() + 13 - bob))
            top_y = cy - spr.get_height() + 6
        else:
            pygame.draw.circle(screen, (235, 128, 92), (cx, cy - 12), 14)
            top_y = cy - 34

        if self.knockdown_timer > 0.0 and not self.is_run_over_dead:
            for i in range(3):
                ang = sim_time * 6.5 + i * (math.tau / 3.0)
                sx = cx + int(math.cos(ang) * 16)
                sy = top_y - 4 + int(math.sin(ang) * 6)
                pygame.draw.circle(screen, (255, 232, 64), (sx, sy), 4)
                pygame.draw.circle(screen, (212, 118, 24), (sx, sy), 4, 1)
            lbl = font_small.render(f"CHOÁNG {self.knockdown_timer:.1f}s", True, (255, 235, 90))
            pygame.draw.rect(
                screen,
                (42, 22, 18),
                (cx - lbl.get_width() // 2 - 4, top_y - 24, lbl.get_width() + 8, 16),
                border_radius=4,
            )
            screen.blit(lbl, (cx - lbl.get_width() // 2, top_y - 23))
            return

        name_tag = font_small.render(self.name, True, (255, 248, 225))
        nx = cx - name_tag.get_width() // 2
        ny = cy + 16
        pygame.draw.rect(
            screen,
            (32, 22, 14, 190),
            (nx - 4, ny - 1, name_tag.get_width() + 8, 15),
            border_radius=4,
        )
        screen.blit(name_tag, (nx, ny))

        if quest_marker:
            bounce = int(math.sin(sim_time * 6.0) * 3.0)
            q_col = (255, 218, 52) if quest_marker == "!" else (88, 242, 118)
            q_bg = (68, 38, 16) if quest_marker == "!" else (22, 64, 32)
            qx, qy = cx - 11, top_y - 24 + bounce
            pygame.draw.rect(screen, q_bg, (qx, qy, 22, 20), border_radius=6)
            pygame.draw.rect(screen, q_col, (qx, qy, 22, 20), 2, border_radius=6)
            ql = font_small.render(quest_marker, True, q_col)
            screen.blit(ql, (qx + 11 - ql.get_width() // 2, qy + 2))
        elif self.emote:
            bx, by = cx + 8, top_y - 18
            pygame.draw.rect(screen, (255, 252, 240), (bx, by, 28, 22), border_radius=6)
            pygame.draw.rect(screen, (92, 58, 32), (bx, by, 28, 22), 2, border_radius=6)
            icon_name = {"♥": "icon_heart", "♪": "icon_coin", "!": "icon_warning"}.get(self.emote)
            icon = vault.scaled(icon_name, 18, 17) if icon_name else None
            if icon is not None:
                screen.blit(icon, (bx + 5, by + 3))
            else:
                em_col = (225, 42, 58) if self.emote == "!" else (62, 46, 32)
                lbl = font_small.render(self.emote, True, em_col)
                screen.blit(lbl, (bx + 14 - lbl.get_width() // 2, by + 3))


class RobotPlayer:
    """Nhân vật Robot nông trại."""

    def __init__(self, x: float, y: float):
        self.x = float(x)
        self.y = float(y)
        self.theta = math.pi / 2.0
        self.radius = m_to_px(ROBOT_RADIUS_M)

        self.v_mps = 0.0
        self.vx = 0.0
        self.vy = 0.0
        self.slow_mode_toggle = False
        self.is_slow_active = False

        self.stun_timer = 0.0

        self.harvest_target: HarvestSpot | None = None
        self.harvest_timer = 0.0
        self.harvest_duration = 1.5

        self.fishing_spot: FishingSpot | None = None
        self.fishing_state = "idle"  # "idle" | "waiting" | "biting"
        self.fishing_timer = 0.0
        self.fishing_bite_window = 0.85

        self.inventory: list[str] = []
        self.max_inventory = 4
        self.battery: float = 100.0
        self.max_battery: float = 100.0
        self.is_charging: bool = False
        self.anim_timer = 0.0

    @property
    def sort_y(self) -> float:
        return self.y + 11.0

    @property
    def carrying_item(self) -> bool:
        return len(self.inventory) > 0

    def add_item(self, item_key: str) -> bool:
        if len(self.inventory) >= self.max_inventory:
            return False
        self.inventory.append(item_key)
        return True

    def remove_item(self, item_key: str) -> bool:
        if item_key in self.inventory:
            self.inventory.remove(item_key)
            return True
        return False

    def apply_knockback(self, from_x: float, from_y: float, game):
        dx = self.x - from_x
        dy = self.y - from_y
        dist = math.hypot(dx, dy)
        if dist < 1e-4:
            dx, dy = -math.cos(self.theta), -math.sin(self.theta)
        else:
            dx, dy = dx / dist, dy / dist

        bounce_px = m_to_px(0.40)
        for step in (1.0, 0.7, 0.4, 0.2):
            nx = self.x + dx * bounce_px * step
            ny = self.y + dy * bounce_px * step
            if not game.is_circle_blocked(nx, ny, self.radius):
                self.x, self.y = nx, ny
                break

        self.v_mps = 0.0
        self.vx, self.vy = 0.0, 0.0
        self.stun_timer = 1.0
        self.harvest_target = None
        self.fishing_state = "idle"

    def draw(
        self,
        screen: pygame.Surface,
        vault: SpriteVault,
        font_small: pygame.font.Font,
        sim_time: float,
    ):
        cx, cy = int(round(self.x)), int(round(self.y))
        facing = dir_from_angle(self.theta)

        sh = pygame.Surface((30, 12), pygame.SRCALPHA)
        pygame.draw.ellipse(sh, (14, 24, 12, 110), (0, 0, 30, 12))
        screen.blit(sh, (cx - 15, cy + 5))

        ring_col = (
            (255, 72, 72)
            if self.stun_timer > 0.0
            else ((92, 228, 255) if self.is_slow_active else (255, 232, 92))
        )
        pygame.draw.ellipse(screen, ring_col, (cx - 16, cy + 3, 32, 13), 2)

        if self.stun_timer > 0.0:
            rel = "robot/hit_carry" if self.carrying_item else f"robot/hit_{facing}"
        elif self.carrying_item and facing == "down" and self.v_mps < 0.05:
            rel = "robot/carry"
        elif self.v_mps > 0.04:
            frame = int(self.anim_timer * 10.0) % 6
            rel = f"robot/walk_{facing}_{frame}"
        else:
            rel = f"robot/idle_{facing}"

        spr = vault.scaled(rel, None, 58)
        if spr is not None:
            screen.blit(spr, (cx - spr.get_width() // 2, cy - spr.get_height() + 12))
        else:
            pygame.draw.circle(screen, (52, 138, 235), (cx, cy - 12), 15)

        if self.carrying_item:
            top_item = self.inventory[-1]
            icon = vault.get_item_icon(top_item, 22)
            ox = 10 if facing == "right" else (-10 if facing == "left" else 0)
            oy = -18 if facing != "up" else -26
            screen.blit(icon, (cx + ox - 11, cy + oy))

        hx = cx + int(math.cos(self.theta) * 20)
        hy = cy + int(math.sin(self.theta) * 20)
        pygame.draw.circle(screen, ring_col, (hx, hy), 3)

        if self.harvest_target is not None:
            ratio = min(1.0, self.harvest_timer / max(0.01, self.harvest_duration))
            bw, bh = 68, 10
            bx, by = cx - bw // 2, cy - 58
            pygame.draw.rect(screen, (32, 22, 14), (bx - 2, by - 2, bw + 4, bh + 4), border_radius=4)
            pygame.draw.rect(screen, (92, 232, 88), (bx, by, int(bw * ratio), bh), border_radius=3)
            lbl = font_small.render("Đang hái...", True, (255, 248, 210))
            screen.blit(lbl, (cx - lbl.get_width() // 2, by - 16))

        if self.fishing_state in ("waiting", "biting") and self.fishing_spot is not None:
            wx, wy = int(self.fishing_spot.water_x), int(self.fishing_spot.water_y)
            pygame.draw.line(screen, (235, 240, 245), (cx, cy - 18), (wx, wy), 2)
            bob_y = wy + (
                int(math.sin(sim_time * 24.0) * 5)
                if self.fishing_state == "biting"
                else int(math.sin(sim_time * 4.0) * 2)
            )
            pygame.draw.circle(screen, (255, 250, 240), (wx, bob_y), 6)
            pygame.draw.circle(screen, (235, 48, 48), (wx, bob_y - 2), 4)
            pygame.draw.circle(screen, (180, 230, 255), (wx, wy), 12 + int(sim_time * 12) % 8, 1)

            if self.fishing_state == "biting":
                alert = font_small.render("!! CÁ CẮN CÂU! BẤM [E] !!", True, (255, 245, 75))
                ax = wx - alert.get_width() // 2
                ay = wy - 32
                pygame.draw.rect(
                    screen,
                    (195, 28, 28),
                    (ax - 6, ay - 3, alert.get_width() + 12, 20),
                    border_radius=5,
                )
                pygame.draw.rect(
                    screen,
                    (255, 235, 90),
                    (ax - 6, ay - 3, alert.get_width() + 12, 20),
                    2,
                    border_radius=5,
                )
                screen.blit(alert, (ax, ay))
            else:
                wait_lbl = font_small.render("Đang đợi cá cắn câu...", True, (215, 242, 255))
                screen.blit(wait_lbl, (wx - wait_lbl.get_width() // 2, wy - 26))

