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
    ITEM_NAMES_VI,
    SCORE_HARVEST_FRUIT,
    SCREEN_H,
    SCREEN_W,
    TILE_SIZE,
)


# Bảng mở rộng tên tiếng Việt cho tất cả các vật phẩm bao gồm Foraging
EXTENDED_ITEM_NAMES_VI: dict[str, str] = {
    **ITEM_NAMES_VI,
    "mushroom": "Nấm Rừng Thơm",
    "wild_berry": "Quả Mọng Rừng",
    "golden_flower": "Hoa Cúc Vàng",
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
        """Thêm vật phẩm vào khay chứa đồ của Robot kèm phẩm chất sao."""
        max_cap = getattr(game.robot, "max_inventory", getattr(game.robot, "max_capacity", 4))
        if len(game.robot.inventory) >= max_cap:
            return False
        game.robot.inventory.append(item_key)
        self.slot_meta.append(InventorySlot(item_key=item_key, quality=quality, quantity=quantity))
        return True

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
            self.persistent_harvest_state[spot.spot_id] = {
                "has_produce": spot.has_produce,
                "regrow_timer": spot.regrow_timer,
                "regrow_total": getattr(spot, "regrow_total", 16.0),
                "growth_stage": getattr(spot, "growth_stage", 9),
                "map_id": current_map,
            }

    def sync_map_harvest_from_state(self, game: Any) -> None:
        """Đồng bộ trạng thái ruộng cây trồng từ persistent_harvest_state khi vào Map mới."""
        all_spots = getattr(game, "harvest_spots", []) + getattr(game, "deco_fields", [])
        for spot in all_spots:
            if spot.spot_id in self.persistent_harvest_state:
                data = self.persistent_harvest_state[spot.spot_id]
                spot.has_produce = data.get("has_produce", True)
                spot.regrow_timer = data.get("regrow_timer", 0.0)

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
    # KẾT THÚC NGÀY & CHUYỂN BƯỚC MÙA VỤ (END OF DAY & SEASON ADVANCE)
    # --------------------------------------------------------------------------

    def end_day_and_advance(self, game: Any) -> None:
        """
        Kết thúc ca làm việc trong ngày và bắt đầu ngày mới:
        - Mở Modal Báo Cáo Cuối Ngày (`self.summary_open = True`).
        - Tính thưởng An Toàn HRI (+50G nếu không có va chạm trong ngày).
        - Phục hồi toàn bộ ruộng cây trồng (`has_produce = True`).
        - Tăng ngày `self.day += 1`.
        - Cứ mỗi 5 ngày tự động chuyển sang mùa tiếp theo.
        - Ngày 3 của mỗi mùa kích hoạt Lễ hội thị trấn (`festival_active = True`).
        - Đặt lại đồng hồ thời gian buổi sáng (07:00).
        """
        # 1. Tính thưởng An Toàn HRI
        safety_bonus = 50 if self.daily_collisions == 0 else 0
        if hasattr(game, "gold"):
            game.gold += safety_bonus
        if hasattr(game, "add_score") and safety_bonus > 0:
            game.add_score(50, "Thưởng An Toàn HRI Không Va Chạm")

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

        # 3. Phục hồi toàn bộ ruộng cây trồng trong persistent_harvest_state
        for spot_id, sdata in self.persistent_harvest_state.items():
            sdata["has_produce"] = True
            sdata["regrow_timer"] = 0.0
            sdata["growth_stage"] = 9

        # Cập nhật trực tiếp cho các thửa ruộng ở Map hiện tại
        all_spots = getattr(game, "harvest_spots", []) + getattr(game, "deco_fields", [])
        for spot in all_spots:
            spot.has_produce = True
            spot.regrow_timer = 0.0

        # 4. Tăng ngày và tính toán chu kỳ Mùa / Lễ hội
        self.day += 1
        self.season_idx = ((self.day - 1) // 5) % len(self.SEASONS)

        # Ngày 3 của mỗi mùa (1 mùa gồm 5 ngày: ngày 3, ngày 8, ngày 13, ...) là Ngày Lễ Hội
        day_in_season = ((self.day - 1) % 5) + 1
        self.festival_active = (day_in_season == 3)

        # 5. Sinh mới vật phẩm nhặt dã ngoại
        self.spawn_daily_forage_items()

        # 6. Đặt lại đồng hồ buổi sáng sớm (07:00)
        if hasattr(game, "sim_time"):
            game.sim_time = 0.0

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
        if hasattr(game, "workshop") and hasattr(game.workshop, "bought_status"):
            workshop_bought = dict(game.workshop.bought_status)

        # Thu thập điểm thiện cảm NPC
        friendship_data: dict[str, int] = {}
        if hasattr(game, "dialogue") and hasattr(game.dialogue, "friendship"):
            friendship_data = dict(game.dialogue.friendship)

        now_str = datetime.now().strftime("%d/%m/%Y %H:%M")
        save_payload = {
            "slot_id": safe_slot,
            "saved_at": now_str,
            "save_time": f"Ngày {self.day} ({self.current_season_name}) - {now_str}",
            "day": self.day,
            "season_idx": self.season_idx,
            "season_name": self.current_season_name,
            "festival_active": self.festival_active,
            "gold": getattr(game, "gold", 60),
            "score": getattr(game, "score", 0),
            "hearts": getattr(game, "hearts", 3),
            "completed_quests_count": getattr(game, "completed_quests_count", 0),
            "total_knockdowns": getattr(game, "total_knockdowns", 0),
            "quest_idx": getattr(game, "quest_idx", 0),
            "current_map_id": getattr(game, "current_map_id", 1),
            "in_interior": getattr(game, "in_interior", False),
            "robot_x": float(game.robot.x),
            "robot_y": float(game.robot.y),
            "robot_theta": float(game.robot.theta),
            "inventory": list(game.robot.inventory),
            "max_inventory": getattr(game.robot, "max_inventory", 4),
            "slot_meta": [asdict(s) for s in self.slot_meta],
            "workshop_bought": workshop_bought,
            "friendship": friendship_data,
            "persistent_harvest_state": self.persistent_harvest_state,
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

            if hasattr(game, "gold"):
                game.gold = int(payload.get("gold", 60))
            if hasattr(game, "score"):
                game.score = int(payload.get("score", 0))
            if hasattr(game, "hearts"):
                game.hearts = int(payload.get("hearts", 3))
            if hasattr(game, "completed_quests_count"):
                game.completed_quests_count = int(payload.get("completed_quests_count", 0))
            if hasattr(game, "total_knockdowns"):
                game.total_knockdowns = int(payload.get("total_knockdowns", 0))
            if hasattr(game, "quest_idx"):
                game.quest_idx = int(payload.get("quest_idx", 0))

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
            if hasattr(game, "workshop") and isinstance(workshop_bought, dict):
                game.workshop.bought_status.update({k: bool(v) for k, v in workshop_bought.items()})
                game.workshop.apply_passive_effects(game)
            if hasattr(game, "robot"):
                game.robot.max_inventory = int(payload.get("max_inventory", game.robot.max_inventory))

            # Khôi phục thiện cảm NPC
            friendship_data = payload.get("friendship", {})
            if hasattr(game, "dialogue") and hasattr(game.dialogue, "friendship"):
                game.dialogue.friendship = {k: int(v) for k, v in friendship_data.items()}

            # Khôi phục trạng thái ruộng cây trồng
            self.persistent_harvest_state = payload.get("persistent_harvest_state", {})

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
