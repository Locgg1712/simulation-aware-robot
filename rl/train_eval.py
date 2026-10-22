# Phase 6: Script huấn luyện và lưu model với Stable-Baselines3
import argparse
from pathlib import Path
import numpy as np
import yaml
from stable_baselines3 import DQN, PPO
from stable_baselines3.common.callbacks import CheckpointCallback, EvalCallback
from stable_baselines3.common.monitor import Monitor

from environment.world import World
from objects.robot import RobotAction
from .gym_env import ContextAwareNavEnv
from .state_builder import StateBuilder


ALGO_MAP = {
    "PPO": PPO,
    "DQN": DQN,
}


class RLPolicyAgent:
    def __init__(
        self,
        model_path: str | Path | None = None,
        algo: str = "PPO",
        include_social_context: bool = True,
        deterministic: bool = True,
    ):
        self.algo_name = algo.upper()
        self.include_social_context = bool(include_social_context)
        self.deterministic = bool(deterministic)
        self.state_builder = StateBuilder(
            include_social_context=self.include_social_context
        )
        self.model = None
        self.loaded_path: str = ""

        if model_path is not None:
            self.load(model_path, self.algo_name)

    @property
    def is_loaded(self) -> bool:
        return self.model is not None

    def load(self, model_path: str | Path, algo: str | None = None) -> bool:
        path = Path(model_path)
        if not path.exists() and not path.with_suffix(".zip").exists():
            return False

        if algo is not None:
            self.algo_name = algo.upper()

        algo_cls = ALGO_MAP.get(self.algo_name, PPO)
        try:
            self.model = algo_cls.load(str(path))
            self.loaded_path = str(path)
            return True
        except Exception:
            for fallback_name, fallback_cls in ALGO_MAP.items():
                try:
                    self.model = fallback_cls.load(str(path))
                    self.algo_name = fallback_name
                    self.loaded_path = str(path)
                    return True
                except Exception:
                    continue
        return False

    def auto_load_default(self, mode: str = "full_context") -> bool:
        candidates = [
            Path(f"models/best_ppo_{mode}/best_model.zip"),
            Path(f"models/ppo_{mode}.zip"),
            Path(f"models/best_dqn_{mode}/best_model.zip"),
            Path(f"models/dqn_{mode}.zip"),
        ]
        for cand in candidates:
            if cand.exists():
                algo = "DQN" if "dqn" in cand.name.lower() or "dqn" in str(cand.parent).lower() else "PPO"
                if self.load(cand, algo=algo):
                    return True
        return False

    def select_action(self, world: World) -> RobotAction:
        if self.model is None or world.robot is None:
            return RobotAction.STOP

        obs = self.state_builder.build(world)
        action, _ = self.model.predict(obs, deterministic=self.deterministic)
        return RobotAction(int(action))


def load_rl_hyperparams(path_str: str = "configs/rl_hyperparams.yaml") -> dict:
    path = Path(path_str)
    if not path.exists():
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def build_model(
    algo_name: str,
    env,
    train_cfg: dict,
    seed: int,
    tensorboard_log: str | None = None,
):
    algo_key = algo_name.upper()
    lr = float(train_cfg.get("learning_rate", 3e-4))
    gamma = float(train_cfg.get("gamma", 0.99))
    batch_size = int(train_cfg.get("batch_size", 64))
    policy_kwargs = dict(net_arch=[256, 256])

    if algo_key == "PPO":
        return PPO(
            policy="MlpPolicy",
            env=env,
            learning_rate=lr,
            n_steps=2048,
            batch_size=batch_size,
            n_epochs=10,
            gamma=gamma,
            gae_lambda=0.95,
            clip_range=0.2,
            ent_coef=0.01,
            policy_kwargs=policy_kwargs,
            verbose=1,
            seed=seed,
            tensorboard_log=tensorboard_log,
        )

    if algo_key == "DQN":
        return DQN(
            policy="MlpPolicy",
            env=env,
            learning_rate=lr,
            buffer_size=100000,
            learning_starts=1000,
            batch_size=batch_size,
            gamma=gamma,
            train_freq=4,
            gradient_steps=1,
            target_update_interval=1000,
            exploration_fraction=0.25,
            exploration_final_eps=0.05,
            policy_kwargs=policy_kwargs,
            verbose=1,
            seed=seed,
            tensorboard_log=tensorboard_log,
        )

    raise ValueError(f"Thuật toán không hợp lệ: {algo_name}. Chọn PPO hoặc DQN.")


def train_model(
    algo: str = "PPO",
    mode: str = "full_context",
    timesteps: int | None = None,
    seed: int = 42,
    eval_freq: int = 5000,
    n_eval_episodes: int = 15,
) -> Path:
    assert mode in ("full_context", "no_context")
    include_social = mode == "full_context"
    algo_upper = algo.upper()
    run_name = f"{algo_upper.lower()}_{mode}"

    rl_cfg = load_rl_hyperparams("configs/rl_hyperparams.yaml")
    train_cfg = rl_cfg.get("training", {})
    total_timesteps = int(
        timesteps if timesteps is not None else train_cfg.get("total_timesteps", 500000)
    )

    models_dir = Path("models")
    logs_dir = Path("logs") / run_name
    best_model_dir = models_dir / f"best_{run_name}"
    ckpt_dir = models_dir / f"checkpoints_{run_name}"

    models_dir.mkdir(parents=True, exist_ok=True)
    logs_dir.mkdir(parents=True, exist_ok=True)
    best_model_dir.mkdir(parents=True, exist_ok=True)
    ckpt_dir.mkdir(parents=True, exist_ok=True)

    train_env = ContextAwareNavEnv(
        split="train",
        include_social_context=include_social,
        continuous_actions=False,
    )
    train_env = Monitor(train_env, filename=str(logs_dir / "monitor.csv"))

    val_env = ContextAwareNavEnv(
        split="val",
        include_social_context=include_social,
        continuous_actions=False,
    )
    val_env = Monitor(val_env)

    tb_log_dir = None
    try:
        import tensorboard
        tb_log_dir = str(Path("logs") / "tb")
    except ImportError:
        tb_log_dir = None

    model = build_model(
        algo_name=algo_upper,
        env=train_env,
        train_cfg=train_cfg,
        seed=seed,
        tensorboard_log=tb_log_dir,
    )

    effective_eval_freq = max(1000, min(eval_freq, max(1000, total_timesteps // 2)))

    eval_callback = EvalCallback(
        val_env,
        best_model_save_path=str(best_model_dir),
        log_path=str(logs_dir),
        eval_freq=effective_eval_freq,
        n_eval_episodes=n_eval_episodes,
        deterministic=True,
        render=False,
    )

    checkpoint_callback = CheckpointCallback(
        save_freq=max(2000, total_timesteps // 5),
        save_path=str(ckpt_dir),
        name_prefix=run_name,
    )

    print("=" * 72)
    print(f"[Phase 6] Bắt đầu huấn luyện: Algo={algo_upper} | Mode={mode} | Steps={total_timesteps}")
    print("=" * 72)

    model.learn(
        total_timesteps=total_timesteps,
        callback=[eval_callback, checkpoint_callback],
        progress_bar=False,
    )

    final_model_path = models_dir / f"{run_name}.zip"
    model.save(str(final_model_path))

    train_env.close()
    val_env.close()

    print(f"[OK] Đã lưu model cuối tại      : {final_model_path}")
    print(f"[OK] Đã lưu best model tại      : {best_model_dir / 'best_model.zip'}")
    print(f"[OK] Đã lưu log huấn luyện tại  : {logs_dir / 'monitor.csv'}")
    return final_model_path


def evaluate_saved_model(
    model_path: str | Path,
    algo: str = "PPO",
    mode: str = "full_context",
    split: str = "val",
    episodes: int = 20,
    seed: int = 1000,
) -> dict:
    include_social = mode == "full_context"
    env = ContextAwareNavEnv(
        split=split,
        include_social_context=include_social,
        continuous_actions=False,
    )

    agent = RLPolicyAgent(
        model_path=model_path,
        algo=algo,
        include_social_context=include_social,
        deterministic=True,
    )
    if not agent.is_loaded:
        env.close()
        raise FileNotFoundError(f"Không thể nạp model từ đường dẫn: {model_path}")

    successes = 0
    collisions = 0
    timeouts = 0
    ep_rewards: list[float] = []
    ep_Steps: list[int] = []
    intrusion_steps = 0
    total_steps = 0

    for ep in range(episodes):
        obs, info = env.reset(seed=seed + ep)
        done = False
        ep_rew = 0.0
        steps = 0

        while not done:
            action, _ = agent.model.predict(obs, deterministic=True)
            obs, reward, terminated, truncated, info = env.step(int(action))
            ep_rew += reward
            steps += 1
            total_steps += 1

            soc = info.get("social_status", {})
            if soc.get("personal_intrusion") or soc.get("ospace_intrusion"):
                intrusion_steps += 1

            done = terminated or truncated

        ep_rewards.append(ep_rew)
        ep_Steps.append(steps)
        if info.get("is_goal_reached"):
            successes += 1
        elif info.get("is_collision"):
            collisions += 1
        else:
            timeouts += 1

    env.close()

    results = {
        "model_path": str(model_path),
        "split": split,
        "episodes": episodes,
        "success_rate": round(100.0 * successes / max(1, episodes), 2),
        "collision_rate": round(100.0 * collisions / max(1, episodes), 2),
        "timeout_rate": round(100.0 * timeouts / max(1, episodes), 2),
        "mean_reward": round(float(np.mean(ep_rewards)), 2),
        "mean_steps": round(float(np.mean(ep_Steps)), 1),
        "social_intrusion_ratio": round(
            100.0 * intrusion_steps / max(1, total_steps), 2
        ),
    }

    print("=" * 72)
    print(f"[Đánh giá Model] {results['model_path']} trên tập '{split.upper()}' ({episodes} episodes):")
    print(f"  - Success Rate           : {results['success_rate']:.2f}%")
    print(f"  - Collision Rate         : {results['collision_rate']:.2f}%")
    print(f"  - Timeout Rate           : {results['timeout_rate']:.2f}%")
    print(f"  - Mean Episode Reward    : {results['mean_reward']:+.2f}")
    print(f"  - Mean Steps             : {results['mean_steps']:.1f}")
    print(f"  - Social Intrusion Ratio : {results['social_intrusion_ratio']:.2f}%")
    print("=" * 72)
    return results


def parse_args():
    parser = argparse.ArgumentParser(
        description="Huấn luyện và đánh giá RL Agent (PPO / DQN) cho Phase 6"
    )
    parser.add_argument(
        "--algo",
        type=str,
        default="PPO",
        choices=["PPO", "DQN", "ppo", "dqn"],
    )
    parser.add_argument(
        "--mode",
        type=str,
        default="full_context",
        choices=["full_context", "no_context"],
    )
    parser.add_argument(
        "--timesteps",
        type=int,
        default=None,
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
    )
    parser.add_argument(
        "--eval-freq",
        type=int,
        default=5000,
    )
    parser.add_argument(
        "--eval-episodes",
        type=int,
        default=15,
    )
    parser.add_argument(
        "--eval-only",
        action="store_true",
    )
    parser.add_argument(
        "--model-path",
        type=str,
        default=None,
    )
    parser.add_argument(
        "--split",
        type=str,
        default="val",
        choices=["train", "val", "test"],
    )
    return parser.parse_args()


def main():
    args = parse_args()
    algo = args.algo.upper()
    run_name = f"{algo.lower()}_{args.mode}"

    if args.eval_only:
        target_path = (
            Path(args.model_path)
            if args.model_path
            else Path(f"models/best_{run_name}/best_model.zip")
        )
        if not target_path.exists():
            target_path = Path(f"models/{run_name}.zip")
        evaluate_saved_model(
            model_path=target_path,
            algo=algo,
            mode=args.mode,
            split=args.split,
            episodes=args.eval_episodes,
            seed=args.seed,
        )
        return

    saved_path = train_model(
        algo=algo,
        mode=args.mode,
        timesteps=args.timesteps,
        seed=args.seed,
        eval_freq=args.eval_freq,
        n_eval_episodes=args.eval_episodes,
    )

    best_candidate = Path(f"models/best_{run_name}/best_model.zip")
    eval_target = best_candidate if best_candidate.exists() else saved_path
    evaluate_saved_model(
        model_path=eval_target,
        algo=algo,
        mode=args.mode,
        split="val",
        episodes=args.eval_episodes,
        seed=args.seed + 500,
    )


if __name__ == "__main__":
    main()