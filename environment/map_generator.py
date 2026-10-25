# environment/map_generator.py
import random
from objects.static_object import StaticObject, ShapeType
from objects.semi_static_object import SemiStaticObject, SemiStaticState
from .topology import TopologyID


class MapGenerator:
    """
    Bộ sinh bản đồ đồng bộ trực tiếp với 4 Bản đồ Ngoài trời + Nội thất Map 5 của trò chơi FarmBot Town (`game/maps.py`):
    - Map 1 (tid=1): Quảng Trường Thị Trấn Pelican, Dòng Sông Uốn Lượn, 2 Cây Cầu (Cầu Đá & Cầu Gỗ),
      Phòng Khám Harvey, Tạp Hóa Pierre, Quán Stardrop Saloon, Kho Vận JojaMart, Giếng Cổ.
    - Map 2 (tid=2): Đại Nông Trại (Grand Farmstead), Kênh Nước Tây, 2 Tháp Silo, Nhà Kính, Cối Xay Gió,
      Kho Nông Sản, Nhà Chính, 6 Thửa Ruộng Có Rào, Vườn Cây Ăn Quả, Chuồng Gia Súc & Ao Cá.
    - Map 3 (tid=3): Đảo Rừng Xanh & Bến Hồ Câu Cá (Lakeside Pier), Hồ Nước Lớn, Đảo Bắc & Đảo Nam,
      3 Cây Cầu Gỗ / Cầu Tàu vượt hồ, Chòi Ngư Cụ & Ruộng Ven Hồ.
    - Map 4 (tid=4): Khu Dân Cư & Xưởng Robot (Residential Village), 4 Ngôi Nhà Cư Dân (Gus, Robin, Willy, Lewis),
      Xưởng & Nhà Robot Số 5 (Đông-Nam), Vườn Gia Đình, Giếng & Hồ Cá.
    - Topologies 5..15: Các cấu hình hành lang, nút giao, cửa bán tĩnh phục vụ huấn luyện và đánh giá tổng quát.
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
                StaticObject(
                    obj_id, ShapeType.RECTANGLE, rx, ry, width=rw, height=rh, name=name
                )
            )
            obj_id += 1

        def add_rect(x: float, y: float, w: float, h: float, name: str = "wall"):
            nonlocal obj_id
            static_objs.append(
                StaticObject(
                    obj_id,
                    ShapeType.RECTANGLE,
                    x,
                    y,
                    width=w,
                    height=h,
                    name=f"{name}_{obj_id}",
                )
            )
            obj_id += 1

        def add_circle(cx: float, cy: float, r: float, name: str = "tree"):
            nonlocal obj_id
            static_objs.append(
                StaticObject(
                    obj_id,
                    ShapeType.CIRCLE,
                    cx,
                    cy,
                    radius=r,
                    name=f"{name}_{obj_id}",
                )
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
        # GAME MAP 1: QUẢNG TRƯỜNG THỊ TRẤN PELICAN & 2 CẦU QUA SÔNG (game/maps.py)
        # ======================================================================
        if tid == 1:
            # Dòng sông phía Đông (x = 13.8..15.3) với 2 Cây Cầu:
            # - Cầu đá trung tâm tại y = [9.0 .. 11.4]
            # - Cầu gỗ phía Nam tại y = [15.2 .. 17.0]
            add_rect(13.8, 0.25, 1.5, 8.75, "water_river_north")
            add_rect(13.8, 11.4, 1.5, 3.8, "water_river_mid")
            add_rect(13.8, 17.0, 1.5, 2.75, "water_river_south")

            # 4 Tòa nhà chính của Map 1:
            # 1) Phòng Khám Y Tế Bác sĩ Harvey (Tây-Bắc)
            add_rect(2.0, 2.2, 2.6, 2.2, "house_Clinic_Harvey")
            # 2) Tạp Hóa Pierre (Bắc Quảng trường)
            add_rect(5.6, 2.2, 2.8, 2.2, "house_Pierres_Store")
            # 3) Quán Nước Stardrop Saloon (Đông-Bắc Quảng trường, trước bờ sông)
            add_rect(10.4, 2.6, 2.6, 2.2, "house_Stardrop_Saloon")
            # 4) Trung Tâm Kho Vận JojaMart (Bờ Đông bên kia sông)
            add_rect(16.2, 2.4, 2.6, 2.4, "house_JojaMart_Depot")

            # Giếng cổ giữa Quảng trường + Vườn Dâu Tây & Bắp Cải Cộng Đồng
            add_circle(8.0, 10.2, 0.65, "well_roof_plaza")
            add_rect(1.2, 12.6, 2.4, 2.0, "fence_town_strawberry")
            add_rect(16.4, 12.4, 2.2, 1.9, "fence_town_cabbage")

            # Cây xanh trang trí quanh thị trấn
            for cx, cy, r, tname in [
                (1.6, 8.2, 0.48, "cherry_tree"),
                (4.0, 12.2, 0.48, "oak_tree"),
                (12.2, 14.0, 0.48, "cherry_tree"),
                (18.2, 8.4, 0.48, "cherry_tree"),
            ]:
                add_circle(cx, cy, r, tname)

            # Các cặp điểm xuất phát - đích mô phỏng nhiệm vụ thực tế trên Map 1
            m1_routes = [
                ((1.8, 10.2), (17.2, 6.2)),   # Cổng Tây (Map 4) -> Qua cầu đá -> JojaMart
                ((8.8, 1.6), (17.5, 10.2)),   # Cổng Bắc (Map 2) -> Cổng Đông (Map 3)
                ((3.3, 5.2), (11.6, 5.6)),    # Phòng khám Harvey -> Quán Saloon (Cô Emily)
                ((6.8, 5.2), (17.0, 15.8)),   # Tạp hóa Pierre -> Qua cầu gỗ Nam -> Bờ Đông
                ((17.2, 6.2), (3.3, 5.2)),    # JojaMart -> Phòng khám Harvey
            ]
            start_hint, goal_hint = random.choice(m1_routes)

        # ======================================================================
        # GAME MAP 2: ĐẠI NÔNG TRẠI, 6 RUỘNG RÀO & VƯỜN QUẢ (game/maps.py)
        # ======================================================================
        elif tid == 2:
            # Kênh nước tưới tiêu dọc rìa Tây
            add_rect(0.25, 1.5, 1.1, 17.0, "water_west_canal")

            # Cụm công trình nông trại phía Bắc: Silo, Nhà Kính, Cối Xay Gió, Kho & Nhà Chính
            add_circle(2.4, 2.6, 0.50, "silo_1")
            add_circle(3.5, 2.6, 0.50, "silo_2")
            add_rect(4.6, 2.0, 2.4, 2.2, "greenhouse_main")
            add_rect(7.8, 2.0, 1.4, 2.2, "windmill_tower")
            add_rect(10.8, 2.0, 2.4, 2.2, "house_Farm_Shed")
            add_rect(14.2, 2.0, 2.8, 2.2, "house_Main_Farmhouse")

            # 6 Thửa ruộng nông sản có rào chắn (nằm ở nửa Đông, chừa các lối đi 1.8m-2.2m)
            add_rect(11.0, 8.8, 2.2, 2.1, "fence_crop_strawberry")
            add_rect(14.2, 8.8, 2.2, 2.1, "fence_crop_pumpkin")
            add_rect(11.0, 13.8, 2.2, 2.1, "fence_crop_tomato")
            add_rect(14.2, 13.8, 2.2, 2.1, "fence_crop_carrot")

            # Chuồng Gà, Chuồng Bò & Ao Cá góc Nam
            add_rect(2.6, 15.8, 2.2, 2.0, "house_Red_Coop")
            add_rect(5.4, 15.8, 2.4, 2.1, "house_Red_Barn")
            add_rect(17.0, 16.5, 1.8, 1.8, "water_farm_fishpond")

            # Cổng bán tĩnh trên trục đường nông trại
            add_door(8.8, 9.0, 0.4, 2.4, SemiStaticState.OPEN, closed_d=2.5, open_d=7.5)

            # Vườn cây ăn quả (Táo, Cam, Đào) bên trái trung tâm
            for cx, cy in [(3.2, 11.2), (5.5, 11.2), (7.6, 11.2)]:
                add_circle(cx, cy, 0.48, "fruit_tree")

            m2_routes = [
                ((9.5, 18.2), (15.5, 5.2)),   # Cổng Nam (từ Map 1) -> Nhà Chính Nông Trại
                ((8.2, 6.8), (13.6, 12.2)),   # Quầy Hạt Giống Caroline -> Giữa các thửa ruộng
                ((2.8, 6.8), (17.6, 12.2)),   # Đường Tây Nông Trại -> Lối đi ruộng Đông
                ((15.5, 5.2), (4.2, 13.8)),   # Nhà Chính -> Vườn Cây Ăn Quả / Chuồng Trại
                ((12.0, 5.2), (9.5, 18.2)),   # Kho Nông Sản Marnie -> Cổng Nam
            ]
            start_hint, goal_hint = random.choice(m2_routes)

        # ======================================================================
        # GAME MAP 3: ĐẢO RỪNG XANH, HỒ LỚN & 3 CẦU GỖ CÂU CÁ (game/maps.py)
        # ======================================================================
        elif tid == 3:
            # Hồ nước lớn chia cắt bờ Tây (x < 8.6) với Đảo Bắc, Cầu Tàu Giữa và Đảo Nam (x > 12.2)
            # Chừa 3 Cây Cầu Gỗ ở:
            # - Cầu Bắc: y = [4.2 .. 6.0]
            # - Cầu Tàu Trung Tâm: y = [9.4 .. 11.2]
            # - Cầu Nam: y = [14.4 .. 16.2]
            add_rect(8.6, 0.25, 3.6, 3.95, "water_lake_north")
            add_rect(8.6, 6.0, 3.6, 3.4, "water_lake_upper_mid")
            add_rect(8.6, 11.2, 3.6, 3.2, "water_lake_lower_mid")
            add_rect(8.6, 16.2, 3.6, 3.55, "water_lake_south")

            # Vùng nước giữa Đảo Bắc và Đảo Nam ở phía Đông (x = 12.2..19.75)
            add_rect(12.2, 7.2, 7.55, 2.0, "water_east_channel_1")
            add_rect(12.2, 11.4, 7.55, 2.6, "water_east_channel_2")

            # Chòi Ngư Cụ Ven Hồ & Ruộng Bắp Cải bờ Tây
            add_rect(2.4, 3.6, 2.4, 2.1, "house_Fisher_Shed")
            add_rect(1.6, 12.2, 2.4, 1.8, "fence_lake_cabbage")

            # Cây rừng & tảng đá trên bờ Tây và trên 2 Đảo
            for cx, cy, r in [
                (1.8, 2.2, 0.48),
                (6.8, 3.2, 0.45),
                (6.8, 13.8, 0.48),
                (17.2, 3.8, 0.48),
                (16.8, 16.2, 0.48),
            ]:
                add_circle(cx, cy, r, "pine_tree")

            m3_routes = [
                ((1.8, 10.2), (16.2, 10.2)),  # Cổng Tây (Map 1) -> Mũi Cầu Tàu Trung Tâm
                ((1.8, 10.2), (15.2, 5.0)),   # Cổng Tây -> Qua Cầu Bắc -> Đảo Hoa Anh Đào Bắc
                ((3.6, 6.6), (15.2, 15.2)),   # Chòi Ngư Cụ -> Qua Cầu Nam -> Đảo Câu Cá Nam
                ((15.2, 5.0), (15.2, 15.2)),  # Đảo Bắc -> Về bờ Tây -> Sang Đảo Nam
                ((16.2, 10.2), (3.6, 6.6)),   # Cầu Tàu Trung Tâm -> Chòi Ngư Cụ
            ]
            start_hint, goal_hint = random.choice(m3_routes)

        # ======================================================================
        # GAME MAP 4: KHU DÂN CƯ 4 DINH THỰ & XƯỞNG ROBOT SỐ 5 (game/maps.py)
        # ======================================================================
        elif tid == 4:
            # Suối nhỏ góc Tây-Nam
            add_rect(0.8, 16.8, 3.4, 2.4, "water_village_stream")

            # 4 Ngôi Nhà Cư Dân + Xưởng & Nhà Robot (Số 5):
            # 1) Nhà Đầu Bếp Gus (Tây-Bắc)
            add_rect(3.4, 3.2, 2.6, 2.2, "house_Gus_Kitchen")
            # 2) Nhà Thợ Mộc Robin (Đông-Bắc)
            add_rect(12.2, 3.2, 2.6, 2.2, "house_Robin_Carpentry")
            # 3) Nhà Ngư Phủ Willy (Tây-Nam)
            add_rect(3.6, 12.8, 2.6, 2.2, "house_Willy_Cabin")
            # 4) Dinh Thự Thị Trưởng Lewis (Nam Trung Tâm)
            add_rect(11.2, 12.8, 2.8, 2.3, "house_Lewis_Manor")
            # 5) Xưởng & Nhà Robot (Đông-Nam)
            add_rect(16.0, 12.8, 2.6, 2.3, "house_Robot_Workshop")

            # Vườn rau gia đình phía Bắc + Hồ cá & Giếng khu dân cư
            add_rect(6.8, 2.2, 2.2, 1.8, "fence_gus_tomato")
            add_rect(15.6, 2.2, 2.2, 1.8, "fence_robin_pumpkin")
            add_circle(9.0, 8.2, 0.55, "well_village")
            add_rect(7.6, 16.5, 2.2, 1.8, "water_village_fishpond")

            for cx, cy in [(1.8, 5.8), (10.2, 5.2), (18.2, 6.2), (1.8, 13.8)]:
                add_circle(cx, cy, 0.48, "oak_tree")

            m4_routes = [
                ((17.2, 16.0), (18.2, 9.8)),  # Cửa Xưởng Robot (Số 5) -> Cổng Đông (sang Map 1)
                ((17.2, 16.0), (4.7, 6.2)),   # Xưởng Robot -> Nhà Đầu Bếp Gus (Số 1)
                ((18.2, 9.8), (12.6, 15.8)),  # Cổng Đông -> Dinh Thự Thị Trưởng Lewis (Số 4)
                ((4.7, 6.2), (13.5, 6.2)),    # Nhà Gus -> Nhà Thợ Mộc Robin (Số 2)
                ((4.9, 15.8), (17.2, 16.0)),  # Nhà Willy (Số 3) -> Về Xưởng Robot Sạc Pin
            ]
            start_hint, goal_hint = random.choice(m4_routes)

        # ======================================================================
        # CÁC TOPOLOGY TỪ 5 ĐẾN 15 (GIỮ NGUYÊN CHO BENCHMARK & ĐÁNH GIÁ TỔNG QUÁT)
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
            add_door(
                9.65, 8.25, 0.5, 3.0, SemiStaticState.CLOSED, closed_d=3.5, open_d=6.5
            )
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
            add_door(
                6.55, 8.25, 0.4, 3.0, SemiStaticState.CLOSED, closed_d=3.0, open_d=6.0
            )
            add_rect(13.0, 0.25, 0.5, 8.0, "b2_top")
            add_rect(13.0, 11.25, 0.5, 8.5, "b2_bot")
            add_door(
                13.05, 8.25, 0.4, 3.0, SemiStaticState.OPEN, closed_d=3.5, open_d=6.0
            )
            start_hint, goal_hint = (2.5, 10.0), (17.5, 10.0)

        elif tid == TopologyID.THREE_ROOM_OFFICE:
            add_rect(0.25, 9.5, 7.0, 0.5, "office_h1")
            add_rect(10.5, 9.5, 9.25, 0.5, "office_h2")
            add_rect(9.5, 0.25, 0.5, 6.5, "office_v1")
            add_door(
                7.25, 9.55, 3.25, 0.4, SemiStaticState.OPEN, closed_d=3.0, open_d=7.0
            )
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
            add_door(
                9.75, 8.0, 0.5, 4.0, SemiStaticState.OPEN, closed_d=4.0, open_d=6.0
            )
            start_hint, goal_hint = (2.5, 10.0), (17.5, 10.0)

        elif tid == TopologyID.MULTI_ROOM_MAZE:
            add_rect(5.5, 0.25, 0.5, 13.5, "maze_w1")
            add_rect(10.5, 6.25, 0.5, 13.5, "maze_w2")
            add_rect(15.0, 0.25, 0.5, 13.5, "maze_w3")
            start_hint, goal_hint = (2.5, 2.5), (17.8, 17.5)

        else:
            add_rect(9.6, 0.25, 0.6, 4.5, "plaza_w1")
            add_door(
                9.65, 4.75, 0.5, 3.0, SemiStaticState.OPEN, closed_d=3.5, open_d=6.5
            )
            add_rect(9.6, 7.75, 0.6, 4.5, "plaza_w2")
            add_door(
                9.65, 12.25, 0.5, 3.0, SemiStaticState.CLOSED, closed_d=3.5, open_d=6.5
            )
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
        Tạo bản đồ Nội thất bên trong Ngôi Nhà (Indoor Room - Map 5).
        """
        rx, ry, rw, rh = 4.5, 4.0, 11.0, 12.0
        objs: list[StaticObject] = []
        oid = 100

        outer_walls = [
            ("indoor_void_top", 0.0, 0.0, self.width, ry),
            ("indoor_void_bottom", 0.0, ry + rh, self.width, self.height - (ry + rh)),
            ("indoor_void_left", 0.0, ry, rx, rh),
            ("indoor_void_right", rx + rw, ry, self.width - (rx + rw), rh),
        ]
        for name, x, y, w, h in outer_walls:
            objs.append(
                StaticObject(oid, ShapeType.RECTANGLE, x, y, width=w, height=h, name=name)
            )
            oid += 1

        objs.append(
            StaticObject(
                oid,
                ShapeType.RECTANGLE,
                rx + 0.6,
                ry + 0.5,
                width=2.4,
                height=1.1,
                name="furniture_bookshelf",
            )
        )
        oid += 1
        objs.append(
            StaticObject(
                oid,
                ShapeType.RECTANGLE,
                rx + 4.3,
                ry + 0.4,
                width=2.2,
                height=1.0,
                name="furniture_fireplace",
            )
        )
        oid += 1
        objs.append(
            StaticObject(
                oid,
                ShapeType.RECTANGLE,
                rx + rw - 2.8,
                ry + 0.8,
                width=2.1,
                height=2.4,
                name="furniture_bed",
            )
        )
        oid += 1

        if house_id % 2 == 0:
            objs.append(
                StaticObject(
                    oid,
                    ShapeType.RECTANGLE,
                    rx + 2.0,
                    ry + 4.8,
                    width=2.4,
                    height=1.6,
                    name="furniture_table",
                )
            )
            indoor_goal = (rx + 7.8, ry + 4.2)
        else:
            objs.append(
                StaticObject(
                    oid,
                    ShapeType.RECTANGLE,
                    rx + 6.4,
                    ry + 5.0,
                    width=2.4,
                    height=1.6,
                    name="furniture_table",
                )
            )
            indoor_goal = (rx + 3.0, ry + 4.2)
        oid += 1

        objs.append(
            StaticObject(
                oid,
                ShapeType.CIRCLE,
                rx + 1.1,
                ry + rh - 1.2,
                radius=0.45,
                name="furniture_plant_left",
            )
        )
        oid += 1
        objs.append(
            StaticObject(
                oid,
                ShapeType.CIRCLE,
                rx + rw - 1.1,
                ry + rh - 1.2,
                radius=0.45,
                name="furniture_plant_right",
            )
        )

        entry_spawn = (rx + rw / 2.0, ry + rh - 1.3)
        exit_portal = (rx + rw / 2.0, ry + rh - 0.55)
        return objs, (rx, ry, rw, rh), entry_spawn, exit_portal, indoor_goal
