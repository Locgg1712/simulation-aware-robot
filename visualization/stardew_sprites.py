# visualization/stardew_sprites.py
"""
Bộ tạo tài nguyên đồ họa Pixel-Art phong cách Stardew Valley (Procedural 16-bit Pixel Art).
Tự động vẽ và cache các Sprite sắc nét (Nearest-Neighbor) cho:
- Thảm cỏ, hoa dại, đường lát đá/đất
- Ngôi nhà mái ngói ấm áp có cửa ra vào (House Portal), hàng rào gỗ, tường đá
- Cây cối tán lá đa tầng (Lush Trees) & Bụi cây
- Robot nhân vật giao hàng dễ thương (xoay 4 hướng, hiệu ứng bước đi, bê kiện hàng)
- Nhân vật dân làng (Villager NPCs) kèm bong bóng hội thoại kiểu Stardew Valley
- Xe chở hàng (Minecart/AGV) và Trạm giao nhận hàng (Delivery Goal)
"""

import math
import random
import pygame


class StardewSpriteBank:
    """Quản lý và sinh toàn bộ Pixel-Art Sprites phong cách Stardew Valley."""

    # Bảng màu ấm áp đặc trưng của Stardew Valley
    PALETTE = {
        "grass_base": (110, 178, 75),
        "grass_light": (132, 198, 90),
        "grass_dark": (88, 152, 60),
        "dirt_base": (210, 166, 108),
        "dirt_edge": (176, 130, 78),
        "dirt_highlight": (228, 188, 132),
        "shadow": (20, 35, 18, 95),
        "wood_light": (186, 122, 68),
        "wood_dark": (128, 76, 36),
        "roof_red": (196, 70, 62),
        "roof_red_dark": (148, 45, 42),
        "roof_blue": (72, 118, 172),
        "roof_blue_dark": (48, 82, 128),
        "wall_cream": (242, 224, 188),
        "wall_brick": (212, 188, 148),
        "window_glow": (255, 232, 138),
    }

    def __init__(self, scale: float):
        self.scale = scale
        self._cache: dict = {}

    @staticmethod
    def _make_pixel_surface(grid: list[str], color_map: dict[str, tuple], pixel_size: int = 3) -> pygame.Surface:
        """Biến ma trận ký tự ASCII thành Surface Pixel-Art sắc nét."""
        h = len(grid)
        w = len(grid[0]) if h > 0 else 1
        raw = pygame.Surface((w, h), pygame.SRCALPHA)
        for r, row in enumerate(grid):
            for c, ch in enumerate(row):
                if ch in color_map and color_map[ch] is not None:
                    raw.set_at((c, r), color_map[ch])
        return pygame.transform.scale(raw, (w * pixel_size, h * pixel_size))

    # ------------------------------------------------------------------
    # 1. NỀN BẢN ĐỒ: CỎ, HOA DẠI, ĐÁ CUỘI & CÂY TRANG TRÍ BÊN NGOÀI
    # ------------------------------------------------------------------
    def build_background_surface(
        self,
        window_size: int,
        world_width: float,
        world_height: float,
        static_objects: list,
        start_pos: tuple[float, float],
        goal_pos: tuple[float, float],
        seed: int = 42,
    ) -> pygame.Surface:
        """Tạo lớp nền đồng cỏ Stardew Valley có hoa, sỏi và đường mòn dẫn lối."""
        bg = pygame.Surface((window_size, window_size))
        bg.fill(self.PALETTE["grass_base"])

        rng = random.Random(seed)
        tile_px = max(16, int(round(0.5 * self.scale)))

        # Vẽ ô cỏ xen kẽ sắc độ nhẹ
        for y in range(0, window_size, tile_px):
            for x in range(0, window_size, tile_px):
                val = rng.random()
                if val < 0.28:
                    pygame.draw.rect(bg, self.PALETTE["grass_light"], (x, y, tile_px, tile_px))
                elif val < 0.45:
                    pygame.draw.rect(bg, self.PALETTE["grass_dark"], (x, y, tile_px, tile_px))

        # Vẽ sân lát đất ấm áp quanh khu vực Xuất phát (Start) và Đích (Goal)
        for px, py, pad_m in [(start_pos[0], start_pos[1], 1.3), (goal_pos[0], goal_pos[1], 1.5)]:
            sx = int(round((px - pad_m) * self.scale))
            sy = int(round((py - pad_m) * self.scale))
            sw = int(round(pad_m * 2 * self.scale))
            pygame.draw.rect(bg, self.PALETTE["dirt_edge"], (sx - 3, sy - 3, sw + 6, sw + 6), border_radius=10)
            pygame.draw.rect(bg, self.PALETTE["dirt_base"], (sx, sy, sw, sw), border_radius=8)

        # Rải các khóm cỏ non, hoa dại (vàng, trắng, hồng, xanh) trên mặt đất
        flower_colors = [
            (255, 225, 85),   # Hoa cúc vàng
            (255, 245, 250),  # Hoa trắng
            (255, 145, 178),  # Hoa hồng phấn
            (130, 205, 255),  # Hoa lưu ly xanh
        ]
        for _ in range(180):
            fx = rng.randint(18, window_size - 18)
            fy = rng.randint(18, window_size - 18)
            if rng.random() < 0.65:
                # Khóm cỏ V nhỏ
                c = self.PALETTE["grass_dark"]
                pygame.draw.line(bg, c, (fx, fy), (fx - 2, fy - 4), 2)
                pygame.draw.line(bg, c, (fx, fy), (fx + 2, fy - 4), 2)
            else:
                # Bông hoa pixel nhỏ
                fc = rng.choice(flower_colors)
                pygame.draw.rect(bg, self.PALETTE["grass_dark"], (fx, fy + 2, 2, 3))
                pygame.draw.rect(bg, fc, (fx - 2, fy - 2, 5, 5))
                pygame.draw.rect(bg, (255, 200, 50), (fx, fy, 2, 2))

        return bg

    # ------------------------------------------------------------------
    # 2. CÂY CỐI, NGÔI NHÀ CÓ CỬA VÀO (PORTAL) & HÀNG RÀO GỖ
    # ------------------------------------------------------------------
    def draw_tree_sprite(self, screen: pygame.Surface, cx: int, cy: int, radius_px: int, obj_id: int = 1):
        """Vẽ cây sồi / cây thông tán lá nhiều tầng kiểu Stardew Valley tại vị trí cột tròn."""
        # Bóng râm dưới gốc cây
        shadow_w = int(radius_px * 2.2)
        shadow_h = int(radius_px * 1.2)
        sh_surf = pygame.Surface((shadow_w, shadow_h), pygame.SRCALPHA)
        pygame.draw.ellipse(sh_surf, self.PALETTE["shadow"], (0, 0, shadow_w, shadow_h))
        screen.blit(sh_surf, (cx - shadow_w // 2, cy + radius_px // 4))

        # Thân cây gỗ
        trunk_w = max(8, int(radius_px * 0.55))
        trunk_h = max(12, int(radius_px * 0.95))
        pygame.draw.rect(
            screen,
            self.PALETTE["wood_dark"],
            (cx - trunk_w // 2, cy - trunk_h // 4, trunk_w, trunk_h),
            border_radius=2,
        )
        pygame.draw.rect(
            screen,
            self.PALETTE["wood_light"],
            (cx - trunk_w // 2 + 2, cy - trunk_h // 4, max(2, trunk_w // 2), trunk_h - 2),
        )

        # Tán lá 3 tầng đậm -> nhạt + quả táo đỏ nhỏ
        is_pine = (obj_id % 3 == 0)
        leaf_dark = (38, 108, 54) if not is_pine else (32, 92, 68)
        leaf_mid = (58, 148, 68) if not is_pine else (46, 128, 88)
        leaf_bright = (92, 184, 82) if not is_pine else (72, 162, 108)

        canopy_y = cy - int(radius_px * 0.55)
        r_main = int(radius_px * 1.15)

        pygame.draw.circle(screen, leaf_dark, (cx, canopy_y + 4), r_main)
        pygame.draw.circle(screen, leaf_mid, (cx - r_main // 3, canopy_y), int(r_main * 0.78))
        pygame.draw.circle(screen, leaf_mid, (cx + r_main // 3, canopy_y), int(r_main * 0.78))
        pygame.draw.circle(screen, leaf_bright, (cx, canopy_y - r_main // 4), int(r_main * 0.72))
        pygame.draw.circle(screen, (28, 75, 38), (cx, canopy_y + 4), r_main, 2)

        # Điểm xuyết vài quả chín hoặc hoa trên tán cây
        if obj_id % 2 == 0:
            for ox, oy in [(-r_main // 3, -2), (r_main // 3, 3), (0, -r_main // 3)]:
                pygame.draw.circle(screen, (230, 65, 55), (cx + ox, canopy_y + oy), max(2, r_main // 6))

    def draw_house_or_wall(
        self,
        screen: pygame.Surface,
        sx: int,
        sy: int,
        sw: int,
        sh: int,
        obj_id: int,
        name: str,
        font: pygame.font.Font,
    ):
        """
        Phân loại thông minh:
        - Tường bao quanh map -> Hàng rào gỗ nông trại / Tường đá cổ điển.
        - Khối chữ nhật lớn (rộng và cao >= 48px) -> Ngôi nhà Stardew Valley có mái ngói, cửa sổ, ống khói và cửa bước vào!
        - Tường ngăn hẹp -> Tường gỗ / Hàng rào khu vườn kèm bụi cây.
        """
        is_border = name.startswith("wall_top") or name.startswith("wall_bottom") or name.startswith("wall_left") or name.startswith("wall_right")

        if is_border:
            # Vẽ tường rào gỗ nông trại bao quanh thị trấn
            pygame.draw.rect(screen, self.PALETTE["wood_dark"], (sx, sy, sw, sh))
            pygame.draw.rect(screen, self.PALETTE["wood_light"], (sx + 1, sy + 1, max(1, sw - 2), max(1, sh - 2)))
            step = max(12, int(0.8 * self.scale))
            if sw > sh:
                for px in range(sx, sx + sw, step):
                    pygame.draw.rect(screen, self.PALETTE["wood_dark"], (px, sy, 4, sh))
            else:
                for py in range(sy, sy + sh, step):
                    pygame.draw.rect(screen, self.PALETTE["wood_dark"], (sx, py, sw, 4))
            return

        # Nếu là khối lớn -> Vẽ thành NGÔI NHÀ STARDEW VALLEY (Cozy Cottage) có cửa ra vào!
        min_house_px = max(44, int(1.6 * self.scale))
        if sw >= min_house_px and sh >= min_house_px:
            self._draw_stardew_cottage(screen, sx, sy, sw, sh, obj_id, font)
        else:
            # Tường ngăn / Hàng rào đá & gỗ kết hợp bụi hoa
            shadow = pygame.Surface((sw + 4, sh + 6), pygame.SRCALPHA)
            shadow.fill(self.PALETTE["shadow"])
            screen.blit(shadow, (sx + 2, sy + 3))

            pygame.draw.rect(screen, self.PALETTE["wood_dark"], (sx, sy, sw, sh), border_radius=4)
            pygame.draw.rect(screen, self.PALETTE["wood_light"], (sx + 2, sy + 2, max(1, sw - 4), max(1, sh - 4)), border_radius=3)

            # Vân gạch/vân gỗ
            plank_step = max(10, int(0.5 * self.scale))
            if sw >= sh:
                for x_line in range(sx + plank_step, sx + sw - 4, plank_step):
                    pygame.draw.line(screen, self.PALETTE["wood_dark"], (x_line, sy + 2), (x_line, sy + sh - 2), 2)
            else:
                for y_line in range(sy + plank_step, sy + sh - 4, plank_step):
                    pygame.draw.line(screen, self.PALETTE["wood_dark"], (sx + 2, y_line), (sx + sw - 2, y_line), 2)

    def _draw_stardew_cottage(
        self,
        screen: pygame.Surface,
        sx: int,
        sy: int,
        sw: int,
        sh: int,
        obj_id: int,
        font: pygame.font.Font,
    ):
        """Vẽ ngôi nhà gỗ/gạch mái ngói phong cách Stardew Valley kèm Cửa Ra Vào (Portal)."""
        # 1. Bóng đổ ngôi nhà
        sh_surf = pygame.Surface((sw + 8, sh + 8), pygame.SRCALPHA)
        pygame.draw.rect(sh_surf, self.PALETTE["shadow"], (0, 0, sw + 8, sh + 8), border_radius=6)
        screen.blit(sh_surf, (sx + 3, sy + 4))

        # 2. Phần thân tường nhà (nửa dưới) & Mái ngói (nửa trên)
        roof_h = max(20, int(sh * 0.52))
        wall_y = sy + roof_h - 4
        wall_h = max(16, sh - roof_h + 4)

        # Tường gỗ/kem ấm áp
        pygame.draw.rect(screen, self.PALETTE["wall_cream"], (sx + 2, wall_y, sw - 4, wall_h), border_radius=3)
        pygame.draw.rect(screen, self.PALETTE["wood_dark"], (sx + 2, wall_y, sw - 4, wall_h), 2, border_radius=3)

        # Kẻ vân gỗ ngang trên tường nhà
        for wy in range(wall_y + 6, wall_y + wall_h - 4, 7):
            pygame.draw.line(screen, self.PALETTE["wall_brick"], (sx + 4, wy), (sx + sw - 5, wy), 1)

        # 3. Mái ngói đỏ hoặc xanh kiểu Pelican Town
        use_red = (obj_id % 2 == 1)
        roof_main = self.PALETTE["roof_red"] if use_red else self.PALETTE["roof_blue"]
        roof_dark = self.PALETTE["roof_red_dark"] if use_red else self.PALETTE["roof_blue_dark"]

        pygame.draw.rect(screen, roof_main, (sx, sy, sw, roof_h), border_radius=5)
        # Vân ngói lợp
        for ry in range(sy + 5, sy + roof_h - 3, 6):
            pygame.draw.line(screen, roof_dark, (sx + 3, ry), (sx + sw - 4, ry), 2)
        # Chóp mái & viền mái gỗ
        pygame.draw.rect(screen, self.PALETTE["wood_dark"], (sx, sy, sw, roof_h), 2, border_radius=5)
        pygame.draw.line(screen, (255, 215, 175), (sx + 4, sy + 3), (sx + sw - 5, sy + 3), 2)

        # 4. Ống khói nhỏ trên mái
        if sw >= 60:
            chim_x = sx + sw - 20
            chim_y = sy - 6
            pygame.draw.rect(screen, (140, 75, 65), (chim_x, chim_y, 10, 14))
            pygame.draw.rect(screen, (90, 45, 40), (chim_x - 1, chim_y, 12, 4))

        # 5. Cửa chính bước vào nhà (Portal Door) + Thảm chào mừng
        door_w = min(22, max(12, sw // 4))
        door_h = min(24, max(12, wall_h - 4))
        door_x = sx + sw // 2 - door_w // 2
        door_y = sy + sh - door_h

        pygame.draw.rect(screen, self.PALETTE["wood_dark"], (door_x, door_y, door_w, door_h), border_top_left_radius=4, border_top_right_radius=4)
        pygame.draw.rect(screen, self.PALETTE["wood_light"], (door_x + 2, door_y + 2, door_w - 4, door_h - 2), border_top_left_radius=3, border_top_right_radius=3)
        # Tay nắm cửa vàng
        pygame.draw.circle(screen, (255, 215, 70), (door_x + door_w - 5, door_y + door_h // 2), 2)
        # Thảm đỏ trước cửa nhà
        pygame.draw.rect(screen, (200, 70, 65), (door_x - 2, sy + sh, door_w + 4, 5), border_radius=2)

        # 6. Cửa sổ sáng đèn vàng ấm áp hai bên cửa chính
        if sw >= 68 and wall_h >= 18:
            win_size = min(14, max(8, wall_h // 2))
            win_y = wall_y + 5
            for wx in [sx + 10, sx + sw - 10 - win_size]:
                if abs(wx - door_x) > win_size:
                    pygame.draw.rect(screen, self.PALETTE["window_glow"], (wx, win_y, win_size, win_size))
                    pygame.draw.rect(screen, self.PALETTE["wood_dark"], (wx, win_y, win_size, win_size), 2)
                    pygame.draw.line(screen, self.PALETTE["wood_dark"], (wx + win_size // 2, win_y), (wx + win_size // 2, win_y + win_size), 1)
                    pygame.draw.line(screen, self.PALETTE["wood_dark"], (wx, win_y + win_size // 2), (wx + win_size, win_y + win_size // 2), 1)

    # ------------------------------------------------------------------
    # 3. ROBOT NHÂN VẬT PIXEL-ART (CÓ HIỆU ỨNG BƯỚC ĐI & BÊ HỘP HÀNG)
    # ------------------------------------------------------------------
    def draw_robot_character(
        self,
        screen: pygame.Surface,
        rx: int,
        ry: int,
        rad_px: int,
        theta: float,
        speed: float,
        sim_time: float,
        is_collision: bool = False,
        carrying_item: bool = True,
    ):
        """
        Vẽ Robot hình nhân vật Pixel-Art dễ thương kiểu Stardew Valley (Helper Bot):
        - Có ăng-ten phát sáng, tai nghe hai bên, màn hình mặt LED xanh ngọc với 2 mắt chớp.
        - Có hiệu ứng nhấp nhô bước chân khi di chuyển.
        - Có tùy chọn hiển thị Kiện Hàng Giao Nhận (Parcel Box) để phục vụ chuỗi nhiệm vụ!
        """
        # Hiệu ứng nhấp nhô khi Robot đang di chuyển
        bob_y = int(round(math.sin(sim_time * 12.0) * 2.0)) if speed > 0.05 else 0

        # 1. Bóng đổ dưới chân Robot
        sh_w = int(rad_px * 2.1)
        sh_h = int(rad_px * 1.0)
        sh_surf = pygame.Surface((sh_w, sh_h), pygame.SRCALPHA)
        pygame.draw.ellipse(sh_surf, self.PALETTE["shadow"], (0, 0, sh_w, sh_h))
        screen.blit(sh_surf, (rx - sh_w // 2, ry + rad_px // 2))

        body_color = (225, 65, 65) if is_collision else (72, 148, 235)
        body_highlight = (248, 113, 113) if is_collision else (135, 198, 255)
        outline_color = (28, 45, 78)

        # 2. Chân bước đi (2 bàn chân robot)
        leg_swing = int(round(math.sin(sim_time * 12.0) * 3.0)) if speed > 0.05 else 0
        foot_w = max(5, rad_px // 2)
        foot_h = max(4, rad_px // 3)
        pygame.draw.rect(screen, (65, 75, 95), (rx - foot_w - 1, ry + rad_px // 3 + leg_swing, foot_w, foot_h), border_radius=2)
        pygame.draw.rect(screen, (65, 75, 95), (rx + 1, ry + rad_px // 3 - leg_swing, foot_w, foot_h), border_radius=2)

        # 3. Thân & Đầu Robot Pixel-Art
        w_body = int(rad_px * 1.55)
        h_body = int(rad_px * 1.45)
        bx = rx - w_body // 2
        by = ry - h_body // 2 + bob_y

        pygame.draw.rect(screen, body_color, (bx, by, w_body, h_body), border_radius=6)
        pygame.draw.rect(screen, body_highlight, (bx + 2, by + 2, w_body - 4, max(4, h_body // 3)), border_radius=4)
        pygame.draw.rect(screen, outline_color, (bx, by, w_body, h_body), 2, border_radius=6)

        # Tai Robot 2 bên
        pygame.draw.rect(screen, (245, 175, 55), (bx - 3, by + h_body // 3, 4, max(6, h_body // 3)), border_radius=2)
        pygame.draw.rect(screen, (245, 175, 55), (bx + w_body - 1, by + h_body // 3, 4, max(6, h_body // 3)), border_radius=2)

        # Ăng-ten phát sáng trên đỉnh đầu
        ant_top_y = by - 7
        pygame.draw.line(screen, outline_color, (rx, by), (rx, ant_top_y), 2)
        bulb_col = (255, 80, 80) if is_collision else (80, 245, 165)
        pygame.draw.circle(screen, bulb_col, (rx, ant_top_y), 4)
        pygame.draw.circle(screen, outline_color, (rx, ant_top_y), 4, 1)

        # 4. Màn hình khuôn mặt xoay theo hướng góc theta
        look_dx = int(round(math.cos(theta) * 3.0))
        look_dy = int(round(math.sin(theta) * 2.5))
        visor_w = max(10, int(w_body * 0.72))
        visor_h = max(7, int(h_body * 0.48))
        vx = rx - visor_w // 2 + look_dx
        vy = by + int(h_body * 0.25) + look_dy

        pygame.draw.rect(screen, (22, 32, 48), (vx, vy, visor_w, visor_h), border_radius=3)
        # Hai mắt LED xanh ngọc biết chớp
        blink = (int(sim_time * 3.0) % 11 == 0)
        eye_col = (255, 110, 110) if is_collision else (95, 250, 225)
        if blink:
            pygame.draw.line(screen, eye_col, (vx + 3, vy + visor_h // 2), (vx + visor_w - 4, vy + visor_h // 2), 2)
        else:
            eye_r = max(2, visor_h // 4)
            pygame.draw.circle(screen, eye_col, (vx + visor_w // 3, vy + visor_h // 2), eye_r)
            pygame.draw.circle(screen, eye_col, (vx + (2 * visor_w) // 3, vy + visor_h // 2), eye_r)

        # 5. Kiện hàng nhỏ (Delivery Parcel) gắn phía trước/trên vai Robot
        if carrying_item:
            px_box = rx + int(math.cos(theta) * (rad_px * 0.65)) - 5
            py_box = ry + int(math.sin(theta) * (rad_px * 0.65)) - 5 + bob_y
            pygame.draw.rect(screen, (218, 152, 84), (px_box, py_box, 10, 9), border_radius=2)
            pygame.draw.rect(screen, (125, 72, 28), (px_box, py_box, 10, 9), 1, border_radius=2)
            pygame.draw.line(screen, (235, 75, 65), (px_box + 5, py_box), (px_box + 5, py_box + 8), 2)

    # ------------------------------------------------------------------
    # 4. NHÂN VẬT CON NGƯỜI (VILLAGER NPC) & BONG BÓNG HỘI THOẠI
    # ------------------------------------------------------------------
    def draw_villager_npc(
        self,
        screen: pygame.Surface,
        cx: int,
        cy: int,
        rad_px: int,
        human,
        sim_time: float,
        small_font: pygame.font.Font,
        debug_mode: bool = False,
    ):
        """Vẽ nhân vật dân làng Pixel-Art có đầu, tóc, trang phục và bong bóng cảm xúc."""
        # Chọn màu tóc & màu áo theo ID nhân vật và Activity
        hair_colors = [(115, 62, 36), (235, 182, 65), (185, 68, 52), (55, 58, 72)]
        hair_col = hair_colors[human.obj_id % len(hair_colors)]

        act_name = human.activity.value
        if act_name == "STANDING":
            shirt_col = (56, 178, 212)   # Xanh ngọc lịch sự
        elif act_name == "WALKING":
            shirt_col = (234, 118, 45)   # Áo cam nông trại
        else:
            shirt_col = (225, 55, 85)    # Áo đỏ thể thao (Running)

        bob_y = int(round(math.sin(sim_time * 10.0 + human.obj_id) * 2.0)) if human.speed > 0.1 else 0

        # 1. Bóng đổ dưới chân
        sh_w = int(rad_px * 1.9)
        sh_h = int(rad_px * 0.9)
        sh_surf = pygame.Surface((sh_w, sh_h), pygame.SRCALPHA)
        pygame.draw.ellipse(sh_surf, self.PALETTE["shadow"], (0, 0, sh_w, sh_h))
        screen.blit(sh_surf, (cx - sh_w // 2, cy + rad_px // 2))

        # 2. Quần & Chân bước đi
        swing = int(round(math.sin(sim_time * 10.0 + human.obj_id) * 3.0)) if human.speed > 0.1 else 0
        pygame.draw.rect(screen, (52, 78, 128), (cx - 5, cy + 2 + swing, 4, 6), border_radius=1)
        pygame.draw.rect(screen, (52, 78, 128), (cx + 1, cy + 2 - swing, 4, 6), border_radius=1)

        # 3. Thân áo (Torso)
        torso_w = max(12, int(rad_px * 1.25))
        torso_h = max(10, int(rad_px * 0.95))
        pygame.draw.rect(
            screen,
            shirt_col,
            (cx - torso_w // 2, cy - torso_h // 2 + 2 + bob_y, torso_w, torso_h),
            border_radius=4,
        )
        pygame.draw.rect(
            screen,
            (35, 30, 30),
            (cx - torso_w // 2, cy - torso_h // 2 + 2 + bob_y, torso_w, torso_h),
            1,
            border_radius=4,
        )

        # 4. Đầu & Khuôn mặt (Head)
        head_r = max(6, int(rad_px * 0.68))
        head_y = cy - torso_h // 2 - head_r // 2 + 1 + bob_y
        pygame.draw.circle(screen, (255, 218, 185), (cx, head_y), head_r)
        pygame.draw.circle(screen, (65, 42, 32), (cx, head_y), head_r, 1)

        # Mái tóc Pixel-Art
        pygame.draw.arc(
            screen,
            hair_col,
            (cx - head_r, head_y - head_r - 1, head_r * 2, head_r * 2),
            0.0,
            math.pi,
            max(4, head_r // 2 + 2),
        )

        # Mắt nhìn theo hướng di chuyển theta
        ex = cx + int(math.cos(human.theta) * 2.5)
        ey = head_y + int(math.sin(human.theta) * 1.5)
        pygame.draw.circle(screen, (40, 30, 30), (ex - 2, ey), 1)
        pygame.draw.circle(screen, (40, 30, 30), (ex + 2, ey), 1)

        # 5. Bong bóng cảm xúc kiểu Stardew Valley (khi đang nói chuyện nhóm hoặc cắt ngang)
        ctx_name = human.social_context.value
        if ctx_name == "INTERACTING" and not debug_mode:
            bx, by = cx + 6, head_y - head_r - 14
            pygame.draw.rect(screen, (255, 255, 255), (bx, by, 20, 12), border_radius=4)
            pygame.draw.rect(screen, (85, 65, 45), (bx, by, 20, 12), 1, border_radius=4)
            for dot_i in range(3):
                pygame.draw.circle(screen, (95, 75, 55), (bx + 5 + dot_i * 5, by + 6), 1)
        elif ctx_name in ("APPROACHING", "CROSSING") and not debug_mode:
            bx, by = cx - 6, head_y - head_r - 15
            pygame.draw.rect(screen, (255, 245, 215), (bx, by, 13, 13), border_radius=3)
            pygame.draw.rect(screen, (220, 60, 50), (bx, by, 13, 13), 1, border_radius=3)
            excl = small_font.render("!", True, (220, 38, 38))
            screen.blit(excl, (bx + 3, by))

    # ------------------------------------------------------------------
    # 5. TRẠM ĐÍCH GIAO HÀNG (DELIVERY GOAL) & XE CHỞ HÀNG (AGV CART)
    # ------------------------------------------------------------------
    def draw_delivery_goal(self, screen: pygame.Surface, gx: int, gy: int, grad_px: int, sim_time: float):
        """Vẽ Trạm Giao Hàng (Shipping Bin / Quest Shrine) kèm mũi tên vàng nhấp nhô."""
        # Vòng sáng cỏ ma thuật dưới mặt đất
        pulse = int(math.sin(sim_time * 4.0) * 3)
        pygame.draw.circle(screen, (245, 215, 110), (gx, gy), grad_px + pulse, 2)
        pygame.draw.circle(screen, (118, 215, 125), (gx, gy), max(4, grad_px - 3))

        # Thùng gỗ giao hàng (Stardew Shipping Bin)
        bin_w = max(20, int(grad_px * 1.4))
        bin_h = max(16, int(grad_px * 1.1))
        bx = gx - bin_w // 2
        by = gy - bin_h // 2
        pygame.draw.rect(screen, self.PALETTE["wood_dark"], (bx, by, bin_w, bin_h), border_radius=3)
        pygame.draw.rect(screen, self.PALETTE["wood_light"], (bx + 2, by + 2, bin_w - 4, bin_h - 4), border_radius=2)
        pygame.draw.line(screen, self.PALETTE["wood_dark"], (bx + 2, by + bin_h // 2), (bx + bin_w - 2, by + bin_h // 2), 2)
        # Khóa sắt vàng ở giữa thùng
        pygame.draw.rect(screen, (250, 204, 21), (gx - 3, by + bin_h // 2 - 3, 6, 6), border_radius=1)

        # Mũi tên nhiệm vụ màu vàng nhấp nhô phía trên
        arrow_y = by - 10 + int(math.sin(sim_time * 6.0) * 4.0)
        pts = [(gx, arrow_y + 7), (gx - 6, arrow_y), (gx + 6, arrow_y)]
        pygame.draw.polygon(screen, (255, 215, 40), pts)
        pygame.draw.polygon(screen, (145, 85, 20), pts, 1)

    def draw_agv_cart(self, screen: pygame.Surface, cx: int, cy: int, rad_px: int, theta: float):
        """Vẽ vật thể động (AGV) thành Xe Goòng Chở Hàng (Wooden Minecart)."""
        w = max(16, int(rad_px * 1.7))
        h = max(14, int(rad_px * 1.4))
        pygame.draw.rect(screen, (75, 65, 60), (cx - w // 2, cy - h // 2, w, h), border_radius=4)
        pygame.draw.rect(screen, (168, 112, 62), (cx - w // 2 + 2, cy - h // 2 + 2, w - 4, h - 4), border_radius=3)
        # Kiện hàng tím/vàng bên trong xe
        pygame.draw.rect(screen, (168, 85, 247), (cx - w // 4, cy - h // 4, w // 2, h // 2), border_radius=2)