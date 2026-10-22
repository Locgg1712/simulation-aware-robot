# visualization/pygame_renderer.py
import math
import pygame
from environment.world import World
from objects.static_object import ShapeType
from objects.semi_static_object import SemiStaticState
from human.human_agent import HumanAgent, HumanActivity, SocialContext
from human.social_space import get_gaussian_ellipse_axes


class PygameRenderer:
    """
    Bộ hiển thị trực quan 2D Top-Down bằng Pygame (Phase 5).
    Hiển thị đầy đủ Global A* Path, Sliding Local Sub-goal, Social Space, O-Space,
    Raycast 16 tia và thông số Reward thời gian thực.
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

    COLOR_ASTAR_PATH = (5, 150, 105)
    COLOR_SUBGOAL = (245, 158, 11)

    COLOR_ROBOT = (37, 99, 235)
    COLOR_ROBOT_COLLISION = (220, 38, 38)
    COLOR_ROBOT_HEADING = (255, 255, 255)
    COLOR_GOAL = (16, 185, 129)
    COLOR_TRAJECTORY = (96, 165, 250)
    COLOR_SENSOR_RANGE = (59, 130, 246)
    COLOR_LIDAR_RAY = (239, 68, 68)
    COLOR_HUD_BG = (17, 24, 39, 222)
    COLOR_TEXT = (249, 250, 251)

    def __init__(self, world: World, config: dict):
        pygame.init()
        pygame.display.set_caption(
            "Context-Aware Robot Navigation Simulation - Phase 5 (Gymnasium, 106-D State & Reward)"
        )

        vis_cfg = config["visualization"]
        self.window_size: int = int(vis_cfg["window_size"])
        self.fps: int = int(vis_cfg["fps"])
        self.world = world
        self.scale: float = self.window_size / self.world.width

        self.screen = pygame.display.set_mode((self.window_size, self.window_size))
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont("consolas", 14)
        self.small_font = pygame.font.SysFont("consolas", 12)

        self.debug_mode: bool = True
        self.paused: bool = False
        self.agent_mode: int = 3

        # Thông tin Reward & State để hiển thị trên HUD
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

    def render(self):
        self.screen.fill(self.COLOR_BG)
        if self.debug_mode:
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
        step_px = self.meters_to_px(1.0)
        for pos in range(0, self.window_size, step_px):
            pygame.draw.line(
                self.screen, self.COLOR_GRID_LINE, (pos, 0), (pos, self.window_size), 1
            )
            pygame.draw.line(
                self.screen, self.COLOR_GRID_LINE, (0, pos), (self.window_size, pos), 1
            )

    def _draw_astar_and_subgoal(self):
        robot = self.world.robot
        if robot is None:
            return

        if len(self.world.global_path) >= 2:
            pts = [self.world_to_screen(px, py) for px, py in self.world.global_path]
            pygame.draw.lines(self.screen, self.COLOR_ASTAR_PATH, False, pts, 3)

        sgx, sgy = self.world_to_screen(robot.subgoal_x, robot.subgoal_y)
        rx, ry = self.world_to_screen(robot.x, robot.y)
        pygame.draw.line(self.screen, self.COLOR_SUBGOAL, (rx, ry), (sgx, sgy), 2)
        pygame.draw.circle(self.screen, self.COLOR_SUBGOAL, (sgx, sgy), 7)
        pygame.draw.circle(self.screen, (255, 255, 255), (sgx, sgy), 7, 2)

    def _draw_static_objects(self):
        for obj in self.world.static_objects:
            if obj.shape == ShapeType.RECTANGLE:
                rx, ry, rw, rh = obj.bbox
                sx, sy = self.world_to_screen(rx, ry)
                sw = self.meters_to_px(rw)
                sh = self.meters_to_px(rh)
                pygame.draw.rect(
                    self.screen,
                    self.COLOR_STATIC_RECT,
                    pygame.Rect(sx, sy, sw, sh),
                    border_radius=2,
                )
            elif obj.shape == ShapeType.CIRCLE:
                cx, cy = self.world_to_screen(obj.x, obj.y)
                rad_px = self.meters_to_px(obj.radius)
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
                color = self.COLOR_DOOR_CLOSED
                width = 0
            elif door.state in (SemiStaticState.OPENING, SemiStaticState.CLOSING):
                color = self.COLOR_DOOR_TRANSITION
                width = 0
            else:
                color = self.COLOR_DOOR_OPEN
                width = 2

            pygame.draw.rect(
                self.screen,
                color,
                pygame.Rect(sx, sy, sw, sh),
                width=width,
                border_radius=2,
            )

            if self.debug_mode:
                label = self.small_font.render(door.state.value, True, color)
                self.screen.blit(label, (sx + 4, sy - 14))

    def _draw_social_spaces(self):
        for grp in self.world.human_groups:
            cx, cy = self.world_to_screen(grp.center_x, grp.center_y)
            rad_px = self.meters_to_px(grp.radius)
            is_interact = grp.group_type.value == "INTERACTING"
            color = (
                self.COLOR_OSPACE_INTERACT if is_interact else self.COLOR_OSPACE_GROUP
            )

            surf = pygame.Surface((rad_px * 2 + 4, rad_px * 2 + 4), pygame.SRCALPHA)
            pygame.draw.circle(
                surf, (*color, 38), (rad_px + 2, rad_px + 2), rad_px
            )
            pygame.draw.circle(
                surf, (*color, 180), (rad_px + 2, rad_px + 2), rad_px, 2
            )
            self.screen.blit(surf, (cx - rad_px - 2, cy - rad_px - 2))

            if is_interact and len(grp.members) >= 2:
                pts = [self.world_to_screen(m.x, m.y) for m in grp.members]
                pygame.draw.lines(self.screen, color, True, pts, 1)

        for h in self.world.humans:
            poly_pts = self._build_asymmetric_gaussian_polygon(h, num_segments=28)
            if len(poly_pts) >= 3:
                pygame.draw.polygon(self.screen, self.COLOR_PERSONAL_SPACE, poly_pts, 1)

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
        for dyn in self.world.dynamic_objects:
            cx, cy = self.world_to_screen(dyn.x, dyn.y)
            rad_px = self.meters_to_px(dyn.radius)
            pygame.draw.circle(self.screen, self.COLOR_DYNAMIC_OBJ, (cx, cy), rad_px)
            pygame.draw.circle(self.screen, (255, 255, 255), (cx, cy), rad_px, 2)

            hx = dyn.x + dyn.radius * 1.3 * math.cos(dyn.theta)
            hy = dyn.y + dyn.radius * 1.3 * math.sin(dyn.theta)
            shx, shy = self.world_to_screen(hx, hy)
            pygame.draw.line(self.screen, (255, 255, 255), (cx, cy), (shx, shy), 2)

            if self.debug_mode:
                pred_pts = dyn.predict_trajectory(
                    dt=self.world.dt, horizon_sec=2.4, step_stride=4
                )
                for px, py in pred_pts:
                    spx, spy = self.world_to_screen(px, py)
                    pygame.draw.circle(self.screen, self.COLOR_PRED_TRAJ, (spx, spy), 3)

    def _draw_humans(self):
        for h in self.world.humans:
            cx, cy = self.world_to_screen(h.x, h.y)
            rad_px = self.meters_to_px(h.radius)

            if h.activity == HumanActivity.STANDING:
                color = self.COLOR_HUMAN_STANDING
            elif h.activity == HumanActivity.WALKING:
                color = self.COLOR_HUMAN_WALKING
            else:
                color = self.COLOR_HUMAN_RUNNING

            pygame.draw.circle(self.screen, color, (cx, cy), rad_px)
            pygame.draw.circle(self.screen, (255, 255, 255), (cx, cy), rad_px, 2)

            vec_len = h.radius * (1.2 + 0.45 * h.speed)
            hx = h.x + vec_len * math.cos(h.theta)
            hy = h.y + vec_len * math.sin(h.theta)
            shx, shy = self.world_to_screen(hx, hy)
            pygame.draw.line(self.screen, color, (cx, cy), (shx, shy), 2)

            if self.debug_mode:
                for px, py in h.predict_trajectory(
                    dt=self.world.dt, horizon_sec=2.5, step_stride=4
                ):
                    spx, spy = self.world_to_screen(px, py)
                    pygame.draw.circle(self.screen, color, (spx, spy), 3)

                tag = f"{h.activity.value[:4]}|{h.social_context.value}"
                tag_color = (
                    (220, 38, 38)
                    if h.social_context
                    in (
                        SocialContext.APPROACHING,
                        SocialContext.CROSSING,
                        SocialContext.INTERACTING,
                    )
                    else (31, 41, 55)
                )
                lbl = self.small_font.render(tag, True, tag_color)
                self.screen.blit(lbl, (cx - 34, cy - rad_px - 15))

    def _draw_goal(self):
        robot = self.world.robot
        if robot is None:
            return
        gx, gy = self.world_to_screen(robot.goal_x, robot.goal_y)
        grad_px = self.meters_to_px(robot.goal_radius)
        pygame.draw.circle(self.screen, self.COLOR_GOAL, (gx, gy), grad_px)
        pygame.draw.circle(
            self.screen, (255, 255, 255), (gx, gy), max(2, grad_px // 2), 2
        )

    def _draw_debug_overlays(self):
        robot = self.world.robot
        if robot is None:
            return
        rx, ry = self.world_to_screen(robot.x, robot.y)
        sensor_px = self.meters_to_px(robot.sensor_radius)
        pygame.draw.circle(
            self.screen, self.COLOR_SENSOR_RANGE, (rx, ry), sensor_px, 1
        )

        for hx, hy in self.world.lidar_hit_points:
            shx, shy = self.world_to_screen(hx, hy)
            pygame.draw.line(self.screen, self.COLOR_LIDAR_RAY, (rx, ry), (shx, shy), 1)
            pygame.draw.circle(self.screen, self.COLOR_LIDAR_RAY, (shx, shy), 3)

        if len(robot.trajectory) >= 2:
            pts = [self.world_to_screen(px, py) for px, py in robot.trajectory]
            pygame.draw.lines(self.screen, self.COLOR_TRAJECTORY, False, pts, 2)

    def _draw_robot(self):
        robot = self.world.robot
        if robot is None:
            return
        rx, ry = self.world_to_screen(robot.x, robot.y)
        rad_px = self.meters_to_px(robot.radius)
        color = (
            self.COLOR_ROBOT_COLLISION if self.world.is_collision else self.COLOR_ROBOT
        )
        pygame.draw.circle(self.screen, color, (rx, ry), rad_px)
        pygame.draw.circle(self.screen, (255, 255, 255), (rx, ry), rad_px, 2)

        hx = robot.x + robot.radius * math.cos(robot.theta)
        hy = robot.y + robot.radius * math.sin(robot.theta)
        shx, shy = self.world_to_screen(hx, hy)
        pygame.draw.line(self.screen, self.COLOR_ROBOT_HEADING, (rx, ry), (shx, shy), 3)

    def _draw_hud(self):
        info = self.world.get_info()
        soc = info["social_status"]
        panel = pygame.Surface((500, 260), pygame.SRCALPHA)
        panel.fill(self.COLOR_HUD_BG)
        self.screen.blit(panel, (12, 12))

        mode_names = {
            1: "1: Manual (Keyboard)",
            2: "2: Baseline 1 (A* + Basic Avoidance)",
            3: "3: Baseline 2 (A* + Social Rules)",
            4: "4: RL Policy (Phase 6)",
        }

        status_str = "RUNNING"
        status_color = (52, 211, 153)
        if self.paused:
            status_str = "PAUSED"
            status_color = (251, 191, 36)
        if info["is_collision"]:
            status_str = f"COLLISION ({info['collided_with']})"
            status_color = (248, 113, 113)
        elif info["is_goal_reached"]:
            status_str = "GOAL REACHED (+100.0)"
            status_color = (52, 211, 153)

        social_alert = "SAFE (0.0)"
        social_color = (52, 211, 153)
        if soc["group_splitting"] or soc["ospace_intrusion"]:
            social_alert = f"O-SPACE / GROUP VIOLATION ({soc['group_penalty']})"
            social_color = (248, 113, 113)
        elif soc["personal_intrusion"]:
            social_alert = (
                f"PERSONAL INTRUSION ({soc['social_penalty']}, C={soc['max_social_cost']:.2f})"
            )
            social_color = (251, 191, 36)

        rb = self.reward_breakdown
        rew_detail = (
            f"R_t={self.last_reward:+.2f} | Sum={self.episode_reward:+.1f} "
            f"(prog:{rb.get('r_progress', 0.0):+.2f}, wait:{rb.get('r_context', 0.0):+.1f})"
        )
        rew_color = (52, 211, 153) if self.last_reward >= 0.0 else (251, 191, 36)

        lines = [
            (f"STATUS   : {status_str}", status_color),
            (f"TOPOLOGY : {info['topology']} | State: {self.state_dim}-D", self.COLOR_TEXT),
            (f"AGENT    : {mode_names.get(self.agent_mode, '1: Manual')}", (96, 165, 250)),
            (f"TIME     : {info['sim_time']:.1f}s (Step {info['step']})", self.COLOR_TEXT),
            (
                f"POSE     : x={info['robot_pos'][0]:.2f}m, y={info['robot_pos'][1]:.2f}m, θ={info['robot_theta_deg']:.1f}°",
                self.COLOR_TEXT,
            ),
            (
                f"SUBGOAL  : d_sg={info['dist_to_subgoal']:.2f}m | d_goal={info['distance_to_goal']:.2f}m",
                self.COLOR_TEXT,
            ),
            (f"SOCIAL   : {social_alert}", social_color),
            (f"REWARD   : {rew_detail}", rew_color),
            (
                f"VEL      : v={info['robot_v']:.2f} m/s, ω={info['robot_omega']:.2f} rad/s | Debug: {'ON' if self.debug_mode else 'OFF'}",
                self.COLOR_TEXT,
            ),
            (
                "KEYS     : [1-3] Mode | [D] Debug | [T] Topology | [R] Reset",
                self.COLOR_TEXT,
            ),
        ]

        for idx, (text, color) in enumerate(lines):
            surf = self.font.render(text, True, color)
            self.screen.blit(surf, (22, 18 + idx * 23))

    def close(self):
        pygame.quit()