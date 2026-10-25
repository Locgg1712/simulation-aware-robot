# game/random_events.py
"""
Hệ thống Sự Kiện Ngẫu Nhiên (Random & Dynamic World Events) chuẩn Stardew Valley
kết hợp bài toán An toàn Tương tác Người - Robot (HRI).

Mô-đun quản lý:
1. Nạp và quản trị 7 sự kiện ngẫu nhiên sinh động từ data/random_events.json:
   - Mưa sao băng & Khoáng thạch tím Iridium rơi rải rác.
   - Tìm giỏ đồ thất lạc giúp cụ bà Evelyn.
   - Đàn cừu non tinh nghịch đi lạc ra đường lớn.
   - Xe hàng Thương nhân Du mục ghé thăm với giá thưởng x1.8.
   - Đơn chuyển phát cấp cứu y tế khẩn cấp [SOS] của Bác sĩ Harvey.
   - Cơn mưa rào lộc xuân bất chợt tưới mát ruộng đồng.
   - Hội họp đột xuất giữa quảng trường thị trấn (Vùng Không gian Xã hội O-Space).
2. Tự động kích hoạt luân phiên, đếm lùi thời gian hiệu lực và thời gian hồi (cooldown).
3. Kiểm tra cự ly an toàn HRI khi Robot tiếp cận và bấm phím [E] để tương tác.
4. Trao thưởng Vàng (Gold), Điểm đạo đức (Score), Nông sản chất lượng sao,
   và điểm Thiện cảm (Friendship Hearts) với dân làng tương ứng.
5. Hiệu ứng đồ họa vòng hào quang phát sáng Pulsing Halo, Sprite đại diện,
   và Thẻ thông báo nổi HUD hiển thị thời gian đếm ngược.
"""

from __future__ import annotations

import copy
import json
import math
import os
from pathlib import Path
import random
from typing import Any, Optional

import pygame


# ==============================================================================
# DỮ LIỆU DỰ PHÒNG AN TOÀN CHO 7 SỰ KIỆN THẾ GIỚI (FALLBACK EVENTS)
# ==============================================================================

FALLBACK_EVENTS: dict[str, dict[str, Any]] = {
    "iridium_meteor": {
        "id": "iridium_meteor",
        "title": "Mưa Sao Băng & Khoáng Thạch Tím",
        "desc": "Một khối Khoáng Thạch Iridium lấp lánh vừa rơi xuống! Hãy tới bấm [E] thu thập.",
        "map_id": 2,
        "x_tile": 12.5,
        "y_tile": 11.5,
        "reward_gold": 120,
        "reward_score": 80,
        "reward_item": "iridium_ore",
        "reward_quality": 3,
        "duration": 95.0,
    },
    "lost_item_search": {
        "id": "lost_item_search",
        "title": "Tìm Túi Đồ Đánh Rơi Của Bà Evelyn",
        "desc": "Bà Evelyn đánh rơi giỏ thảo dược ở Quảng Trường (Map 1). Hãy tới nhặt [E] giúp bà!",
        "map_id": 1,
        "x_tile": 19.5,
        "y_tile": 14.5,
        "target_npc": "Bà Evelyn",
        "reward_gold": 75,
        "reward_score": 70,
        "reward_hearts": 150,
        "duration": 90.0,
    },
    "runaway_animals": {
        "id": "runaway_animals",
        "title": "Cừu Non Tinh Nghịch Đi Lạc",
        "desc": "Một chú Cừu Non đi lạc ra đường lớn Map 2! Hãy tiếp cận an toàn và bấm [E] dẫn về chuồng.",
        "map_id": 2,
        "x_tile": 17.0,
        "y_tile": 13.5,
        "target_npc": "Nông dân Marnie",
        "reward_gold": 85,
        "reward_score": 65,
        "reward_hearts": 120,
        "duration": 85.0,
    },
    "traveling_merchant": {
        "id": "traveling_merchant",
        "title": "Thương Nhân Du Mục Ghé Thăm",
        "desc": "Xe hàng Thương Nhân Du Mục đang đỗ tại Quảng Trường Map 1! Bấm [E] nhận quà & bán giá x1.8.",
        "map_id": 1,
        "x_tile": 13.0,
        "y_tile": 11.0,
        "reward_gold": 90,
        "reward_score": 60,
        "reward_item": "peach",
        "reward_quality": 2,
        "duration": 110.0,
    },
    "flash_express_order": {
        "id": "flash_express_order",
        "title": "Đơn Cấp Cứu Y Tế Khẩn Cấp [SOS]",
        "desc": "Bác sĩ Harvey cần gấp thảo dược tại Map 1! Tới điểm tiếp nhận bấm [E] để nhận thưởng x2.",
        "map_id": 1,
        "x_tile": 6.5,
        "y_tile": 9.5,
        "target_npc": "Chủ tiệm Pierre",
        "reward_gold": 110,
        "reward_score": 90,
        "reward_hearts": 100,
        "duration": 75.0,
    },
    "sudden_squall": {
        "id": "sudden_squall",
        "title": "Cơn Mưa Rào Lộc Xuân Bất Chợt",
        "desc": "Mưa rào bất chợt giúp cây trồng lớn nhanh x2! Hãy tới kiểm tra trạm nước Map 3 bấm [E].",
        "map_id": 3,
        "x_tile": 13.5,
        "y_tile": 12.0,
        "reward_gold": 70,
        "reward_score": 65,
        "weather_override": "rain",
        "duration": 80.0,
    },
    "spontaneous_gathering": {
        "id": "spontaneous_gathering",
        "title": "Hội Họp Đột Xuất Giữa Quảng Trường (O-Space)",
        "desc": "Cư dân đang tụ họp trò chuyện tại Quảng Trường Map 1. Hãy đi chậm [X] và bấm [E] chào hỏi!",
        "map_id": 1,
        "x_tile": 16.2,
        "y_tile": 12.2,
        "target_npc": "Ông George",
        "reward_gold": 80,
        "reward_score": 75,
        "reward_hearts": 110,
        "duration": 90.0,
    },
}


# ==============================================================================
# LỚP QUẢN LÝ SỰ KIỆN THẾ GIỚI NGẪU NHIÊN (RANDOM EVENT MANAGER)
# ==============================================================================

class RandomEventManager:
    """
    Quản lý vòng đời toàn diện của các sự kiện thế giới ngẫu nhiên trong FarmBot Town:
    - Kích hoạt sự kiện theo chu kỳ hoặc khi bắt đầu ngày mới.
    - Cập nhật thời gian đếm lùi, thời gian chờ.
    - Kiểm tra và xử lý tương tác vật lý phím [E] của Robot.
    - Kết xuất đồ họa phát sáng tại thực địa và thanh HUD thông báo thời gian thực.
    """

    def __init__(self, data_path: str | Path | None = None) -> None:
        if data_path is not None:
            self.data_path = Path(data_path)
        else:
            self.data_path = Path(__file__).resolve().parent / "data" / "random_events.json"

        # Tải danh sách sự kiện từ file JSON (kèm fallback an toàn)
        self.events_db: dict[str, dict[str, Any]] = self._load_events()

        # Trạng thái sự kiện hiện hành
        self.active_event: dict[str, Any] | None = None
        self.event_timer: float = 0.0
        self.cooldown_timer: float = 25.0

        # Thống kê thành tích
        self.events_completed_today: int = 0
        self.total_events_completed: int = 0
        self.event_history: list[str] = []

        # Đồng hồ phục vụ hiệu ứng hoạt họa nhịp sin
        self.anim_time: float = 0.0
        self._font_cache: dict[str, pygame.font.Font] = {}

    # --------------------------------------------------------------------------
    # NẠP DỮ LIỆU TỪ TỆP TIN JSON
    # --------------------------------------------------------------------------

    def _load_events(self) -> dict[str, dict[str, Any]]:
        """Nạp dữ liệu sự kiện từ file JSON, trả về dict fallback nếu gặp lỗi."""
        if self.data_path.is_file():
            try:
                with open(self.data_path, "r", encoding="utf-8") as f:
                    raw_data = json.load(f)
                if isinstance(raw_data, dict) and len(raw_data) > 0:
                    events: dict[str, dict[str, Any]] = {}
                    for k, v in raw_data.items():
                        if isinstance(v, dict):
                            entry = dict(v)
                            entry.setdefault("id", k)
                            events[k] = entry
                    return events
            except Exception as exc:
                print(f"[RandomEvents] Cảnh báo lỗi nạp {self.data_path}: {exc}. Dùng dữ liệu dự phòng.")

        return copy.deepcopy(FALLBACK_EVENTS)

    # --------------------------------------------------------------------------
    # KÍCH HOẠT SỰ KIỆN THẾ GIỚI
    # --------------------------------------------------------------------------

    def trigger_random_event(self, game: Any, event_id: str | None = None) -> dict[str, Any]:
        """
        Kích hoạt một sự kiện thế giới ngẫu nhiên hoặc theo ID cụ thể.
        Tính toán tọa độ pixel thực, chuyển đổi thời tiết, phát âm thanh và hiển thị thông báo.
        """
        if not self.events_db:
            self.events_db = copy.deepcopy(FALLBACK_EVENTS)

        # Lựa chọn sự kiện
        if event_id is not None and event_id in self.events_db:
            chosen_key = event_id
        else:
            # Ưu tiên chọn sự kiện khác với sự kiện gần nhất và ưu tiên cùng bản đồ hiện tại
            available_keys = list(self.events_db.keys())
            last_event = self.event_history[-1] if (len(available_keys) > 1 and self.event_history) else None
            candidates = [k for k in available_keys if k != last_event] or available_keys
            cur_map = getattr(game, "current_map_id", 1)
            same_map_candidates = [
                k for k in candidates if self.events_db[k].get("map_id", 1) == cur_map
            ]
            if same_map_candidates and random.random() < 0.72:
                chosen_key = random.choice(same_map_candidates)
            else:
                chosen_key = random.choice(candidates)

        # Khởi tạo bản sao sự kiện đang hoạt động
        template = self.events_db[chosen_key]
        ev: dict[str, Any] = copy.deepcopy(template)
        ev.setdefault("id", chosen_key)

        # Tính tọa độ pixel thực tế trên bản đồ
        x_tile = float(ev.get("x_tile", 12.0))
        y_tile = float(ev.get("y_tile", 12.0))
        ev["px"] = x_tile * 32.0
        ev["py"] = y_tile * 32.0
        ev["stage"] = 1
        ev["mining_progress"] = 0.0
        ev["mining_required"] = 1.5
        ev["ospace_warn_cd"] = 0.0
        ev["startled_cd"] = 0.0

        # Cài đặt thời gian đếm ngược
        duration = float(ev.get("duration", 90.0))
        self.active_event = ev
        self.event_timer = duration
        self.event_history.append(chosen_key)

        # 1. Chuyển đổi thời tiết & kích hoạt hiệu ứng tức thời cho Cơn Mưa Rào Lộc Xuân (sudden_squall)
        if ev.get("weather_override") == "rain" and hasattr(game, "atmosphere") and game.atmosphere:
            atm = game.atmosphere
            try:
                if hasattr(atm, "weather_modes") and "rain" in atm.weather_modes:
                    atm.current_weather_idx = atm.weather_modes.index("rain")
                elif hasattr(atm, "current_weather_idx"):
                    atm.current_weather_idx = 2
            except Exception:
                pass
        if chosen_key == "sudden_squall":
            # Thúc đẩy toàn bộ cây trồng trên bản đồ hiện tại chín nhanh +55% và sinh thêm nấm rừng/quả mọng
            for spot in getattr(game, "harvest_spots", []):
                if not getattr(spot, "ready", True):
                    regen = float(getattr(spot, "regen_time", 20.0))
                    spot.timer = min(regen, float(getattr(spot, "timer", 0.0)) + regen * 0.55)
                    if spot.timer >= regen:
                        spot.ready = True
            state = getattr(game, "state", None)
            if state is not None and hasattr(state, "forage_items"):
                from .game_state import ForageItem
                cur_m = getattr(game, "current_map_id", 1)
                state.forage_items.append(ForageItem("mushroom", 14.5 * 32.0, 13.5 * 32.0, cur_m, False, 1))
                state.forage_items.append(ForageItem("wild_berry", 16.5 * 32.0, 14.2 * 32.0, cur_m, False, 1))

        # 2. Phát âm thanh chuông báo SFX
        if hasattr(game, "audio") and game.audio and hasattr(game.audio, "play_sfx"):
            try:
                game.audio.play_sfx("bite")
            except Exception:
                pass

        # 3. Đẩy Toast thông báo góc màn hình
        title = ev.get("title", "Sự kiện mới")
        map_id = ev.get("map_id", 1)
        if hasattr(game, "vfx") and game.vfx and hasattr(game.vfx, "push_toast"):
            try:
                game.vfx.push_toast(
                    f"SỰ KIỆN: {title}",
                    f"Map {map_id} - Bấm [E] tương tác",
                    "icon_warning",
                    (255, 215, 75),
                )
            except Exception:
                pass

        # 4. Hiển thị thông điệp trên dải băng Banner giữa màn hình
        if hasattr(game, "set_banner"):
            try:
                game.set_banner(
                    f"SỰ KIỆN MỚI: {title}! Di chuyển tới Map {map_id} và bấm [E] nhận thưởng.",
                    (255, 225, 95),
                )
            except Exception:
                pass

        return ev

    # --------------------------------------------------------------------------
    # CHUYỂN SANG SỰ KIỆN KẾ TIẾP (HỖ TRỢ PHÍM TẮT [O])
    # --------------------------------------------------------------------------

    def cycle_next_event(self, game: Any) -> dict[str, Any]:
        """Chuyển đổi ngay sang sự kiện tiếp theo trong danh sách (hỗ trợ phím [O])."""
        keys = list(self.events_db.keys())
        if not keys:
            return {}
        cur_id = self.active_event.get("id") if self.active_event else None
        if cur_id in keys:
            idx = (keys.index(cur_id) + 1) % len(keys)
        else:
            idx = 0
        return self.trigger_random_event(game, keys[idx])

    # --------------------------------------------------------------------------
    # XỬ LÝ KHI BẮT ĐẦU NGÀY MỚI (NEW DAY)
    # --------------------------------------------------------------------------

    def on_new_day(self, game: Any) -> None:
        """Đặt lại số lượng sự kiện hoàn thành trong ngày và có 75% kích hoạt sự kiện đầu ngày."""
        self.events_completed_today = 0
        # 75% cơ hội kích hoạt ngay 1 sự kiện ngẫu nhiên chào ngày mới
        if random.random() < 0.75:
            self.trigger_random_event(game)
        else:
            self.cooldown_timer = float(random.uniform(20.0, 35.0))

    # --------------------------------------------------------------------------
    # CẬP NHẬT VÒNG LẶP THEO KHUNG HÌNH (UPDATE LOOP)
    # --------------------------------------------------------------------------

    def update(self, game: Any, dt: float) -> None:
        """
        Cập nhật tiến trình thời gian cho sự kiện:
        - Giảm thời gian sự kiện đang hoạt động.
        - Tự động đóng sự kiện khi hết giờ và thông báo cho người chơi.
        - Đếm lùi thời gian hồi và tự động sinh sự kiện mới khi sẵn sàng.
        """
        self.anim_time += dt

        if self.active_event is not None:
            ev = self.active_event
            ev_id = ev.get("id", "")
            cur_map = getattr(game, "current_map_id", 1)
            in_interior = getattr(game, "in_interior", False)
            robot = getattr(game, "robot", None)

            if ev.get("ospace_warn_cd", 0.0) > 0.0:
                ev["ospace_warn_cd"] = max(0.0, float(ev["ospace_warn_cd"]) - dt)
            if ev.get("startled_cd", 0.0) > 0.0:
                ev["startled_cd"] = max(0.0, float(ev["startled_cd"]) - dt)

            # Cơ chế động theo khung hình cho từng sự kiện khi Robot ở cùng bản đồ
            if not in_interior and cur_map == ev.get("map_id", 1) and robot is not None:
                px = float(ev.get("px", 0.0))
                py = float(ev.get("py", 0.0))
                dist = math.hypot(robot.x - px, robot.y - py)

                # (A) Cừu non đi lạc (runaway_animals): Hoảng sợ bỏ chạy nếu Robot lao tới nhanh (> 0.38 m/s)
                if ev_id == "runaway_animals" and dist < 115.0 and getattr(robot, "v_mps", 0.0) > 0.38 and not getattr(robot, "is_slow_active", False):
                    ux = (px - robot.x) / max(1.0, dist)
                    uy = (py - robot.y) / max(1.0, dist)
                    ev["px"] = max(160.0, min(960.0, px + ux * 64.0 * dt))
                    ev["py"] = max(160.0, min(600.0, py + uy * 64.0 * dt))
                    if ev.get("startled_cd", 0.0) <= 0.0:
                        ev["startled_cd"] = 2.0
                        if hasattr(game, "set_banner"):
                            game.set_banner(
                                "Cừu non hoảng sợ chạy trốn! Hãy bật Chế độ Đi Chậm [X] khi tiếp cận chú cừu!",
                                (255, 195, 95),
                            )

                # (B) Hội họp O-Space (spontaneous_gathering): Phạt nếu Robot cắt ngang tâm vòng tròn O-Space (< 32 px)
                elif ev_id == "spontaneous_gathering" and dist < 32.0 and ev.get("ospace_warn_cd", 0.0) <= 0.0:
                    ev["ospace_warn_cd"] = 3.0
                    if hasattr(game, "add_score"):
                        game.add_score(-15, "Cắt ngang tâm vòng tròn giao tiếp O-Space!", px, py)
                    if hasattr(game, "comfort_score"):
                        game.comfort_score = max(0.0, float(game.comfort_score) - 12.0)
                    if hasattr(game, "set_banner"):
                        game.set_banner(
                            "VI PHẠM O-SPACE (-15đ): Đừng cắt ngang giữa vòng tròn cư dân! Hãy đứng ở rìa ngoài (35-76px) đi chậm [X] và bấm [E].",
                            (255, 120, 95),
                        )

            self.event_timer -= dt
            if self.event_timer <= 0.0:
                old_title = ev.get("title", "Sự kiện")
                # Nếu đang giao đơn cấp cứu [SOS] bước 2 mà để hết giờ -> phạt trễ hẹn
                if ev_id == "flash_express_order" and ev.get("stage", 1) == 2:
                    if hasattr(game, "add_score"):
                        game.add_score(-25, "Trễ đơn cấp cứu y tế [SOS]!")
                # Đóng sự kiện do hết thời gian
                self.active_event = None
                self.event_timer = 0.0
                self.cooldown_timer = 85.0

                # Thông báo hết giờ cho người chơi
                if hasattr(game, "vfx") and game.vfx and hasattr(game.vfx, "push_toast"):
                    try:
                        game.vfx.push_toast(
                            "HẾT THỜI GIAN SỰ KIỆN",
                            f"Sự kiện '{old_title}' đã kết thúc!",
                            "icon_warning",
                            (220, 180, 150),
                        )
                    except Exception:
                        pass

                if hasattr(game, "set_banner"):
                    try:
                        game.set_banner(
                            f"Sự kiện '{old_title}' đã hết thời gian hiệu lực.",
                            (210, 190, 170),
                        )
                    except Exception:
                        pass
        else:
            # Giảm thời gian chờ cooldown để kích hoạt sự kiện kế tiếp
            self.cooldown_timer -= dt
            if self.cooldown_timer <= 0.0:
                self.trigger_random_event(game)
                self.cooldown_timer = 85.0

    # --------------------------------------------------------------------------
    # TƯƠNG TÁC SỰ KIỆN (BẤM PHÍM [E])
    # --------------------------------------------------------------------------

    def try_interact_event(self, game: Any) -> bool:
        """
        Kiểm tra khi người chơi bấm [E]:
        - Nếu Robot đứng trong bán kính an toàn (<= 68.0 px) của sự kiện đúng bản đồ:
          Hoàn thành sự kiện, trao Vàng, Điểm, Vật phẩm phẩm chất cao và Tim Thiện Cảm.
        - Trả về True nếu tương tác thành công, False nếu không đủ điều kiện.
        """
        if self.active_event is None:
            return False

        cur_map = getattr(game, "current_map_id", 1)
        in_interior = getattr(game, "in_interior", False)
        ev_map = self.active_event.get("map_id", 1)

        # Chỉ tương tác được khi ở cùng bản đồ ngoài trời
        if cur_map != ev_map or in_interior:
            return False

        robot = getattr(game, "robot", None)
        if robot is None:
            return False

        px = float(self.active_event.get("px", 0.0))
        py = float(self.active_event.get("py", 0.0))
        dist = math.hypot(robot.x - px, robot.y - py)
        ev = self.active_event
        ev_id = ev.get("id", "")

        # Ngưỡng khoảng cách tương tác cho phép (mở rộng 78 px cho vòng O-Space)
        max_interact_dist = 78.0 if ev_id == "spontaneous_gathering" else 68.0
        if dist > max_interact_dist:
            return False

        # ----------------------------------------------------------------------
        # XỬ LÝ CƠ CHẾ RIÊNG CHO TỪNG LOẠI SỰ KIỆN (PHA 2)
        # ----------------------------------------------------------------------
        # 1. Thiên thạch Iridium (iridium_meteor): Cần khai thác tích lũy đủ tiến trình
        if ev_id == "iridium_meteor":
            fast_h = bool(getattr(getattr(game, "workshop", None), "bought_status", {}).get("fast_harvest", False))
            step_work = 0.85 if fast_h else 0.55
            ev["mining_progress"] = float(ev.get("mining_progress", 0.0)) + step_work
            req = float(ev.get("mining_required", 1.5))
            if ev["mining_progress"] < req:
                pct = min(99, int(round((ev["mining_progress"] / req) * 100)))
                if hasattr(game, "audio") and game.audio:
                    game.audio.play_sfx("bump")
                if hasattr(game, "set_banner"):
                    game.set_banner(
                        f"Đang khai thác Thiên Thạch Iridium... ({pct}%) — Bấm [E] tiếp để tách khoáng thạch!",
                        (215, 165, 255),
                    )
                return True

        # 2. Tìm túi đồ Bà Evelyn (lost_item_search): Bước 1 nhặt giỏ -> Bước 2 mang tới Bà Evelyn
        elif ev_id == "lost_item_search" and int(ev.get("stage", 1)) == 1:
            ev["stage"] = 2
            ev["title"] = "Trao Giỏ Thảo Dược Cho Bà Evelyn"
            # Tìm vị trí thực tế của Bà Evelyn trên Map 1 (hoặc tọa độ mặc định trước quầy hoa)
            target_x, target_y = 15.5 * 32.0, 10.5 * 32.0
            for npc in getattr(game, "npcs", []):
                if "Evelyn" in getattr(npc, "name", ""):
                    target_x, target_y = float(npc.x), float(npc.y) + 28.0
                    break
            ev["px"], ev["py"] = target_x, target_y
            if hasattr(game, "set_banner"):
                game.set_banner(
                    "Đã nhặt Giỏ Thảo Dược! Hãy mang tới trao cho Bà Evelyn ở Quảng Trường Map 1 bấm [E].",
                    (135, 245, 175),
                )
            return True

        # 3. Đơn cấp cứu y tế [SOS] (flash_express_order): Bước 1 nhận thuốc -> Bước 2 giao Trạm Y Tế
        elif ev_id == "flash_express_order" and int(ev.get("stage", 1)) == 1:
            ev["stage"] = 2
            ev["title"] = "Giao Túi Cấp Cứu [SOS] Tới Trạm Xá Map 1"
            ev["px"], ev["py"] = 20.5 * 32.0, 8.2 * 32.0
            self.event_timer = max(self.event_timer, 65.0)
            if hasattr(game, "set_banner"):
                game.set_banner(
                    "Đã nhận Túi Cấp Cứu [SOS]! Hãy giao khẩn cấp tới cửa Phòng Khám Bác Sĩ Harvey (Đông-Bắc Map 1)!",
                    (255, 155, 125),
                )
            return True

        # 4. Cừu non đi lạc (runaway_animals): Phải đi chậm hoặc dừng lại mới vỗ về được
        elif ev_id == "runaway_animals":
            if getattr(robot, "v_mps", 0.0) > 0.38 and not getattr(robot, "is_slow_active", False):
                if hasattr(game, "set_banner"):
                    game.set_banner(
                        "Bạn đang đi quá nhanh khiến Cừu Non sợ! Hãy bật Đi Chậm [X] hoặc dừng lại rồi bấm [E].",
                        (255, 185, 95),
                    )
                return True

        # 5. Hội họp O-Space (spontaneous_gathering): Không được đứng chèn giữa tâm vòng tròn (< 30 px)
        elif ev_id == "spontaneous_gathering":
            if dist < 30.0:
                if hasattr(game, "set_banner"):
                    game.set_banner(
                        "Hãy lùi ra rìa ngoài vòng tròn O-Space (30-78px) để tôn trọng không gian chung rồi bấm [E]!",
                        (255, 195, 95),
                    )
                return True

        # 6. Thương nhân du mục (traveling_merchant): Thu mua nông sản trong túi đồ với giá x1.8
        elif ev_id == "traveling_merchant":
            from .stardew_systems import ITEM_GOLD_PRICES
            quest_key = getattr(getattr(game, "active_quest", None), "item_key", "") if getattr(getattr(game, "active_quest", None), "status", "") == "accepted" else ""
            sold_count = 0
            bonus_sale_gold = 0
            state = getattr(game, "state", None)
            if state is not None and hasattr(robot, "inventory") and robot.inventory:
                for idx in range(len(robot.inventory) - 1, -1, -1):
                    ik = robot.inventory[idx]
                    if ik != quest_key:
                        _, slot_obj = state.remove_inventory_at(game, idx)
                        base_p = ITEM_GOLD_PRICES.get(ik, 45)
                        q_mult = {0: 1.0, 1: 1.25, 2: 1.5, 3: 2.0}.get(getattr(slot_obj, "quality", 0), 1.0)
                        bonus_sale_gold += int(round(base_p * q_mult * 1.8))
                        sold_count += 1
            if sold_count > 0:
                ev["reward_gold"] = int(ev.get("reward_gold", 90)) + bonus_sale_gold
                ev["reward_item"] = None

        # ----------------------------------------------------------------------
        # HOÀN THÀNH SỰ KIỆN & TRAO THƯỞNG
        # ----------------------------------------------------------------------
        title = ev.get("title", "Sự Kiện")
        gold = int(ev.get("reward_gold", 0))
        score = int(ev.get("reward_score", 0))
        reward_item = ev.get("reward_item")
        reward_quality = int(ev.get("reward_quality", 0))
        reward_hearts = int(ev.get("reward_hearts", 0))
        target_npc = ev.get("target_npc")

        # 1. Cộng Vàng (Gold)
        if hasattr(game, "gold"):
            game.gold += gold
        if hasattr(game, "state") and game.state:
            game.state.daily_gold_earned = getattr(game.state, "daily_gold_earned", 0) + gold

        # 2. Cộng Điểm uy tín (Score)
        if hasattr(game, "add_score"):
            game.add_score(score, f"Sự kiện: {title}", px, py)
        elif hasattr(game, "score"):
            game.score += score

        # 3. Thêm vật phẩm phẩm chất sao vào túi đồ của Robot
        if reward_item and hasattr(game, "state") and game.state:
            if hasattr(game.state, "add_inventory_item"):
                try:
                    game.state.add_inventory_item(game, reward_item, quality=reward_quality)
                except Exception:
                    pass

        # 4. Cộng điểm thiện cảm (Friendship Hearts) với NPC mục tiêu
        if reward_hearts and target_npc and hasattr(game, "dialogue") and game.dialogue:
            try:
                if hasattr(game.dialogue, "adjust_friendship"):
                    game.dialogue.adjust_friendship(target_npc, reward_hearts)
                elif hasattr(game.dialogue, "friendship"):
                    cur_f = game.dialogue.friendship.get(target_npc, 200)
                    game.dialogue.friendship[target_npc] = cur_f + reward_hearts
            except Exception:
                pass

        # 5. Phát âm thanh SFX đồng vàng leng keng
        if hasattr(game, "audio") and game.audio and hasattr(game.audio, "play_sfx"):
            try:
                game.audio.play_sfx("gold")
            except Exception:
                pass

        # 6. Đẩy Toast thông báo phần thưởng
        if hasattr(game, "vfx") and game.vfx and hasattr(game.vfx, "push_toast"):
            try:
                game.vfx.push_toast(
                    "HOÀN THÀNH SỰ KIỆN!",
                    f"+{gold}G | +{score}đ",
                    "icon_coin",
                    (120, 255, 150),
                )
            except Exception:
                pass

        # 7. Cập nhật dải băng Banner
        if hasattr(game, "set_banner"):
            try:
                game.set_banner(
                    f"Hoàn thành sự kiện: {title}! Nhận +{gold}G, +{score}đ.",
                    (120, 255, 150),
                )
            except Exception:
                pass

        # 8. Cập nhật thống kê và kết thúc sự kiện
        self.events_completed_today += 1
        self.total_events_completed += 1
        self.active_event = None
        self.event_timer = 0.0
        self.cooldown_timer = 85.0

        return True

    # --------------------------------------------------------------------------
    # KẾT XUẤT ĐỒ HỌA SỰ KIỆN TRÊN THẾ GIỚI (RENDER WORLD EVENT)
    # --------------------------------------------------------------------------

    def render_world_event(self, screen: pygame.Surface, game: Any) -> None:
        """
        Vẽ hiệu ứng thực địa tại tọa độ sự kiện:
        - Vòng hào quang phát sáng Pulsing Halo co giãn theo nhịp sin.
        - Sprite đại diện tương ứng từ SpriteVault hoặc vector pixel sắc sảo.
        - Nhãn nổi song ngữ tiếng Việt thuần túy, tuyệt đối không dùng emoji gây lỗi font.
        """
        if self.active_event is None:
            return

        cur_map = getattr(game, "current_map_id", 1)
        in_interior = getattr(game, "in_interior", False)
        ev_map = self.active_event.get("map_id", 1)

        if cur_map != ev_map or in_interior:
            return

        px = float(self.active_event.get("px", 0.0))
        py = float(self.active_event.get("py", 0.0))

        # Áp dụng độ lệch rung màn hình camera shake nếu có
        ox, oy = 0, 0
        if hasattr(game, "vfx") and game.vfx and hasattr(game.vfx, "get_shake_offset"):
            try:
                ox, oy = game.vfx.get_shake_offset()
            except Exception:
                pass

        draw_x = int(round(px + ox))
        draw_y = int(round(py + oy))

        ev_id = self.active_event.get("id", "")
        gold_reward = self.active_event.get("reward_gold", 0)

        # 1. Tính toán màu sắc hào quang và nhịp thở phát sáng
        pulse = (math.sin(self.anim_time * 3.6) + 1.0) * 0.5  # Dao động [0.0..1.0]
        base_r = int(26 + pulse * 9)

        if ev_id == "iridium_meteor":
            glow_color = (195, 75, 245)       # Tím Iridium huyền ảo
            inner_color = (245, 195, 255)
        elif ev_id == "sudden_squall":
            glow_color = (60, 185, 255)       # Xanh lam mưa xuân
            inner_color = (190, 240, 255)
        elif ev_id == "runaway_animals":
            glow_color = (95, 225, 120)       # Xanh ngọc thảo nguyên
            inner_color = (210, 255, 180)
        else:
            glow_color = (255, 215, 65)       # Vàng óng ấm áp
            inner_color = (255, 245, 180)

        # Vẽ vòng hào quang nhiều lớp mờ mượt mà
        halo_diam = base_r * 4
        halo_surf = pygame.Surface((halo_diam, halo_diam), pygame.SRCALPHA)
        center = halo_diam // 2

        # Lớp quầng mờ ngoài cùng
        outer_alpha = max(15, min(120, int(35 + pulse * 45)))
        pygame.draw.circle(
            halo_surf,
            (*glow_color, outer_alpha),
            (center, center),
            int(base_r * 1.35),
        )

        # Vòng viền phát sáng giữa
        mid_alpha = max(50, min(200, int(90 + pulse * 60)))
        pygame.draw.circle(
            halo_surf,
            (*glow_color, mid_alpha),
            (center, center),
            base_r,
            width=2,
        )

        # Lõi phát sáng trung tâm
        core_alpha = max(90, min(255, int(130 + pulse * 70)))
        pygame.draw.circle(
            halo_surf,
            (*inner_color, core_alpha),
            (center, center),
            max(5, int(base_r * 0.45)),
        )

        screen.blit(halo_surf, (draw_x - center, draw_y - center))

        # 2. Vẽ Sprite / Biểu tượng vật thể sự kiện
        vault = getattr(game, "vault", None)
        sprite_drawn = False

        if vault is not None:
            if ev_id == "iridium_meteor":
                sp = vault.scaled("rock_3", 34, 34)
                if sp:
                    screen.blit(sp, (draw_x - 17, draw_y - 17))
                    sprite_drawn = True
                    # Vẽ 4 tia sao lấp lánh tím quanh thiên thạch
                    self._draw_twinkle_stars(screen, draw_x, draw_y, glow_color)
            elif ev_id == "runaway_animals":
                sp = vault.scaled("sheep", 34, 34)
                if sp:
                    bob_y = int(math.sin(self.anim_time * 5.0) * 2.0)
                    screen.blit(sp, (draw_x - 17, draw_y - 17 + bob_y))
                    sprite_drawn = True
            elif ev_id in ("lost_item_search", "flash_express_order"):
                sp = vault.scaled("icon_parcel", 30, 30) or vault.scaled("crate", 30, 30)
                if sp:
                    screen.blit(sp, (draw_x - 15, draw_y - 15))
                    sprite_drawn = True
            elif ev_id == "traveling_merchant":
                sp = vault.scaled("crate", 34, 34) or vault.scaled("barrel", 34, 34)
                if sp:
                    screen.blit(sp, (draw_x - 17, draw_y - 17))
                    sprite_drawn = True

        # Vẽ hình dạng dự phòng nếu sprite chưa nạp
        if not sprite_drawn:
            if ev_id == "spontaneous_gathering":
                # Vòng tròn họp nhóm O-Space nét đứt với các chấm người
                self._draw_o_space_gathering(screen, draw_x, draw_y, glow_color)
            elif ev_id == "sudden_squall":
                # Biểu tượng trạm nước và giọt mưa xanh ngọc
                self._draw_water_squall_icon(screen, draw_x, draw_y, glow_color)
            else:
                # Viên tinh thể ngọc hình thoi đa giác 3D
                self._draw_fallback_crystal(screen, draw_x, draw_y, glow_color, inner_color)

        # 3. Vẽ nhãn nổi chỉ dẫn phía trên vật thể (Floating Label)
        self._draw_floating_label(screen, game, draw_x, draw_y - base_r - 12, ev_id, gold_reward, glow_color)

    # --------------------------------------------------------------------------
    # CÁC HÀM TRỢ GIÚP ĐỒ HỌA WORLD RENDERING
    # --------------------------------------------------------------------------

    def _draw_twinkle_stars(
        self,
        screen: pygame.Surface,
        cx: int,
        cy: int,
        color: tuple[int, int, int],
    ) -> None:
        """Vẽ các hạt sao lấp lánh hình thoi xung quanh thiên thạch Iridium."""
        offsets = [
            (-18, -14, 0.0),
            (17, -15, 1.6),
            (-14, 16, 3.2),
            (19, 14, 4.8),
        ]
        for ox, oy, phase in offsets:
            tw = (math.sin(self.anim_time * 6.0 + phase) + 1.0) * 0.5
            s = int(2 + tw * 3.5)
            sx = cx + ox
            sy = cy + oy
            pts = [(sx, sy - s), (sx + s, sy), (sx, sy + s), (sx - s, sy)]
            pygame.draw.polygon(screen, (255, 240, 255), pts)
            pygame.draw.polygon(screen, color, pts, 1)

    def _draw_o_space_gathering(
        self,
        screen: pygame.Surface,
        cx: int,
        cy: int,
        color: tuple[int, int, int],
    ) -> None:
        """Vẽ vòng tròn không gian xã hội O-Space biểu trưng cho buổi hội họp cư dân."""
        r = 28
        dash_surf = pygame.Surface((r * 2 + 10, r * 2 + 10), pygame.SRCALPHA)
        center = r + 5
        # Vẽ các cung tròn nét đứt quanh tâm
        for deg in range(0, 360, 30):
            rad1 = math.radians(deg)
            rad2 = math.radians(deg + 18)
            x1 = center + int(math.cos(rad1) * r)
            y1 = center + int(math.sin(rad1) * r)
            x2 = center + int(math.cos(rad2) * r)
            y2 = center + int(math.sin(rad2) * r)
            pygame.draw.line(dash_surf, (*color, 180), (x1, y1), (x2, y2), 2)

        # Vẽ 3 biểu tượng vị trí cư dân nhỏ gọn
        for angle in (0.0, 2.1, 4.2):
            nx = center + int(math.cos(angle + self.anim_time * 0.5) * (r * 0.65))
            ny = center + int(math.sin(angle + self.anim_time * 0.5) * (r * 0.65))
            pygame.draw.circle(dash_surf, (255, 255, 230, 220), (nx, ny), 4)
            pygame.draw.circle(dash_surf, (80, 50, 25, 200), (nx, ny), 4, 1)

        screen.blit(dash_surf, (cx - center, cy - center))

    def _draw_water_squall_icon(
        self,
        screen: pygame.Surface,
        cx: int,
        cy: int,
        color: tuple[int, int, int],
    ) -> None:
        """Vẽ biểu tượng trạm nước sinh thái kết hợp gợn sóng mưa xuân."""
        # Bệ trạm nước hình trụ
        pygame.draw.rect(screen, (75, 120, 160), (cx - 12, cy - 4, 24, 16), border_radius=3)
        pygame.draw.rect(screen, (160, 210, 245), (cx - 12, cy - 4, 24, 16), width=1, border_radius=3)
        # Giọt nước pha lê lớn ở trên
        pts = [(cx, cy - 18), (cx + 8, cy - 6), (cx, cy), (cx - 8, cy - 6)]
        pygame.draw.polygon(screen, color, pts)
        pygame.draw.polygon(screen, (230, 250, 255), pts, 1)

    def _draw_fallback_crystal(
        self,
        screen: pygame.Surface,
        cx: int,
        cy: int,
        color: tuple[int, int, int],
        inner: tuple[int, int, int],
    ) -> None:
        """Vẽ viên tinh thể lục giác phát sáng đại diện cho vật phẩm sự kiện."""
        pts = [
            (cx, cy - 16),
            (cx + 12, cy - 6),
            (cx + 12, cy + 8),
            (cx, cy + 16),
            (cx - 12, cy + 8),
            (cx - 12, cy - 6),
        ]
        pygame.draw.polygon(screen, color, pts)
        pygame.draw.polygon(screen, inner, pts, 2)
        pygame.draw.circle(screen, (255, 255, 255), (cx, cy), 3)

    def _draw_floating_label(
        self,
        screen: pygame.Surface,
        game: Any,
        cx: int,
        bottom_y: int,
        ev_id: str,
        gold: int,
        glow_color: tuple[int, int, int],
    ) -> None:
        """Vẽ nhãn nổi 1 dòng nhỏ gọn chỉ khi Robot đứng gần <= 115px để không che bản đồ."""
        robot = getattr(game, "robot", None)
        if robot is not None and math.hypot(robot.x - cx, robot.y - bottom_y) > 115.0:
            return

        line1 = f"[E] Sự kiện (+{gold}G)"
        font_sub = self._get_font(game, "xs")
        surf1 = font_sub.render(line1, True, (130, 255, 160))

        w = surf1.get_width() + 12
        h = 18
        bx = cx - w // 2
        by = bottom_y - h

        bg_surf = pygame.Surface((w, h), pygame.SRCALPHA)
        bg_surf.fill((20, 18, 28, 195))
        screen.blit(bg_surf, (bx, by))
        pygame.draw.rect(screen, (*glow_color, 190), (bx, by, w, h), width=1, border_radius=4)
        screen.blit(surf1, (bx + 6, by + 1))

    # --------------------------------------------------------------------------
    # KẾT XUẤT THẺ THÔNG BÁO SỰ KIỆN TRÊN HUD (RENDER EVENT HUD)
    # --------------------------------------------------------------------------

    def render_event_hud(self, screen: pygame.Surface, game: Any) -> None:
        """
        Vẽ thanh thông báo sự kiện 1 dòng siêu gọn ở phía trên giữa màn hình (h = 22px),
        tự động rút gọn nội dung để chữ luôn nằm gọn 100% bên trong khung thanh.
        """
        if self.active_event is None:
            return

        title = str(self.active_event.get("title", "Sự Kiện")).strip()
        map_id = self.active_event.get("map_id", 1)
        gold = self.active_event.get("reward_gold", 80)
        duration = float(self.active_event.get("duration", 90.0))
        remain_sec = max(0, int(self.event_timer))

        font = self._get_font(game, "xs")
        max_box_w = 390
        max_text_w = max_box_w - 26

        suffix = f" (M{map_id}, +{gold}G) [E]"
        prefix = f"[SK {remain_sec}s] "
        short_title = title
        line_str = f"{prefix}{short_title}{suffix}"
        while len(short_title) > 6 and font.size(line_str)[0] > max_text_w:
            short_title = short_title[:-1].rstrip()
            line_str = f"{prefix}{short_title}…{suffix}"

        l_surf = font.render(line_str, True, (255, 238, 140))

        w = min(max_box_w, l_surf.get_width() + 26)
        h = 22
        x = (screen.get_width() - w) // 2
        y = 42 if getattr(game, "banner_timer", 0.0) > 0.0 else 6

        hud_surf = pygame.Surface((w, h), pygame.SRCALPHA)
        pygame.draw.rect(hud_surf, (22, 18, 30, 205), (0, 0, w, h), border_radius=5)
        pygame.draw.rect(hud_surf, (235, 185, 68, 215), (0, 0, w, h), width=1, border_radius=5)

        ratio = max(0.0, min(1.0, self.event_timer / max(1.0, duration)))
        bar_w = int((w - 10) * ratio)
        bar_color = (115, 235, 155) if ratio > 0.35 else ((255, 210, 70) if ratio > 0.15 else (255, 95, 85))
        if bar_w > 0:
            pygame.draw.rect(hud_surf, bar_color, (5, h - 3, bar_w, 2), border_radius=1)

        pygame.draw.circle(hud_surf, bar_color, (11, h // 2 - 1), 3)
        hud_surf.blit(l_surf, (18, 2))
        screen.blit(hud_surf, (x, y))

    # --------------------------------------------------------------------------
    # QUẢN LÝ FONT CHỮ DỰ PHÒNG AN TOÀN
    # --------------------------------------------------------------------------

    def _get_font(self, game: Any, size_key: str = "xs") -> pygame.font.Font:
        """Lấy phông chữ từ trò chơi hoặc nạp Segoe UI tiếng Việt chuẩn."""
        game_attr = f"font_{size_key}"
        if hasattr(game, game_attr) and getattr(game, game_attr) is not None:
            return getattr(game, game_attr)

        if size_key not in self._font_cache:
            pt = 13 if size_key == "xs" else (15 if size_key == "sm" else 18)
            try:
                self._font_cache[size_key] = pygame.font.SysFont("Segoe UI", pt, bold=True)
            except Exception:
                self._font_cache[size_key] = pygame.font.Font(None, pt + 4)

        return self._font_cache[size_key]
