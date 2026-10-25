# game/constants.py
"""
Hằng số cấu hình màn hình, quy đổi đơn vị vật lý (Mét <-> Pixel),
thông số HRI (Front Interaction Zone) và Bảng điểm chuẩn theo Context_game_farmbot.md.
"""

import math

# Kích thước cửa sổ & Lưới Tilemap (1152x768 = 36x24 ô 32px)
SCREEN_W = 1152
SCREEN_H = 768
TILE_SIZE = 32
GRID_COLS = SCREEN_W // TILE_SIZE  # 36 cột
GRID_ROWS = SCREEN_H // TILE_SIZE  # 24 hàng
WORLD_COLS = GRID_COLS
WORLD_ROWS = GRID_ROWS
WORLD_W = SCREEN_W
WORLD_H = SCREEN_H

# Tỉ lệ quy đổi: 1.0 mét = 48.0 pixel
PX_PER_METER = 48.0

# Bán kính va chạm & Khoảng cách an toàn (Mục 3 & Mục 4)
ROBOT_RADIUS_M = 0.35                           # R_robot = 0.35 m (16.8 px)
NPC_RADIUS_M = 0.30                             # r_npc   = 0.30 m (14.4 px)
HITBOX_TOUCH_M = ROBOT_RADIUS_M + NPC_RADIUS_M  # 0.65 m (31.2 px)
PERSONAL_SPACE_M = 0.70                         # d < 0.70 m -> Xâm phạm vùng cá nhân (-5đ/s)

# Vùng Tương Tác Hợp Lệ Trước Mặt NPC (Front Interaction Zone - Mục 3.2)
INTERACT_MIN_M = 0.75                           # Khoảng cách tối thiểu 0.75 m
INTERACT_MAX_M = 1.45                           # Khoảng cách tối đa 1.45 m
INTERACT_NPC_FAN_DEG = 35.0                     # Góc lệch trước mặt NPC <= 35°
INTERACT_ROBOT_FACE_DEG = 45.0                  # Góc lệch hướng mặt Robot <= 45°
INTERACT_STOP_SPEED_MPS = 0.05                  # Dừng hẳn v < 0.05 m/s

# Vận tốc của Robot
ROBOT_V_MAX_MPS = 1.00                          # v_max = 1.0 m/s
ROBOT_SLOW_FACTOR = 0.30                        # Chế độ đi chậm an toàn v = 0.3 * v_max
ROBOT_SCREEN_SPEED_SCALE = 185.0                # 1.0 m/s tương ứng 185 px/s trên màn hình

# Mã địa hình Tile
T_GRASS = 0
T_WATER = 1
T_SAND = 2
T_DIRT = 3
T_COBBLE = 4
T_CLIFF = 5
T_CROP = 6        # Đất ruộng đã xới (Tilled soil)
T_BRIDGE = 7      # Cầu gỗ / Cầu đá bắc qua sông hồ
T_WOOD_DOCK = 8   # Cầu tàu câu cá
T_TALL_GRASS = 9  # Cỏ xanh đậm
T_FOREST = 10     # Rừng cây viền bản đồ

BLOCKING_TILES = (T_WATER, T_CLIFF, T_FOREST)

# Danh sách 7 sprite NPC 1 hướng (đứng yên giao nhiệm vụ) trong `sprites/sprites/`
SINGLE_DIR_NPC_SPRITES = (
    "npc_red",
    "npc_old",
    "npc_green",
    "npc_brown",
    "npc_black",
    "npc_blonde",
    "npc_purple",
)

# Danh sách 12 thư mục nhân vật NPC nhiều hướng (di chuyển tuần tra 4 hướng) trong `sprites/sprites/characters/`
ALL_NPC_FOLDERS = (
    "npc_01_orange_boy",
    "npc_02_blonde_girl",
    "npc_03_purple_hair",
    "npc_04_green_hair",
    "npc_05_blue_boy",
    "npc_06_farmer_girl",
    "npc_07_old_man",
    "npc_08_maid",
    "npc_09_young_girl",
    "npc_10_cat_boy",
    "npc_12_adventurer",
    "npc_13_scholar",
)

# Tên hiển thị của 5 Bản đồ Liên thông
MAP_TITLES = {
    1: "Map 1: Quảng Trường & Bờ Sông Thị Trấn",
    2: "Map 2: Đại Nông Trại & Ruộng Cây Trồng",
    3: "Map 3: Đảo Rừng Xanh & Bến Hồ Câu Cá",
    4: "Map 4: Khu Dân Cư & Vườn Hoa Gia Đình",
    5: "Map 5: Không Gian Nội Thất Trong Nhà",
}

# Tên tiếng Việt của các vật phẩm trong Khay Chứa Đồ (4 Inventory Slots)
ITEM_NAMES_VI = {
    "apple": "Táo Đỏ Chín",
    "orange": "Cam Vàng Mọng",
    "peach": "Đào Tiên Hồng",
    "strawberry": "Dâu Tây Đỏ",
    "pumpkin": "Bí Ngô Vàng",
    "tomato": "Cà Chua Chín",
    "carrot": "Cà Rốt Tươi",
    "corn": "Bắp Ngô Ngọt",
    "cabbage": "Bắp Cải Xanh",
    "wheat": "Lúa Mì Vàng",
    "fish": "Cá Hồ Tươi",
    "bread": "Bánh Mì Nóng",
    "parcel": "Kiện Hàng Nhanh",
    "mushroom": "Nấm Rừng Thơm",
    "wild_berry": "Quả Mọng Rừng",
    "golden_flower": "Hoa Cúc Vàng",
    "iridium_ore": "Khoáng Thạch Iridium",
}

# Bảng quy đổi Điểm thưởng & Phạt (Mục 6)
SCORE_ACCEPT_QUEST = +20
SCORE_HARVEST_FRUIT = +30
SCORE_CATCH_FISH = +50
SCORE_DELIVER_OUTDOOR = +150
SCORE_DELIVER_INDOOR = +250
SCORE_EXPRESS_BONUS = +50
SCORE_SMART_YIELD = +5
PENALTY_PERSONAL_SPACE_PER_SEC = -5
PENALTY_KNOCKDOWN = -100
PENALTY_MULTI_HIT_DIE = -250
PENALTY_RUN_OVER_DIE = -500

# Vị trí Trạm Sạc Pin & Nghỉ Ngơi (Charging Dock) tại 4 Bản đồ Ngoài trời (Map 1..4)
CHARGING_DOCKS: dict[int, tuple[float, float, str]] = {
    1: (16.0 * TILE_SIZE, 12.2 * TILE_SIZE, "Trạm Sạc Quảng Trường"),
    2: (18.5 * TILE_SIZE, 8.2 * TILE_SIZE, "Trạm Sạc Nông Trại"),
    3: (8.5 * TILE_SIZE, 11.2 * TILE_SIZE, "Trạm Sạc Bến Hồ"),
    4: (21.5 * TILE_SIZE, 10.5 * TILE_SIZE, "Trạm Sạc Xưởng Robin"),
}


def m_to_px(meters: float) -> float:
    return meters * PX_PER_METER


def px_to_m(pixels: float) -> float:
    return pixels / PX_PER_METER


def normalize_angle(angle: float) -> float:
    return math.atan2(math.sin(angle), math.cos(angle))


def angle_diff_deg(a: float, b: float) -> float:
    return abs(math.degrees(normalize_angle(a - b)))


def dir_from_angle(theta: float) -> str:
    c, s = math.cos(theta), math.sin(theta)
    if abs(c) >= abs(s):
        return "right" if c > 0 else "left"
    return "down" if s > 0 else "up"
