# environment/topology.py
from enum import IntEnum


class TopologyID(IntEnum):
    # 4 Bản đồ Chính của Trò chơi FarmBot Town (game/maps.py: Map 1 - Map 4)
    FARMBOT_MAP1_TOWN_SQUARE = 1       # Map 1: Quảng Trường Thị Trấn, Dòng Sông & 2 Cây Cầu
    FARMBOT_MAP2_GRAND_FARM = 2        # Map 2: Đại Nông Trại, 6 Ruộng Cây, Vườn Quả & Chuồng Trại
    FARMBOT_MAP3_LAKESIDE_ISLAND = 3   # Map 3: Đảo Rừng Xanh, Hồ Lớn & 3 Cầu Gỗ Câu Cá
    FARMBOT_MAP4_RESIDENTIAL_ROBOT = 4 # Map 4: Khu Dân Cư 4 Dinh Thự & Xưởng Robot (Số 5)

    # Không gian Nội thất Map 5 & Các Topology Huấn luyện / Đánh giá (5 - 15)
    T_JUNCTION = 5
    CROSS_INTERSECTION = 6
    SINGLE_DOOR_ROOM = 7
    TWO_ROOM_CONNECTED = 8
    PILLAR_HALL = 9
    DOUBLE_BOTTLENECK = 10
    THREE_ROOM_OFFICE = 11
    COURTYARD_DYNAMIC_LANES = 12
    H_SHAPED_COMPLEX = 13
    MULTI_ROOM_MAZE = 14
    CROWDED_PLAZA_GATES = 15


TOPOLOGY_NAMES: dict[int, str] = {
    1: "Game Map 1: Pelican Town Square & River Bridges",
    2: "Game Map 2: Grand Farmstead, 6 Crop Fields & Orchard",
    3: "Game Map 3: Forest Island & 3 Lakeside Bridges",
    4: "Game Map 4: Residential Village & Robot Workshop",
    5: "5: Indoor & T-Junction Plaza (Train)",
    6: "6: Cross Intersection (Train)",
    7: "7: Single Door Room (Train)",
    8: "8: Two-Room Connected (Train)",
    9: "9: Pillar Hall (Train)",
    10: "10: Double Bottleneck (Val)",
    11: "11: Three-Room Office (Val)",
    12: "12: Courtyard Dynamic Lanes (Val)",
    13: "13: H-Shaped Complex (Test)",
    14: "14: Multi-Room Maze (Test)",
    15: "15: Crowded Plaza & Gates (Test)",
}

GAME_TOPOLOGIES = [1, 2, 3, 4]
TRAIN_TOPOLOGIES = list(range(1, 10))
VAL_TOPOLOGIES = [10, 11, 12]
TEST_TOPOLOGIES = [13, 14, 15]
