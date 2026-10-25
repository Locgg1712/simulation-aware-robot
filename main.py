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
    print(
        f"[Headless Mode] Đang chạy mô phỏng {steps} bước trên {world.get_info()['topology']}..."
    )
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
        description="Context-Aware Robot Navigation Simulation & FarmBot Town Game"
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

    # Khởi chạy trực tiếp trò chơi FarmBot Town RPG (game/app.py)
    from game.app import main as run_game_main

    run_game_main()


if __name__ == "__main__":
    main()
