# Phase 6: Script huấn luyện và lưu model với Stable-Baselines3 (Tối ưu hóa cho Local & Kaggle)
import argparse
from pathlib import Path
import shutil
import numpy as np
import torch
import torch.nn.functional as F
import yaml
from stable_baselines3 import DQN, PPO
from stable_baselines3.common.callbacks import CheckpointCallback, EvalCallback
from stable_baselines3.common.monitor import Monitor
from stable_baselines3.common.vec_env import DummyVecEnv, SubprocVecEnv, VecMonitor

from behavior.rule_based_agent import RuleBasedAgent
from environment.world import World
from objects.robot import RobotAction
from .gym_env import ContextAwareNavEnv, PROJECT_ROOT
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
            alt = PROJECT_ROOT / path
            if alt.exists() or alt.with_suffix(".zip").exists():
                path = alt
            else:
                return False

        if algo is not None:
            self.algo_name = algo.upper()

        algo_cls = ALGO_MAP.get(self.algo_name, PPO)
        try:
            self.model = algo_cls.load(str(path), device="cpu")
            self.loaded_path = str(path)
            return True
        except Exception:
            for fallback_name, fallback_cls in ALGO_MAP.items():
                try:
                    self.model = fallback_cls.load(str(path), device="cpu")
                    self.algo_name = fallback_name
                    self.loaded_path = str(path)
                    return True
                except Exception:
                    continue
        return False

    def auto_load_default(
        self, mode: str = "full_context", models_dir: str | Path = "models"
    ) -> bool:
        m_dir = Path(models_dir)
        search_dirs = [m_dir]
        if (PROJECT_ROOT / "models") not in search_dirs:
            search_dirs.append(PROJECT_ROOT / "models")

        for base in search_dirs:
            candidates = [
                base / f"best_ppo_{mode}" / "best_model.zip",
                base / f"ppo_{mode}.zip",
                base / f"best_dqn_{mode}" / "best_model.zip",
                base / f"dqn_{mode}.zip",
            ]
            for cand in candidates:
                if cand.exists():
                    algo = (
                        "DQN"
                        if "dqn" in cand.name.lower()
                        or "dqn" in str(cand.parent).lower()
                        else "PPO"
                    )
                    if self.load(cand, algo=algo):
                        return True
        return False

    def select_action(self, world: World) -> RobotAction:
        if self.model is None or world.robot is None:
            return RobotAction.STOP

        obs = self.state_builder.build(world)
        return self.select_action_from_obs(obs)

    def select_action_from_obs(self, obs: np.ndarray) -> RobotAction:
        if self.model is None:
            return RobotAction.STOP
        obs_space = getattr(self.model, "observation_space", None)
        if obs_space is not None and hasattr(obs_space, "shape") and obs_space.shape:
            exp_dim = int(obs_space.shape[0])
            if obs.shape[0] > exp_dim:
                obs = obs[:exp_dim]
            elif obs.shape[0] < exp_dim:
                pad = np.zeros(exp_dim - obs.shape[0], dtype=np.float32)
                obs = np.concatenate([obs, pad], axis=0)
        action, _ = self.model.predict(obs, deterministic=self.deterministic)
        return RobotAction(int(action))


def load_rl_hyperparams(path_str: str = "configs/rl_hyperparams.yaml") -> dict:
    path = Path(path_str)
    if not path.exists():
        alt = PROJECT_ROOT / path_str
        if alt.exists():
            path = alt
        else:
            return {}
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def _make_env_fn(
    split: str,
    include_social: bool,
    seed: int,
    rank: int = 0,
):
    def _init():
        env = ContextAwareNavEnv(
            split=split,
            include_social_context=include_social,
            continuous_actions=False,
        )
        env.reset(seed=seed + rank * 1009)
        return env

    return _init


def create_vectorized_env(
    split: str,
    include_social: bool,
    n_envs: int,
    seed: int,
    monitor_filename: str | None = None,
    use_subproc: bool = True,
):
    n_envs = max(1, int(n_envs))
    env_fns = [
        _make_env_fn(split=split, include_social=include_social, seed=seed, rank=i)
        for i in range(n_envs)
    ]
    if n_envs > 1 and use_subproc:
        try:
            vec_env = SubprocVecEnv(env_fns, start_method="spawn")
        except Exception:
            vec_env = DummyVecEnv(env_fns)
    else:
        vec_env = DummyVecEnv(env_fns)

    return VecMonitor(vec_env, filename=monitor_filename)


def build_model(
    algo_name: str,
    env,
    train_cfg: dict,
    seed: int,
    n_envs: int = 1,
    device: str = "auto",
    tensorboard_log: str | None = None,
):
    algo_key = algo_name.upper()
    lr = float(train_cfg.get("learning_rate", 3e-4))
    gamma = float(train_cfg.get("gamma", 0.99))
    batch_size = int(train_cfg.get("batch_size", 64))
    policy_kwargs = dict(net_arch=[256, 256])

    if algo_key == "PPO":
        # Với mạng MLP 2 lớp [256, 256], PPO chạy trên CPU nhanh và ổn định hơn GPU
        ppo_device = "cpu" if device == "auto" else device
        n_steps = max(512, 2048 // max(1, n_envs))
        return PPO(
            policy="MlpPolicy",
            env=env,
            learning_rate=lr,
            n_steps=n_steps,
            batch_size=batch_size,
            n_epochs=10,
            gamma=gamma,
            gae_lambda=0.95,
            clip_range=0.2,
            ent_coef=0.01,
            policy_kwargs=policy_kwargs,
            verbose=1,
            seed=seed,
            device=ppo_device,
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
            device=device,
            tensorboard_log=tensorboard_log,
        )

    raise ValueError(f"Thuật toán không hợp lệ: {algo_name}. Chọn PPO hoặc DQN.")


def pretrain_with_expert(
    model,
    include_social: bool,
    bc_steps: int = 3500,
    bc_epochs: int = 12,
    batch_size: int = 128,
    seed: int = 42,
):
    """
    Warm-start mạng Policy (PPO / DQN) bằng Behavioral Cloning từ RuleBasedAgent trên
    các bản đồ Game FarmBot Town (Maps 1-4) và Train Topologies (5-9) trước khi chạy RL.
    Giúp Agent nắm vững kỹ năng bám đường A* và tránh vật cản ngay từ đầu, tránh kẹt ở local minimum.
    """
    if bc_steps <= 0:
        return

    expert_mode = "social" if include_social else "basic"
    expert = RuleBasedAgent(mode=expert_mode)
    env = ContextAwareNavEnv(
        split="train",
        include_social_context=include_social,
        continuous_actions=False,
    )

    obs_list: list[np.ndarray] = []
    act_list: list[int] = []

    obs, _ = env.reset(seed=seed)
    ep_idx = 0
    for _ in range(bc_steps):
        act = int(expert.select_action(env.world))
        obs_list.append(obs.copy())
        act_list.append(act)
        obs, _, terminated, truncated, _ = env.step(act)
        if terminated or truncated:
            ep_idx += 1
            obs, _ = env.reset(seed=seed + ep_idx)

    env.close()

    obs_arr = np.asarray(obs_list, dtype=np.float32)
    act_arr = np.asarray(act_list, dtype=np.int64)
    device = model.device

    obs_t = torch.as_tensor(obs_arr, device=device)
    act_t = torch.as_tensor(act_arr, device=device)

    if isinstance(model, PPO):
        net = model.policy
        optimizer = torch.optim.Adam(net.parameters(), lr=1e-3)
        net.train()
        n_samples = len(obs_arr)
        for _ in range(bc_epochs):
            perm = torch.randperm(n_samples, device=device)
            for i in range(0, n_samples, batch_size):
                idx = perm[i : i + batch_size]
                b_obs = obs_t[idx]
                b_act = act_t[idx]
                dist = net.get_distribution(b_obs)
                logits = dist.distribution.logits
                loss = F.cross_entropy(logits, b_act)
                optimizer.zero_grad()
                loss.backward()
                optimizer.step()
    elif isinstance(model, DQN):
        q_net = model.q_net
        optimizer = torch.optim.Adam(q_net.parameters(), lr=1e-3)
        q_net.train()
        n_samples = len(obs_arr)
        for _ in range(bc_epochs):
            perm = torch.randperm(n_samples, device=device)
            for i in range(0, n_samples, batch_size):
                idx = perm[i : i + batch_size]
                b_obs = obs_t[idx]
                b_act = act_t[idx]
                q_vals = q_net(b_obs)
                loss = F.cross_entropy(q_vals, b_act)
                optimizer.zero_grad()
                loss.backward()
                optimizer.step()
        model.q_net_target.load_state_dict(model.q_net.state_dict())

    print(
        f"[Warm-Start BC] Đã khởi tạo kỹ năng điều hướng cơ sở ({bc_steps} steps, mode='{expert_mode}')."
    )


def train_model(
    algo: str = "PPO",
    mode: str = "full_context",
    timesteps: int | None = None,
    seed: int = 42,
    eval_freq: int = 5000,
    n_eval_episodes: int = 15,
    n_envs: int = 1,
    device: str = "auto",
    output_dir: str | Path = ".",
    bc_steps: int = 3500,
    use_subproc: bool = True,
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

    out_root = Path(output_dir)
    models_dir = out_root / "models"
    logs_dir = out_root / "logs" / run_name
    best_model_dir = models_dir / f"best_{run_name}"
    ckpt_dir = models_dir / f"checkpoints_{run_name}"

    models_dir.mkdir(parents=True, exist_ok=True)
    logs_dir.mkdir(parents=True, exist_ok=True)
    best_model_dir.mkdir(parents=True, exist_ok=True)
    ckpt_dir.mkdir(parents=True, exist_ok=True)

    n_envs = max(1, int(n_envs))
    train_env = create_vectorized_env(
        split="train",
        include_social=include_social,
        n_envs=n_envs,
        seed=seed,
        monitor_filename=str(logs_dir / "monitor.csv"),
        use_subproc=use_subproc,
    )

    val_env = create_vectorized_env(
        split="val",
        include_social=include_social,
        n_envs=1,
        seed=seed + 999,
        monitor_filename=None,
        use_subproc=False,
    )

    tb_log_dir = None
    try:
        import tensorboard  # noqa: F401

        tb_log_dir = str(out_root / "logs" / "tb")
    except ImportError:
        tb_log_dir = None

    model = build_model(
        algo_name=algo_upper,
        env=train_env,
        train_cfg=train_cfg,
        seed=seed,
        n_envs=n_envs,
        device=device,
        tensorboard_log=tb_log_dir,
    )

    # Khởi tạo Warm-Start trước khi học tăng cường
    if bc_steps > 0:
        pretrain_with_expert(
            model=model,
            include_social=include_social,
            bc_steps=bc_steps,
            seed=seed,
        )

    raw_eval_freq = max(1000, min(eval_freq, max(1000, total_timesteps // 2)))
    effective_eval_freq = max(250, raw_eval_freq // n_envs)
    effective_ckpt_freq = max(500, max(2000, total_timesteps // 5) // n_envs)

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
        save_freq=effective_ckpt_freq,
        save_path=str(ckpt_dir),
        name_prefix=run_name,
    )

    print("=" * 76)
    print(
        f"[Phase 6] Bắt đầu huấn luyện: Algo={algo_upper} | Mode={mode} "
        f"| Steps={total_timesteps} | n_envs={n_envs} | device={model.device}"
    )
    print("=" * 76)

    model.learn(
        total_timesteps=total_timesteps,
        callback=[eval_callback, checkpoint_callback],
        progress_bar=False,
    )

    final_model_path = models_dir / f"{run_name}.zip"
    model.save(str(final_model_path))

    # Nếu EvalCallback đã lưu best_model.zip tốt nhất trên tập Val, đồng bộ sang final_model_path
    best_model_file = best_model_dir / "best_model.zip"
    if best_model_file.exists():
        shutil.copy2(best_model_file, final_model_path)
    else:
        shutil.copy2(final_model_path, best_model_file)

    train_env.close()
    val_env.close()

    print(f"[OK] Đã lưu model cuối tại      : {final_model_path}")
    print(f"[OK] Đã lưu best model tại      : {best_model_file}")
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
    print(
        f"[Đánh giá Model] {results['model_path']} trên tập '{split.upper()}' ({episodes} episodes):"
    )
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
        description="Huấn luyện và đánh giá RL Agent (PPO / DQN) cho FarmBot Town & Kaggle"
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
        "--n-envs",
        type=int,
        default=4,
        help="Số môi trường chạy song song (trên Kaggle nên đặt 4)",
    )
    parser.add_argument(
        "--device",
        type=str,
        default="auto",
        choices=["auto", "cpu", "cuda"],
        help="Thiết bị huấn luyện (PPO MLP tự động ưu tiên cpu khi chọn auto)",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default=".",
        help="Thư mục gốc lưu models/ và logs/ (trên Kaggle đặt /kaggle/working)",
    )
    parser.add_argument(
        "--bc-steps",
        type=int,
        default=3500,
        help="Số bước Warm-Start Behavioral Cloning trước khi học RL (0 để tắt)",
    )
    parser.add_argument(
        "--no-subproc",
        action="store_true",
        help="Sử dụng DummyVecEnv thay vì SubprocVecEnv",
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
        choices=["game", "train", "val", "test"],
    )
    return parser.parse_args()


def main():
    args = parse_args()
    algo = args.algo.upper()
    run_name = f"{algo.lower()}_{args.mode}"
    out_root = Path(args.output_dir)

    if args.eval_only:
        target_path = (
            Path(args.model_path)
            if args.model_path
            else out_root / "models" / f"best_{run_name}" / "best_model.zip"
        )
        if not target_path.exists():
            target_path = out_root / "models" / f"{run_name}.zip"
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
        n_envs=args.n_envs,
        device=args.device,
        output_dir=out_root,
        bc_steps=args.bc_steps,
        use_subproc=not args.no_subproc,
    )

    best_candidate = out_root / "models" / f"best_{run_name}" / "best_model.zip"
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
