# stardew_game.py
"""
STARDEW VALLEY COZY RPG - 4 PROCEDURAL MAPS & INDOOR HOUSE EDITION
- Điều khiển nhân vật mượt mà 8 hướng (WASD / Arrow Keys, giữ Shift để chạy)
- 4 Map sinh ngẫu nhiên (Beach Farm, Hill-top Farm, Pelican Town, Four Corners Forest)
- Các nhân vật NPC dân làng đi dạo ngẫu nhiên, trò chuyện và hiện biểu cảm
- Đi vào bất kỳ cửa nhà nào (hoặc nhấn phím E) -> Làm tối vùng ngoài, mở căn phòng nội thất
- Giao diện UI chuẩn Stardew Valley: Hộp gỗ nhỏ góc phải trên + Thanh nút bấm gọn dưới đáy
"""

import math
import random
import sys
import pygame

from asset_builder import ensure_assets


# ==============================================================================
# CẤU HÌNH MÀN HÌNH & LƯỚI TILEMAP
# ==============================================================================
SCREEN_W = 1152
SCREEN_H = 768
TILE_SIZE = 32
GRID_COLS = SCREEN_W // TILE_SIZE  # 36 cột
GRID_ROWS = SCREEN_H // TILE_SIZE  # 24 hàng

# Mã địa hình Tile
T_GRASS = 0
T_WATER = 1
T_SAND = 2
T_DIRT = 3
T_COBBLE = 4
T_CLIFF = 5
T_CROP = 6
T_BRIDGE = 7


# ==============================================================================
# LỚP NHÂN VẬT (NGƯỜI CHƠI & DÂN LÀNG NPC)
# ==============================================================================
class Character:
    def __init__(
        self,
        name: str,
        x: float,
        y: float,
        shirt_col: tuple,
        hair_col: tuple,
        pants_col: tuple = (52, 78, 132),
        is_player: bool = False,
    ):
        self.name = name
        self.x = float(x)
        self.y = float(y)
        self.shirt_col = shirt_col
        self.hair_col = hair_col
        self.pants_col = pants_col
        self.is_player = is_player

        self.radius = 11.0
        self.speed = 175.0 if is_player else random.uniform(62.0, 88.0)
        self.vx = 0.0
        self.vy = 0.0
        self.facing = "down"  # down, up, left, right
        self.anim_timer = random.uniform(0.0, 10.0)

        # Trạng thái AI cho NPC ngẫu nhiên
        self.state = "walk"
        self.state_timer = random.uniform(1.5, 4.0)
        self.target_dir = (0.0, 1.0)
        self.emote: str | None = None
        self.emote_timer = 0.0

    @property
    def sort_y(self) -> float:
        return self.y + 10.0

    def update_ai(self, dt: float, world_game):
        """AI cho NPC tự đi dạo, rẽ theo đường mòn và dừng lại trò chuyện."""
        self.state_timer -= dt
        if self.emote_timer > 0.0:
            self.emote_timer -= dt
            if self.emote_timer <= 0.0:
                self.emote = None

        if self.state_timer <= 0.0:
            if random.random() < 0.38:
                self.state = "idle"
                self.state_timer = random.uniform(1.2, 3.0)
                self.vx, self.vy = 0.0, 0.0
                if random.random() < 0.45:
                    self.emote = random.choice(["...", "♥", "♪", "!"])
                    self.emote_timer = 1.8
            else:
                self.state = "walk"
                self.state_timer = random.uniform(2.0, 4.5)
                dirs = [(1, 0), (-1, 0), (0, 1), (0, -1), (0.7, 0.7), (-0.7, 0.7)]
                dx, dy = random.choice(dirs)
                self.target_dir = (dx, dy)

        if self.state == "walk":
            dx, dy = self.target_dir
            self.vx = dx * self.speed
            self.vy = dy * self.speed
            moved = self.move_and_slide(self.vx * dt, self.vy * dt, world_game)
            if not moved:
                # Đổi hướng nếu gặp vật cản
                dx, dy = random.choice([(1, 0), (-1, 0), (0, 1), (0, -1)])
                self.target_dir = (dx, dy)
        self._update_facing_and_anim(dt)

    def move_and_slide(self, dx: float, dy: float, world_game) -> bool:
        """Di chuyển có trượt mượt theo cạnh tường/cây (Collision Sliding)."""
        moved = False
        if abs(dx) > 1e-4:
            nx = self.x + dx
            if not world_game.is_circle_blocked(nx, self.y, self.radius):
                self.x = nx
                moved = True
        if abs(dy) > 1e-4:
            ny = self.y + dy
            if not world_game.is_circle_blocked(self.x, ny, self.radius):
                self.y = ny
                moved = True
        return moved

    def _update_facing_and_anim(self, dt: float):
        spd = math.hypot(self.vx, self.vy)
        if spd > 5.0:
            self.anim_timer += dt * (spd / 18.0)
            if abs(self.vx) > abs(self.vy):
                self.facing = "right" if self.vx > 0 else "left"
            else:
                self.facing = "down" if self.vy > 0 else "up"
        else:
            self.anim_timer = 0.0

    def draw(self, screen: pygame.Surface, font_small: pygame.font.Font):
        cx, cy = int(round(self.x)), int(round(self.y))
        is_moving = math.hypot(self.vx, self.vy) > 5.0
        bob = int(round(abs(math.sin(self.anim_timer)) * 2.5)) if is_moving else 0
        swing = int(round(math.sin(self.anim_timer) * 4.0)) if is_moving else 0

        # 1. Bóng đổ dưới chân
        sh = pygame.Surface((24, 10), pygame.SRCALPHA)
        pygame.draw.ellipse(sh, (14, 24, 12, 105), (0, 0, 24, 10))
        screen.blit(sh, (cx - 12, cy + 5))

        # 2. Vòng sáng nhẹ dưới chân Người Chơi để dễ nhận biết
        if self.is_player:
            pygame.draw.ellipse(screen, (255, 230, 95), (cx - 13, cy + 4, 26, 11), 2)

        # 3. Hai chân bước đi
        pygame.draw.rect(screen, self.pants_col, (cx - 6, cy + 1 + swing, 5, 8), border_radius=2)
        pygame.draw.rect(screen, self.pants_col, (cx + 1, cy + 1 - swing, 5, 8), border_radius=2)
        pygame.draw.rect(screen, (72, 42, 22), (cx - 6, cy + 7 + swing, 5, 3))
        pygame.draw.rect(screen, (72, 42, 22), (cx + 1, cy + 7 - swing, 5, 3))

        # 4. Thân áo & Dây yếm nông trại (Stardew Overalls)
        body_y = cy - 11 - bob
        pygame.draw.rect(screen, self.shirt_col, (cx - 9, body_y, 18, 14), border_radius=4)
        if self.is_player:
            pygame.draw.rect(screen, (48, 92, 168), (cx - 6, body_y + 5, 12, 9), border_radius=2)
        pygame.draw.rect(screen, (34, 24, 20), (cx - 9, body_y, 18, 14), 1, border_radius=4)

        # Hai tay vung theo nhịp bước
        arm_swing = int(round(math.sin(self.anim_timer) * 3.0)) if is_moving else 0
        pygame.draw.rect(screen, self.shirt_col, (cx - 12, body_y + 2 - arm_swing, 4, 9), border_radius=2)
        pygame.draw.rect(screen, self.shirt_col, (cx + 8, body_y + 2 + arm_swing, 4, 9), border_radius=2)

        # 5. Đầu & Mái tóc Pixel-Art theo 4 hướng nhìn
        head_y = body_y - 9
        pygame.draw.circle(screen, (255, 218, 184), (cx, head_y), 10)
        pygame.draw.circle(screen, (68, 42, 30), (cx, head_y), 10, 1)

        # Tóc phủ đỉnh đầu
        pygame.draw.arc(screen, self.hair_col, (cx - 11, head_y - 11, 22, 20), 0, math.pi, 6)
        if self.facing == "up":
            pygame.draw.circle(screen, self.hair_col, (cx, head_y - 1), 9)
        else:
            ox = -3 if self.facing == "left" else (3 if self.facing == "right" else 0)
            pygame.draw.rect(screen, (38, 26, 24), (cx - 4 + ox, head_y - 1, 2, 3))
            pygame.draw.rect(screen, (38, 26, 24), (cx + 2 + ox, head_y - 1, 2, 3))

        # Mũ rơm nhỏ cho người chơi
        if self.is_player:
            pygame.draw.ellipse(screen, (242, 198, 84), (cx - 13, head_y - 12, 26, 7))
            pygame.draw.rect(screen, (218, 168, 58), (cx - 8, head_y - 15, 16, 5), border_radius=2)
            pygame.draw.line(screen, (204, 58, 52), (cx - 8, head_y - 11), (cx + 8, head_y - 11), 2)

        # 6. Bong bóng cảm xúc (Emote Bubble)
        if self.emote:
            bx, by = cx + 8, head_y - 24
            pygame.draw.rect(screen, (255, 252, 240), (bx, by, 24, 16), border_radius=5)
            pygame.draw.rect(screen, (92, 58, 32), (bx, by, 24, 16), 2, border_radius=5)
            em_col = (225, 48, 68) if self.emote in ("♥", "!") else (72, 52, 38)
            lbl = font_small.render(self.emote, True, em_col)
            screen.blit(lbl, (bx + 12 - lbl.get_width() // 2, by + 1))


# ==============================================================================
# LỚP CÔNG TRÌNH & CÂY CỐI CÓ Y-SORTING
# ==============================================================================
class PropObject:
    def __init__(
        self,
        kind: str,
        x: int,
        y: int,
        sprite: pygame.Surface,
        collider_rect: pygame.Rect,
        door_rect: pygame.Rect | None = None,
        interior_type: str = "farmhouse",
        title: str = "Stardew Cottage",
    ):
        self.kind = kind
        self.x = x
        self.y = y
        self.sprite = sprite
        self.collider = collider_rect
        self.door_rect = door_rect
        self.interior_type = interior_type
        self.title = title

    @property
    def sort_y(self) -> float:
        return float(self.collider.bottom)

    def draw(self, screen: pygame.Surface):
        screen.blit(self.sprite, (self.x, self.y))


# ==============================================================================
# LỚP QUẢN LÝ GAME CHÍNH (4 MAP PROCEDURAL + INDOOR HOUSE + STARDEW UI)
# ==============================================================================
class StardewRPGGame:
    MAP_TITLES = {
        1: "Map 1: Beach & Island Farm",
        2: "Map 2: Hill-top & Greenhouse",
        3: "Map 3: Pelican Town & River",
        4: "Map 4: Four Corners & Ponds",
    }

    def __init__(self):
        pygame.init()
        pygame.display.set_caption("Stardew Valley Cozy RPG - 4 Procedural Maps & Indoor House")
        self.screen = pygame.display.set_mode((SCREEN_W, SCREEN_H))
        self.clock = pygame.time.Clock()

        self.font_ui = pygame.font.SysFont("consolas", 15, bold=True)
        self.font_small = pygame.font.SysFont("consolas", 13, bold=True)
        self.font_title = pygame.font.SysFont("consolas", 18, bold=True)

        # Đảm bảo bộ tài nguyên .png đã được tạo
        self.asset_dir = ensure_assets()
        self.images: dict[str, pygame.Surface] = {}
        self._load_png_assets()

        self.current_map_id = 1
        self.map_seed = random.randint(1000, 9999)
        self.sim_time = 0.0
        self.show_ui = True

        # Hệ thống chuyển cảnh Fade & Chế độ Trong Nhà (Indoor Mode)
        self.in_indoor = False
        self.indoor_info: dict = {}
        self.outdoor_backup: dict | None = None
        self.fade_alpha = 0.0
        self.portal_cooldown = 0.0

        # Dữ liệu bản đồ hiện tại
        self.grid = [[T_GRASS for _ in range(GRID_COLS)] for _ in range(GRID_ROWS)]
        self.terrain_surface = pygame.Surface((SCREEN_W, SCREEN_H))
        self.props: list[PropObject] = []
        self.npcs: list[Character] = []
        self.player = Character("Farmer", 320, 420, (228, 72, 64), (112, 58, 32), is_player=True)

        # Các nút bấm trên thanh Mini Hotbar dưới đáy màn hình
        self.ui_buttons: list[tuple[pygame.Rect, str, str]] = []
        self._build_ui_buttons()

        self.generate_map(self.current_map_id, new_seed=False)

    def _load_png_assets(self):
        for p in self.asset_dir.glob("*.png"):
            self.images[p.stem] = pygame.image.load(str(p)).convert_alpha()

    def _build_ui_buttons(self):
        labels = [
            ("1:Beach", "map1"),
            ("2:Hilltop", "map2"),
            ("3:Town", "map3"),
            ("4:Forest", "map4"),
            ("[R] Randomize", "rand"),
            ("[E] Enter/Exit House", "door"),
            ("[H] UI", "hud"),
        ]
        total_w = sum(len(t) * 9 + 24 for t, _ in labels) + (len(labels) - 1) * 8
        start_x = (SCREEN_W - total_w) // 2
        y = SCREEN_H - 42
        cur_x = start_x
        self.ui_buttons.clear()
        for text, act in labels:
            bw = len(text) * 9 + 24
            self.ui_buttons.append((pygame.Rect(cur_x, y, bw, 32), text, act))
            cur_x += bw + 8

    # ------------------------------------------------------------------
    # BỘ SINH NGẪU NHIÊN 4 BẢN ĐỒ STARDEW VALLEY (PROCEDURAL GENERATOR)
    # ------------------------------------------------------------------
    def generate_map(self, map_id: int, new_seed: bool = True):
        self.current_map_id = map_id
        if new_seed:
            self.map_seed = random.randint(1000, 99999)
        rng = random.Random(self.map_seed + map_id * 31)

        self.in_indoor = False
        self.outdoor_backup = None
        self.portal_cooldown = 0.8
        self.fade_alpha = 180.0

        self.grid = [[T_GRASS for _ in range(GRID_COLS)] for _ in range(GRID_ROWS)]
        self.props.clear()
        self.npcs.clear()

        def fill_tiles(c1: int, r1: int, c2: int, r2: int, t_type: int):
            for r in range(max(0, r1), min(GRID_ROWS, r2)):
                for c in range(max(0, c1), min(GRID_COLS, c2)):
                    self.grid[r][c] = t_type

        # ==================================================================
        # MAP 1: BEACH & ISLAND FARM (Ảnh 1 - Biển xanh, bãi cát, đảo, cầu gỗ)
        # ==================================================================
        if map_id == 1:
            # Biển bao quanh bờ Tây, Nam và góc Đông Nam
            fill_tiles(0, 0, 6, GRID_ROWS, T_WATER)
            fill_tiles(0, 19, GRID_COLS, GRID_ROWS, T_WATER)
            fill_tiles(32, 4, GRID_COLS, GRID_ROWS, T_WATER)
            # Hồ nước lớn phía Nam & Ao nhỏ ở giữa
            fill_tiles(19, 16, 27, 22, T_WATER)
            fill_tiles(18, 9, 21, 12, T_WATER)

            # Đảo nhỏ bên trái nối bằng Cầu gỗ
            fill_tiles(1, 3, 5, 9, T_GRASS)
            fill_tiles(5, 5, 7, 7, T_BRIDGE)

            # Bãi cát vàng trải rộng góc Đông Bắc & dọc bờ biển
            fill_tiles(16, 1, 32, 8, T_SAND)
            fill_tiles(6, 8, 9, 19, T_SAND)
            fill_tiles(26, 12, 32, 19, T_SAND)

            # Đường mòn đất & Khu ruộng canh tác
            fill_tiles(8, 5, 16, 7, T_DIRT)
            fill_tiles(11, 7, 13, 16, T_DIRT)
            fill_tiles(9, 7, 15, 11, T_CROP)
            fill_tiles(10, 12, 16, 16, T_CROP)

            # Đặt các ngôi nhà (Barn, Farmhouse, Beach Cabin)
            self._place_building("house_barn", 6 * 32, 1 * 32 + 8, "barn", "Island Red Barn")
            self._place_building("house_farm", 12 * 32, 1 * 32 + 4, "farmhouse", "Beach Farmhouse")
            self._place_building("house_town", 26 * 32, 7 * 32, "cabin", "Seaside Cabin")

            self.player.x, self.player.y = 13.5 * 32, 6.2 * 32

        # ==================================================================
        # MAP 2: HILL-TOP FARM & GREENHOUSE (Ảnh 2 - Đường đá, Nhà kính, Silo)
        # ==================================================================
        elif map_id == 2:
            # Suối nước bên rìa Tây
            fill_tiles(0, 0, 2, GRID_ROWS, T_WATER)
            # Vách đá đồi chạy ngang phía Bắc và phía Nam đường đá
            fill_tiles(3, 2, 34, 4, T_CLIFF)
            fill_tiles(3, 14, 12, 16, T_CLIFF)
            fill_tiles(26, 14, 34, 16, T_CLIFF)

            # Hệ thống đường lát đá xám (Cobblestone Road) đặc trưng của Ảnh 2
            fill_tiles(5, 11, 33, 13, T_COBBLE)
            fill_tiles(18, 5, 20, 12, T_COBBLE)
            fill_tiles(8, 12, 10, 22, T_COBBLE)
            fill_tiles(24, 12, 26, 22, T_COBBLE)

            # Ruộng cây có Sprinkler tưới tiêu ở giữa & góc Đông Nam
            fill_tiles(10, 5, 17, 10, T_CROP)
            fill_tiles(27, 17, 33, 22, T_CROP)

            # 2 Tháp Silo đỏ bên trái + Nhà Kính lớn + Cối xay + Nhà chính + Chuồng đỏ
            self._place_prop("silo", 3 * 32, 2 * 32)
            self._place_prop("silo", 4 * 32 + 22, 2 * 32)
            self._place_building("greenhouse", 5 * 32, 4 * 32 + 10, "greenhouse", "Crystal Greenhouse")
            self._place_building("house_town", 20 * 32 + 12, 4 * 32 + 18, "cabin", "Log Storage Shed")
            self._place_building("house_farm", 25 * 32, 4 * 32 + 10, "farmhouse", "Hill-top Farmhouse")
            self._place_building("house_barn", 13 * 32, 15 * 32, "barn", "Red Poultry Coop")
            self._place_building("house_barn", 18 * 32, 15 * 32 + 8, "barn", "Grand Red Barn")

            self.player.x, self.player.y = 19.0 * 32, 12.0 * 32

        # ==================================================================
        # MAP 3: PELICAN TOWN & RIVER (Ảnh 3 - Quảng trường, Sông & 2 Cầu đá)
        # ==================================================================
        elif map_id == 3:
            # Dòng sông xanh chảy dọc từ Bắc xuống Nam (cột 21..24)
            fill_tiles(21, 0, 25, GRID_ROWS, T_WATER)
            fill_tiles(20, 0, 21, GRID_ROWS, T_SAND)
            fill_tiles(25, 0, 26, GRID_ROWS, T_SAND)

            # 2 Cây cầu đá bắc qua dòng sông (Bắc và Nam)
            fill_tiles(20, 6, 26, 8, T_BRIDGE)
            fill_tiles(20, 18, 26, 20, T_BRIDGE)

            # Quảng trường lát đá cuội (Town Square) bên Tây
            fill_tiles(6, 6, 14, 14, T_COBBLE)
            fill_tiles(2, 6, 6, 8, T_COBBLE)
            fill_tiles(8, 14, 10, 21, T_COBBLE)
            fill_tiles(10, 15, 16, 17, T_COBBLE)
            fill_tiles(14, 6, 20, 8, T_DIRT)
            fill_tiles(26, 6, 33, 8, T_DIRT)
            fill_tiles(16, 18, 20, 20, T_DIRT)

            # Các tòa nhà trong Thị trấn Pelican
            self._place_building("house_town", 9 * 32, 1 * 32 + 8, "shop", "Pierre's General Store")
            self._place_building("house_blue", 15 * 32 + 10, 2 * 32 + 12, "cabin", "Riverside Blue House")
            self._place_building("house_farm", 14 * 32, 8 * 32 + 10, "saloon", "The Stardrop Saloon")
            self._place_building("house_blue", 2 * 32, 13 * 32, "cabin", "2 Willow Lane")
            self._place_building("house_manor", 15 * 32 + 8, 13 * 32 + 12, "manor", "Mayor's Manor")
            # Bên kia bờ sông: Siêu thị JojaMart & Lò rèn
            self._place_building("jojamart", 27 * 32, 1 * 32 + 8, "shop", "JojaMart Supermarket")
            self._place_building("house_town", 28 * 32, 13 * 32, "cabin", "Clint's Blacksmith")

            self.player.x, self.player.y = 10.0 * 32, 10.0 * 32

        # ==================================================================
        # MAP 4: FOUR CORNERS & 3 FISH PONDS (Ảnh 4 - Đảo Nhà kính, 3 Hồ cá)
        # ==================================================================
        else:
            # Sông bao quanh đảo Nhà Kính bên Tây
            fill_tiles(0, 0, 2, GRID_ROWS, T_WATER)
            fill_tiles(6, 0, 8, 12, T_WATER)
            fill_tiles(0, 11, 8, 13, T_WATER)
            fill_tiles(6, 6, 8, 8, T_BRIDGE)

            # Đường đất/đá chia 4 góc nông trại
            fill_tiles(8, 10, 34, 12, T_DIRT)
            fill_tiles(18, 2, 20, 22, T_DIRT)

            # Ruộng cây xanh mướt ở giữa & góc Tây Nam
            fill_tiles(21, 6, 27, 10, T_CROP)
            fill_tiles(5, 18, 17, 22, T_CROP)

            # Đảo Nhà Kính bên trái + Silo & Nhà chính góc Đông Bắc
            self._place_building("greenhouse", 2 * 32, 2 * 32 + 10, "greenhouse", "Island Greenhouse")
            self._place_prop("silo", 19 * 32 + 16, 1 * 32 + 8)
            self._place_building("house_farm", 22 * 32, 1 * 32 + 8, "farmhouse", "Forest Farmhouse")

            # 2 Chuồng gia súc đỏ (Twin Barns) góc Tây Nam
            self._place_building("house_barn", 4 * 32, 13 * 32 + 8, "barn", "West Red Barn")
            self._place_building("house_barn", 12 * 32, 13 * 32 + 8, "barn", "East Red Barn")

            # 3 Hồ nuôi cá viền đá (Fish Ponds) ở góc Đông Nam
            self._place_prop("fishpond", 26 * 32, 15 * 32)
            self._place_prop("fishpond", 29 * 32, 15 * 32 + 10)
            self._place_prop("fishpond", 32 * 32, 16 * 32)
            self._place_building("house_blue", 21 * 32, 16 * 32, "cabin", "Fisherman's Cottage")

            self.player.x, self.player.y = 19.0 * 32, 11.0 * 32

        # ------------------------------------------------------------------
        # RẢI CÂY ANH ĐÀO, CÂY SỒI, CÂY THÔNG NGẪU NHIÊN KHÔNG CHÈN LÊN ĐƯỜNG/NHÀ
        # ------------------------------------------------------------------
        tree_types = ["tree_cherry", "tree_oak", "tree_pine"]
        placed_trees = 0
        for _ in range(180):
            if placed_trees >= 26:
                break
            tc = rng.randint(2, GRID_COLS - 3)
            tr = rng.randint(2, GRID_ROWS - 3)
            if self.grid[tr][tc] != T_GRASS:
                continue
            tx, ty = tc * TILE_SIZE, tr * TILE_SIZE
            if math.hypot(tx - self.player.x, ty - self.player.y) < 90:
                continue
            trunk_rect = pygame.Rect(tx - 14, ty - 12, 28, 24)
            if any(trunk_rect.colliderect(p.collider.inflate(28, 28)) for p in self.props):
                continue

            t_img_name = rng.choices(tree_types, weights=[0.28, 0.42, 0.30])[0]
            spr = self.images[t_img_name]
            self.props.append(
                PropObject(
                    kind="tree",
                    x=tx - spr.get_width() // 2,
                    y=ty - spr.get_height() + 14,
                    sprite=spr,
                    collider_rect=trunk_rect,
                )
            )
            placed_trees += 1

        # ------------------------------------------------------------------
        # SINH NGẪU NHIÊN 9 DÂN LÀNG NPC ĐI DẠO TRÊN BẢN ĐỒ
        # ------------------------------------------------------------------
        villager_presets = [
            ("Abigail", (108, 72, 168), (138, 82, 188)),
            ("Robin", (218, 92, 48), (186, 68, 42)),
            ("Leah", (72, 158, 92), (196, 88, 48)),
            ("Sebastian", (48, 52, 68), (38, 40, 52)),
            ("Haley", (238, 128, 168), (245, 208, 88)),
            ("Sam", (62, 138, 212), (242, 198, 74)),
            ("Penny", (228, 178, 68), (178, 74, 46)),
            ("Mayor Lewis", (128, 92, 62), (168, 168, 174)),
            ("Alex", (68, 168, 84), (132, 78, 42)),
        ]
        rng.shuffle(villager_presets)
        for name, shirt_c, hair_c in villager_presets:
            for _ in range(60):
                nc = rng.randint(3, GRID_COLS - 4)
                nr = rng.randint(3, GRID_ROWS - 4)
                if self.grid[nr][nc] in (T_GRASS, T_DIRT, T_COBBLE, T_SAND):
                    nx, ny = nc * TILE_SIZE + 16, nr * TILE_SIZE + 16
                    if not self.is_circle_blocked(nx, ny, 14.0):
                        self.npcs.append(Character(name, nx, ny, shirt_c, hair_c))
                        break

        self._bake_terrain_surface(rng)

    def _place_building(self, img_key: str, x: int, y: int, interior_type: str, title: str):
        spr = self.images[img_key]
        w, h = spr.get_width() - 12, spr.get_height() - 12
        # Khung va chạm vật lý nằm ở nửa dưới ngôi nhà để nhân vật có thể đi phía sau mái nhà (Y-Sorting)
        collider = pygame.Rect(x + 8, y + int(h * 0.44), w - 8, int(h * 0.54))
        door_rect = pygame.Rect(x + w // 2 - 18, y + h - 8, 40, 24)
        self.props.append(
            PropObject(
                kind="building",
                x=x,
                y=y,
                sprite=spr,
                collider_rect=collider,
                door_rect=door_rect,
                interior_type=interior_type,
                title=title,
            )
        )

    def _place_prop(self, img_key: str, x: int, y: int):
        spr = self.images[img_key]
        w, h = spr.get_width(), spr.get_height()
        collider = pygame.Rect(x + 6, y + h // 2, w - 12, h // 2 - 4)
        self.props.append(PropObject(kind="prop", x=x, y=y, sprite=spr, collider_rect=collider))

    def _bake_terrain_surface(self, rng: random.Random):
        """Kết xuất sẵn lớp địa hình mặt đất, bờ nước, cầu và vách đá ra 1 Surface."""
        surf = self.terrain_surface
        for r in range(GRID_ROWS):
            for c in range(GRID_COLS):
                px, py = c * TILE_SIZE, r * TILE_SIZE
                t = self.grid[r][c]
                if t == T_GRASS:
                    g_idx = (c * 7 + r * 13) % 4
                    surf.blit(self.images[f"grass_{g_idx}"], (px, py))
                elif t == T_SAND:
                    surf.blit(self.images["sand"], (px, py))
                elif t == T_DIRT:
                    surf.blit(self.images["dirt"], (px, py))
                elif t == T_COBBLE:
                    surf.blit(self.images["cobble"], (px, py))
                elif t == T_CLIFF:
                    surf.blit(self.images["cliff"], (px, py))
                elif t == T_CROP:
                    surf.blit(self.images["crop"], (px, py))
                elif t == T_BRIDGE:
                    pygame.draw.rect(surf, (44, 118, 184), (px, py, TILE_SIZE, TILE_SIZE))
                    pygame.draw.rect(surf, (132, 78, 38), (px, py + 2, TILE_SIZE, TILE_SIZE - 4))
                    for bx in range(px + 2, px + TILE_SIZE, 8):
                        pygame.draw.rect(surf, (186, 122, 66), (bx, py + 4, 6, TILE_SIZE - 8))
                elif t == T_WATER:
                    pygame.draw.rect(surf, (52, 128, 196), (px, py, TILE_SIZE, TILE_SIZE))
                    # Viền bờ cát & bọt sóng trắng tự động khi giáp đất liền
                    if r > 0 and self.grid[r - 1][c] != T_WATER:
                        pygame.draw.rect(surf, (218, 184, 122), (px, py, TILE_SIZE, 4))
                        pygame.draw.line(surf, (235, 248, 255), (px, py + 5), (px + TILE_SIZE, py + 5), 2)
                    if c > 0 and self.grid[r][c - 1] != T_WATER:
                        pygame.draw.line(surf, (235, 248, 255), (px + 3, py), (px + 3, py + TILE_SIZE), 2)
                    if c < GRID_COLS - 1 and self.grid[r][c + 1] != T_WATER:
                        pygame.draw.line(surf, (235, 248, 255), (px + TILE_SIZE - 4, py), (px + TILE_SIZE - 4, py + TILE_SIZE), 2)

        # Vòng tròn gạch trang trí ở tâm Quảng trường Map 3 (Pelican Town)
        if self.current_map_id == 3:
            cx, cy = 10 * TILE_SIZE, 10 * TILE_SIZE
            pygame.draw.circle(surf, (188, 86, 74), (cx, cy), 38)
            pygame.draw.circle(surf, (138, 56, 48), (cx, cy), 38, 4)
            pygame.draw.circle(surf, (218, 124, 108), (cx, cy), 22, 3)

    # ------------------------------------------------------------------
    # HỆ THỐNG VÀO NHÀ (INDOOR ROOM + LÀM TỐI VÙNG NGOÀI)
    # ------------------------------------------------------------------
    def enter_house(self, building: PropObject):
        if self.in_indoor:
            return
        self.outdoor_backup = {
            "player_pos": (self.player.x, building.door_rect.bottom + 14 if building.door_rect else self.player.y + 20),
            "npcs": list(self.npcs),
        }
        self.in_indoor = True
        self.portal_cooldown = 0.7
        self.fade_alpha = 220.0

        # Khung căn phòng nằm chính giữa màn hình; toàn bộ bên ngoài sẽ tối đen
        rw, rh = 520, 420
        rx, ry = (SCREEN_W - rw) // 2, (SCREEN_H - rh) // 2
        exit_rect = pygame.Rect(rx + rw // 2 - 32, ry + rh - 22, 64, 24)

        # Tạo danh sách vật cản nội thất trong phòng
        furn_colliders = [
            pygame.Rect(rx + 24, ry + 18, 120, 48),       # Kệ sách / Tủ
            pygame.Rect(rx + rw // 2 - 48, ry + 14, 96, 42),  # Lò sưởi / Quầy chính
            pygame.Rect(rx + rw - 130, ry + 32, 102, 92),  # Giường ngủ / Kệ hàng
            pygame.Rect(rx + 110, ry + 180, 120, 74),     # Bàn trà giữa phòng
        ]

        self.indoor_info = {
            "title": building.title,
            "type": building.interior_type,
            "room_rect": pygame.Rect(rx, ry, rw, rh),
            "exit_rect": exit_rect,
            "colliders": furn_colliders,
        }

        # Đặt người chơi ở cửa phòng nhìn lên trên
        self.player.x = float(rx + rw // 2)
        self.player.y = float(ry + rh - 44)
        self.player.facing = "up"

        # Tạo 1-2 NPC chủ nhà ở bên trong phòng
        host = Character(
            "Host",
            rx + rw // 2 + 70,
            ry + 140,
            (64, 168, 212),
            (186, 74, 52),
        )
        host.emote = "♥"
        host.emote_timer = 4.0
        self.npcs = [host]

    def exit_house(self):
        if not self.in_indoor or self.outdoor_backup is None:
            return
        self.in_indoor = False
        self.portal_cooldown = 0.7
        self.fade_alpha = 200.0
        self.player.x, self.player.y = self.outdoor_backup["player_pos"]
        self.player.facing = "down"
        self.npcs = self.outdoor_backup["npcs"]
        self.outdoor_backup = None

    def toggle_nearest_house(self):
        if self.in_indoor:
            self.exit_house()
            return
        buildings = [p for p in self.props if p.door_rect is not None]
        if not buildings:
            return
        nearest = min(
            buildings,
            key=lambda b: math.hypot(
                b.door_rect.centerx - self.player.x, b.door_rect.centery - self.player.y
            ),
        )
        self.enter_house(nearest)

    # ------------------------------------------------------------------
    # KIỂM TRA VA CHẠM VẬT LÝ
    # ------------------------------------------------------------------
    def is_circle_blocked(self, cx: float, cy: float, radius: float) -> bool:
        char_rect = pygame.Rect(int(cx - radius), int(cy - radius), int(radius * 2), int(radius * 2))

        if self.in_indoor:
            room: pygame.Rect = self.indoor_info["room_rect"]
            inner_walkable = pygame.Rect(room.x + 14, room.y + 42, room.width - 28, room.height - 52)
            if not inner_walkable.contains(char_rect):
                return True
            for fc in self.indoor_info["colliders"]:
                if char_rect.colliderect(fc):
                    return True
            return False

        # Ngoài trời: Kiểm tra biên màn hình
        if cx - radius < 8 or cx + radius > SCREEN_W - 8 or cy - radius < 8 or cy + radius > SCREEN_H - 8:
            return True

        # Kiểm tra địa hình Nước (T_WATER) và Vách đá (T_CLIFF)
        for sx, sy in [
            (cx - radius * 0.7, cy - radius * 0.7),
            (cx + radius * 0.7, cy - radius * 0.7),
            (cx - radius * 0.7, cy + radius * 0.7),
            (cx + radius * 0.7, cy + radius * 0.7),
        ]:
            gc, gr = int(sx // TILE_SIZE), int(sy // TILE_SIZE)
            if 0 <= gc < GRID_COLS and 0 <= gr < GRID_ROWS:
                if self.grid[gr][gc] in (T_WATER, T_CLIFF):
                    return True

        # Kiểm tra va chạm với Công trình & Thân cây
        for p in self.props:
            if char_rect.colliderect(p.collider):
                return True

        return False

    # ------------------------------------------------------------------
    # CẬP NHẬT TRẠNG THÁI MỖI KHUNG HÌNH
    # ------------------------------------------------------------------
    def update(self, dt: float):
        self.sim_time += dt
        if self.portal_cooldown > 0.0:
            self.portal_cooldown = max(0.0, self.portal_cooldown - dt)
        if self.fade_alpha > 0.0:
            self.fade_alpha = max(0.0, self.fade_alpha - dt * 520.0)

        # 1. Điều khiển Người Chơi (WASD hoặc Phím Mũi Tên, giữ Shift chạy nhanh)
        keys = pygame.key.get_pressed()
        dx = float((keys[pygame.K_d] or keys[pygame.K_RIGHT]) - (keys[pygame.K_a] or keys[pygame.K_LEFT]))
        dy = float((keys[pygame.K_s] or keys[pygame.K_DOWN]) - (keys[pygame.K_w] or keys[pygame.K_UP]))

        if dx != 0.0 and dy != 0.0:
            inv = 1.0 / math.sqrt(2.0)
            dx *= inv
            dy *= inv

        sprint = 1.45 if (keys[pygame.K_LSHIFT] or keys[pygame.K_RSHIFT]) else 1.0
        self.player.vx = dx * self.player.speed * sprint
        self.player.vy = dy * self.player.speed * sprint
        self.player.move_and_slide(self.player.vx * dt, self.player.vy * dt, self)
        self.player._update_facing_and_anim(dt)

        # 2. Cập nhật các NPC dân làng
        for npc in self.npcs:
            npc.update_ai(dt, self)

        # 3. Kiểm tra tự động bước vào cửa nhà hoặc bước ra khỏi nhà
        if self.portal_cooldown <= 0.0:
            p_rect = pygame.Rect(int(self.player.x - 10), int(self.player.y - 10), 20, 20)
            if self.in_indoor:
                if p_rect.colliderect(self.indoor_info["exit_rect"]):
                    self.exit_house()
            else:
                for b in self.props:
                    if b.door_rect and p_rect.colliderect(b.door_rect):
                        self.enter_house(b)
                        break

    # ------------------------------------------------------------------
    # VẼ ĐỒ HỌA (RENDERING)
    # ------------------------------------------------------------------
    def render(self):
        if self.in_indoor:
            self._render_indoor_scene()
        else:
            self._render_outdoor_scene()

        if self.show_ui:
            self._render_stardew_ui()

        if self.fade_alpha > 1.0:
            fade = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
            fade.fill((8, 6, 14, int(self.fade_alpha)))
            self.screen.blit(fade, (0, 0))

        pygame.display.flip()

    def _render_outdoor_scene(self):
        self.screen.blit(self.terrain_surface, (0, 0))

        # Sóng nước lấp lánh theo thời gian thực
        wave_offset = int(math.sin(self.sim_time * 3.0) * 4)
        for r in range(0, GRID_ROWS, 2):
            for c in range(0, GRID_COLS, 2):
                if self.grid[r][c] == T_WATER:
                    wx = c * TILE_SIZE + 8 + wave_offset
                    wy = r * TILE_SIZE + 14
                    pygame.draw.line(self.screen, (135, 205, 250), (wx, wy), (wx + 10, wy), 2)

        # Y-Sorting: Sắp xếp tất cả Nhà cửa, Cây cối, NPC và Người chơi theo tọa độ Y chân
        renderables = []
        for p in self.props:
            renderables.append((p.sort_y, "prop", p))
        for npc in self.npcs:
            renderables.append((npc.sort_y, "char", npc))
        renderables.append((self.player.sort_y, "char", self.player))
        renderables.sort(key=lambda item: item[0])

        for _, r_type, obj in renderables:
            if r_type == "prop":
                obj.draw(self.screen)
            else:
                obj.draw(self.screen, self.font_small)

        # Nếu người chơi đứng gần cửa nhà, hiện gợi ý nhỏ ngay trên mái hiên
        for b in self.props:
            if b.door_rect and math.hypot(b.door_rect.centerx - self.player.x, b.door_rect.centery - self.player.y) < 52:
                tag = self.font_small.render(f"[Walk in / Press E] {b.title}", True, (255, 245, 150))
                bx = b.door_rect.centerx - tag.get_width() // 2
                by = b.door_rect.top - 24
                pygame.draw.rect(self.screen, (38, 24, 14, 210), (bx - 6, by - 3, tag.get_width() + 12, 20), border_radius=4)
                self.screen.blit(tag, (bx, by))

    def _render_indoor_scene(self):
        """
        Vẽ Không gian Trong Nhà:
        - Toàn bộ vùng ngoài căn phòng được làm tối đen hoàn toàn (Darkened Exterior Void)
        - Giữa màn hình là căn phòng sàn gỗ ấm áp, lò sưởi cháy sáng, cửa sổ đón nắng và đồ nội thất.
        """
        # 1. Làm tối đen toàn bộ vùng ngoài
        self.screen.fill((8, 6, 14))

        room: pygame.Rect = self.indoor_info["room_rect"]
        rx, ry, rw, rh = room.x, room.y, room.width, room.height

        # Quầng sáng ấm hắt nhẹ quanh căn phòng
        glow = pygame.Surface((rw + 48, rh + 48), pygame.SRCALPHA)
        pygame.draw.rect(glow, (255, 190, 95, 25), (0, 0, rw + 48, rh + 48), border_radius=18)
        self.screen.blit(glow, (rx - 24, ry - 24))

        # 2. Khung tường gỗ dày & Sàn ván gỗ thông ấm áp
        pygame.draw.rect(self.screen, (88, 52, 26), (rx - 12, ry - 12, rw + 24, rh + 24), border_radius=8)
        pygame.draw.rect(self.screen, (218, 162, 102), room, border_radius=4)
        for py in range(ry, ry + rh, 18):
            pygame.draw.line(self.screen, (188, 134, 76), (rx, py), (rx + rw, py), 2)
            for px in range(rx + (py % 36), rx + rw, 48):
                pygame.draw.line(self.screen, (172, 118, 64), (px, py), (px, min(ry + rh, py + 18)), 1)

        # 3. Tường hậu phía Bắc + Cửa sổ hắt nắng vàng xuống sàn
        pygame.draw.rect(self.screen, (238, 216, 182), (rx, ry, rw, 44))
        pygame.draw.line(self.screen, (112, 66, 32), (rx, ry + 44), (rx + rw, ry + 44), 3)
        for wx in (rx + 150, rx + rw - 190):
            pygame.draw.rect(self.screen, (255, 238, 148), (wx, ry + 8, 40, 28), border_radius=2)
            pygame.draw.rect(self.screen, (104, 58, 26), (wx, ry + 8, 40, 28), 2, border_radius=2)
            # Tia nắng ấm chiếu xuống sàn gỗ
            sun = pygame.Surface((48, 36), pygame.SRCALPHA)
            pygame.draw.polygon(sun, (255, 242, 168, 55), [(4, 0), (44, 0), (48, 36), (0, 36)])
            self.screen.blit(sun, (wx - 4, ry + 46))

        # 4. Thảm dệt trang trí giữa phòng
        pygame.draw.rect(self.screen, (186, 62, 56), (rx + rw // 2 - 110, ry + 150, 220, 130), border_radius=6)
        pygame.draw.rect(self.screen, (244, 212, 128), (rx + rw // 2 - 102, ry + 158, 204, 114), 2, border_radius=4)

        # 5. Đồ nội thất trong phòng (Kệ sách, Lò sưởi lửa bập bùng, Giường đỏ, Bàn trà)
        c_book, c_fire, c_bed, c_table = self.indoor_info["colliders"]
        # Kệ sách gỗ
        pygame.draw.rect(self.screen, (118, 68, 34), c_book, border_radius=4)
        for sy in range(c_book.y + 8, c_book.bottom - 6, 12):
            pygame.draw.rect(self.screen, (78, 42, 18), (c_book.x + 6, sy, c_book.width - 12, 8))
            for bx in range(c_book.x + 8, c_book.right - 12, 10):
                pygame.draw.rect(self.screen, (215, 78, 68) if bx % 20 == 0 else (68, 142, 198), (bx, sy + 1, 7, 7))

        # Lò sưởi gạch đỏ có ngọn lửa nhấp nhô
        pygame.draw.rect(self.screen, (142, 68, 56), c_fire, border_radius=4)
        pygame.draw.rect(self.screen, (38, 26, 24), (c_fire.x + 16, c_fire.y + 10, c_fire.width - 32, c_fire.height - 10), border_radius=3)
        flicker = int(math.sin(self.sim_time * 14.0) * 3)
        pygame.draw.circle(self.screen, (255, 138, 38), (c_fire.centerx, c_fire.bottom - 10), 11 + flicker)
        pygame.draw.circle(self.screen, (255, 228, 78), (c_fire.centerx, c_fire.bottom - 8), 6)

        # Giường ngủ chăn đỏ kiểu Farmhouse
        pygame.draw.rect(self.screen, (118, 68, 34), c_bed, border_radius=5)
        pygame.draw.rect(self.screen, (248, 242, 232), (c_bed.x + 6, c_bed.y + 8, c_bed.width - 12, 24), border_radius=3)
        pygame.draw.rect(self.screen, (204, 68, 62), (c_bed.x + 6, c_bed.y + 34, c_bed.width - 12, c_bed.height - 40), border_radius=4)

        # Bàn gỗ & Ấm trà
        pygame.draw.rect(self.screen, (132, 78, 38), c_table, border_radius=5)
        pygame.draw.rect(self.screen, (178, 114, 58), c_table.inflate(-8, -8), border_radius=4)
        pygame.draw.circle(self.screen, (245, 240, 225), c_table.center, 8)

        # 6. Thảm Đỏ Lối Ra (Exit Mat) ở mép dưới căn phòng
        ex: pygame.Rect = self.indoor_info["exit_rect"]
        pygame.draw.rect(self.screen, (212, 64, 58), ex, border_radius=3)
        pygame.draw.rect(self.screen, (250, 218, 110), ex, 2, border_radius=3)
        ex_lbl = self.font_small.render("EXIT TO TOWN [Walk Here or Press E]", True, (255, 235, 150))
        self.screen.blit(ex_lbl, (ex.centerx - ex_lbl.get_width() // 2, room.bottom + 16))

        # 7. Vẽ NPC Chủ nhà & Người chơi theo thứ tự Y-Sorting
        chars = sorted(self.npcs + [self.player], key=lambda ch: ch.sort_y)
        for ch in chars:
            ch.draw(self.screen, self.font_small)

        # Tiêu đề ngôi nhà phía trên vùng tối
        title_s = self.font_title.render(f"🏠 INSIDE: {self.indoor_info['title'].upper()}", True, (255, 228, 128))
        self.screen.blit(title_s, (SCREEN_W // 2 - title_s.get_width() // 2, ry - 42))

    # ------------------------------------------------------------------
    # GIAO DIỆN UI GỌN ĐẸP CHUẨN STARDEW VALLEY (GÓC PHẢI TRÊN + ĐÁY)
    # ------------------------------------------------------------------
    def _render_stardew_ui(self):
        # 1. Hộp gỗ thông tin nhỏ gọn ở Góc Trên Bên Phải (Giống Ảnh 2)
        box_w, box_h = 268, 86
        bx, by = SCREEN_W - box_w - 14, 14
        panel = pygame.Surface((box_w, box_h), pygame.SRCALPHA)
        panel.fill((68, 42, 22, 235))
        pygame.draw.rect(panel, (224, 168, 88), (0, 0, box_w, box_h), 3, border_radius=8)
        pygame.draw.rect(panel, (132, 82, 38), (3, 3, box_w - 6, box_h - 6), 2, border_radius=6)
        self.screen.blit(panel, (bx, by))

        # Tính giờ trong game
        minutes = int((self.sim_time * 12) % 720)
        hour = 6 + (minutes // 60)
        min_step = (minutes % 60 // 10) * 10
        am_pm = "AM" if hour < 12 else "PM"
        disp_h = hour if hour <= 12 else hour - 12

        loc_text = f"Inside: {self.indoor_info['title']}" if self.in_indoor else self.MAP_TITLES[self.current_map_id]
        t1 = self.font_ui.render(f"Spring 14  •  {disp_h:02d}:{min_step:02d} {am_pm}", True, (255, 248, 220))
        t2 = self.font_small.render(loc_text[:28], True, (152, 238, 138))
        t3 = self.font_ui.render("G 349,988", True, (255, 215, 64))

        self.screen.blit(t1, (bx + 14, by + 10))
        self.screen.blit(t2, (bx + 14, by + 34))
        self.screen.blit(t3, (bx + 14, by + 56))

        # 2. Thanh nút bấm nhỏ gọn ở sát đáy màn hình (Click chuột hoặc bấm phím tắt)
        mouse_pos = pygame.mouse.get_pos()
        for rect, label, act in self.ui_buttons:
            is_active = (act == f"map{self.current_map_id}" and not self.in_indoor)
            is_hover = rect.collidepoint(mouse_pos)
            bg_col = (158, 96, 44, 240) if (is_active or is_hover) else (58, 36, 18, 215)
            border_col = (255, 225, 110) if is_active else (208, 152, 78)

            btn_surf = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
            btn_surf.fill(bg_col)
            pygame.draw.rect(btn_surf, border_col, (0, 0, rect.width, rect.height), 2, border_radius=6)
            self.screen.blit(btn_surf, rect.topleft)

            lbl_s = self.font_small.render(label, True, (255, 248, 225))
            self.screen.blit(
                lbl_s,
                (rect.centerx - lbl_s.get_width() // 2, rect.centery - lbl_s.get_height() // 2),
            )

    def handle_ui_click(self, pos: tuple[int, int]):
        for rect, _, act in self.ui_buttons:
            if rect.collidepoint(pos):
                if act.startswith("map"):
                    self.generate_map(int(act[-1]), new_seed=False)
                elif act == "rand":
                    self.generate_map(self.current_map_id, new_seed=True)
                elif act == "door":
                    self.toggle_nearest_house()
                elif act == "hud":
                    self.show_ui = not self.show_ui

    def run(self):
        running = True
        while running:
            dt = min(0.05, self.clock.tick(60) / 1000.0)
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    self.handle_ui_click(event.pos)
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        running = False
                    elif event.key in (pygame.K_1, pygame.K_2, pygame.K_3, pygame.K_4):
                        self.generate_map(event.key - pygame.K_0, new_seed=False)
                    elif event.key == pygame.K_t:
                        nxt = (self.current_map_id % 4) + 1
                        self.generate_map(nxt, new_seed=False)
                    elif event.key == pygame.K_r:
                        self.generate_map(self.current_map_id, new_seed=True)
                    elif event.key == pygame.K_e:
                        self.toggle_nearest_house()
                    elif event.key == pygame.K_h:
                        self.show_ui = not self.show_ui

            self.update(dt)
            self.render()

        pygame.quit()
        sys.exit(0)


if __name__ == "__main__":
    game = StardewRPGGame()
    game.run()