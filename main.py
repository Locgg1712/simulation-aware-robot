# main.py
from pathlib import Path
import sys
import pygame
import yaml

from environment.world import World
from objects.robot import RobotAction
from visualization.pygame_renderer import PygameRenderer


def load_config(config_path: str = "configs/default_config.yaml") -> dict:
    path = Path(config_path)
    if not path.exists():
        raise FileNotFoundError(f"Không tìm thấy file cấu hình tại: {path.resolve()}")
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def map_keyboard_to_action(keys) -> RobotAction:
    if keys[pygame.K_s]:
        return RobotAction.STOP
    if keys[pygame.K_UP] or keys[pygame.K_w]:
        return RobotAction.FORWARD
    if keys[pygame.K_LEFT] or keys[pygame.K_a]:
        return RobotAction.TURN_LEFT
    if keys[pygame.K_RIGHT]:
        return RobotAction.TURN_RIGHT
    if keys[pygame.K_DOWN] or keys[pygame.K_x]:
        return RobotAction.SLOW_DOWN
    return RobotAction.WAIT


def main():
    config = load_config("configs/default_config.yaml")
    world = World(config)
    renderer = PygameRenderer(world, config)

    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
                elif event.key == pygame.K_SPACE:
                    renderer.paused = not renderer.paused
                elif event.key == pygame.K_d:
                    renderer.debug_mode = not renderer.debug_mode
                elif event.key == pygame.K_r:
                    world.reset()
                elif event.key == pygame.K_t:
                    world.next_topology()
                elif event.key in (pygame.K_1, pygame.K_2, pygame.K_3, pygame.K_4):
                    renderer.agent_mode = event.key - pygame.K_0

        if not renderer.paused:
            keys = pygame.key.get_pressed()
            action = map_keyboard_to_action(keys)
            world.step(action)

        renderer.render()

    renderer.close()
    sys.exit(0)


if __name__ == "__main__":
    main()