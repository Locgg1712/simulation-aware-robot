# game/maps.py
"""
Xây dựng Hệ thống 5 Bản đồ Liên thông phong cách Stardew Valley (sử dụng toàn bộ tài nguyên ảnh trong `sprites/sprites/`):
- Map 1: Quảng Trường & Bờ Sông Thị Trấn (Pelican Town Square & River — cầu đá, cầu gỗ, giếng cổ, vườn hoa, JojaMart, Tạp hóa Pierre, Saloon).
- Map 2: Đại Nông Trại & Ruộng Cây Trồng (Grand Farmstead — 6 thửa ruộng lớn có rào gỗ, vòi tưới sprinkler, bù nhìn scarecrow, nhà kính, cối xay gió, 2 tháp silo, vườn cây ăn quả, chuồng bò/cừu/heo/gà, ao cá và AGV).
- Map 3: Đảo Rừng Xanh & Bến Hồ Câu Cá (Forest Island & Lakeside Pier — đảo nối bằng cầu gỗ & cầu đá, ruộng ven hồ, rừng thông/sồi/anh đào, gốc cây, khúc gỗ, chòi ngư cụ, 3 điểm thả câu).
- Map 4: Khu Dân Cư & Vườn Hoa Gia Đình (Residential Village — 4 ngôi nhà có sân vườn riêng, hàng rào trắng, mèo con, hồ cá, đèn đường, ghế đá).
- Map 5: Không Gian Nội Thất Trong Nhà (Indoor House — mỗi ngôi nhà có một thiết kế nội thất, tông màu sàn/tường và bài trí đồ đạc riêng biệt!).
"""

from __future__ import annotations

import math
import pygame

from .constants import (
    BLOCKING_TILES,
    GRID_COLS,
    GRID_ROWS,
    MAP_TITLES,
    SCREEN_H,
    SCREEN_W,
    T_BRIDGE,
    T_CLIFF,
    T_COBBLE,
    T_CROP,
    T_DIRT,
    T_FOREST,
    T_GRASS,
    T_SAND,
    T_TALL_GRASS,
    T_WATER,
    T_WOOD_DOCK,
    TILE_SIZE,
)
from .entities import (
    FarmAnimal,
    FarmCartAGV,
    FishingSpot,
    HarvestSpot,
    MapPortal,
    PropObject,
    VillagerNPC,
)
from .terrain import bake_terrain_surface
from .world_builder import WorldBuilder

T = TILE_SIZE


# ==============================================================================
# CẤU HÌNH NỘI THẤT RIÊNG BIỆT CHO TỪNG NGÔI NHÀ (MAP 5)
# ==============================================================================
INTERIOR_THEMES: dict[str, dict] = {
    "house_gus": {
        "subtitle": "Gian Bếp Ấm Cúng & Phòng Ăn Của Đầu Bếp Gus",
        "room_size": (672, 464),
        "floor_tint": (235, 195, 155),
        "wall_tint": (255, 228, 190),
        "border_col": (165, 88, 46),
        "rug_tint": (245, 160, 140),
        "furniture": [
            ("furn_fireplace", 0.24, 0.12, 92, 86),
            ("furn_fireplace", 0.50, 0.12, 92, 86),
            ("furn_bookshelf", 0.78, 0.13, 76, 86),
            ("furn_counter", 0.22, 0.36, 118, 72),
            ("furn_counter", 0.42, 0.36, 118, 72),
            ("barrel", 0.10, 0.36, 44, 62),
            ("crate", 0.10, 0.54, 48, 50),
            ("barrel", 0.10, 0.70, 44, 62),
            ("furn_table", 0.26, 0.68, 96, 76),
            ("bench", 0.26, 0.82, 76, 46),
            ("furn_table", 0.74, 0.62, 96, 76),
            ("bench", 0.74, 0.76, 76, 46),
            ("furn_bed", 0.86, 0.34, 78, 98),
            ("furn_plant", 0.08, 0.86, 46, 62),
            ("furn_plant", 0.92, 0.86, 46, 62),
            ("cat", 0.64, 0.36, 40, 48),
        ],
        "display_items": [("bread", 0.22, 0.31), ("tomato", 0.42, 0.31), ("pumpkin", 0.26, 0.63)],
    },
    "house_robin": {
        "subtitle": "Xưởng Mộc Sáng Tạo & Tổ Ấm Của Kiến Trúc Sư Robin",
        "room_size": (672, 464),
        "floor_tint": (245, 215, 165),
        "wall_tint": (235, 245, 215),
        "border_col": (128, 96, 52),
        "rug_tint": (175, 225, 165),
        "furniture": [
            ("furn_bookshelf", 0.16, 0.13, 82, 86),
            ("furn_bookshelf", 0.32, 0.13, 82, 86),
            ("furn_fireplace", 0.54, 0.12, 90, 86),
            ("furn_bed", 0.84, 0.28, 82, 102),
            ("furn_counter", 0.20, 0.44, 122, 74),
            ("log", 0.16, 0.64, 92, 52),
            ("stump", 0.32, 0.66, 64, 48),
            ("crate", 0.12, 0.78, 52, 52),
            ("barrel", 0.24, 0.78, 44, 62),
            ("furn_table", 0.76, 0.66, 100, 78),
            ("bench", 0.76, 0.81, 80, 48),
            ("furn_plant", 0.08, 0.28, 48, 64),
            ("furn_plant", 0.92, 0.84, 48, 64),
        ],
        "display_items": [("parcel", 0.20, 0.39), ("carrot", 0.76, 0.61)],
    },
    "house_willy": {
        "subtitle": "Căn Nhà Gỗ Ven Hồ & Kho Ngư Cụ Của Ông Lão Willy",
        "room_size": (640, 448),
        "floor_tint": (185, 205, 220),
        "wall_tint": (205, 232, 245),
        "border_col": (68, 108, 138),
        "rug_tint": (155, 210, 235),
        "furniture": [
            ("furn_fireplace", 0.50, 0.12, 88, 84),
            ("furn_bookshelf", 0.20, 0.13, 78, 84),
            ("barrel", 0.12, 0.38, 46, 64),
            ("barrel", 0.22, 0.38, 46, 64),
            ("crate", 0.14, 0.56, 52, 52),
            ("crate", 0.25, 0.56, 52, 52),
            ("furn_counter", 0.24, 0.74, 118, 70),
            ("furn_bed", 0.84, 0.30, 80, 100),
            ("furn_table", 0.76, 0.68, 96, 74),
            ("bench", 0.76, 0.82, 76, 46),
            ("cat", 0.62, 0.56, 40, 48),
            ("furn_plant", 0.90, 0.86, 46, 62),
        ],
        "display_items": [("fish", 0.24, 0.69), ("fish", 0.76, 0.63)],
    },
    "house_lewis": {
        "subtitle": "Đại Sảnh Dinh Thự Thị Trưởng Lewis",
        "room_size": (720, 480),
        "floor_tint": (245, 205, 175),
        "wall_tint": (255, 242, 195),
        "border_col": (195, 145, 58),
        "rug_tint": (245, 135, 135),
        "furniture": [
            ("furn_bookshelf", 0.14, 0.13, 82, 88),
            ("furn_bookshelf", 0.28, 0.13, 82, 88),
            ("furn_fireplace", 0.50, 0.12, 98, 90),
            ("furn_bookshelf", 0.72, 0.13, 82, 88),
            ("furn_bed", 0.86, 0.28, 86, 106),
            ("furn_table", 0.24, 0.58, 104, 80),
            ("bench", 0.24, 0.73, 82, 48),
            ("furn_table", 0.76, 0.62, 104, 80),
            ("bench", 0.76, 0.77, 82, 48),
            ("furn_plant", 0.08, 0.34, 50, 68),
            ("furn_plant", 0.92, 0.56, 50, 68),
            ("furn_plant", 0.08, 0.84, 50, 68),
            ("furn_plant", 0.92, 0.84, 50, 68),
            ("cat", 0.40, 0.54, 42, 50),
        ],
        "display_items": [("peach", 0.24, 0.53), ("strawberry", 0.76, 0.57)],
    },
    "pierre_shop": {
        "subtitle": "Siêu Thị Nông Sản & Tạp Hóa Pierre",
        "room_size": (680, 464),
        "floor_tint": (240, 225, 185),
        "wall_tint": (235, 250, 220),
        "border_col": (96, 148, 68),
        "rug_tint": (185, 235, 175),
        "furniture": [
            ("furn_bookshelf", 0.16, 0.13, 84, 86),
            ("furn_bookshelf", 0.34, 0.13, 84, 86),
            ("furn_bookshelf", 0.66, 0.13, 84, 86),
            ("furn_bookshelf", 0.84, 0.13, 84, 86),
            ("furn_counter", 0.24, 0.42, 122, 74),
            ("furn_counter", 0.76, 0.42, 122, 74),
            ("crate", 0.14, 0.68, 54, 54),
            ("crate", 0.24, 0.68, 54, 54),
            ("barrel", 0.14, 0.82, 46, 62),
            ("crate", 0.76, 0.68, 54, 54),
            ("barrel", 0.86, 0.68, 46, 62),
            ("furn_plant", 0.08, 0.34, 48, 64),
            ("furn_plant", 0.92, 0.34, 48, 64),
        ],
        "display_items": [
            ("strawberry", 0.20, 0.37),
            ("pumpkin", 0.28, 0.37),
            ("corn", 0.72, 0.37),
            ("cabbage", 0.80, 0.37),
            ("carrot", 0.14, 0.63),
            ("tomato", 0.76, 0.63),
        ],
    },
    "stardrop_saloon": {
        "subtitle": "Quán Nước & Nhà Hàng Stardrop Saloon",
        "room_size": (680, 464),
        "floor_tint": (215, 168, 128),
        "wall_tint": (245, 210, 175),
        "border_col": (158, 76, 42),
        "rug_tint": (235, 155, 125),
        "furniture": [
            ("furn_fireplace", 0.50, 0.12, 94, 88),
            ("barrel", 0.14, 0.18, 46, 64),
            ("barrel", 0.23, 0.18, 46, 64),
            ("barrel", 0.77, 0.18, 46, 64),
            ("barrel", 0.86, 0.18, 46, 64),
            ("furn_counter", 0.24, 0.38, 124, 74),
            ("furn_counter", 0.76, 0.38, 124, 74),
            ("furn_table", 0.22, 0.66, 96, 76),
            ("bench", 0.22, 0.80, 78, 46),
            ("furn_table", 0.78, 0.66, 96, 76),
            ("bench", 0.78, 0.80, 78, 46),
            ("furn_plant", 0.08, 0.86, 46, 62),
            ("furn_plant", 0.92, 0.86, 46, 62),
        ],
        "display_items": [("orange", 0.24, 0.33), ("bread", 0.22, 0.61), ("apple", 0.78, 0.61)],
    },
    "joja_depot": {
        "subtitle": "Trung Tâm Kho Vận & Phân Phối JojaMart",
        "room_size": (680, 464),
        "floor_tint": (185, 205, 235),
        "wall_tint": (210, 228, 250),
        "border_col": (62, 118, 195),
        "rug_tint": (145, 190, 245),
        "furniture": [
            ("furn_bookshelf", 0.16, 0.13, 84, 86),
            ("furn_bookshelf", 0.34, 0.13, 84, 86),
            ("furn_bookshelf", 0.66, 0.13, 84, 86),
            ("furn_bookshelf", 0.84, 0.13, 84, 86),
            ("crate", 0.16, 0.42, 54, 54),
            ("crate", 0.26, 0.42, 54, 54),
            ("crate", 0.74, 0.42, 54, 54),
            ("crate", 0.84, 0.42, 54, 54),
            ("furn_counter", 0.24, 0.68, 120, 72),
            ("furn_counter", 0.76, 0.68, 120, 72),
            ("barrel", 0.12, 0.82, 46, 62),
            ("barrel", 0.88, 0.82, 46, 62),
        ],
        "display_items": [("parcel", 0.24, 0.63), ("parcel", 0.76, 0.63), ("wheat", 0.16, 0.37)],
    },
    "clinic_house": {
        "subtitle": "Phòng Khám Y Tế & Chăm Sóc Sức Khỏe Thị Trấn",
        "room_size": (640, 448),
        "floor_tint": (215, 245, 235),
        "wall_tint": (235, 255, 248),
        "border_col": (72, 168, 148),
        "rug_tint": (175, 242, 225),
        "furniture": [
            ("furn_bookshelf", 0.18, 0.13, 80, 84),
            ("furn_bookshelf", 0.34, 0.13, 80, 84),
            ("furn_bed", 0.76, 0.26, 80, 98),
            ("furn_bed", 0.88, 0.26, 80, 98),
            ("furn_counter", 0.24, 0.48, 120, 72),
            ("furn_table", 0.78, 0.68, 96, 74),
            ("bench", 0.78, 0.82, 76, 46),
            ("furn_plant", 0.10, 0.32, 48, 64),
            ("furn_plant", 0.10, 0.84, 48, 64),
            ("furn_plant", 0.90, 0.84, 48, 64),
        ],
        "display_items": [("apple", 0.24, 0.43), ("strawberry", 0.78, 0.63)],
    },
    "farm_house": {
        "subtitle": "Ngôi Nhà Gỗ Nông Trại Truyền Thống",
        "room_size": (656, 456),
        "floor_tint": (238, 202, 158),
        "wall_tint": (250, 232, 198),
        "border_col": (142, 92, 48),
        "rug_tint": (235, 175, 135),
        "furniture": [
            ("furn_fireplace", 0.50, 0.12, 92, 86),
            ("furn_bookshelf", 0.20, 0.13, 80, 84),
            ("furn_bed", 0.84, 0.28, 82, 100),
            ("furn_counter", 0.22, 0.44, 118, 72),
            ("furn_table", 0.76, 0.66, 98, 76),
            ("bench", 0.76, 0.80, 78, 46),
            ("barrel", 0.12, 0.68, 44, 62),
            ("crate", 0.22, 0.68, 50, 50),
            ("cat", 0.38, 0.56, 40, 48),
            ("furn_plant", 0.10, 0.86, 46, 62),
            ("furn_plant", 0.90, 0.86, 46, 62),
        ],
        "display_items": [("corn", 0.22, 0.39), ("pumpkin", 0.76, 0.61)],
    },
    "fisher_shed": {
        "subtitle": "Chòi Ngư Cụ & Trạm Nghỉ Chân Ven Hồ",
        "room_size": (624, 440),
        "floor_tint": (195, 212, 222),
        "wall_tint": (218, 238, 245),
        "border_col": (76, 122, 148),
        "rug_tint": (165, 218, 235),
        "furniture": [
            ("furn_fireplace", 0.50, 0.12, 86, 82),
            ("barrel", 0.16, 0.28, 46, 62),
            ("crate", 0.26, 0.28, 50, 50),
            ("furn_counter", 0.24, 0.56, 116, 70),
            ("furn_bed", 0.82, 0.32, 78, 96),
            ("furn_table", 0.76, 0.68, 94, 72),
            ("bench", 0.76, 0.82, 74, 44),
            ("furn_plant", 0.10, 0.84, 46, 60),
        ],
        "display_items": [("fish", 0.24, 0.51), ("fish", 0.76, 0.63)],
    },
    "robot_house": {
        "subtitle": "Xưởng Cải Tiến Công Nghệ & Trạm Sạc Pin Của Robot",
        "room_size": (704, 440),
        "floor_tint": (198, 206, 218),
        "wall_tint": (215, 225, 238),
        "border_col": (235, 132, 42),
        "rug_tint": (110, 205, 235),
        "furniture": [
            # Hệ thống tường kỹ thuật phía Bắc
            ("rh_wall_vent", 0.10, 0.12, 68, 86),
            ("rh_wall_screen", 0.22, 0.12, 62, 86),
            ("rh_whiteboard", 0.40, 0.12, 138, 72),
            ("rh_wall_doors", 0.61, 0.12, 126, 86),
            ("rh_server_1", 0.77, 0.14, 44, 86),
            ("rh_server_2", 0.84, 0.14, 44, 86),
            ("rh_cooling_unit", 0.93, 0.14, 68, 66),
            # Khu vực Trạm Cánh Tay Cải Tiến Robot (Bên Trái)
            ("rh_shelf_parts", 0.09, 0.36, 70, 116),
            ("rh_shelf_wide", 0.09, 0.64, 90, 100),
            ("rh_tool_cabinet", 0.19, 0.32, 52, 74),
            ("rh_upgrade_station", 0.27, 0.54, 118, 148),
            ("rh_workbench_green", 0.25, 0.82, 84, 86),
            ("rh_crate_open", 0.10, 0.86, 76, 44),
            # Khu vực Bàn Thiết Kế & Máy Chủ Trung Tâm
            ("rh_computer_desk", 0.50, 0.30, 96, 88),
            ("rh_round_table", 0.48, 0.68, 96, 78),
            ("rh_stool_1", 0.40, 0.68, 30, 32),
            ("rh_stool_2", 0.56, 0.68, 30, 34),
            # Khu vực Đế Sạc Pin & Ngủ Tia Chớp (Bên Phải)
            ("rh_solder_station", 0.74, 0.30, 82, 62),
            ("rh_diag_table", 0.90, 0.32, 90, 54),
            ("rh_charging_dock", 0.77, 0.56, 108, 102),
            ("rh_battery_box", 0.91, 0.52, 38, 42),
            ("rh_extinguisher", 0.92, 0.66, 32, 62),
            ("rh_plant_tall", 0.91, 0.82, 52, 76),
            ("rh_barrel_blue1", 0.66, 0.84, 38, 56),
        ],
        "display_items": [],
    },
}


def load_outdoor_map(
    game,
    map_id: int,
    spawn_pos: tuple[float, float] | None = None,
    spawn_theta: float | None = None,
):
    """Tải 1 trong 4 bản đồ ngoài trời (Map 1..4) và khởi tạo toàn bộ công trình, ruộng cây, NPC."""
    game.in_interior = False
    game.current_interior = None
    game.interior_npcs.clear()
    game.current_map_id = map_id

    game.props.clear()
    game.npcs.clear()
    game.portals.clear()
    game.harvest_spots.clear()
    game.deco_fields = []
    game.fishing_spots.clear()
    game.agvs.clear()
    game.animals.clear()
    game.extra_blockers = []
    game.decals = []

    game.robot.harvest_target = None
    game.robot.fishing_state = "idle"
    game.robot.fishing_spot = None

    wb = WorldBuilder(game, seed=map_id * 1337 + 42)

    if map_id == 1:
        _build_map1_town_square(game, wb, spawn_pos, spawn_theta)
    elif map_id == 2:
        _build_map2_orchard_farm(game, wb, spawn_pos, spawn_theta)
    elif map_id == 3:
        _build_map3_lakeside_fishing(game, wb, spawn_pos, spawn_theta)
    elif map_id == 4:
        _build_map4_residential_village(game, wb, spawn_pos, spawn_theta)

    game.terrain_surface = bake_terrain_surface(game)
    game.set_banner(f"Đã tới {MAP_TITLES[map_id]}", (235, 248, 255))


# ==============================================================================
# MAP 1: QUẢNG TRƯỜNG & BỜ SÔNG THỊ TRẤN (Lấy cảm hứng từ Ảnh 3)
# ==============================================================================
def _build_map1_town_square(game, wb: WorldBuilder, spawn_pos, spawn_theta):
    # 1. Rừng viền & Vách đá phía Bắc
    wb.forest_border(depth=1, gaps={"N": (14, 19), "S": (14, 19), "W": (10, 14), "E": (10, 14)})
    wb.cliff_band(1, 13, 1, height=2)
    wb.cliff_band(20, 24, 1, height=2)

    # 2. Dòng sông uốn lượn bên phải (Cột 25..28) + Bờ cát vàng hai bên
    for r in range(0, GRID_ROWS):
        c_mid = 26 + int(round(math.sin(r * 0.35)))
        wb.fill(c_mid - 2, r, c_mid + 2, r, T_SAND)
        wb.fill(c_mid - 1, r, c_mid + 1, r, T_WATER)

    # 3. Quảng trường lát đá trung tâm + Đường trục Đông-Tây & Bắc-Nam
    wb.fill(15, 0, 18, 23, T_COBBLE)
    wb.fill(0, 11, 35, 13, T_COBBLE)
    wb.fill(8, 8, 21, 16, T_COBBLE)
    wb.ellipse(14.5, 12.0, 4.2, 3.2, T_DIRT)
    wb.ellipse(14.5, 12.0, 2.8, 2.0, T_COBBLE)

    # 2 Cây cầu bắc qua sông: Cầu đá trung tâm (Hàng 11..13) & Cầu gỗ phía Nam (Hàng 19..20)
    wb.fill(24, 11, 29, 13, T_BRIDGE)
    wb.decal("bridge_stone", 24 * T + 4, 11 * T - 6, 5 * T - 8, 3 * T + 12)
    wb.fill(24, 19, 29, 20, T_BRIDGE)
    wb.decal("bridge_wood", 24 * T + 4, 19 * T - 4, 5 * T - 8, 2 * T + 10)
    wb.fill(15, 19, 32, 20, T_DIRT)

    # 4. Cổng chuyển tiếp sang Map 2 (Bắc), Map 3 (Đông), Map 4 (Tây)
    game.portals.extend([
        MapPortal(
            rect=pygame.Rect(15 * T, 0, 4 * T, 24),
            target_map_id=2,
            spawn_x=17.5 * T,
            spawn_y=SCREEN_H - 68.0,
            spawn_theta=-math.pi / 2.0,
            label="▲ Lên Map 2: Đại Nông Trại",
            arrow_dir="up",
        ),
        MapPortal(
            rect=pygame.Rect(SCREEN_W - 24, 11 * T, 24, 3 * T),
            target_map_id=3,
            spawn_x=72.0,
            spawn_y=12.5 * T,
            spawn_theta=0.0,
            label="► Sang Map 3: Đảo & Bến Hồ",
            arrow_dir="right",
        ),
        MapPortal(
            rect=pygame.Rect(0, 11 * T, 24, 3 * T),
            target_map_id=4,
            spawn_x=SCREEN_W - 76.0,
            spawn_y=12.5 * T,
            spawn_theta=math.pi,
            label="◄ Sang Map 4: Khu Dân Cư",
            arrow_dir="left",
        ),
    ])

    # 5. Các Tòa Nhà Thị Trấn (đều có cửa bấm [E] vào Map 5 Nội Thất riêng!)
    wb.building(
        "house_town", 5.5 * T, 7.6 * T, 0.92,
        house_id="clinic_house", interior_type="clinic",
        title="Phòng Khám Y Tế", owner_name="Bác sĩ Harvey",
        owner_folder="npc_13_scholar", owner_role="Bác sĩ Thị trấn",
    )
    wb.building(
        "shop_pierre", 11.2 * T, 7.6 * T, 0.94,
        house_id="pierre_shop", interior_type="shop",
        title="Tạp Hóa Pierre", owner_name="Chủ tiệm Pierre",
        owner_folder="npc_green", owner_role="Chủ tiệm Tạp Hóa",
    )
    wb.building(
        "saloon", 21.5 * T, 8.2 * T, 0.92,
        house_id="stardrop_saloon", interior_type="saloon",
        title="Quán Nước Stardrop", owner_name="Cô Emily",
        owner_folder="npc_08_maid", owner_role="Quản lý Quán Nước",
    )
    wb.building(
        "jojamart", 31.8 * T, 7.8 * T, 0.92,
        house_id="joja_depot", interior_type="depot",
        title="Kho Vận JojaMart", owner_name="Anh Shane",
        owner_folder="npc_05_blue_boy", owner_role="Điều phối Kho vận",
    )

    # 6. Ruộng Rau Cộng Đồng & Vườn Hoa trong Thị Trấn
    wb.field(2, 15, 6, 18, "strawberry", spot_id="town_straw", title="Vườn Dâu Thị Trấn",
             item_key="strawberry", fence=True, sprinkler=True)
    wb.field(30, 15, 33, 17, "cabbage", spot_id="town_cab", title="Vườn Bắp Cải Bờ Đông",
             item_key="cabbage", fence=True, scarecrow=True)
    wb.flower_bed(8, 6, 10, 7)
    wb.flower_bed(19, 6, 20, 7)
    wb.flower_bed(9, 17, 13, 18)

    # 7. Giếng cổ có mái, ghế dài, cột đèn, hòm thư, biển chỉ dẫn, thùng gỗ
    wb.prop("well_roof", 14.5 * T, 12.2 * T, h=92, collider_w=0.75, collider_h=24, kind="well")
    wb.prop("bench", 9.8 * T, 8.9 * T, h=42)
    wb.prop("bench", 18.2 * T, 8.9 * T, h=42)
    wb.prop("bench", 12.2 * T, 15.6 * T, h=42)
    wb.lamp(8.5 * T, 10.6 * T)
    wb.lamp(20.5 * T, 10.6 * T)
    wb.lamp(14.5 * T, 16.5 * T)
    wb.prop("signpost", 16.6 * T, 9.2 * T, h=52)
    wb.prop("mailbox", 13.0 * T, 7.8 * T, h=48)
    wb.prop("barrel", 23.2 * T, 8.2 * T, h=44)
    wb.prop("crate", 23.9 * T, 8.4 * T, h=38)
    wb.prop("cat", 12.8 * T, 14.8 * T, h=36, solid=False)

    # Cây anh đào, cây sồi, cây thông trang trí
    for cx, cy, tkind in [
        (3.0 * T, 10.2 * T, "tree_cherry"),
        (7.2 * T, 14.8 * T, "tree_oak"),
        (22.5 * T, 16.8 * T, "tree_cherry"),
        (33.5 * T, 10.2 * T, "tree_cherry"),
        (33.5 * T, 21.8 * T, "tree_pine"),
        (3.2 * T, 22.0 * T, "tree_oak"),
    ]:
        wb.tree(tkind, cx, cy, h=116)

    # 8. Các NPC:
    # - Nhóm NPC 1 hướng (`npc_red`, `npc_old`, `npc_green`): đứng yên giao nhiệm vụ (`is_stationary=True`)
    # - Nhóm NPC nhiều hướng (`npc_09_young_girl`, `npc_08_maid`, `npc_01_orange_boy`): di chuyển tuần tra 4 hướng
    game.npcs.extend([
        VillagerNPC(
            name="Bà Evelyn",
            role="Người giao Nhiệm vụ Hái Quả",
            x=11.5 * T,
            y=9.6 * T,
            folder="npc_red",
            theta=math.pi / 2.0,
            is_stationary=True,
        ),
        VillagerNPC(
            name="Ông George",
            role="Người giao Nhiệm vụ Câu Cá",
            x=18.2 * T,
            y=9.6 * T,
            folder="npc_old",
            theta=math.pi / 2.0,
            is_stationary=True,
        ),
        VillagerNPC(
            name="Chủ tiệm Pierre",
            role="Người giao Nhiệm vụ Chuyển Phát",
            x=9.5 * T,
            y=14.4 * T,
            folder="npc_green",
            theta=math.pi / 2.0,
            is_stationary=True,
        ),
        VillagerNPC(
            name="Bé Jas",
            role="Học sinh đi dạo",
            x=7.2 * T,
            y=12.0 * T,
            folder="npc_09_young_girl",
            patrol_points=[
                (4.5 * T, 11.8 * T),
                (12.2 * T, 11.8 * T),
                (12.2 * T, 13.4 * T),
                (4.5 * T, 13.4 * T),
            ],
        ),
        VillagerNPC(
            name="Cô Emily",
            role="Quản lý Quán Nước tuần phố",
            x=19.2 * T,
            y=11.8 * T,
            folder="npc_08_maid",
            patrol_points=[
                (16.4 * T, 11.6 * T),
                (21.2 * T, 11.6 * T),
                (21.2 * T, 15.2 * T),
                (16.4 * T, 15.2 * T),
            ],
        ),
        VillagerNPC(
            name="Anh Sam",
            role="Nhạc công qua cầu",
            x=25.0 * T,
            y=12.0 * T,
            folder="npc_01_orange_boy",
            patrol_points=[
                (22.0 * T, 11.8 * T),
                (31.5 * T, 11.8 * T),
                (31.5 * T, 13.2 * T),
                (22.0 * T, 13.2 * T),
            ],
        ),
    ])

    if spawn_pos is not None:
        game.robot.x, game.robot.y = spawn_pos
        game.robot.theta = spawn_theta if spawn_theta is not None else -math.pi / 2.0
    else:
        game.robot.x, game.robot.y = 14.5 * T, 14.2 * T
        game.robot.theta = -math.pi / 2.0


# ==============================================================================
# MAP 2: ĐẠI NÔNG TRẠI & RUỘNG CÂY TRỒNG (Lấy cảm hứng từ Ảnh 2 & Ảnh 4)
# ==============================================================================
def _build_map2_orchard_farm(game, wb: WorldBuilder, spawn_pos, spawn_theta):
    # 1. Vách đá bậc thang phía Bắc + Kênh nước tưới tiêu bên trái
    wb.cliff_band(0, 35, 0, height=2)
    wb.fill(0, 2, 1, 23, T_WATER)
    wb.fill(2, 2, 2, 23, T_SAND)

    # 2. Hệ thống đường lát đá & đường đất nông trại (giống Ảnh 2)
    wb.fill(3, 9, 34, 10, T_COBBLE)
    wb.fill(16, 4, 18, 23, T_COBBLE)
    wb.fill(14, 11, 16, 15, T_COBBLE)  # Sân đá Quầy Hạt Giống Cô Caroline
    wb.fill(4, 16, 33, 17, T_DIRT)

    # Cổng phía Nam về Map 1
    game.portals.append(
        MapPortal(
            rect=pygame.Rect(15 * T, SCREEN_H - 26, 5 * T, 26),
            target_map_id=1,
            spawn_x=16.5 * T,
            spawn_y=64.0,
            spawn_theta=math.pi / 2.0,
            label="▼ Về Map 1: Quảng Trường Thị Trấn",
            arrow_dir="down",
        )
    )

    # 3. Khu Công Trình Nông Trại Phía Bắc (2 Tháp Silo, Nhà Kính, Cối Xay Gió, Nhà Nông Trại)
    wb.building("silo", 3.6 * T, 7.6 * T, 0.72, door=False)
    wb.building("silo", 5.2 * T, 7.6 * T, 0.72, door=False)
    wb.building("greenhouse", 8.4 * T, 7.8 * T, 0.85, door=False)
    wb.building("windmill", 14.2 * T, 7.8 * T, 0.80, door=False)
    wb.building(
        "house_shed", 20.5 * T, 7.8 * T, 0.92,
        house_id="farm_house", interior_type="farmhouse",
        title="Kho Nông Sản", owner_name="Nông dân Marnie",
        owner_folder="npc_06_farmer_girl", owner_role="Quản lý Nông trại",
    )
    wb.building(
        "house_farm", 26.2 * T, 7.8 * T, 0.92,
        house_id="farm_house", interior_type="farmhouse",
        title="Nhà Chính Nông Trại", owner_name="Cô Leah",
        owner_folder="npc_04_green_hair", owner_role="Nghệ nhân & Chăm sóc vườn",
    )
    wb.prop("mailbox", 28.8 * T, 8.0 * T, h=46)
    wb.prop("crate", 29.8 * T, 8.2 * T, w=42, h=38)  # Thùng Giao Hàng Nông Trại (Shipping Bin)
    wb.prop("barrel", 22.4 * T, 7.9 * T, h=42)
    wb.prop("crate", 23.1 * T, 8.1 * T, h=38)

    # 4. SÁU THỬA RUỘNG CÂY TRỒNG CÓ RÀO GỖ, VÒI TƯỚI (SPRINKLER) & BÙ NHÌN (SCARECROW)
    wb.field(
        20, 11, 23, 14, "strawberry",
        spot_id="crop_straw_1", title="Ruộng Dâu Tây Đỏ", item_key="strawberry",
        fence=True, sprinkler=True, scarecrow=True,
    )
    wb.field(
        25, 11, 29, 14, "pumpkin",
        spot_id="crop_pump_1", title="Ruộng Bí Ngô Vàng", item_key="pumpkin",
        fence=True, sprinkler=True,
    )
    wb.field(
        31, 11, 34, 14, "corn",
        spot_id="crop_corn_1", title="Ruộng Bắp Ngô Ngọt", item_key="corn",
        fence=True, scarecrow=True,
    )
    wb.field(
        20, 18, 23, 21, "tomato",
        spot_id="crop_tom_1", title="Ruộng Cà Chua Chín", item_key="tomato",
        fence=True, sprinkler=True,
    )
    wb.field(
        25, 18, 29, 21, "carrot",
        spot_id="crop_carrot_1", title="Ruộng Cà Rốt Tươi", item_key="carrot",
        fence=True, sprinkler=True,
    )
    wb.field(
        31, 3, 34, 7, "wheat",
        spot_id="crop_wheat_1", title="Ruộng Lúa Mì Vàng", item_key="wheat",
        fence=True, scarecrow=True,
    )

    # 5. VƯỜN CÂY ĂN QUẢ (TÁO, CAM, ĐÀO) BÊN TRÁI TRUNG TÂM
    wb.fence_h(3, 14, 11, style="rail", gaps=(8, 9))
    wb.fruit_tree("tree_apple_1", "Cây Táo Đỏ #1", "apple", 5.0 * T, 14.0 * T, "tree_oak", h=112)
    wb.fruit_tree("tree_orange_1", "Cây Cam Vàng #1", "orange", 9.0 * T, 14.0 * T, "tree_oak", h=112)
    wb.fruit_tree("tree_peach_1", "Cây Đào Tiên #1", "peach", 13.0 * T, 14.0 * T, "tree_cherry", h=112)
    wb.fruit_tree("tree_apple_2", "Cây Táo Đỏ #2", "apple", 11.2 * T, 6.8 * T, "tree_oak", h=108)
    wb.fruit_tree("tree_peach_2", "Cây Đào Tiên #2", "peach", 31.8 * T, 18.8 * T, "tree_cherry", h=108)

    # 6. KHU CHĂN NUÔI GIA SÚC (Chuồng Bò, Chuồng Gà, Đồng Cỏ Có Hàng Rào & Ao Cá)
    wb.building("house_coop", 4.8 * T, 20.2 * T, 0.82, door=False)
    wb.building("house_barn", 8.8 * T, 20.4 * T, 0.82, door=False)
    wb.pasture(
        10, 18, 14, 22,
        animals=[("cow", 44), ("pig", 38), ("sheep", 40), ("chicken", 30), ("chicken", 30)],
        gate_col=12,
    )
    wb.prop("fishpond", 32.5 * T, 22.8 * T, w=118, h=96, collider_w=0.85, collider_h=64, kind="pond")
    wb.prop("crate", 14.2 * T, 12.1 * T, h=36, solid=False)
    wb.prop("barrel", 15.7 * T, 11.9 * T, h=40, solid=False)
    wb.prop("sunflower", 18.4 * T, 15.2 * T, h=42, solid=False)
    wb.prop("sunflower", 24.4 * T, 15.2 * T, h=42, solid=False)

    # 7. Xe kéo nông sản tự hành (AGV) & Nông dân
    game.agvs.append(
        FarmCartAGV(
            17.0 * T,
            9.5 * T,
            waypoints=[(5.0 * T, 9.5 * T), (30.0 * T, 9.5 * T), (17.0 * T, 9.5 * T), (17.0 * T, 16.5 * T)],
        )
    )
    game.npcs.extend([
        VillagerNPC(
            name="Quản nông Kent",
            role="Người giao Nhiệm vụ Nông Vụ",
            x=14.8 * T,
            y=8.8 * T,
            folder="npc_brown",
            theta=math.pi / 2.0,
            is_stationary=True,
        ),
        VillagerNPC(
            name="Cô Caroline",
            role="Cửa Hàng Hạt Giống [E]",
            x=15.0 * T,
            y=12.5 * T,
            folder="npc_purple",
            theta=math.pi / 2.0,
            is_stationary=True,
        ),
        VillagerNPC(
            name="Nông dân Marnie",
            role="Chăm sóc vườn quả & đồng cỏ",
            x=10.5 * T,
            y=9.6 * T,
            folder="npc_06_farmer_girl",
            patrol_points=[
                (6.5 * T, 9.5 * T),
                (17.2 * T, 9.5 * T),
                (17.2 * T, 16.4 * T),
                (17.2 * T, 9.5 * T),
            ],
        ),
        VillagerNPC(
            name="Cô Leah",
            role="Chăm sóc luống rau",
            x=24.0 * T,
            y=9.5 * T,
            folder="npc_04_green_hair",
            patrol_points=[
                (18.5 * T, 9.4 * T),
                (32.0 * T, 9.4 * T),
                (32.0 * T, 10.4 * T),
                (18.5 * T, 10.4 * T),
            ],
        ),
        VillagerNPC(
            name="Anh Shane",
            role="Điều phối nông sản",
            x=22.0 * T,
            y=16.4 * T,
            folder="npc_05_blue_boy",
            patrol_points=[
                (17.8 * T, 16.3 * T),
                (30.0 * T, 16.3 * T),
                (30.0 * T, 17.3 * T),
                (17.8 * T, 17.3 * T),
            ],
        ),
    ])

    if spawn_pos is not None:
        game.robot.x, game.robot.y = spawn_pos
        game.robot.theta = spawn_theta if spawn_theta is not None else -math.pi / 2.0
    else:
        game.robot.x, game.robot.y = 17.5 * T, SCREEN_H - 68.0
        game.robot.theta = -math.pi / 2.0


# ==============================================================================
# MAP 3: ĐẢO RỪNG XANH & BẾN HỒ CÂU CÁ (Lấy cảm hứng từ Ảnh 1)
# ==============================================================================
def _build_map3_lakeside_fishing(game, wb: WorldBuilder, spawn_pos, spawn_theta):
    # 1. Mặt hồ lớn xanh biếc chiếm nửa phải & góc Tây-Nam, bao quanh các hòn đảo
    wb.fill(15, 1, 35, 22, T_SAND)
    wb.fill(16, 2, 35, 21, T_WATER)
    wb.ellipse(9.0, 20.5, 6.5, 3.2, T_SAND)
    wb.ellipse(9.0, 20.8, 5.5, 2.4, T_WATER)

    # Đảo Rừng Phía Bắc (Cột 25..33, Hàng 3..9) & Đảo Câu Cá Phía Nam (Cột 23..30, Hàng 16..20)
    wb.ellipse(29.0, 6.2, 4.8, 3.2, T_SAND)
    wb.ellipse(29.0, 6.2, 3.9, 2.4, T_GRASS)
    wb.ellipse(26.5, 18.0, 4.0, 2.5, T_SAND)
    wb.ellipse(26.5, 18.0, 3.1, 1.8, T_GRASS)

    # 2. Đường đá & Đường đất rừng từ Cổng Tây (Map 1) dẫn ra 3 Cầu Gỗ / Cầu Tàu
    wb.fill(0, 11, 15, 13, T_COBBLE)
    wb.fill(8, 5, 11, 18, T_DIRT)
    wb.fill(3, 6, 13, 8, T_DIRT)

    # 3 Cầu gỗ bắc qua hồ (Thử thách đi chậm an toàn [SHIFT]/[X])
    wb.fill(15, 6, 25, 7, T_BRIDGE)       # Cầu Bắc nối ra Đảo Rừng Bắc
    wb.fill(15, 12, 30, 13, T_WOOD_DOCK)  # Cầu Tàu Trung Tâm vươn xa giữa hồ
    wb.fill(15, 17, 23, 18, T_BRIDGE)     # Cầu Nam nối ra Đảo Câu Cá Nam

    # Cổng phía Tây về Map 1
    game.portals.append(
        MapPortal(
            rect=pygame.Rect(0, 11 * T, 24, 3 * T),
            target_map_id=1,
            spawn_x=SCREEN_W - 76.0,
            spawn_y=12.5 * T,
            spawn_theta=math.pi,
            label="◄ Về Map 1: Quảng Trường Thị Trấn",
            arrow_dir="left",
        )
    )

    # 3. Chòi Ngư Cụ Ven Hồ & Ruộng Nông Sản Ven Bờ Nước (giống Ảnh 1)
    wb.building(
        "house_shed", 5.2 * T, 6.6 * T, 0.94,
        house_id="fisher_shed", interior_type="cabin",
        title="Chòi Ngư Cụ Ven Hồ", owner_name="Chàng mèo Leo",
        owner_folder="npc_10_cat_boy", owner_role="Ngư dân trẻ",
    )
    wb.field(
        2, 14, 6, 16, "cabbage",
        spot_id="lake_cab_1", title="Ruộng Bắp Cải Ven Hồ", item_key="cabbage",
        fence=True, sprinkler=True,
    )
    wb.field(
        27, 5, 30, 6, "strawberry",
        spot_id="island_straw_1", title="Vườn Dâu Trên Đảo", item_key="strawberry",
        fence=False,
    )

    # Rừng cây, gốc cây (stump), khúc gỗ (log), tảng đá (rock_1..4), bụi quả mọng (bush_berry)
    for cx, cy, tk in [
        (2.2 * T, 4.2 * T, "tree_pine"),
        (12.8 * T, 4.4 * T, "tree_cherry"),
        (32.2 * T, 5.8 * T, "tree_cherry"),
        (28.5 * T, 18.2 * T, "tree_pine"),
        (13.2 * T, 16.2 * T, "tree_oak"),
    ]:
        wb.tree(tk, cx, cy, h=114)

    wb.prop("stump", 12.2 * T, 9.8 * T, h=42)
    wb.prop("log", 4.5 * T, 9.8 * T, h=38)
    wb.prop("bush_berry", 7.2 * T, 4.8 * T, h=44)
    wb.prop("bush_berry", 25.5 * T, 17.5 * T, h=42)
    wb.prop("rock_1", 13.8 * T, 10.4 * T, h=32)
    wb.prop("rock_3", 29.8 * T, 8.2 * T, h=34)
    wb.prop("barrel", 7.2 * T, 6.6 * T, h=42)
    wb.prop("signpost", 14.2 * T, 11.2 * T, h=50)

    # 4. Ba Điểm Thả Câu Cá (Fishing Spots)
    game.fishing_spots.extend([
        FishingSpot(
            spot_id="dock_center",
            title="Mũi Cầu Tàu Trung Tâm",
            stand_x=float(29 * T + 16),
            stand_y=float(12 * T + 28),
            water_x=float(32 * T + 8),
            water_y=float(12 * T + 28),
        ),
        FishingSpot(
            spot_id="island_north",
            title="Bờ Đảo Hoa Anh Đào Phía Bắc",
            stand_x=float(31 * T + 12),
            stand_y=float(7 * T + 12),
            water_x=float(34 * T),
            water_y=float(7 * T + 12),
        ),
        FishingSpot(
            spot_id="island_south",
            title="Đảo Câu Cá Phía Nam",
            stand_x=float(27 * T + 16),
            stand_y=float(18 * T + 16),
            water_x=float(31 * T),
            water_y=float(18 * T + 16),
        ),
    ])

    # 5. Cư dân Bến Hồ:
    # - NPC 1 hướng (`npc_black`): đứng yên giao nhiệm vụ tại đầu cầu tàu
    # - 3 NPC nhiều hướng (`npc_07_old_man`, `npc_12_adventurer`, `npc_10_cat_boy`): di chuyển tuần tra 4 hướng
    game.npcs.extend([
        VillagerNPC(
            name="Kỹ sư Sebastian",
            role="Người giao Nhiệm vụ Bến Hồ",
            x=float(11.8 * T),
            y=float(10.8 * T),
            folder="npc_black",
            theta=math.pi / 2.0,
            is_stationary=True,
        ),
        VillagerNPC(
            name="Ngư phủ Willy",
            role="Thợ câu lão luyện",
            x=float(20.5 * T),
            y=float(12.5 * T),
            folder="npc_07_old_man",
            patrol_points=[
                (float(15.5 * T), float(12.4 * T)),
                (float(26.5 * T), float(12.4 * T)),
                (float(26.5 * T), float(13.3 * T)),
                (float(15.5 * T), float(13.3 * T)),
            ],
        ),
        VillagerNPC(
            name="Nhà thám hiểm Marlon",
            role="Canh gác Đảo Bắc",
            x=float(20.0 * T),
            y=float(6.5 * T),
            folder="npc_12_adventurer",
            patrol_points=[
                (float(15.5 * T), float(6.4 * T)),
                (float(26.2 * T), float(6.4 * T)),
                (float(26.2 * T), float(7.3 * T)),
                (float(15.5 * T), float(7.3 * T)),
            ],
        ),
        VillagerNPC(
            name="Chàng mèo Leo",
            role="Dạo bộ bờ hồ",
            x=float(9.5 * T),
            y=float(14.2 * T),
            folder="npc_10_cat_boy",
            patrol_points=[
                (float(9.0 * T), float(7.2 * T)),
                (float(9.0 * T), float(17.2 * T)),
                (float(10.5 * T), float(17.2 * T)),
                (float(10.5 * T), float(7.2 * T)),
            ],
        ),
    ])

    if spawn_pos is not None:
        game.robot.x, game.robot.y = spawn_pos
        game.robot.theta = spawn_theta if spawn_theta is not None else 0.0
    else:
        game.robot.x, game.robot.y = 72.0, 12.5 * T
        game.robot.theta = 0.0


# ==============================================================================
# MAP 4: KHU DÂN CƯ & VƯỜN HOA GIA ĐÌNH (Lấy cảm hứng từ Ảnh 3 & Ảnh 4)
# ==============================================================================
def _build_map4_residential_village(game, wb: WorldBuilder, spawn_pos, spawn_theta):
    # 1. Rừng cây viền bản đồ & Suối nhỏ góc Tây-Nam
    wb.forest_border(depth=1, gaps={"E": (10, 14)})
    wb.ellipse(4.5, 22.0, 5.0, 2.4, T_SAND)
    wb.ellipse(4.5, 22.3, 4.0, 1.7, T_WATER)

    # 2. Đại lộ lát đá chính nối sang Cổng Đông (Map 1) & Đường nhánh vào 4 Dinh Thự + Xưởng Robot
    wb.fill(3, 11, 35, 13, T_COBBLE)
    wb.fill(8, 7, 10, 19, T_DIRT)
    wb.fill(22, 7, 24, 19, T_DIRT)
    wb.fill(26, 14, 28, 21, T_COBBLE)
    wb.fill(26, 20, 33, 21, T_COBBLE)

    # Cổng phía Đông quay về Map 1
    game.portals.append(
        MapPortal(
            rect=pygame.Rect(SCREEN_W - 24, 11 * T, 24, 3 * T),
            target_map_id=1,
            spawn_x=76.0,
            spawn_y=12.5 * T,
            spawn_theta=0.0,
            label="► Về Map 1: Quảng Trường Thị Trấn",
            arrow_dir="right",
        )
    )

    # 3. NĂM TÒA NHÀ KHU DÂN CƯ (4 Nhà Cư Dân + Xưởng & Nhà Robot Số 5 tại khoảng trống Đông-Nam!)
    wb.building(
        "house_farm", 8.8 * T, 7.6 * T, 0.94,
        house_id="house_gus", interior_type="gus_kitchen",
        title="Nhà Đầu Bếp Gus (Số 1)", owner_name="Đầu bếp Gus",
        owner_folder="npc_01_orange_boy", owner_role="Đầu bếp Trưởng",
    )
    wb.building(
        "house_blue", 24.0 * T, 7.6 * T, 0.94,
        house_id="house_robin", interior_type="robin_workshop",
        title="Nhà Thợ Mộc Robin (Số 2)", owner_name="Thợ mộc Robin",
        owner_folder="npc_06_farmer_girl", owner_role="Kiến trúc sư",
    )
    wb.building(
        "house_town", 9.0 * T, 19.6 * T, 0.94,
        house_id="house_willy", interior_type="willy_cabin",
        title="Nhà Ngư Phủ Willy (Số 3)", owner_name="Ngư phủ Willy",
        owner_folder="npc_07_old_man", owner_role="Ngư dân kỳ cựu",
    )
    wb.building(
        "house_manor", 22.8 * T, 19.8 * T, 0.95,
        house_id="house_lewis", interior_type="lewis_manor",
        title="Dinh Thự Thị Trưởng Lewis (Số 4)", owner_name="Thị trưởng Lewis",
        owner_folder="npc_13_scholar", owner_role="Thị trưởng Thị trấn",
    )
    wb.building(
        "house_robot", 31.4 * T, 19.8 * T, 0.28,
        house_id="robot_house", interior_type="robot_workshop",
        title="Xưởng & Nhà Robot (Số 5)", owner_name="Thợ mộc Robin",
        owner_folder="npc_06_farmer_girl", owner_role="Kiến trúc sư & Cải tiến Robot",
    )

    # 4. Sân vườn riêng trước mỗi ngôi nhà (Vườn rau gia đình, hàng rào trắng, hồ cá, mèo con, cọc tiêu Xưởng Robot)
    wb.field(
        13, 4, 16, 6, "tomato",
        spot_id="village_tom_1", title="Vườn Cà Chua Nhà Gus", item_key="tomato",
        fence=True, sprinkler=True,
    )
    wb.field(
        29, 4, 32, 6, "pumpkin",
        spot_id="village_pump_1", title="Vườn Bí Ngô Nhà Robin", item_key="pumpkin",
        fence=True,
    )
    wb.flower_bed(14, 16, 17, 17)
    wb.fence_h(19, 25, 20, style="picket", gaps=(22, 23))
    wb.prop("rh_bollard", 29.0 * T, 20.1 * T, h=42)
    wb.prop("rh_bollard", 33.8 * T, 20.1 * T, h=42)
    wb.prop("rh_sensor_post", 29.0 * T, 15.8 * T, h=52)

    wb.prop("fishpond", 14.8 * T, 21.8 * T, w=116, h=92, collider_w=0.85, collider_h=60, kind="pond")
    wb.prop("well", 16.5 * T, 10.2 * T, h=72)
    wb.prop("bench", 16.5 * T, 14.8 * T, h=42)
    wb.prop("mailbox", 11.8 * T, 7.8 * T, h=46)
    wb.prop("mailbox", 26.8 * T, 7.8 * T, h=46)
    wb.prop("mailbox", 11.6 * T, 19.8 * T, h=46)
    wb.prop("mailbox", 25.8 * T, 19.8 * T, h=46)
    wb.prop("log", 28.2 * T, 7.8 * T, h=38)
    wb.prop("cat", 20.4 * T, 19.5 * T, h=36, solid=False)
    wb.lamp(6.2 * T, 10.6 * T)
    wb.lamp(19.5 * T, 10.6 * T)
    wb.lamp(30.5 * T, 10.6 * T)

    for cx, cy, tk in [
        (3.2 * T, 7.2 * T, "tree_cherry"),
        (19.2 * T, 6.8 * T, "tree_oak"),
        (33.2 * T, 8.2 * T, "tree_cherry"),
        (3.2 * T, 17.5 * T, "tree_oak"),
    ]:
        wb.tree(tk, cx, cy, h=114)

    # 5. Cư dân Khu Dân Cư:
    # - 2 NPC 1 hướng (`npc_blonde`, `npc_purple`): đứng yên giao nhiệm vụ (`is_stationary=True`)
    # - 3 NPC nhiều hướng (`npc_02_blonde_girl`, `npc_03_purple_hair`, `npc_13_scholar`): di chuyển tuần tra 4 hướng
    game.npcs.extend([
        VillagerNPC(
            name="Cô giáo Penny",
            role="Người giao Nhiệm vụ Mùa Vụ",
            x=13.8 * T,
            y=10.6 * T,
            folder="npc_blonde",
            theta=math.pi / 2.0,
            is_stationary=True,
        ),
        VillagerNPC(
            name="Dược sĩ Maru",
            role="Người giao Nhiệm vụ Y Tế",
            x=20.8 * T,
            y=10.6 * T,
            folder="npc_purple",
            theta=math.pi / 2.0,
            is_stationary=True,
        ),
        VillagerNPC(
            name="Cô Haley",
            role="Nhiếp ảnh gia Khu Dân Cư",
            x=18.0 * T,
            y=12.0 * T,
            folder="npc_02_blonde_girl",
            theta=0.0,
            patrol_points=[
                (6.0 * T, 11.8 * T),
                (29.0 * T, 11.8 * T),
                (29.0 * T, 13.3 * T),
                (6.0 * T, 13.3 * T),
            ],
        ),
        VillagerNPC(
            name="Cô Abigail",
            role="Cư dân yêu khám phá",
            x=24.2 * T,
            y=13.5 * T,
            folder="npc_03_purple_hair",
            patrol_points=[
                (23.6 * T, 9.2 * T),
                (23.6 * T, 15.6 * T),
                (25.0 * T, 15.6 * T),
                (25.0 * T, 9.2 * T),
            ],
        ),
        VillagerNPC(
            name="Học giả Elliott",
            role="Nhà văn đi dạo khu dân cư",
            x=9.2 * T,
            y=13.5 * T,
            folder="npc_13_scholar",
            patrol_points=[
                (8.6 * T, 9.2 * T),
                (8.6 * T, 15.6 * T),
                (10.0 * T, 15.6 * T),
                (10.0 * T, 9.2 * T),
            ],
        ),
    ])

    if spawn_pos is not None:
        game.robot.x, game.robot.y = spawn_pos
        game.robot.theta = spawn_theta if spawn_theta is not None else math.pi
    else:
        game.robot.x, game.robot.y = SCREEN_W - 76.0, 12.5 * T
        game.robot.theta = math.pi


# ==============================================================================
# CHUYỂN TIẾP VÀO / RA MAP 5 (NỘI THẤT ĐẶC SẮC CHO TỪNG NGÔI NHÀ)
# ==============================================================================
def get_interior_theme(building: PropObject | None) -> dict:
    if building is None:
        return INTERIOR_THEMES["farm_house"]
    return INTERIOR_THEMES.get(building.house_id, INTERIOR_THEMES["farm_house"])


def enter_house(game, building: PropObject, spawn_on_dock: bool = False):
    """Chuyển từ Map ngoài trời vào Map 5: Không Gian Nội Thất Trong Nhà (mỗi nhà 1 giao diện riêng)."""
    game.saved_outdoor_map_id = game.current_map_id
    game.saved_outdoor_pos = (
        float(building.door_rect.centerx),
        float(building.door_rect.bottom + 24),
    )
    game.saved_outdoor_theta = -math.pi / 2.0

    game.in_interior = True
    game.current_interior = building

    theme = get_interior_theme(building)
    rw, rh = theme["room_size"]
    rh = min(rh, 440)
    game.room_rect = pygame.Rect((SCREEN_W - rw) // 2, (SCREEN_H - rh) // 2 + 34, rw, rh)
    rx, ry = game.room_rect.x, game.room_rect.y

    # Nếu là Xưởng & Nhà Robot và spawn_on_dock=True -> Đặt Robot đứng ngay trên Đế Sạc Tia Chớp
    if getattr(building, "house_id", "") == "robot_house" and spawn_on_dock:
        game.robot.x = float(rx + int(rw * 0.77))
        game.robot.y = float(ry + int(rh * 0.56))
        game.robot.theta = math.pi / 2.0
    else:
        # Đặt Robot ở tấm thảm lối vào trong nhà
        game.robot.x = float(game.room_rect.centerx)
        game.robot.y = float(ry + rh - 52)
        game.robot.theta = -math.pi / 2.0
    game.robot.v_mps = 0.0
    game.robot.vx, game.robot.vy = 0.0, 0.0

    if getattr(building, "house_id", "") == "robot_house":
        game.interior_npcs = []
        game.set_banner(
            "Xưởng & Nhà Robot: Bấm [E]/[U] tại Cánh Tay Robot (Trái) để Nâng cấp, hoặc [E]/[N] tại Đế Sạc (Phải) để Sạc & Ngủ!",
            (135, 245, 255),
        )
    else:
        # Đặt Chủ nhà đứng giữa phòng, mặt hướng về phía cửa (theta = pi/2)
        host = VillagerNPC(
            name=building.owner_name,
            role=building.owner_role,
            x=float(rx + rw * 0.50),
            y=float(ry + rh * 0.45),
            folder=building.owner_folder,
            theta=math.pi / 2.0,
            is_stationary=True,
        )
        host.trigger_emote("♥", 2.5)
        game.interior_npcs = [host]
        game.set_banner(
            f"Đã vào {building.title} — Tiến vào Quạt Xanh trước mặt {building.owner_name} rồi bấm [E]",
            (255, 240, 165),
        )


def exit_house(game):
    """Rời khỏi Map 5 Nội Thất quay về đúng vị trí cửa nhà ngoài trời."""
    game.in_interior = False
    game.current_interior = None
    game.interior_npcs.clear()
    game.current_map_id = game.saved_outdoor_map_id
    game.robot.x, game.robot.y = game.saved_outdoor_pos
    game.robot.theta = game.saved_outdoor_theta
    game.robot.v_mps = 0.0
    game.robot.vx, game.robot.vy = 0.0, 0.0
    game.set_banner(f"Đã rời khỏi nhà — Trở lại {MAP_TITLES[game.current_map_id]}", (220, 245, 255))


def is_circle_blocked(game, cx: float, cy: float, radius: float) -> bool:
    """Kiểm tra va chạm hình tròn của Robot/NPC với tường, mặt nước hoặc công trình."""
    if game.in_interior:
        inner = game.room_rect.inflate(-int(radius * 2), -int(radius * 2))
        if not inner.collidepoint(int(cx), int(cy)):
            return True
        rx, ry = game.room_rect.x, game.room_rect.y
        if cy - radius < ry + 92:
            return True
        return False

    if cx - radius < 6 or cx + radius > SCREEN_W - 6:
        return True
    if cy - radius < 6 or cy + radius > SCREEN_H - 6:
        return True

    for ang in (0.0, math.pi * 0.5, math.pi, math.pi * 1.5, math.pi * 0.25, math.pi * 0.75):
        px = cx + math.cos(ang) * (radius * 0.82)
        py = cy + math.sin(ang) * (radius * 0.82)
        tc = int(px) // TILE_SIZE
        tr = int(py) // TILE_SIZE
        if 0 <= tr < GRID_ROWS and 0 <= tc < GRID_COLS:
            if game.tiles[tr][tc] in BLOCKING_TILES:
                return True

    foot_rect = pygame.Rect(
        int(cx - radius * 0.78),
        int(cy - radius * 0.58),
        int(radius * 1.56),
        int(radius * 1.16),
    )
    for prop in game.props:
        if prop.solid and prop.collider.colliderect(foot_rect):
            return True
    for blk in getattr(game, "extra_blockers", []):
        if blk.colliderect(foot_rect):
            return True

    return False
