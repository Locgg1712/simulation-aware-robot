# Phase 2: Biến thể hóa kích thước phòng, vị trí tường/cửa
# environment/map_generator.py
import random
from objects.static_object import StaticObject, ShapeType
from objects.semi_static_object import SemiStaticObject, SemiStaticState
from .topology import TopologyID


class MapGenerator:
    """
    Bộ sinh bản đồ theo thủ tục (Procedural Map Generator) cho 15 Topology Templates.
    Trả về:
    - static_objects: danh sách tường bao, tường ngăn, cột, chướng ngại vật.
    - semi_static_objects: danh sách cửa tự động / cổng barrier.
    - start_hint, goal_hint: vùng tọa độ gợi ý cho Robot và Goal.
    """

    def __init__(self, width: float = 20.0, height: float = 20.0):
        self.width = float(width)
        self.height = float(height)
        self.wall_t = 0.25

    def generate(
        self, topology_id: int
    ) -> tuple[
        list[StaticObject],
        list[SemiStaticObject],
        tuple[float, float],
        tuple[float, float],
    ]:
        static_objs: list[StaticObject] = []
        semi_objs: list[SemiStaticObject] = []
        obj_id = 1

        # Luôn tạo 4 bức tường bao quanh bản đồ 20m x 20m
        W, H, t = self.width, self.height, self.wall_t
        borders = [
            ("wall_top", 0.0, 0.0, W, t),
            ("wall_bottom", 0.0, H - t, W, t),
            ("wall_left", 0.0, 0.0, t, H),
            ("wall_right", W - t, 0.0, t, H),
        ]
        for name, rx, ry, rw, rh in borders:
            static_objs.append(
                StaticObject(obj_id, ShapeType.RECTANGLE, rx, ry, width=rw, height=rh, name=name)
            )
            obj_id += 1

        def add_rect(x: float, y: float, w: float, h: float, name: str = "wall"):
            nonlocal obj_id
            static_objs.append(
                StaticObject(obj_id, ShapeType.RECTANGLE, x, y, width=w, height=h, name=f"{name}_{obj_id}")
            )
            obj_id += 1

        def add_circle(cx: float, cy: float, r: float, name: str = "pillar"):
            nonlocal obj_id
            static_objs.append(
                StaticObject(obj_id, ShapeType.CIRCLE, cx, cy, radius=r, name=f"{name}_{obj_id}")
            )
            obj_id += 1

        def add_door(
            x: float,
            y: float,
            w: float,
            h: float,
            init_state: SemiStaticState = SemiStaticState.CLOSED,
            closed_d: float = 4.0,
            open_d: float = 6.0,
            trigger_d: float = 3.5,
        ):
            nonlocal obj_id
            semi_objs.append(
                SemiStaticObject(
                    obj_id=obj_id,
                    x=x,
                    y=y,
                    width=w,
                    height=h,
                    initial_state=init_state,
                    closed_duration=closed_d,
                    opening_duration=1.2,
                    open_duration=open_d,
                    closing_duration=1.2,
                    trigger_distance=trigger_d,
                    name=f"door_{obj_id}",
                )
            )
            obj_id += 1

        tid = TopologyID(topology_id)
        start_hint = (2.2, 2.2)
        goal_hint = (17.8, 17.8)

        # ----------------------------------------------------------------------
        # TẬP TRAINING (TOPOLOGY 1 - 9)
        # ----------------------------------------------------------------------
        if tid == TopologyID.OPEN_AREA:
            for _ in range(7):
                cx = random.uniform(4.5, 15.5)
                cy = random.uniform(4.5, 15.5)
                if random.random() < 0.5:
                    add_circle(cx, cy, random.uniform(0.55, 0.85), "rock")
                else:
                    add_rect(cx - 0.8, cy - 0.6, random.uniform(1.2, 2.0), random.uniform(1.0, 1.6), "block")

        elif tid == TopologyID.STRAIGHT_CORRIDOR:
            y_top = random.uniform(6.2, 7.0)
            corridor_w = random.uniform(4.8, 5.8)
            add_rect(0.25, 0.25, 19.5, y_top, "corridor_north")
            add_rect(0.25, y_top + corridor_w, 19.5, 19.75 - (y_top + corridor_w), "corridor_south")
            start_hint = (2.0, y_top + corridor_w / 2.0)
            goal_hint = (18.0, y_top + corridor_w / 2.0)

        elif tid == TopologyID.NARROW_PASSAGE:
            add_rect(0.25, 0.25, 19.5, 5.5, "upper_wall")
            add_rect(0.25, 14.25, 19.5, 5.5, "lower_wall")
            # Nút thắt ở giữa chỉ rộng ~ 1.8m
            add_rect(8.5, 5.75, 3.0, 3.2, "choke_top")
            add_rect(8.5, 10.95, 3.0, 3.3, "choke_bottom")
            start_hint = (2.5, 10.0)
            goal_hint = (17.5, 10.0)

        elif tid == TopologyID.L_CORNER:
            add_rect(7.5, 0.25, 12.25, 12.0, "inner_L_block")
            start_hint = (3.5, 2.5)
            goal_hint = (17.5, 16.0)

        elif tid == TopologyID.T_JUNCTION:
            add_rect(0.25, 0.25, 7.2, 11.5, "left_block")
            add_rect(12.55, 0.25, 7.2, 11.5, "right_block")
            start_hint = (10.0, 2.0)
            goal_hint = (2.5, 15.5) if random.random() < 0.5 else (17.5, 15.5)

        elif tid == TopologyID.CROSS_INTERSECTION:
            add_rect(0.25, 0.25, 7.2, 7.2, "nw_block")
            add_rect(12.55, 0.25, 7.2, 7.2, "ne_block")
            add_rect(0.25, 12.55, 7.2, 7.2, "sw_block")
            add_rect(12.55, 12.55, 7.2, 7.2, "se_block")
            start_hint = (2.0, 10.0)
            goal_hint = (18.0, 10.0)

        elif tid == TopologyID.SINGLE_DOOR_ROOM:
            # Tường chia đôi bản đồ kèm 1 cửa tự động ở giữa
            add_rect(9.6, 0.25, 0.6, 8.0, "room_wall_top")
            add_rect(9.6, 11.25, 0.6, 8.5, "room_wall_bottom")
            add_door(9.65, 8.25, 0.5, 3.0, SemiStaticState.CLOSED, closed_d=3.5, open_d=6.5)
            start_hint = (3.0, 10.0)
            goal_hint = (17.0, 10.0)

        elif tid == TopologyID.TWO_ROOM_CONNECTED:
            add_rect(6.2, 0.25, 0.5, 7.5, "wall_1_top")
            add_rect(6.2, 10.8, 0.5, 8.95, "wall_1_bot")
            add_rect(13.3, 0.25, 0.5, 9.0, "wall_2_top")
            add_rect(13.3, 12.3, 0.5, 7.45, "wall_2_bot")
            add_circle(10.0, 6.0, 0.65, "pillar")
            start_hint = (2.5, 10.0)
            goal_hint = (17.5, 10.0)

        elif tid == TopologyID.PILLAR_HALL:
            for r_y in (5.5, 10.0, 14.5):
                for c_x in (5.5, 10.0, 14.5):
                    jx = random.uniform(-0.35, 0.35)
                    jy = random.uniform(-0.35, 0.35)
                    add_circle(c_x + jx, r_y + jy, 0.65, "hall_pillar")
            start_hint = (2.0, 2.0)
            goal_hint = (18.0, 18.0)

        # ----------------------------------------------------------------------
        # TẬP VALIDATION (TOPOLOGY 10 - 12)
        # ----------------------------------------------------------------------
        elif tid == TopologyID.DOUBLE_BOTTLENECK:
            add_rect(6.5, 0.25, 0.5, 8.0, "b1_top")
            add_rect(6.5, 11.25, 0.5, 8.5, "b1_bot")
            add_door(6.55, 8.25, 0.4, 3.0, SemiStaticState.CLOSED, closed_d=3.0, open_d=6.0)

            add_rect(13.0, 0.25, 0.5, 8.0, "b2_top")
            add_rect(13.0, 11.25, 0.5, 8.5, "b2_bot")
            add_door(13.05, 8.25, 0.4, 3.0, SemiStaticState.OPEN, closed_d=3.5, open_d=6.0)
            start_hint = (2.5, 10.0)
            goal_hint = (17.5, 10.0)

        elif tid == TopologyID.THREE_ROOM_OFFICE:
            add_rect(0.25, 9.5, 7.0, 0.5, "office_h1")
            add_rect(10.5, 9.5, 9.25, 0.5, "office_h2")
            add_rect(9.5, 0.25, 0.5, 6.5, "office_v1")
            add_door(7.25, 9.55, 3.25, 0.4, SemiStaticState.OPEN, closed_d=3.0, open_d=7.0)
            start_hint = (3.0, 3.0)
            goal_hint = (16.5, 16.0)

        elif tid == TopologyID.COURTYARD_DYNAMIC_LANES:
            add_rect(4.5, 4.5, 2.2, 2.2, "island_nw")
            add_rect(13.3, 4.5, 2.2, 2.2, "island_ne")
            add_rect(4.5, 13.3, 2.2, 2.2, "island_sw")
            add_rect(13.3, 13.3, 2.2, 2.2, "island_se")
            add_circle(10.0, 10.0, 0.85, "center_fountain")
            start_hint = (2.0, 10.0)
            goal_hint = (18.0, 10.0)

        # ----------------------------------------------------------------------
        # TẬP TESTING - UNSEEN TOPOLOGIES (TOPOLOGY 13 - 15)
        # ----------------------------------------------------------------------
        elif tid == TopologyID.H_SHAPED_COMPLEX:
            add_rect(5.5, 3.8, 9.0, 4.2, "h_top_block")
            add_rect(5.5, 12.0, 9.0, 4.2, "h_bot_block")
            add_door(9.75, 8.0, 0.5, 4.0, SemiStaticState.CLOSED, closed_d=4.0, open_d=6.0)
            start_hint = (2.5, 10.0)
            goal_hint = (17.5, 10.0)

        elif tid == TopologyID.MULTI_ROOM_MAZE:
            add_rect(5.5, 0.25, 0.5, 13.5, "maze_w1")
            add_rect(10.5, 6.25, 0.5, 13.5, "maze_w2")
            add_rect(15.0, 0.25, 0.5, 13.5, "maze_w3")
            start_hint = (2.5, 2.5)
            goal_hint = (17.8, 17.5)

        elif tid == TopologyID.CROWDED_PLAZA_GATES:
            add_rect(9.6, 0.25, 0.6, 4.5, "plaza_w1")
            add_door(9.65, 4.75, 0.5, 3.0, SemiStaticState.OPEN, closed_d=3.5, open_d=6.5)
            add_rect(9.6, 7.75, 0.6, 4.5, "plaza_w2")
            add_door(9.65, 12.25, 0.5, 3.0, SemiStaticState.CLOSED, closed_d=3.5, open_d=6.5)
            add_rect(9.6, 15.25, 0.6, 4.5, "plaza_w3")
            add_circle(5.5, 10.0, 0.7, "plaza_pillar_1")
            add_circle(14.5, 10.0, 0.7, "plaza_pillar_2")
            start_hint = (2.2, 10.0)
            goal_hint = (17.8, 10.0)

        return static_objs, semi_objs, start_hint, goal_hint