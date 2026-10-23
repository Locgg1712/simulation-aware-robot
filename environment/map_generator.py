# environment/map_generator.py
import random
from objects.static_object import StaticObject, ShapeType
from objects.semi_static_object import SemiStaticObject, SemiStaticState
from .topology import TopologyID


class MapGenerator:
    """
    Bộ sinh bản đồ cho 4 Map Stardew Valley (Beach Farm, Hill-top Farm, Pelican Town, Forest Ponds)
    và sinh Không gian Nội thất (Indoor House Room) khi Robot bước vào cửa nhà.
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

        def add_circle(cx: float, cy: float, r: float, name: str = "tree"):
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
            init_state: SemiStaticState = SemiStaticState.OPEN,
            closed_d: float = 3.5,
            open_d: float = 7.0,
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
                    opening_duration=1.0,
                    open_duration=open_d,
                    closing_duration=1.0,
                    trigger_distance=trigger_d,
                    name=f"door_{obj_id}",
                )
            )
            obj_id += 1

        tid = int(topology_id)
        start_hint = (3.5, 9.5)
        goal_hint = (15.5, 9.5)

        # ======================================================================
        # MAP 1: BEACH & ISLAND FARM (Ảnh 1 - Biển xanh, bãi cát, 2 nhà gỗ, đảo)
        # ======================================================================
        if tid == 1:
            # Vùng nước biển rìa trái & góc dưới (chặn vật lý để Robot đi trên đất liền/cầu)
            add_rect(0.25, 6.2, 2.6, 13.5, "water_sea_left")
            add_rect(2.85, 16.5, 4.5, 3.25, "water_sea_bottom")
            # Hồ nước lớn phía nam & Ao nhỏ ở giữa
            add_rect(11.2, 15.2, 3.8, 3.6, "water_pond_south")
            add_rect(10.8, 7.2, 1.5, 1.5, "water_pond_center")

            # Ngôi nhà 1: Barn & Nhà kính nhỏ góc tây bắc
            add_rect(2.4, 2.2, 2.6, 2.1, "house_Barn_NW")
            # Ngôi nhà 2: Farmhouse chính ở trung tâm bắc
            add_rect(6.8, 1.8, 2.8, 2.2, "house_Beach_Farmhouse")
            # Ngôi nhà 3: Cabin gỗ bên bờ cát phía đông
            add_rect(15.2, 6.0, 2.8, 2.3, "house_East_Cabin")

            # Cây anh đào hồng (cherry) & cây thông/sồi rải rác như Ảnh 1
            trees_m1 = [
                (4.8, 12.8, 0.55, "cherry_tree"),
                (4.6, 15.0, 0.55, "cherry_tree"),
                (10.2, 7.8, 0.55, "cherry_tree"),
                (18.0, 9.8, 0.55, "cherry_tree"),
                (10.5, 2.5, 0.50, "pine_tree"),
                (12.2, 2.8, 0.50, "oak_tree"),
                (14.0, 2.4, 0.50, "pine_tree"),
                (16.0, 2.6, 0.50, "oak_tree"),
                (13.2, 10.5, 0.55, "oak_tree"),
                (14.5, 11.2, 0.55, "pine_tree"),
                (7.8, 12.5, 0.50, "pine_tree"),
            ]
            for cx, cy, r, tname in trees_m1:
                add_circle(cx, cy, r, tname)

            start_hint = (4.2, 5.2)
            goal_hint = (16.6, 9.2)

        # ======================================================================
        # MAP 2: HILL-TOP FARM & GREENHOUSE (Ảnh 2 - Đường đá, Nhà kính, Silo, Cối xay)
        # ======================================================================
        elif tid == 2:
            # 2 Tháp Silo đỏ góc tây bắc + 1 Silo cạnh nhà chính
            add_circle(1.4, 2.2, 0.55, "silo_1")
            add_circle(2.5, 2.2, 0.55, "silo_2")
            add_circle(12.6, 3.8, 0.55, "silo_3")

            # Nhà Kính (Greenhouse) lớn bên trái
            add_rect(2.6, 3.6, 2.6, 3.2, "greenhouse_main")

            # Cối xay gió (Windmill) ở giữa bắc
            add_rect(9.2, 2.8, 1.4, 2.4, "windmill_tower")

            # Nhà kho gỗ (Log Shed) & Nhà chính (Main Farmhouse) góc đông bắc
            add_rect(11.2, 4.8, 2.3, 2.2, "house_Log_Shed")
            add_rect(13.8, 4.3, 3.2, 2.6, "house_Hilltop_Farmhouse")

            # Cụm Chuồng trại mái đỏ (Coop & Red Barn) phía nam đường đá
            add_rect(7.6, 12.6, 2.3, 2.2, "house_Red_Coop")
            add_rect(10.2, 13.4, 2.7, 2.4, "house_Red_Barn")

            # Hàng rào gỗ dọc theo trục đường đá trung tâm & cổng tự động
            add_rect(5.8, 11.2, 3.8, 0.35, "fence_center_left")
            add_door(9.6, 11.2, 2.2, 0.35, SemiStaticState.OPEN)
            add_rect(11.8, 11.2, 2.2, 0.35, "fence_center_right")

            # Cây cối trang trí trên đồi
            add_circle(8.3, 1.4, 0.60, "cherry_tree")
            add_circle(17.2, 4.5, 0.55, "oak_tree")
            add_circle(13.8, 13.8, 0.55, "oak_tree")

            start_hint = (4.5, 10.0)
            goal_hint = (15.4, 8.2)

        # ======================================================================
        # MAP 3: PELICAN TOWN & RIVER (Ảnh 3 - Quảng trường, Dòng sông, 2 Cầu, JojaMart)
        # ======================================================================
        elif tid == 3:
            # Dòng sông chảy dọc từ Bắc xuống Nam ở x = [11.6 .. 13.4], chừa 2 Cây Cầu ở y=4.2..5.8 và y=16.2..17.8
            add_rect(11.6, 0.25, 1.7, 3.8, "water_river_north")
            add_rect(11.6, 5.9, 1.7, 10.2, "water_river_mid")
            add_rect(11.6, 17.9, 1.7, 1.85, "water_river_south")

            # Phòng khám Harvey & Cửa hàng Tạp hóa Pierre (Góc bắc quảng trường)
            add_rect(5.5, 1.8, 3.2, 2.4, "house_Pierres_Store")

            # Nhà xanh góc tây bắc bên phải quảng trường
            add_rect(9.1, 4.2, 2.0, 2.0, "house_River_Cottage")

            # Quán Saloon ở ngay cạnh phải quảng trường
            add_rect(6.6, 7.2, 2.1, 2.1, "house_Stardrop_Saloon")

            # 2 Ngôi nhà góc tây nam (Nhà xanh dương & Nhà cam)
            add_rect(1.2, 11.5, 2.0, 2.2, "house_Blue_Cabin")
            add_rect(3.4, 12.5, 2.1, 2.2, "house_Haley_House")

            # Biệt thự Thị trưởng Lewis (Mayor's Manor) ở giữa nam
            add_rect(9.0, 11.2, 2.2, 2.3, "house_Mayors_Manor")

            # Bên kia bờ sông (Bờ Đông): Siêu thị JojaMart (Bắc) & Lò rèn / Bảo tàng (Nam)
            add_rect(14.8, 1.2, 3.4, 2.5, "jojamart_building")
            add_rect(15.2, 11.0, 2.1, 2.0, "house_Blacksmith")
            add_rect(16.2, 14.2, 2.3, 2.1, "house_Museum")

            # Cây xanh & Hoa anh đào trong thị trấn
            town_trees = [
                (1.2, 6.2, 0.50, "oak_tree"),
                (2.8, 8.8, 0.50, "oak_tree"),
                (4.2, 17.2, 0.55, "cherry_tree"),
                (8.5, 15.8, 0.50, "oak_tree"),
                (15.8, 7.2, 0.55, "cherry_tree"),
                (17.5, 8.2, 0.55, "cherry_tree"),
                (19.0, 10.5, 0.55, "cherry_tree"),
            ]
            for cx, cy, r, tname in town_trees:
                add_circle(cx, cy, r, tname)

            start_hint = (4.5, 8.5)
            goal_hint = (14.5, 13.8)

        # ======================================================================
        # MAP 4: FOUR CORNERS & 3 FISH PONDS (Ảnh 4 - Đảo Nhà kính, 3 Hồ cá, Chuồng đỏ)
        # ======================================================================
        elif tid == 4:
            # Sông/Hồ nước rìa tây chia tách đảo Nhà Kính
            add_rect(0.25, 8.8, 2.2, 10.9, "water_west_channel")

            # Nhà Kính trên bán đảo góc tây bắc
            add_rect(1.4, 3.2, 2.4, 2.8, "greenhouse_island")

            # Silo đỏ & Nhà chính (Forest Farmhouse) ở góc đông bắc
            add_circle(10.5, 3.2, 0.55, "silo_forest")
            add_rect(11.6, 2.4, 3.2, 2.4, "house_Forest_Farmhouse")

            # Nhà kho nhỏ ở giữa bắc
            add_rect(8.2, 4.8, 1.8, 1.9, "house_Garden_Shed")

            # 2 Chuồng gia súc mái đỏ (Twin Barns) + 1 Coop ở góc tây nam
            add_rect(3.0, 12.2, 2.2, 2.1, "house_West_Barn")
            add_rect(7.6, 12.0, 1.8, 1.9, "house_Mid_Coop")
            add_rect(9.6, 12.2, 2.2, 2.1, "house_East_Barn")

            # Nhà gỗ nhỏ phía nam & Nhà ven hồ cá
            add_rect(12.8, 15.6, 2.1, 2.1, "house_South_Cottage")
            add_rect(15.8, 15.8, 2.0, 2.0, "house_Pond_Cabin")

            # 3 Hồ nuôi cá vuông viền đá ở góc đông nam
            add_rect(15.2, 13.8, 1.3, 1.3, "water_fishpond_1")
            add_rect(16.9, 14.0, 1.3, 1.3, "water_fishpond_2")
            add_rect(18.4, 14.2, 1.1, 1.3, "water_fishpond_3")

            # Rừng cây góc đông bắc & quanh nông trại
            forest_trees = [
                (16.2, 2.8, 0.55, "oak_tree"),
                (17.8, 3.5, 0.55, "pine_tree"),
                (16.8, 5.2, 0.55, "oak_tree"),
                (6.0, 4.2, 0.50, "oak_tree"),
                (11.8, 9.2, 0.50, "oak_tree"),
                (13.2, 9.2, 0.50, "oak_tree"),
            ]
            for cx, cy, r, tname in forest_trees:
                add_circle(cx, cy, r, tname)

            start_hint = (5.8, 8.2)
            goal_hint = (13.2, 6.2)

        # ======================================================================
        # CÁC TOPOLOGY TỪ 5 ĐẾN 15 (GIỮ NGUYÊN CHO BENCHMARK & RL)
        # ======================================================================
        elif tid == TopologyID.T_JUNCTION:
            add_rect(0.25, 0.25, 7.2, 11.5, "house_Left_Manor")
            add_rect(12.55, 0.25, 7.2, 11.5, "house_Right_Manor")
            start_hint, goal_hint = (10.0, 2.0), (17.5, 15.5)

        elif tid == TopologyID.CROSS_INTERSECTION:
            add_rect(0.25, 0.25, 7.2, 7.2, "house_NW")
            add_rect(12.55, 0.25, 7.2, 7.2, "house_NE")
            add_rect(0.25, 12.55, 7.2, 7.2, "house_SW")
            add_rect(12.55, 12.55, 7.2, 7.2, "house_SE")
            start_hint, goal_hint = (2.0, 10.0), (18.0, 10.0)

        elif tid == TopologyID.SINGLE_DOOR_ROOM:
            add_rect(9.6, 0.25, 0.6, 8.0, "room_wall_top")
            add_rect(9.6, 11.25, 0.6, 8.5, "room_wall_bottom")
            add_door(9.65, 8.25, 0.5, 3.0, SemiStaticState.CLOSED, closed_d=3.5, open_d=6.5)
            start_hint, goal_hint = (3.0, 10.0), (17.0, 10.0)

        elif tid == TopologyID.TWO_ROOM_CONNECTED:
            add_rect(6.2, 0.25, 0.5, 7.5, "wall_1_top")
            add_rect(6.2, 10.8, 0.5, 8.95, "wall_1_bot")
            add_rect(13.3, 0.25, 0.5, 9.0, "wall_2_top")
            add_rect(13.3, 12.3, 0.5, 7.45, "wall_2_bot")
            add_circle(10.0, 6.0, 0.65, "tree_center")
            start_hint, goal_hint = (2.5, 10.0), (17.5, 10.0)

        elif tid == TopologyID.PILLAR_HALL:
            for r_y in (5.5, 10.0, 14.5):
                for c_x in (5.5, 10.0, 14.5):
                    add_circle(c_x, r_y, 0.65, "oak_tree")
            start_hint, goal_hint = (2.0, 2.0), (18.0, 18.0)

        elif tid == TopologyID.DOUBLE_BOTTLENECK:
            add_rect(6.5, 0.25, 0.5, 8.0, "b1_top")
            add_rect(6.5, 11.25, 0.5, 8.5, "b1_bot")
            add_door(6.55, 8.25, 0.4, 3.0, SemiStaticState.CLOSED, closed_d=3.0, open_d=6.0)
            add_rect(13.0, 0.25, 0.5, 8.0, "b2_top")
            add_rect(13.0, 11.25, 0.5, 8.5, "b2_bot")
            add_door(13.05, 8.25, 0.4, 3.0, SemiStaticState.OPEN, closed_d=3.5, open_d=6.0)
            start_hint, goal_hint = (2.5, 10.0), (17.5, 10.0)

        elif tid == TopologyID.THREE_ROOM_OFFICE:
            add_rect(0.25, 9.5, 7.0, 0.5, "office_h1")
            add_rect(10.5, 9.5, 9.25, 0.5, "office_h2")
            add_rect(9.5, 0.25, 0.5, 6.5, "office_v1")
            add_door(7.25, 9.55, 3.25, 0.4, SemiStaticState.OPEN, closed_d=3.0, open_d=7.0)
            start_hint, goal_hint = (3.0, 3.0), (16.5, 16.0)

        elif tid == TopologyID.COURTYARD_DYNAMIC_LANES:
            add_rect(4.2, 4.2, 2.6, 2.4, "house_NW_Cottage")
            add_rect(13.2, 4.2, 2.6, 2.4, "house_NE_Cottage")
            add_rect(4.2, 13.2, 2.6, 2.4, "house_SW_Cottage")
            add_rect(13.2, 13.2, 2.6, 2.4, "house_SE_Cottage")
            add_circle(10.0, 10.0, 0.85, "cherry_tree")
            start_hint, goal_hint = (2.0, 10.0), (18.0, 10.0)

        elif tid == TopologyID.H_SHAPED_COMPLEX:
            add_rect(5.5, 3.8, 9.0, 4.2, "house_H_North")
            add_rect(5.5, 12.0, 9.0, 4.2, "house_H_South")
            add_door(9.75, 8.0, 0.5, 4.0, SemiStaticState.OPEN, closed_d=4.0, open_d=6.0)
            start_hint, goal_hint = (2.5, 10.0), (17.5, 10.0)

        elif tid == TopologyID.MULTI_ROOM_MAZE:
            add_rect(5.5, 0.25, 0.5, 13.5, "maze_w1")
            add_rect(10.5, 6.25, 0.5, 13.5, "maze_w2")
            add_rect(15.0, 0.25, 0.5, 13.5, "maze_w3")
            start_hint, goal_hint = (2.5, 2.5), (17.8, 17.5)

        else:
            add_rect(9.6, 0.25, 0.6, 4.5, "plaza_w1")
            add_door(9.65, 4.75, 0.5, 3.0, SemiStaticState.OPEN, closed_d=3.5, open_d=6.5)
            add_rect(9.6, 7.75, 0.6, 4.5, "plaza_w2")
            add_door(9.65, 12.25, 0.5, 3.0, SemiStaticState.CLOSED, closed_d=3.5, open_d=6.5)
            add_rect(9.6, 15.25, 0.6, 4.5, "plaza_w3")
            add_circle(5.5, 10.0, 0.7, "cherry_tree")
            add_circle(14.5, 10.0, 0.7, "cherry_tree")
            start_hint, goal_hint = (2.2, 10.0), (17.8, 10.0)

        return static_objs, semi_objs, start_hint, goal_hint

    def generate_house_interior(
        self, house_id: int = 1, house_name: str = "Stardew Cottage"
    ) -> tuple[
        list[StaticObject],
        tuple[float, float, float, float],
        tuple[float, float],
        tuple[float, float],
        tuple[float, float],
    ]:
        """
        Tạo bản đồ Nội thất bên trong Ngôi Nhà (Indoor Room) nằm ở trung tâm màn hình.
        Vùng bên ngoài (ngoài khung room_bounds) sẽ được khóa vật lý và làm tối đen hoàn toàn.
        Trả về:
        - interior_static_objs: tường bao căn phòng + bàn ghế, giường, tủ sách, lò sưởi.
        - room_bounds: (rx, ry, rw, rh) = (4.5, 4.0, 11.0, 12.0) (mét).
        - entry_spawn: tọa độ Robot xuất hiện ngay lối vào (10.0, 14.6).
        - exit_portal: tọa độ thảm chùi chân lối ra ở mép dưới phòng (10.0, 15.4).
        - indoor_goal: tọa độ điểm giao hàng bên trong nhà.
        """
        rx, ry, rw, rh = 4.5, 4.0, 11.0, 12.0
        objs: list[StaticObject] = []
        oid = 100

        # 4 Khối tường dày bao quanh căn phòng (chặn hoàn toàn vùng tối bên ngoài)
        outer_walls = [
            ("indoor_void_top", 0.0, 0.0, self.width, ry),
            ("indoor_void_bottom", 0.0, ry + rh, self.width, self.height - (ry + rh)),
            ("indoor_void_left", 0.0, ry, rx, rh),
            ("indoor_void_right", rx + rw, ry, self.width - (rx + rw), rh),
        ]
        for name, x, y, w, h in outer_walls:
            objs.append(StaticObject(oid, ShapeType.RECTANGLE, x, y, width=w, height=h, name=name))
            oid += 1

        # Nội thất bên trong căn phòng (bàn gỗ, kệ sách, lò sưởi, giường, quầy bếp)
        # Bố cục thay đổi nhẹ theo house_id
        objs.append(
            StaticObject(oid, ShapeType.RECTANGLE, rx + 0.6, ry + 0.5, width=2.4, height=1.1, name="furniture_bookshelf")
        )
        oid += 1
        objs.append(
            StaticObject(oid, ShapeType.RECTANGLE, rx + 4.3, ry + 0.4, width=2.2, height=1.0, name="furniture_fireplace")
        )
        oid += 1
        objs.append(
            StaticObject(oid, ShapeType.RECTANGLE, rx + rw - 2.8, ry + 0.8, width=2.1, height=2.4, name="furniture_bed")
        )
        oid += 1

        # Bàn trà / Bàn ăn ở giữa lệch trái hoặc phải
        if house_id % 2 == 0:
            objs.append(
                StaticObject(oid, ShapeType.RECTANGLE, rx + 2.0, ry + 4.8, width=2.4, height=1.6, name="furniture_table")
            )
            indoor_goal = (rx + 7.8, ry + 4.2)
        else:
            objs.append(
                StaticObject(oid, ShapeType.RECTANGLE, rx + 6.4, ry + 5.0, width=2.4, height=1.6, name="furniture_table")
            )
            indoor_goal = (rx + 3.0, ry + 4.2)
        oid += 1

        # Chậu cây cảnh góc phòng
        objs.append(StaticObject(oid, ShapeType.CIRCLE, rx + 1.1, ry + rh - 1.2, radius=0.45, name="furniture_plant_left"))
        oid += 1
        objs.append(StaticObject(oid, ShapeType.CIRCLE, rx + rw - 1.1, ry + rh - 1.2, radius=0.45, name="furniture_plant_right"))

        entry_spawn = (rx + rw / 2.0, ry + rh - 1.3)
        exit_portal = (rx + rw / 2.0, ry + rh - 0.55)
        return objs, (rx, ry, rw, rh), entry_spawn, exit_portal, indoor_goal