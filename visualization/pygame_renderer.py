# visualization/pygame_renderer.py
import math
import pygame
from environment.world import World
from objects.static_object import ShapeType
from objects.semi_static_object import SemiStaticState


class PygameRenderer:
    """
    Bộ hiển thị trực quan 2D Top-Down bằng Pygame (Phase 2).
    Hỗ trợ hiển thị 15 Topology, Semi-static Doors (FSM) và Dynamic Objects + Trajectory Prediction.
    """

    COLOR_BG = (245, 247, 250)
    COLOR_GRID_LINE = (225, 230, 238)
    COLOR_OCCUPIED_CELL = (210, 218, 230)
    COLOR_STATIC_RECT = (75, 85, 99)
    COLOR_STATIC_CIRCLE = (55, 65, 81)

    # Màu cho Semi-static Door theo trạng thái FSM
    COLOR_DOOR_CLOSED = (220, 38, 38)
    COLOR_DOOR_TRANSITION = (245, 158, 11)
    COLOR_DOOR_OPEN = (16, 185, 129)

    # Màu cho Dynamic Object & Quỹ đạo dự đoán
    COLOR_DYNAMIC_OBJ = (147, 51, 234)
    COLOR_PRED_TRAJ = (168, 85, 247)

    COLOR_ROBOT = (37, 99, 235)
    COLOR_ROBOT_COLLISION = (220, 38, 38)
    COLOR_ROBOT_HEADING = (255, 255, 255)
    COLOR_GOAL = (16, 185, 129)
    COLOR_TRAJECTORY = (96, 165, 250)
    COLOR_SENSOR_RANGE = (59, 130, 246)
    COLOR_LIDAR_RAY = (239, 68, 68)
    COLOR_HUD_BG = (17, 24, 39, 215)
    COLOR_TEXT = (249, 250, 251)

    def __init__(self, world: World, config: dict):
        pygame.init()
        pygame.display.set_caption("Context-Aware Robot Navigation Simulation - Phase 2")

        vis_cfg = config["visualization"]
        self.window_size: int = int(vis_cfg["window_size"])
        self.fps: int = int(vis_cfg["fps"])
        self.world = world
        self.scale: float = self.window_size / self.world.width

        self.screen = pygame.display.set_mode((self.window_size, self.window_size))
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont("consolas", 14)

        self.debug_mode: bool = True
        self.paused: bool = False
        self.agent_mode: int = 1

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
        self._draw_dynamic_objects()

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
            pygame.draw.line(self.screen, self.COLOR_GRID_LINE, (pos, 0), (pos, self.window_size), 1)
            pygame.draw.line(self.screen, self.COLOR_GRID_LINE, (0, pos), (self.window_size, pos), 1)

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
                pygame.draw.circle(self.screen, self.COLOR_STATIC_CIRCLE, (cx, cy), rad_px)

    def _draw_semi_static_objects(self):
        """Vẽ cửa bán tĩnh với màu sắc phản ánh đúng trạng thái FSM."""
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
                width = 2  # Khi OPEN chỉ vẽ khung viền xanh lá để thấy lối thông

            pygame.draw.rect(self.screen, color, pygame.Rect(sx, sy, sw, sh), width=width, border_radius=2)

            if self.debug_mode:
                label = self.font.render(door.state.value, True, color)
                self.screen.blit(label, (sx + 6, sy - 16))

    def _draw_dynamic_objects(self):
        """Vẽ các vật thể động (AGV / Robot khác) và mũi tên vận tốc."""
        for dyn in self.world.dynamic_objects:
            cx, cy = self.world_to_screen(dyn.x, dyn.y)
            rad_px = self.meters_to_px(dyn.radius)
            pygame.draw.circle(self.screen, self.COLOR_DYNAMIC_OBJ, (cx, cy), rad_px)
            pygame.draw.circle(self.screen, (255, 255, 255), (cx, cy), rad_px, 2)

            # Vector hướng di chuyển
            hx = dyn.x + dyn.radius * 1.3 * math.cos(dyn.theta)
            hy = dyn.y + dyn.radius * 1.3 * math.sin(dyn.theta)
            shx, shy = self.world_to_screen(hx, hy)
            pygame.draw.line(self.screen, (255, 255, 255), (cx, cy), (shx, shy), 2)

            # Vẽ quỹ đạo dự đoán chấm bi trong Debug Mode
            if self.debug_mode:
                pred_pts = dyn.predict_trajectory(dt=self.world.dt, horizon_sec=2.4, step_stride=4)
                for px, py in pred_pts:
                    spx, spy = self.world_to_screen(px, py)
                    pygame.draw.circle(self.screen, self.COLOR_PRED_TRAJ, (spx, spy), 3)

    def _draw_goal(self):
        robot = self.world.robot
        if robot is None:
            return
        gx, gy = self.world_to_screen(robot.goal_x, robot.goal_y)
        grad_px = self.meters_to_px(robot.goal_radius)
        pygame.draw.circle(self.screen, self.COLOR_GOAL, (gx, gy), grad_px)
        pygame.draw.circle(self.screen, (255, 255, 255), (gx, gy), max(2, grad_px // 2), 2)

    def _draw_debug_overlays(self):
        robot = self.world.robot
        if robot is None:
            return
        rx, ry = self.world_to_screen(robot.x, robot.y)
        sensor_px = self.meters_to_px(robot.sensor_radius)
        pygame.draw.circle(self.screen, self.COLOR_SENSOR_RANGE, (rx, ry), sensor_px, 1)

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
        color = self.COLOR_ROBOT_COLLISION if self.world.is_collision else self.COLOR_ROBOT
        pygame.draw.circle(self.screen, color, (rx, ry), rad_px)
        pygame.draw.circle(self.screen, (255, 255, 255), (rx, ry), rad_px, 2)

        hx = robot.x + robot.radius * math.cos(robot.theta)
        hy = robot.y + robot.radius * math.sin(robot.theta)
        shx, shy = self.world_to_screen(hx, hy)
        pygame.draw.line(self.screen, self.COLOR_ROBOT_HEADING, (rx, ry), (shx, shy), 3)

    def _draw_hud(self):
        info = self.world.get_info()
        panel = pygame.Surface((420, 215), pygame.SRCALPHA)
        panel.fill(self.COLOR_HUD_BG)
        self.screen.blit(panel, (12, 12))

        mode_names = {
            1: "1: Manual (Keyboard)",
            2: "2: A* Basic (Phase 4)",
            3: "3: A* Social Rules (Phase 4)",
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

        lines = [
            f"STATUS   : {status_str}",
            f"TOPOLOGY : {info['topology']}",
            f"MODE     : {mode_names.get(self.agent_mode, '1: Manual')}",
            f"TIME     : {info['sim_time']:.1f}s (Step {info['step']})",
            f"POSE     : x={info['robot_pos'][0]:.2f}m, y={info['robot_pos'][1]:.2f}m, θ={info['robot_theta_deg']:.1f}°",
            f"VEL      : v={info['robot_v']:.2f} m/s, ω={info['robot_omega']:.2f} rad/s",
            f"GOAL D   : {info['distance_to_goal']:.2f} m",
            f"DEBUG    : {'ON' if self.debug_mode else 'OFF'} (Press D)",
            "KEYS     : [WASD/Arrows] Move | [T] Next Topology | [R] Reset",
        ]

        for idx, text in enumerate(lines):
            color = status_color if idx == 0 else self.COLOR_TEXT
            surf = self.font.render(text, True, color)
            self.screen.blit(surf, (22, 18 + idx * 21))

    def close(self):
        pygame.quit()