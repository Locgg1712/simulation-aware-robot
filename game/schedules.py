# game/schedules.py
"""
Hệ thống Bản Đồ Thu Nhỏ (Minimap Radar) & Lịch Sinh Hoạt Cư Dân Theo Giờ (Daily NPC Schedules):
- Mục 8.1: Bản đồ thu nhỏ Radar hiển thị địa hình, cổng chuyển vùng, điểm nông sản chín,
  vị trí và hướng di chuyển của Robot, cùng các NPC (chấm nhấp nháy cho NPC nhiệm vụ).
- Mục 8.6: Lịch sinh hoạt cư dân theo 3 khung giờ chuẩn Stardew Valley:
  + 07:00 - 11:30: Sáng Sớm — Chăm Vườn & Chợ Sớm (v = 64.0 px/s).
  + 11:30 - 17:00: Giữa Trưa — Dạo Phố & Câu Cá (v = 54.0 px/s).
  + 17:00 - 22:00: Chiều Tối — Hóng Gió & Sum Họp (v = 45.0 px/s).
"""

from __future__ import annotations

import math
from typing import TYPE_CHECKING
import pygame

from .constants import SCREEN_H, SCREEN_W

if TYPE_CHECKING:
    from .entities import VillagerNPC


class MinimapAndScheduleSystem:
    """
    Bộ quản lý tích hợp Radar Minimap và Lịch trình Sinh hoạt Cư dân theo thời gian.
    """

    def __init__(self) -> None:
        self.show_minimap: bool = True
        self._cached_map_id: int = -1
        self._cached_mini_terrain: pygame.Surface | None = None
        self.current_period_name: str = "Buổi Sáng (07:00 - 11:30)"
        self.current_period_title: str = "Sáng Sớm — Chăm Vườn & Chợ Sớm"
        self.current_time_str: str = "07:00"
        self._internal_font: pygame.font.Font | None = None

    def _get_font(self, game=None) -> pygame.font.Font:
        """Lấy font chữ nhỏ cho tiêu đề Minimap, ưu tiên font có sẵn của game."""
        if game is not None and getattr(game, "font_xs", None) is not None:
            return game.font_xs
        if self._internal_font is None:
            self._internal_font = pygame.font.SysFont("Segoe UI", 11, bold=True)
        return self._internal_font

    def toggle_minimap(self) -> bool:
        """Bật / tắt trạng thái hiển thị Minimap khi người chơi bấm phím [M]."""
        self.show_minimap = not self.show_minimap
        return self.show_minimap

    def handle_event(self, event: pygame.event.Event) -> bool:
        """
        Xử lý sự kiện phím tắt [M] để bật/tắt Minimap.
        Trả về True nếu sự kiện được tiêu thụ.
        """
        if event.type == pygame.KEYDOWN and event.key == pygame.K_m:
            self.toggle_minimap()
            return True
        return False

    def get_time_info(self, sim_time: float) -> tuple[float, str, str, float]:
        """
        Tính toán giờ hiện tại trong game từ sim_time.
        Chu kỳ 15 giờ trong ngày (07:00 -> 22:00), mỗi ngày game kéo dài 225 giây thực tế.
        
        Trả về:
            (hour_float, time_str, period_name, target_npc_speed)
        """
        hour = 7.0 + ((sim_time * 4.0) % (15.0 * 60.0)) / 60.0
        h = int(hour)
        m = int((hour - h) * 60.0)
        time_str = f"{h:02d}:{m:02d}"

        if hour < 11.5:
            period_title = "Sáng Sớm — Chăm Vườn & Chợ Sớm"
            period_name = f"{period_title} (07:00 - 11:30)"
            target_speed = 64.0
        elif hour < 17.0:
            period_title = "Giữa Trưa — Dạo Phố & Câu Cá"
            period_name = f"{period_title} (11:30 - 17:00)"
            target_speed = 54.0
        else:
            period_title = "Chiều Tối — Hóng Gió & Sum Họp"
            period_name = f"{period_title} (17:00 - 22:00)"
            target_speed = 45.0

        return hour, time_str, period_name, target_speed

    def update_schedules(self, game, dt: float) -> None:
        """
        Cập nhật lịch trình sinh hoạt cư dân theo giờ trong ngày.
        - Điều chỉnh tốc độ tuần tra của NPC phù hợp với nhịp sinh hoạt.
        - Cập nhật mô tả hoạt động `npc.schedule_note` cho từng nhân vật.
        """
        sim_time = getattr(game, "sim_time", 0.0)
        hour, time_str, period_name, target_speed = self.get_time_info(sim_time)
        self.current_period_name = period_name
        self.current_time_str = time_str

        npcs: list[VillagerNPC] = getattr(game, "npcs", [])
        for npc in npcs:
            # Điều chỉnh vận tốc tuần tra cho các NPC di chuyển
            if not getattr(npc, "is_stationary", False):
                npc.base_speed = target_speed

            # Cập nhật ghi chú lịch trình sinh hoạt theo nghề nghiệp và khung giờ
            role = getattr(npc, "role", "").lower()
            name = getattr(npc, "name", "Cư dân")

            if hour < 11.5:
                if "nông" in role or "vườn" in role:
                    npc.schedule_note = f"{name}: Chăm sóc cây trồng & thu hoạch sớm"
                elif "thương" in role or "tiệm" in role or "bán" in role:
                    npc.schedule_note = f"{name}: Mở sạp chợ sớm & nhập nông sản"
                else:
                    npc.schedule_note = f"{name}: Đi dạo chợ sớm & hít thở sớm mai"
            elif hour < 17.0:
                if "cá" in role or "thủy" in role:
                    npc.schedule_note = f"{name}: Buông cần câu cá bên bờ hồ"
                elif "bếp" in role or "quán" in role:
                    npc.schedule_note = f"{name}: Chuẩn bị món ăn trưa & giải khát"
                else:
                    npc.schedule_note = f"{name}: Dạo phố, trò chuyện & dạo mát"
            else:
                if "già" in role or "trưởng" in role:
                    npc.schedule_note = f"{name}: Hóng gió hoàng hôn & kể chuyện xóm"
                else:
                    npc.schedule_note = f"{name}: Dạo mát chiều tối & sum họp gia đình"

    def render_minimap(self, screen: pygame.Surface, game, top_y: int = 128) -> None:
        """
        Vẽ bản đồ thu nhỏ Minimap Radar ở góc trái màn hình.
        - Kích thước: mw=148, mh=100 tại (10, top_y).
        - Hiển thị địa hình thu nhỏ mượt mà với bộ nhớ đệm (cache).
        - Hiển thị cổng chuyển vùng, điểm nông sản chín, NPC và Robot.
        """
        # Không vẽ khi người chơi tắt minimap hoặc đang trong không gian nội thất Map 5
        if not self.show_minimap or getattr(game, "in_interior", False):
            return

        mw, mh = 148, 100
        rect = pygame.Rect(10, top_y, mw, mh)

        inner_w = mw - 8   # 140
        inner_h = mh - 22  # 78
        inner_x = rect.x + 4
        inner_y = rect.y + 18
        inner_rect = pygame.Rect(inner_x, inner_y, inner_w, inner_h)

        # 1. Cập nhật bản đồ địa hình thu nhỏ vào cache khi đổi Map
        current_map_id = getattr(game, "current_map_id", 0)
        terrain_surface = getattr(game, "terrain_surface", None)
        if terrain_surface is not None and self._cached_map_id != current_map_id:
            try:
                self._cached_mini_terrain = pygame.transform.smoothscale(
                    terrain_surface, (inner_w, inner_h)
                )
                self._cached_map_id = current_map_id
            except Exception:
                self._cached_mini_terrain = None

        # 2. Vẽ khung gỗ viền vàng bóng bẩy
        # Đổ bóng tối phía sau
        shadow_rect = rect.move(2, 2)
        shadow_surf = pygame.Surface((mw, mh), pygame.SRCALPHA)
        pygame.draw.rect(shadow_surf, (10, 8, 6, 120), (0, 0, mw, mh), border_radius=6)
        screen.blit(shadow_surf, shadow_rect.topleft)

        # Nền khung gỗ chính
        wood_bg = pygame.Surface((mw, mh), pygame.SRCALPHA)
        pygame.draw.rect(wood_bg, (40, 26, 16, 238), (0, 0, mw, mh), border_radius=6)
        screen.blit(wood_bg, rect.topleft)

        # Thanh tiêu đề trên cùng
        header_bar = pygame.Rect(rect.x + 2, rect.y + 2, mw - 4, 16)
        pygame.draw.rect(
            screen, (52, 34, 22), header_bar, border_top_left_radius=5, border_top_right_radius=5
        )

        # Viền kim loại vàng hoàng gia
        pygame.draw.rect(screen, (228, 182, 54), rect, width=2, border_radius=6)
        pygame.draw.rect(screen, (84, 56, 30), rect.inflate(-2, -2), width=1, border_radius=5)

        # Tiêu đề và giờ hiển thị
        font = self._get_font(game)
        title_surf = font.render("Radar [M]", True, (255, 235, 120))
        time_surf = font.render(self.current_time_str, True, (215, 240, 255))
        screen.blit(title_surf, (rect.x + 8, rect.y + 3))
        screen.blit(time_surf, (rect.right - time_surf.get_width() - 8, rect.y + 3))

        # 3. Vẽ vùng hiển thị bản đồ thu nhỏ bên trong
        if self._cached_mini_terrain is not None:
            screen.blit(self._cached_mini_terrain, (inner_x, inner_y))
        else:
            pygame.draw.rect(screen, (34, 48, 30), inner_rect)

        # Khung viền mỏng quanh lòng bản đồ
        pygame.draw.rect(screen, (74, 52, 32), inner_rect, width=1)

        # Tỷ lệ co giãn tọa độ từ thế giới sang Minimap
        sx = float(inner_w) / float(SCREEN_W)
        sy = float(inner_h) / float(SCREEN_H)

        def to_mini(wx: float, wy: float) -> tuple[int, int]:
            """Chuyển đổi tọa độ thế giới sang tọa độ pixel trên Minimap, giới hạn trong lòng khung."""
            mx = int(round(inner_x + wx * sx))
            my = int(round(inner_y + wy * sy))
            mx = max(inner_x + 1, min(inner_x + inner_w - 2, mx))
            my = max(inner_y + 1, min(inner_y + inner_h - 2, my))
            return mx, my

        # A. Vẽ Cổng Chuyển Vùng (Portals) bằng vạch / khối màu vàng cam
        portals = getattr(game, "portals", [])
        for portal in portals:
            prect = getattr(portal, "rect", None)
            if prect is not None:
                px = inner_x + prect.x * sx
                py = inner_y + prect.y * sy
                pw = max(3.0, prect.width * sx)
                ph = max(3.0, prect.height * sy)
                p_box = pygame.Rect(int(px), int(py), int(pw), int(ph)).clamp(inner_rect)
                pygame.draw.rect(screen, (255, 170, 42), p_box)
                pygame.draw.rect(screen, (130, 70, 15), p_box, width=1)

        # B. Vẽ Điểm Thu Hoạch đang có nông sản/trái cây chín (chấm xanh lá r=2)
        harvest_spots = getattr(game, "harvest_spots", [])
        for spot in harvest_spots:
            if getattr(spot, "has_produce", False):
                hx, hy = to_mini(spot.x, spot.y)
                pygame.draw.circle(screen, (90, 235, 110), (hx, hy), 2)

        # C. Xác định NPC mục tiêu của nhiệm vụ đang kích hoạt
        active_quest = getattr(game, "active_quest", None)
        giver_target: str | None = None
        receiver_target: str | None = None
        if active_quest is not None:
            q_status = getattr(active_quest, "status", "")
            if q_status == "available":
                giver_target = getattr(active_quest, "giver_name", None)
            elif q_status == "accepted":
                receiver_target = getattr(active_quest, "receiver_name", None)

        sim_time = getattr(game, "sim_time", 0.0)
        flash_state = int(sim_time * 6.0) % 2 == 0

        # D. Vẽ các NPC
        npcs = getattr(game, "npcs", [])
        for npc in npcs:
            nx, ny = to_mini(npc.x, npc.y)
            is_giver = giver_target is not None and npc.name == giver_target
            is_receiver = receiver_target is not None and npc.name == receiver_target

            if is_giver or is_receiver:
                # Chấm lớn nhấp nháy cho NPC liên quan đến nhiệm vụ
                if is_giver:
                    col = (255, 230, 55) if flash_state else (230, 160, 25)
                else:
                    col = (80, 255, 140) if flash_state else (40, 190, 230)

                # Vòng hào quang ngoài và nhân sáng bên trong
                pygame.draw.circle(screen, (20, 20, 20), (nx, ny), 5)
                pygame.draw.circle(screen, col, (nx, ny), 4)
                pygame.draw.circle(screen, (255, 255, 255), (nx, ny), 1)
            else:
                # NPC bình thường: chấm trắng cam r=3
                pygame.draw.circle(screen, (50, 25, 15), (nx, ny), 4)
                pygame.draw.circle(screen, (255, 175, 120), (nx, ny), 3)

        # E. Vẽ Vị trí & Hướng Mặt của Robot (chấm xanh dương sáng r=4 kèm vạch hướng theta)
        robot = getattr(game, "robot", None)
        if robot is not None:
            rx, ry = to_mini(robot.x, robot.y)
            theta = getattr(robot, "theta", 0.0)

            # Vạch chỉ hướng
            dir_len = 6.5
            lx = int(round(rx + math.cos(theta) * dir_len))
            ly = int(round(ry + math.sin(theta) * dir_len))
            lx = max(inner_x + 1, min(inner_x + inner_w - 2, lx))
            ly = max(inner_y + 1, min(inner_y + inner_h - 2, ly))

            pygame.draw.line(screen, (255, 255, 255), (rx, ry), (lx, ly), 2)

            # Chấm tròn Robot nổi bật
            pygame.draw.circle(screen, (10, 28, 54), (rx, ry), 5)
            pygame.draw.circle(screen, (75, 235, 255), (rx, ry), 4)
            pygame.draw.circle(screen, (255, 255, 255), (rx, ry), 1)
