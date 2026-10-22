# visualization/pygame_renderer.py
"""
Bộ hiển thị trực quan 2D Top-Down bằng Pygame – Pixel-Art Stardew Valley Edition.
Tích hợp toàn diện StardewSpriteEngine:
- Robot Automaton (Maru's Farm Helper) có xích cơ khí, mắt CRT nhấp nháy, ăng-ten chớp đèn.
- Dân làng / Nông dân (Villagers) đa dạng trang phục, mũ rơm, hoạt ảnh bước đi, bóng thoại emote.
- Xe goòng hầm mỏ (Minecart) chở khoáng thạch thạch anh tím & đèn bão lơ lửng.
- Thùng rượu sồi (Wine Barrels) và tường đá rêu phong (Cobblestone masonry).
- Vùng đích Đại Thần Điện (Grand Stardrop Shrine) với vòng hoa cổ tích, bệ đá rune, bụi sao lấp lánh.
- Bảng điều khiển HUD gỗ mộc mạc (Rustic Wood Signboard) nhỏ gọn, trang nhã.
"""

import math
import random
import pygame
from environment.world import World
from objects.static_object import ShapeType
from objects.semi_static_object import SemiStaticState
from human.human_agent import HumanAgent, HumanActivity, SocialContext
from human.social_space import get_gaussian_ellipse_axes
from visualization.stardew_sprites import StardewSpriteEngine, PALETTE


class PygameRenderer:
    """Bộ hiển thị trực quan 2D Top-Down phong cách Stardew Valley Pixel Art."""

    # Màu sắc hỗ trợ cho Debug Overlays
    COLOR_TRAJECTORY     = (100, 180, 240)
    COLOR_SENSOR_RANGE   = (120, 190, 240, 110)
    COLOR_LIDAR_RAY      = (240, 90, 80, 75)
    COLOR_LIDAR_HIT      = (255, 120, 95)
    COLOR_ASTAR_PATH     = (60, 130, 80)
    COLOR_SUBGOAL        = (255, 215, 50)
    COLOR_OSPACE_INTERACT= (210, 80, 80, 70)
    COLOR_OSPACE_GROUP   = (60, 175, 150, 70)
    COLOR_PERSONAL_SPACE = (235, 150, 60, 45)

    def __init__(self, world: World, config: dict):
        pygame.init()
        pygame.display.set_caption(
            "🌿 Context-Aware Robot Navigation – Stardew Valley Farm Edition 🌿"
        )

        vis_cfg = config.get("visualization", {})
        self.window_size: int = int(vis_cfg.get("window_size", 960))
        self.fps: int = int(vis_cfg.get("fps", 30))
        self.world = world
        self.scale: float = self.window_size / self.world.width

        self.screen = pygame.display.set_mode((self.window_size, self.window_size))
        self.clock = pygame.time.Clock()

        # Engine sinh Sprite Pixel Art phong cách Stardew Valley
        self.sprite_engine = StardewSpriteEngine(self.scale)

        # Phông chữ giao diện
        self.font = pygame.font.SysFont("consolas", 13, bold=True)
        self.small_font = pygame.font.SysFont("consolas", 11, bold=True)
        self.title_font = pygame.font.SysFont("consolas", 14, bold=True)

        self.debug_mode: bool = True
        self.paused: bool = False
        self.show_hud: bool = True
        self.agent_mode: int = 3

        # Thông tin Reward & State để hiển thị trên HUD
        self.last_reward: float = 0.0
        self.episode_reward: float = 0.0
        self.reward_breakdown: dict = {}
        self.state_dim: int = 106

        # Biến đếm frame hoạt ảnh
        self._frame_count: int = 0

    # ═══════════════════════════════════════════════════════════════════════
    #  PUBLIC API
    # ═══════════════════════════════════════════════════════════════════════

    def update_rl_telemetry(
        self, step_reward: float, episode_reward: float, breakdown: dict, state_dim: int = 106
    ):
        self.last_reward = float(step_reward)
        self.episode_reward = float(episode_reward)
        self.reward_breakdown = breakdown or {}
        self.state_dim = int(state_dim)

    def world_to_screen(self, x: float, y: float) -> tuple[int, int]:
        return int(round(x * self.scale)), int(round(y * self.scale))

    def meters_to_px(self, m: float) -> int:
        return max(1, int(round(m * self.scale)))

    def render(self):
        self._frame_count += 1

        # 1. Nền đồng cỏ hoa Stardew Valley
        self._draw_grass_meadow()

        # 2. Lưới ô cản mờ (khi bật Debug)
        if self.debug_mode:
            self._draw_occupancy_grid()

        # 3. Đường mòn A* & Subgoal
        if self.debug_mode:
            self._draw_astar_and_subgoal()

        # 4. Vùng đích Đền thờ Sao Vàng (Grand Goal Monument)
        self._draw_goal()

        # 5. Chướng ngại vật tĩnh (Tường đá & Thùng rượu)
        self._draw_static_objects()

        # 6. Cửa nông trại trượt (Barn Doors)
        self._draw_semi_static_objects()

        # 7. Không gian xã hội (O-Space & Personal Space)
        if self.debug_mode:
            self._draw_social_spaces()

        # 8. Xe goòng hầm mỏ động (Dynamic Minecarts)
        self._draw_dynamic_objects()

        # 9. Dân làng / Nông dân (Human NPCs)
        self._draw_humans()

        # 10. Lớp hiển thị cảm biến (LiDAR 16 tia, Vệt di chuyển)
        if self.debug_mode:
            self._draw_debug_overlays()

        # 11. Robot Automaton (Maru's Helper)
        self._draw_robot()

        # 12. Bảng điều khiển HUD gỗ mộc mạc
        if self.show_hud:
            self._draw_hud()

        pygame.display.flip()
        self.clock.tick(self.fps)

    # ═══════════════════════════════════════════════════════════════════════
    #  PHƯƠNG THỨC VẼ TỪNG THÀNH PHẦN
    # ═══════════════════════════════════════════════════════════════════════

    def _draw_grass_meadow(self):
        """Lát nền đồng cỏ Stardew với 8 biến thể hoa cúc vàng, hoa trắng, sỏi đá."""
        tile_size = 32
        cols = (self.window_size + tile_size - 1) // tile_size
        rows = (self.window_size + tile_size - 1) // tile_size

        for r in range(rows):
            for c in range(cols):
                # Băm vị trí để giữ hoa dại cố định trên bản đồ
                tile_id = (c * 7 + r * 13 + (c ^ r)) % 8
                tile_surf = self.sprite_engine.get_terrain_tile(tile_id)
                self.screen.blit(tile_surf, (c * tile_size, r * tile_size))

        # Viền nẹp gỗ hoặc hàng rào nông trại ở mép bản đồ (Boundary frame)
        pygame.draw.rect(self.screen, PALETTE["wood_dark"],
                         (0, 0, self.window_size, self.window_size), 3)

    def _draw_occupancy_grid(self):
        """Hiển thị lưới ô cản mờ nhẹ cho mục đích debug."""
        cell_px = self.meters_to_px(self.world.grid_res)
        for r in range(self.world.grid_rows):
            for c in range(self.world.grid_cols):
                if self.world.occupancy_grid[r, c] == 1:
                    sx = int(round(c * self.world.grid_res * self.scale))
                    sy = int(round(r * self.world.grid_res * self.scale))
                    cell_surf = pygame.Surface((cell_px, cell_px), pygame.SRCALPHA)
                    cell_surf.fill((120, 110, 95, 45))
                    self.screen.blit(cell_surf, (sx, sy))

    def _draw_astar_and_subgoal(self):
        """Vẽ đường mòn dã ngoại A* và viên kim cương vàng Sub-goal."""
        robot = self.world.robot
        if robot is None:
            return

        # Đường dẫn A* phong cách dấu chân mòn trên cỏ
        if len(self.world.global_path) >= 2:
            pts = self.world.global_path
            for i in range(len(pts) - 1):
                x1, y1 = self.world_to_screen(pts[i][0], pts[i][1])
                x2, y2 = self.world_to_screen(pts[i + 1][0], pts[i + 1][1])
                dx, dy = x2 - x1, y2 - y1
                dist = max(1, math.hypot(dx, dy))
                num_dots = max(1, int(dist / 8))
                for j in range(num_dots):
                    t = j / num_dots
                    dot_x = int(x1 + dx * t)
                    dot_y = int(y1 + dy * t)
                    pygame.draw.circle(self.screen, (160, 130, 80), (dot_x, dot_y), 3)
                    pygame.draw.circle(self.screen, (220, 195, 140), (dot_x, dot_y), 1)

        # Sub-goal: viên kim cương vàng Stardrop mini
        sgx, sgy = self.world_to_screen(robot.subgoal_x, robot.subgoal_y)
        rx, ry = self.world_to_screen(robot.x, robot.y)

        # Dây nối kim tuyến đứt đoạn tới Sub-goal
        dx, dy = sgx - rx, sgy - ry
        dist = max(1, math.hypot(dx, dy))
        num_dashes = max(1, int(dist / 10))
        for j in range(0, num_dashes, 2):
            t1 = j / num_dashes
            t2 = min(1.0, (j + 1) / num_dashes)
            pygame.draw.line(self.screen, (255, 215, 60),
                             (int(rx + dx * t1), int(ry + dy * t1)),
                             (int(rx + dx * t2), int(ry + dy * t2)), 2)

        # Kim cương Sub-goal
        d_sz = 8
        d_pts = [(sgx, sgy - d_sz), (sgx + d_sz, sgy),
                 (sgx, sgy + d_sz), (sgx - d_sz, sgy)]
        pygame.draw.polygon(self.screen, PALETTE["star_gold_mid"], d_pts)
        pygame.draw.polygon(self.screen, (255, 255, 220), [(sgx, sgy - d_sz + 2), (sgx + d_sz - 2, sgy),
                                                            (sgx, sgy + d_sz - 2), (sgx - d_sz + 2, sgy)])
        pygame.draw.polygon(self.screen, (160, 110, 20), d_pts, 2)

    def _draw_goal(self):
        """Vẽ Vùng đích Sao Vàng Thần Thoại khổng lồ."""
        robot = self.world.robot
        if robot is None:
            return
        gx, gy = self.world_to_screen(robot.goal_x, robot.goal_y)
        grad_px = self.meters_to_px(robot.goal_radius)
        self.sprite_engine.draw_grand_goal(self.screen, gx, gy, grad_px, self._frame_count)

    def _draw_static_objects(self):
        """Vẽ tường đá rêu phong và thùng rượu sồi."""
        for obj in self.world.static_objects:
            if obj.shape == ShapeType.RECTANGLE:
                rx, ry, rw, rh = obj.bbox
                sx, sy = self.world_to_screen(rx, ry)
                sw = self.meters_to_px(rw)
                sh = self.meters_to_px(rh)
                self.sprite_engine.draw_cobblestone_wall(self.screen, sx, sy, sw, sh)

            elif obj.shape == ShapeType.CIRCLE:
                cx, cy = self.world_to_screen(obj.x, obj.y)
                rad_px = self.meters_to_px(obj.radius)
                barrel_surf = self.sprite_engine.get_barrel_pillar_sprite(rad_px)
                self.screen.blit(barrel_surf,
                                 (cx - barrel_surf.get_width() // 2,
                                  cy - barrel_surf.get_height() // 2))

    def _draw_semi_static_objects(self):
        """Vẽ cửa nông trại trượt kiểu Stardew Valley."""
        for door in self.world.semi_static_objects:
            rx, ry, rw, rh = door.bbox
            sx, sy = self.world_to_screen(rx, ry)
            sw = self.meters_to_px(rw)
            sh = self.meters_to_px(rh)
            self.sprite_engine.draw_barn_door(self.screen, sx, sy, sw, sh, door.state.value)

            if self.debug_mode:
                state_text = f"DOOR:{door.state.value}"
                lbl = self.small_font.render(state_text, True, PALETTE["hud_text_parchment"])
                lbl_bg = pygame.Surface((lbl.get_width() + 6, lbl.get_height() + 2), pygame.SRCALPHA)
                lbl_bg.fill((45, 30, 20, 180))
                self.screen.blit(lbl_bg, (sx + 2, sy - 14))
                self.screen.blit(lbl, (sx + 5, sy - 13))

    def _draw_social_spaces(self):
        """Vẽ vòng tròn tương tác nhóm (O-Space) & không gian cá nhân kiểu ấm cúng."""
        for grp in self.world.human_groups:
            cx, cy = self.world_to_screen(grp.center_x, grp.center_y)
            rad_px = self.meters_to_px(grp.radius)
            is_interact = grp.group_type.value == "INTERACTING"
            color = self.COLOR_OSPACE_INTERACT if is_interact else self.COLOR_OSPACE_GROUP

            surf = pygame.Surface((rad_px * 2 + 6, rad_px * 2 + 6), pygame.SRCALPHA)
            pygame.draw.circle(surf, color, (rad_px + 3, rad_px + 3), rad_px)

            # Viền đứt nét duyên dáng
            num_dashes = 28
            for i in range(0, num_dashes, 2):
                a1 = 2 * math.pi * i / num_dashes
                a2 = 2 * math.pi * (i + 1) / num_dashes
                p1 = (rad_px + 3 + int(rad_px * math.cos(a1)),
                      rad_px + 3 + int(rad_px * math.sin(a1)))
                p2 = (rad_px + 3 + int(rad_px * math.cos(a2)),
                      rad_px + 3 + int(rad_px * math.sin(a2)))
                pygame.draw.line(surf, (*color[:3], 180), p1, p2, 2)

            self.screen.blit(surf, (cx - rad_px - 3, cy - rad_px - 3))

            # Đường kết nối giữa các thành viên đang nói chuyện
            if is_interact and len(grp.members) >= 2:
                pts = [self.world_to_screen(m.x, m.y) for m in grp.members]
                pygame.draw.lines(self.screen, color[:3], True, pts, 1)

        # Không gian cá nhân Asymmetric Gaussian
        for h in self.world.humans:
            poly_pts = self._build_asymmetric_gaussian_polygon(h, num_segments=28)
            if len(poly_pts) >= 3:
                ps_surf = pygame.Surface((self.window_size, self.window_size), pygame.SRCALPHA)
                pygame.draw.polygon(ps_surf, self.COLOR_PERSONAL_SPACE, poly_pts)
                pygame.draw.polygon(ps_surf, (220, 140, 50, 110), poly_pts, 1)
                self.screen.blit(ps_surf, (0, 0))

    def _build_asymmetric_gaussian_polygon(
        self, human: HumanAgent, num_segments: int = 28
    ) -> list[tuple[int, int]]:
        sigma_front, sigma_rear, sigma_side = get_gaussian_ellipse_axes(human)
        cos_t = math.cos(human.theta)
        sin_t = math.sin(human.theta)

        screen_pts: list[tuple[int, int]] = []
        for i in range(num_segments):
            phi = (2.0 * math.pi * i) / num_segments
            c_phi = math.cos(phi)
            s_phi = math.sin(phi)
            a = sigma_front if c_phi >= 0.0 else sigma_rear
            x_local = a * c_phi
            y_local = sigma_side * s_phi

            wx = human.x + x_local * cos_t - y_local * sin_t
            wy = human.y + x_local * sin_t + y_local * cos_t
            screen_pts.append(self.world_to_screen(wx, wy))
        return screen_pts

    def _draw_dynamic_objects(self):
        """Vẽ xe goòng mỏ chở ngọc Stardew Valley (Minecarts)."""
        for dyn in self.world.dynamic_objects:
            cx, cy = self.world_to_screen(dyn.x, dyn.y)
            rad_px = self.meters_to_px(dyn.radius)
            cart_surf = self.sprite_engine.get_minecart_sprite(rad_px, dyn.theta, self._frame_count)
            self.screen.blit(cart_surf, (cx - cart_surf.get_width() // 2,
                                         cy - cart_surf.get_height() // 2))

            if self.debug_mode:
                pred_pts = dyn.predict_trajectory(
                    dt=self.world.dt, horizon_sec=2.4, step_stride=4
                )
                for idx, (px, py) in enumerate(pred_pts):
                    spx, spy = self.world_to_screen(px, py)
                    alpha = max(60, 180 - idx * 25)
                    dot_surf = pygame.Surface((8, 8), pygame.SRCALPHA)
                    pygame.draw.circle(dot_surf, (190, 100, 240, alpha), (4, 4), 3)
                    self.screen.blit(dot_surf, (spx - 4, spy - 4))

    def _draw_humans(self):
        """Vẽ dân làng / nông dân Stardew Valley chân thực."""
        for h in self.world.humans:
            cx, cy = self.world_to_screen(h.x, h.y)
            rad_px = self.meters_to_px(h.radius)

            # Xác định xem người này có đang nói chuyện hay không
            is_talking = (h.social_context in (SocialContext.INTERACTING, SocialContext.CROSSING)) or (
                h.activity == HumanActivity.STANDING and any(
                    h in g.members for g in self.world.human_groups if g.group_type.value == "INTERACTING"
                )
            )

            h_surf = self.sprite_engine.get_human_sprite(
                radius_px=rad_px,
                theta=h.theta,
                speed=h.speed,
                activity_str=h.activity.value,
                human_id=h.id,
                frame_count=self._frame_count,
                is_talking=is_talking,
            )
            self.screen.blit(h_surf, (cx - h_surf.get_width() // 2,
                                      cy - h_surf.get_height() // 2))

            # Hiển thị vệt dự đoán di chuyển khi debug
            if self.debug_mode and h.activity != HumanActivity.STANDING:
                for idx, (px, py) in enumerate(h.predict_trajectory(
                    dt=self.world.dt, horizon_sec=2.5, step_stride=4
                )):
                    spx, spy = self.world_to_screen(px, py)
                    dot_col = (230, 140, 50) if h.activity == HumanActivity.WALKING else (230, 60, 80)
                    alpha = max(50, 160 - idx * 22)
                    dot_surf = pygame.Surface((6, 6), pygame.SRCALPHA)
                    pygame.draw.circle(dot_surf, (*dot_col, alpha), (3, 3), 2)
                    self.screen.blit(dot_surf, (spx - 3, spy - 3))

    def _draw_debug_overlays(self):
        """Vẽ 16 tia LiDAR phát quang mềm mại và vệt di chuyển robot."""
        robot = self.world.robot
        if robot is None:
            return
        rx, ry = self.world_to_screen(robot.x, robot.y)
        sensor_px = self.meters_to_px(robot.sensor_radius)

        # Vòng quét cảm biến mỏng nét cổ tích
        num_dashes = 40
        for i in range(0, num_dashes, 2):
            a1 = 2 * math.pi * i / num_dashes
            a2 = 2 * math.pi * (i + 1) / num_dashes
            p1 = (rx + int(sensor_px * math.cos(a1)), ry + int(sensor_px * math.sin(a1)))
            p2 = (rx + int(sensor_px * math.cos(a2)), ry + int(sensor_px * math.sin(a2)))
            pygame.draw.line(self.screen, (100, 175, 230), p1, p2, 1)

        # 16 tia quét LiDAR dịu mắt (Translucent Laser Ray)
        lidar_surf = pygame.Surface((self.window_size, self.window_size), pygame.SRCALPHA)
        for hx, hy in self.world.lidar_hit_points:
            shx, shy = self.world_to_screen(hx, hy)
            pygame.draw.line(lidar_surf, (240, 80, 70, 70), (rx, ry), (shx, shy), 1)
            # Điểm va chạm phát sáng
            pygame.draw.circle(lidar_surf, (255, 130, 100, 200), (shx, shy), 3)
            pygame.draw.circle(lidar_surf, (255, 255, 230, 240), (shx, shy), 1)
        self.screen.blit(lidar_surf, (0, 0))

        # Dấu vết di chuyển robot (Stardust Trail)
        if len(robot.trajectory) >= 2:
            pts = [self.world_to_screen(px, py) for px, py in robot.trajectory]
            for i, (px, py) in enumerate(pts):
                alpha = min(180, 40 + i * 2)
                trail_surf = pygame.Surface((6, 6), pygame.SRCALPHA)
                pygame.draw.circle(trail_surf, (*self.COLOR_TRAJECTORY, alpha), (3, 3), 2)
                self.screen.blit(trail_surf, (px - 3, py - 3))

    def _draw_robot(self):
        """Vẽ Robot Automaton (Maru's Steampunk Farm Helper) đầy đủ chi tiết."""
        robot = self.world.robot
        if robot is None:
            return
        rx, ry = self.world_to_screen(robot.x, robot.y)
        rad_px = self.meters_to_px(robot.radius)

        bot_surf = self.sprite_engine.get_robot_sprite(
            radius_px=rad_px,
            theta=robot.theta,
            frame_count=self._frame_count,
            is_collision=self.world.is_collision,
        )
        self.screen.blit(bot_surf, (rx - bot_surf.get_width() // 2,
                                    ry - bot_surf.get_height() // 2))

    def _draw_hud(self):
        """Vẽ Bảng thông số HUD gỗ mộc mạc nhỏ gọn phong cách nhật ký Stardew Valley."""
        info = self.world.get_info()
        soc = info["social_status"]

        # Kích thước nhỏ gọn, đặt góc trên để không che bản đồ
        panel_w, panel_h = 440, 195
        panel_x, panel_y = 12, 12

        # Bảng gỗ óc chó đậm với vân gỗ
        panel = pygame.Surface((panel_w, panel_h), pygame.SRCALPHA)
        panel.fill((45, 28, 16, 235))

        # Vân gỗ nhẹ
        rng = random.Random(42)
        for y in range(0, panel_h, 4):
            val = rng.randint(8, 26)
            pygame.draw.line(panel, (85, 55, 30, val), (0, y), (panel_w, y), 1)
        self.screen.blit(panel, (panel_x, panel_y))

        # Khung viền gỗ 3 lớp (3-tier rustic frame)
        outer = pygame.Rect(panel_x, panel_y, panel_w, panel_h)
        pygame.draw.rect(self.screen, (32, 18, 10), outer, 3)
        inner = outer.inflate(-4, -4)
        pygame.draw.rect(self.screen, (135, 92, 50), inner, 2)
        innermost = inner.inflate(-4, -4)
        pygame.draw.rect(self.screen, (185, 138, 78), innermost, 1)

        # 4 đinh tán mạ đồng 4 góc
        for cx_nail, cy_nail in [(panel_x + 6, panel_y + 6),
                                 (panel_x + panel_w - 7, panel_y + 6),
                                 (panel_x + 6, panel_y + panel_h - 7),
                                 (panel_x + panel_w - 7, panel_y + panel_h - 7)]:
            pygame.draw.circle(self.screen, (220, 185, 60), (cx_nail, cy_nail), 3)
            pygame.draw.circle(self.screen, (50, 30, 15), (cx_nail, cy_nail), 3, 1)

        mode_names = {
            1: "Manual (Keyboard)",
            2: "B1: A* + Basic",
            3: "B2: A* + Social",
            4: "B4: RL Policy",
        }

        # Trạng thái
        status_str = "RUNNING"
        status_color = (100, 230, 140)
        if self.paused:
            status_str = "PAUSED"
            status_color = (255, 215, 60)
        if info["is_collision"]:
            status_str = f"COLLISION ({info['collided_with']})"
            status_color = (255, 95, 95)
        elif info["is_goal_reached"]:
            status_str = "★ GOAL REACHED (+100) ★"
            status_color = (255, 235, 80)

        # Vi phạm xã hội
        social_alert = "SAFE"
        social_color = (100, 230, 140)
        if soc["group_splitting"] or soc["ospace_intrusion"]:
            social_alert = f"O-SPACE INTRUSION ({soc['group_penalty']})"
            social_color = (255, 95, 95)
        elif soc["personal_intrusion"]:
            social_alert = f"PERSONAL INTRUSION ({soc['social_penalty']})"
            social_color = (255, 210, 60)

        rb = self.reward_breakdown
        rew_detail = (
            f"R={self.last_reward:+.2f} Ep={self.episode_reward:+.1f} "
            f"(p:{rb.get('r_progress', 0.0):+.2f} w:{rb.get('r_context', 0.0):+.1f})"
        )
        rew_color = (100, 230, 140) if self.last_reward >= 0.0 else (255, 210, 60)

        lines = [
            (f"STATUS   {status_str}", status_color),
            (f"MAP      {info['topology']}", (245, 230, 190)),
            (f"AGENT    {mode_names.get(self.agent_mode, 'Social')}", (130, 190, 255)),
            (f"TIME     {info['sim_time']:.1f}s (Step {info['step']}) | d_goal={info['distance_to_goal']:.2f}m", (245, 230, 190)),
            (f"SOCIAL   {social_alert}", social_color),
            (f"REWARD   {rew_detail}", rew_color),
            (f"VEL      v={info['robot_v']:.2f}m/s ω={info['robot_omega']:.2f} | Dbg:{'ON' if self.debug_mode else 'OFF'}", (220, 210, 180)),
            ("KEYS     [1-4]Mode [D]Dbg [H]HUD [T]Topo [R]Reset", (180, 160, 130)),
        ]

        text_x = panel_x + 14
        text_y = panel_y + 12
        for idx, (text, color) in enumerate(lines):
            # Bóng chữ đen cổ điển
            shadow = self.font.render(text, True, (20, 12, 6))
            self.screen.blit(shadow, (text_x + 1, text_y + idx * 21 + 1))
            # Chữ chính
            surf = self.font.render(text, True, color)
            self.screen.blit(surf, (text_x, text_y + idx * 21))

    def close(self):
        pygame.quit()