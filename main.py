import argparse
from pathlib import Path
import sys
import yaml

from behavior.rule_based_agent import RuleBasedAgent
from environment.world import World
from objects.robot import RobotAction
from rl.reward_calculator import RewardCalculator
from rl.state_builder import StateBuilder


if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")


def ensure_runtime_directories():
    for folder in ("models", "logs", "results"):
        Path(folder).mkdir(parents=True, exist_ok=True)


def load_config(config_path: str = "configs/default_config.yaml") -> dict:
    path = Path(config_path)
    if not path.exists():
        raise FileNotFoundError(f"Không tìm thấy file cấu hình tại: {path.resolve()}")
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def map_keyboard_to_action(keys, pygame_mod) -> RobotAction:
    if keys[pygame_mod.K_s]:
        return RobotAction.STOP
    if keys[pygame_mod.K_UP] or keys[pygame_mod.K_w]:
        return RobotAction.FORWARD
    if keys[pygame_mod.K_LEFT] or keys[pygame_mod.K_a]:
        return RobotAction.TURN_LEFT
    if keys[pygame_mod.K_RIGHT]:
        return RobotAction.TURN_RIGHT
    if keys[pygame_mod.K_DOWN] or keys[pygame_mod.K_x]:
        return RobotAction.SLOW_DOWN
    return RobotAction.WAIT


def run_gym_env_verification():
    from rl.gym_env import ContextAwareNavEnv
    from stable_baselines3.common.env_checker import check_env

    print("=" * 72)
    print("[Phase 5] Đang khởi tạo ContextAwareNavEnv và chạy SB3 check_env()...")
    env = ContextAwareNavEnv(split="train", include_social_context=True)
    check_env(env, warn=True)
    print("[OK] Vượt qua bài kiểm tra check_env() của Stable-Baselines3 không lỗi!")

    obs, info = env.reset(seed=42)
    print(f"[OK] Kích thước Vector State S_t : {obs.shape} (dtype={obs.dtype})")
    print(f"     - Khối 1 (Robot & Sub-goal, 6 chiều) : {obs[:6].round(3)}")
    print(f"     - Khối 2 (16 tia LiDAR, 16 chiều)    : {obs[6:22].round(3)}")

    baseline_agent = RuleBasedAgent(mode="social")
    print("\n--- Chạy thử 10 bước mô phỏng và in chi tiết Reward ---")
    for step_i in range(1, 11):
        action = int(baseline_agent.select_action(env.world))
        obs, reward, terminated, truncated, info = env.step(action)
        rb = info["reward_breakdown"]
        print(
            f"Step {step_i:02d} | Action={RobotAction(action).name:<10} "
            f"| R_t={reward:+.3f} (prog={rb['r_progress']:+.3f}, "
            f"soc={rb['r_social']:+.2f}, grp={rb['r_group']:+.1f}, wait={rb['r_context']:+.1f}) "
            f"| d_goal={info['distance_to_goal']:.2f}m"
        )
        if terminated or truncated:
            break

    env.close()
    print("=" * 72)


def run_headless_simulation(config: dict, rl_cfg: dict, steps: int = 100):
    world = World(config)
    world.use_social_astar = True
    world.replan_global_path()
    world._update_subgoal()

    agent = RuleBasedAgent(mode="social")
    state_builder = StateBuilder(include_social_context=True)
    reward_calc = RewardCalculator(rl_cfg.get("reward_weights", {}))
    episode_reward = 0.0

    print("=" * 72)
    print(f"[Headless Mode] Đang chạy mô phỏng {steps} bước trên {world.get_info()['topology']}...")
    for step_i in range(1, steps + 1):
        prev_goal_d = world.robot.distance_to_goal()
        prev_subgoal_d = world.subgoal_info["dist_to_subgoal"]
        action = agent.select_action(world)
        info = world.step(action)
        state_vec = state_builder.build(world)
        reward, _ = reward_calc.compute(
            world, action, prev_goal_d, prev_subgoal_d
        )
        episode_reward += reward

        if step_i % 10 == 0 or info["is_collision"] or info["is_goal_reached"]:
            print(
                f"Step {step_i:03d} | Pose={info['robot_pos']} | "
                f"Action={action.name:<10} | StateDim={len(state_vec)} | "
                f"d_goal={info['distance_to_goal']:.2f}m | "
                f"EpReward={episode_reward:+.2f}"
            )
        if info["is_collision"] or info["is_goal_reached"]:
            break
def main():
    ensure_runtime_directories()
    parser = argparse.ArgumentParser(
        description="Context-Aware Robot Navigation Simulation"
    )
    parser.add_argument(
        "--check-env",
        action="store_true",
    )
    parser.add_argument(
        "--headless",
        action="store_true",
        help="Chạy mô phỏng trên terminal, không cần Pygame",
    )
    parser.add_argument(
        "--steps",
        type=int,
        default=100,
        help="Số bước chạy ở chế độ headless",
    )
    parser.add_argument(
        "--model-path",
        type=str,
        default=None,
    )
    parser.add_argument(
        "--algo",
        type=str,
        default="PPO",
    )
    parser.add_argument(
        "--mode",
        type=str,
        default="full_context",
        choices=["full_context", "no_context"],
    )
    args = parser.parse_args()

    if args.check_env:
        run_gym_env_verification()
        return

    config = load_config("configs/default_config.yaml")
    rl_cfg_path = Path("configs/rl_hyperparams.yaml")
    rl_cfg = (
        yaml.safe_load(rl_cfg_path.read_text(encoding="utf-8"))
        if rl_cfg_path.exists()
        else {}
    )

    if args.headless:
        run_headless_simulation(config, rl_cfg, steps=args.steps)
        return

    import pygame
    from rl.train_eval import RLPolicyAgent
    from visualization.pygame_renderer import PygameRenderer

    world = World(config)
    renderer = PygameRenderer(world, config)

    include_social = args.mode == "full_context"
    state_builder = StateBuilder(include_social_context=include_social)
    reward_calc = RewardCalculator(rl_cfg.get("reward_weights", {}))
    episode_reward = 0.0

    baseline_basic = RuleBasedAgent(mode="basic")
    baseline_social = RuleBasedAgent(mode="social")

    rl_agent = RLPolicyAgent(include_social_context=include_social)
    if args.model_path:
        loaded = rl_agent.load(args.model_path, algo=args.algo)
    else:
        loaded = rl_agent.auto_load_default(mode=args.mode)

    if loaded:
        print(f"[RL Policy] Đã nạp thành công model: {rl_agent.loaded_path}")
        renderer.agent_mode = 4
    else:
        print("[RL Policy] Chưa tìm thấy file model trong 'models/'. Phím 4 sẽ tạm dùng Baseline 2.")

    world.use_social_astar = renderer.agent_mode in (3, 4)
    world.replan_global_path()
    world._update_subgoal()

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
                elif event.key == pygame.K_v:
                    renderer.stardew_mode = not renderer.stardew_mode
                elif event.key == pygame.K_r:
                    world.reset()
                    episode_reward = 0.0
                    renderer.update_rl_telemetry(0.0, 0.0, {})
                elif event.key == pygame.K_t:
                    world.next_topology()
                    episode_reward = 0.0
                    renderer.update_rl_telemetry(0.0, 0.0, {})
                elif event.key == pygame.K_e:
                    world.toggle_indoor_house()
                elif event.key == pygame.K_h:
                    renderer.show_hud = not renderer.show_hud
                elif event.key in (pygame.K_1, pygame.K_2, pygame.K_3, pygame.K_4):
                    renderer.agent_mode = event.key - pygame.K_0
                    world.use_social_astar = renderer.agent_mode in (3, 4)
                    world.replan_global_path()
                    world._update_subgoal()

        if not renderer.paused and not (world.is_collision or world.is_goal_reached):
            if renderer.agent_mode == 1:
                keys = pygame.key.get_pressed()
                action = map_keyboard_to_action(keys, pygame)
            elif renderer.agent_mode == 2:
                action = baseline_basic.select_action(world)
            elif renderer.agent_mode == 3:
                action = baseline_social.select_action(world)
            else:
                if rl_agent.is_loaded:
                    action = rl_agent.select_action(world)
                else:
                    action = baseline_social.select_action(world)

            prev_goal_d = world.robot.distance_to_goal()
            prev_subgoal_d = world.subgoal_info["dist_to_subgoal"]

            world.step(action)

            state_vec = state_builder.build(world)
            step_rew, breakdown = reward_calc.compute(
                world=world,
                action=action,
                prev_goal_dist=prev_goal_d,
                prev_subgoal_dist=prev_subgoal_d,
            )
            episode_reward += step_rew
            renderer.update_rl_telemetry(
                step_reward=step_rew,
                episode_reward=episode_reward,
                breakdown=breakdown,
                state_dim=len(state_vec),
            )

        renderer.render()

    renderer.close()
    sys.exit(0)


if __name__ == "__main__":
    main()