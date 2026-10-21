# Phase 2: Định nghĩa 15 Topology Templates (Training 1-9, Validation 10-12, Testing 13-15)
# environment/topology.py
from enum import IntEnum


class TopologyID(IntEnum):
    # Tập Training (1 - 9)
    OPEN_AREA = 1
    STRAIGHT_CORRIDOR = 2
    NARROW_PASSAGE = 3
    L_CORNER = 4
    T_JUNCTION = 5
    CROSS_INTERSECTION = 6
    SINGLE_DOOR_ROOM = 7
    TWO_ROOM_CONNECTED = 8
    PILLAR_HALL = 9

    # Tập Validation (10 - 12)
    DOUBLE_BOTTLENECK = 10
    THREE_ROOM_OFFICE = 11
    COURTYARD_DYNAMIC_LANES = 12

    # Tập Testing - Unseen Topologies (13 - 15)
    H_SHAPED_COMPLEX = 13
    MULTI_ROOM_MAZE = 14
    CROWDED_PLAZA_GATES = 15


TOPOLOGY_NAMES: dict[int, str] = {
    1: "1: Open Area (Train)",
    2: "2: Straight Corridor (Train)",
    3: "3: Narrow Passage (Train)",
    4: "4: L-Corner (Train)",
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