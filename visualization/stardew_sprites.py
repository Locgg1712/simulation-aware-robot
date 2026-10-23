# visualization/stardew_sprites.py
import math
import random
import pygame


class StardewSpriteBank:
    """
    Bộ tạo đồ họa Pixel-Art Stardew Valley cho:
    - 4 Bản đồ ngoài trời (Beach Farm, Hill-top Farm, Pelican Town, Four Corners Forest)
    - Không gian Nội thất Trong Nhà (Indoor Room) với hiệu ứng làm tối vùng bên ngoài
    """

    PALETTE = {
        "grass_base": (106, 176, 72),
        "grass_light": (128, 196, 88),
        "grass_dark": (84, 148, 56),
        "sand_base": (238, 206, 142),
        "sand_dark": (214, 176, 112),
        "water_deep": (56, 132, 198),
        "water_light": (92, 168, 226),
        "stone_road": (132, 136, 146),
        "stone_dark": (96, 100, 110),
        "dirt_base": (210, 164, 102),
        "dirt_edge": (172, 126, 74),
        "crop_soil": (138, 86, 46),
        "shadow": (18, 32, 16, 95),
        "wood_light": (188, 124, 68),
        "wood_dark": (124, 72, 34),
        "roof_red": (198, 68, 58),
        "roof_red_dark": (146, 42, 38),
        "roof_blue": (68, 116, 174),
        "roof_blue_dark": (44, 78, 126),
        "wall_cream": (244, 226, 188),
        "wall_brick": (212, 188, 148),
        "window_glow": (255, 234, 142),
    }

    def __init__(self, scale: float):
        self.scale = scale

    def _m2px(self, m: float) -> int:
        return int(round(m * self.scale))

    def _rect_m2px(self, x: float, y: float, w: float, h: float) -> tuple[int, int, int, int]:
        return (self._m2px(x), self._m2px(y), self._m2px(w), self._m2px(h))

    # ------------------------------------------------------------------
    # 1. NỀN BẢN ĐỒ THEO TỪNG MAP (1: BEACH, 2: HILL-TOP, 3: TOWN, 4: FOREST)
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
        topology_id: int = 1,
    ) -> pygame.Surface:
        bg = pygame.Surface((window_size, window_size))
        bg.fill(self.PALETTE["grass_base"])

        rng = random.Random(seed)
        tile_px = max(16, int(round(0.5 * self.scale)))

        # Vẽ ô cỏ đa sắc độ
        for y in range(0, window_size, tile_px):
            for x in range(0, window_size, tile_px):
                val = rng.random()
                if val < 0.28:
                    pygame.draw.rect(bg, self.PALETTE["grass_light"], (x, y, tile_px, tile_px))
                elif val < 0.45:
                    pygame.draw.rect(bg, self.PALETTE["grass_dark"], (x, y, tile_px, tile_px))

        # --- BỐ CỤC ĐỊA HÌNH ĐẶC TRƯNG CỦA 4 BẢN ĐỒ STARDEW VALLEY ---
        if topology_id == 1:
            # MAP 1 (Ảnh 1): Bãi cát vàng góc đông bắc & dọc bờ biển, ruộng cây, cầu gỗ
            pygame.draw.rect(bg, self.PALETTE["sand_base"], self._rect_m2px(9.2, 0.25, 10.5, 5.4), border_radius=14)
            pygame.draw.rect(bg, self.PALETTE["sand_base"], self._rect_m2px(2.4, 5.5, 3.0, 11.5), border_radius=12)
            pygame.draw.rect(bg, self.PALETTE["sand_base"], self._rect_m2px(9.5, 13.8, 9.8, 5.8), border_radius=14)
            # Khu đất canh tác màu vàng cam ở giữa & tây bắc
            self._draw_crop_field(bg, 4.8, 2.2, 2.0, 3.4)
            self._draw_crop_field(bg, 6.0, 7.6, 3.6, 3.4)
            # Cầu gỗ bắc qua eo biển phía tây bắc
            self._draw_wooden_bridge(bg, 4.4, 0.4, 0.9, 1.4)

        elif topology_id == 2:
            # MAP 2 (Ảnh 2): Đường lát gạch đá xám (Cobblestone) ngang dọc + Ruộng tưới tiêu + Vách đồi
            self._draw_crop_field(bg, 5.6, 4.6, 4.8, 4.8, with_sprinklers=True)
            self._draw_crop_field(bg, 15.8, 14.8, 3.4, 4.2, with_sprinklers=True)
            # Hệ thống đường đá xám chính giữa bản đồ
            self._draw_cobblestone_road(bg, 3.0, 9.4, 16.5, 1.7)
            self._draw_cobblestone_road(bg, 9.8, 5.2, 1.5, 4.5)
            self._draw_cobblestone_road(bg, 4.2, 10.8, 1.4, 8.5)
            self._draw_cobblestone_road(bg, 14.2, 10.8, 1.4, 8.5)
            # Suối nước bên rìa trái
            pygame.draw.rect(bg, self.PALETTE["water_deep"], self._rect_m2px(0.25, 0.25, 0.9, 19.5))

        elif topology_id == 3:
            # MAP 3 (Ảnh 3): Quảng trường lát đá Pelican Town + Đường mòn đất vàng + 2 Cầu qua sông
            self._draw_cobblestone_road(bg, 3.2, 4.4, 4.8, 6.4)
            self._draw_cobblestone_road(bg, 0.5, 4.2, 3.0, 1.2)
            self._draw_cobblestone_road(bg, 4.4, 10.6, 1.3, 6.2)
            self._draw_cobblestone_road(bg, 5.4, 12.8, 3.6, 1.2)
            # Vòng tròn gạch đỏ ở tâm Quảng trường
            pcx, pcy = self._m2px(5.2), self._m2px(7.8)
            pygame.draw.circle(bg, (186, 88, 76), (pcx, pcy), self._m2px(0.95))
            pygame.draw.circle(bg, (142, 62, 54), (pcx, pcy), self._m2px(0.95), 3)
            pygame.draw.circle(bg, (212, 122, 106), (pcx, pcy), self._m2px(0.55), 2)
            # Bờ cát/đất vàng dọc hai bên dòng sông (x = 11.0 .. 14.0)
            pygame.draw.rect(bg, self.PALETTE["dirt_base"], self._rect_m2px(10.8, 0.25, 3.3, 19.5))
            # 2 Cây cầu đá bắc qua sông tại y = 4.05..5.90 và y = 16.1..17.9
            self._draw_cobblestone_road(bg, 11.2, 4.15, 2.5, 1.65)
            self._draw_cobblestone_road(bg, 11.2, 16.15, 2.5, 1.65)

        elif topology_id == 4:
            # MAP 4 (Ảnh 4): Nông trại Four Corners, đường sỏi chia 4 góc, ruộng cây & bờ sông tây
            pygame.draw.rect(bg, self.PALETTE["sand_base"], self._rect_m2px(0.25, 1.5, 4.2, 7.2), border_radius=12)
            pygame.draw.rect(bg, self.PALETTE["dirt_base"], self._rect_m2px(4.5, 7.6, 14.8, 1.4), border_radius=6)
            pygame.draw.rect(bg, self.PALETTE["dirt_base"], self._rect_m2px(9.2, 2.0, 1.4, 16.8), border_radius=6)
            self._draw_crop_field(bg, 11.2, 7.8, 3.6, 4.2, with_sprinklers=True)
            self._draw_crop_field(bg, 3.2, 15.2, 8.8, 3.4, with_sprinklers=True)

        # Sân lát đất quanh Start và Goal
        for px, py, pad_m in [(start_pos[0], start_pos[1], 1.1), (goal_pos[0], goal_pos[1], 1.2)]:
            sx, sy, sw, sh = self._rect_m2px(px - pad_m, py - pad_m, pad_m * 2, pad_m * 2)
            pygame.draw.rect(bg, self.PALETTE["dirt_edge"], (sx - 2, sy - 2, sw + 4, sh + 4), border_radius=8)
            pygame.draw.rect(bg, self.PALETTE["dirt_base"], (sx, sy, sw, sh), border_radius=6)

        # Rải hoa dại và cỏ non
        flower_colors = [(255, 225, 85), (255, 245, 250), (255, 145, 178), (130, 205, 255)]
        for _ in range(160):
            fx = rng.randint(18, window_size - 18)
            fy = rng.randint(18, window_size - 18)
            if rng.random() < 0.65:
                c = self.PALETTE["grass_dark"]
                pygame.draw.line(bg, c, (fx, fy), (fx - 2, fy - 4), 2)
                pygame.draw.line(bg, c, (fx, fy), (fx + 2, fy - 4), 2)
            else:
                fc = rng.choice(flower_colors)
                pygame.draw.rect(bg, fc, (fx - 2, fy - 2, 5, 5))
                pygame.draw.rect(bg, (255, 200, 50), (fx, fy, 2, 2))

        return bg

    def _draw_cobblestone_road(self, surf: pygame.Surface, x: float, y: float, w: float, h: float):
        rx, ry, rw, rh = self._rect_m2px(x, y, w, h)
        pygame.draw.rect(surf, self.PALETTE["stone_dark"], (rx - 2, ry - 2, rw + 4, rh + 4), border_radius=5)
        pygame.draw.rect(surf, self.PALETTE["stone_road"], (rx, ry, rw, rh), border_radius=4)
        step = max(10, int(0.45 * self.scale))
        for py in range(ry + 4, ry + rh - 4, step):
            for px in range(rx + 4, rx + rw - 4, step):
                pygame.draw.rect(surf, (148, 152, 162), (px, py, step - 3, step - 3), border_radius=2)

    def _draw_crop_field(
        self, surf: pygame.Surface, x: float, y: float, w: float, h: float, with_sprinklers: bool = False
    ):
        rx, ry, rw, rh = self._rect_m2px(x, y, w, h)
        pygame.draw.rect(surf, self.PALETTE["crop_soil"], (rx, ry, rw, rh), border_radius=6)
        pygame.draw.rect(surf, (104, 62, 32), (rx, ry, rw, rh), 2, border_radius=6)
        step = max(10, int(0.42 * self.scale))
        for py in range(ry + 6, ry + rh - 5, step):
            for px in range(rx + 6, rx + rw - 5, step):
                pygame.draw.circle(surf, (76, 168, 62), (px, py), 3)
                pygame.draw.circle(surf, (235, 95, 75), (px + 1, py - 1), 1)
        if with_sprinklers:
            pygame.draw.rect(surf, (185, 195, 210), (rx + rw // 2 - 4, ry + rh // 2 - 4, 8, 8), border_radius=2)

    def _draw_wooden_bridge(self, surf: pygame.Surface, x: float, y: float, w: float, h: float):
        rx, ry, rw, rh = self._rect_m2px(x, y, w, h)
        pygame.draw.rect(surf, self.PALETTE["wood_dark"], (rx, ry, rw, rh), border_radius=3)
        pygame.draw.rect(surf, self.PALETTE["wood_light"], (rx + 2, ry + 2, rw - 4, rh - 4), border_radius=2)

    # ------------------------------------------------------------------
    # 2. VẼ KHÔNG GIAN TRONG NHÀ & LÀM TỐI VÙNG NGOÀI (INDOOR HOUSE VIEW)
    # ------------------------------------------------------------------
    def draw_indoor_room_environment(
        self,
        screen: pygame.Surface,
        room_bounds: tuple[float, float, float, float],
        exit_portal: tuple[float, float],
        house_name: str,
        font: pygame.font.Font,
    ):
        """
        Vẽ không gian Nội thất bên trong Ngôi Nhà:
        - Toàn bộ vùng ngoài khung phòng được làm tối đen (Darkened Exterior Void) tạo cảm giác bước vào nhà.
        - Bên trong phòng là sàn ván gỗ ấm áp, tường bao nội thất, cửa sổ đón nắng, thảm dệt và lối ra.
        """
        w_scr, h_scr = screen.get_size()
        # 1. Làm tối toàn bộ vùng bên ngoài ngôi nhà
        screen.fill((10, 8, 16))

        rx, ry, rw, rh = self._rect_m2px(*room_bounds)

        # Vầng sáng ấm nhẹ tỏa ra quanh khung phòng trên nền tối
        glow = pygame.Surface((rw + 36, rh + 36), pygame.SRCALPHA)
        pygame.draw.rect(glow, (255, 195, 110, 28), (0, 0, rw + 36, rh + 36), border_radius=16)
        screen.blit(glow, (rx - 18, ry - 18))

        # 2. Khung tường bao nội thất & Sàn gỗ thông ấm áp
        pygame.draw.rect(screen, (92, 54, 28), (rx - 10, ry - 10, rw + 20, rh + 20), border_radius=8)
        pygame.draw.rect(screen, (214, 158, 98), (rx, ry, rw, rh), border_radius=4)

        # Kẻ ván sàn gỗ ngang dọc
        plank_h = max(12, int(0.45 * self.scale))
        for py in range(ry, ry + rh, plank_h):
            pygame.draw.line(screen, (186, 132, 74), (rx, py), (rx + rw, py), 2)

        # Tường hậu phía Bắc trong phòng (Wallpaper ấm áp + 2 Cửa sổ phát sáng)
        wall_top_h = max(26, int(0.85 * self.scale))
        pygame.draw.rect(screen, (236, 214, 178), (rx, ry, rw, wall_top_h))
        pygame.draw.line(screen, (124, 72, 34), (rx, ry + wall_top_h), (rx + rw, ry + wall_top_h), 3)

        for wx in [rx + rw // 4 - 16, rx + (3 * rw) // 4 - 16]:
            pygame.draw.rect(screen, self.PALETTE["window_glow"], (wx, ry + 5, 32, wall_top_h - 10), border_radius=2)
            pygame.draw.rect(screen, (112, 64, 30), (wx, ry + 5, 32, wall_top_h - 10), 2, border_radius=2)

        # 3. Thảm dệt trang trí chính giữa phòng khách
        rug_w, rug_h = int(rw * 0.42), int(rh * 0.32)
        rug_x, rug_y = rx + rw // 2 - rug_w // 2, ry + rh // 2 - rug_h // 2 + 12
        pygame.draw.rect(screen, (188, 64, 58), (rug_x, rug_y, rug_w, rug_h), border_radius=6)
        pygame.draw.rect(screen, (242, 208, 124), (rug_x + 4, rug_y + 4, rug_w - 8, rug_h - 8), 2, border_radius=4)

        # 4. Thảm Đỏ Lối Ra (Exit Door Mat) ở mép dưới căn phòng
        ex, ey = self._m2px(exit_portal[0]), self._m2px(exit_portal[1])
        pygame.draw.rect(screen, (215, 65, 58), (ex - 26, ry + rh - 14, 52, 16), border_radius=3)
        pygame.draw.rect(screen, (255, 220, 110), (ex - 26, ry + rh - 14, 52, 16), 2, border_radius=3)
        exit_lbl = font.render("EXIT [E]", True, (255, 245, 200))
        screen.blit(exit_lbl, (ex - exit_lbl.get_width() // 2, ry + rh + 6))

        # 5. Biển tên Ngôi nhà ở phía trên khung phòng
        title_surf = font.render(f"INSIDE: {house_name.upper()} (Press [E] or Walk to EXIT to leave)", True, (255, 230, 130))
        screen.blit(title_surf, (w_scr // 2 - title_surf.get_width() // 2, max(12, ry - 32)))

    # ------------------------------------------------------------------
    # 3. VẼ CÂY CỐI, SILO, NHÀ KÍNH, HỒ NƯỚC & NGÔI NHÀ STARDEW VALLEY
    # ------------------------------------------------------------------
    def draw_tree_sprite(
        self, screen: pygame.Surface, cx: int, cy: int, radius_px: int, obj_id: int = 1, name: str = "tree"
    ):
        # Nếu là Tháp Ủ Cỏ Đỏ (Silo) trong Map 2 & Map 4
        if name.startswith("silo"):
            w = int(radius_px * 2.1)
            h = int(radius_px * 3.6)
            sx, sy = cx - w // 2, cy - h + radius_px
            pygame.draw.rect(screen, (168, 64, 54), (sx, sy + w // 2, w, h - w // 2), border_radius=4)
            pygame.draw.rect(screen, (115, 38, 32), (sx, sy + w // 2, w, h - w // 2), 2, border_radius=4)
            pygame.draw.circle(screen, (208, 72, 58), (cx, sy + w // 2), w // 2)
            pygame.draw.circle(screen, (125, 38, 32), (cx, sy + w // 2), w // 2, 2)
            return

        # Nếu là Chậu cây nội thất trong nhà
        if name.startswith("furniture_plant"):
            pygame.draw.circle(screen, (168, 92, 48), (cx, cy + 4), radius_px // 2 + 2)
            pygame.draw.circle(screen, (68, 168, 78), (cx, cy - 4), radius_px)
            pygame.draw.circle(screen, (102, 204, 108), (cx - 3, cy - 7), radius_px // 2)
            return

        # Bóng râm dưới gốc cây
        shadow_w, shadow_h = int(radius_px * 2.2), int(radius_px * 1.2)
        sh_surf = pygame.Surface((shadow_w, shadow_h), pygame.SRCALPHA)
        pygame.draw.ellipse(sh_surf, self.PALETTE["shadow"], (0, 0, shadow_w, shadow_h))
        screen.blit(sh_surf, (cx - shadow_w // 2, cy + radius_px // 4))

        # Thân cây gỗ
        trunk_w = max(8, int(radius_px * 0.55))
        trunk_h = max(12, int(radius_px * 0.95))
        pygame.draw.rect(screen, self.PALETTE["wood_dark"], (cx - trunk_w // 2, cy - trunk_h // 4, trunk_w, trunk_h), border_radius=2)

        # Phân biệt Cây Hoa Anh Đào Hồng (Cherry Blossom), Cây Thông (Pine) và Cây Sồi (Oak)
        is_cherry = "cherry" in name
        is_pine = "pine" in name or (not is_cherry and obj_id % 3 == 0)

        if is_cherry:
            leaf_dark, leaf_mid, leaf_bright = (196, 98, 142), (236, 142, 184), (255, 192, 220)
        elif is_pine:
            leaf_dark, leaf_mid, leaf_bright = (32, 92, 68), (46, 128, 88), (72, 162, 108)
        else:
            leaf_dark, leaf_mid, leaf_bright = (38, 108, 54), (58, 148, 68), (92, 184, 82)

        canopy_y = cy - int(radius_px * 0.55)
        r_main = int(radius_px * 1.15)

        pygame.draw.circle(screen, leaf_dark, (cx, canopy_y + 4), r_main)
        pygame.draw.circle(screen, leaf_mid, (cx - r_main // 3, canopy_y), int(r_main * 0.78))
        pygame.draw.circle(screen, leaf_mid, (cx + r_main // 3, canopy_y), int(r_main * 0.78))
        pygame.draw.circle(screen, leaf_bright, (cx, canopy_y - r_main // 4), int(r_main * 0.72))

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
        # 1. Không vẽ đè khối tường bao tối đen khi đang ở chế độ Trong Nhà (Indoor Mode)
        if name.startswith("indoor_void_"):
            return

        # 2. Vẽ Nội thất bên trong nhà (Bàn, Kệ sách, Lò sưởi, Giường)
        if name.startswith("furniture_"):
            self._draw_indoor_furniture(screen, sx, sy, sw, sh, name)
            return

        # 3. Vẽ Sông, Biển, Ao hồ và 3 Hồ Cá (Water / Fish Ponds)
        if name.startswith("water_"):
            is_pond = "fishpond" in name
            if is_pond:
                pygame.draw.rect(screen, (118, 124, 134), (sx - 3, sy - 3, sw + 6, sh + 6), border_radius=5)
            pygame.draw.rect(screen, self.PALETTE["water_deep"], (sx, sy, sw, sh), border_radius=4 if is_pond else 2)
            pygame.draw.rect(screen, self.PALETTE["water_light"], (sx + 4, sy + 4, max(4, sw - 8), max(4, sh - 8)), border_radius=4)
            return

        # 4. Vẽ Nhà Kính (Glass Greenhouse - Ảnh 2 & Ảnh 4)
        if name.startswith("greenhouse"):
            pygame.draw.rect(screen, (215, 238, 250), (sx, sy, sw, sh), border_radius=6)
            pygame.draw.rect(screen, (120, 165, 190), (sx, sy, sw, sh), 3, border_radius=6)
            for gx in range(sx + 12, sx + sw - 6, 14):
                pygame.draw.line(screen, (150, 195, 215), (gx, sy + 3), (gx, sy + sh - 3), 2)
            for gy in range(sy + 12, sy + sh - 6, 14):
                pygame.draw.line(screen, (150, 195, 215), (sx + 3, gy), (sx + sw - 3, gy), 2)
            return

        # 5. Vẽ Cối xay gió (Windmill - Ảnh 2)
        if name.startswith("windmill"):
            pygame.draw.rect(screen, self.PALETTE["wood_light"], (sx + 4, sy + 8, sw - 8, sh - 8), border_radius=4)
            pygame.draw.rect(screen, self.PALETTE["wood_dark"], (sx + 4, sy + 8, sw - 8, sh - 8), 2, border_radius=4)
            cx, cy = sx + sw // 2, sy + 12
            for dx, dy in [(-18, -14), (18, -14), (-18, 14), (18, 14)]:
                pygame.draw.line(screen, (245, 240, 225), (cx, cy), (cx + dx, cy + dy), 4)
            pygame.draw.circle(screen, self.PALETTE["wood_dark"], (cx, cy), 4)
            return

        # 6. Vẽ Siêu thị JojaMart xanh dương (Ảnh 3)
        if name.startswith("jojamart"):
            pygame.draw.rect(screen, (62, 114, 184), (sx, sy, sw, sh), border_radius=5)
            pygame.draw.rect(screen, (195, 225, 255), (sx + 4, sy + 4, sw - 8, sh // 3), border_radius=3)
            pygame.draw.rect(screen, (36, 72, 128), (sx, sy, sw, sh), 3, border_radius=5)
            lbl = font.render("JOJAMART", True, (255, 255, 255))
            screen.blit(lbl, (sx + sw // 2 - lbl.get_width() // 2, sy + sh // 2 - 4))
            return

        # 7. Tường bao quanh biên bản đồ
        is_border = (
            name.startswith("wall_top")
            or name.startswith("wall_bottom")
            or name.startswith("wall_left")
            or name.startswith("wall_right")
        )
        if is_border:
            pygame.draw.rect(screen, self.PALETTE["wood_dark"], (sx, sy, sw, sh))
            pygame.draw.rect(screen, self.PALETTE["wood_light"], (sx + 1, sy + 1, max(1, sw - 2), max(1, sh - 2)))
            return

        # 8. Ngôi nhà Stardew Valley có Cửa Vào Nhà (Portal)
        min_house_px = max(44, int(1.6 * self.scale))
        if name.startswith("house_") or (sw >= min_house_px and sh >= min_house_px):
            self._draw_stardew_cottage(screen, sx, sy, sw, sh, obj_id, name, font)
        else:
            pygame.draw.rect(screen, self.PALETTE["wood_dark"], (sx, sy, sw, sh), border_radius=4)
            pygame.draw.rect(
                screen, self.PALETTE["wood_light"], (sx + 2, sy + 2, max(1, sw - 4), max(1, sh - 4)), border_radius=3
            )

    def _draw_indoor_furniture(self, screen: pygame.Surface, sx: int, sy: int, sw: int, sh: int, name: str):
        if "fireplace" in name:
            pygame.draw.rect(screen, (128, 72, 58), (sx, sy, sw, sh), border_radius=4)
            pygame.draw.rect(screen, (40, 28, 24), (sx + 8, sy + 8, max(8, sw - 16), max(8, sh - 10)), border_radius=3)
            pygame.draw.circle(screen, (255, 145, 45), (sx + sw // 2, sy + sh - 8), 8)
            pygame.draw.circle(screen, (255, 225, 85), (sx + sw // 2, sy + sh - 6), 4)
        elif "bed" in name:
            pygame.draw.rect(screen, self.PALETTE["wood_dark"], (sx, sy, sw, sh), border_radius=5)
            pygame.draw.rect(screen, (245, 240, 230), (sx + 4, sy + 6, sw - 8, sh // 3), border_radius=3)
            pygame.draw.rect(screen, (205, 72, 68), (sx + 4, sy + sh // 3 + 2, sw - 8, (2 * sh) // 3 - 6), border_radius=4)
        else:
            pygame.draw.rect(screen, self.PALETTE["wood_dark"], (sx, sy, sw, sh), border_radius=5)
            pygame.draw.rect(screen, self.PALETTE["wood_light"], (sx + 3, sy + 3, sw - 6, sh - 6), border_radius=4)

    def _draw_stardew_cottage(
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
        sh_surf = pygame.Surface((sw + 8, sh + 8), pygame.SRCALPHA)
        pygame.draw.rect(sh_surf, self.PALETTE["shadow"], (0, 0, sw + 8, sh + 8), border_radius=6)
        screen.blit(sh_surf, (sx + 3, sy + 4))

        roof_h = max(20, int(sh * 0.52))
        wall_y = sy + roof_h - 4
        wall_h = max(16, sh - roof_h + 4)

        is_barn = "Barn" in name or "Coop" in name
        wall_col = (196, 68, 58) if is_barn else self.PALETTE["wall_cream"]
        pygame.draw.rect(screen, wall_col, (sx + 2, wall_y, sw - 4, wall_h), border_radius=3)
        pygame.draw.rect(screen, self.PALETTE["wood_dark"], (sx + 2, wall_y, sw - 4, wall_h), 2, border_radius=3)

        use_red = ("Blue" not in name) and (obj_id % 2 == 1 or is_barn)
        roof_main = self.PALETTE["roof_red"] if use_red else self.PALETTE["roof_blue"]
        roof_dark = self.PALETTE["roof_red_dark"] if use_red else self.PALETTE["roof_blue_dark"]

        pygame.draw.rect(screen, roof_main, (sx, sy, sw, roof_h), border_radius=5)
        for ry in range(sy + 5, sy + roof_h - 3, 6):
            pygame.draw.line(screen, roof_dark, (sx + 3, ry), (sx + sw - 4, ry), 2)
        pygame.draw.rect(screen, self.PALETTE["wood_dark"], (sx, sy, sw, roof_h), 2, border_radius=5)

        # Cửa chính (Portal Door) + Thảm đỏ chào mừng (Đi vào đây sẽ chuyển vào Map Trong Nhà)
        door_w = min(22, max(12, sw // 4))
        door_h = min(24, max(12, wall_h - 4))
        door_x = sx + sw // 2 - door_w // 2
        door_y = sy + sh - door_h

        pygame.draw.rect(screen, self.PALETTE["wood_dark"], (door_x, door_y, door_w, door_h), border_top_left_radius=4, border_top_right_radius=4)
        pygame.draw.rect(screen, self.PALETTE["wood_light"], (door_x + 2, door_y + 2, door_w - 4, door_h - 2), border_top_left_radius=3, border_top_right_radius=3)
        pygame.draw.circle(screen, (255, 215, 70), (door_x + door_w - 5, door_y + door_h // 2), 2)
        pygame.draw.rect(screen, (215, 65, 58), (door_x - 3, sy + sh, door_w + 6, 6), border_radius=2)

        # Cửa sổ phát sáng hai bên
        if sw >= 68 and wall_h >= 18:
            win_size = min(14, max(8, wall_h // 2))
            win_y = wall_y + 5
            for wx in [sx + 10, sx + sw - 10 - win_size]:
                if abs(wx - door_x) > win_size:
                    pygame.draw.rect(screen, self.PALETTE["window_glow"], (wx, win_y, win_size, win_size))
                    pygame.draw.rect(screen, self.PALETTE["wood_dark"], (wx, win_y, win_size, win_size), 2)

    # ------------------------------------------------------------------
    # 4. ROBOT NHÂN VẬT & NPC DÂN LÀNG (ĐÃ SỬA LỖI human.id)
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
        bob_y = int(round(math.sin(sim_time * 12.0) * 2.0)) if speed > 0.05 else 0
        sh_w, sh_h = int(rad_px * 2.1), int(rad_px * 1.0)
        sh_surf = pygame.Surface((sh_w, sh_h), pygame.SRCALPHA)
        pygame.draw.ellipse(sh_surf, self.PALETTE["shadow"], (0, 0, sh_w, sh_h))
        screen.blit(sh_surf, (rx - sh_w // 2, ry + rad_px // 2))

        body_color = (225, 65, 65) if is_collision else (72, 148, 235)
        body_highlight = (248, 113, 113) if is_collision else (135, 198, 255)
        outline_color = (28, 45, 78)

        leg_swing = int(round(math.sin(sim_time * 12.0) * 3.0)) if speed > 0.05 else 0
        foot_w, foot_h = max(5, rad_px // 2), max(4, rad_px // 3)
        pygame.draw.rect(screen, (65, 75, 95), (rx - foot_w - 1, ry + rad_px // 3 + leg_swing, foot_w, foot_h), border_radius=2)
        pygame.draw.rect(screen, (65, 75, 95), (rx + 1, ry + rad_px // 3 - leg_swing, foot_w, foot_h), border_radius=2)

        w_body, h_body = int(rad_px * 1.55), int(rad_px * 1.45)
        bx, by = rx - w_body // 2, ry - h_body // 2 + bob_y

        pygame.draw.rect(screen, body_color, (bx, by, w_body, h_body), border_radius=6)
        pygame.draw.rect(screen, body_highlight, (bx + 2, by + 2, w_body - 4, max(4, h_body // 3)), border_radius=4)
        pygame.draw.rect(screen, outline_color, (bx, by, w_body, h_body), 2, border_radius=6)

        ant_top_y = by - 7
        pygame.draw.line(screen, outline_color, (rx, by), (rx, ant_top_y), 2)
        bulb_col = (255, 80, 80) if is_collision else (80, 245, 165)
        pygame.draw.circle(screen, bulb_col, (rx, ant_top_y), 4)

        look_dx = int(round(math.cos(theta) * 3.0))
        look_dy = int(round(math.sin(theta) * 2.5))
        visor_w, visor_h = max(10, int(w_body * 0.72)), max(7, int(h_body * 0.48))
        vx, vy = rx - visor_w // 2 + look_dx, by + int(h_body * 0.25) + look_dy

        pygame.draw.rect(screen, (22, 32, 48), (vx, vy, visor_w, visor_h), border_radius=3)
        eye_col = (255, 110, 110) if is_collision else (95, 250, 225)
        eye_r = max(2, visor_h // 4)
        pygame.draw.circle(screen, eye_col, (vx + visor_w // 3, vy + visor_h // 2), eye_r)
        pygame.draw.circle(screen, eye_col, (vx + (2 * visor_w) // 3, vy + visor_h // 2), eye_r)

        if carrying_item:
            px_box = rx + int(math.cos(theta) * (rad_px * 0.65)) - 5
            py_box = ry + int(math.sin(theta) * (rad_px * 0.65)) - 5 + bob_y
            pygame.draw.rect(screen, (218, 152, 84), (px_box, py_box, 10, 9), border_radius=2)
            pygame.draw.rect(screen, (125, 72, 28), (px_box, py_box, 10, 9), 1, border_radius=2)
            pygame.draw.line(screen, (235, 75, 65), (px_box + 5, py_box), (px_box + 5, py_box + 8), 2)

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
        # Đã sửa lỗi: lấy human.id an toàn thay vì human.obj_id
        hid = getattr(human, "id", getattr(human, "obj_id", 0))
        hair_colors = [(115, 62, 36), (235, 182, 65), (185, 68, 52), (55, 58, 72)]
        hair_col = hair_colors[hid % len(hair_colors)]

        act_name = human.activity.value
        if act_name == "STANDING":
            shirt_col = (56, 178, 212)
        elif act_name == "WALKING":
            shirt_col = (234, 118, 45)
        else:
            shirt_col = (225, 55, 85)

        bob_y = int(round(math.sin(sim_time * 10.0 + hid) * 2.0)) if human.speed > 0.1 else 0

        sh_w, sh_h = int(rad_px * 1.9), int(rad_px * 0.9)
        sh_surf = pygame.Surface((sh_w, sh_h), pygame.SRCALPHA)
        pygame.draw.ellipse(sh_surf, self.PALETTE["shadow"], (0, 0, sh_w, sh_h))
        screen.blit(sh_surf, (cx - sh_w // 2, cy + rad_px // 2))

        swing = int(round(math.sin(sim_time * 10.0 + hid) * 3.0)) if human.speed > 0.1 else 0
        pygame.draw.rect(screen, (52, 78, 128), (cx - 5, cy + 2 + swing, 4, 6), border_radius=1)
        pygame.draw.rect(screen, (52, 78, 128), (cx + 1, cy + 2 - swing, 4, 6), border_radius=1)

        torso_w, torso_h = max(12, int(rad_px * 1.25)), max(10, int(rad_px * 0.95))
        pygame.draw.rect(screen, shirt_col, (cx - torso_w // 2, cy - torso_h // 2 + 2 + bob_y, torso_w, torso_h), border_radius=4)
        pygame.draw.rect(screen, (35, 30, 30), (cx - torso_w // 2, cy - torso_h // 2 + 2 + bob_y, torso_w, torso_h), 1, border_radius=4)

        head_r = max(6, int(rad_px * 0.68))
        head_y = cy - torso_h // 2 - head_r // 2 + 1 + bob_y
        pygame.draw.circle(screen, (255, 218, 185), (cx, head_y), head_r)
        pygame.draw.circle(screen, (65, 42, 32), (cx, head_y), head_r, 1)
        pygame.draw.arc(screen, hair_col, (cx - head_r, head_y - head_r - 1, head_r * 2, head_r * 2), 0.0, math.pi, max(4, head_r // 2 + 2))

        ex = cx + int(math.cos(human.theta) * 2.5)
        ey = head_y + int(math.sin(human.theta) * 1.5)
        pygame.draw.circle(screen, (40, 30, 30), (ex - 2, ey), 1)
        pygame.draw.circle(screen, (40, 30, 30), (ex + 2, ey), 1)

        ctx_name = human.social_context.value
        if ctx_name == "INTERACTING" and not debug_mode:
            bx, by = cx + 6, head_y - head_r - 14
            pygame.draw.rect(screen, (255, 255, 255), (bx, by, 20, 12), border_radius=4)
            pygame.draw.rect(screen, (85, 65, 45), (bx, by, 20, 12), 1, border_radius=4)
            for dot_i in range(3):
                pygame.draw.circle(screen, (95, 75, 55), (bx + 5 + dot_i * 5, by + 6), 1)

    def draw_delivery_goal(self, screen: pygame.Surface, gx: int, gy: int, grad_px: int, sim_time: float):
        pulse = int(math.sin(sim_time * 4.0) * 3)
        pygame.draw.circle(screen, (245, 215, 110), (gx, gy), grad_px + pulse, 2)
        pygame.draw.circle(screen, (118, 215, 125), (gx, gy), max(4, grad_px - 3))

        bin_w, bin_h = max(20, int(grad_px * 1.4)), max(16, int(grad_px * 1.1))
        bx, by = gx - bin_w // 2, gy - bin_h // 2
        pygame.draw.rect(screen, self.PALETTE["wood_dark"], (bx, by, bin_w, bin_h), border_radius=3)
        pygame.draw.rect(screen, self.PALETTE["wood_light"], (bx + 2, by + 2, bin_w - 4, bin_h - 4), border_radius=2)
        pygame.draw.rect(screen, (250, 204, 21), (gx - 3, by + bin_h // 2 - 3, 6, 6), border_radius=1)

        arrow_y = by - 10 + int(math.sin(sim_time * 6.0) * 4.0)
        pts = [(gx, arrow_y + 7), (gx - 6, arrow_y), (gx + 6, arrow_y)]
        pygame.draw.polygon(screen, (255, 215, 40), pts)
        pygame.draw.polygon(screen, (145, 85, 20), pts, 1)

    def draw_agv_cart(self, screen: pygame.Surface, cx: int, cy: int, rad_px: int, theta: float):
        w, h = max(16, int(rad_px * 1.7)), max(14, int(rad_px * 1.4))
        pygame.draw.rect(screen, (75, 65, 60), (cx - w // 2, cy - h // 2, w, h), border_radius=4)
        pygame.draw.rect(screen, (168, 112, 62), (cx - w // 2 + 2, cy - h // 2 + 2, w - 4, h - 4), border_radius=3)
        pygame.draw.rect(screen, (168, 85, 247), (cx - w // 4, cy - h // 4, w // 2, h // 2), border_radius=2)