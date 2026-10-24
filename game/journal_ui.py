# game/journal_ui.py
"""
Sổ Tay Thị Trấn & Menu Tổng Hợp FarmBot (Journal & Compendium Modal - Phím [J]):
Quản lý sổ tay thông tin cư dân, thư viện đơn hàng, lưu/tải tiến trình chơi và cẩm nang
vòng lặp chơi cốt lõi (Core Loop) chuẩn phong cách Stardew Valley.

Các tính năng chính:
- Tab 1 — Sổ Tay Cư Dân & Mốc Tim (12 NPCs):
  + Lưới danh sách 12 cư dân với ảnh đại diện, tên, nhóm tuổi (Người Cao Tuổi / Trẻ Nhỏ / Cư Dân).
  + Thuyết minh Radar An Toàn 8.7: Tự động giảm tốc từ xa 1.65m đối với Người già & Trẻ nhỏ.
  + Số Tim hiện tại (0..5 ♥), Món Yêu Thích (Loved Items), và trạng thái mở khóa Mốc 3 ♥ / Mốc 5 ♥.
  + Bảng hồ sơ chi tiết (Dossier) của cư dân đang chọn: sở thích quà tặng, vị trí bản đồ, lịch trình.
- Tab 2 — Thư Viện Đơn Hàng & Bí Mật Thị Trấn:
  + Danh sách toàn bộ đơn hàng (Đơn thường + Đơn đặc biệt theo Mùa Vụ / Mốc Tim).
  + Chuyên mục 'Tin Đồn & Bí Mật Khám Phá': gợi ý vị trí Nấm Rừng Quý, Quả Mọng Dại, Hoa Cúc Vàng, Lễ Hội Hoa Anh Đào.
- Tab 3 — Lưu / Tải Game (3 Save Slots) & Hướng Dẫn Core Loop:
  + 3 Slot lưu dữ liệu độc lập với các nút Lưu / Tải trực tiếp (gọi game.state.save_to_slot / load_from_slot).
  + Tóm tắt 4 bước vòng lặp chơi Stardew Valley: Thu hoạch -> An toàn HRI -> Tặng quà -> Nâng cấp Xưởng Robin.
"""

from __future__ import annotations

import json
import math
import os
import time
from typing import Any
import pygame

from .constants import ITEM_NAMES_VI, SCREEN_H, SCREEN_W


# ==============================================================================
# CƠ SỞ DỮ LIỆU 12 CƯ DÂN THỊ TRẤN FARMBOT TOWN (DEFAULT_NPCS_DB)
# ==============================================================================
DEFAULT_NPCS_DB: dict[str, dict[str, Any]] = {
    "Bà Evelyn": {
        "name": "Bà Evelyn",
        "role": "Người giao Nhiệm vụ Hái Quả / Chăm Hoa",
        "folder": "npc_red",
        "age_group": "Người Cao Tuổi",
        "map_id": 1,
        "loved_items": ["strawberry", "peach", "bread"],
        "liked_items": ["apple", "orange", "cabbage", "corn"],
        "hated_items": ["fish", "parcel"],
        "favorite_desc": "Dâu Tây Đỏ, Đào Tiên Hồng, Bánh Mì Nóng",
        "secret_hint": "Bà Evelyn thích nhất món Dâu Tây Đỏ hái từ luống dâu Map 1 & Map 2.",
        "schedule_hint": "Sáng chăm hoa Quảng Trường (07:00), Chiều trò chuyện gần đài phun nước.",
    },
    "Ông George": {
        "name": "Ông George",
        "role": "Lão Ngư Giao Việc Câu Cá",
        "folder": "npc_old",
        "age_group": "Người Cao Tuổi",
        "map_id": 1,
        "loved_items": ["fish", "pumpkin", "bread"],
        "liked_items": ["carrot", "corn", "tomato", "apple"],
        "hated_items": ["strawberry", "peach"],
        "favorite_desc": "Cá Hồ Tươi, Bí Ngô Vàng, Bánh Mì Nóng",
        "secret_hint": "Ông George mê món Cá Hồ Tươi câu ở Cầu Tàu Map 3 và Bí Ngô Vàng.",
        "schedule_hint": "Ngồi sưởi nắng bên ghế đá Quảng Trường cả ngày.",
    },
    "Thị trưởng Lewis": {
        "name": "Thị trưởng Lewis",
        "role": "Thị Trưởng Điều Hành Thị Trấn",
        "folder": "npc_13_scholar",
        "age_group": "Người Cao Tuổi",
        "map_id": 4,
        "loved_items": ["pumpkin", "orange", "bread"],
        "liked_items": ["apple", "corn", "tomato", "carrot"],
        "hated_items": ["fish"],
        "favorite_desc": "Bí Ngô Vàng, Cam Vàng Mọng, Bánh Mì Nóng",
        "secret_hint": "Thị trưởng rất trân trọng những kiện hàng chuyển phát đúng hẹn.",
        "schedule_hint": "Làm việc tại Dinh thự Map 4, Chiều dạo quanh khu dân cư kiểm tra thùng hàng.",
    },
    "Ngư phủ Willy": {
        "name": "Ngư phủ Willy",
        "role": "Ngư Dân Kỳ Cựu Ven Hồ",
        "folder": "npc_07_old_man",
        "age_group": "Người Cao Tuổi",
        "map_id": 3,
        "loved_items": ["fish", "pumpkin", "bread"],
        "liked_items": ["apple", "orange", "corn"],
        "hated_items": ["cabbage", "carrot"],
        "favorite_desc": "Cá Hồ Tươi, Bí Ngô Vàng, Bánh Mì Nóng",
        "secret_hint": "Willy thường thả câu ở Mũi Cầu Tàu Trung Tâm Map 3 lúc hoàng hôn.",
        "schedule_hint": "Sáng sớm ở Chòi Ngư Cụ Map 3, Trưa và Chiều câu cá tại Cầu Tàu.",
    },
    "Bé Jas": {
        "name": "Bé Jas",
        "role": "Học Sinh Vui Tươi Đi Dạo",
        "folder": "npc_09_young_girl",
        "age_group": "Trẻ Nhỏ",
        "map_id": 1,
        "loved_items": ["strawberry", "peach", "apple"],
        "liked_items": ["orange", "bread", "corn"],
        "hated_items": ["fish", "cabbage", "tomato"],
        "favorite_desc": "Dâu Tây Đỏ, Đào Tiên Hồng, Táo Đỏ Chín",
        "secret_hint": "Bé Jas thích trái cây ngọt và những quả đào tiên hái trên cây Map 2.",
        "schedule_hint": "Sáng đi học qua cầu Map 1, Chiều đu quay & dạo quanh giếng cổ.",
    },
    "Chàng mèo Leo": {
        "name": "Chàng mèo Leo",
        "role": "Cậu Bé Yêu Rừng Bờ Hồ",
        "folder": "npc_10_cat_boy",
        "age_group": "Trẻ Nhỏ",
        "map_id": 3,
        "loved_items": ["fish", "strawberry", "orange"],
        "liked_items": ["peach", "apple", "bread"],
        "hated_items": ["cabbage", "carrot", "tomato"],
        "favorite_desc": "Cá Hồ Tươi, Dâu Tây Đỏ, Cam Vàng Mọng",
        "secret_hint": "Leo thích chơi với cá tươi và nhặt nấm rừng trên các hòn đảo Map 3.",
        "schedule_hint": "Dạo bộ quanh bờ hồ Map 3, Leo trèo bên các bụi cây quả mọng.",
    },
    "Thợ mộc Robin": {
        "name": "Thợ mộc Robin",
        "role": "Kiến Trúc Sư & Xưởng Nâng Cấp",
        "folder": "npc_06_farmer_girl",
        "age_group": "Cư Dân",
        "map_id": 4,
        "loved_items": ["peach", "pumpkin", "apple"],
        "liked_items": ["bread", "carrot", "corn", "orange"],
        "hated_items": ["fish"],
        "favorite_desc": "Đào Tiên Hồng, Bí Ngô Vàng, Táo Đỏ Chín",
        "secret_hint": "Đạt 3 ♥ với Robin giúp giảm 20% chi phí nâng cấp Robot tại Xưởng [U].",
        "schedule_hint": "Sáng làm việc tại Xưởng Mộc Map 4, Chiều ra sườn đồi kiếm gỗ tốt.",
    },
    "Đầu bếp Gus": {
        "name": "Đầu bếp Gus",
        "role": "Đầu Bếp Trưởng Saloon",
        "folder": "npc_01_orange_boy",
        "age_group": "Cư Dân",
        "map_id": 4,
        "loved_items": ["fish", "tomato", "bread", "pumpkin"],
        "liked_items": ["apple", "orange", "cabbage", "corn", "carrot"],
        "hated_items": ["parcel"],
        "favorite_desc": "Cá Hồ Tươi, Cà Chua Chín, Bánh Mì Nóng, Bí Ngô",
        "secret_hint": "Gus luôn tìm nguyên liệu tươi ngon để làm món xúp cá đặc sản.",
        "schedule_hint": "Sáng đi chợ chọn rau củ, Trưa nấu ăn trong nhà, Tối mở Saloon đón khách.",
    },
    "Chủ tiệm Pierre": {
        "name": "Chủ tiệm Pierre",
        "role": "Chủ Tiệm Tạp Hóa Thị Trấn",
        "folder": "npc_green",
        "age_group": "Cư Dân",
        "map_id": 1,
        "loved_items": ["orange", "bread", "apple"],
        "liked_items": ["strawberry", "corn", "carrot", "cabbage"],
        "hated_items": ["fish"],
        "favorite_desc": "Cam Vàng Mọng, Bánh Mì Nóng, Táo Đỏ Chín",
        "secret_hint": "Pierre rất thích cam vàng mọng và cam kết hỗ trợ kinh doanh thị trấn.",
        "schedule_hint": "Đứng quầy Tạp Hóa Map 1 từ 07:00 đến chiều muộn.",
    },
    "Cô Haley": {
        "name": "Cô Haley",
        "role": "Nhiếp Ảnh Gia Khu Dân Cư",
        "folder": "npc_02_blonde_girl",
        "age_group": "Cư Dân",
        "map_id": 4,
        "loved_items": ["strawberry", "peach"],
        "liked_items": ["bread", "orange", "apple"],
        "hated_items": ["fish", "cabbage", "pumpkin"],
        "favorite_desc": "Dâu Tây Đỏ, Đào Tiên Hồng",
        "secret_hint": "Haley rất kén chọn, chỉ nhận dâu tây đỏ tươi và đào tiên hồng ngọt thơm.",
        "schedule_hint": "Chụp ảnh hoa viên Map 4 buổi sáng, Chiều dạo quanh bờ suối ngắm nắng.",
    },
    "Cô Abigail": {
        "name": "Cô Abigail",
        "role": "Cư Dân Yêu Thám Hiểm",
        "folder": "npc_03_purple_hair",
        "age_group": "Cư Dân",
        "map_id": 4,
        "loved_items": ["pumpkin", "apple", "fish"],
        "liked_items": ["strawberry", "orange", "bread"],
        "hated_items": ["cabbage", "carrot"],
        "favorite_desc": "Bí Ngô Vàng, Táo Đỏ Chín, Cá Hồ Tươi",
        "secret_hint": "Abigail thích khám phá đảo bí mật phía bắc và ăn bí ngô vàng.",
        "schedule_hint": "Dạo quanh khu vườn phía sau nhà Map 4, Chiều tập sáo bên bờ hồ.",
    },
    "Nông dân Marnie": {
        "name": "Nông dân Marnie",
        "role": "Quản Lý Nông Trại & Thú Nuôi",
        "folder": "npc_06_farmer_girl",
        "age_group": "Cư Dân",
        "map_id": 2,
        "loved_items": ["wheat", "pumpkin", "carrot"],
        "liked_items": ["corn", "apple", "orange", "bread"],
        "hated_items": ["fish"],
        "favorite_desc": "Lúa Mì Vàng, Bí Ngô Vàng, Cà Rốt Tươi",
        "secret_hint": "Marnie yêu động vật, thích lúa mì vàng và cà rốt tươi làm thức ăn gia súc.",
        "schedule_hint": "Đi tuần quanh vườn quả, đường lát đá và đồng cỏ Map 2 cả ngày.",
    },
    # ---------------- 6 NPC MỚI: dùng nốt 7 sprite 1 hướng & các bộ 4 hướng còn lại ----------------
    "Quản nông Kent": {
        "name": "Quản nông Kent",
        "role": "Người Giao Nhiệm Vụ Nông Vụ",
        "folder": "npc_brown",
        "age_group": "Cư Dân",
        "map_id": 2,
        "loved_items": ["wheat", "corn", "bread"],
        "liked_items": ["pumpkin", "carrot", "apple"],
        "hated_items": ["fish", "golden_flower"],
        "favorite_desc": "Lúa Mì Vàng, Bắp Ngô Ngọt, Bánh Mì Nóng",
        "secret_hint": "Kent đứng trước cối xay gió Map 2, phát đơn thu hoạch lúa mì cho Marnie.",
        "schedule_hint": "Đứng yên trực tại cối xay gió Map 2 để giao việc (1 hướng).",
    },
    "Kỹ sư Sebastian": {
        "name": "Kỹ sư Sebastian",
        "role": "Người Giao Nhiệm Vụ Bến Hồ",
        "folder": "npc_black",
        "age_group": "Cư Dân",
        "map_id": 3,
        "loved_items": ["fish", "mushroom", "parcel"],
        "liked_items": ["bread", "pumpkin", "orange"],
        "hated_items": ["golden_flower", "cabbage"],
        "favorite_desc": "Cá Hồ Tươi, Nấm Rừng Thơm, Kiện Hàng",
        "secret_hint": "Sebastian ngồi đầu cầu tàu Map 3, đặt đơn cá tươi gửi bé Leo.",
        "schedule_hint": "Đứng yên ở biển chỉ dẫn đầu cầu tàu Map 3 (1 hướng).",
    },
    "Cô giáo Penny": {
        "name": "Cô giáo Penny",
        "role": "Người Giao Nhiệm Vụ Mùa Vụ",
        "folder": "npc_blonde",
        "age_group": "Cư Dân",
        "map_id": 4,
        "loved_items": ["golden_flower", "strawberry", "peach"],
        "liked_items": ["bread", "apple", "cabbage"],
        "hated_items": ["fish", "parcel"],
        "favorite_desc": "Hoa Cúc Vàng, Dâu Tây Đỏ, Đào Tiên Hồng",
        "secret_hint": "Penny đứng cạnh giếng làng Map 4, phát Đơn Mùa Vụ hoa cúc vàng.",
        "schedule_hint": "Đứng yên cạnh giếng làng Map 4 để giao việc (1 hướng).",
    },
    "Dược sĩ Maru": {
        "name": "Dược sĩ Maru",
        "role": "Người Giao Nhiệm Vụ Y Tế",
        "folder": "npc_purple",
        "age_group": "Cư Dân",
        "map_id": 4,
        "loved_items": ["peach", "orange", "strawberry"],
        "liked_items": ["apple", "carrot", "bread"],
        "hated_items": ["mushroom", "wild_berry"],
        "favorite_desc": "Đào Tiên Hồng, Cam Vàng Mọng, Dâu Tây Đỏ",
        "secret_hint": "Maru cần Đào Tiên để Bác sĩ Harvey bào chế thuốc bổ cho người già.",
        "schedule_hint": "Đứng yên trên đại lộ Map 4 để giao việc (1 hướng).",
    },
    "Cô Emily": {
        "name": "Cô Emily",
        "role": "Quản Lý Quán Nước Đi Tuần Phố",
        "folder": "npc_08_maid",
        "age_group": "Cư Dân",
        "map_id": 1,
        "loved_items": ["orange", "strawberry", "golden_flower"],
        "liked_items": ["apple", "bread", "peach"],
        "hated_items": ["fish", "corn"],
        "favorite_desc": "Cam Vàng Mọng, Dâu Tây Đỏ, Hoa Cúc Vàng",
        "secret_hint": "Emily đi một vòng quanh giếng cổ Map 1 trước giờ mở quán Saloon.",
        "schedule_hint": "Đi tuần vòng quanh quảng trường Map 1 (4 hướng).",
    },
    "Anh Shane": {
        "name": "Anh Shane",
        "role": "Điều Phối Nông Sản Kho Joja",
        "folder": "npc_05_blue_boy",
        "age_group": "Cư Dân",
        "map_id": 2,
        "loved_items": ["pumpkin", "corn", "bread"],
        "liked_items": ["tomato", "carrot", "wheat"],
        "hated_items": ["golden_flower", "peach"],
        "favorite_desc": "Bí Ngô Vàng, Bắp Ngô Ngọt, Bánh Mì Nóng",
        "secret_hint": "Shane chạy dọc đường đất giữa các thửa ruộng Map 2 để gom hàng cho Kho Joja.",
        "schedule_hint": "Đi tuần dọc đường đất giữa các ruộng Map 2 (4 hướng).",
    },
    "Anh Sam": {
        "name": "Anh Sam",
        "role": "Nhạc Công Qua Cầu",
        "folder": "npc_01_orange_boy",
        "age_group": "Cư Dân",
        "map_id": 1,
        "loved_items": ["bread", "strawberry", "orange"],
        "liked_items": ["apple", "carrot", "corn"],
        "hated_items": ["cabbage", "fish"],
        "favorite_desc": "Bánh Mì Nóng, Dâu Tây Đỏ, Cam Vàng Mọng",
        "secret_hint": "Sam đi qua lại cầu đá Map 1 tập guitar cho lễ hội.",
        "schedule_hint": "Đi tuần qua cầu đá phía đông Map 1 (4 hướng).",
    },
    "Cô Leah": {
        "name": "Cô Leah",
        "role": "Nghệ Sĩ Chăm Luống Rau",
        "folder": "npc_04_green_hair",
        "age_group": "Cư Dân",
        "map_id": 2,
        "loved_items": ["golden_flower", "mushroom", "peach"],
        "liked_items": ["wild_berry", "cabbage", "apple"],
        "hated_items": ["bread", "fish"],
        "favorite_desc": "Hoa Cúc Vàng, Nấm Rừng Thơm, Đào Tiên Hồng",
        "secret_hint": "Leah đi dọc đường lát đá Map 2, ngắm ruộng dâu và bí ngô.",
        "schedule_hint": "Đi tuần dọc đường lát đá phía bắc Map 2 (4 hướng).",
    },
    "Nhà thám hiểm Marlon": {
        "name": "Nhà thám hiểm Marlon",
        "role": "Canh Gác Đảo Bắc",
        "folder": "npc_12_adventurer",
        "age_group": "Cư Dân",
        "map_id": 3,
        "loved_items": ["mushroom", "bread", "parcel"],
        "liked_items": ["apple", "pumpkin", "fish"],
        "hated_items": ["golden_flower", "strawberry"],
        "favorite_desc": "Nấm Rừng Thơm, Bánh Mì Nóng, Kiện Hàng",
        "secret_hint": "Marlon tuần tra cầu gỗ phía bắc Map 3 dẫn ra Đảo Rừng.",
        "schedule_hint": "Đi tuần trên cầu gỗ phía bắc Map 3 (4 hướng).",
    },
    "Học giả Elliott": {
        "name": "Học giả Elliott",
        "role": "Nhà Văn Đi Dạo Khu Dân Cư",
        "folder": "npc_13_scholar",
        "age_group": "Cư Dân",
        "map_id": 4,
        "loved_items": ["golden_flower", "peach", "fish"],
        "liked_items": ["bread", "apple", "strawberry"],
        "hated_items": ["cabbage", "parcel"],
        "favorite_desc": "Hoa Cúc Vàng, Đào Tiên Hồng, Cá Hồ Tươi",
        "secret_hint": "Elliott đi dọc lối đất trước nhà Gus tìm cảm hứng viết văn.",
        "schedule_hint": "Đi tuần lối đất phía tây Map 4 (4 hướng).",
    },
}


def get_npc_age_group(game: Any, npc_name: str) -> str:
    """
    Tra cứu nhóm tuổi của NPC:
    - Tra từ game.state.npcs_db nếu có (quy đổi 'elder' -> 'Người Cao Tuổi', 'child' -> 'Trẻ Nhỏ', 'adult' -> 'Cư Dân').
    """
    map_vi = {
        "elder": "Người Cao Tuổi",
        "child": "Trẻ Nhỏ",
        "adult": "Cư Dân",
        "Người Cao Tuổi": "Người Cao Tuổi",
        "Trẻ Nhỏ": "Trẻ Nhỏ",
        "Cư Dân": "Cư Dân",
    }
    if hasattr(game, "state") and getattr(game.state, "npcs_db", None):
        info = game.state.npcs_db.get(npc_name)
        if isinstance(info, dict) and "age_group" in info:
            raw = str(info["age_group"])
            return map_vi.get(raw, raw)
        if hasattr(info, "age_group"):
            raw = str(getattr(info, "age_group"))
            return map_vi.get(raw, raw)

    elders = ("Bà Evelyn", "Ông George", "Thị trưởng Lewis", "Ngư phủ Willy")
    kids = ("Bé Jas", "Chàng mèo Leo")
    for e in elders:
        if e in npc_name:
            return "Người Cao Tuổi"
    for k in kids:
        if k in npc_name:
            return "Trẻ Nhỏ"
    return "Cư Dân"


# ==============================================================================
# HỆ THỐNG LƯU / TẢI TIẾN TRÌNH CHƠI (TownGameState - 3 Save Slots)
# ==============================================================================
class TownGameState:
    """Quản lý dữ liệu lưu trữ (3 Save Slots) và cơ sở dữ liệu cư dân thị trấn."""

    def __init__(self) -> None:
        self.npcs_db: dict[str, dict[str, Any]] = dict(DEFAULT_NPCS_DB)
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.save_dir: str = os.path.join(base_dir, "saves")
        try:
            os.makedirs(self.save_dir, exist_ok=True)
        except Exception:
            pass

    def get_slot_path(self, slot_idx: int) -> str:
        """Đường dẫn tệp JSON của slot lưu trữ tương ứng (1, 2, 3)."""
        return os.path.join(self.save_dir, f"save_slot_{slot_idx}.json")

    def get_slot_info(self, slot_idx: int) -> dict[str, Any] | None:
        """Đọc tóm tắt thông tin save slot nếu tồn tại."""
        path = self.get_slot_path(slot_idx)
        if not os.path.exists(path):
            return None
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return None

    def save_to_slot(self, game: Any, slot_idx: int) -> bool:
        """Lưu toàn bộ trạng thái tiến trình chơi vào slot 1, 2, hoặc 3."""
        try:
            os.makedirs(self.save_dir, exist_ok=True)
            path = self.get_slot_path(slot_idx)
            data = {
                "slot_idx": slot_idx,
                "save_time": time.strftime("%d/%m/%Y %H:%M"),
                "score": getattr(game, "score", 0),
                "gold": getattr(game, "gold", 60),
                "hearts": getattr(game, "hearts", 3),
                "completed_quests_count": getattr(game, "completed_quests_count", 0),
                "quest_idx": getattr(game, "quest_idx", 0),
                "current_map_id": getattr(game, "current_map_id", 1),
                "in_interior": getattr(game, "in_interior", False),
                "robot_x": getattr(game.robot, "x", 0.0),
                "robot_y": getattr(game.robot, "y", 0.0),
                "robot_theta": getattr(game.robot, "theta", 0.0),
                "inventory": list(getattr(game.robot, "inventory", [])),
                "max_inventory": getattr(game.robot, "max_inventory", 4),
                "friendship": dict(getattr(game.dialogue, "friendship", {})),
                "workshop_bought": dict(getattr(game.workshop, "bought_status", {})),
            }
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            if hasattr(game, "set_banner"):
                game.set_banner(
                    f"ĐÃ LƯU GAME VÀO SLOT {slot_idx} THÀNH CÔNG! ({data['gold']}G | {data['score']}đ)",
                    (115, 255, 145),
                )
            return True
        except Exception as e:
            if hasattr(game, "set_banner"):
                game.set_banner(f"Lỗi khi lưu Slot {slot_idx}: {e}", (255, 110, 110))
            return False

    def load_from_slot(self, game: Any, slot_idx: int) -> bool:
        """Tải trạng thái tiến trình chơi từ slot 1, 2, hoặc 3."""
        path = self.get_slot_path(slot_idx)
        if not os.path.exists(path):
            if hasattr(game, "set_banner"):
                game.set_banner(f"Slot {slot_idx} chưa có dữ liệu lưu!", (255, 165, 100))
            return False
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            game.score = data.get("score", getattr(game, "score", 0))
            game.gold = data.get("gold", getattr(game, "gold", 60))
            game.hearts = data.get("hearts", getattr(game, "hearts", 3))
            game.completed_quests_count = data.get("completed_quests_count", getattr(game, "completed_quests_count", 0))
            quests_len = len(getattr(game, "quests", [1]))
            game.quest_idx = data.get("quest_idx", getattr(game, "quest_idx", 0)) % max(1, quests_len)

            if hasattr(game, "robot"):
                game.robot.inventory = list(data.get("inventory", []))
                game.robot.max_inventory = data.get("max_inventory", 4)
            if hasattr(game, "dialogue"):
                game.dialogue.friendship = dict(data.get("friendship", {}))
            if hasattr(game, "workshop"):
                game.workshop.bought_status = dict(data.get("workshop_bought", {}))
                game.workshop.apply_passive_effects(game)

            map_id = data.get("current_map_id", 1)
            spawn_pos = (data.get("robot_x", game.robot.x), data.get("robot_y", game.robot.y))
            spawn_theta = data.get("robot_theta", game.robot.theta)
            if hasattr(game, "load_outdoor_map"):
                game.load_outdoor_map(map_id, spawn_pos=spawn_pos, spawn_theta=spawn_theta)

            if hasattr(game, "set_banner"):
                game.set_banner(
                    f"ĐÃ TẢI TIẾN TRÌNH TỪ SLOT {slot_idx} THÀNH CÔNG! Chào mừng trở lại.",
                    (115, 255, 145),
                )
            return True
        except Exception as e:
            if hasattr(game, "set_banner"):
                game.set_banner(f"Lỗi khi tải Slot {slot_idx}: {e}", (255, 110, 110))
            return False


def ensure_game_state(game: Any) -> TownGameState:
    """Đảm bảo đối tượng game.state luôn tồn tại và sẵn sàng sử dụng."""
    if not hasattr(game, "state") or game.state is None:
        game.state = TownGameState()
    return game.state


# ==============================================================================
# MODAL SỔ TAY THỊ TRẤN & BÁCH KHOA TOÀN THƯ (JournalAndCompendiumModal - Phím [J])
# ==============================================================================
class JournalAndCompendiumModal:
    """
    Quản lý Giao Diện Sổ Tay Cư Dân, Thư Viện Đơn Hàng & Lưu/Tải Game (Mục 8).
    Mở / Đóng bằng phím [J] hoặc nút điều khiển HUD.
    """

    def __init__(self) -> None:
        self.open: bool = False
        self.current_tab: int = 1  # 1: Cư Dân & Mốc Tim, 2: Đơn Hàng & Bí Mật, 3: Lưu/Tải & Core Loop
        self.selected_npc_name: str = "Bà Evelyn"

        # Vùng hình chữ nhật tương tác
        self.modal_rect: pygame.Rect = pygame.Rect(0, 0, 0, 0)
        self.close_btn_rect: pygame.Rect = pygame.Rect(0, 0, 0, 0)
        self.tab_rects: list[pygame.Rect] = []
        self.npc_card_rects: dict[str, pygame.Rect] = {}
        self.save_btn_rects: dict[int, pygame.Rect] = {}
        self.load_btn_rects: dict[int, pygame.Rect] = {}

    def toggle(self) -> None:
        """Đóng hoặc mở cửa sổ Sổ Tay Thị Trấn."""
        self.open = not self.open

    def handle_key(self, key: int, uni: str, game: Any) -> bool:
        """
        Xử lý sự kiện bàn phím khi modal đang mở:
        - [J]: Đóng / Mở modal.
        - [ESC]: Đóng modal.
        - [1], [2], [3]: Chuyển đổi tab tương ứng.
        - Trả về True nếu sự kiện được modal xử lý (nuốt sự kiện).
        """
        u = (uni or "").lower()
        if key == pygame.K_j or u == "j":
            self.toggle()
            return True

        if not self.open:
            return False

        if key == pygame.K_ESCAPE:
            self.open = False
            return True
        elif key in (pygame.K_1, pygame.K_KP1) or u == "1":
            self.current_tab = 1
            return True
        elif key in (pygame.K_2, pygame.K_KP2) or u == "2":
            self.current_tab = 2
            return True
        elif key in (pygame.K_3, pygame.K_KP3) or u == "3":
            self.current_tab = 3
            return True
        elif self.current_tab == 1 and key in (pygame.K_LEFT, pygame.K_PAGEUP):
            self.npc_page = max(0, getattr(self, "npc_page", 0) - 1)
            return True
        elif self.current_tab == 1 and key in (pygame.K_RIGHT, pygame.K_PAGEDOWN):
            self.npc_page = getattr(self, "npc_page", 0) + 1
            return True

        return True  # Nuốt phím để robot không di chuyển khi đang tra cứu sổ tay

    def handle_click(self, pos: tuple[int, int], game: Any) -> bool:
        """
        Xử lý sự kiện chuột click trên các nút bấm của Modal:
        - Nút đóng [X].
        - Thanh chuyển Tab 1, 2, 3.
        - Thẻ nhân vật trong Tab 1.
        - Các nút Lưu / Tải trong Tab 3.
        """
        if not self.open:
            return False

        mx, my = pos
        if self.close_btn_rect.collidepoint(mx, my):
            self.open = False
            return True

        for idx, t_rect in enumerate(self.tab_rects, start=1):
            if t_rect.collidepoint(mx, my):
                self.current_tab = idx
                return True

        if self.current_tab == 1:
            pr = getattr(self, "page_prev_rect", None)
            nr = getattr(self, "page_next_rect", None)
            if pr is not None and pr.collidepoint(mx, my):
                self.npc_page = max(0, getattr(self, "npc_page", 0) - 1)
                return True
            if nr is not None and nr.collidepoint(mx, my):
                self.npc_page = getattr(self, "npc_page", 0) + 1
                return True
            for name, r_rect in self.npc_card_rects.items():
                if r_rect.collidepoint(mx, my):
                    self.selected_npc_name = name
                    return True

        elif self.current_tab == 3:
            ensure_game_state(game)
            for s_idx, btn_rect in self.save_btn_rects.items():
                if btn_rect.collidepoint(mx, my):
                    game.state.save_to_slot(game, s_idx)
                    return True
            for s_idx, btn_rect in self.load_btn_rects.items():
                if btn_rect.collidepoint(mx, my):
                    game.state.load_from_slot(game, s_idx)
                    return True

        if self.modal_rect.collidepoint(mx, my):
            return True

        return False

    def render(self, screen: pygame.Surface, game: Any) -> None:
        """Vẽ toàn bộ giao diện Sổ Tay Thị Trấn phong cách Stardew Valley lên màn hình."""
        if not self.open:
            return

        ensure_game_state(game)

        # 1. Lớp phủ đen mờ nền toàn màn hình
        overlay = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
        overlay.fill((12, 10, 16, 185))
        screen.blit(overlay, (0, 0))

        # 2. Khung hộp gỗ chính giữa màn hình (1060 x 620)
        mw, mh = 1060, 620
        mx = (SCREEN_W - mw) // 2
        my = (SCREEN_H - mh) // 2
        self.modal_rect = pygame.Rect(mx, my, mw, mh)

        # Nền gỗ trầm ấm & Viền vàng đồng đôi
        pygame.draw.rect(screen, (46, 28, 18), self.modal_rect, border_radius=12)
        pygame.draw.rect(screen, (222, 168, 52), self.modal_rect, width=3, border_radius=12)
        inner_box = self.modal_rect.inflate(-8, -8)
        pygame.draw.rect(screen, (108, 72, 42), inner_box, width=2, border_radius=10)

        font_xs = getattr(game, "font_xs", None) or pygame.font.SysFont("Segoe UI", 13, bold=True)
        font_sm = getattr(game, "font_sm", None) or pygame.font.SysFont("Segoe UI", 15, bold=True)
        font_md = getattr(game, "font_md", None) or pygame.font.SysFont("Segoe UI", 18, bold=True)

        # 3. Header: Tiêu đề Sổ Tay & Nút đóng [X]
        header_surf = font_md.render("SỔ TAY THỊ TRẤN & BÁCH KHOA TOÀN THƯ FARMBOT", True, (255, 235, 110))
        screen.blit(header_surf, (mx + 28, my + 16))

        sub_surf = font_xs.render(
            "Quản lý hồ sơ cư dân, mốc thiện cảm tim, thư viện nhiệm vụ & lưu trữ ca làm việc",
            True,
            (215, 195, 175),
        )
        screen.blit(sub_surf, (mx + 28, my + 42))

        # Nút đóng [X] góc trên bên phải
        self.close_btn_rect = pygame.Rect(mx + mw - 46, my + 16, 32, 32)
        pygame.draw.rect(screen, (168, 42, 42), self.close_btn_rect, border_radius=6)
        pygame.draw.rect(screen, (235, 95, 95), self.close_btn_rect, width=2, border_radius=6)
        x_lbl = font_sm.render("X", True, (255, 255, 255))
        screen.blit(
            x_lbl,
            (
                self.close_btn_rect.centerx - x_lbl.get_width() // 2,
                self.close_btn_rect.centery - x_lbl.get_height() // 2 - 1,
            ),
        )

        # 4. Thanh 3 Tab chuyển đổi
        self.tab_rects.clear()
        tab_defs = [
            (1, "[1] Sổ Tay Cư Dân & Mốc Tim"),
            (2, "[2] Thư Viện Đơn Hàng & Bí Mật Thị Trấn"),
            (3, "[3] Lưu / Tải Game (3 Slots) & Core Loop"),
        ]
        start_tx = mx + 24
        tab_y = my + 68
        tab_w = 310
        tab_h = 34
        mouse_pos = pygame.mouse.get_pos()

        for t_idx, t_title in tab_defs:
            t_rect = pygame.Rect(start_tx, tab_y, tab_w, tab_h)
            self.tab_rects.append(t_rect)
            is_active = self.current_tab == t_idx
            is_hover = t_rect.collidepoint(mouse_pos)

            if is_active:
                t_bg = (68, 44, 28)
                t_bd = (255, 218, 65)
                t_col = (255, 248, 220)
            elif is_hover:
                t_bg = (54, 34, 22)
                t_bd = (215, 168, 55)
                t_col = (245, 230, 195)
            else:
                t_bg = (34, 22, 14)
                t_bd = (112, 74, 44)
                t_col = (185, 170, 150)

            pygame.draw.rect(screen, t_bg, t_rect, border_radius=6)
            pygame.draw.rect(screen, t_bd, t_rect, width=2 if is_active else 1, border_radius=6)
            t_surf = font_xs.render(t_title, True, t_col)
            screen.blit(
                t_surf,
                (
                    t_rect.centerx - t_surf.get_width() // 2,
                    t_rect.centery - t_surf.get_height() // 2,
                ),
            )
            start_tx += tab_w + 14

        # Phân cách giữa Tab và Nội dung
        pygame.draw.line(screen, (115, 76, 46), (mx + 20, my + 108), (mx + mw - 20, my + 108), 2)

        # 5. Nội dung tương ứng theo Tab đang chọn
        if self.current_tab == 1:
            self._render_tab1_citizens(screen, game, mx, my, mw, mh)
        elif self.current_tab == 2:
            self._render_tab2_quests_secrets(screen, game, mx, my, mw, mh)
        elif self.current_tab == 3:
            self._render_tab3_save_loop(screen, game, mx, my, mw, mh)

        # 6. Footer hướng dẫn
        guide_txt = "Phím tắt: [1], [2], [3] Chuyển Tab  |  [G]: Tặng Quà Cư Dân  |  [J] hoặc [ESC]: Đóng Sổ Tay"
        g_surf = font_xs.render(guide_txt, True, (215, 195, 145))
        screen.blit(g_surf, (mx + mw // 2 - g_surf.get_width() // 2, my + mh - 24))

    # --------------------------------------------------------------------------
    # TAB 1: SỔ TAY CƯ DÂN & MỐC TIM (12 NPCs)
    # --------------------------------------------------------------------------
    def _render_tab1_citizens(
        self, screen: pygame.Surface, game: Any, mx: int, my: int, mw: int, mh: int
    ) -> None:
        font_xs = getattr(game, "font_xs", None) or pygame.font.SysFont("Segoe UI", 13, bold=True)
        font_sm = getattr(game, "font_sm", None) or pygame.font.SysFont("Segoe UI", 15, bold=True)
        mouse_pos = pygame.mouse.get_pos()

        # Cột Trái: Lưới 12 Cư Dân (2 Cột x 6 Hàng)
        self.npc_card_rects.clear()
        col_w = 256
        row_h = 64
        grid_x = mx + 24
        grid_y = my + 118
        gap_x = 12
        gap_y = 6

        npcs_list = list(DEFAULT_NPCS_DB.values())
        per_page = 12
        total_pages = max(1, (len(npcs_list) + per_page - 1) // per_page)
        self.npc_page = max(0, min(getattr(self, "npc_page", 0), total_pages - 1))
        page_items = npcs_list[self.npc_page * per_page:(self.npc_page + 1) * per_page]

        # Thanh phân trang ở dưới lưới cư dân: [<] Trang x/y [>]
        pg_y = grid_y + 6 * (row_h + gap_y) - 2
        self.page_prev_rect = pygame.Rect(grid_x, pg_y, 36, 22)
        self.page_next_rect = pygame.Rect(grid_x + 2 * col_w + gap_x - 36, pg_y, 36, 22)
        for r_btn, sym, enabled in (
            (self.page_prev_rect, "<", self.npc_page > 0),
            (self.page_next_rect, ">", self.npc_page < total_pages - 1),
        ):
            pygame.draw.rect(screen, (62, 42, 26) if enabled else (36, 24, 16), r_btn, border_radius=5)
            pygame.draw.rect(screen, (255, 215, 65) if enabled else (95, 70, 44), r_btn, width=1, border_radius=5)
            s_lbl = font_sm.render(sym, True, (255, 240, 200) if enabled else (120, 100, 80))
            screen.blit(s_lbl, (r_btn.centerx - s_lbl.get_width() // 2, r_btn.centery - s_lbl.get_height() // 2))
        pg_txt = font_xs.render(
            f"Trang {self.npc_page + 1}/{total_pages}  ({len(npcs_list)} cư dân)  —  phím [←]/[→] để lật trang",
            True,
            (225, 205, 165),
        )
        screen.blit(pg_txt, (grid_x + col_w + gap_x // 2 - pg_txt.get_width() // 2, pg_y + 3))

        for idx, npc in enumerate(page_items):
            c = idx % 2
            r = idx // 2
            rx = grid_x + c * (col_w + gap_x)
            ry = grid_y + r * (row_h + gap_y)
            c_rect = pygame.Rect(rx, ry, col_w, row_h)
            self.npc_card_rects[npc["name"]] = c_rect

            is_sel = self.selected_npc_name == npc["name"]
            is_hover = c_rect.collidepoint(mouse_pos)
            bg_col = (62, 42, 26) if is_sel else ((50, 32, 20) if is_hover else (36, 24, 16))
            bd_col = (255, 215, 65) if is_sel else ((215, 165, 55) if is_hover else (105, 72, 44))

            pygame.draw.rect(screen, bg_col, c_rect, border_radius=8)
            pygame.draw.rect(screen, bd_col, c_rect, width=2 if is_sel else 1, border_radius=8)

            # Avatar nhỏ của NPC
            spr = None
            if hasattr(game, "vault") and game.vault is not None:
                spr = game.vault.get_npc_portrait(npc['folder'], 44)
            if spr is not None:
                screen.blit(spr, (rx + 8, ry + (row_h - spr.get_height()) // 2))
            else:
                pygame.draw.circle(screen, (225, 140, 100), (rx + 28, ry + row_h // 2), 18)

            # Tên NPC (tự cắt ngắn để không đè lên huy hiệu 3♥ / 5♥)
            name_col = (255, 248, 225) if not is_sel else (255, 235, 110)
            disp_name = npc["name"]
            max_name_w = col_w - 56 - 56
            while len(disp_name) > 4 and font_sm.size(disp_name)[0] > max_name_w:
                disp_name = disp_name[:-1]
            if disp_name != npc["name"]:
                disp_name = disp_name.rstrip() + "."
            name_surf = font_sm.render(disp_name, True, name_col)
            screen.blit(name_surf, (rx + 56, ry + 8))

            # Nhóm tuổi badge
            age_group = npc["age_group"]
            age_colors = {
                "Người Cao Tuổi": ((255, 185, 110), (75, 45, 20)),
                "Trẻ Nhỏ": ((135, 235, 255), (20, 50, 70)),
                "Cư Dân": ((150, 245, 150), (25, 65, 30)),
            }
            afg, abg = age_colors.get(age_group, ((220, 220, 220), (50, 50, 50)))
            albl = font_xs.render(f"[{age_group}]", True, afg)
            screen.blit(albl, (rx + 56, ry + 28))

            # 5 Tim thiện cảm hiện tại
            cur_hearts = 2
            if hasattr(game, "dialogue") and game.dialogue is not None:
                cur_hearts = game.dialogue.get_hearts(npc["name"])

            heart_ico = game.vault.scaled("icon_heart", 13, 12) if hasattr(game, "vault") else None
            for hi in range(5):
                hx = rx + 56 + hi * 15
                hy = ry + 48
                if hi < cur_hearts:
                    if heart_ico:
                        screen.blit(heart_ico, (hx, hy))
                    else:
                        pygame.draw.circle(screen, (245, 55, 65), (hx + 6, hy + 6), 5)
                else:
                    pygame.draw.circle(screen, (75, 50, 42), (hx + 6, hy + 6), 5)
                    pygame.draw.circle(screen, (135, 95, 80), (hx + 6, hy + 6), 5, width=1)

            # Huy hiệu Mốc Tim (3♥ / 5♥) ở góc phải thẻ
            m3_col = (115, 255, 145) if cur_hearts >= 3 else (135, 115, 100)
            m5_col = (255, 215, 65) if cur_hearts >= 5 else (135, 115, 100)
            m3_lbl = font_xs.render("3♥", True, m3_col)
            m5_lbl = font_xs.render("5♥", True, m5_col)
            screen.blit(m3_lbl, (rx + col_w - 48, ry + 10))
            screen.blit(m5_lbl, (rx + col_w - 26, ry + 10))

        # Cột Phải: Bảng Hồ Sơ Chi Tiết (Dossier) của Cư Dân Đang Chọn
        d_x = mx + 560
        d_y = my + 118
        d_w = mw - (d_x - mx) - 24
        d_h = 464
        d_rect = pygame.Rect(d_x, d_y, d_w, d_h)

        pygame.draw.rect(screen, (34, 22, 14), d_rect, border_radius=10)
        pygame.draw.rect(screen, (215, 165, 55), d_rect, width=2, border_radius=10)

        sel_npc = DEFAULT_NPCS_DB.get(self.selected_npc_name, npcs_list[0])

        # Chân dung lớn của NPC (cao 68px)
        p_frame = pygame.Rect(d_x + 16, d_y + 16, 76, 76)
        pygame.draw.rect(screen, (64, 42, 28), p_frame, border_radius=8)
        pygame.draw.rect(screen, (185, 135, 65), p_frame, width=2, border_radius=8)
        big_spr = None
        if hasattr(game, "vault") and game.vault is not None:
            big_spr = game.vault.get_npc_portrait(sel_npc['folder'], 64)
        if big_spr is not None:
            screen.blit(big_spr, (p_frame.centerx - big_spr.get_width() // 2, p_frame.centery - big_spr.get_height() // 2))

        # Tên, Nghề nghiệp và Nhóm tuổi
        sel_name_surf = font_sm.render(sel_npc["name"], True, (255, 235, 110))
        screen.blit(sel_name_surf, (d_x + 104, d_y + 18))
        role_surf = font_xs.render(f"Vai trò: {sel_npc['role']}", True, (230, 215, 195))
        screen.blit(role_surf, (d_x + 104, d_y + 40))

        cur_hearts = 2
        if hasattr(game, "dialogue") and game.dialogue is not None:
            cur_hearts = game.dialogue.get_hearts(sel_npc["name"])
        pts = getattr(game.dialogue, "friendship", {}).get(sel_npc["name"], 200) if hasattr(game, "dialogue") else 200
        h_info_surf = font_xs.render(f"Thiện Cảm: {cur_hearts}/5 ♥  ({pts}/500 điểm)", True, (255, 175, 185))
        screen.blit(h_info_surf, (d_x + 104, d_y + 64))

        # Kiểu NPC: 1 hướng (đứng yên giao việc) hoặc 4 hướng (đi tuần tra)
        is_single_dir = not str(sel_npc.get("folder", "")).startswith("npc_0") and not str(
            sel_npc.get("folder", "")
        ).startswith("npc_1")
        kind_txt = (
            "Kiểu: NPC 1 hướng — Đứng yên giao nhiệm vụ [!]"
            if is_single_dir
            else "Kiểu: NPC 4 hướng — Đi tuần tra quanh bản đồ"
        )
        kind_col = (255, 215, 95) if is_single_dir else (140, 225, 255)
        screen.blit(font_xs.render(kind_txt, True, kind_col), (d_x + 104, d_y + 84))

        # Đường kẻ phân cách
        pygame.draw.line(screen, (105, 72, 44), (d_x + 16, d_y + 104), (d_x + d_w - 16, d_y + 104), 1)

        # Khung giải thích Radar An Toàn 8.7
        radar_rect = pygame.Rect(d_x + 16, d_y + 116, d_w - 32, 62)
        is_elder_or_child = sel_npc["age_group"] in ("Người Cao Tuổi", "Trẻ Nhỏ")
        r_bg = (52, 34, 18) if not is_elder_or_child else (48, 28, 22)
        r_bd = (145, 195, 120) if not is_elder_or_child else (255, 175, 95)
        pygame.draw.rect(screen, r_bg, radar_rect, border_radius=6)
        pygame.draw.rect(screen, r_bd, radar_rect, width=1, border_radius=6)

        r_title = font_xs.render(
            "[!] RADAR AN TOÀN 8.7: TỰ ĐỘNG GIẢM TỐC TỪ XA 1.65m" if is_elder_or_child
            else "[!] RADAR AN TOÀN 8.7: TỰ ĐỘNG GIẢM TỐC KHOẢNG CÁCH 1.30m",
            True,
            r_bd,
        )
        screen.blit(r_title, (radar_rect.x + 8, radar_rect.y + 8))

        r_desc = (
            "Nhóm Người Cao Tuổi / Trẻ Nhỏ: Robot tự giảm tốc từ xa 1.65m\nđể tránh gây giật mình và đảm bảo an toàn tuyệt đối."
            if is_elder_or_child
            else "Nhóm Cư Dân Trưởng Thành: Robot tự giảm tốc khi cách người < 1.30m."
        )
        for li, lstr in enumerate(r_desc.split("\n")):
            screen.blit(font_xs.render(lstr, True, (215, 205, 190)), (radar_rect.x + 8, radar_rect.y + 26 + li * 15))

        # Sở thích quà tặng [G]
        gy = d_y + 190
        screen.blit(font_sm.render("SỞ THÍCH QUÀ TẶNG (PHÍM [G]):", True, (255, 225, 95)), (d_x + 16, gy))

        # Loved Items (+120 thiện cảm, +40đ)
        loved_names = [ITEM_NAMES_VI.get(k, k) for k in sel_npc["loved_items"][:3]]
        l_str = f"♥ Yêu Thích (+120 tim): {', '.join(loved_names)}"
        screen.blit(font_xs.render(l_str, True, (255, 150, 180)), (d_x + 16, gy + 24))

        # Liked Items (+65 thiện cảm, +25đ)
        liked_names = [ITEM_NAMES_VI.get(k, k) for k in sel_npc["liked_items"][:3]]
        lk_str = f"+ Thích (+65 tim): {', '.join(liked_names)}"
        screen.blit(font_xs.render(lk_str, True, (140, 235, 160)), (d_x + 16, gy + 44))

        # Hated Items (-50 thiện cảm)
        hated_names = [ITEM_NAMES_VI.get(k, k) for k in sel_npc["hated_items"][:3]]
        h_str = f"! Ghét (-50 tim): {', '.join(hated_names)}"
        screen.blit(font_xs.render(h_str, True, (255, 120, 120)), (d_x + 16, gy + 64))

        # Đường kẻ phân cách
        pygame.draw.line(screen, (105, 72, 44), (d_x + 16, gy + 88), (d_x + d_w - 16, gy + 88), 1)

        # Trạng thái mở khóa Mốc 3 ♥ và Mốc 5 ♥
        my_y = gy + 98
        screen.blit(font_sm.render("TRẠNG THÁI MỞ KHÓA MỐC TIM:", True, (255, 225, 95)), (d_x + 16, my_y))

        m3_open = cur_hearts >= 3
        m3_box = pygame.Rect(d_x + 16, my_y + 24, d_w - 32, 54)
        pygame.draw.rect(screen, (28, 52, 32) if m3_open else (42, 28, 20), m3_box, border_radius=6)
        pygame.draw.rect(screen, (95, 235, 125) if m3_open else (115, 80, 52), m3_box, width=1, border_radius=6)

        m3_title = f"MỐC 3 ♥: GIẢM 20% XƯỞNG & QUÀ 50G — {'[ĐÃ MỞ KHÓA]' if m3_open else '[ĐANG KHÓA]'}"
        screen.blit(font_xs.render(m3_title, True, (135, 255, 155) if m3_open else (195, 175, 150)), (m3_box.x + 8, m3_box.y + 6))
        m3_desc = "Tặng quà [G] hoặc giao hàng đạt 300 điểm thiện cảm để mở khóa."
        screen.blit(font_xs.render(m3_desc, True, (215, 205, 185)), (m3_box.x + 8, m3_box.y + 26))

        m5_open = cur_hearts >= 5
        m5_box = pygame.Rect(d_x + 16, my_y + 86, d_w - 32, 54)
        pygame.draw.rect(screen, (52, 44, 20) if m5_open else (42, 28, 20), m5_box, border_radius=6)
        pygame.draw.rect(screen, (255, 215, 65) if m5_open else (115, 80, 52), m5_box, width=1, border_radius=6)

        m5_title = f"MỐC 5 ♥: MỞ ĐƠN ĐẶC BIỆT & QUÀ 120G — {'[ĐÃ MỞ KHÓA]' if m5_open else '[ĐANG KHÓA]'}"
        screen.blit(font_xs.render(m5_title, True, (255, 230, 95) if m5_open else (195, 175, 150)), (m5_box.x + 8, m5_box.y + 6))
        m5_desc = "Đạt 500 điểm thiện cảm: mở khóa các đơn đặt hàng VIP thưởng lớn."
        screen.blit(font_xs.render(m5_desc, True, (215, 205, 185)), (m5_box.x + 8, m5_box.y + 26))

        # Gợi ý lịch sinh hoạt
        sched_y = m5_box.bottom + 12
        sched_txt = f"Lịch trình: {sel_npc['schedule_hint'][:58]}"
        screen.blit(font_xs.render(sched_txt, True, (235, 215, 165)), (d_x + 16, sched_y))

    # --------------------------------------------------------------------------
    # TAB 2: THƯ VIỆN ĐƠN HÀNG & BÍ MẬT THỊ TRẤN
    # --------------------------------------------------------------------------
    def _render_tab2_quests_secrets(
        self, screen: pygame.Surface, game: Any, mx: int, my: int, mw: int, mh: int
    ) -> None:
        font_xs = getattr(game, "font_xs", None) or pygame.font.SysFont("Segoe UI", 13, bold=True)
        font_sm = getattr(game, "font_sm", None) or pygame.font.SysFont("Segoe UI", 15, bold=True)
        font_md = getattr(game, "font_md", None) or pygame.font.SysFont("Segoe UI", 18, bold=True)

        # Cột Trái (w = 480): Thư Viện Đơn Hàng Thị Trấn
        left_w = 480
        left_x = mx + 24
        left_y = my + 118
        left_h = 464

        screen.blit(font_md.render("THƯ VIỆN ĐƠN HÀNG THỊ TRẤN", True, (255, 235, 110)), (left_x, left_y))
        comp_count = getattr(game, "completed_quests_count", 0)
        c_txt = font_xs.render(f"Đã hoàn thành xuất sắc: {comp_count} đơn hàng", True, (115, 255, 145))
        screen.blit(c_txt, (left_x + 280, left_y + 4))

        # Danh sách nhiệm vụ chuẩn
        quests = getattr(game, "quests", [])
        qy = left_y + 32
        for i, q in enumerate(quests[:5]):
            q_box = pygame.Rect(left_x, qy, left_w, 42)
            is_active = (i == getattr(game, "quest_idx", 0))
            is_done = getattr(q, "status", "") == "completed" or (comp_count > i)

            q_bg = (46, 32, 22) if not is_active else (58, 42, 26)
            q_bd = (255, 215, 65) if is_active else ((95, 235, 125) if is_done else (105, 75, 46))
            pygame.draw.rect(screen, q_bg, q_box, border_radius=6)
            pygame.draw.rect(screen, q_bd, q_box, width=1, border_radius=6)

            title_txt = font_xs.render(q.title, True, (255, 248, 225) if not is_active else (255, 235, 110))
            screen.blit(title_txt, (q_box.x + 8, q_box.y + 6))

            status_str = "[ĐÃ XONG]" if is_done else ("[ĐANG LÀM]" if is_active else "[SẴN SÀNG]")
            status_col = (115, 255, 145) if is_done else ((255, 215, 65) if is_active else (165, 215, 255))
            screen.blit(font_xs.render(status_str, True, status_col), (q_box.right - 88, q_box.y + 6))

            sub_txt = f"{q.giver_name} -> {q.receiver_name} | {q.item_label}"
            screen.blit(font_xs.render(sub_txt, True, (200, 185, 168)), (q_box.x + 8, q_box.y + 22))

            qy += 48

        # Danh sách đơn hàng đặc biệt mùa vụ & mốc tim
        qy += 8
        screen.blit(font_sm.render("ĐƠN ĐẶC BIỆT MÙA VỤ & MỐC TIM:", True, (255, 225, 95)), (left_x, qy))
        qy += 26

        special_orders = [
            (
                "Đơn VIP 5 ♥: Tiệc Làng Thịnh Soạn",
                "Giao 4 Bí Ngô & 2 Cá Hồ cho Gus Saloon",
                "Thưởng: +350G, +150đ | Yêu cầu: 5 ♥ với Gus / Lewis",
                (255, 215, 65),
            ),
            (
                "Đơn Mùa Xuân: Lễ Hội Hoa Anh Đào",
                "Mang 4 Quả Đào Tiên ra Bờ Đảo Bắc Map 3",
                "Thưởng: +280G, Vương Miện Hoa | Yêu cầu: Mùa Xuân [V]",
                (255, 160, 200),
            ),
            (
                "Đơn Kiểm Định 3 ♥: Xưởng Mộc Robin",
                "Chế tạo giàn tưới tiêu tự động cho Nông trại",
                "Thưởng: +220G, Giảm 20% Xưởng | Yêu cầu: 3 ♥ Robin",
                (125, 245, 145),
            ),
        ]

        for s_title, s_desc, s_rew, s_col in special_orders:
            sp_box = pygame.Rect(left_x, qy, left_w, 48)
            pygame.draw.rect(screen, (38, 26, 18), sp_box, border_radius=6)
            pygame.draw.rect(screen, s_col, sp_box, width=1, border_radius=6)

            screen.blit(font_xs.render(s_title, True, s_col), (sp_box.x + 8, sp_box.y + 4))
            screen.blit(font_xs.render(s_desc, True, (235, 225, 210)), (sp_box.x + 8, sp_box.y + 18))
            screen.blit(font_xs.render(s_rew, True, (205, 190, 160)), (sp_box.x + 8, sp_box.y + 32))
            qy += 54

        # Cột Phải (w = 440): Tin Đồn & Bí Mật Khám Phá
        right_w = 440
        right_x = mx + 530
        right_y = my + 118

        screen.blit(font_md.render("TIN ĐỒN & BÍ MẬT KHÁM PHÁ", True, (255, 235, 110)), (right_x, right_y))
        screen.blit(font_xs.render("Gợi ý từ các cuộc trò chuyện thân mật với cư dân thị trấn", True, (215, 195, 175)), (right_x, right_y + 24))

        secrets = [
            (
                "[NẤM] NẤM RỪNG QUÝ VEN MỎM ĐÁ (MAP 3)",
                "Vị trí: Bờ phía Tây-Bắc hồ nước và quanh các gốc cây cổ thụ Đảo Rừng.\nGợi ý: Thường xuất hiện sau những cơn mưa rào mùa xuân, hồi phục thể lực rất tốt.",
                (235, 165, 105),
            ),
            (
                "[QUẢ] BỤI QUẢ MỌNG DẠI HOANG DÃ (MAP 4 & MAP 3)",
                "Vị trí: Dọc dòng suối nhỏ góc Tây-Nam Map 4 và góc Đảo Câu Cá Map 3.\nGợi ý: Quả mọng dại chín mọng có thể hái tự do để ăn hoặc làm quà tặng bình dân.",
                (255, 140, 160),
            ),
            (
                "[HOA] HOA CÚC VÀNG & THẢO DƯỢC (MAP 1 BỜ SÔNG)",
                "Vị trí: Bãi cỏ dọc bờ sông và gần chân cầu đá Map 1.\nGợi ý: Là món quà rất được lòng Bà Evelyn và Cô Haley để kết bạn nhanh chóng.",
                (255, 235, 110),
            ),
            (
                "[LỄ HỘI] LỄ HỘI HOA ANH ĐÀO MÙA XUÂN (QUẢNG TRƯỜNG MAP 1)",
                "Vị trí: Quảng trường thị trấn Map 1 vào Ngày 3 mỗi mùa (hoặc bấm phím [L]).\nGợi ý: Dây cờ lễ hội rực rỡ giăng khắp quảng trường và mưa cánh hoa đào tuyệt đẹp!",
                (255, 185, 220),
            ),
        ]

        sy = right_y + 52
        for sec_title, sec_desc, sec_col in secrets:
            sec_box = pygame.Rect(right_x, sy, right_w, 88)
            pygame.draw.rect(screen, (34, 22, 14), sec_box, border_radius=8)
            pygame.draw.rect(screen, (105, 75, 46), sec_box, width=1, border_radius=8)

            screen.blit(font_sm.render(sec_title, True, sec_col), (sec_box.x + 12, sec_box.y + 8))
            lines = sec_desc.split("\n")
            for li, line in enumerate(lines):
                screen.blit(font_xs.render(line, True, (215, 205, 185)), (sec_box.x + 12, sec_box.y + 32 + li * 20))

            sy += 100

    # --------------------------------------------------------------------------
    # TAB 3: LƯU / TẢI GAME (3 SLOTS) & HƯỚNG DẪN CORE LOOP
    # --------------------------------------------------------------------------
    def _render_tab3_save_loop(
        self, screen: pygame.Surface, game: Any, mx: int, my: int, mw: int, mh: int
    ) -> None:
        font_xs = getattr(game, "font_xs", None) or pygame.font.SysFont("Segoe UI", 13, bold=True)
        font_sm = getattr(game, "font_sm", None) or pygame.font.SysFont("Segoe UI", 15, bold=True)
        font_md = getattr(game, "font_md", None) or pygame.font.SysFont("Segoe UI", 18, bold=True)
        mouse_pos = pygame.mouse.get_pos()

        # Phần trên: 3 Save Slot cards
        top_y = my + 118
        screen.blit(font_md.render("HỆ THỐNG LƯU / TẢI GAME (3 SAVE SLOTS ĐỘC LẬP)", True, (255, 235, 110)), (mx + 24, top_y))
        screen.blit(font_xs.render("Lưu lại toàn bộ Vàng (G), Điểm uy tín, Thiện cảm NPC, Khay đồ và Bản đồ đang đứng", True, (215, 195, 175)), (mx + 24, top_y + 24))

        slot_w = 300
        slot_h = 168
        slot_start_x = mx + 24
        slot_gap = 26
        slot_y = top_y + 48

        self.save_btn_rects.clear()
        self.load_btn_rects.clear()

        for s_idx in (1, 2, 3):
            sx = slot_start_x + (s_idx - 1) * (slot_w + slot_gap)
            s_rect = pygame.Rect(sx, slot_y, slot_w, slot_h)

            pygame.draw.rect(screen, (36, 24, 16), s_rect, border_radius=8)
            pygame.draw.rect(screen, (215, 165, 55), s_rect, width=2, border_radius=8)

            # Tiêu đề Slot
            s_title = font_sm.render(f"SAVE SLOT {s_idx}", True, (255, 235, 110))
            screen.blit(s_title, (sx + 14, slot_y + 10))

            info = game.state.get_slot_info(s_idx)
            if info is not None:
                screen.blit(font_xs.render(f"Thời gian: {info.get('save_time', 'N/A')}", True, (135, 235, 255)), (sx + 14, slot_y + 34))
                screen.blit(font_xs.render(f"Vàng: {info.get('gold', 0)}G  |  Điểm: {info.get('score', 0)}đ  |  Mạng: {info.get('hearts', 3)}♥", True, (255, 225, 95)), (sx + 14, slot_y + 54))
                screen.blit(font_xs.render(f"Bản đồ: Map {info.get('current_map_id', 1)}  |  Đã xong: {info.get('completed_quests_count', 0)} đơn", True, (185, 242, 175)), (sx + 14, slot_y + 74))
                inv_items = info.get("inventory", [])
                inv_str = f"Khay đồ: {len(inv_items)} món" if inv_items else "Khay đồ: Trống"
                screen.blit(font_xs.render(inv_str, True, (215, 205, 190)), (sx + 14, slot_y + 94))
            else:
                screen.blit(font_xs.render("[Ô LƯU TRỐNG — CHƯA CÓ DỮ LIỆU]", True, (175, 155, 140)), (sx + 14, slot_y + 42))
                screen.blit(font_xs.render("Sẵn sàng ghi đè dữ liệu ca làm việc mới", True, (145, 135, 120)), (sx + 14, slot_y + 66))

            # 2 Nút Lưu / Tải trong từng Slot
            btn_w = 130
            btn_h = 32
            btn_y = slot_y + slot_h - 40

            save_btn = pygame.Rect(sx + 12, btn_y, btn_w, btn_h)
            load_btn = pygame.Rect(sx + slot_w - btn_w - 12, btn_y, btn_w, btn_h)
            self.save_btn_rects[s_idx] = save_btn
            self.load_btn_rects[s_idx] = load_btn

            s_hov = save_btn.collidepoint(mouse_pos)
            pygame.draw.rect(screen, (34, 115, 52) if not s_hov else (48, 145, 68), save_btn, border_radius=6)
            pygame.draw.rect(screen, (115, 245, 145), save_btn, width=1, border_radius=6)
            slbl = font_xs.render(f"LƯU SLOT {s_idx}", True, (255, 255, 255))
            screen.blit(slbl, (save_btn.centerx - slbl.get_width() // 2, save_btn.centery - slbl.get_height() // 2))

            l_hov = load_btn.collidepoint(mouse_pos)
            has_data = (info is not None)
            l_bg = (36, 85, 145) if (has_data and not l_hov) else ((48, 110, 185) if (has_data and l_hov) else (54, 44, 40))
            l_bd = (115, 195, 255) if has_data else (95, 80, 75)
            pygame.draw.rect(screen, l_bg, load_btn, border_radius=6)
            pygame.draw.rect(screen, l_bd, load_btn, width=1, border_radius=6)
            llbl = font_xs.render(f"TẢI SLOT {s_idx}", True, (255, 255, 255) if has_data else (150, 140, 135))
            screen.blit(llbl, (load_btn.centerx - llbl.get_width() // 2, load_btn.centery - llbl.get_height() // 2))

        # Phần dưới: Tóm Tắt Vòng Lặp Chơi Chuẩn Stardew Valley (Core Loop)
        loop_y = slot_y + slot_h + 20
        screen.blit(font_md.render("CẨM NANG VÒNG LẶP CHƠI CỐT LÕI (CORE GAMEPLAY LOOP)", True, (255, 235, 110)), (mx + 24, loop_y))

        loop_box = pygame.Rect(mx + 24, loop_y + 26, mw - 48, 180)
        pygame.draw.rect(screen, (34, 22, 14), loop_box, border_radius=8)
        pygame.draw.rect(screen, (112, 76, 46), loop_box, width=1, border_radius=8)

        steps = [
            (
                "[1] BƯỚC 1: THU HOẠCH, HÁI LƯỢM & CÂU CÁ",
                "Hái quả chín tại vườn Map 2 (Táo, Cam, Đào), thu hoạch ruộng dâu/bí/bắp, hoặc câu cá tại Bến Hồ Map 3.\nBán nông sản dư thừa tại Thùng Giao Hàng Map 2 để tích lũy Vàng (G) và Điểm uy tín.",
                (255, 225, 95),
            ),
            (
                "[2] BƯỚC 2: AN TOÀN HRI & QUẠT XANH LỊCH SỰ",
                "Tiến vào Quạt Xanh [0.75m - 1.45m] trước mặt NPC để giao tiếp. Radar An Toàn 8.7 tự động giảm tốc từ xa 1.65m\nđối với Người Cao Tuổi & Trẻ Nhỏ để tránh mọi nguy cơ va chạm và bảo vệ trọn vẹn 3 Mạng Uy Tín.",
                (125, 245, 155),
            ),
            (
                "[3] BƯỚC 3: TẶNG QUÀ THIỆN CẢM [G] & MỐC TIM",
                "Cầm nông sản trên tay và bấm [G] trước mặt cư dân. Tặng đúng món yêu thích (+120 tim, +40đ) để nhanh chóng\nmở Mốc 3 ♥ (+50G, giảm 20% Xưởng) và Mốc 5 ♥ (+120G, mở Đơn Đặt Hàng Đặc Biệt).",
                (255, 160, 190),
            ),
            (
                "[4] BƯỚC 4: ĐẦU TƯ NÂNG CẤP XƯỞNG ROBIN [U] & QUA NGÀY [N]",
                "Dùng Vàng tích lũy mở Xưởng Robin [U] để nâng cấp Khay Chứa 6 ô, Cánh tay thu hoạch siêu tốc 0.75s\nvà Radar An Toàn HRI Tự Động, rồi bấm [N] tổng kết cuối ngày để sang Ngày & Mùa vụ mới!",
                (140, 225, 255),
            ),
        ]

        step_y = loop_box.y + 10
        for st_title, st_desc, st_col in steps:
            screen.blit(font_xs.render(st_title, True, st_col), (loop_box.x + 12, step_y))
            for li, lstr in enumerate(st_desc.split("\n")):
                screen.blit(font_xs.render(lstr, True, (220, 210, 195)), (loop_box.x + 12, step_y + 15 + li * 13))
            step_y += 42
