# game/atmosphere.py
"""
Hệ thống Khí quyển, Chu kỳ Ngày – Đêm, Ánh sáng Động, 4 Mùa (Xuân, Hè, Thu, Đông),
Thời tiết Theo Mùa, Lễ Hội Hoa Anh Đào Thị Trấn và Vòi tưới Sprinkler
cho thế giới FarmBot Town (Mục 8.3 & 8.4 trong Context_game_farmbot.md).

Mô-đun quản lý:
1. Bốn Mùa ("spring", "summer", "fall", "winter"):
   - "spring" (Xuân): Cánh hoa anh đào hồng phấn bay lượn, Lễ Hội Hoa Anh Đào Quảng Trường.
   - "summer" (Hè): Nắng vàng trong trẻo, đom đóm lập lòe đêm hè.
   - "fall" (Thu): Lá phong đỏ/cam/vàng rơi xoay nhẹ, tint thu vàng ấm áp.
   - "winter" (Đông): Bông tuyết trắng xanh lất phất, sương băng lạnh giá mùa đông.
2. Ba chế độ thời tiết theo mùa:
   - "sunny_petals": Xuân Ấm (Hoa Anh Đào) — cánh hoa hồng phấn rơi chéo nhẹ nhàng, lắc lư hình sin.
   - "clear": Nắng Vàng Trong Trẻo — Bụi nắng vàng óng ả lơ lửng bồng bềnh.
   - "rain": Mưa Rào Nông Trại — 85 tia mưa rơi chéo + vòng tròn gợn nước tiếp đất + thúc đẩy sinh trưởng cây trồng.
3. Chu kỳ Ngày – Đêm (07:00 -> 22:00) theo thời gian mô phỏng `sim_time`.
4. Ánh sáng Động & Bóng tối môi trường:
   - Ban ngày trong trẻo (07:00 - 15:30).
   - Hoàng hôn Stardew chuyển sang cam hồng ấm áp (15:30 - 18:00).
   - Màn đêm xanh thẫm huyền ảo (18:00 - 22:00).
   - Đom đóm mùa hè chớp sáng dịu dàng khi chiều tối (hour >= 17.5).
   - Quầng sáng vàng ấm (Radial Glow) quanh đèn đường, cửa/cửa sổ nhà và Nón đèn pha Robot khi trời tối.
5. Trang trí Lễ Hội Hoa Anh Đào Thị Trấn:
   - Dây cờ tam giác nhiều màu (Festival Bunting Banners) chăng ngang Quảng Trường & quanh giếng nước.
   - Biển hiệu Lễ hội hoa anh đào nổi bật nhân đôi thiện cảm NPC!
6. Vòi tưới tự động Sprinkler:
   - Bắn tia nước xanh sáng tỏa 4 hướng quanh tâm ruộng theo chu kỳ `math.sin(sim_time * 5.0)`.
   - Tăng tốc độ mọc lại của nông sản cho các thửa ruộng được tưới mát.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass
from typing import Any, List, Optional, Tuple

import pygame

from .constants import SCREEN_H, SCREEN_W, TILE_SIZE

# Bảng tên hiển thị tiếng Việt của các chế độ thời tiết
WEATHER_NAMES_VI: dict[str, str] = {
    "sunny_petals": "Xuân Ấm (Hoa Anh Đào)",
    "clear": "Nắng Vàng Trong Trẻo",
    "rain": "Mưa Rào Nông Trại",
}

# Bảng tên hiển thị tiếng Việt của 4 Mùa
SEASON_NAMES_VI: dict[str, str] = {
    "spring": "Xuân",
    "summer": "Hè",
    "fall": "Thu",
    "winter": "Đông",
}


class PetalParticle:
    """Cánh hoa anh đào mùa xuân rơi chéo nhẹ nhàng, lắc lư hình sin qua màn hình ngoài trời."""

    def __init__(self, random_y: bool = True):
        self.x = random.uniform(-20.0, float(SCREEN_W + 20))
        self.y = (
            random.uniform(-30.0, float(SCREEN_H + 20))
            if random_y
            else random.uniform(-40.0, -10.0)
        )
        self.vx = random.uniform(32.0, 56.0)
        self.vy = random.uniform(38.0, 68.0)
        self.phase = random.uniform(0.0, math.tau)
        self.osc_speed = random.uniform(2.0, 3.4)
        self.osc_amp = random.uniform(20.0, 38.0)
        self.size = random.uniform(5.5, 9.0)
        self.angle = random.uniform(0.0, math.tau)
        self.rot_speed = random.uniform(-2.2, 2.2)
        # Sắc hồng phấn hoa anh đào tươi thắm
        self.color = random.choice(
            [
                (255, 182, 193),
                (255, 192, 203),
                (255, 212, 222),
                (246, 168, 190),
                (255, 225, 235),
            ]
        )

    def update(self, dt: float):
        self.phase += self.osc_speed * dt
        self.angle += self.rot_speed * dt
        sway = math.sin(self.phase) * self.osc_amp
        self.x += (self.vx + sway) * dt
        self.y += self.vy * dt

        # Wrap khi cánh hoa rơi khỏi màn hình
        if self.y > SCREEN_H + 20 or self.x > SCREEN_W + 30 or self.x < -30:
            self.y = random.uniform(-35.0, -10.0)
            self.x = random.uniform(-30.0, float(SCREEN_W * 0.9))
            self.phase = random.uniform(0.0, math.tau)

    def draw(self, screen: pygame.Surface):
        cx, cy = self.x, self.y
        cos_a = math.cos(self.angle)
        sin_a = math.sin(self.angle)
        length = self.size
        width = self.size * 0.52
        pts = (
            (cx + cos_a * length, cy + sin_a * length),
            (cx - sin_a * width, cy + cos_a * width),
            (cx - cos_a * length * 0.75, cy - sin_a * length * 0.75),
            (cx + sin_a * width, cy - cos_a * width),
        )
        pygame.draw.polygon(screen, self.color, [(int(px), int(py)) for px, py in pts])


class AutumnLeafParticle:
    """Hạt Lá Phong Mùa Thu màu cam/đỏ/vàng rơi xoay nhẹ nhàng trong gió thu."""

    def __init__(self, random_y: bool = True):
        self.x = random.uniform(-20.0, float(SCREEN_W + 20))
        self.y = (
            random.uniform(-30.0, float(SCREEN_H + 20))
            if random_y
            else random.uniform(-40.0, -10.0)
        )
        self.vx = random.uniform(24.0, 52.0)
        self.vy = random.uniform(34.0, 62.0)
        self.phase = random.uniform(0.0, math.tau)
        self.osc_speed = random.uniform(1.8, 3.2)
        self.osc_amp = random.uniform(22.0, 42.0)
        self.size = random.uniform(6.5, 10.0)
        self.angle = random.uniform(0.0, math.tau)
        self.rot_speed = random.uniform(-2.4, 2.4)
        # Bảng màu sắc lá phong mùa thu: Cam ấm, Đỏ phong, Vàng kim thu, Nâu cam, Đỏ thẫm
        self.color = random.choice(
            [
                (238, 108, 36),
                (214, 52, 38),
                (246, 184, 46),
                (218, 134, 42),
                (188, 44, 46),
            ]
        )

    def update(self, dt: float):
        self.phase += self.osc_speed * dt
        self.angle += self.rot_speed * dt
        sway = math.sin(self.phase) * self.osc_amp
        self.x += (self.vx + sway) * dt
        self.y += self.vy * dt

        if self.y > SCREEN_H + 25 or self.x > SCREEN_W + 35 or self.x < -35:
            self.y = random.uniform(-35.0, -10.0)
            self.x = random.uniform(-30.0, float(SCREEN_W * 0.95))
            self.phase = random.uniform(0.0, math.tau)

    def draw(self, screen: pygame.Surface):
        cx, cy = self.x, self.y
        cos_a = math.cos(self.angle)
        sin_a = math.sin(self.angle)
        s = self.size
        # Hình chiếc lá phong thu 5 nhánh nhọn đặc trưng
        local_pts = [
            (0.0, -s),
            (s * 0.45, -s * 0.45),
            (s * 0.9, -s * 0.2),
            (s * 0.5, s * 0.3),
            (s * 0.65, s * 0.85),
            (0.0, s * 0.45),
            (-s * 0.65, s * 0.85),
            (-s * 0.5, s * 0.3),
            (-s * 0.9, -s * 0.2),
            (-s * 0.45, -s * 0.45),
        ]
        pts = []
        for lx, ly in local_pts:
            rx = cx + lx * cos_a - ly * sin_a
            ry = cy + lx * sin_a + ly * cos_a
            pts.append((int(rx), int(ry)))
        if len(pts) >= 3:
            pygame.draw.polygon(screen, self.color, pts)


class SnowflakeParticle:
    """Bông Tuyết Mùa Đông màu trắng xanh rơi lất phất trên bầu trời."""

    def __init__(self, random_y: bool = True):
        self.x = random.uniform(-20.0, float(SCREEN_W + 20))
        self.y = (
            random.uniform(-20.0, float(SCREEN_H + 20))
            if random_y
            else random.uniform(-30.0, -5.0)
        )
        self.vx = random.uniform(-10.0, 15.0)
        self.vy = random.uniform(28.0, 62.0)
        self.phase = random.uniform(0.0, math.tau)
        self.pulse_speed = random.uniform(1.6, 3.2)
        self.size = random.uniform(2.0, 4.2)
        # Sắc trắng xanh tinh khôi của băng tuyết
        self.color = random.choice(
            [
                (255, 255, 255),
                (242, 248, 255),
                (225, 242, 255),
                (210, 236, 255),
            ]
        )

    def update(self, dt: float):
        self.phase += self.pulse_speed * dt
        sway = math.sin(self.phase) * 12.0
        self.x += (self.vx + sway) * dt
        self.y += self.vy * dt

        if self.y > SCREEN_H + 15 or self.x > SCREEN_W + 25 or self.x < -25:
            self.y = random.uniform(-25.0, -5.0)
            self.x = random.uniform(-20.0, float(SCREEN_W + 10))
            self.phase = random.uniform(0.0, math.tau)

    def draw(self, screen: pygame.Surface):
        cx, cy = int(self.x), int(self.y)
        r = max(1, int(self.size))
        pygame.draw.circle(screen, self.color, (cx, cy), r)
        # Vẽ tia hoa tuyết chữ thập nhẹ nếu bông tuyết đủ lớn
        if r >= 3:
            pygame.draw.line(screen, self.color, (cx - r - 1, cy), (cx + r + 1, cy), 1)
            pygame.draw.line(screen, self.color, (cx, cy - r - 1), (cx, cy + r + 1), 1)


class SunMoteParticle:
    """Hạt bụi nắng vàng óng ả lơ lửng, nhấp nháy nhẹ trong ngày nắng trong trẻo."""

    def __init__(self, random_y: bool = True):
        self.x = random.uniform(0.0, float(SCREEN_W))
        self.y = (
            random.uniform(0.0, float(SCREEN_H))
            if random_y
            else float(SCREEN_H + random.uniform(5.0, 20.0))
        )
        self.vx = random.uniform(-7.0, 7.0)
        self.vy = random.uniform(-15.0, -5.0)
        self.phase = random.uniform(0.0, math.tau)
        self.pulse_speed = random.uniform(1.8, 3.2)
        self.size = random.uniform(2.0, 3.6)
        self.color = random.choice(
            [
                (255, 248, 185),
                (255, 238, 140),
                (255, 226, 115),
            ]
        )

    def update(self, dt: float):
        self.phase += self.pulse_speed * dt
        self.x += (self.vx + math.sin(self.phase * 0.8) * 6.0) * dt
        self.y += self.vy * dt
        if self.y < -10.0 or self.x < -10.0 or self.x > SCREEN_W + 10.0:
            self.y = float(SCREEN_H + random.uniform(5.0, 20.0))
            self.x = random.uniform(0.0, float(SCREEN_W))

    def draw(self, screen: pygame.Surface):
        glow = 0.55 + 0.45 * math.sin(self.phase)
        r = int(self.color[0] * glow)
        g = int(self.color[1] * glow)
        b = int(self.color[2] * glow)
        pygame.draw.circle(screen, (r, g, b), (int(self.x), int(self.y)), int(self.size))


@dataclass
class RainSplash:
    """Vòng tròn gợn nước mờ dần khi giọt mưa tiếp đất trên cánh đồng."""

    x: float
    y: float
    radius: float = 1.5
    max_radius: float = 8.0
    timer: float = 0.22
    max_timer: float = 0.22

    def update(self, dt: float) -> bool:
        self.timer -= dt
        progress = 1.0 - max(0.0, self.timer / self.max_timer)
        self.radius = 1.5 + progress * (self.max_radius - 1.5)
        return self.timer > 0.0

    def draw(self, screen: pygame.Surface):
        alpha = int(170 * (self.timer / self.max_timer))
        if alpha <= 0:
            return
        rw = int(self.radius * 2.0)
        rh = max(2, int(self.radius * 0.9))
        sp_surf = pygame.Surface((rw + 2, rh + 2), pygame.SRCALPHA)
        pygame.draw.ellipse(sp_surf, (175, 215, 255, alpha), (1, 1, rw, rh), 1)
        screen.blit(sp_surf, (int(self.x - rw // 2), int(self.y - rh // 2)))


class RainDrop:
    """Tia mưa rơi chéo nhanh trong cơn mưa rào nông trại."""

    def __init__(self, random_y: bool = True):
        self.x = random.uniform(-60.0, float(SCREEN_W + 60))
        self.y = (
            random.uniform(-40.0, float(SCREEN_H))
            if random_y
            else random.uniform(-60.0, -10.0)
        )
        self.vx = 48.0  # Rơi nghiêng nhẹ theo chiều gió
        self.vy = random.uniform(550.0, 720.0)
        self.length = random.uniform(14.0, 22.0)
        self.ground_y = random.uniform(float(SCREEN_H * 0.35), float(SCREEN_H + 10))

    def update(self, dt: float, splashes: list[RainSplash]):
        self.x += self.vx * dt
        self.y += self.vy * dt

        if self.y >= self.ground_y or self.y > SCREEN_H:
            # Xác suất tạo vòng tròn nước bắn khi tiếp đất
            if random.random() < 0.65:
                splashes.append(
                    RainSplash(
                        x=self.x,
                        y=min(self.y, float(SCREEN_H - 10)),
                        max_radius=random.uniform(5.5, 9.5),
                        timer=random.uniform(0.18, 0.25),
                        max_timer=0.22,
                    )
                )
            # Tái tạo tia mưa mới từ trên đỉnh trời
            self.y = random.uniform(-50.0, -10.0)
            self.x = random.uniform(-60.0, float(SCREEN_W))
            self.ground_y = random.uniform(float(SCREEN_H * 0.35), float(SCREEN_H + 10))

    def draw(self, screen: pygame.Surface):
        inv_spd = self.length / math.hypot(self.vx, self.vy)
        x2 = self.x - self.vx * inv_spd
        y2 = self.y - self.vy * inv_spd
        pygame.draw.line(
            screen,
            (185, 222, 255),
            (int(self.x), int(self.y)),
            (int(x2), int(y2)),
            1,
        )


class FireflyParticle:
    """Đom đóm mùa hè phát sáng nhẹ nhàng, lượn lờ chầm chậm khi hoàng hôn / đêm về."""

    def __init__(self):
        self.x = random.uniform(40.0, float(SCREEN_W - 40))
        self.y = random.uniform(60.0, float(SCREEN_H - 80))
        self.vx = random.uniform(-14.0, 14.0)
        self.vy = random.uniform(-12.0, 12.0)
        self.phase = random.uniform(0.0, math.tau)
        self.color = (215, 255, 95)  # Sắc vàng chanh phát quang dịu mắt

    def update(self, dt: float):
        self.phase += dt * random.uniform(2.0, 3.4)
        self.x += self.vx * dt + math.sin(self.phase * 0.9) * 8.0 * dt
        self.y += self.vy * dt + math.cos(self.phase * 0.7) * 8.0 * dt

        # Giữ đom đóm trong tầm mắt
        if self.x < 30.0:
            self.vx = abs(self.vx)
        elif self.x > SCREEN_W - 30.0:
            self.vx = -abs(self.vx)
        if self.y < 50.0:
            self.vy = abs(self.vy)
        elif self.y > SCREEN_H - 60.0:
            self.vy = -abs(self.vy)

    def draw(self, screen: pygame.Surface):
        glow = max(0.0, math.sin(self.phase))
        alpha = int(glow * 210)
        if alpha <= 10:
            return
        cx, cy = int(self.x), int(self.y)
        # Quầng sáng mờ quanh đom đóm
        g_rad = int(3 + glow * 5)
        surf = pygame.Surface((g_rad * 2 + 2, g_rad * 2 + 2), pygame.SRCALPHA)
        pygame.draw.circle(
            surf,
            (self.color[0], self.color[1], self.color[2], int(alpha * 0.5)),
            (g_rad + 1, g_rad + 1),
            g_rad,
        )
        screen.blit(surf, (cx - g_rad - 1, cy - g_rad - 1))
        # Đốm sáng tâm
        pygame.draw.circle(screen, (245, 255, 185), (cx, cy), 1)


def _create_radial_glow_surface(
    radius: int,
    color: tuple[int, int, int],
    inner_alpha: int = 150,
    sub_mode: bool = False,
) -> pygame.Surface:
    """Tạo Surface quầng sáng tròn mờ dần (Radial Glow) để tái sử dụng tối ưu hiệu năng."""
    size = radius * 2
    surf = pygame.Surface((size, size), pygame.SRCALPHA)
    cx, cy = radius, radius
    steps = max(12, radius // 3)
    for i in range(steps, 0, -1):
        r = int(radius * (i / steps))
        ratio = i / steps
        alpha = int(inner_alpha * ((1.0 - ratio) ** 1.35))
        if alpha <= 0:
            continue
        if sub_mode:
            col = (0, 0, 0, alpha)
        else:
            col = (color[0], color[1], color[2], alpha)
        pygame.draw.circle(surf, col, (cx, cy), r)
    return surf


def _draw_festival_bunting(
    screen: pygame.Surface,
    p1: tuple[float, float],
    p2: tuple[float, float],
    sag: float = 16.0,
    sim_time: float = 0.0,
    flag_spacing: float = 24.0,
):
    """
    Vẽ dây cờ tam giác nhiều màu sắc (Festival Bunting Banner) nối 2 điểm p1 -> p2
    với độ võng hình parabol tự nhiên và các lá cờ tam giác rực rỡ lay nhẹ trong gió.
    """
    x1, y1 = p1
    x2, y2 = p2
    dx = x2 - x1
    dy = y2 - y1
    dist = math.hypot(dx, dy)
    if dist < 12.0:
        return

    # Bảng màu sắc cờ tam giác lễ hội tươi vui
    flag_colors = [
        (238, 55, 65),   # Đỏ cờ
        (255, 215, 45),  # Vàng tươi
        (48, 195, 95),   # Xanh lá
        (46, 148, 248),  # Xanh dương
        (255, 132, 186), # Hồng đào
        (255, 138, 38),  # Cam rực
        (175, 88, 245),  # Tím biếc
    ]

    steps = max(16, int(dist / 8.0))
    rope_pts: list[tuple[int, int]] = []
    for s in range(steps + 1):
        t = s / steps
        rx = x1 + dx * t
        parabola = 4.0 * t * (1.0 - t)
        ry = y1 + dy * t + sag * parabola
        rope_pts.append((int(rx), int(ry)))

    # 1. Vẽ dây thừng màu nâu đất
    if len(rope_pts) >= 2:
        pygame.draw.lines(screen, (132, 98, 62), False, rope_pts, 2)

    # 2. Đính các lá cờ tam giác rủ xuống dọc theo dây
    num_flags = max(2, int(dist / flag_spacing))
    for f in range(num_flags):
        t = (f + 0.5) / num_flags
        fx = x1 + dx * t
        parabola = 4.0 * t * (1.0 - t)
        fy = y1 + dy * t + sag * parabola

        # Lay động nhẹ nhàng theo chiều gió
        wind = math.sin(sim_time * 4.2 + f * 1.3) * 2.5
        col = flag_colors[f % len(flag_colors)]

        # 3 đỉnh tam giác của lá cờ: 2 đỉnh trên dây, 1 đỉnh trỏ xuống
        hw = 7.0
        tri_pts = [
            (int(fx - hw), int(fy)),
            (int(fx + hw), int(fy)),
            (int(fx + wind), int(fy + 14)),
        ]
        pygame.draw.polygon(screen, col, tri_pts)
        pygame.draw.polygon(screen, (40, 24, 16), tri_pts, 1)


class AtmosphereManager:
    """
    Quản lý Khí quyển, 4 Mùa (Xuân, Hè, Thu, Đông), Thời tiết Theo Mùa, Chu kỳ Ngày – Đêm,
    Ánh sáng Đèn đường, Trang trí Lễ Hội Hoa Anh Đào & Vòi tưới Sprinkler.
    """

    def __init__(self):
        # 4 Mùa trong năm: mặc định "spring" (Mùa Xuân)
        self.seasons: list[str] = ["spring", "summer", "fall", "winter"]
        self.current_season_idx: int = 0

        # 3 chế độ thời tiết: mặc định "sunny_petals" (Mùa Xuân Hoa Anh Đào Bay)
        self.weather_modes: list[str] = ["sunny_petals", "clear", "rain"]
        self.current_weather_idx: int = 0

        # Khởi tạo các nhóm hạt môi trường
        self.petals: list[PetalParticle] = [PetalParticle(random_y=True) for _ in range(45)]
        self.autumn_leaves: list[AutumnLeafParticle] = [
            AutumnLeafParticle(random_y=True) for _ in range(45)
        ]
        self.snowflakes: list[SnowflakeParticle] = [
            SnowflakeParticle(random_y=True) for _ in range(75)
        ]
        self.sun_motes: list[SunMoteParticle] = [
            SunMoteParticle(random_y=True) for _ in range(40)
        ]
        self.rain_drops: list[RainDrop] = [RainDrop(random_y=True) for _ in range(85)]
        self.rain_splashes: list[RainSplash] = []
        self.fireflies: list[FireflyParticle] = [FireflyParticle() for _ in range(20)]

        # Tái sử dụng một Surface kích thước màn hình để phủ bóng tối (tránh cấp phát mới mỗi frame)
        self._light_surf = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)

        # Lớp tint theo mùa tối ưu hóa hiệu năng
        self._fall_tint = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
        self._fall_tint.fill((255, 190, 110, 18))

        self._winter_tint = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
        self._winter_tint.fill((195, 225, 255, 24))

        # Caching các quầng sáng (Radial Glow surfaces) để đạt 60 FPS mượt mà
        self._lamp_glow_radius = 78
        self._lamp_glow_sub = _create_radial_glow_surface(
            78, (255, 225, 120), inner_alpha=55, sub_mode=True
        )
        self._lamp_glow_add = _create_radial_glow_surface(
            78, (255, 224, 118), inner_alpha=72, sub_mode=False
        )

        self._window_glow_radius = 52
        self._window_glow_sub = _create_radial_glow_surface(
            52, (255, 205, 100), inner_alpha=45, sub_mode=True
        )
        self._window_glow_add = _create_radial_glow_surface(
            52, (255, 205, 98), inner_alpha=54, sub_mode=False
        )

    @property
    def current_season(self) -> str:
        """Mã mùa hiện tại: 'spring' | 'summer' | 'fall' | 'winter'."""
        return self.seasons[self.current_season_idx]

    @property
    def current_season_name(self) -> str:
        """Tên tiếng Việt hiển thị của mùa hiện tại: 'Xuân' | 'Hè' | 'Thu' | 'Đông'."""
        return SEASON_NAMES_VI.get(self.current_season, "Xuân")

    def cycle_season(self, game: Any = None) -> str:
        """
        Chuyển sang mùa tiếp theo trong 4 mùa ('spring' -> 'summer' -> 'fall' -> 'winter').
        Đồng bộ với game.state.season_idx nếu có và trả về tên tiếng Việt tương ứng.
        """
        self.current_season_idx = (self.current_season_idx + 1) % len(self.seasons)
        if game is not None:
            state = getattr(game, "state", None)
            if state is not None and hasattr(state, "season_idx"):
                state.season_idx = self.current_season_idx
        return self.current_season_name

    @property
    def current_weather(self) -> str:
        """Mã thời tiết hiện tại: 'sunny_petals' | 'clear' | 'rain'."""
        return self.weather_modes[self.current_weather_idx]

    @property
    def current_weather_name(self) -> str:
        """Tên tiếng Việt hiển thị của thời tiết hiện tại."""
        return WEATHER_NAMES_VI.get(self.current_weather, "Thời Tiết Mát Mẻ")

    def cycle_weather(self) -> str:
        """Chuyển sang chế độ thời tiết tiếp theo và trả về tên tiếng Việt tương ứng."""
        self.current_weather_idx = (self.current_weather_idx + 1) % len(self.weather_modes)
        return self.current_weather_name

    def get_clock_hour(self, sim_time: float) -> float:
        """
        Tính giờ trong game từ 7.0 (07:00 sáng) đến 22.0 (22:00 đêm) theo công thức chuẩn:
        7.0 + ((sim_time * 4.0) % (15.0 * 60.0)) / 60.0
        """
        return 7.0 + ((sim_time * 4.0) % (15.0 * 60.0)) / 60.0

    def get_clock_string(self, sim_time: float) -> str:
        """Định dạng chuỗi giờ phút hiển thị trên HUD (ví dụ: '08:30', '18:15')."""
        hour_val = self.get_clock_hour(sim_time)
        h = int(hour_val)
        m = int((hour_val - h) * 60.0)
        return f"{h:02d}:{m:02d}"

    def update(self, game: Any, dt: float):
        """
        Cập nhật vị trí hạt thời tiết, hiệu ứng mưa, mùa trong năm, và vòi tưới tự động (Sprinkler).
        """
        # Đồng bộ mùa với game.state nếu bên ngoài có cập nhật
        state = getattr(game, "state", None)
        if state is not None and hasattr(state, "season_idx"):
            if isinstance(state.season_idx, int):
                self.current_season_idx = state.season_idx % len(self.seasons)

        hour = self.get_clock_hour(game.sim_time)
        mode = self.current_weather
        season = self.current_season

        # 1. Cập nhật nhóm hạt thời tiết theo chế độ
        if mode == "sunny_petals":
            for p in self.petals:
                p.update(dt)
        elif mode == "clear":
            for sm in self.sun_motes:
                sm.update(dt)
        elif mode == "rain":
            for rd in self.rain_drops:
                rd.update(dt, self.rain_splashes)

            # Cập nhật vòng tròn gợn nước tiếp đất
            for sp in list(self.rain_splashes):
                if not sp.update(dt):
                    self.rain_splashes.remove(sp)

            # Mưa rào: tự động tăng tốc độ mọc lại của cây trồng thêm 0.5 * dt
            all_spots = getattr(game, "harvest_spots", []) + getattr(game, "deco_fields", [])
            for spot in all_spots:
                if not spot.has_produce and getattr(spot, "regrow_timer", 0.0) > 0.0:
                    spot.regrow_timer = max(0.0, spot.regrow_timer - 0.5 * dt)

        # 2. Cập nhật hạt theo mùa khi không mưa
        if mode != "rain":
            if season == "fall":
                for leaf in self.autumn_leaves:
                    leaf.update(dt)
            elif season == "winter":
                for snow in self.snowflakes:
                    snow.update(dt)

        # 3. Cập nhật đom đóm khi trời chiều tối (hour >= 17.5)
        if hour >= 17.5:
            for ff in self.fireflies:
                ff.update(dt)

        # 4. Hiệu ứng Vòi tưới Sprinkler: tăng tốc độ mọc lại cho các thửa ruộng có vòi tưới
        all_field_spots = getattr(game, "harvest_spots", []) + getattr(game, "deco_fields", [])
        for spot in all_field_spots:
            if getattr(spot, "field_rect", None) is not None:
                if not spot.has_produce and getattr(spot, "regrow_timer", 0.0) > 0.0:
                    # Vòi tưới tưới ẩm liên tục giúp cây trồng lớn nhanh thêm 0.7 * dt
                    spot.regrow_timer = max(0.0, spot.regrow_timer - 0.7 * dt)

    def render_sprinklers(self, screen: pygame.Surface, game: Any):
        """
        Nếu không ở trong nhà (not game.in_interior):
        Tìm các HarvestSpot có field_rect hoặc các prop sprinkler trong game.props,
        vẽ các tia nước xanh sáng bắn tỏa tròn 4 hướng quanh tâm ruộng theo chu kỳ math.sin(sim_time * 5.0).
        """
        if getattr(game, "in_interior", False):
            return

        # Thu thập các tọa độ đầu phun sprinkler
        sprinkler_points: list[tuple[float, float]] = []

        # Ruộng nông sản có field_rect (Map 2, Map 4)
        all_field_spots = getattr(game, "harvest_spots", []) + getattr(game, "deco_fields", [])
        for spot in all_field_spots:
            rect = getattr(spot, "field_rect", None)
            if rect is not None:
                sprinkler_points.append((float(rect.centerx), float(rect.centery)))

        # Các prop vòi tưới sprinkler nếu có trong game.props
        for prop in getattr(game, "props", []):
            if prop.kind == "prop" and (
                "sprinkler" in getattr(prop, "title", "").lower()
                or (prop.collider.width <= 20 and prop.collider.height <= 20 and not prop.solid)
            ):
                sprinkler_points.append(
                    (
                        float(prop.x + prop.sprite.get_width() // 2),
                        float(prop.y + prop.sprite.get_height() // 2),
                    )
                )

        # Lọc trùng lặp các điểm quá sát nhau
        unique_points: list[tuple[float, float]] = []
        for px, py in sprinkler_points:
            if not any(math.hypot(px - ux, py - uy) < 24.0 for ux, uy in unique_points):
                unique_points.append((px, py))

        # Hiệu ứng chu kỳ bắn nước
        sim_time = getattr(game, "sim_time", 0.0)
        cycle_pulse = math.sin(sim_time * 5.0)
        rot_angle = sim_time * 3.2
        reach = 16.0 + 14.0 * abs(cycle_pulse)

        for cx, cy in unique_points:
            ix, iy = int(cx), int(cy)

            # 1. Vẽ đế vòi tưới kim loại có chốt đồng thau
            pygame.draw.circle(screen, (95, 110, 125), (ix, iy), 5)
            pygame.draw.circle(screen, (55, 65, 75), (ix, iy), 5, 1)
            pygame.draw.circle(screen, (225, 185, 70), (ix, iy), 2)

            # 2. Vẽ 4 tia nước xanh sáng bắn tỏa tròn 4 hướng
            for k in range(4):
                ang = rot_angle + k * (math.pi / 2.0)
                cos_k = math.cos(ang)
                sin_k = math.sin(ang)

                # Hạt nước li ti trên đường parabol bay ra
                d1 = reach * 0.35
                d2 = reach * 0.70
                d3 = reach * 1.00

                p1 = (int(cx + cos_k * d1), int(cy + sin_k * d1 - 2))
                p2 = (int(cx + cos_k * d2), int(cy + sin_k * d2 - 4))
                p3 = (int(cx + cos_k * d3), int(cy + sin_k * d3 + 1))

                pygame.draw.circle(screen, (130, 225, 255), p1, 1)
                pygame.draw.circle(screen, (170, 238, 255), p2, 2)
                pygame.draw.circle(screen, (215, 248, 255), p3, 1)

                # Vệt nước tiếp đất gợn sóng ẩm ướt
                pygame.draw.ellipse(
                    screen,
                    (100, 205, 255),
                    (p3[0] - 3, p3[1] - 2, 6, 4),
                    1,
                )

    def _render_headlight_glow(
        self,
        screen: pygame.Surface,
        rx: float,
        ry: float,
        theta: float,
    ):
        """Vẽ Quầng sáng Nón đèn pha phía trước Robot (Headlight Cone)."""
        hx = rx + math.cos(theta) * 14.0
        hy = ry + math.sin(theta) * 14.0

        # Lớp 1: Nón rộng xa (ánh sáng mờ vàng kem)
        reach_far = 114.0
        fan_far = 0.44
        pts_far = [(hx, hy)]
        for i in range(9):
            ang = theta - fan_far + (2.0 * fan_far * i / 8.0)
            pts_far.append((hx + math.cos(ang) * reach_far, hy + math.sin(ang) * reach_far))

        # Lớp 2: Nón lõi gần (sáng ấm đậm)
        reach_near = 62.0
        fan_near = 0.32
        pts_near = [(hx, hy)]
        for i in range(9):
            ang = theta - fan_near + (2.0 * fan_near * i / 8.0)
            pts_near.append((hx + math.cos(ang) * reach_near, hy + math.sin(ang) * reach_near))

        # Giới hạn bounding box nhỏ để tối ưu hóa hiệu năng
        all_x = [p[0] for p in pts_far]
        all_y = [p[1] for p in pts_far]
        min_x = max(0, int(min(all_x)) - 6)
        max_x = min(SCREEN_W, int(max(all_x)) + 6)
        min_y = max(0, int(min(all_y)) - 6)
        max_y = min(SCREEN_H, int(max(all_y)) + 6)
        bw = max_x - min_x
        bh = max_y - min_y

        if bw > 0 and bh > 0:
            cone_surf = pygame.Surface((bw, bh), pygame.SRCALPHA)
            offset_far = [(px - min_x, py - min_y) for px, py in pts_far]
            offset_near = [(px - min_x, py - min_y) for px, py in pts_near]
            pygame.draw.polygon(cone_surf, (255, 238, 155, 42), offset_far)
            pygame.draw.polygon(cone_surf, (255, 245, 185, 68), offset_near)
            screen.blit(cone_surf, (min_x, min_y))

        # Bóng đèn pha trước ngực Robot
        pygame.draw.circle(screen, (255, 252, 215), (int(hx), int(hy)), 3)

    def render_festival_decor(self, screen: pygame.Surface, game: Any):
        """
        Vẽ đồ trang trí Lễ Hội Hoa Anh Đào Mùa Xuân tại Quảng Trường Thị Trấn (Map 1):
        - Khi festival_active bật và đang ở ngoài trời Map 1:
          + Vẽ các dây cờ tam giác nhiều màu sắc chăng ngang Quảng Trường (từ (180, 140) sang (960, 140)).
          + Vẽ dây cờ tam giác chăng quanh Giếng nước trung tâm.
          + Vẽ tấm biển lễ hội: "LỄ HỘI HOA ANH ĐÀO THỊ TRẤN (Thiện cảm NPC x2!)" rực rỡ phía trên Quảng Trường.
        """
        # Kiểm tra cờ festival_active từ game.state hoặc game
        fest_active = getattr(getattr(game, "state", None), "festival_active", False) or getattr(
            game, "festival_active", False
        )
        if not fest_active:
            return

        # Chỉ vẽ ở Map 1 ngoài trời
        if getattr(game, "current_map_id", 1) != 1 or getattr(game, "in_interior", False):
            return

        sim_t = getattr(game, "sim_time", 0.0)

        # 1. Dây cờ tam giác chăng ngang Quảng Trường từ (180, 140) sang (960, 140)
        # Chia thành 4 nhịp cung võng tự nhiên nối tiếp nhau
        spans = [
            ((180.0, 138.0), (375.0, 138.0)),
            ((375.0, 138.0), (570.0, 138.0)),
            ((570.0, 138.0), (765.0, 138.0)),
            ((765.0, 138.0), (960.0, 138.0)),
        ]
        for p1, p2 in spans:
            _draw_festival_bunting(screen, p1, p2, sag=18.0, sim_time=sim_t, flag_spacing=22.0)

        # Cột cọc gỗ ở 2 đầu dây cờ
        for cx in (180, 375, 570, 765, 960):
            pygame.draw.line(screen, (88, 58, 32), (cx, 134), (cx, 148), 3)
            pygame.draw.circle(screen, (222, 175, 48), (cx, 134), 3)

        # 2. Dây cờ tam giác chăng quanh Giếng nước trung tâm
        well_pos = (464.0, 390.0)
        for prop in getattr(game, "props", []):
            if prop.kind == "well" or "well" in getattr(prop, "title", "").lower():
                well_pos = (
                    float(prop.x + prop.sprite.get_width() // 2),
                    float(prop.y + prop.sprite.get_height() // 2),
                )
                break

        wx, wy = well_pos
        rw = 52.0
        rh = 36.0
        well_posts = [
            (wx - rw, wy - rh),
            (wx + rw, wy - rh),
            (wx + rw, wy + rh),
            (wx - rw, wy + rh),
        ]
        for idx in range(4):
            wp1 = well_posts[idx]
            wp2 = well_posts[(idx + 1) % 4]
            _draw_festival_bunting(screen, wp1, wp2, sag=10.0, sim_time=sim_t, flag_spacing=18.0)
            pygame.draw.line(screen, (88, 58, 32), (int(wp1[0]), int(wp1[1]) - 4), (int(wp1[0]), int(wp1[1]) + 8), 2)
            pygame.draw.circle(screen, (222, 175, 48), (int(wp1[0]), int(wp1[1]) - 4), 2)

        # 3. Tấm biển Lễ Hội Hoa Anh Đào nổi bật phía trên Quảng Trường
        bx_center = 514
        by = 92
        bw = 432
        bh = 32
        bx = bx_center - bw // 2

        # Khung biển lễ hội gỗ sơn son thếp vàng
        board_rect = pygame.Rect(bx, by, bw, bh)
        pygame.draw.rect(screen, (108, 28, 42), board_rect, border_radius=8)
        pygame.draw.rect(screen, (248, 198, 56), board_rect, width=2, border_radius=8)
        pygame.draw.rect(screen, (255, 142, 180), (bx + 3, by + 3, bw - 6, bh - 6), width=1, border_radius=6)

        # Hoa văn hoa anh đào ở 2 đầu bảng
        for hx in (bx + 16, bx + bw - 16):
            pygame.draw.circle(screen, (255, 182, 193), (hx, by + bh // 2), 7)
            pygame.draw.circle(screen, (255, 235, 145), (hx, by + bh // 2), 3)

        # Dòng chữ Lễ Hội Hoa Anh Đào Thị Trấn
        font_board = getattr(game, "font_sm", None) or pygame.font.SysFont("Segoe UI", 15, bold=True)
        txt = "LỄ HỘI HOA ANH ĐÀO THỊ TRẤN (Thiện cảm NPC x2!)"
        # Hiệu ứng chữ nổi bật có đổ bóng
        sh_surf = font_board.render(txt, True, (48, 14, 18))
        fg_surf = font_board.render(txt, True, (255, 245, 180))
        tx = bx_center - fg_surf.get_width() // 2
        ty = by + (bh - fg_surf.get_height()) // 2
        screen.blit(sh_surf, (tx + 1, ty + 1))
        screen.blit(fg_surf, (tx, ty))

    def render_lighting_and_weather(self, screen: pygame.Surface, game: Any):
        """
        Hiệu ứng Chu kỳ Ngày – Đêm, Ánh Sáng Động, 4 Mùa (Xuân, Hè, Thu, Đông) & Thời Tiết Ngoài Trời.
        Chỉ kết xuất khi không ở trong nhà (not game.in_interior).
        """
        if getattr(game, "in_interior", False):
            return

        # 1. Vẽ trang trí Lễ Hội Hoa Anh Đào (nếu đang kích hoạt)
        self.render_festival_decor(screen, game)

        # 2. Vẽ vòi tưới tự động (Sprinkler)
        self.render_sprinklers(screen, game)

        # 3. Vẽ hạt thời tiết và hạt theo mùa
        mode = self.current_weather
        season = self.current_season

        if mode == "sunny_petals":
            for p in self.petals:
                p.draw(screen)
        elif mode == "clear":
            for sm in self.sun_motes:
                sm.draw(screen)
        elif mode == "rain":
            for sp in self.rain_splashes:
                sp.draw(screen)
            for rd in self.rain_drops:
                rd.draw(screen)

        # Vẽ hạt mùa thu hoặc mùa đông khi thời tiết không mưa
        if mode != "rain":
            if season == "fall":
                for leaf in self.autumn_leaves:
                    leaf.draw(screen)
            elif season == "winter":
                for snow in self.snowflakes:
                    snow.draw(screen)

        # Vẽ đom đóm khi chiều tối (hour >= 17.5)
        hour = self.get_clock_hour(game.sim_time)
        if hour >= 17.5:
            for ff in self.fireflies:
                ff.draw(screen)

        # 4. Tính màu phủ môi trường theo giờ trong game
        ambient_rgba: tuple[int, int, int, int] | None = None
        if hour < 15.5:
            # 07:00 - 15:30: Ban ngày trong trẻo (nếu mưa thì phủ lớp xanh xám nhẹ)
            if mode == "rain":
                ambient_rgba = (28, 42, 68, 38)
            else:
                ambient_rgba = None
        elif hour < 18.0:
            # 15:30 - 18:00: Hoàng hôn Stardew chuyển dần sang cam hồng ấm áp
            ratio = (hour - 15.5) / (18.0 - 15.5)
            alpha = int(max(0.0, min(1.0, ratio)) * 52)
            if mode == "rain":
                ambient_rgba = (195, 120, 85, max(alpha, 38))
            else:
                ambient_rgba = (255, 138, 68, alpha)
        else:
            # 18:00 - 22:00: Ban đêm xanh thẫm
            ratio = (hour - 18.0) / (22.0 - 18.0)
            alpha = int(45 + max(0.0, min(1.0, ratio)) * 65)  # 45 -> 110
            ambient_rgba = (14, 20, 48, alpha)

        # 5. Phủ bóng tối và đục lỗ ánh sáng trên _light_surf
        self._light_surf.fill((0, 0, 0, 0))
        if ambient_rgba is not None and ambient_rgba[3] > 0:
            self._light_surf.fill(ambient_rgba)

        is_dark = (hour >= 17.2) or (mode == "rain")

        # Khi trời tối hoặc mưa: Đục lỗ bóng tối tại các nguồn sáng
        if is_dark:
            glow_sub_flag = getattr(pygame, "BLEND_RGBA_SUB", 0)

            # Cột đèn đường
            for prop in getattr(game, "props", []):
                is_lamp = (
                    prop.kind == "prop"
                    and prop.collider.width <= 28
                    and prop.sprite.get_height() >= 48
                ) or "lamp" in getattr(prop, "title", "").lower()
                if is_lamp:
                    lx = prop.x + prop.sprite.get_width() // 2
                    ly = prop.y + 14
                    top_left = (lx - self._lamp_glow_radius, ly - self._lamp_glow_radius)
                    self._light_surf.blit(self._lamp_glow_sub, top_left, special_flags=glow_sub_flag)

            # Cửa sổ / Cửa ra vào tòa nhà
            for prop in getattr(game, "props", []):
                if prop.kind == "building":
                    if prop.door_rect is not None:
                        bx = prop.door_rect.centerx
                        by = prop.door_rect.top - 8
                    else:
                        bx = prop.x + prop.sprite.get_width() // 2
                        by = prop.y + int(prop.sprite.get_height() * 0.5)
                    top_left = (bx - self._window_glow_radius, by - self._window_glow_radius)
                    self._light_surf.blit(self._window_glow_sub, top_left, special_flags=glow_sub_flag)

            # Nón đèn pha Robot
            rx = game.robot.x
            ry = game.robot.y
            theta = game.robot.theta
            hx = rx + math.cos(theta) * 14.0
            hy = ry + math.sin(theta) * 14.0
            reach = 114.0
            half_fan = 0.44
            cone_pts = [(hx, hy)]
            for idx in range(9):
                ang = theta - half_fan + (2.0 * half_fan * idx / 8.0)
                cone_pts.append((hx + math.cos(ang) * reach, hy + math.sin(ang) * reach))

            pygame.draw.polygon(
                self._light_surf,
                (0, 0, 0, 14),
                [(int(px), int(py)) for px, py in cone_pts],
            )

        # 6. Phủ màn bóng tối lên màn hình nếu có
        if ambient_rgba is not None and ambient_rgba[3] > 0:
            screen.blit(self._light_surf, (0, 0))

        # 7. Phủ lớp tint mùa đặc trưng (Mùa Thu hoặc Mùa Đông) khi thời tiết không mưa
        if mode != "rain":
            if season == "fall":
                screen.blit(self._fall_tint, (0, 0))
            elif season == "winter":
                screen.blit(self._winter_tint, (0, 0))

        # 8. Khi trời tối hoặc mưa: Vẽ Quầng sáng vàng ấm (Radial Glow & Headlight Bloom) lên screen
        if is_dark:
            # Quầng sáng đèn đường
            for prop in getattr(game, "props", []):
                is_lamp = (
                    prop.kind == "prop"
                    and prop.collider.width <= 28
                    and prop.sprite.get_height() >= 48
                ) or "lamp" in getattr(prop, "title", "").lower()
                if is_lamp:
                    lx = prop.x + prop.sprite.get_width() // 2
                    ly = prop.y + 14
                    screen.blit(
                        self._lamp_glow_add,
                        (lx - self._lamp_glow_radius, ly - self._lamp_glow_radius),
                    )
                    pygame.draw.circle(screen, (255, 248, 200), (lx, ly), 4)

            # Quầng sáng cửa sổ / cửa nhà
            for prop in getattr(game, "props", []):
                if prop.kind == "building":
                    if prop.door_rect is not None:
                        bx = prop.door_rect.centerx
                        by = prop.door_rect.top - 8
                    else:
                        bx = prop.x + prop.sprite.get_width() // 2
                        by = prop.y + int(prop.sprite.get_height() * 0.5)
                    screen.blit(
                        self._window_glow_add,
                        (bx - self._window_glow_radius, by - self._window_glow_radius),
                    )

            # Quầng sáng nón đèn pha Robot
            self._render_headlight_glow(screen, game.robot.x, game.robot.y, game.robot.theta)
