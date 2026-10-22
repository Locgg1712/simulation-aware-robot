# Phase 7: Chạy tự động 4 Baselines trên tập Validation & Test
import argparse
import csv
import json
from pathlib import Path

from behavior.rule_based_agent import RuleBasedAgent
from environment.topology import TRAIN_TOPOLOGIES, VAL_TOPOLOGIES, TEST_TOPOLOGIES
from rl.gym_env import ContextAwareNavEnv
from rl.train_eval import RLPolicyAgent
from .metrics import EpisodeTracker, aggregate_metrics


BASELINE_CONFIGS = [
    {
        "id": "baseline_1",
        "name": "Baseline 1: A* + Basic Avoidance",
        "type": "rule",
        "mode": "basic",
        "use_social_astar": False,
    },
    {
        "id": "baseline_2",
        "name": "Baseline 2: A* + Social Rules",
        "type": "rule",
        "mode": "social",
        "use_social_astar": True,
    },
    {
        "id": "baseline_3",
        "name": "Baseline 3: A* + RL (No Social Context)",
        "type": "rl",
        "mode": "no_context",
        "use_social_astar": False,
    },
    {
        "id": "baseline_4",
        "name": "Baseline 4: A* + RL (Full Context)",
        "type": "rl",
        "mode": "full_context",
        "use_social_astar": True,
    },
]


def get_topologies_for_split(split: str) -> list[int]:
    if split == "train":
        return TRAIN_TOPOLOGIES
    if split == "val":
        return VAL_TOPOLOGIES
    if split == "test":
        return TEST_TOPOLOGIES
    return list(range(1, 16))


def evaluate_single_baseline(
    baseline_cfg: dict,
    split: str,
    episodes: int,
    base_seed: int,
    algo: str = "PPO",
) -> dict:
    topologies = get_topologies_for_split(split)
    is_rl = baseline_cfg["type"] == "rl"
    mode = baseline_cfg["mode"]
    include_social = mode != "no_context"

    env = ContextAwareNavEnv(
        split=split,
        include_social_context=True,
        continuous_actions=False,
    )
    env.world.use_social_astar = bool(baseline_cfg["use_social_astar"])

    if is_rl:
        rl_agent = RLPolicyAgent(include_social_context=include_social)
        loaded = rl_agent.auto_load_default(mode=mode)
        if not loaded:
            print(
                f"[Cảnh báo] Chưa tìm thấy model đã huấn luyện cho {baseline_cfg['name']}. "
                f"Đang sử dụng fallback agent để hoàn tất luồng chạy."
            )
        fallback_rule = RuleBasedAgent(mode="basic" if mode == "no_context" else "social")
    else:
        rule_agent = RuleBasedAgent(mode=mode)

    tracker = EpisodeTracker()
    episodes_results: list[dict] = []

    for ep_idx in range(episodes):
        ep_seed = base_seed + ep_idx
        topo_id = topologies[ep_idx % len(topologies)]

        obs, info = env.reset(seed=ep_seed, options={"topology_id": topo_id})
        env.world.use_social_astar = bool(baseline_cfg["use_social_astar"])
        env.world.replan_global_path()
        env.world._update_subgoal()

        tracker.reset()
        if env.world.robot is not None:
            tracker._prev_pos = env.world.robot.position

        done = False
        while not done:
            if is_rl:
                if rl_agent.is_loaded:
                    action = int(rl_agent.select_action(env.world))
                else:
                    action = int(fallback_rule.select_action(env.world))
            else:
                action = int(rule_agent.select_action(env.world))

            obs, reward, terminated, truncated, info = env.step(action)
            tracker.update(
                robot_pos=info["robot_pos"],
                dt=env.world.dt,
                step_reward=reward,
                social_status=info.get("social_status", {}),
                reward_breakdown=info.get("reward_breakdown", {}),
            )
            done = terminated or truncated

        ep_summary = tracker.finalize(
            is_goal_reached=info.get("is_goal_reached", False),
            is_collision=info.get("is_collision", False),
            topology_id=topo_id,
        )
        episodes_results.append(ep_summary)

    env.close()

    agg = aggregate_metrics(episodes_results)
    agg["baseline_id"] = baseline_cfg["id"]
    agg["baseline_name"] = baseline_cfg["name"]
    agg["split"] = split
    return agg


def save_benchmark_outputs(results: list[dict], split: str, out_dir: Path):
    out_dir.mkdir(parents=True, exist_ok=True)

    json_path = out_dir / f"benchmark_{split}.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    csv_path = out_dir / f"benchmark_{split}.csv"
    fieldnames = [
        "baseline_name",
        "split",
        "episodes",
        "success_rate",
        "collision_rate",
        "timeout_rate",
        "navigation_time",
        "path_length",
        "social_intrusion_ratio",
        "group_splitting_count",
        "smart_wait_count",
        "mean_reward",
    ]
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in results:
            writer.writerow({k: row.get(k, "") for k in fieldnames})

    md_path = out_dir / f"benchmark_{split}.md"
    lines = [
        f"# Kết quả Đánh giá Benchmark (Tập `{split.upper()}`)\n",
        "| Phương pháp (Baseline) | Success (%) | Collision (%) | Timeout (%) | Nav Time (s) | Path Len (m) | Social Intrusion (%) | Group Split | Smart Wait | Mean Reward |",
        "| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |",
    ]
    for r in results:
        lines.append(
            f"| **{r['baseline_name']}** | {r['success_rate']:.1f} | {r['collision_rate']:.1f} | "
            f"{r['timeout_rate']:.1f} | {r['navigation_time']:.2f} | {r['path_length']:.2f} | "
            f"{r['social_intrusion_ratio']:.2f} | {r['group_splitting_count']:.2f} | "
            f"{r['smart_wait_count']:.2f} | {r['mean_reward']:+.2f} |"
        )
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print("\n" + "\n".join(lines))
    print(f"\n[OK] Đã lưu báo cáo JSON : {json_path}")
    print(f"[OK] Đã lưu báo cáo CSV  : {csv_path}")
    print(f"[OK] Đã lưu báo cáo MD   : {md_path}")


def run_benchmark_suite(
    split: str = "val",
    episodes: int = 30,
    seed: int = 2026,
    algo: str = "PPO",
    output_dir: str = "results",
) -> list[dict]:
    out_path = Path(output_dir)
    all_results: list[dict] = []

    print("=" * 80)
    print(f"[Phase 7] Chạy Benchmark 4 Baselines | Split='{split.upper()}' | Episodes={episodes}")
    print("=" * 80)

    for cfg in BASELINE_CONFIGS:
        print(f"-> Đang đánh giá: {cfg['name']} ...")
        res = evaluate_single_baseline(
            baseline_cfg=cfg,
            split=split,
            episodes=episodes,
            base_seed=seed,
            algo=algo,
        )
        all_results.append(res)

    save_benchmark_outputs(all_results, split=split, out_dir=out_path)
    return all_results


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--split",
        type=str,
        default="both",
        choices=["train", "val", "test", "both"],
    )
    parser.add_argument("--episodes", type=int, default=30)
    parser.add_argument("--seed", type=int, default=2026)
    parser.add_argument("--algo", type=str, default="PPO")
    parser.add_argument("--output-dir", type=str, default="results")
    return parser.parse_args()


def main():
    args = parse_args()
    if args.split == "both":
        run_benchmark_suite("val", args.episodes, args.seed, args.algo, args.output_dir)
        run_benchmark_suite("test", args.episodes, args.seed + 5000, args.algo, args.output_dir)
    else:
        run_benchmark_suite(args.split, args.episodes, args.seed, args.algo, args.output_dir)


if __name__ == "__main__":
    main()