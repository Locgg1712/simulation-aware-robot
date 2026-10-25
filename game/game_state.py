# game/game_state.py
"""
Kiến trúc Quản lý Trạng Thái Game Tập Trung (Central GameState & Persistence)
cho thế giới FarmBot Town:
1. InventorySlot: Lưu trữ từng món đồ trong khay kèm chất lượng Sao (Thường, Bạc ★, Vàng ★★, Iridium ★★★).
2. ForageItem: Quản lý các vật phẩm nhặt dã ngoại sinh ngẫu nhiên mỗi ngày (Nấm rừng, Quả mọng, Hoa cúc vàng).
3. GameState:
   - Nạp và quản lý items_db, npcs_db, quests_db từ 3 file JSON trong `game/data/`.
   - Quản lý Chu kỳ Ngày (Day), Mùa vụ (Season - Xuân, Hạ, Thu, Đông), Lễ hội thị trấn (Festival).
   - Theo dõi kinh tế: Vàng kiếm trong ngày, số đơn hoàn thành, nông sản giao bán, số va chạm HRI.
   - Quản lý persistent_harvest_state: bảo toàn sinh trưởng cây trồng qua lại giữa 5 Map.
   - Quản lý dropped_items: vật phẩm bị rơi khi Robot ngã cấp 2 để nhặt lại.
   - Thống kê cuối ngày (End-of-day Summary Modal phong cách Stardew Valley).
   - Hệ thống Lưu / Đọc 3 Slot Save Game (Save/Load Slots) định dạng JSON.
"""

from __future__ import annotations

import json
import math
import os
import random
from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

import pygame

from .constants import (
    CHARGING_DOCKS,
    ITEM_NAMES_VI,
    SCORE_HARVEST_FRUIT,
    SCREEN_H,
    SCREEN_W,
    TILE_SIZE,
    px_to_m,
)
from .farming import apply_state_dict_to_spot, spot_to_state_dict


# Bảng mở rộng tên tiếng Việt cho tất cả các vật phẩm bao gồm Foraging
EXTENDED_ITEM_NAMES_VI: dict[str, str] = {
    **ITEM_NAMES_VI,
    "mushroom": "Nấm Rừng Thơm",
    "wild_berry": "Quả Mọng Rừng",
    "golden_flower": "Hoa Cúc Vàng",
    "iridium_ore": "Khoáng Thạch Iridium",
}


# ==============================================================================
# 1. CẤU TRÚC DỮ LIỆU INVENTORY SLOT VỚI CHẤT LƯỢNG SAO (STAR QUALITY)
# ==============================================================================

@dataclass
class InventorySlot:
    """
    Mỗi ô trong khay chứa đồ của Robot đi kèm phẩm chất Stardew Valley:
    - 0: Thường (Hệ số x1.0, không có sao)
    - 1: Bạc ★ (Hệ số x1.25, giá trị tăng 25%)
    - 2: Vàng ★★ (Hệ số x1.50, giá trị tăng 50%)
    - 3: Iridium ★★★ (Hệ số x2.0, giá trị tăng gấp đôi)
    """
    item_key: str
    quality: int = 0
    quantity: int = 1

    @property
    def stars_label(self) -> str:
        """Ký hiệu sao hiển thị trên giao diện HUD và thông báo."""
        if self.quality == 1:
            return "*"
        elif self.quality == 2:
            return "**"
        elif self.quality >= 3:
            return "***"
        return ""

    @property
    def quality_name_vi(self) -> str:
        """Tên tiếng Việt của phẩm chất nông sản."""
        names = {0: "Thường", 1: "Sao Bạc", 2: "Sao Vàng", 3: "Sao Iridium"}
        return names.get(self.quality, "Thường")

    @property
    def quality_color(self) -> tuple[int, int, int]:
        """Màu sắc biểu trưng cho từng cấp chất lượng."""
        colors = {
            0: (235, 235, 235),
            1: (195, 205, 230),  # Bạc sáng
            2: (255, 220, 50),   # Vàng óng
            3: (210, 110, 240),  # Iridium tím huyền ảo
        }
        return colors.get(self.quality, (235, 235, 235))

    def sell_price(self, base_price: int) -> int:
        """
        Tính giá bán thực tế sau khi nhân hệ số chất lượng Stardew Valley:
        quality 0 -> x1.0, quality 1 -> x1.25, quality 2 -> x1.5, quality 3 -> x2.0.
        """
        multipliers = {0: 1.0, 1: 1.25, 2: 1.5, 3: 2.0}
        mult = multipliers.get(self.quality, 1.0)
        return int(round(base_price * mult))


# ==============================================================================
# 2. CẤU TRÚC DỮ LIỆU VẬT PHẨM NHẶT DÃ NGOẠI (FORAGE ITEM)
# ==============================================================================

@dataclass
class ForageItem:
    """Vật phẩm nhặt dã ngoại hoang dã xuất hiện rải rác ngoài tự nhiên trên các Map."""
    item_key: str
    x: float
    y: float
    map_id: int
    collected: bool = False
    quality: int = 0


# ==============================================================================
# CẤU HÌNH 4 CẤP CHỨNG NHẬN AN TOÀN HRI & 10 THÀNH TỰU DANH GIÁ
# ==============================================================================

CERTIFICATIONS_CONFIG: list[dict] = [
    {
        "level": 1,
        "id": "cert_lv1_novice",
        "title": "Chứng Nhận Cấp I: Robot Tập Sự Thung Lũng",
        "short_tag": "CHỨNG NHẬN HRI CẤP I",
        "req_desc": "Hoàn thành >= 2 đơn hàng & Đạt >= 150đ Uy tín",
        "perk_desc": "Thưởng +100G & Mở khóa Gọi Xe Kéo AGV Liên Bản Đồ [C]",
        "reward_gold": 100,
    },
    {
        "level": 2,
        "id": "cert_lv2_courier",
        "title": "Chứng Nhận Cấp II: Chuyên Gia Giao Vận ISO-HRI",
        "short_tag": "CHỨNG NHẬN HRI CẤP II",
        "req_desc": "Hoàn thành >= 5 đơn hàng, Điểm >= 450đ & An tâm HRI >= 75%",
        "perk_desc": "Thưởng +200G & Tăng Trợ cấp An Toàn cuối ngày lên +85G",
        "reward_gold": 200,
    },
    {
        "level": 3,
        "id": "cert_lv3_master_agro",
        "title": "Chứng Nhận Cấp III: Kỹ Sư Nông Nghiệp Tự Động",
        "short_tag": "CHỨNG NHẬN HRI CẤP III",
        "req_desc": "Mua đủ 3 nâng cấp Robin, Bán >= 6 nông sản & 2 Sự kiện",
        "perk_desc": "Thưởng +350G & Tăng +15% giá bán nông sản tại Thùng Giao Hàng",
        "reward_gold": 350,
    },
    {
        "level": 4,
        "id": "cert_lv4_golden_citizen",
        "title": "Chứng Nhận Cấp IV: Huân Chương Vàng Công Dân HRI",
        "short_tag": "★ CÔNG DÂN VÀNG HRI (CẤP IV)",
        "req_desc": "Điểm >= 1000đ, Hoàn thành >= 10 đơn & >= 3 cư dân đạt 4♥",
        "perk_desc": "Thưởng +600G & Cúp Vàng Thị Trưởng Lewis (Mục tiêu Endgame)",
        "reward_gold": 600,
    },
]

ACHIEVEMENTS_CONFIG: list[dict] = [
    {
        "id": "first_delivery",
        "title": "Chuyến Hàng Đầu Tiên",
        "desc": "Hoàn thành đơn giao hàng đầu tiên cho cư dân.",
        "reward_gold": 40,
        "reward_score": 30,
        "icon": "icon_parcel",
    },
    {
        "id": "agv_partner",
        "title": "Đội Vận Tải Cơ Giới AGV",
        "desc": "Đẩy nhẹ, gọi Xe Kéo AGV đi theo [C] hoặc chất hàng lên AGV.",
        "reward_gold": 50,
        "reward_score": 40,
        "icon": "carrot",
    },
    {
        "id": "gentle_yielder",
        "title": "Robot Lịch Thiệp Chuẩn HRI",
        "desc": "Nhường đường văn minh cho cư dân đi bộ đủ 5 lần.",
        "reward_gold": 60,
        "reward_score": 50,
        "icon": "icon_heart",
    },
    {
        "id": "master_angler",
        "title": "Ngư Phủ Cơ Khí Bến Hồ",
        "desc": "Câu thành công 3 con cá tươi tại Bến Hồ Map 3.",
        "reward_gold": 75,
        "reward_score": 50,
        "icon": "fish",
    },
    {
        "id": "green_thumb",
        "title": "Bàn Tay Vàng Nông Nghiệp",
        "desc": "Xuất bán tích lũy 6 nông sản qua Thùng Giao Hàng hoặc AGV.",
        "reward_gold": 80,
        "reward_score": 60,
        "icon": "strawberry",
    },
    {
        "id": "beloved_neighbor",
        "title": "Người Bạn Của Mọi Nhà",
        "desc": "Đạt mốc thiện cảm >= 3 Trái Tim với ít nhất 3 cư dân.",
        "reward_gold": 100,
        "reward_score": 80,
        "icon": "golden_flower",
    },
    {
        "id": "robin_maxed",
        "title": "Siêu Robot Toàn Diện",
        "desc": "Nâng cấp tối đa cả 3 hạng mục tại Xưởng Mộc Robin [U].",
        "reward_gold": 120,
        "reward_score": 100,
        "icon": "icon_coin",
    },
    {
        "id": "event_hero",
        "title": "Người Hùng Sự Kiện Thị Trấn",
        "desc": "Hoàn thành 3 Sự kiện Thế giới Ngẫu nhiên trong thị trấn.",
        "reward_gold": 120,
        "reward_score": 90,
        "icon": "iridium_ore",
    },
    {
        "id": "zero_accident_streak",
        "title": "Chuỗi Ca Trực Không Tai Nạn",
        "desc": "Hoàn thành 3 ngày làm việc liên tiếp có đơn hàng và 0 va chạm.",
        "reward_gold": 150,
        "reward_score": 120,
        "icon": "icon_heart",
    },
    {
        "id": "mayor_grand_cup",
        "title": "Cúp Vàng Thị Trưởng Lewis",
        "desc": "Đạt Chứng Nhận Cấp IV: Công Dân Tự Hành Danh Dự Pelican!",
        "reward_gold": 300,
        "reward_score": 200,
        "icon": "icon_coin",
    },
]


# ==============================================================================
# 3. LỚP QUẢN LÝ TRẠNG THÁI GAME TRUNG TÂM (GAMESTATE)
# ==============================================================================

class GameState:
    """
    Lớp điều phối trạng thái trung tâm của FarmBot Town:
    - Lưu trữ cơ sở dữ liệu vật phẩm, dân làng, đơn đặt hàng từ file JSON.
    - Quản lý thời gian, ngày, mùa vụ, lễ hội thị trấn.
    - Duy trì trạng thái ruộng cây trồng khi chuyển Map (Persistent Harvest).
    - Tạo và xử lý vật phẩm dã ngoại (Foraging) và rơi đồ khi ngã (Knockdown Drop).
    - Hiển thị bảng tổng kết cuối ngày và lưu/đọc tiến trình chơi qua 3 Slot.
    """

    SEASONS: list[str] = ["spring", "summer", "fall", "winter"]
    SEASON_NAMES_VI: dict[str, str] = {
        "spring": "Mùa Xuân",
        "summer": "Mùa Hè",
        "fall": "Mùa Thu",
        "winter": "Mùa Đông",
    }

    def __init__(self) -> None:
        # Đường dẫn thư mục dữ liệu và thư mục lưu game
        self.base_dir: str = os.path.dirname(os.path.abspath(__file__))
        self.data_dir: str = os.path.join(self.base_dir, "data")
        self.saves_dir: str = os.path.join(self.base_dir, "saves")
        os.makedirs(self.data_dir, exist_ok=True)
        os.makedirs(self.saves_dir, exist_ok=True)

        # Nạp dữ liệu JSON
        self.items_db: dict[str, dict] = self._load_json_data("items.json", default_factory=self._fallback_items)
        self.npcs_db: dict[str, dict] = self._load_json_data("npcs.json", default_factory=self._fallback_npcs)
        self.quests_db: list[dict] = self._load_json_data("quests.json", default_factory=self._fallback_quests)

        # Tiến trình Ngày & Mùa vụ
        self.day: int = 1
        self.season_idx: int = 0
        self.festival_active: bool = False

        # Thống kê hoạt động kinh tế trong ngày
        self.daily_gold_earned: int = 0
        self.daily_orders_completed: int = 0
        self.daily_crops_shipped: int = 0
        self.daily_collisions: int = 0

        # Thống kê tích lũy dài hạn, Chứng Nhận HRI (0..4), Thành Tựu & Đồng hành AGV
        self.total_crops_shipped: int = 0
        self.total_fish_caught: int = 0
        self.total_yields: int = 0
        self.safe_days_streak: int = 0
        self.certification_level: int = 0
        self.unlocked_achievements: list[str] = []
        self.agv_companion_active: bool = False
        self.agv_cargo: list[dict] = []

        # Modal Thống Kê Cuối Ngày
        self.summary_open: bool = False
        self.last_summary: dict = {}

        # Danh sách Slot Meta (song hành với game.robot.inventory)
        self.slot_meta: list[InventorySlot] = []

        # Trạng thái ruộng cây trồng bền vững trên tất cả 5 Map
        # Format: { spot_id: {"has_produce": bool, "regrow_timer": float, "growth_stage": int, "map_id": int} }
        self.persistent_harvest_state: dict[str, dict] = {}

        # Danh sách vật phẩm nhặt dã ngoại và vật phẩm rơi khi ngã
        self.forage_items: list[ForageItem] = []
        self.dropped_items: list[dict] = []

        # Khởi tạo vật phẩm nhặt dã ngoại cho Ngày 1
        self.spawn_daily_forage_items()

    @property
    def current_season(self) -> str:
        """Mã mùa hiện tại ('spring', 'summer', 'fall', 'winter')."""
        return self.SEASONS[self.season_idx % len(self.SEASONS)]

    @property
    def current_season_name(self) -> str:
        """Tên tiếng Việt của mùa hiện tại."""
        return self.SEASON_NAMES_VI.get(self.current_season, "Mùa Xuân")

    def get_item_name(self, item_key: str) -> str:
        """Lấy tên tiếng Việt của một vật phẩm từ items_db hoặc EXTENDED_ITEM_NAMES_VI."""
        if item_key in self.items_db:
            return self.items_db[item_key].get("name_vi", item_key)
        return EXTENDED_ITEM_NAMES_VI.get(item_key, item_key)

    def get_item_base_price(self, item_key: str) -> int:
        """Lấy giá bán cơ bản của vật phẩm."""
        if item_key in self.items_db:
            return int(self.items_db[item_key].get("base_price", 35))
        return 35

    # --------------------------------------------------------------------------
    # NẠP DỮ LIỆU TỪ FILE JSON VỚI DỰ PHÒNG AN TOÀN (FALLBACK)
    # --------------------------------------------------------------------------

    def _load_json_data(self, filename: str, default_factory) -> Any:
        path = os.path.join(self.data_dir, filename)
        if os.path.isfile(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                print(f"[GameState] Cảnh báo lỗi nạp {filename}: {e}, sử dụng dữ liệu mặc định.")
        return default_factory()

    def _fallback_items(self) -> dict[str, dict]:
        return {
            k: {"name_vi": v, "category": "crop", "base_price": 35, "seasons": ["spring", "summer", "fall", "winter"]}
            for k, v in EXTENDED_ITEM_NAMES_VI.items()
        }

    def _fallback_npcs(self) -> dict[str, dict]:
        return {}

    def _fallback_quests(self) -> list[dict]:
        return []

    # --------------------------------------------------------------------------
    # ĐỒNG BỘ KHAY ĐỒ ROBOT (INVENTORY & SLOT_META)
    # --------------------------------------------------------------------------

    def sync_slot_meta_with_inventory(self, inventory: list[str]) -> None:
        """Đảm bảo danh sách slot_meta luôn đồng bộ tuyệt đối với game.robot.inventory."""
        if not isinstance(self.slot_meta, list):
            if isinstance(self.slot_meta, dict):
                converted: list[InventorySlot] = []
                for idx in range(len(inventory)):
                    raw = self.slot_meta.get(idx, {})
                    q = int(raw.get("quality", 0)) if isinstance(raw, dict) else getattr(raw, "quality", 0)
                    converted.append(InventorySlot(item_key=inventory[idx], quality=q))
                self.slot_meta = converted
            else:
                self.slot_meta = []

        while len(self.slot_meta) < len(inventory):
            new_item = inventory[len(self.slot_meta)]
            self.slot_meta.append(InventorySlot(item_key=new_item, quality=0))
        while len(self.slot_meta) > len(inventory):
            self.slot_meta.pop()
        for i, item_key in enumerate(inventory):
            entry = self.slot_meta[i]
            if isinstance(entry, dict):
                q = int(entry.get("quality", 0))
                self.slot_meta[i] = InventorySlot(item_key=item_key, quality=q)
            elif not isinstance(entry, InventorySlot) or entry.item_key != item_key:
                q = getattr(entry, "quality", 0) if getattr(entry, "item_key", None) == item_key else 0
                self.slot_meta[i] = InventorySlot(item_key=item_key, quality=q)

    def add_inventory_item(
        self,
        game: Any,
        item_key: str,
        quality: int = 0,
        quantity: int = 1,
    ) -> bool:
        """
        Thêm vật phẩm vào khay chứa đồ của Robot kèm phẩm chất sao.
        Nếu khay Robot đã đầy nhưng có Xe Kéo AGV đang đi theo (hoặc đứng gần <= 95px)
        và thùng AGV còn chỗ trống (< 4 ô), tự động chất hàng lên thùng AGV!
        """
        max_cap = getattr(game.robot, "max_inventory", getattr(game.robot, "max_capacity", 4))
        if len(game.robot.inventory) < max_cap:
            game.robot.inventory.append(item_key)
            self.slot_meta.append(InventorySlot(item_key=item_key, quality=quality, quantity=quantity))
            return True

        # Nếu khay Robot đầy -> kiểm tra Xe Kéo AGV đi theo hoặc đứng gần
        for agv in getattr(game, "agvs", []):
            dist = math.hypot(game.robot.x - agv.x, game.robot.y - agv.y)
            if (getattr(agv, "mode", "") == "follow" or dist <= 95.0) and len(agv.cargo) < getattr(agv, "max_cargo", 4):
                agv.cargo.append({"item_key": item_key, "quality": int(quality), "quantity": int(quantity)})
                self.agv_cargo = [dict(c) for c in agv.cargo]
                self.unlock_achievement(game, "agv_partner")
                item_vi = self.get_item_name(item_key)
                if hasattr(game, "vfx") and game.vfx is not None:
                    game.vfx.push_toast(
                        f"Chất lên AGV: {item_vi}",
                        f"Thùng Xe Kéo AGV: {len(agv.cargo)}/{agv.max_cargo} ô",
                        item_key,
                        (125, 245, 185),
                    )
                return True
        return False

    def remove_inventory_at(self, game: Any, idx: int) -> tuple[str, Optional[InventorySlot]]:
        """Lấy một món đồ ra khỏi khay chứa đồ của Robot tại vị trí idx."""
        if 0 <= idx < len(game.robot.inventory):
            item_key = game.robot.inventory.pop(idx)
            slot = self.slot_meta.pop(idx) if idx < len(self.slot_meta) else None
            return item_key, slot
        return "", None

    # --------------------------------------------------------------------------
    # BẢO TOÀN TRẠNG THÁI RUỘNG CÂY TRỒNG KHI CHUYỂN MAP (PERSISTENT HARVEST)
    # --------------------------------------------------------------------------

    def save_map_harvest_to_state(self, game: Any) -> None:
        """Lưu trạng thái ruộng cây trồng và cây ăn quả của Map hiện tại."""
        all_spots = getattr(game, "harvest_spots", []) + getattr(game, "deco_fields", [])
        current_map = getattr(game, "current_map_id", 1)
        for spot in all_spots:
            entry = spot_to_state_dict(spot)
            entry["map_id"] = current_map
            self.persistent_harvest_state[spot.spot_id] = entry

    def sync_map_harvest_from_state(self, game: Any) -> None:
        """Đồng bộ trạng thái ruộng cây trồng từ persistent_harvest_state khi vào Map mới."""
        all_spots = getattr(game, "harvest_spots", []) + getattr(game, "deco_fields", [])
        for spot in all_spots:
            if spot.spot_id in self.persistent_harvest_state:
                data = self.persistent_harvest_state[spot.spot_id]
                apply_state_dict_to_spot(spot, data)

    # --------------------------------------------------------------------------
    # HỆ THỐNG VẬT PHẨM DÃ NGOẠI HOANG DÃ (FORAGING SYSTEM)
    # --------------------------------------------------------------------------

    def spawn_daily_forage_items(self) -> None:
        """
        Khởi tạo ngẫu nhiên 3-5 vật phẩm nhặt dã ngoại (nấm rừng, quả mọng, hoa cúc)
        trên các vị trí an toàn ở Map 1, 2, 3, 4 mỗi khi bước sang ngày mới.
        """
        self.forage_items.clear()

        candidate_positions = [
            # Map 1: Quảng Trường & Bờ Sông
            {"map_id": 1, "x": 28.5 * 32.0, "y": 18.5 * 32.0, "item_key": "golden_flower"},
            {"map_id": 1, "x": 7.5 * 32.0, "y": 18.5 * 32.0, "item_key": "wild_berry"},
            {"map_id": 1, "x": 20.0 * 32.0, "y": 6.8 * 32.0, "item_key": "golden_flower"},
            # Map 2: Đại Nông Trại
            {"map_id": 2, "x": 8.0 * 32.0, "y": 18.2 * 32.0, "item_key": "wild_berry"},
            {"map_id": 2, "x": 14.5 * 32.0, "y": 17.5 * 32.0, "item_key": "golden_flower"},
            {"map_id": 2, "x": 4.5 * 32.0, "y": 12.0 * 32.0, "item_key": "mushroom"},
            # Map 3: Đảo Rừng Xanh & Bến Hồ Câu Cá
            {"map_id": 3, "x": 28.5 * 32.0, "y": 8.2 * 32.0, "item_key": "mushroom"},
            {"map_id": 3, "x": 8.2 * 32.0, "y": 16.5 * 32.0, "item_key": "mushroom"},
            {"map_id": 3, "x": 25.8 * 32.0, "y": 19.2 * 32.0, "item_key": "wild_berry"},
            {"map_id": 3, "x": 12.5 * 32.0, "y": 8.5 * 32.0, "item_key": "golden_flower"},
            # Map 4: Khu Dân Cư & Vườn Hoa Gia Đình
            {"map_id": 4, "x": 18.5 * 32.0, "y": 16.2 * 32.0, "item_key": "golden_flower"},
            {"map_id": 4, "x": 6.5 * 32.0, "y": 8.5 * 32.0, "item_key": "wild_berry"},
            {"map_id": 4, "x": 31.0 * 32.0, "y": 18.5 * 32.0, "item_key": "mushroom"},
        ]

        # Chọn ngẫu nhiên 4-6 điểm cho ngày mới
        count = min(len(candidate_positions), random.randint(4, 6))
        chosen = random.sample(candidate_positions, count)

        for pos in chosen:
            # Tỷ lệ phẩm chất dã ngoại: 70% Thường (0), 20% Sao Bạc (1), 10% Sao Vàng (2)
            rand_val = random.random()
            if rand_val < 0.70:
                q = 0
            elif rand_val < 0.90:
                q = 1
            else:
                q = 2

            self.forage_items.append(
                ForageItem(
                    item_key=pos["item_key"],
                    x=pos["x"],
                    y=pos["y"],
                    map_id=pos["map_id"],
                    collected=False,
                    quality=q,
                )
            )

    def try_pickup_forage(self, game: Any) -> bool:
        """
        Kiểm tra và thực hiện nhặt vật phẩm dã ngoại khi Robot đứng gần (khoảng cách <= 52.0px).
        Cộng điểm kinh nghiệm, thêm vào khay đồ và hiển thị thông báo.
        """
        if getattr(game, "in_interior", False):
            return False

        current_map = getattr(game, "current_map_id", 1)
        robot_x, robot_y = game.robot.x, game.robot.y

        for item in self.forage_items:
            if item.collected or item.map_id != current_map:
                continue

            dist = math.hypot(robot_x - item.x, robot_y - item.y)
            if dist <= 52.0:
                # Kiểm tra dung lượng khay đồ
                max_cap = getattr(game.robot, "max_inventory", getattr(game.robot, "max_capacity", 4))
                if len(game.robot.inventory) >= max_cap:
                    if hasattr(game, "set_banner"):
                        game.set_banner(
                            "Khay chứa đồ đã đầy! Hãy bán bớt nông sản hoặc nâng cấp khay đồ tại Xưởng Robin [U].",
                            (255, 185, 95),
                        )
                    return False

                # Nhặt vật phẩm
                item.collected = True
                self.add_inventory_item(game, item.item_key, quality=item.quality)

                item_name = self.get_item_name(item.item_key)
                star = InventorySlot(item_key=item.item_key, quality=item.quality).stars_label

                if hasattr(game, "add_score"):
                    game.add_score(25, f"Thu hái {item_name}{star}")

                if hasattr(game, "floating_texts"):
                    from .entities import FloatingText
                    game.floating_texts.append(
                        FloatingText(f"+1 {item_name} {star}", item.x, item.y - 24, (120, 255, 140))
                    )

                if hasattr(game, "audio"):
                    game.audio.play_sfx("harvest")
                if hasattr(game, "vfx"):
                    game.vfx.push_toast(
                        f"Dã ngoại: +1 {item_name} {star}".strip(),
                        "Đã nhặt vật phẩm tự nhiên (+25đ)",
                        item.item_key,
                        (145, 255, 165),
                    )
                if hasattr(game, "set_banner"):
                    game.set_banner(
                        f"Đã nhặt: {item_name} {star} (+25đ Dã Ngoại)!".strip(),
                        (155, 245, 175),
                    )
                return True

        return False

    def render_forage_items(self, screen: pygame.Surface, game: Any) -> None:
        """Vẽ các vật phẩm dã ngoại chưa nhặt trên Map hiện tại kèm hiệu ứng bập bồng mượt mà."""
        if getattr(game, "in_interior", False):
            return

        current_map = getattr(game, "current_map_id", 1)
        sim_time = getattr(game, "sim_time", 0.0)

        for item in self.forage_items:
            if item.collected or item.map_id != current_map:
                continue

            # Hiệu ứng bập bồng lơ lửng hình sin
            bob = int(math.sin(sim_time * 4.2 + item.x * 0.1) * 3.0)

            # Vẽ bóng đổ mờ hình elip dưới mặt đất
            shadow_surf = pygame.Surface((24, 10), pygame.SRCALPHA)
            pygame.draw.ellipse(shadow_surf, (16, 24, 12, 85), (0, 0, 24, 10))
            screen.blit(shadow_surf, (int(item.x - 12), int(item.y + 6)))

            # Lấy icon từ SpriteVault
            icon = game.vault.get_item_icon(item.item_key, 28)
            ix = int(item.x - 14)
            iy = int(item.y - 14 + bob)

            if icon is not None:
                screen.blit(icon, (ix, iy))
            else:
                # Vẽ fallback nếu thiếu icon
                pygame.draw.circle(screen, (245, 215, 80), (int(item.x), int(item.y + bob)), 10)
                pygame.draw.circle(screen, (160, 110, 25), (int(item.x), int(item.y + bob)), 10, width=2)

            # Hiển thị sao phẩm chất
            if item.quality > 0:
                slot_info = InventorySlot(item_key=item.item_key, quality=item.quality)
                font = getattr(game, "font_xs", None) or pygame.font.SysFont("Segoe UI", 11, bold=True)
                star_lbl = font.render(slot_info.stars_label, True, slot_info.quality_color)
                screen.blit(star_lbl, (ix + 16, iy - 2))

            # Gợi ý phím [E] khi Robot đứng trong phạm vi gần (<= 64px)
            dist_to_robot = math.hypot(game.robot.x - item.x, game.robot.y - item.y)
            if dist_to_robot <= 64.0:
                font = getattr(game, "font_xs", None) or pygame.font.SysFont("Segoe UI", 12, bold=True)
                hint = font.render("[E] Nhặt", True, (255, 245, 185))
                hx = int(item.x - hint.get_width() // 2)
                hy = int(item.y - 28 + bob)
                bg_rect = pygame.Rect(hx - 4, hy - 2, hint.get_width() + 8, hint.get_height() + 4)
                pygame.draw.rect(screen, (34, 22, 14, 220), bg_rect, border_radius=4)
                pygame.draw.rect(screen, (225, 175, 45), bg_rect, width=1, border_radius=4)
                screen.blit(hint, (hx, hy))

    # --------------------------------------------------------------------------
    # RƠI ĐỒ KHI VA CHẠM NGÃ CẤP 2 (KNOCKDOWN DROPPED ITEMS)
    # --------------------------------------------------------------------------

    def handle_robot_knockdown_drop(self, game: Any) -> None:
        """
        Khi Robot bị va chạm mạnh dẫn đến ngã ngồi Cấp 2, rơi 1 món đồ từ khay
        ra mặt đất cách 36px để người chơi có thể điều khiển Robot quay lại nhặt.
        """
        if not game.robot.inventory:
            return

        # Rơi món đồ cuối cùng trong khay
        dropped_key, dropped_slot = self.remove_inventory_at(game, len(game.robot.inventory) - 1)
        if not dropped_key:
            return

        # Tính góc rơi ngược hướng di chuyển hoặc lệch một góc an toàn
        drop_ang = game.robot.theta + math.pi + random.uniform(-0.4, 0.4)
        drop_dist = 36.0
        dx = max(40.0, min(SCREEN_W - 40.0, game.robot.x + math.cos(drop_ang) * drop_dist))
        dy = max(40.0, min(SCREEN_H - 40.0, game.robot.y + math.sin(drop_ang) * drop_dist))

        self.dropped_items.append({
            "item_key": dropped_key,
            "slot": dropped_slot or InventorySlot(item_key=dropped_key),
            "x": dx,
            "y": dy,
            "map_id": getattr(game, "current_map_id", 1),
            "in_interior": getattr(game, "in_interior", False),
            "timer": 180.0,  # Tồn tại trong 3 phút
        })

        item_name = self.get_item_name(dropped_key)
        if hasattr(game, "floating_texts"):
            from .entities import FloatingText
            game.floating_texts.append(
                FloatingText(f"Rơi mất {item_name}!", game.robot.x, game.robot.y - 48, (255, 95, 80))
            )

        if hasattr(game, "set_banner"):
            game.set_banner(
                f"Cảnh báo va chạm ngã! Bạn đã đánh rơi 1 {item_name} ra đất. Hãy tới nhặt lại bằng phím [E]!",
                (255, 120, 100),
            )

    def try_pickup_dropped_items(self, game: Any) -> bool:
        """Kiểm tra và nhặt lại món đồ bị rơi khi Robot tiến lại gần (khoảng cách <= 46.0px)."""
        current_map = getattr(game, "current_map_id", 1)
        in_interior = getattr(game, "in_interior", False)
        robot_x, robot_y = game.robot.x, game.robot.y

        for i, di in enumerate(list(self.dropped_items)):
            if di.get("map_id") != current_map or di.get("in_interior") != in_interior:
                continue

            dist = math.hypot(robot_x - di["x"], robot_y - di["y"])
            if dist <= 46.0:
                max_cap = getattr(game.robot, "max_inventory", getattr(game.robot, "max_capacity", 4))
                if len(game.robot.inventory) >= max_cap:
                    if hasattr(game, "set_banner"):
                        game.set_banner("Khay đồ đang đầy, không thể nhặt lại món đồ đã rơi!", (255, 170, 85))
                    return False

                item_key = di["item_key"]
                slot_obj = di["slot"]
                game.robot.inventory.append(item_key)
                self.slot_meta.append(slot_obj)
                self.dropped_items.pop(i)

                item_name = self.get_item_name(item_key)
                if hasattr(game, "floating_texts"):
                    from .entities import FloatingText
                    game.floating_texts.append(
                        FloatingText(f"Đã nhặt lại {item_name}!", di["x"], di["y"] - 20, (110, 245, 130))
                    )
                if hasattr(game, "audio"):
                    game.audio.play_sfx("harvest")
                if hasattr(game, "vfx"):
                    game.vfx.push_toast(
                        f"Đã nhặt lại: {item_name}",
                        "Khôi phục vật phẩm vào Khay đồ",
                        item_key,
                        (145, 255, 165),
                    )
                if hasattr(game, "set_banner"):
                    game.set_banner(f"Đã nhặt lại thành công: {item_name} vào khay đồ!", (145, 255, 165))
                return True

        return False

    def render_dropped_items(self, screen: pygame.Surface, game: Any) -> None:
        """Vẽ các món đồ đang rơi trên bản đồ với hiệu ứng nhấp nháy phát sáng."""
        current_map = getattr(game, "current_map_id", 1)
        in_interior = getattr(game, "in_interior", False)
        sim_time = getattr(game, "sim_time", 0.0)

        for di in self.dropped_items:
            if di.get("map_id") != current_map or di.get("in_interior") != in_interior:
                continue

            dx, dy = di["x"], di["y"]
            bob = int(math.sin(sim_time * 5.0) * 2.5)

            # Quầng sáng cảnh báo nhấp nháy
            pulse = abs(math.sin(sim_time * 3.5))
            glow_rad = int(14 + pulse * 6)
            glow_surf = pygame.Surface((glow_rad * 2, glow_rad * 2), pygame.SRCALPHA)
            pygame.draw.circle(glow_surf, (255, 120, 60, int(60 + pulse * 70)), (glow_rad, glow_rad), glow_rad)
            screen.blit(glow_surf, (int(dx - glow_rad), int(dy - glow_rad)))

            # Vẽ icon vật phẩm
            icon = game.vault.get_item_icon(di["item_key"], 26)
            if icon is not None:
                screen.blit(icon, (int(dx - 13), int(dy - 13 + bob)))

            # Nhãn hướng dẫn khi Robot đứng gần
            dist = math.hypot(game.robot.x - dx, game.robot.y - dy)
            if dist <= 58.0:
                font = getattr(game, "font_xs", None) or pygame.font.SysFont("Segoe UI", 12, bold=True)
                hint = font.render("[E] Nhặt lại", True, (255, 230, 140))
                hx = int(dx - hint.get_width() // 2)
                hy = int(dy - 26 + bob)
                bg_rect = pygame.Rect(hx - 4, hy - 2, hint.get_width() + 8, hint.get_height() + 4)
                pygame.draw.rect(screen, (50, 20, 16, 230), bg_rect, border_radius=4)
                pygame.draw.rect(screen, (255, 140, 60), bg_rect, width=1, border_radius=4)
                screen.blit(hint, (hx, hy))

    # --------------------------------------------------------------------------
    # HỆ THỐNG TƯƠNG TÁC XE KÉO AGV ĐỒNG HÀNH & MỤC TIÊU DÀI HẠN / CHỨNG NHẬN / THÀNH TỰU
    # --------------------------------------------------------------------------

    def try_interact_agv(self, game: Any) -> bool:
        """
        Tương tác bằng phím [E] khi đứng gần Xe Kéo Nông Sản AGV (<= 74px):
        - Nếu thùng AGV đang có hàng và khay Robot còn chỗ trống: lấy hàng từ AGV sang khay Robot.
        - Ngược lại: chuyển đổi chế độ hoạt động của AGV ('patrol' -> 'follow' -> 'parked' -> 'patrol').
        """
        if getattr(game, "in_interior", False):
            return False

        for agv in getattr(game, "agvs", []):
            dist = math.hypot(game.robot.x - agv.x, game.robot.y - agv.y)
            if dist <= 74.0:
                max_cap = getattr(game.robot, "max_inventory", 4)
                # Ưu tiên lấy hàng từ thùng AGV sang khay Robot nếu có hàng và khay Robot còn trống
                if agv.cargo and len(game.robot.inventory) < max_cap:
                    entry = agv.cargo.pop(0)
                    ik = entry.get("item_key", "apple") if isinstance(entry, dict) else str(entry)
                    ql = int(entry.get("quality", 0)) if isinstance(entry, dict) else 0
                    self.add_inventory_item(game, ik, quality=ql)
                    self.agv_cargo = [dict(c) for c in agv.cargo]
                    item_vi = self.get_item_name(ik)
                    if hasattr(game, "audio") and game.audio:
                        game.audio.play_sfx("harvest")
                    if hasattr(game, "set_banner"):
                        game.set_banner(
                            f"Đã lấy {item_vi} từ Thùng Xe Kéo AGV sang Khay Robot! (Còn {len(agv.cargo)}/{agv.max_cargo} trên AGV)",
                            (145, 248, 175),
                        )
                    return True

                # Đổi chế độ AGV: Đi theo làm việc / Đỗ tại chỗ / Tự tuần tra
                new_mode = agv.toggle_follow_mode()
                self.agv_companion_active = (new_mode == "follow")
                self.agv_cargo = [dict(c) for c in agv.cargo]
                self.unlock_achievement(game, "agv_partner")
                mode_names = {
                    "follow": "ĐI THEO HỖ TRỢ ROBOT (+4 ô thùng hàng tự động hứng nông sản)",
                    "parked": "ĐỨNG ĐỖ TẠI CHỖ (Có thể chạm nhẹ để đẩy đi)",
                    "patrol": "TỰ ĐỘNG TUẦN TRA NÔNG TRẠI",
                }
                if hasattr(game, "audio") and game.audio:
                    game.audio.play_sfx("portal")
                if hasattr(game, "set_banner"):
                    game.set_banner(
                        f"Xe Kéo AGV đã chuyển sang chế độ: {mode_names.get(new_mode, new_mode)}!",
                        (135, 245, 195),
                    )
                return True
        return False

    def call_or_toggle_agv(self, game: Any) -> bool:
        """
        Gọi hoặc chuyển đổi trạng thái Xe Kéo AGV bằng phím [C]:
        - Nếu trên bản đồ hiện tại có AGV: bật/tắt chế độ Đi Theo ('follow').
        - Nếu ở bản đồ khác mà đã đạt Chứng Nhận HRI Cấp I trở lên (hoặc đang có AGV đi theo):
          triệu hồi ngay Xe Kéo AGV tới sau lưng Robot!
        """
        if getattr(game, "in_interior", False):
            if hasattr(game, "set_banner"):
                game.set_banner("Xe Kéo AGV chỉ hoạt động ngoài trời (Map 1..4)!", (255, 195, 115))
            return False

        agvs = getattr(game, "agvs", [])
        if agvs:
            agv = agvs[0]
            agv.mode = "patrol" if agv.mode == "follow" else "follow"
            if agv.mode == "follow":
                # Di chuyển AGV lại gần nếu đang ở quá xa
                if math.hypot(game.robot.x - agv.x, game.robot.y - agv.y) > 160.0:
                    agv.x = max(48.0, min(SCREEN_W - 48.0, game.robot.x - math.cos(game.robot.theta) * 48.0))
                    agv.y = max(56.0, min(SCREEN_H - 56.0, game.robot.y - math.sin(game.robot.theta) * 48.0))
            self.agv_companion_active = (agv.mode == "follow")
            self.agv_cargo = [dict(c) for c in agv.cargo]
            self.unlock_achievement(game, "agv_partner")
            st = "ĐI THEO ROBOT (+4 ô chứa phụ)" if agv.mode == "follow" else "TỰ TUẦN TRA"
            if hasattr(game, "set_banner"):
                game.set_banner(f"Đã điều khiển Xe Kéo AGV [C]: {st}!", (135, 245, 195))
            return True

        # Nếu bản đồ hiện tại chưa có AGV -> kiểm tra Chứng Nhận Cấp I hoặc đã kích hoạt AGV đồng hành
        if self.certification_level >= 1 or self.agv_companion_active:
            from .entities import FarmCartAGV
            ax = max(48.0, min(SCREEN_W - 48.0, game.robot.x - math.cos(game.robot.theta) * 48.0))
            ay = max(56.0, min(SCREEN_H - 56.0, game.robot.y - math.sin(game.robot.theta) * 48.0))
            new_agv = FarmCartAGV(ax, ay, waypoints=[(ax, ay)])
            new_agv.mode = "follow"
            new_agv.cargo = [dict(c) for c in self.agv_cargo]
            game.agvs.append(new_agv)
            self.agv_companion_active = True
            self.unlock_achievement(game, "agv_partner")
            if hasattr(game, "set_banner"):
                game.set_banner(
                    "Đã triệu hồi Xe Kéo AGV Liên Bản Đồ [C] tới hỗ trợ chở nông sản!",
                    (135, 255, 175),
                )
            return True

        if hasattr(game, "set_banner"):
            game.set_banner(
                "Hãy lên Map 2 (Đại Nông Trại) gặp Xe Kéo AGV hoặc đạt Chứng Nhận HRI Cấp I để gọi AGV mọi nơi [C]!",
                (255, 210, 120),
            )
        return False

    def sync_companion_agv_on_map(self, game: Any) -> None:
        """Đảm bảo khi chuyển bản đồ ngoài trời, Xe Kéo AGV đang ở chế độ 'follow' sẽ đi theo Robot sang Map mới."""
        if getattr(game, "in_interior", False) or not self.agv_companion_active:
            return
        agvs = getattr(game, "agvs", [])
        if agvs:
            agv = agvs[0]
            agv.mode = "follow"
            agv.cargo = [dict(c) for c in self.agv_cargo]
            agv.x = max(48.0, min(SCREEN_W - 48.0, game.robot.x - math.cos(game.robot.theta) * 46.0))
            agv.y = max(56.0, min(SCREEN_H - 56.0, game.robot.y - math.sin(game.robot.theta) * 46.0))
        else:
            from .entities import FarmCartAGV
            ax = max(48.0, min(SCREEN_W - 48.0, game.robot.x - math.cos(game.robot.theta) * 46.0))
            ay = max(56.0, min(SCREEN_H - 56.0, game.robot.y - math.sin(game.robot.theta) * 46.0))
            new_agv = FarmCartAGV(ax, ay, waypoints=[(ax, ay)])
            new_agv.mode = "follow"
            new_agv.cargo = [dict(c) for c in self.agv_cargo]
            game.agvs.append(new_agv)

    def unlock_achievement(self, game: Any, ach_id: str) -> bool:
        """Mở khóa một thành tựu (nếu chưa mở) và trao thưởng Vàng + Điểm Uy Tín + Toast thông báo."""
        if ach_id in self.unlocked_achievements:
            return False
        ach_cfg = next((a for a in ACHIEVEMENTS_CONFIG if a["id"] == ach_id), None)
        if ach_cfg is None:
            return False

        self.unlocked_achievements.append(ach_id)
        r_gold = int(ach_cfg.get("reward_gold", 50))
        r_score = int(ach_cfg.get("reward_score", 40))
        title = ach_cfg.get("title", ach_id)
        icon = ach_cfg.get("icon", "icon_coin")

        if hasattr(game, "gold"):
            game.gold += r_gold
        self.daily_gold_earned += r_gold
        if hasattr(game, "add_score"):
            game.add_score(r_score, f"Thành tựu: {title}")
        elif hasattr(game, "score"):
            game.score += r_score

        if hasattr(game, "audio") and game.audio:
            game.audio.play_sfx("gold")
        if hasattr(game, "vfx") and game.vfx:
            game.vfx.push_toast(
                f"THÀNH TỰU: {title}",
                f"Thưởng +{r_gold}G & +{r_score}đ (Xem [J] -> Tab 4)",
                icon,
                (255, 225, 75),
            )
        return True

    def check_achievements_and_certifications(self, game: Any) -> None:
        """Kiểm tra tự động và mở khóa các Thành tựu & Chứng nhận HRI Cấp I..IV khi đủ điều kiện."""
        orders_done = int(getattr(game, "completed_quests_count", 0))
        score_val = int(getattr(game, "score", 0))
        comfort_val = float(getattr(game, "comfort_score", 100.0))
        events_done = int(getattr(getattr(game, "random_events", None), "total_events_completed", 0))
        bought = getattr(getattr(game, "workshop", None), "bought_status", {})
        all_robin = bool(bought) and all(
            bool(bought.get(k, False)) for k in ("cargo_lv2", "fast_harvest", "social_radar")
        )

        hearts_3_count = 0
        hearts_4_count = 0
        if hasattr(game, "dialogue") and game.dialogue is not None and hasattr(game.dialogue, "get_hearts"):
            for npc_name in self.npcs_db.keys():
                h_cnt = game.dialogue.get_hearts(npc_name)
                if h_cnt >= 3:
                    hearts_3_count += 1
                if h_cnt >= 4:
                    hearts_4_count += 1

        # 1. Kiểm tra 10 Thành tựu
        if orders_done >= 1:
            self.unlock_achievement(game, "first_delivery")
        if self.total_yields >= 5:
            self.unlock_achievement(game, "gentle_yielder")
        if self.total_fish_caught >= 3:
            self.unlock_achievement(game, "master_angler")
        if self.total_crops_shipped >= 6:
            self.unlock_achievement(game, "green_thumb")
        if hearts_3_count >= 3:
            self.unlock_achievement(game, "beloved_neighbor")
        if all_robin:
            self.unlock_achievement(game, "robin_maxed")
        if events_done >= 3:
            self.unlock_achievement(game, "event_hero")
        if self.safe_days_streak >= 3:
            self.unlock_achievement(game, "zero_accident_streak")

        # 2. Kiểm tra 4 Cấp Chứng Nhận An Toàn HRI của Thị Trưởng Lewis
        if self.certification_level < 1 and orders_done >= 2 and score_val >= 150:
            self._award_certification(game, 1)
        if self.certification_level < 2 and orders_done >= 5 and score_val >= 450 and comfort_val >= 75.0:
            self._award_certification(game, 2)
        if self.certification_level < 3 and all_robin and self.total_crops_shipped >= 6 and events_done >= 2:
            self._award_certification(game, 3)
        if self.certification_level < 4 and score_val >= 1000 and orders_done >= 10 and hearts_4_count >= 3:
            self._award_certification(game, 4)
            self.unlock_achievement(game, "mayor_grand_cup")

    def _award_certification(self, game: Any, level: int) -> None:
        self.certification_level = max(self.certification_level, level)
        cfg = next((c for c in CERTIFICATIONS_CONFIG if c["level"] == level), None)
        if cfg is None:
            return
        r_gold = int(cfg.get("reward_gold", 100))
        if hasattr(game, "gold"):
            game.gold += r_gold
        self.daily_gold_earned += r_gold
        if hasattr(game, "audio") and game.audio:
            game.audio.play_sfx("gold")
        if hasattr(game, "vfx") and game.vfx:
            game.vfx.push_toast(
                cfg["short_tag"],
                f"+{r_gold}G | {cfg['perk_desc']}",
                "icon_coin",
                (255, 218, 65),
            )
        if hasattr(game, "set_banner"):
            game.set_banner(
                f"CHÚC MỪNG THĂNG CẤP: {cfg['title']}! Nhận +{r_gold}G ({cfg['perk_desc']})",
                (255, 232, 95),
            )

    def compute_mayor_evaluation_score(self, game: Any) -> tuple[int, str]:
        """Tính Điểm Kiểm Định Đô Thị của Thị Trưởng Lewis (0..100 điểm) cho Mục tiêu Dài hạn."""
        score_pts = min(30, int(max(0, getattr(game, "score", 0)) * 30 // 1000))
        order_pts = min(25, int(getattr(game, "completed_quests_count", 0)) * 25 // 10)
        ach_pts = min(20, len(self.unlocked_achievements) * 2)
        cert_pts = min(15, self.certification_level * 4)
        comfort_pts = min(10, int(float(getattr(game, "comfort_score", 100.0)) // 10))
        total_eval = min(100, score_pts + order_pts + ach_pts + cert_pts + comfort_pts)
        if total_eval >= 90:
            title = "HUYỀN THOẠI ROBOT AN TOÀN PELICAN (Hạng S+)"
        elif total_eval >= 70:
            title = "CHUYÊN GIA TỰ HÀNH ĐÁNG TIN CẬY (Hạng A)"
        elif total_eval >= 45:
            title = "TRỢ THỦ NÔNG TRẠI TIỀM NĂNG (Hạng B)"
        else:
            title = "ROBOT TẬP SỰ ĐANG THỬ VIỆC (Hạng C)"
        return total_eval, title

    # --------------------------------------------------------------------------
    # TRẠM SẠC PIN (CHARGING DOCK), KẾT THÚC NGÀY & CHUYỂN BƯỚC MÙA VỤ
    # --------------------------------------------------------------------------

    def get_current_dock(self, game: Any) -> tuple[float, float, str]:
        """Lấy tọa độ (x, y, tên) của Đế Sạc Tia Chớp bên trong Xưởng & Nhà Robot (Map 4 -> Nội thất robot_house)."""
        room = getattr(game, "room_rect", pygame.Rect((1152 - 704) // 2, (768 - 440) // 2 + 34, 704, 440))
        dock_x = float(room.x + int(room.width * 0.77))
        dock_y = float(room.y + int(room.height * 0.56))
        return (dock_x, dock_y, "Đế Sạc Xưởng Robot (Map 4)")

    def is_in_robot_house(self, game: Any) -> bool:
        """Kiểm tra Robot có đang ở bên trong Xưởng & Nhà Robot (robot_house) hay không."""
        return bool(
            getattr(game, "in_interior", False)
            and getattr(getattr(game, "current_interior", None), "house_id", "") == "robot_house"
        )

    def is_near_charging_dock(self, game: Any, max_dist: float = 78.0) -> tuple[bool, float, tuple[float, float, str]]:
        """Kiểm tra Robot có đang đứng tại Đế Sạc Tia Chớp bên trong Xưởng & Nhà Robot hay không."""
        dock = self.get_current_dock(game)
        if not self.is_in_robot_house(game):
            return False, 999.0, dock
        dx = float(getattr(game.robot, "x", 0.0)) - dock[0]
        dy = float(getattr(game.robot, "y", 0.0)) - dock[1]
        dist_px = math.hypot(dx, dy)
        return (dist_px <= max_dist), dist_px, dock

    def is_near_upgrade_station(self, game: Any, max_dist: float = 86.0) -> tuple[bool, float]:
        """Kiểm tra Robot có đang đứng cạnh Trạm Cánh Tay Cải Tiến Robot bên trong Xưởng Robot hay không."""
        if not self.is_in_robot_house(game):
            return False, 999.0
        room = getattr(game, "room_rect", pygame.Rect((1152 - 704) // 2, (768 - 440) // 2 + 34, 704, 440))
        up_x = float(room.x + int(room.width * 0.27))
        up_y = float(room.y + int(room.height * 0.54) + 16)
        dist_px = math.hypot(float(getattr(game.robot, "x", 0.0)) - up_x, float(getattr(game.robot, "y", 0.0)) - up_y)
        return (dist_px <= max_dist), dist_px

    def try_interact_upgrade_station(self, game: Any) -> bool:
        """Tương tác bằng phím [E] khi đứng cạnh Trạm Cánh Tay Cải Tiến Robot bên trong Xưởng Robot."""
        near_up, _ = self.is_near_upgrade_station(game, 86.0)
        if not near_up:
            return False
        if getattr(game, "workshop", None) is not None:
            game.workshop.open = True
            if hasattr(game, "vfx") and game.vfx:
                game.vfx._mark_step_done(4)
            if hasattr(game, "set_banner"):
                game.set_banner(
                    "Đã kết nối Trạm Cánh Tay Cải Tiến Robot! Chọn gói nâng cấp [1]..[5] (Lv.1 -> Lv.3) hoặc Bảo Dưỡng [6].",
                    (135, 248, 165),
                )
            return True
        return False

    def try_interact_charging_dock(self, game: Any) -> bool:
        """
        Tương tác bằng phím [E] khi đứng tại Đế Sạc Tia Chớp trong Xưởng Robot:
        Sạc Pin gắn liền với việc Ngủ qua ngày mới (không tự động đầy ngay khi chỉ đứng lên).
        """
        near_dock, _, _ = self.is_near_charging_dock(game, 78.0)
        if not near_dock:
            return False
        self.try_sleep_and_advance(game)
        return True

    def try_sleep_and_advance(self, game: Any) -> bool:
        """
        Kiểm tra điều kiện Sạc Pin & Đi Ngủ Qua Ngày [N] / [E]:
        1. BẮT BUỘC phải về Xưởng & Nhà Robot (Map 4) và đứng trên Đế Sạc Tia Chớp (<= 78px).
        2. Sạc Pin gắn liền với việc Ngủ qua ngày: nếu vừa thức dậy lúc sáng (Pin >= 95%, chưa làm việc),
           chặn bấm nhầm để tránh spam qua ngày.
        """
        near_dock, dist_px, dock = self.is_near_charging_dock(game, 78.0)
        if not near_dock:
            if self.is_in_robot_house(game):
                dist_m = px_to_m(dist_px)
                msg = f"Hãy di chuyển lại gần Đế Sạc Tia Chớp bên phải phòng (cách {dist_m:.1f}m) rồi bấm [E] hoặc [N] để Sạc Pin & Ngủ!"
            else:
                msg = "Không thể ngủ hay sạc ngoài đường! Hãy về [Xưởng & Nhà Robot (Số 5)] tại Map 4 (Khu Dân Cư) để Sạc Pin & Ngủ [N]!"
            if hasattr(game, "set_banner"):
                game.set_banner(msg, (255, 195, 95))
            return False

        from .atmosphere import compute_clock_hour
        hour = compute_clock_hour(float(getattr(game, "sim_time", 0.0)))
        has_farming_progress = any(
            isinstance(s, dict) and s.get("crop_state") == "growing"
            for s in self.persistent_harvest_state.values()
        )
        has_worked = (
            self.daily_orders_completed > 0
            or self.daily_crops_shipped > 0
            or self.daily_gold_earned > 0
            or has_farming_progress
        )
        cur_bat = float(getattr(game.robot, "battery", 100.0))
        if (6.0 <= hour < 18.0) and not has_worked and cur_bat >= 95.0:
            if hasattr(game, "set_banner"):
                game.set_banner(
                    f"Pin đang đầy ({cur_bat:.0f}%) và mới {int(hour):02d}:00 sáng! Hãy ra ngoài làm việc trước khi Sạc Pin & Ngủ qua ngày mới.",
                    (255, 185, 95),
                )
            return False
        self.end_day_and_advance(game)
        return True

    def rollover_new_day_continuous(self, game: Any) -> None:
        """
        Chuyển sang ngày mới mượt mà tại 07:00 sáng khi người chơi chọn thức làm việc xuyên đêm (không bấm [N] đi ngủ):
        - Không bật Modal làm gián đoạn mạch chơi, chỉ thông báo qua Toast & Banner.
        """
        base_safe_bonus = 85 if self.certification_level >= 2 else 50
        if self.daily_collisions == 0 and self.daily_orders_completed >= 1:
            safety_bonus = base_safe_bonus
            self.safe_days_streak += 1
        else:
            safety_bonus = 0
            if self.daily_collisions > 0:
                self.safe_days_streak = 0
        if hasattr(game, "gold"):
            game.gold += safety_bonus
        if hasattr(game, "add_score") and safety_bonus > 0:
            game.add_score(50, "Thưởng Ca Đêm An Toàn HRI")
        self.check_achievements_and_certifications(game)

        rained = (getattr(getattr(game, "atmosphere", None), "current_weather", "") == "rain")
        if hasattr(game, "farming") and game.farming is not None:
            game.farming.advance_day(game, rained=rained)

        self.day += 1
        self.season_idx = ((self.day - 1) // 5) % len(self.SEASONS)
        day_in_season = ((self.day - 1) % 5) + 1
        self.festival_active = (day_in_season == 3)
        self.spawn_daily_forage_items()

        if hasattr(game, "total_knockdowns"):
            game.total_knockdowns = 0
        if hasattr(game, "hearts"):
            game.hearts = getattr(game, "max_hearts", 3)
        if hasattr(game, "comfort_score"):
            game.comfort_score = 100.0

        self.daily_gold_earned = 0
        self.daily_orders_completed = 0
        self.daily_crops_shipped = 0
        self.daily_collisions = 0

        if hasattr(game, "vfx") and game.vfx:
            game.vfx.push_toast(
                f"Bình Minh Ngày {self.day} ({self.current_season_name})",
                f"Ca đêm hoàn tất! +{safety_bonus}G thưởng an toàn",
                "icon_coin",
                (255, 225, 95),
            )
        if hasattr(game, "set_banner"):
            game.set_banner(
                f"Bình minh Ngày {self.day} ({self.current_season_name})! Cư dân đã thức dậy và cây trồng đã chín mới.",
                (255, 235, 140),
            )
        if hasattr(game, "random_events") and game.random_events is not None:
            game.random_events.on_new_day(game)

    def end_day_and_advance(self, game: Any) -> None:
        """
        Kết thúc ca làm việc trong ngày và bắt đầu ngày mới:
        - Mở Modal Báo Cáo Cuối Ngày (`self.summary_open = True`).
        - Tính thưởng An Toàn HRI (+50G & +50đ CHỈ KHI không va chạm VÀ đã hoàn thành ít nhất 1 đơn hàng trong ngày).
        - Phục hồi toàn bộ ruộng cây trồng (`has_produce = True`).
        - Tăng ngày `self.day += 1`.
        - Cứ mỗi 5 ngày tự động chuyển sang mùa tiếp theo.
        - Ngày 3 của mỗi mùa kích hoạt Lễ hội thị trấn (`festival_active = True`).
        - Đặt lại đồng hồ thời gian buổi sáng (07:00).
        """
        # 1. Tính thưởng An Toàn HRI (Chống spam ngủ: phải hoàn thành >= 1 đơn hàng mới được thưởng ca làm việc an toàn)
        base_safe_bonus = 85 if self.certification_level >= 2 else 50
        if self.daily_collisions == 0 and self.daily_orders_completed >= 1:
            safety_bonus = base_safe_bonus
            self.safe_days_streak += 1
        else:
            safety_bonus = 0
            if self.daily_collisions > 0:
                self.safe_days_streak = 0
        if hasattr(game, "gold"):
            game.gold += safety_bonus
        if hasattr(game, "add_score") and safety_bonus > 0:
            game.add_score(50, "Thưởng An Toàn HRI Không Va Chạm")
        self.check_achievements_and_certifications(game)

        # 2. Lưu lại thống kê tổng kết
        self.last_summary = {
            "day": self.day,
            "season_name": self.current_season_name,
            "season_key": self.current_season,
            "daily_gold": self.daily_gold_earned,
            "safety_bonus": safety_bonus,
            "collisions": self.daily_collisions,
            "orders_completed": self.daily_orders_completed,
            "crops_shipped": self.daily_crops_shipped,
            "total_gold": getattr(game, "gold", 0),
            "total_score": getattr(game, "score", 0),
            "festival_active": self.festival_active,
        }

        # 3. Tăng trưởng cây trồng & cây ăn quả qua ngày mới theo hệ thống Nông Nghiệp Theo Ngày
        rained = (getattr(getattr(game, "atmosphere", None), "current_weather", "") == "rain")
        if hasattr(game, "farming") and game.farming is not None:
            game.farming.advance_day(game, rained=rained)

        # 4. Tăng ngày và tính toán chu kỳ Mùa / Lễ hội
        self.day += 1
        self.season_idx = ((self.day - 1) // 5) % len(self.SEASONS)

        # Ngày 3 của mỗi mùa (1 mùa gồm 5 ngày: ngày 3, ngày 8, ngày 13, ...) là Ngày Lễ Hội
        day_in_season = ((self.day - 1) % 5) + 1
        self.festival_active = (day_in_season == 3)

        # 5. Sinh mới vật phẩm nhặt dã ngoại
        self.spawn_daily_forage_items()

        # 6. Đặt lại đồng hồ buổi sáng sớm (07:00) & hồi phục Tim An Toàn / Comfort HRI / reset số lần đâm trong ngày (L2, Pha 2)
        if hasattr(game, "sim_time"):
            game.sim_time = 0.0
        if hasattr(game, "total_knockdowns"):
            game.total_knockdowns = 0
        if hasattr(game, "hearts"):
            game.hearts = getattr(game, "max_hearts", 3)
        if hasattr(game, "comfort_score"):
            game.comfort_score = 100.0
        if hasattr(game, "robot") and hasattr(game.robot, "battery"):
            game.robot.battery = float(getattr(game.robot, "max_battery", 100.0))

        # 7. Đặt lại các biến thống kê trong ngày
        self.daily_gold_earned = 0
        self.daily_orders_completed = 0
        self.daily_crops_shipped = 0
        self.daily_collisions = 0

        # 8. Mở modal tổng kết cuối ngày
        self.summary_open = True

    def close_summary_modal(self, game: Any) -> None:
        """Đóng bảng tổng kết cuối ngày và bắt đầu ca làm việc của ngày mới."""
        self.summary_open = False
        fest_msg = " [HÔM NAY LÀ NGÀY LỄ HỘI THỊ TRẤN!]" if self.festival_active else ""
        if hasattr(game, "set_banner"):
            game.set_banner(
                f"Bắt đầu Ngày {self.day} — {self.current_season_name}!{fest_msg} Chúc bạn một ngày làm việc bội thu & an toàn.",
                (255, 235, 140),
            )
        if hasattr(game, "random_events") and game.random_events is not None:
            game.random_events.on_new_day(game)

    # --------------------------------------------------------------------------
    # VẼ MODAL BÁO CÁO CUỐI NGÀY PHONG CÁCH STARDEW VALLEY
    # --------------------------------------------------------------------------

    def render_end_of_day_modal(self, screen: pygame.Surface, game: Any) -> None:
        """Vẽ bảng tổng kết cuối ngày phong cách Stardew Valley cổ điển."""
        if not self.summary_open:
            return

        # 1. Phủ mờ toàn màn hình
        overlay = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 185))
        screen.blit(overlay, (0, 0))

        # 2. Khung hộp gỗ Stardew Valley ở trung tâm màn hình
        mw, mh = 620, 500
        mx = (SCREEN_W - mw) // 2
        my = (SCREEN_H - mh) // 2

        # Bóng đổ khung hộp
        shadow_rect = pygame.Rect(mx + 8, my + 10, mw, mh)
        pygame.draw.rect(screen, (8, 6, 4, 190), shadow_rect, border_radius=14)

        # Khung hộp chính gỗ nâu ấm áp
        modal_rect = pygame.Rect(mx, my, mw, mh)
        pygame.draw.rect(screen, (46, 28, 16), modal_rect, border_radius=14)
        pygame.draw.rect(screen, (235, 185, 52), modal_rect, width=3, border_radius=14)

        # Viền trang trí bên trong
        inner_rect = modal_rect.inflate(-14, -14)
        pygame.draw.rect(screen, (78, 48, 28), inner_rect, width=2, border_radius=10)

        # 3. Tiêu đề rực rỡ
        title_box = pygame.Rect(mx + 28, my + 24, mw - 56, 52)
        pygame.draw.rect(screen, (92, 52, 26), title_box, border_radius=8)
        pygame.draw.rect(screen, (255, 220, 75), title_box, width=2, border_radius=8)

        font_lg = getattr(game, "font_lg", None) or pygame.font.SysFont("Segoe UI", 24, bold=True)
        font_md = getattr(game, "font_md", None) or pygame.font.SysFont("Segoe UI", 18, bold=True)
        font_sm = getattr(game, "font_sm", None) or pygame.font.SysFont("Segoe UI", 15, bold=True)

        t_lbl = font_lg.render("BÁO CÁO KẾT THÚC NGÀY", True, (255, 235, 140))
        screen.blit(t_lbl, (title_box.centerx - t_lbl.get_width() // 2, title_box.centery - t_lbl.get_height() // 2))

        # 4. Thông tin Ngày & Mùa vụ
        rep_day = self.last_summary.get("day", self.day - 1)
        rep_season = self.last_summary.get("season_name", self.current_season_name)
        day_str = f"Ngày {rep_day} — {rep_season}"
        d_lbl = font_md.render(day_str, True, (245, 215, 160))
        screen.blit(d_lbl, (mx + 42, my + 92))

        if self.last_summary.get("festival_active", False):
            fest_lbl = font_sm.render("[ * NGÀY LỄ HỘI THỊ TRẤN * ]", True, (255, 220, 60))
            screen.blit(fest_lbl, (mx + mw - fest_lbl.get_width() - 42, my + 94))

        # Đường gạch ngang ngăn cách
        pygame.draw.line(screen, (140, 95, 55), (mx + 36, my + 122), (mx + mw - 36, my + 122), 2)

        # 5. Bảng kê khai chi tiết các chỉ số hoạt động trong ngày
        rows = [
            ("Doanh thu Vàng hôm nay:", f"+{self.last_summary.get('daily_gold', 0)} G", (255, 225, 80)),
            ("Thưởng An Toàn HRI (0 va chạm):", f"+{self.last_summary.get('safety_bonus', 0)} G", (110, 245, 130) if self.last_summary.get("safety_bonus", 0) > 0 else (255, 120, 100)),
            ("Số va chạm người dân:", f"{self.last_summary.get('collisions', 0)} lần", (140, 240, 160) if self.last_summary.get("collisions", 0) == 0 else (255, 95, 80)),
            ("Đơn đặt hàng hoàn thành:", f"{self.last_summary.get('orders_completed', 0)} đơn", (230, 230, 230)),
            ("Nông sản đã bán vào Thùng Giao Hàng:", f"{self.last_summary.get('crops_shipped', 0)} món", (230, 230, 230)),
            ("Tổng Vàng tích lũy hiện tại:", f"{self.last_summary.get('total_gold', getattr(game, 'gold', 0))} G", (255, 215, 60)),
            ("Điểm cống hiến thị trấn:", f"{self.last_summary.get('total_score', getattr(game, 'score', 0))} đ", (135, 220, 255)),
        ]

        start_y = my + 138
        row_h = 36
        for i, (label, val, val_col) in enumerate(rows):
            # Nền hàng xen kẽ
            bg_col = (58, 36, 22) if i % 2 == 0 else (46, 28, 16)
            row_rect = pygame.Rect(mx + 36, start_y + i * row_h, mw - 72, row_h - 4)
            pygame.draw.rect(screen, bg_col, row_rect, border_radius=6)

            lbl_surf = font_sm.render(label, True, (230, 215, 185))
            screen.blit(lbl_surf, (row_rect.left + 16, row_rect.centery - lbl_surf.get_height() // 2))

            val_surf = font_md.render(val, True, val_col)
            screen.blit(val_surf, (row_rect.right - val_surf.get_width() - 16, row_rect.centery - val_surf.get_height() // 2))

        # 6. Nút bấm xác nhận ngày mới ở đáy modal
        btn_w = mw - 96
        btn_h = 48
        btn_x = mx + 48
        btn_y = my + mh - 70
        btn_rect = pygame.Rect(btn_x, btn_y, btn_w, btn_h)

        # Hiệu ứng nhịp thở phát sáng nhẹ
        sim_time = getattr(game, "sim_time", 0.0)
        pulse = abs(math.sin(pygame.time.get_ticks() / 320.0))
        btn_border_col = (
            int(220 + pulse * 35),
            int(175 + pulse * 45),
            int(40 + pulse * 30),
        )

        pygame.draw.rect(screen, (36, 92, 44), btn_rect, border_radius=8)
        pygame.draw.rect(screen, btn_border_col, btn_rect, width=2, border_radius=8)

        btn_txt = font_md.render("[E] / [Space] / Click: BẮT ĐẦU NGÀY MỚI", True, (255, 248, 195))
        screen.blit(btn_txt, (btn_rect.centerx - btn_txt.get_width() // 2, btn_rect.centery - btn_txt.get_height() // 2))

    # --------------------------------------------------------------------------
    # HỆ THỐNG LƯU / ĐỌC TIẾN TRÌNH CHƠI (SAVE / LOAD 3 SLOTS)
    # --------------------------------------------------------------------------

    def get_save_slot_path(self, slot_id: int) -> str:
        """Đường dẫn tuyệt đối của file lưu trữ game."""
        safe_slot = max(1, min(3, int(slot_id)))
        return os.path.join(self.saves_dir, f"slot_{safe_slot}.json")

    def has_save_slot(self, slot_id: int) -> bool:
        """Kiểm tra xem Slot đã tồn tại dữ liệu lưu hay chưa."""
        return os.path.isfile(self.get_save_slot_path(slot_id))

    def get_slot_info(self, slot_id: int) -> dict | None:
        """Đọc tóm tắt thông tin save slot nếu tồn tại (phục vụ Tab 3 của Journal UI)."""
        path = self.get_save_slot_path(slot_id)
        if not os.path.isfile(path):
            return None
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return None

    def save_to_slot(self, game: Any, slot_id: int = 1) -> str:
        """
        Lưu toàn bộ trạng thái thế giới hiện tại vào file JSON Slot 1..3.
        """
        safe_slot = max(1, min(3, int(slot_id)))
        filepath = self.get_save_slot_path(safe_slot)

        # Lưu trạng thái ruộng bản đồ hiện tại trước khi ghi đĩa
        self.save_map_harvest_to_state(game)

        # Thu thập trạng thái nâng cấp Robin
        workshop_bought: dict[str, bool] = {}
        workshop_levels: dict[str, int] = {}
        if hasattr(game, "workshop"):
            if hasattr(game.workshop, "bought_status"):
                workshop_bought = dict(game.workshop.bought_status)
            if hasattr(game.workshop, "upgrade_levels"):
                workshop_levels = {k: int(v) for k, v in game.workshop.upgrade_levels.items()}

        # Thu thập điểm thiện cảm NPC
        friendship_data: dict[str, int] = {}
        if hasattr(game, "dialogue") and hasattr(game.dialogue, "friendship"):
            friendship_data = dict(game.dialogue.friendship)

        now_str = datetime.now().strftime("%d/%m/%Y %H:%M")
        self.sync_slot_meta_with_inventory(getattr(game.robot, "inventory", []))
        quests_state = [
            {
                "quest_id": getattr(q, "quest_id", ""),
                "status": getattr(q, "status", "available"),
                "bonus_timer": float(getattr(q, "bonus_timer", 0.0)),
            }
            for q in getattr(game, "quests", [])
        ]
        forage_serialized = [asdict(f) for f in self.forage_items]
        dropped_serialized = [
            {
                "item_key": d.get("item_key", ""),
                "quality": getattr(d.get("slot"), "quality", 0) if d.get("slot") is not None else 0,
                "x": float(d.get("x", 0.0)),
                "y": float(d.get("y", 0.0)),
                "map_id": int(d.get("map_id", 1)),
                "in_interior": bool(d.get("in_interior", False)),
                "timer": float(d.get("timer", 180.0)),
            }
            for d in self.dropped_items
        ]
        active_ev_data = None
        if hasattr(game, "random_events") and getattr(game.random_events, "active_event", None) is not None:
            active_ev_data = {
                "event": dict(game.random_events.active_event),
                "timer": float(getattr(game.random_events, "event_timer", 0.0)),
            }

        save_payload = {
            "save_version": 2,
            "slot_id": safe_slot,
            "saved_at": now_str,
            "save_time": f"Ngày {self.day} ({self.current_season_name}) - {now_str}",
            "day": self.day,
            "season_idx": self.season_idx,
            "season_name": self.current_season_name,
            "festival_active": self.festival_active,
            "sim_time": float(getattr(game, "sim_time", 0.0)),
            "gold": getattr(game, "gold", 60),
            "score": getattr(game, "score", 0),
            "hearts": getattr(game, "hearts", 3),
            "comfort_score": float(getattr(game, "comfort_score", 100.0)),
            "completed_quests_count": getattr(game, "completed_quests_count", 0),
            "total_knockdowns": getattr(game, "total_knockdowns", 0),
            "quest_idx": getattr(game, "quest_idx", 0),
            "quests_state": quests_state,
            "current_map_id": getattr(game, "current_map_id", 1),
            "in_interior": getattr(game, "in_interior", False),
            "robot_x": float(game.robot.x),
            "robot_y": float(game.robot.y),
            "robot_theta": float(game.robot.theta),
            "robot_battery": float(getattr(game.robot, "battery", 100.0)),
            "inventory": list(game.robot.inventory),
            "max_inventory": getattr(game.robot, "max_inventory", 4),
            "slot_meta": [asdict(s) for s in self.slot_meta],
            "workshop_bought": workshop_bought,
            "workshop_levels": workshop_levels,
            "friendship": friendship_data,
            "persistent_harvest_state": self.persistent_harvest_state,
            "forage_items": forage_serialized,
            "dropped_items": dropped_serialized,
            "active_event": active_ev_data,
            "total_crops_shipped": self.total_crops_shipped,
            "total_fish_caught": self.total_fish_caught,
            "total_yields": self.total_yields,
            "safe_days_streak": self.safe_days_streak,
            "certification_level": self.certification_level,
            "unlocked_achievements": list(self.unlocked_achievements),
            "agv_companion_active": self.agv_companion_active,
            "agv_cargo": list(self.agv_cargo),
            "farming": (
                game.farming.to_save_dict()
                if hasattr(game, "farming") and game.farming is not None
                else {}
            ),
        }

        try:
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(save_payload, f, ensure_ascii=False, indent=2)
            msg = f"Đã lưu tiến trình thành công vào Slot {safe_slot} (Ngày {self.day} — {self.current_season_name})!"
            if hasattr(game, "set_banner"):
                game.set_banner(msg, (135, 255, 175))
            return msg
        except Exception as e:
            err = f"Lỗi khi lưu Slot {safe_slot}: {e}"
            print(f"[GameState] {err}")
            if hasattr(game, "set_banner"):
                game.set_banner(err, (255, 100, 100))
            return err

    def load_from_slot(self, game: Any, slot_id: int = 1) -> bool:
        """
        Nạp toàn bộ trạng thái trò chơi đã lưu từ file JSON Slot 1..3:
        Khôi phục toàn bộ tiến trình và đồng bộ lại thế giới.
        """
        safe_slot = max(1, min(3, int(slot_id)))
        filepath = self.get_save_slot_path(safe_slot)

        if not os.path.isfile(filepath):
            if hasattr(game, "set_banner"):
                game.set_banner(f"Slot {safe_slot} chưa có dữ liệu lưu nào!", (255, 170, 90))
            return False

        try:
            with open(filepath, "r", encoding="utf-8") as f:
                payload = json.load(f)

            self.day = int(payload.get("day", 1))
            self.season_idx = int(payload.get("season_idx", 0))
            self.festival_active = bool(payload.get("festival_active", False))
            if hasattr(game, "sim_time"):
                game.sim_time = float(payload.get("sim_time", 0.0))

            if hasattr(game, "gold"):
                game.gold = int(payload.get("gold", 60))
            if hasattr(game, "score"):
                game.score = int(payload.get("score", 0))
            if hasattr(game, "hearts"):
                game.hearts = int(payload.get("hearts", 3))
            if hasattr(game, "comfort_score"):
                game.comfort_score = float(payload.get("comfort_score", 100.0))
            if hasattr(game, "completed_quests_count"):
                game.completed_quests_count = int(payload.get("completed_quests_count", 0))
            if hasattr(game, "total_knockdowns"):
                game.total_knockdowns = int(payload.get("total_knockdowns", 0))
            if hasattr(game, "quest_idx"):
                game.quest_idx = int(payload.get("quest_idx", 0))

            # Khôi phục trạng thái từng nhiệm vụ (L5)
            saved_quests = payload.get("quests_state", [])
            if isinstance(saved_quests, list) and hasattr(game, "quests"):
                by_id = {q.quest_id: q for q in game.quests if hasattr(q, "quest_id")}
                for sq in saved_quests:
                    if isinstance(sq, dict):
                        qid = sq.get("quest_id", "")
                        if qid in by_id:
                            by_id[qid].status = str(sq.get("status", "available"))
                            by_id[qid].bonus_timer = float(sq.get("bonus_timer", by_id[qid].bonus_time_limit))

            # Khôi phục forage_items, dropped_items và sự kiện đang chạy (L5)
            raw_forage = payload.get("forage_items")
            if isinstance(raw_forage, list):
                self.forage_items = [
                    ForageItem(
                        item_key=str(f.get("item_key", "mushroom")),
                        x=float(f.get("x", 0.0)),
                        y=float(f.get("y", 0.0)),
                        map_id=int(f.get("map_id", 1)),
                        collected=bool(f.get("collected", False)),
                        quality=int(f.get("quality", 0)),
                    )
                    for f in raw_forage
                    if isinstance(f, dict)
                ]
            raw_dropped = payload.get("dropped_items")
            if isinstance(raw_dropped, list):
                self.dropped_items = [
                    {
                        "item_key": str(d.get("item_key", "apple")),
                        "slot": InventorySlot(
                            item_key=str(d.get("item_key", "apple")),
                            quality=int(d.get("quality", 0)),
                        ),
                        "x": float(d.get("x", 0.0)),
                        "y": float(d.get("y", 0.0)),
                        "map_id": int(d.get("map_id", 1)),
                        "in_interior": bool(d.get("in_interior", False)),
                        "timer": float(d.get("timer", 180.0)),
                    }
                    for d in raw_dropped
                    if isinstance(d, dict)
                ]
            active_ev_data = payload.get("active_event")
            if hasattr(game, "random_events") and game.random_events is not None:
                if isinstance(active_ev_data, dict) and isinstance(active_ev_data.get("event"), dict):
                    game.random_events.active_event = dict(active_ev_data["event"])
                    game.random_events.event_timer = float(active_ev_data.get("timer", 60.0))
                else:
                    game.random_events.active_event = None
                    game.random_events.event_timer = 0.0

            # Khôi phục khay đồ và slot_meta
            game.robot.inventory = list(payload.get("inventory", []))
            raw_meta = payload.get("slot_meta", [])
            self.slot_meta = [
                InventorySlot(
                    item_key=d.get("item_key", ""),
                    quality=int(d.get("quality", 0)),
                    quantity=int(d.get("quantity", 1)),
                )
                for d in raw_meta
            ]
            self.sync_slot_meta_with_inventory(game.robot.inventory)

            # Khôi phục nâng cấp Robin
            workshop_bought = payload.get("workshop_bought", {})
            workshop_levels = payload.get("workshop_levels", {})
            if hasattr(game, "workshop"):
                if isinstance(workshop_bought, dict) and hasattr(game.workshop, "bought_status"):
                    game.workshop.bought_status.update({k: bool(v) for k, v in workshop_bought.items()})
                if isinstance(workshop_levels, dict) and hasattr(game.workshop, "upgrade_levels"):
                    game.workshop.upgrade_levels.update({k: int(v) for k, v in workshop_levels.items()})
                game.workshop.apply_passive_effects(game)
            if hasattr(game, "robot"):
                game.robot.max_inventory = int(payload.get("max_inventory", game.robot.max_inventory))
                game.robot.battery = float(payload.get("robot_battery", 100.0))

            # Khôi phục thiện cảm NPC
            friendship_data = payload.get("friendship", {})
            if hasattr(game, "dialogue") and hasattr(game.dialogue, "friendship"):
                game.dialogue.friendship = {k: int(v) for k, v in friendship_data.items()}

            # Khôi phục trạng thái ruộng cây trồng & Thành tựu / Chứng nhận / AGV / Nông nghiệp
            self.persistent_harvest_state = payload.get("persistent_harvest_state", {})
            if hasattr(game, "farming") and game.farming is not None and isinstance(payload.get("farming"), dict):
                game.farming.load_save_dict(payload["farming"])
            self.total_crops_shipped = int(payload.get("total_crops_shipped", 0))
            self.total_fish_caught = int(payload.get("total_fish_caught", 0))
            self.total_yields = int(payload.get("total_yields", 0))
            self.safe_days_streak = int(payload.get("safe_days_streak", 0))
            self.certification_level = int(payload.get("certification_level", 0))
            self.unlocked_achievements = list(payload.get("unlocked_achievements", []))
            self.agv_companion_active = bool(payload.get("agv_companion_active", False))
            self.agv_cargo = list(payload.get("agv_cargo", []))

            # Khôi phục bản đồ và vị trí Robot
            target_map = int(payload.get("current_map_id", 1))
            rx = float(payload.get("robot_x", 14.5 * TILE_SIZE))
            ry = float(payload.get("robot_y", 14.2 * TILE_SIZE))
            r_theta = float(payload.get("robot_theta", 0.0))

            if hasattr(game, "load_outdoor_map"):
                game.load_outdoor_map(target_map, spawn_pos=(rx, ry), spawn_theta=r_theta)

            # Đồng bộ lại ruộng cây trồng vào Map mới nạp
            self.sync_map_harvest_from_state(game)

            msg = f"Đã nạp thành công Slot {safe_slot} (Ngày {self.day} — {self.current_season_name})!"
            if hasattr(game, "set_banner"):
                game.set_banner(msg, (120, 245, 160))
            return True
        except Exception as e:
            err = f"Lỗi khi nạp Slot {safe_slot}: {e}"
            print(f"[GameState] {err}")
            if hasattr(game, "set_banner"):
                game.set_banner(err, (255, 90, 90))
            return False
