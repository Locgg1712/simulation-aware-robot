# environment/topology.py
from enum import IntEnum


class TopologyID(IntEnum):
    # 4 Bản đồ Stardew Valley đặc trưng theo 4 ảnh mẫu (1 - 4)
    STARDEW_BEACH_FARM = 1         # Ảnh 1: Nông trại Bờ Biển & Đảo Xanh
    STARDEW_HILLTOP_FARM = 2       # Ảnh 2: Nông trại Đồi Cao, Đường Đá & Nhà Kính
    STARDEW_PELICAN_TOWN = 3       # Ảnh 3: Thị trấn Pelican, Quảng Trường & Dòng Sông
    STARDEW_FOREST_PONDS = 4       # Ảnh 4: Nông trại Rừng Xanh & 3 Hồ Cá

    # Các Topology bổ sung (5 - 15)
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
    1: "Map 1: Beach & Island Farm (Stardew)",
    2: "Map 2: Hill-top Farm & Greenhouse (Stardew)",
    3: "Map 3: Pelican Town & River Bridges (Stardew)",
    4: "Map 4: Four Corners & 3 Fish Ponds (Stardew)",
    5: "5: T-Junction (Train)",
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

TRAIN_TOPOLOGIES = list(range(1, 10))
VAL_TOPOLOGIES = [10, 11, 12]
TEST_TOPOLOGIES = [13, 14, 15]