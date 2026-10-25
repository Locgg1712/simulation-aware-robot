# game/farming.py
"""
Hệ thống Nông Nghiệp Theo Ngày & Cửa Hàng Hạt Giống Cô Caroline (FarmBot Town):
- Cây trồng trên ruộng (crop_plot) lớn theo ngày (qua ngày khi Ngủ tại Đế Sạc hoặc qua 07:00 sáng).
- Các thửa ruộng thu hoạch mặc định là Ruộng Đất Trống (crop_state = "empty").
- Người chơi mua hạt giống tại Cô Caroline (Map 2) -> Gieo hạt [E] -> Tưới nước [E] -> Chờ qua ngày -> Thu hoạch [E].
- Khoảng cách tương tác chuẩn xác tới hình chữ nhật thửa ruộng (HARVEST_REACH_FIELD_PX = 36.0px).
"""

from __future__ import annotations

import math
import random
from typing import Any
import pygame

from .constants import ITEM_NAMES_VI, SCREEN_H, SCREEN_W
from .entities import FloatingText

SEED_VENDOR_NAME = "Cô Caroline"
HARVEST_REACH_FIELD_PX = 36.0   # Khoảng cách tối đa từ Robot tới hình chữ nhật ruộng (0 nếu đứng trong ruộng)
HARVEST_REACH_TREE_PX = 50.0    # Khoảng cách tối đa từ Robot tới điểm (spot.x, spot.y) của cây ăn quả
TREE_REGROW_DAYS = 1            # Cây ăn quả: thu hoạch xong, sáng hôm sau mới có quả lại

CROP_CATALOG: dict[str, dict[str, Any]] = {
    "wheat": {
        "name_vi": "Lúa Mì",
        "seed_price": 12,
        "days": 1,
        "yield": 3,
        "regrow_days": 0,
        "sell_price": 20,
    },
    "carrot": {
        "name_vi": "Cà Rốt",
        "seed_price": 14,
        "days": 2,
        "yield": 3,
        "regrow_days": 0,
        "sell_price": 22,
    },
    "cabbage": {
        "name_vi": "Bắp Cải",
        "seed_price": 18,
        "days": 2,
        "yield": 3,
        "regrow_days": 0,
        "sell_price": 30,
    },
    "tomato": {
        "name_vi": "Cà Chua",
        "seed_price": 22,
        "days": 2,
        "yield": 2,
        "regrow_days": 1,
        "sell_price": 26,
    },
    "corn": {
        "name_vi": "Bắp Ngô",
        "seed_price": 20,
        "days": 3,
        "yield": 3,
        "regrow_days": 2,
        "sell_price": 24,
    },
    "strawberry": {
        "name_vi": "Dâu Tây",
        "seed_price": 26,
        "days": 3,
        "yield": 2,
        "regrow_days": 2,
        "sell_price": 32,
    },
    "pumpkin": {
        "name_vi": "Bí Ngô",
        "seed_price": 38,
        "days": 4,
        "yield": 3,
        "regrow_days": 0,
        "sell_price": 42,
    },
}

EQUIP_CATALOG: dict[str, dict[str, Any]] = {
    "sprinkler": {
        "name_vi": "Máy Tưới Tự Động",
        "short_vi": "Máy Tưới Tự Động",
        "price": 85,
        "key_hint": "8",
        "sprite": "sprinkler",
        "attr": "has_sprinkler",
        "desc": "Tự động tưới mỗi sáng & tăng gấp đôi tốc độ lớn (+2 ngày/đêm)!",
        "desc_vi": "Tự tưới nước & tăng gấp đôi tốc độ lớn (+2 ngày/đêm)",
    },
    "scarecrow": {
        "name_vi": "Bù Nhìn Chống Quạ",
        "short_vi": "Bù Nhìn Chống Quạ",
        "price": 65,
        "key_hint": "9",
        "sprite": "scarecrow",
        "attr": "has_scarecrow",
        "desc": "Xua đuổi 100% quạ ăn mất nông sản hoặc phá ruộng vào ban đêm!",
        "desc_vi": "Bảo vệ ruộng 100% khỏi quạ phá hoại vào ban đêm",
    },
    "bio_sensor": {
        "name_vi": "Cọc Cảm Biến & Hướng Dương",
        "short_vi": "Cảm Biến & Hướng Dương",
        "price": 95,
        "key_hint": "0",
        "sprite": "sunflower",
        "attr": "has_bio_sensor",
        "desc": "Trang trí hoa hướng dương & cảm biến: +1 quả/vụ & +25% tỉ lệ Sao Vàng!",
        "desc_vi": "Trang trí ruộng: +1 quả/vụ & +25% tỉ lệ Sao Vàng",
    },
}


def is_harvestable_plot(spot: Any) -> bool:
    """Kiểm tra có phải là thửa ruộng thu hoạch thật (không phải ruộng trang trí deco_)."""
    return (
        getattr(spot, "kind", "") == "crop_plot"
        and not str(getattr(spot, "spot_id", "")).startswith("deco_")
    )


def init_empty_crop_plot(spot: Any) -> None:
    """Đưa thửa ruộng về trạng thái Đất Trống chờ gieo hạt."""
    spot.crop_state = "empty"
    spot.has_produce = False
    spot.regrow_timer = 0.0
    spot.yield_left = 0
    spot.days_grown = 0
    spot.days_needed = 1
    spot.watered = False
    spot.title = "Thửa Ruộng Trống"


def reach_distance(rx: float, ry: float, spot: Any) -> float:
    """
    Tính khoảng cách tương tác thực tế từ Robot (rx, ry) tới điểm thu hoạch:
    - Với thửa ruộng (spot.field_rect is not None): khoảng cách tới hình chữ nhật field_rect
      (bằng 0 nếu đứng trong lòng ruộng), cộng phạt +25px nếu đứng phía Bắc hàng rào.
    - Với cây ăn quả (spot.field_rect is None): khoảng cách Euclid tới (spot.x, spot.y).
    """
    r = getattr(spot, "field_rect", None)
    if r is not None:
        cx = max(r.left, min(rx, r.right))
        cy = max(r.top, min(ry, r.bottom))
        d_rect = math.hypot(rx - cx, ry - cy)
        if ry < r.top - 6:
            d_rect += 25.0
        return float(d_rect)
    return float(math.hypot(rx - spot.x, ry - spot.y))


def is_within_harvest_reach(rx: float, ry: float, spot: Any) -> bool:
    """Kiểm tra Robot có đứng đủ gần để trồng/tưới/thu hoạch tại spot hay không."""
    dist = reach_distance(rx, ry, spot)
    if getattr(spot, "field_rect", None) is not None:
        return dist <= HARVEST_REACH_FIELD_PX
    return dist <= HARVEST_REACH_TREE_PX


def spot_to_state_dict(spot: Any) -> dict[str, Any]:
    """Đóng gói trạng thái HarvestSpot thành dict để lưu vào persistent_harvest_state."""
    return {
        "kind": getattr(spot, "kind", "crop_plot"),
        "title": getattr(spot, "title", ""),
        "item_key": getattr(spot, "item_key", ""),
        "crop_name": getattr(spot, "crop_name", "wheat"),
        "crop_state": getattr(
            spot,
            "crop_state",
            "ripe" if getattr(spot, "has_produce", False) else "empty",
        ),
        "has_produce": bool(getattr(spot, "has_produce", False)),
        "regrow_timer": float(getattr(spot, "regrow_timer", 0.0)),
        "regrow_total": float(getattr(spot, "regrow_total", 16.0)),
        "days_grown": int(getattr(spot, "days_grown", 0)),
        "days_needed": max(1, int(getattr(spot, "days_needed", 1))),
        "watered": bool(getattr(spot, "watered", False)),
        "yield_left": int(getattr(spot, "yield_left", 1 if getattr(spot, "has_produce", False) else 0)),
        "has_sprinkler": bool(getattr(spot, "has_sprinkler", False)),
        "has_scarecrow": bool(getattr(spot, "has_scarecrow", False)),
        "has_bio_sensor": bool(getattr(spot, "has_bio_sensor", False)),
        "growth_stage": int(getattr(spot, "growth_stage", 0)),
    }


def apply_state_dict_to_spot(spot: Any, d: dict[str, Any]) -> None:
    """
    Khôi phục trạng thái HarvestSpot từ dict (tương thích ngược với file save cũ).
    Nếu thiếu 'crop_state':
    - crop_plot thu hoạch: 'ripe' nếu has_produce else 'empty'
    - fruit_tree: 'ripe' nếu has_produce else 'growing'
    """
    if not isinstance(d, dict):
        return

    spot_id = str(getattr(spot, "spot_id", ""))
    if spot_id.startswith("deco_"):
        spot.has_produce = bool(d.get("has_produce", getattr(spot, "has_produce", True)))
        spot.regrow_timer = float(d.get("regrow_timer", getattr(spot, "regrow_timer", 0.0)))
        return

    c_state = d.get("crop_state")
    if c_state not in ("empty", "growing", "ripe"):
        hp = bool(d.get("has_produce", getattr(spot, "has_produce", False)))
        if is_harvestable_plot(spot):
            c_state = "ripe" if hp else "empty"
        else:
            c_state = "ripe" if hp else "growing"

    if "has_sprinkler" in d:
        spot.has_sprinkler = bool(d.get("has_sprinkler", getattr(spot, "has_sprinkler", False)))
    if "has_scarecrow" in d:
        spot.has_scarecrow = bool(d.get("has_scarecrow", getattr(spot, "has_scarecrow", False)))
    if "has_bio_sensor" in d:
        spot.has_bio_sensor = bool(d.get("has_bio_sensor", getattr(spot, "has_bio_sensor", False)))

    if is_harvestable_plot(spot) and c_state == "empty":
        init_empty_crop_plot(spot)
        return

    if d.get("crop_name"):
        spot.crop_name = str(d["crop_name"])
    if d.get("item_key"):
        spot.item_key = str(d["item_key"])
    if d.get("title"):
        spot.title = str(d["title"])

    spot.crop_state = c_state
    spot.days_grown = max(0, int(d.get("days_grown", getattr(spot, "days_grown", 0))))
    spot.days_needed = max(1, int(d.get("days_needed", getattr(spot, "days_needed", 1))))
    spot.watered = bool(d.get("watered", getattr(spot, "watered", False)))

    if c_state == "ripe":
        spot.has_produce = True
        spot.regrow_timer = 0.0
        default_yield = (
            int(CROP_CATALOG.get(getattr(spot, "crop_name", ""), {}).get("yield", 2))
            if is_harvestable_plot(spot)
            else 1
        )
        spot.yield_left = max(1, int(d.get("yield_left", default_yield)))
    else:
        # Trạng thái growing: has_produce = False và regrow_timer = 0.0
        spot.has_produce = False
        spot.regrow_timer = 0.0
        spot.yield_left = max(0, int(d.get("yield_left", 0)))


class FarmingManager:
    """
    Quản lý túi hạt giống, thao tác trồng trọt (gieo hạt, tưới nước, thu hoạch nhiều đợt),
    tăng trưởng cây trồng qua ngày và giao diện Cửa Hàng Hạt Giống Cô Caroline.
    """

    def __init__(self) -> None:
        self.seed_bag: dict[str, int] = {"wheat": 2, "strawberry": 1}
        self.equip_bag: dict[str, int] = {"sprinkler": 0, "scarecrow": 0, "bio_sensor": 0}
        self.selected_seed: str = "wheat"
        self.shop_open: bool = False
        self._row_rects: list[tuple[str, pygame.Rect]] = []
        self._equip_rects: list[tuple[str, pygame.Rect]] = []
        self._close_rect: pygame.Rect = pygame.Rect(0, 0, 0, 0)
        self._modal_rect: pygame.Rect = pygame.Rect(0, 0, 0, 0)

    def _sync_spot_to_persistent(self, game: Any, spot: Any) -> None:
        """Đồng bộ ngay trạng thái spot vào persistent_harvest_state."""
        state = getattr(game, "state", None)
        if state is None:
            return
        p_state = getattr(state, "persistent_harvest_state", None)
        if isinstance(p_state, dict) and getattr(spot, "spot_id", ""):
            entry = spot_to_state_dict(spot)
            entry["map_id"] = int(getattr(game, "current_map_id", 1))
            p_state[spot.spot_id] = entry

    def get_active_seed_key(self) -> str:
        """Trả về loại hạt hoặc thiết bị đang chọn (hoặc hạt đầu tiên còn trong túi nếu đã hết)."""
        if self.selected_seed in EQUIP_CATALOG and self.equip_bag.get(self.selected_seed, 0) > 0:
            return self.selected_seed
        if self.seed_bag.get(self.selected_seed, 0) > 0:
            return self.selected_seed
        for k in CROP_CATALOG:
            if self.seed_bag.get(k, 0) > 0:
                self.selected_seed = k
                return k
        for ek in EQUIP_CATALOG:
            if self.equip_bag.get(ek, 0) > 0:
                self.selected_seed = ek
                return ek
        return self.selected_seed if self.selected_seed in CROP_CATALOG else "wheat"

    def cycle_selected_seed(self, game: Any) -> None:
        """Đổi loại hạt giống hoặc thiết bị ruộng đang chọn khi bấm phím [Q]."""
        owned = [k for k in CROP_CATALOG if self.seed_bag.get(k, 0) > 0] + [
            ek for ek in EQUIP_CATALOG if self.equip_bag.get(ek, 0) > 0
        ]
        if len(owned) >= 2:
            if self.selected_seed in owned:
                idx = (owned.index(self.selected_seed) + 1) % len(owned)
            else:
                idx = 0
            self.selected_seed = owned[idx]
        elif len(owned) == 1:
            self.selected_seed = owned[0]
        else:
            keys = list(CROP_CATALOG.keys())
            idx = (keys.index(self.selected_seed) + 1) % len(keys) if self.selected_seed in keys else 0
            self.selected_seed = keys[idx]

        if self.selected_seed in EQUIP_CATALOG:
            eq = EQUIP_CATALOG[self.selected_seed]
            cnt = int(self.equip_bag.get(self.selected_seed, 0))
            if hasattr(game, "set_banner"):
                game.set_banner(
                    f"Đang chọn Thiết Bị: {eq['name_vi']} (Còn {cnt}) — Đứng cạnh ruộng bấm [E] để lắp đặt! ({eq['desc']})",
                    (255, 232, 125),
                )
            return

        info = CROP_CATALOG.get(self.selected_seed, CROP_CATALOG["wheat"])
        cnt = int(self.seed_bag.get(self.selected_seed, 0))
        if hasattr(game, "set_banner"):
            if cnt > 0:
                game.set_banner(
                    f"Đang chọn Hạt {info['name_vi']} (Còn {cnt} gói | {info['days']} ngày chín, {info['yield']} quả/đợt).",
                    (155, 248, 175),
                )
            else:
                game.set_banner(
                    f"Túi hạt giống đang trống! Hãy tới gặp {SEED_VENDOR_NAME} ở Map 2 để mua hạt giống & thiết bị ruộng.",
                    (255, 205, 115),
                )

    def install_equipment(self, game: Any, spot: Any, equip_key: str) -> bool:
        """Lắp đặt thiết bị ruộng (Máy Tưới Tự Động / Bù Nhìn Chống Quạ / Cọc Cảm Biến Hướng Dương) lên thửa ruộng."""
        if not is_harvestable_plot(spot) or equip_key not in EQUIP_CATALOG:
            return False
        if self.equip_bag.get(equip_key, 0) <= 0:
            return False

        eq = EQUIP_CATALOG[equip_key]
        attr_name = str(eq["attr"])
        if getattr(spot, attr_name, False):
            if hasattr(game, "set_banner"):
                game.set_banner(
                    f"Thửa ruộng này đã được lắp đặt [{eq['name_vi']}] rồi! Hãy thử lắp ở thửa ruộng khác hoặc bấm [Q] đổi sang Hạt Giống.",
                    (255, 205, 115),
                )
            return True

        self.equip_bag[equip_key] = max(0, int(self.equip_bag.get(equip_key, 0)) - 1)
        setattr(spot, attr_name, True)
        if equip_key == "sprinkler" and getattr(spot, "crop_state", "") == "growing":
            spot.watered = True
        self._sync_spot_to_persistent(game, spot)

        if self.equip_bag.get(equip_key, 0) <= 0:
            for k in CROP_CATALOG:
                if self.seed_bag.get(k, 0) > 0:
                    self.selected_seed = k
                    break

        audio = getattr(game, "audio", None)
        if audio is not None and hasattr(audio, "play_sfx"):
            audio.play_sfx("harvest")
        if hasattr(game, "floating_texts") and isinstance(game.floating_texts, list):
            game.floating_texts.append(
                FloatingText(f"Đã lắp {eq['name_vi']}!", spot.x, spot.y - 28, (255, 235, 110))
            )
        if hasattr(game, "set_banner"):
            game.set_banner(
                f"ĐÃ LẮP ĐẶT [{eq['name_vi']}] vào {spot.title}! {eq['desc']}",
                (135, 255, 165),
            )
        return True

    def try_field_action(self, game: Any, spot: Any) -> bool:
        """
        Xử lý phím [E] tại thửa ruộng thu hoạch:
        - Nếu đang cầm Thiết bị ruộng (sprinkler / scarecrow / bio_sensor) và ruộng chưa lắp -> lắp ngay!
        - empty -> plant() (trả về True)
        - growing & chưa tưới -> water() (trả về True)
        - growing & đã tưới -> hiện banner báo số ngày còn lại (trả về True)
        - ripe -> trả về False để logic thu hoạch chuẩn chạy tiếp.
        """
        if not is_harvestable_plot(spot):
            return False

        if self.selected_seed in EQUIP_CATALOG and self.equip_bag.get(self.selected_seed, 0) > 0:
            return self.install_equipment(game, spot, self.selected_seed)

        c_state = getattr(spot, "crop_state", "ripe" if getattr(spot, "has_produce", False) else "empty")
        if c_state == "ripe" or getattr(spot, "has_produce", False):
            return False

        if c_state == "empty":
            self.plant(game, spot)
            return True

        if c_state == "growing":
            if not getattr(spot, "watered", False) and not getattr(spot, "has_sprinkler", False):
                self.water(game, spot)
                return True
            if getattr(spot, "has_sprinkler", False):
                spot.watered = True
            rem = max(1, int(getattr(spot, "days_needed", 1)) - int(getattr(spot, "days_grown", 0)))
            crop_vi = CROP_CATALOG.get(getattr(spot, "crop_name", ""), {}).get("name_vi", spot.title)
            if hasattr(game, "set_banner"):
                game.set_banner(
                    f"{spot.title} đã tưới đủ ẩm! Còn {rem} ngày nữa {crop_vi} sẽ chín (Ngủ qua ngày tại Đế Sạc [N]).",
                    (135, 228, 255),
                )
            return True

        return False

    def plant(self, game: Any, spot: Any) -> bool:
        """Gieo 1 gói hạt giống xuống thửa ruộng trống."""
        if not is_harvestable_plot(spot):
            return False
        c_state = getattr(spot, "crop_state", "ripe" if getattr(spot, "has_produce", False) else "empty")
        if c_state != "empty":
            return False

        crop_key = self.selected_seed if self.selected_seed in CROP_CATALOG else "wheat"
        if self.seed_bag.get(crop_key, 0) <= 0:
            found = None
            for k in CROP_CATALOG:
                if self.seed_bag.get(k, 0) > 0:
                    found = k
                    break
            if found is None:
                if hasattr(game, "set_banner"):
                    game.set_banner(
                        f"Bạn đã hết hạt giống! Hãy tới gặp {SEED_VENDOR_NAME} tại Map 2 (Đại Nông Trại) để mua hạt.",
                        (255, 195, 105),
                    )
                return False
            crop_key = found
            self.selected_seed = found

        info = CROP_CATALOG[crop_key]
        self.seed_bag[crop_key] = max(0, int(self.seed_bag.get(crop_key, 0)) - 1)

        spot.crop_name = crop_key
        spot.item_key = crop_key
        spot.title = f"Ruộng {info['name_vi']}"
        spot.crop_state = "growing"
        spot.has_produce = False
        spot.regrow_timer = 0.0
        spot.days_needed = int(info["days"])
        spot.days_grown = 0
        spot.yield_left = 0
        spot.watered = bool(getattr(spot, "has_sprinkler", False))

        self._sync_spot_to_persistent(game, spot)

        # Tự động chuyển sang hạt còn trong túi nếu loại hạt vừa gieo đã hết
        if self.seed_bag.get(self.selected_seed, 0) <= 0:
            for k in CROP_CATALOG:
                if self.seed_bag.get(k, 0) > 0:
                    self.selected_seed = k
                    break

        audio = getattr(game, "audio", None)
        if audio is not None and hasattr(audio, "play_sfx"):
            audio.play_sfx("pickup")

        if hasattr(game, "floating_texts") and isinstance(game.floating_texts, list):
            game.floating_texts.append(
                FloatingText(f"Gieo hạt {info['name_vi']}!", spot.x, spot.y - 26, (135, 255, 155))
            )

        if hasattr(game, "set_banner"):
            if spot.watered:
                game.set_banner(
                    f"Đã gieo Hạt {info['name_vi']}! Vòi tưới Sprinkler đã tự tưới ẩm ({info['days']} ngày chín).",
                    (120, 255, 165),
                )
            else:
                game.set_banner(
                    f"Đã gieo Hạt {info['name_vi']}! Bấm [E] lần nữa để tưới nước cho ruộng ({info['days']} ngày chín).",
                    (145, 248, 165),
                )
        return True

    def water(self, game: Any, spot: Any) -> bool:
        """Tưới nước cho thửa ruộng đang phát triển."""
        if not is_harvestable_plot(spot):
            return False
        if getattr(spot, "crop_state", "") != "growing":
            return False
        if getattr(spot, "watered", False):
            return False

        spot.watered = True
        spot.has_produce = False
        spot.regrow_timer = 0.0
        self._sync_spot_to_persistent(game, spot)

        audio = getattr(game, "audio", None)
        if audio is not None and hasattr(audio, "play_sfx"):
            audio.play_sfx("pickup")

        if hasattr(game, "floating_texts") and isinstance(game.floating_texts, list):
            game.floating_texts.append(
                FloatingText("Đã tưới nước!", spot.x, spot.y - 26, (115, 225, 255))
            )

        rem = max(1, int(getattr(spot, "days_needed", 1)) - int(getattr(spot, "days_grown", 0)))
        crop_vi = CROP_CATALOG.get(getattr(spot, "crop_name", ""), {}).get("name_vi", spot.title)
        if hasattr(game, "set_banner"):
            game.set_banner(
                f"Đã tưới nước cho {spot.title}! Còn {rem} ngày nữa {crop_vi} sẽ chín (Ngủ tại Đế Sạc [N] để qua ngày).",
                (115, 235, 255),
            )
        return True

    def on_harvested(self, game: Any, spot: Any) -> None:
        """
        Gọi sau mỗi lần Robot thu hoạch xong 1 nông sản từ spot:
        - Giảm yield_left đi 1; nếu còn > 0 thì vẫn giữ trạng thái chín (ripe).
        - Nếu hết yield_left:
          + Cây ăn quả -> chuyển sang growing (days_needed = TREE_REGROW_DAYS = 1).
          + Cây trồng tái thu hoạch (regrow_days > 0) -> growing (days_needed = regrow_days).
          + Cây trồng thu hoạch 1 lần (regrow_days == 0) -> trở về Thửa Ruộng Trống (empty).
        """
        cur_yield = max(1, int(getattr(spot, "yield_left", 1))) - 1
        if cur_yield > 0:
            spot.yield_left = cur_yield
            spot.crop_state = "ripe"
            spot.has_produce = True
            spot.regrow_timer = 0.0
            self._sync_spot_to_persistent(game, spot)
            return

        if getattr(spot, "kind", "") == "fruit_tree":
            spot.crop_state = "growing"
            spot.has_produce = False
            spot.regrow_timer = 0.0
            spot.days_grown = 0
            spot.days_needed = TREE_REGROW_DAYS
            spot.yield_left = 0
            spot.watered = True
        else:
            crop_key = str(getattr(spot, "crop_name", "") or getattr(spot, "item_key", ""))
            info = CROP_CATALOG.get(crop_key, {})
            regrow_days = int(info.get("regrow_days", 0))
            if regrow_days > 0:
                spot.crop_state = "growing"
                spot.has_produce = False
                spot.regrow_timer = 0.0
                spot.days_grown = 0
                spot.days_needed = regrow_days
                spot.yield_left = 0
                spot.watered = bool(getattr(spot, "has_sprinkler", False))
            else:
                init_empty_crop_plot(spot)

        self._sync_spot_to_persistent(game, spot)

    def advance_day(self, game: Any, rained: bool = False, crow_chance: float = 0.28) -> None:
        """
        Xử lý tăng trưởng nông sản khi bước sang ngày mới:
        1. Lưu các spot ở Map hiện tại vào persistent_harvest_state.
        2. Duyệt toàn bộ spot_id (bỏ qua deco_):
           - Cây ăn quả đang growing: +1 ngày -> chín (yield_left = 1).
           - Ruộng đang growing: nếu đã tưới (watered / has_sprinkler / rained) -> +1 ngày (+2 ngày nếu có Sprinkler);
             nếu đủ days_needed -> chín (ripe) với yield_left = CROP_CATALOG[crop]['yield'] (+1 nếu có has_bio_sensor).
           - Sự kiện Quạ Phá Ruộng ban đêm: ruộng cây nhiều ngày hoặc đang chín để qua đêm mà KHÔNG có Bù Nhìn (has_scarecrow)
             có tỉ lệ bị quạ mổ mất 1 quả hoặc chậm lớn 1 ngày.
        3. Đồng bộ lại ra các spot đang hiển thị trên Map.
        """
        state = getattr(game, "state", None)
        if state is not None and hasattr(state, "save_map_harvest_to_state"):
            state.save_map_harvest_to_state(game)

        p_state: dict[str, dict[str, Any]] = (
            getattr(state, "persistent_harvest_state", {}) if state is not None else {}
        )

        # Đảm bảo mọi harvest_spots trên map hiện tại đều có mặt trong p_state
        for spot in getattr(game, "harvest_spots", []):
            if not str(spot.spot_id).startswith("deco_") and spot.spot_id not in p_state:
                entry = spot_to_state_dict(spot)
                entry["map_id"] = int(getattr(game, "current_map_id", 1))
                p_state[spot.spot_id] = entry

        crow_attacked_plots: list[str] = []

        for spot_id, d in list(p_state.items()):
            if str(spot_id).startswith("deco_") or not isinstance(d, dict):
                continue

            kind = str(d.get("kind", "fruit_tree" if "tree" in str(spot_id) else "crop_plot"))
            c_state = d.get("crop_state")
            if c_state not in ("empty", "growing", "ripe"):
                hp = bool(d.get("has_produce", False))
                c_state = ("ripe" if hp else "empty") if kind == "crop_plot" else ("ripe" if hp else "growing")

            if kind == "fruit_tree":
                if c_state == "growing":
                    days_grown = int(d.get("days_grown", 0)) + 1
                    days_needed = max(1, int(d.get("days_needed", TREE_REGROW_DAYS)))
                    if days_grown >= days_needed:
                        d["crop_state"] = "ripe"
                        d["has_produce"] = True
                        d["regrow_timer"] = 0.0
                        d["days_grown"] = days_needed
                        d["yield_left"] = 1
                    else:
                        d["crop_state"] = "growing"
                        d["has_produce"] = False
                        d["regrow_timer"] = 0.0
                        d["days_grown"] = days_grown
                else:
                    d["crop_state"] = "ripe"
                    d["has_produce"] = True
                    d["regrow_timer"] = 0.0
                    d["yield_left"] = max(1, int(d.get("yield_left", 1)))
            else:
                has_sprinkler = bool(d.get("has_sprinkler", False))
                has_scarecrow = bool(d.get("has_scarecrow", False))
                has_bio_sensor = bool(d.get("has_bio_sensor", False))

                if c_state == "growing":
                    was_watered = bool(d.get("watered", False)) or has_sprinkler or bool(rained)
                    days_grown = int(d.get("days_grown", 0))
                    days_needed = max(1, int(d.get("days_needed", 1)))
                    crop_key = str(d.get("crop_name") or d.get("item_key") or "wheat")
                    if was_watered:
                        # Máy tưới tự động (Sprinkler) tăng tốc độ sinh trưởng gấp đôi (+2 ngày/đêm)
                        days_grown += 2 if has_sprinkler else 1

                    # Quạ phá ruộng ban đêm với ruộng nhiều ngày không có Bù Nhìn
                    crow_pecked = False
                    if not has_scarecrow and days_needed >= 2 and crow_chance > 0.0:
                        if random.random() < crow_chance:
                            crow_pecked = True
                            crow_attacked_plots.append(str(spot_id))

                    if days_grown >= days_needed:
                        crop_yield = int(CROP_CATALOG.get(crop_key, {}).get("yield", 2))
                        if has_bio_sensor:
                            crop_yield += 1
                        if crow_pecked and crop_yield > 1:
                            crop_yield -= 1
                        d["crop_state"] = "ripe"
                        d["has_produce"] = True
                        d["regrow_timer"] = 0.0
                        d["days_grown"] = days_needed
                        d["yield_left"] = crop_yield
                        d["watered"] = False
                    else:
                        if crow_pecked and days_grown > 0:
                            days_grown = max(0, days_grown - 1)
                        d["crop_state"] = "growing"
                        d["has_produce"] = False
                        d["regrow_timer"] = 0.0
                        d["days_grown"] = days_grown
                        d["watered"] = True if has_sprinkler else False
                elif c_state == "ripe":
                    cur_yield = max(1, int(d.get("yield_left", 1)))
                    if not has_scarecrow and cur_yield > 1 and crow_chance > 0.0:
                        if random.random() < crow_chance:
                            cur_yield -= 1
                            crow_attacked_plots.append(str(spot_id))
                    d["crop_state"] = "ripe"
                    d["has_produce"] = True
                    d["regrow_timer"] = 0.0
                    d["yield_left"] = cur_yield
                    d["watered"] = False
                else:
                    d["crop_state"] = "empty"
                    d["has_produce"] = False
                    d["regrow_timer"] = 0.0
                    d["watered"] = False
                    d["yield_left"] = 0
                    d["days_grown"] = 0

        if state is not None and hasattr(state, "sync_map_harvest_from_state"):
            state.sync_map_harvest_from_state(game)
        for spot in getattr(game, "harvest_spots", []):
            if spot.spot_id in p_state:
                apply_state_dict_to_spot(spot, p_state[spot.spot_id])

        if crow_attacked_plots and hasattr(game, "vfx") and game.vfx is not None:
            game.vfx.push_toast(
                "Cảnh báo Quạ Phá Ruộng đêm qua!",
                f"{len(crow_attacked_plots)} ruộng chưa gắn Bù Nhìn bị quạ mổ giảm năng suất!",
                "sunflower",
            )

    def open_shop(self, game: Any) -> None:
        """Mở giao diện Cửa Hàng Hạt Giống & Vật Phẩm Trang Trí Ruộng Cô Caroline."""
        self.shop_open = True
        if hasattr(game, "robot"):
            game.robot.v_mps = 0.0
            game.robot.vx = 0.0
            game.robot.vy = 0.0
        audio = getattr(game, "audio", None)
        if audio is not None and hasattr(audio, "play_sfx"):
            audio.play_sfx("pickup")

    def buy_seed(self, game: Any, crop_key: str, qty: int = 1) -> bool:
        """Mua qty gói hạt giống của crop_key từ Cửa Hàng Hạt Giống Cô Caroline."""
        if crop_key not in CROP_CATALOG or qty <= 0:
            return False

        info = CROP_CATALOG[crop_key]
        total_cost = int(info["seed_price"]) * int(qty)
        cur_gold = int(getattr(game, "gold", 0))
        if cur_gold < total_cost:
            if hasattr(game, "set_banner"):
                game.set_banner(
                    f"Không đủ Vàng! Cần {total_cost}G để mua Hạt {info['name_vi']} (Hiện có: {cur_gold}G).",
                    (255, 135, 95),
                )
            return False

        game.gold = cur_gold - total_cost
        self.seed_bag[crop_key] = int(self.seed_bag.get(crop_key, 0)) + int(qty)
        self.selected_seed = crop_key

        audio = getattr(game, "audio", None)
        if audio is not None and hasattr(audio, "play_sfx"):
            audio.play_sfx("gold")

        vfx = getattr(game, "vfx", None)
        if vfx is not None and hasattr(vfx, "push_toast"):
            vfx.push_toast(
                f"Đã mua Hạt {info['name_vi']} x{qty}",
                f"-{total_cost}G | Trong túi: {self.seed_bag[crop_key]} gói",
                crop_key,
            )

        if hasattr(game, "set_banner"):
            game.set_banner(
                f"Đã mua {qty} gói Hạt {info['name_vi']} (-{total_cost}G)! Đang có: {self.seed_bag[crop_key]} gói. Ra ruộng trống bấm [E] để trồng!",
                (120, 255, 155),
            )
        return True

    def buy_equipment(self, game: Any, equip_key: str, qty: int = 1) -> bool:
        """Mua thiết bị / vật phẩm trang trí ruộng (Máy Tưới Tự Động, Bù Nhìn, Cọc Cảm Biến)."""
        if equip_key not in EQUIP_CATALOG or qty <= 0:
            return False

        info = EQUIP_CATALOG[equip_key]
        total_cost = int(info["price"]) * int(qty)
        cur_gold = int(getattr(game, "gold", 0))
        if cur_gold < total_cost:
            if hasattr(game, "set_banner"):
                game.set_banner(
                    f"Không đủ Vàng! Cần {total_cost}G để mua {info['name_vi']} (Hiện có: {cur_gold}G).",
                    (255, 135, 95),
                )
            return False

        game.gold = cur_gold - total_cost
        self.equip_bag[equip_key] = int(self.equip_bag.get(equip_key, 0)) + int(qty)
        self.selected_seed = equip_key

        audio = getattr(game, "audio", None)
        if audio is not None and hasattr(audio, "play_sfx"):
            audio.play_sfx("gold")

        vfx = getattr(game, "vfx", None)
        if vfx is not None and hasattr(vfx, "push_toast"):
            vfx.push_toast(
                f"Đã mua {info['name_vi']} x{qty}",
                f"-{total_cost}G | Ra thửa ruộng bấm [E] để lắp đặt!",
                "sunflower",
            )

        if hasattr(game, "set_banner"):
            game.set_banner(
                f"Đã mua {qty} {info['name_vi']} (-{total_cost}G)! Đứng cạnh thửa ruộng bấm [E] để lắp đặt lên ruộng!",
                (125, 255, 195),
            )
        return True

    def handle_key(self, key: int, uni: str, game: Any) -> bool:
        """
        Xử lý bàn phím khi Cửa Hàng Hạt Giống & Thiết Bị Ruộng đang mở:
        - Phím [1..7]: mua 1 gói hạt tương ứng.
        - Phím [8, 9, 0]: mua thiết bị ruộng (Máy Tưới, Bù Nhìn, Cọc Cảm Biến).
        - Phím [ESC]/[E]/[Enter]/[SPACE]: đóng cửa hàng.
        """
        if not self.shop_open:
            return False

        if key in (pygame.K_ESCAPE, pygame.K_e, pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE):
            self.shop_open = False
            return True

        crop_keys = list(CROP_CATALOG.keys())
        num_idx = -1
        if pygame.K_1 <= key <= pygame.K_7:
            num_idx = key - pygame.K_1
        elif pygame.K_KP1 <= key <= pygame.K_KP7:
            num_idx = key - pygame.K_KP1
        elif uni in ("1", "2", "3", "4", "5", "6", "7"):
            num_idx = int(uni) - 1

        if 0 <= num_idx < len(crop_keys):
            self.buy_seed(game, crop_keys[num_idx], 1)
            return True

        if key in (pygame.K_8, pygame.K_KP8) or uni == "8":
            self.buy_equipment(game, "sprinkler", 1)
            return True
        if key in (pygame.K_9, pygame.K_KP9) or uni == "9":
            self.buy_equipment(game, "scarecrow", 1)
            return True
        if key in (pygame.K_0, pygame.K_KP0) or uni == "0":
            self.buy_equipment(game, "bio_sensor", 1)
            return True

        return True

    def handle_click(self, pos: tuple[int, int], game: Any) -> bool:
        """Xử lý click chuột trong Cửa Hàng Hạt Giống & Thiết Bị Cô Caroline."""
        if not self.shop_open:
            return False

        if self._close_rect.width > 0 and self._close_rect.collidepoint(pos):
            self.shop_open = False
            return True

        for crop_key, row_rect in self._row_rects:
            if row_rect.collidepoint(pos):
                self.buy_seed(game, crop_key, 1)
                return True

        for eq_key, eq_rect in self._equip_rects:
            if eq_rect.collidepoint(pos):
                self.buy_equipment(game, eq_key, 1)
                return True

        if self._modal_rect.width > 0 and not self._modal_rect.collidepoint(pos):
            self.shop_open = False
            return True

        return True

    def render_shop(self, screen: pygame.Surface, game: Any) -> None:
        """Vẽ bảng gỗ Cửa Hàng Hạt Giống & Thiết Bị Trang Trí Ruộng Cô Caroline (700x575)."""
        if not self.shop_open:
            return

        ov = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
        ov.fill((12, 8, 6, 185))
        screen.blit(ov, (0, 0))

        mw, mh = 700, 575
        mx, my = SCREEN_W // 2 - mw // 2, SCREEN_H // 2 - mh // 2
        self._modal_rect = pygame.Rect(mx, my, mw, mh)

        # Khung gỗ 2 lớp
        pygame.draw.rect(screen, (52, 34, 22), self._modal_rect, border_radius=12)
        pygame.draw.rect(screen, (228, 178, 78), self._modal_rect, 3, border_radius=12)
        inner = self._modal_rect.inflate(-10, -10)
        pygame.draw.rect(screen, (68, 44, 28), inner, border_radius=9)
        pygame.draw.rect(screen, (145, 102, 54), inner, 1, border_radius=9)

        # Tiêu đề & số Vàng hiện có
        title_s = game.font_md.render(
            f"TIỆM HẠT GIỐNG & THIẾT BỊ RUỘNG — {SEED_VENDOR_NAME.upper()}",
            True,
            (255, 236, 145),
        )
        screen.blit(title_s, (mx + 20, my + 14))

        gold_val = int(getattr(game, "gold", 0))
        gold_txt = game.font_sm.render(f"Vàng hiện có: {gold_val}G", True, (255, 220, 68))
        screen.blit(gold_txt, (mx + mw - gold_txt.get_width() - 95, my + 16))

        self._close_rect = pygame.Rect(mx + mw - 78, my + 12, 60, 26)
        pygame.draw.rect(screen, (158, 52, 46), self._close_rect, border_radius=6)
        pygame.draw.rect(screen, (255, 198, 175), self._close_rect, 1, border_radius=6)
        close_lbl = game.font_xs.render("[ESC] Đóng", True, (255, 245, 235))
        screen.blit(
            close_lbl,
            (
                self._close_rect.centerx - close_lbl.get_width() // 2,
                self._close_rect.centery - close_lbl.get_height() // 2,
            ),
        )

        sub_s = game.font_xs.render(
            "Phím [1]..[7]: Mua Hạt Giống | Phím [8]..[0]: Mua Thiết Bị Trang Trí & Bảo Vệ Ruộng (Ra ruộng bấm [E] để trồng/lắp).",
            True,
            (225, 215, 192),
        )
        screen.blit(sub_s, (mx + 20, my + 40))

        # Danh sách 7 loại hạt giống
        self._row_rects.clear()
        mouse_pos = pygame.mouse.get_pos()
        row_y = my + 62
        row_h = 44
        for idx, (crop_key, info) in enumerate(CROP_CATALOG.items()):
            r_rect = pygame.Rect(mx + 18, row_y + idx * (row_h + 3), mw - 36, row_h)
            self._row_rects.append((crop_key, r_rect))
            hovered = r_rect.collidepoint(mouse_pos)
            can_afford = gold_val >= int(info["seed_price"])
            in_bag = int(self.seed_bag.get(crop_key, 0))
            is_selected = self.selected_seed == crop_key

            bg_col = (94, 64, 38) if hovered else ((82, 56, 34) if is_selected else (58, 38, 24))
            bd_col = (255, 228, 98) if (hovered or is_selected) else (138, 98, 58)
            pygame.draw.rect(screen, bg_col, r_rect, border_radius=7)
            pygame.draw.rect(screen, bd_col, r_rect, 2 if is_selected else 1, border_radius=7)

            # Phím tắt [1..7] + Icon nông sản
            key_badge = pygame.Rect(r_rect.x + 8, r_rect.y + 9, 26, 26)
            pygame.draw.rect(screen, (42, 28, 18), key_badge, border_radius=5)
            pygame.draw.rect(screen, (215, 172, 88), key_badge, 1, border_radius=5)
            k_lbl = game.font_xs.render(str(idx + 1), True, (255, 235, 145))
            screen.blit(
                k_lbl,
                (key_badge.centerx - k_lbl.get_width() // 2, key_badge.centery - k_lbl.get_height() // 2),
            )

            icon = game.vault.get_item_icon(crop_key, 26)
            if icon is not None:
                screen.blit(icon, (r_rect.x + 42, r_rect.y + 9))

            # Tên hạt & thông số sinh trưởng
            full_vi = ITEM_NAMES_VI.get(crop_key, info["name_vi"])
            name_lbl = game.font_sm.render(f"Hạt {info['name_vi']} ({full_vi})", True, (255, 245, 215))
            screen.blit(name_lbl, (r_rect.x + 76, r_rect.y + 4))

            regrow_str = (
                f" | Tái thu: {info['regrow_days']} ngày/lần"
                if int(info["regrow_days"]) > 0
                else " | Thu hoạch 1 đợt"
            )
            sell_p = int(info.get("sell_price", 25))
            desc_str = (
                f"Lớn: {info['days']} ngày | Sản lượng: {info['yield']} quả/đợt"
                f"{regrow_str} | Bán: {sell_p}G/quả"
            )
            desc_lbl = game.font_xs.render(desc_str, True, (205, 228, 195))
            screen.blit(desc_lbl, (r_rect.x + 76, r_rect.y + 23))

            # Số lượng đang có trong túi
            bag_col = (135, 255, 165) if in_bag > 0 else (185, 172, 155)
            bag_lbl = game.font_xs.render(f"Đang có: {in_bag} gói", True, bag_col)
            screen.blit(bag_lbl, (r_rect.right - 210, r_rect.y + 14))

            # Nút mua & giá hạt
            buy_btn = pygame.Rect(r_rect.right - 104, r_rect.y + 7, 94, 30)
            btn_bg = (48, 138, 68) if can_afford else (92, 54, 48)
            btn_bd = (165, 255, 175) if can_afford else (185, 115, 105)
            pygame.draw.rect(screen, btn_bg, buy_btn, border_radius=6)
            pygame.draw.rect(screen, btn_bd, buy_btn, 1, border_radius=6)
            price_lbl = game.font_xs.render(f"Mua: {info['seed_price']}G", True, (255, 248, 215))
            screen.blit(
                price_lbl,
                (buy_btn.centerx - price_lbl.get_width() // 2, buy_btn.centery - price_lbl.get_height() // 2),
            )

        # Khu vực Vật Phẩm Trang Trí & Thiết Bị Ruộng ([8], [9], [0])
        eq_top = row_y + len(CROP_CATALOG) * (row_h + 3) + 6
        sec_lbl = game.font_xs.render(
            "VẬT PHẨM TRANG TRÍ & TỰ ĐỘNG HÓA RUỘNG (Mua xong đứng gần thửa ruộng bấm [E] để gắn vĩnh viễn):",
            True,
            (255, 232, 138),
        )
        screen.blit(sec_lbl, (mx + 20, eq_top))

        self._equip_rects.clear()
        card_y = eq_top + 20
        card_w = (mw - 36 - 16) // 3
        card_h = 114
        for idx, (eq_key, eq_info) in enumerate(EQUIP_CATALOG.items()):
            cx = mx + 18 + idx * (card_w + 8)
            c_rect = pygame.Rect(cx, card_y, card_w, card_h)
            self._equip_rects.append((eq_key, c_rect))
            hovered = c_rect.collidepoint(mouse_pos)
            can_afford = gold_val >= int(eq_info["price"])
            in_bag = int(self.equip_bag.get(eq_key, 0))
            is_selected = self.selected_seed == eq_key

            bg_col = (74, 58, 38) if hovered else ((66, 52, 34) if is_selected else (48, 34, 22))
            bd_col = (145, 245, 215) if (hovered or is_selected) else (142, 108, 64)
            pygame.draw.rect(screen, bg_col, c_rect, border_radius=8)
            pygame.draw.rect(screen, bd_col, c_rect, 2 if is_selected else 1, border_radius=8)

            # Phím tắt [8], [9], [0]
            k_badge = pygame.Rect(c_rect.x + 8, c_rect.y + 8, 24, 24)
            pygame.draw.rect(screen, (36, 26, 18), k_badge, border_radius=5)
            pygame.draw.rect(screen, (145, 235, 205), k_badge, 1, border_radius=5)
            k_txt = game.font_xs.render(str(eq_info["key_hint"]), True, (175, 255, 225))
            screen.blit(
                k_txt,
                (k_badge.centerx - k_txt.get_width() // 2, k_badge.centery - k_txt.get_height() // 2),
            )

            # Sprite thiết bị trang trí ruộng
            icon_s = game.vault.scaled(str(eq_info["sprite"]), 28, 28)
            if icon_s is not None:
                screen.blit(icon_s, (c_rect.x + 36, c_rect.y + 6))

            title_eq = game.font_xs.render(str(eq_info["short_vi"]), True, (255, 245, 195))
            screen.blit(title_eq, (c_rect.x + 68, c_rect.y + 10))

            # Mô tả tác dụng (2 dòng gọn)
            desc_text = str(eq_info["desc_vi"])
            words = desc_text.split(" ")
            line1, line2 = "", ""
            for w in words:
                test = (line1 + " " + w).strip()
                if game.font_xs.size(test)[0] <= card_w - 16:
                    line1 = test
                else:
                    line2 = (line2 + " " + w).strip()
            d1_s = game.font_xs.render(line1, True, (205, 232, 205))
            screen.blit(d1_s, (c_rect.x + 8, c_rect.y + 38))
            if line2:
                d2_s = game.font_xs.render(line2[:38], True, (185, 218, 188))
                screen.blit(d2_s, (c_rect.x + 8, c_rect.y + 55))

            bag_eq = game.font_xs.render(
                f"Túi: {in_bag}",
                True,
                (135, 255, 175) if in_bag > 0 else (180, 168, 152),
            )
            screen.blit(bag_eq, (c_rect.x + 10, c_rect.bottom - 26))

            buy_eq = pygame.Rect(c_rect.right - 96, c_rect.bottom - 31, 88, 24)
            pygame.draw.rect(
                screen,
                (44, 132, 92) if can_afford else (92, 54, 48),
                buy_eq,
                border_radius=5,
            )
            pygame.draw.rect(
                screen,
                (155, 255, 215) if can_afford else (185, 115, 105),
                buy_eq,
                1,
                border_radius=5,
            )
            p_eq = game.font_xs.render(f"Mua: {eq_info['price']}G", True, (255, 248, 220))
            screen.blit(
                p_eq,
                (buy_eq.centerx - p_eq.get_width() // 2, buy_eq.centery - p_eq.get_height() // 2),
            )

        # Dòng hướng dẫn cuối bảng
        foot_s = game.font_xs.render(
            "Mẹo: Nhấn [Q] ngoài bản đồ để đổi giữa các Hạt Giống & Thiết Bị đang có, rồi ra ruộng bấm [E] để gieo/lắp đặt!",
            True,
            (255, 228, 145),
        )
        screen.blit(foot_s, (mx + mw // 2 - foot_s.get_width() // 2, my + mh - 24))

    def to_save_dict(self) -> dict[str, Any]:
        """Xuất dữ liệu túi hạt giống & thiết bị ruộng để lưu vào file save JSON."""
        return {
            "seed_bag": dict(self.seed_bag),
            "equip_bag": dict(self.equip_bag),
            "selected_seed": self.selected_seed,
        }

    def load_save_dict(self, d: dict[str, Any]) -> None:
        """Khôi phục túi hạt giống & thiết bị ruộng từ file save JSON."""
        if not isinstance(d, dict):
            return
        raw_bag = d.get("seed_bag")
        if isinstance(raw_bag, dict):
            self.seed_bag = {
                str(k): max(0, int(v))
                for k, v in raw_bag.items()
                if str(k) in CROP_CATALOG
            }
        raw_eq = d.get("equip_bag")
        if isinstance(raw_eq, dict):
            self.equip_bag = {
                str(k): max(0, int(v))
                for k, v in raw_eq.items()
                if str(k) in EQUIP_CATALOG
            }
        sel = d.get("selected_seed")
        if isinstance(sel, str) and (sel in CROP_CATALOG or sel in EQUIP_CATALOG):
            self.selected_seed = sel
