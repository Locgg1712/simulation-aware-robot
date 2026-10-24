# game/quests.py
"""
Hệ thống Nhiệm vụ (Quests) & Tương tác Phím [E] trong FarmBot Town:
1. Nhiệm vụ Thu hoạch Trái cây & Nông sản Giao Tận Nhà (Map 2 -> Map 5)
2. Nhiệm vụ Câu Cá tại Bến Hồ (Map 3 -> Map 5)
3. Nhiệm vụ Chuyển Phát Nhanh Liên Bản Đồ (Town Express Delivery - Bonus Timer)
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass
import pygame

from .constants import (
    INTERACT_MAX_M,
    INTERACT_MIN_M,
    ITEM_NAMES_VI,
    SCORE_ACCEPT_QUEST,
    SCORE_CATCH_FISH,
    SCORE_DELIVER_INDOOR,
    SCORE_DELIVER_OUTDOOR,
    SCORE_EXPRESS_BONUS,
    px_to_m,
)
from .entities import HarvestSpot, VillagerNPC
from .safety_hri import check_front_interaction
from .stardew_systems import try_use_shipping_bin


@dataclass
class Quest:
    """Cấu trúc một nhiệm vụ trong FarmBot Town."""
    quest_id: str
    category: str          # "harvest" | "fishing" | "express"
    title: str
    giver_name: str
    giver_map: int
    receiver_name: str
    receiver_map: int      # 1..4 (ngoài trời) hoặc 5 (trong nhà)
    receiver_house_id: str
    receiver_place: str
    item_key: str
    item_label: str
    source_hint: str
    status: str = "available"  # "available" -> "accepted" -> "completed"
    bonus_timer: float = 0.0
    bonus_time_limit: float = 0.0

    @property
    def state(self) -> str:
        if self.status == "accepted":
            return "active"
        return self.status

    @state.setter
    def state(self, val: str):
        self.status = "accepted" if val == "active" else val

    def Item_in_inventory(self, inventory: list[str]) -> bool:
        return self.item_key in inventory


def build_default_quests() -> list[Quest]:
    return [
        Quest(
            quest_id="q1_fruit",
            category="harvest",
            title="NV1: Hái Táo Đỏ Giao Tận Nhà",
            giver_name="Bà Evelyn",
            giver_map=1,
            receiver_name="Đầu bếp Gus",
            receiver_map=5,
            receiver_house_id="house_gus",
            receiver_place="Nhà Đầu Bếp Gus (Map 4 -> Vào Nhà Map 5)",
            item_key="apple",
            item_label="Táo Đỏ Chín",
            source_hint="Lên Map 2 (Nông Trại), đứng cạnh Cây Táo Đỏ bấm [E] 1.5s (+30đ)",
        ),
        Quest(
            quest_id="q2_fish",
            category="fishing",
            title="NV2: Câu Cá Hồ Cho Thợ Mộc Robin",
            giver_name="Ông George",
            giver_map=1,
            receiver_name="Thợ mộc Robin",
            receiver_map=5,
            receiver_house_id="house_robin",
            receiver_place="Nhà Thợ Mộc Robin (Map 4 -> Vào Nhà Map 5)",
            item_key="fish",
            item_label="Cá Hồ Tươi",
            source_hint="Sang Map 3 (Bến Hồ), ra Cầu Tàu bấm [E] thả câu & kéo cá (+50đ)",
        ),
        Quest(
            quest_id="q3_express",
            category="express",
            title="NV3: Chuyển Phát Nhanh Cho Thị Trưởng",
            giver_name="Chủ tiệm Pierre",
            giver_map=1,
            receiver_name="Thị trưởng Lewis",
            receiver_map=5,
            receiver_house_id="house_lewis",
            receiver_place="Dinh Thự Thị Trưởng (Map 4 -> Vào Nhà Map 5)",
            item_key="parcel",
            item_label="Kiện Hàng Nhanh",
            source_hint="Giữ Kiện Hàng trong Khay đồ, giao kịp giờ thưởng thêm +50đ",
            bonus_timer=85.0,
            bonus_time_limit=85.0,
        ),
        Quest(
            quest_id="q4_strawberry",
            category="harvest",
            title="NV4: Thu Hoạch Dâu Tây Tặng Cô Haley",
            giver_name="Bà Evelyn",
            giver_map=1,
            receiver_name="Cô Haley",
            receiver_map=4,
            receiver_house_id="",
            receiver_place="Đường Làng Khu Dân Cư (Map 4 Ngoài Trời)",
            item_key="strawberry",
            item_label="Dâu Tây Đỏ",
            source_hint="Tới Ruộng Dâu Tây (Map 1 hoặc Map 2) bấm [E] 1.5s (+30đ)",
        ),
        Quest(
            quest_id="q5_pumpkin",
            category="harvest",
            title="NV5: Thu Hoạch Bí Ngô Cho Ngư Phủ Willy",
            giver_name="Chủ tiệm Pierre",
            giver_map=1,
            receiver_name="Ngư phủ Willy",
            receiver_map=5,
            receiver_house_id="house_willy",
            receiver_place="Nhà Ngư Phủ Willy (Map 4 -> Vào Nhà Map 5)",
            item_key="pumpkin",
            item_label="Bí Ngô Vàng",
            source_hint="Tới Ruộng Bí Ngô (Map 2 hoặc Map 4) bấm [E] 1.5s (+30đ)",
            bonus_timer=95.0,
            bonus_time_limit=95.0,
        ),
        Quest(
            quest_id="q6_special_spring",
            category="harvest",
            title="Đơn Mùa Vụ: Hoa Cúc Vàng Tặng Bà Evelyn",
            giver_name="Cô giáo Penny",
            giver_map=4,
            receiver_name="Bà Evelyn",
            receiver_map=1,
            receiver_house_id="",
            receiver_place="Quảng Trường Thị Trấn (Map 1 Ngoài Trời)",
            item_key="golden_flower",
            item_label="Hoa Cúc Vàng",
            source_hint="Tìm nhặt Hoa Cúc Vàng mọc dã ngoại quanh Bờ Sông Map 1 / Map 4 bấm [E]",
            bonus_timer=110.0,
            bonus_time_limit=110.0,
        ),
        Quest(
            quest_id="q7_special_chef",
            category="harvest",
            title="Đơn Đặc Biệt 3♥: Nấm Rừng Cho Đầu Bếp Gus",
            giver_name="Ông George",
            giver_map=1,
            receiver_name="Đầu bếp Gus",
            receiver_map=5,
            receiver_house_id="house_gus",
            receiver_place="Nhà Đầu Bếp Gus (Map 4 -> Vào Nhà Map 5)",
            item_key="mushroom",
            item_label="Nấm Rừng Thơm",
            source_hint="Tìm nhặt Nấm Rừng Thơm trên Đảo Rừng Map 3 hoặc bìa rừng Map 2 bấm [E]",
            bonus_timer=120.0,
            bonus_time_limit=120.0,
        ),
        Quest(
            quest_id="q8_wheat_marnie",
            category="harvest",
            title="NV8: Lúa Mì Vàng Cho Đàn Gia Súc Của Marnie",
            giver_name="Quản nông Kent",
            giver_map=2,
            receiver_name="Nông dân Marnie",
            receiver_map=2,
            receiver_house_id="",
            receiver_place="Đường lát đá Đại Nông Trại (Map 2 Ngoài Trời — Marnie đang đi tuần)",
            item_key="wheat",
            item_label="Lúa Mì Vàng",
            source_hint="Tới Ruộng Lúa Mì góc Đông-Bắc Map 2 bấm [E] 1.5s rồi đuổi theo Marnie đang đi tuần",
        ),
        Quest(
            quest_id="q9_fish_leo",
            category="fishing",
            title="NV9: Cá Tươi Cho Chàng Mèo Leo",
            giver_name="Kỹ sư Sebastian",
            giver_map=3,
            receiver_name="Chàng mèo Leo",
            receiver_map=3,
            receiver_house_id="",
            receiver_place="Lối đất ven hồ (Map 3 Ngoài Trời — Leo đang đi dạo)",
            item_key="fish",
            item_label="Cá Hồ Tươi",
            source_hint="Ra Cầu Tàu Map 3 câu cá, rồi chặn trước mặt Leo trên lối đất ven hồ (đi chậm [X] vì Leo là trẻ nhỏ)",
            bonus_timer=100.0,
            bonus_time_limit=100.0,
        ),
        Quest(
            quest_id="q10_peach_clinic",
            category="harvest",
            title="NV10: Đào Tiên Bào Chế Thuốc Cho Bác Sĩ Harvey",
            giver_name="Dược sĩ Maru",
            giver_map=4,
            receiver_name="Bác sĩ Harvey",
            receiver_map=5,
            receiver_house_id="clinic_house",
            receiver_place="Phòng Khám Y Tế (Map 1 -> Vào Nhà Map 5)",
            item_key="peach",
            item_label="Đào Tiên Hồng",
            source_hint="Lên Map 2 hái Đào Tiên ở vườn cây ăn quả bấm [E] 1.5s",
        ),
    ]


def distance_to_harvest_spot(rx: float, ry: float, spot: HarvestSpot) -> float:
    """Khoảng cách từ Robot tới điểm thu hoạch hoặc mép thửa ruộng gần nhất."""
    d_point = math.hypot(spot.x - rx, spot.y - ry)
    if spot.field_rect is not None:
        r = spot.field_rect
        cx = max(r.left, min(rx, r.right))
        cy = max(r.top, min(ry, r.bottom))
        d_rect = math.hypot(rx - cx, ry - cy)
        return min(d_point, d_rect)
    return d_point


def handle_interact_action(game):
    """Xử lý phím [E] theo ngữ cảnh: Báo cáo cuối ngày, Hộp thoại, Câu cá, Thùng bán hàng, Nhặt đồ, Mở cửa nhà, Giao tiếp NPC, Hái quả/ruộng."""
    if game.game_over or game.robot.stun_timer > 0.0:
        return

    # 0. Nếu Bảng Báo Cáo Cuối Ngày đang mở -> Bấm [E] để sang Ngày Mới
    if getattr(getattr(game, "state", None), "summary_open", False):
        game.state.close_summary_modal(game)
        return

    # 0a. Nếu Hộp thoại Chân dung Stardew đang mở -> Bấm [E] để hiện hết chữ hoặc đóng hộp thoại
    if getattr(game, "dialogue", None) is not None and game.dialogue.active:
        game.dialogue.advance_or_close()
        return

    # 0b. Nếu đang chơi Mini-game Thanh Câu Cá Stardew -> Bấm hoặc giữ phím [E] sẽ đẩy thanh câu cá lên
    if getattr(game, "fishing_minigame", None) is not None and game.fishing_minigame.active:
        if hasattr(game.fishing_minigame, "boost_bar"):
            game.fishing_minigame.boost_bar()
        return

    # Tự động phanh dừng Robot ngay khi người chơi bấm [E] để hỗ trợ tương tác lịch sự
    game.robot.v_mps = 0.0
    game.robot.vx = 0.0
    game.robot.vy = 0.0

    # 0c. Kiểm tra nhặt lại món đồ bị rơi khi ngã Cấp 2 hoặc nhặt Vật Phẩm Dã Ngoại (Foraging)
    if getattr(game, "state", None) is not None:
        if game.state.try_pickup_dropped_items(game):
            if getattr(game, "audio", None) is not None:
                game.audio.play_sfx("harvest")
            return
        if game.state.try_pickup_forage(game):
            if getattr(game, "audio", None) is not None:
                game.audio.play_sfx("harvest")
            if getattr(game, "vfx", None) is not None:
                game.vfx.push_toast("Khám Phá Dã Ngoại!", "Đã nhặt vật phẩm tự nhiên (+25đ)", "mushroom")
            return

    # 0d. Kiểm tra tương tác với Sự Kiện Ngẫu Nhiên (Random World Events - Phím [E])
    if getattr(game, "random_events", None) is not None:
        if game.random_events.try_interact_event(game):
            return

    # 1. Nếu đang câu cá ở trạng thái cá cắn câu ('biting') -> Mở Mini-game Thanh Câu Cá Stardew Valley!
    if game.robot.fishing_state == "biting":
        if getattr(game, "fishing_minigame", None) is not None:
            game.fishing_minigame.start()
            game.set_banner(
                "CÁ ĐÃ MẮC CÂU! Giữ [SPACE] / [E] / [W] hoặc Chuột Trái để giữ thanh xanh lá bám theo con cá!",
                (115, 255, 148),
            )
            return
        if game.robot.add_item("fish"):
            game.add_score(SCORE_CATCH_FISH, "Câu được Cá Hồ Tươi!")
            game.set_banner(
                "Tuyệt vời! Bạn đã kéo trúng Cá Hồ Tươi (+50đ) vào Khay chứa đồ!",
                (115, 255, 148),
            )
        else:
            game.set_banner("Khay chứa đồ đã đầy! Hãy đi giao bớt vật phẩm.", (255, 185, 95))
        game.robot.fishing_state = "idle"
        game.robot.fishing_spot = None
        return
    elif game.robot.fishing_state == "waiting":
        game.robot.fishing_state = "idle"
        game.robot.fishing_spot = None
        game.set_banner(
            "Bạn kéo cần câu quá sớm khi cá chưa cắn câu! Hãy bấm [E] thả câu lại.",
            (255, 195, 110),
        )
        return

    # 1b. Kiểm tra Thùng Giao Hàng Nông Trại (Shipping Bin ở Map 2) để bán nông sản lấy Vàng (G)
    if try_use_shipping_bin(game):
        return

    # 2. Kiểm tra Cửa Ra/Vào Nhà (Map 5 Portal có hiệu ứng Fade mượt)
    if game.in_interior:
        rx, ry = game.room_rect.x, game.room_rect.y
        rw, rh = game.room_rect.width, game.room_rect.height
        exit_mat_rect = pygame.Rect(game.room_rect.centerx - 42, ry + rh - 34, 84, 30)
        if math.hypot(exit_mat_rect.centerx - game.robot.x, exit_mat_rect.centery - game.robot.y) < 76.0:
            if getattr(game, "audio", None) is not None:
                game.audio.play_sfx("portal")
            if getattr(game, "vfx", None) is not None:
                game.vfx.start_transition(lambda: game.exit_house())
            else:
                game.exit_house()
            return
    else:
        for b in game.props:
            if b.door_rect and math.hypot(
                b.door_rect.centerx - game.robot.x, b.door_rect.centery - game.robot.y
            ) < 68.0:
                if getattr(game, "audio", None) is not None:
                    game.audio.play_sfx("portal")
                if getattr(game, "vfx", None) is not None:
                    game.vfx.start_transition(lambda b_obj=b: game.enter_house(b_obj))
                else:
                    game.enter_house(b)
                return

    # 3. Kiểm tra giao tiếp với NPC gần nhất (Áp dụng Vùng Quạt Xanh trước mặt NPC)
    active_npcs = game.interior_npcs if game.in_interior else game.npcs
    if active_npcs:
        nearest_npc = min(
            active_npcs,
            key=lambda n: math.hypot(n.x - game.robot.x, n.y - game.robot.y),
        )
        dist_m = px_to_m(math.hypot(nearest_npc.x - game.robot.x, nearest_npc.y - game.robot.y))
        if dist_m <= 2.40:
            _interact_with_npc(game, nearest_npc)
            return

    # 4. Kiểm tra Điểm Hái Trái Cây / Thửa Ruộng Nông Sản
    if not game.in_interior and game.harvest_spots:
        nearest_h = min(
            game.harvest_spots,
            key=lambda h: distance_to_harvest_spot(game.robot.x, game.robot.y, h),
        )
        if distance_to_harvest_spot(game.robot.x, game.robot.y, nearest_h) <= 78.0:
            if not nearest_h.has_produce:
                game.set_banner(
                    f"{nearest_h.title} đang mọc lại, hãy thử cây hoặc ruộng bên cạnh!",
                    (255, 205, 115),
                )
            elif len(game.robot.inventory) >= game.robot.max_inventory:
                game.set_banner("Khay 4 ô chứa đồ đã đầy! Hãy đi giao hàng trước khi thu hoạch tiếp.", (255, 175, 95))
            else:
                game.robot.harvest_target = nearest_h
                game.robot.harvest_timer = 0.0
                game.robot.v_mps = 0.0
                game.set_banner(
                    f"Đang thu hoạch {ITEM_NAMES_VI[nearest_h.item_key]} tại {nearest_h.title} (1.5s)...",
                    (158, 242, 148),
                )
            return

    # 5. Kiểm tra Điểm Thả Câu Cá (Map 3)
    if not game.in_interior and game.fishing_spots:
        nearest_f = min(
            game.fishing_spots,
            key=lambda f: math.hypot(f.stand_x - game.robot.x, f.stand_y - game.robot.y),
        )
        if math.hypot(nearest_f.stand_x - game.robot.x, nearest_f.stand_y - game.robot.y) <= 78.0:
            if len(game.robot.inventory) >= game.robot.max_inventory:
                game.set_banner("Khay 4 ô chứa đồ đã đầy! Hãy đi giao bớt đồ trước khi câu cá.", (255, 175, 95))
            else:
                game.robot.fishing_spot = nearest_f
                game.robot.fishing_state = "waiting"
                game.robot.fishing_timer = random.uniform(1.8, 3.2)
                game.robot.v_mps = 0.0
                game.robot.theta = math.atan2(
                    nearest_f.water_y - game.robot.y, nearest_f.water_x - game.robot.x
                )
                game.set_banner(
                    "Đã thả cần câu xuống hồ! Đợi 2-3 giây đến khi phao nảy [!!] rồi bấm [E] ngay!",
                    (135, 228, 255),
                )
            return

    game.set_banner(
        "Chưa có mục tiêu ở gần! Hãy tiến vào Quạt Xanh trước mặt NPC, Thửa ruộng, Cây quả, Điểm câu hoặc Cửa nhà rồi bấm [E].",
        (235, 215, 155),
    )


def _interact_with_npc(game, npc: VillagerNPC):
    if npc.knockdown_timer > 0.0 or npc.is_run_over_dead:
        game.set_banner(f"{npc.name} đang bị choáng sau va chạm, không thể trò chuyện!", (255, 120, 120))
        return

    # Khi bấm [E] gần NPC, tự động xoay hướng mặt Robot nhìn vào NPC để thuận tiện thao tác
    game.robot.theta = math.atan2(npc.y - game.robot.y, npc.x - game.robot.x)
    game.robot.v_mps = 0.0

    ok_all, details = check_front_interaction(game.robot, npc)
    # Cho phép dung sai nhẹ khi người chơi đã đứng phía trước NPC
    lenient_ok = (
        0.66 <= details["d_m"] <= 1.65
        and details["delta_npc_deg"] <= 45.0
    )
    if not (ok_all or lenient_ok):
        if not details["ok_front"]:
            game.set_banner(
                f"Hãy bước vào Vùng Quạt Xanh phía trước mặt {npc.name} (góc ±35°) rồi bấm [E]!",
                (255, 195, 95),
            )
        elif details["d_m"] < INTERACT_MIN_M:
            game.set_banner(
                f"Bạn đứng quá sát {npc.name} ({details['d_m']:.2f}m < 0.75m)! Hãy lùi nhẹ ra giữa Quạt Xanh.",
                (255, 165, 95),
            )
        elif details["d_m"] > INTERACT_MAX_M:
            game.set_banner(
                f"Bạn đứng hơi xa {npc.name} ({details['d_m']:.2f}m > 1.45m)! Hãy tiến vào Quạt Xanh.",
                (255, 215, 115),
            )
        return

    q = game.active_quest

    # 1. Kiểm tra Giao Vật Phẩm Nhiệm Vụ (Deliver Item)
    if q.status == "accepted" and q.receiver_name == npc.name:
        in_right_place = (
            (q.receiver_map == 5 and game.in_interior)
            or (q.receiver_map != 5 and not game.in_interior)
        )
        if in_right_place and q.item_key in game.robot.inventory:
            delivered_key = q.item_key
            delivered_name = ITEM_NAMES_VI.get(delivered_key, delivered_key)
            # Kiểm tra chất lượng sao của vật phẩm giao hàng
            quality_mult = 1.0
            star_lbl = ""
            if getattr(game, "state", None) is not None:
                game.state.sync_slot_meta_with_inventory(game.robot.inventory)
                idx_item = game.robot.inventory.index(delivered_key)
                _, slot_meta = game.state.remove_inventory_at(game, idx_item)
                if slot_meta is not None:
                    quality_mult = {0: 1.0, 1: 1.25, 2: 1.5, 3: 2.0}.get(slot_meta.quality, 1.0)
                    star_lbl = slot_meta.stars_label
            else:
                game.robot.remove_item(delivered_key)

            npc.handoff_timer = 1.4
            npc.trigger_emote("♥", 3.0)
            pts = int(round((SCORE_DELIVER_INDOOR if game.in_interior else SCORE_DELIVER_OUTDOOR) * quality_mult))
            place_label = "Trong Nhà Map 5" if game.in_interior else "Ngoài Trời"
            game.add_score(pts, f"Giao {delivered_name}{star_lbl} ({place_label})!")
            gold_bonus = int(round(60 * quality_mult))
            if q.bonus_time_limit > 0.0 and q.bonus_timer > 0.0:
                game.add_score(SCORE_EXPRESS_BONUS, "Thưởng Giao Nhanh Đúng Giờ!")
                gold_bonus += 25
            game.gold = getattr(game, "gold", 0) + gold_bonus
            if getattr(game, "state", None) is not None:
                game.state.daily_gold_earned += gold_bonus
                game.state.daily_orders_completed += 1
            if getattr(game, "audio", None) is not None:
                game.audio.play_sfx("gold")
            if getattr(game, "vfx", None) is not None:
                game.vfx.push_toast(
                    f"Hoàn Thành: {delivered_name}{star_lbl}",
                    f"+{pts}đ | +{gold_bonus}G Vàng | +1 Tim",
                    delivered_key,
                    (110, 245, 145),
                )
            game.completed_quests_count += 1
            completed_title = q.title
            q.status = "available"
            q.bonus_timer = q.bonus_time_limit
            game.quest_idx = (game.quest_idx + 1) % len(game.quests)
            new_hearts = 3
            if getattr(game, "dialogue", None) is not None:
                new_hearts = game.dialogue.adjust_friendship(npc.name, 100)
                game.dialogue.open_dialogue(
                    npc,
                    f"Hoàn Thành: {completed_title}",
                    f"Ôi cảm ơn FarmBot nhiều lắm! Món [{delivered_name}{star_lbl}] tươi ngon quá! Bạn đứng giao hàng đúng khoảng cách lịch sự và rất an toàn. Đây là {gold_bonus}G tiền thưởng cho bạn nhé!",
                    reward_badge=f"+{pts}đ | +{gold_bonus}G | {new_hearts}/5 ♥",
                    expression="love",
                )
            game.set_banner(
                f"HOÀN THÀNH [{completed_title}]! Nhận +{pts}đ, +{gold_bonus}G Vàng & +1 ♥ Thiện cảm với {npc.name}!",
                (110, 255, 145),
            )
            return

    # 2. Kiểm tra Nhận Nhiệm Vụ Mới (Accept Quest)
    if q.status == "available" and q.giver_name == npc.name:
        if q.category == "express" and len(game.robot.inventory) >= game.robot.max_inventory:
            game.set_banner("Khay đồ đã đầy, không thể nhận Kiện Hàng Chuyển Phát Nhanh!", (255, 175, 95))
            return
        q.status = "accepted"
        npc.handoff_timer = 1.2
        npc.trigger_emote("!", 2.5)
        game.add_score(SCORE_ACCEPT_QUEST, "Đứng đúng Quạt Xanh & Nhận việc!")
        if q.category == "express":
            game.robot.add_item(q.item_key)
        if q.bonus_time_limit > 0.0:
            q.bonus_timer = q.bonus_time_limit
        if getattr(game, "dialogue", None) is not None:
            new_hearts = game.dialogue.adjust_friendship(npc.name, 50)
            game.dialogue.open_dialogue(
                npc,
                f"Nhận Nhiệm Vụ — {q.title}",
                f"Chào FarmBot tốt bụng! Nhờ bạn giúp mình: {q.source_hint}. Sau đó mang [{q.item_label}] tới giao tận tay cho {q.receiver_name} tại {q.receiver_place} nhé!",
                reward_badge=f"+{SCORE_ACCEPT_QUEST}đ | Thiện cảm: {new_hearts}/5 ♥",
            )
        game.set_banner(
            f"ĐÃ NHẬN NHIỆM VỤ [{q.title}] từ {npc.name} (+20đ)! Xem hướng dẫn ở góc phải.",
            (135, 248, 165),
        )
        return

    # 3. Nếu người chơi nói chuyện với một NPC giao nhiệm vụ khác trong danh sách -> Tự chuyển sang nhiệm vụ của NPC đó!
    for idx, other_q in enumerate(game.quests):
        if other_q.status == "available" and other_q.giver_name == npc.name:
            game.quest_idx = idx
            other_q.status = "accepted"
            npc.handoff_timer = 1.2
            npc.trigger_emote("!", 2.5)
            game.add_score(SCORE_ACCEPT_QUEST, "Đứng đúng Quạt Xanh & Nhận việc!")
            if other_q.category == "express" and len(game.robot.inventory) < game.robot.max_inventory:
                game.robot.add_item(other_q.item_key)
            if other_q.bonus_time_limit > 0.0:
                other_q.bonus_timer = other_q.bonus_time_limit
            if getattr(game, "dialogue", None) is not None:
                new_hearts = game.dialogue.adjust_friendship(npc.name, 50)
                game.dialogue.open_dialogue(
                    npc,
                    f"Nhận Nhiệm Vụ — {other_q.title}",
                    f"Cảm ơn FarmBot đã ghé hỏi thăm! Nhờ bạn giúp mình: {other_q.source_hint}. Rồi mang [{other_q.item_label}] tới cho {other_q.receiver_name} tại {other_q.receiver_place} nhé!",
                    reward_badge=f"+{SCORE_ACCEPT_QUEST}đ | Thiện cảm: {new_hearts}/5 ♥",
                )
            game.set_banner(
                f"ĐÃ NHẬN NHIỆM VỤ [{other_q.title}] từ {npc.name} (+20đ)!",
                (135, 248, 165),
            )
            return

    # 4. Nhắc nhở nếu NPC đang chờ vật phẩm
    if q.status == "accepted" and q.receiver_name == npc.name:
        npc.trigger_emote("?", 2.0)
        if getattr(game, "dialogue", None) is not None:
            cur_h = game.dialogue.get_hearts(npc.name)
            game.dialogue.open_dialogue(
                npc,
                f"Đang Chờ Giao Hàng — {q.title}",
                f"Chào FarmBot! Mình đang chờ bạn mang [{ITEM_NAMES_VI[q.item_key]}] tới giao. Gợi ý: {q.source_hint}!",
                reward_badge=f"Thiện cảm: {cur_h}/5 ♥",
            )
        game.set_banner(
            f"{npc.name}: 'Mình đang chờ bạn mang [{ITEM_NAMES_VI[q.item_key]}] tới giao nhé!'",
            (255, 232, 135),
        )
        return

    npc.trigger_emote("♪", 2.0)
    if getattr(game, "audio", None) is not None:
        game.audio.play_sfx("heart")
    if getattr(game, "dialogue", None) is not None:
        new_hearts = game.dialogue.adjust_friendship(npc.name, 25)
        sched_txt = getattr(npc, "schedule_note", f"{npc.name} đang tận hưởng ngày mới")
        # Lấy lời thoại ngữ cảnh từ npcs.json theo mức tim và thời tiết
        ctx_line = f"Chào FarmBot! Cảm ơn bạn đã dừng lại trò chuyện đúng vùng quạt xanh lịch sự trước mặt mình. ({sched_txt})."
        if getattr(game, "state", None) is not None:
            npc_prof = game.state.npcs_db.get(npc.name, {})
            dlgs = npc_prof.get("dialogues", {})
            rumor = npc_prof.get("rumor", "")
            if getattr(getattr(game, "atmosphere", None), "current_weather", "") == "rain" and "rain" in dlgs:
                ctx_line = dlgs["rain"]
            elif new_hearts >= 4 and "high" in dlgs:
                ctx_line = dlgs["high"] + (f" [Bí mật: {rumor}]" if rumor else "")
            elif new_hearts >= 2 and "mid" in dlgs:
                ctx_line = dlgs["mid"]
            elif "low" in dlgs:
                ctx_line = dlgs["low"]
        extra_tip = (
            " Bấm [U] để mở Xưởng Nâng Cấp Robot hoặc [G] để tặng quà nhé!"
            if "Robin" in npc.name
            else " Bấm [G] nếu bạn muốn tặng nông sản cho mình nhé!"
        )
        game.dialogue.open_dialogue(
            npc,
            f"Trò Chuyện Thân Thiện — {npc.role}",
            ctx_line + extra_tip,
            reward_badge=f"Thiện cảm: {new_hearts}/5 ♥",
            expression="love" if new_hearts >= 4 else "happy",
        )
    game.set_banner(
        f"{npc.name} ({npc.role}): 'Cảm ơn Robot đã đứng nói chuyện lịch sự đúng khoảng cách nhé!'",
        (185, 242, 205),
    )
