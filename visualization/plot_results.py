# Phase 7: Vẽ biểu đồ Learning Curve và bảng so sánh Metrics
import argparse
import csv
import json
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np


def _read_monitor_csv(csv_path: Path) -> tuple[np.ndarray, np.ndarray]:
    rewards: list[float] = []
    lengths: list[int] = []
    if not csv_path.exists():
        return np.array([]), np.array([])

    with open(csv_path, "r", encoding="utf-8") as f:
        lines = [line for line in f if not line.startswith("#")]
        reader = csv.DictReader(lines)
        for row in reader:
            try:
                rewards.append(float(row["r"]))
                lengths.append(int(float(row["l"])))
            except (KeyError, ValueError):
                continue

    if not rewards:
        return np.array([]), np.array([])

    timesteps = np.cumsum(lengths)
    return timesteps, np.array(rewards, dtype=np.float32)


def _moving_average(values: np.ndarray, window: int = 20) -> np.ndarray:
    if len(values) < window or window <= 1:
        return values
    kernel = np.ones(window) / window
    return np.convolve(values, kernel, mode="valid")


def plot_learning_curves(logs_dir: Path, out_dir: Path):
    runs = [
        ("ppo_full_context", "Baseline 4: PPO (Full Context)", "#2563eb"),
        ("ppo_no_context", "Baseline 3: PPO (No Social Context)", "#9333ea"),
        ("dqn_full_context", "DQN (Full Context)", "#059669"),
        ("dqn_no_context", "DQN (No Social Context)", "#d97706"),
    ]

    fig, ax = plt.subplots(figsize=(9, 5), dpi=150)
    plotted = False

    for folder_name, label, color in runs:
        csv_file = logs_dir / folder_name / "monitor.csv"
        steps, rewards = _read_monitor_csv(csv_file)
        if len(rewards) == 0:
            continue

        plotted = True
        ax.plot(steps, rewards, color=color, alpha=0.22, linewidth=1.0)
        win = max(5, min(30, len(rewards) // 5))
        if len(rewards) >= win and win > 1:
            smooth_r = _moving_average(rewards, window=win)
            smooth_s = steps[win - 1 :]
            ax.plot(smooth_s, smooth_r, color=color, linewidth=2.2, label=label)
        else:
            ax.plot(steps, rewards, color=color, linewidth=2.0, label=label)

    if not plotted:
        plt.close(fig)
        return

    ax.set_title("Training Learning Curve (Episode Reward vs. Timesteps)", fontsize=13, fontweight="bold")
    ax.set_xlabel("Timesteps", fontsize=11)
    ax.set_ylabel("Episode Reward", fontsize=11)
    ax.grid(True, linestyle="--", alpha=0.4)
    ax.legend(loc="lower right")
    fig.tight_layout()

    out_path = out_dir / "learning_curve.png"
    fig.savefig(out_path)
    plt.close(fig)
    print(f"[OK] Đã xuất biểu đồ Learning Curve : {out_path}")


def plot_benchmark_comparison(json_path: Path, out_dir: Path):
    if not json_path.exists():
        return

    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    if not data:
        return

    split = data[0].get("split", "val").upper()
    short_names = [
        "B1: A* Basic",
        "B2: A* Social",
        "B3: RL No-Ctx",
        "B4: RL Full-Ctx",
    ]
    labels = short_names[: len(data)]

    metrics_spec = [
        ("success_rate", "Success Rate (%)", "#10b981"),
        ("collision_rate", "Collision Rate (%)", "#ef4444"),
        ("social_intrusion_ratio", "Social Space Intrusion (%)", "#f59e0b"),
        ("group_splitting_count", "Group Splitting (events/ep)", "#ec4899"),
        ("navigation_time", "Navigation Time (s)", "#3b82f6"),
        ("mean_reward", "Mean Episode Reward", "#6366f1"),
    ]

    fig, axes = plt.subplots(2, 3, figsize=(14, 8), dpi=150)
    axes_flat = axes.flatten()

    for idx, (key, title, color) in enumerate(metrics_spec):
        ax = axes_flat[idx]
        vals = [float(item.get(key, 0.0)) for item in data]
        bars = ax.bar(labels, vals, color=color, alpha=0.88, width=0.55)
        ax.set_title(title, fontsize=11, fontweight="bold")
        ax.grid(axis="y", linestyle="--", alpha=0.4)
        ax.tick_params(axis="x", rotation=18)

        for bar, v in zip(bars, vals):
            y_pos = bar.get_height()
            ax.annotate(
                f"{v:.1f}",
                xy=(bar.get_x() + bar.get_width() / 2, y_pos),
                xytext=(0, 3 if y_pos >= 0 else -12),
                textcoords="offset points",
                ha="center",
                va="bottom",
                fontsize=9,
                fontweight="bold",
            )

    fig.suptitle(
        f"Benchmark Comparison Across 4 Baselines ({split} Split)",
        fontsize=14,
        fontweight="bold",
    )
    fig.tight_layout(rect=[0, 0.02, 1, 0.95])

    out_path = out_dir / f"benchmark_comparison_{split.lower()}.png"
    fig.savefig(out_path)
    plt.close(fig)
    print(f"[OK] Đã xuất biểu đồ Benchmark ({split}) : {out_path}")


def generate_all_plots(logs_dir: str = "logs", results_dir: str = "results"):
    l_path = Path(logs_dir)
    r_path = Path(results_dir)
    r_path.mkdir(parents=True, exist_ok=True)

    plot_learning_curves(l_path, r_path)
    plot_benchmark_comparison(r_path / "benchmark_val.json", r_path)
    plot_benchmark_comparison(r_path / "benchmark_test.json", r_path)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--logs-dir", type=str, default="logs")
    parser.add_argument("--results-dir", type=str, default="results")
    args = parser.parse_args()
    generate_all_plots(args.logs_dir, args.results_dir)


if __name__ == "__main__":
    main()