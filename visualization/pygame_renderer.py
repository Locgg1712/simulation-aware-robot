# visualization/pygame_renderer.py
import math
import pygame
from environment.world import World
from objects.static_object import ShapeType
from objects.semi_static_object import SemiStaticState
from human.human_agent import HumanAgent, HumanActivity
from human.social_space import get_gaussian_ellipse_axes
from .stardew_sprites import StardewSpriteBank


class PygameRenderer:
    """
    Bộ hiển thị trực quan 2D Top-Down bằng Pygame.
    Hỗ trợ 4 Bản đồ Stardew Valley + Chế độ Vào Nhà (Indoor House Room làm tối vùng ngoài).
    """

    COLOR_BG = (245, 247, 250)
    COLOR_GRID_LINE = (225, 230, 238)
    COLOR_OCCUPIED_CELL = (210, 218, 230)
    COLOR_STATIC_RECT = (75, 85, 99)
    COLOR_STATIC_CIRCLE = (55, 65, 81)

    COLOR_DOOR_CLOSED = (220, 38, 38)
    COLOR_DOOR_TRANSITION = (245, 158, 11)
    COLOR_DOOR_OPEN = (16, 185, 129)

    COLOR_DYNAMIC_OBJ = (147, 51, 234)
    COLOR_PRED_TRAJ = (168, 85, 247)

    COLOR_HUMAN_STANDING = (14, 165, 233)
    COLOR_HUMAN_WALKING = (234, 88, 12)
    COLOR_HUMAN_RUNNING = (225, 29, 72)

    COLOR_PERSONAL_SPACE = (249, 115, 22)
    COLOR_OSPACE_INTERACT = (220, 38, 38)
    COLOR_OSPACE_GROUP = (20, 184, 166)

    COLOR_SUBGOAL = (245, 158, 11)
    COLOR_ROBOT = (37, 99, 235)
    COLOR_ROBOT_COLLISION = (220, 38, 38)
    COLOR_ROBOT_HEADING = (255, 255, 255)
    COLOR_GOAL = (16, 185, 129)
    COLOR_TRAJECTORY = (96, 165, 250)
    COLOR_LIDAR_RAY = (239, 68, 68)
    COLOR_HUD_BG = (48, 32, 20, 225)
    COLOR_HUD_BORDER = (218, 165, 92)
    COLOR_TEXT = (255, 248, 231)

    def __init__(self, world: World, config: dict):
        pygame.init()
        pygame.display.set_caption(
            "Context-Aware Robot Navigation - Stardew Valley 4 Maps & Indoor Edition"
        )

        vis_cfg = config["visualization"]
        self.window_size: int = int(vis_cfg["window_size"])
        self.fps: int = int(vis_cfg["fps"])
        self.world = world
        self.scale: float = self.window_size / self.world.width

        self.screen = pygame.display.set_mode((self.window_size, self.window_size))
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont("consolas", 14, bold=True)
        self.small_font = pygame.font.SysFont("consolas", 12, bold=True)

        self.stardew_mode: bool = True
        self.debug_mode: bool = False
        self.show_hud: bool = True
        self.paused: bool = False
        self.agent_mode: int = 3

        self.sprites = StardewSpriteBank(self.scale)
        self._cached_bg: pygame.Surface | None = None
        self._cached_bg_key: tuple | None = None

        self.last_reward: float = 0.0
        self.episode_reward: float = 0.0
        self.reward_breakdown: dict = {}
        self.state_dim: int = 106

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

    def _ensure_stardew_background(self):
        robot = self.world.robot
        if robot is None:
            return
        key = (
            self.world.current_topology_id,
            len(self.world.static_objects),
            round(robot.goal_x, 1),
            round(robot.goal_y, 1),
        )
        if self._cached_bg is None or self._cached_bg_key != key:
            start_pos = robot.trajectory[0] if robot.trajectory else (robot.x, robot.y)
            goal_pos = (robot.goal_x, robot.goal_y)
            self._cached_bg = self.sprites.build_background_surface(
                window_size=self.window_size,
                world_width=self.world.width,
                world_height=self.world.height,
                static_objects=self.world.static_objects,
                start_pos=start_pos,
                goal_pos=goal_pos,
                seed=self.world.current_topology_id * 137,
                topology_id=self.world.current_topology_id,
            )
            self._cached_bg_key = key

    def render(self):
        # 1. NẾU ROBOT ĐANG Ở TRONG NHÀ -> LÀM TỐI VÙNG NGOÀI & VẼ PHÒNG NỘI THẤT
        if getattr(self.world, "in_indoor_house", False):
            self.sprites.draw_indoor_room_environment(
                screen=self.screen,
                room_bounds=self.world.indoor_room_bounds,
                exit_portal=self.world.indoor_exit_portal,
                house_name=self.world.current_house_name,
                font=self.font,
            )
        else:
            if self.stardew_mode:
                self._ensure_stardew_background()
                if self._cached_bg is not None:
                    self.screen.blit(self._cached_bg, (0, 0))
                else:
                    self.screen.fill((110, 178, 75))
            else:
                self.screen.fill(self.COLOR_BG)

            if self.debug_mode and not self.stardew_mode:
                self._draw_occupancy_grid()

        self._draw_goal()
        self._draw_static_objects()
        self._draw_semi_static_objects()

        if self.debug_mode:
            self._draw_social_spaces()
            self._draw_astar_and_subgoal()

        self._draw_dynamic_objects()
        self._draw_humans()

        if self.debug_mode:
            self._draw_debug_overlays()

        self._draw_robot()
        if self.show_hud:
            self._draw_hud()

        pygame.display.flip()
        self.clock.tick(self.fps)

    def _draw_occupancy_grid(self):
        cell_px = self.meters_to_px(self.world.grid_res)
        for r in range(self.world.grid_rows):
            for c in range(self.world.grid_cols):
                if self.world.occupancy_grid[r, c] == 1:
                    sx = int(round(c * self.world.grid_res * self.scale))
                    sy = int(round(r * self.world.grid_res * self.scale))
                    pygame.draw.rect(
                        self.screen,
                        self.COLOR_OCCUPIED_CELL,
                        pygame.Rect(sx, sy, cell_px, cell_px),
                    )

    def _draw_astar_and_subgoal(self):
        robot = self.world.robot
        if robot is None:
            return
        if hasattr(self.world, "global_path") and len(self.world.global_path) >= 2:
            pts = [self.world_to_screen(px, py) for px, py in self.world.global_path]
            pygame.draw.lines(self.screen, (255, 235, 120), False, pts, 3)

        sgx, sgy = self.world_to_screen(robot.subgoal_x, robot.subgoal_y)
        rx, ry = self.world_to_screen(robot.x, robot.y)
        pygame.draw.line(self.screen, self.COLOR_SUBGOAL, (rx, ry), (sgx, sgy), 2)
        pygame.draw.circle(self.screen, self.COLOR_SUBGOAL, (sgx, sgy), 7)

    def _draw_static_objects(self):
        for obj in self.world.static_objects:
            if obj.shape == ShapeType.RECTANGLE:
                rx, ry, rw, rh = obj.bbox
                sx, sy = self.world_to_screen(rx, ry)
                sw = self.meters_to_px(rw)
                sh = self.meters_to_px(rh)
                if self.stardew_mode or getattr(self.world, "in_indoor_house", False):
                    self.sprites.draw_house_or_wall(
                        self.screen, sx, sy, sw, sh, obj.id, obj.name, self.small_font
                    )
                else:
                    pygame.draw.rect(
                        self.screen,
                        self.COLOR_STATIC_RECT,
                        pygame.Rect(sx, sy, sw, sh),
                        border_radius=2,
                    )
            elif obj.shape == ShapeType.CIRCLE:
                cx, cy = self.world_to_screen(obj.x, obj.y)
                rad_px = self.meters_to_px(obj.radius)
                if self.stardew_mode or getattr(self.world, "in_indoor_house", False):
                    self.sprites.draw_tree_sprite(
                        self.screen, cx, cy, rad_px, obj.id, obj.name
                    )
                else:
                    pygame.draw.circle(
                        self.screen, self.COLOR_STATIC_CIRCLE, (cx, cy), rad_px
                    )

    def _draw_semi_static_objects(self):
        for door in self.world.semi_static_objects:
            rx, ry, rw, rh = door.bbox
            sx, sy = self.world_to_screen(rx, ry)
            sw = self.meters_to_px(rw)
            sh = self.meters_to_px(rh)
            if door.state == SemiStaticState.CLOSED:
                pygame.draw.rect(self.screen, (135, 72, 32), (sx, sy, sw, sh), border_radius=3)
                pygame.draw.rect(self.screen, (220, 38, 38), (sx, sy, sw, sh), 2, border_radius=3)
            elif door.state in (SemiStaticState.OPENING, SemiStaticState.CLOSING):
                pygame.draw.rect(self.screen, (215, 145, 55), (sx, sy, sw, sh), border_radius=3)
            else:
                pygame.draw.rect(self.screen, (85, 225, 135), (sx, sy, sw, sh), 2, border_radius=3)

    def _draw_social_spaces(self):
        for grp in self.world.human_groups:
            cx, cy = self.world_to_screen(grp.center_x, grp.center_y)
            rad_px = self.meters_to_px(grp.radius)
            is_interact = grp.group_type.value == "INTERACTING"
            color = self.COLOR_OSPACE_INTERACT if is_interact else self.COLOR_OSPACE_GROUP
            surf = pygame.Surface((rad_px * 2 + 4, rad_px * 2 + 4), pygame.SRCALPHA)
            pygame.draw.circle(surf, (*color, 45), (rad_px + 2, rad_px + 2), rad_px)
            pygame.draw.circle(surf, (*color, 200), (rad_px + 2, rad_px + 2), rad_px, 2)
            self.screen.blit(surf, (cx - rad_px - 2, cy - rad_px - 2))

        for h in self.world.humans:
            poly_pts = self._build_asymmetric_gaussian_polygon(h, num_segments=28)
            if len(poly_pts) >= 3:
                pygame.draw.polygon(self.screen, self.COLOR_PERSONAL_SPACE, poly_pts, 1)

    def _build_asymmetric_gaussian_polygon(
        self, human: HumanAgent, num_segments: int = 28
    ) -> list[tuple[int, int]]:
        sigma_front, sigma_rear, sigma_side = get_gaussian_ellipse_axes(human)
        cos_t, sin_t = math.cos(human.theta), math.sin(human.theta)
        screen_pts: list[tuple[int, int]] = []
        for i in range(num_segments):
            phi = (2.0 * math.pi * i) / num_segments
            c_phi, s_phi = math.cos(phi), math.sin(phi)
            a = sigma_front if c_phi >= 0.0 else sigma_rear
            x_local, y_local = a * c_phi, sigma_side * s_phi
            wx = human.x + x_local * cos_t - y_local * sin_t
            wy = human.y + x_local * sin_t + y_local * cos_t
            screen_pts.append(self.world_to_screen(wx, wy))
        return screen_pts

    def _draw_dynamic_objects(self):
        for dyn in self.world.dynamic_objects:
            cx, cy = self.world_to_screen(dyn.x, dyn.y)
            rad_px = self.meters_to_px(dyn.radius)
            if self.stardew_mode:
                self.sprites.draw_agv_cart(self.screen, cx, cy, rad_px, dyn.theta)
            else:
                pygame.draw.circle(self.screen, self.COLOR_DYNAMIC_OBJ, (cx, cy), rad_px)

    def _draw_humans(self):
        for h in self.world.humans:
            cx, cy = self.world_to_screen(h.x, h.y)
            rad_px = self.meters_to_px(h.radius)
            if self.stardew_mode:
                self.sprites.draw_villager_npc(
                    self.screen,
                    cx,
                    cy,
                    rad_px,
                    h,
                    self.world.sim_time,
                    self.small_font,
                    debug_mode=self.debug_mode,
                )
            else:
                pygame.draw.circle(self.screen, self.COLOR_HUMAN_WALKING, (cx, cy), rad_px)

    def _draw_goal(self):
        robot = self.world.robot
        if robot is None:
            return
        gx, gy = self.world_to_screen(robot.goal_x, robot.goal_y)
        grad_px = self.meters_to_px(robot.goal_radius)
        if self.stardew_mode:
            self.sprites.draw_delivery_goal(self.screen, gx, gy, grad_px, self.world.sim_time)
        else:
            pygame.draw.circle(self.screen, self.COLOR_GOAL, (gx, gy), grad_px)

    def _draw_debug_overlays(self):
        robot = self.world.robot
        if robot is None:
            return
        rx, ry = self.world_to_screen(robot.x, robot.y)
        for hx, hy in self.world.lidar_hit_points:
            shx, shy = self.world_to_screen(hx, hy)
            pygame.draw.line(self.screen, self.COLOR_LIDAR_RAY, (rx, ry), (shx, shy), 1)

    def _draw_robot(self):
        robot = self.world.robot
        if robot is None:
            return
        rx, ry = self.world_to_screen(robot.x, robot.y)
        rad_px = self.meters_to_px(robot.radius)
        if self.stardew_mode:
            self.sprites.draw_robot_character(
                screen=self.screen,
                rx=rx,
                ry=ry,
                rad_px=rad_px,
                theta=robot.theta,
                speed=robot.v,
                sim_time=self.world.sim_time,
                is_collision=self.world.is_collision,
                carrying_item=not (self.world.is_goal_reached or self.world.indoor_delivered),
            )
        else:
            pygame.draw.circle(self.screen, self.COLOR_ROBOT, (rx, ry), rad_px)

    def _draw_hud(self):
        info = self.world.get_info()
        panel_w, panel_h = 525, 195
        panel = pygame.Surface((panel_w, panel_h), pygame.SRCALPHA)
        panel.fill(self.COLOR_HUD_BG)
        pygame.draw.rect(panel, self.COLOR_HUD_BORDER, (0, 0, panel_w, panel_h), 3, border_radius=8)
        self.screen.blit(panel, (12, 12))

        if info.get("in_indoor_house"):
            status_str = (
                "DELIVERED! WALK TO EXIT MAT OR PRESS [E]"
                if self.world.indoor_delivered
                else "INSIDE HOUSE: DELIVER PARCEL TO HOST!"
            )
            status_color = (255, 225, 105)
        elif info["is_goal_reached"]:
            status_str = "QUEST COMPLETE! (+100.0)"
            status_color = (255, 225, 85)
        elif info["is_collision"]:
            status_str = f"COLLISION ({info['collided_with']})"
            status_color = (255, 115, 115)
        else:
            status_str = "WALK TO HOUSE DOOR (RED MAT) OR PRESS [E] TO ENTER"
            status_color = (110, 235, 145)

        lines = [
            (f"QUEST : {status_str}", status_color),
            (f"SCENE : {info['topology']}", self.COLOR_TEXT),
            (f"ROBOT : x={info['robot_pos'][0]:.1f}m, y={info['robot_pos'][1]:.1f}m | Goal Dist={info['distance_to_goal']:.2f}m", self.COLOR_TEXT),
            (f"RL REW: Step={self.last_reward:+.2f} | Episode={self.episode_reward:+.2f}", (145, 210, 255)),
            ("KEYS  : [T] Switch 4 Maps | [E] Enter/Exit House | [D] Debug | [1-4] Mode", (255, 220, 140)),
            ("        [H] Hide HUD | [V] Theme | [R] Reset | [SPACE] Pause", (255, 220, 140)),
        ]

        for idx, (text, color) in enumerate(lines):
            surf = self.font.render(text, True, color)
            self.screen.blit(surf, (24, 20 + idx * 27))

    def close(self):
        pygame.quit()