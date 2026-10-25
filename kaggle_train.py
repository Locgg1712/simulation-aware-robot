# kaggle_train.py
"""
Pipeline tự động hóa toàn trình để Huấn luyện, Đánh giá Benchmark và Vẽ Biểu đồ RL
cho FarmBot Town trên Kaggle (hoặc máy cá nhân):
1. Đóng gói mã nguồn lên Kaggle (bao gồm toàn bộ logic `game/` NPC, lịch trình `schedules.py`,
   bản đồ `maps.py`, AGV ở chế độ Headless mà không cần kèm thư mục ảnh `sprites/`):
     python kaggle_train.py --pack-dataset
2. Chạy huấn luyện trọn gói trên Kaggle Notebook:
     !python /kaggle/input/<ten-dataset>/kaggle_train.py --timesteps 500000 --n-envs 4
3. Tự động lưu toàn bộ `models/`, `logs/`, `results/` và nén thành `farmbot_trained_rl_bundle.zip`
   tại `/kaggle/working/` để tải về đưa vào game.
"""

import argparse
from pathlib import Path
import sys
import zipfile

from evaluation.benchmark_runner import run_benchmark_suite
from rl.train_eval import train_model
from visualization.plot_results import generate_all_plots

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

PROJECT_ROOT = Path(__file__).resolve().parent

KAGGLE_INCLUDE_ITEMS = [
    "configs/default_config.yaml",
    "configs/rl_hyperparams.yaml",
    "objects/__init__.py",
    "objects/base_object.py",
    "objects/static_object.py",
    "objects/semi_static_object.py",
    "objects/dynamic_object.py",
    "objects/robot.py",
    "environment/__init__.py",
    "environment/topology.py",
    "environment/map_generator.py",
    "environment/physics.py",
    "environment/spawn_manager.py",
    "environment/world.py",
    "human/__init__.py",
    "human/human_agent.py",
    "human/groups.py",
    "human/motion_model.py",
    "human/social_space.py",
    "perception/__init__.py",
    "perception/ground_truth.py",
    "planning/__init__.py",
    "planning/astar.py",
    "planning/subgoal_selector.py",
    "behavior/__init__.py",
    "behavior/context_classifier.py",
    "behavior/rule_based_agent.py",
    "rl/__init__.py",
    "rl/state_builder.py",
    "rl/reward_calculator.py",
    "rl/gym_env.py",
    "rl/train_eval.py",
    "evaluation/__init__.py",
    "evaluation/metrics.py",
    "evaluation/benchmark_runner.py",
    "visualization/__init__.py",
    "visualization/plot_results.py",
    "game/__init__.py",
    "game/__main__.py",
    "game/app.py",
    "game/atmosphere.py",
    "game/audio.py",
    "game/autopilot.py",
    "game/constants.py",
    "game/dialogue.py",
    "game/entities.py",
    "game/farming.py",
    "game/game_state.py",
    "game/journal_ui.py",
    "game/maps.py",
    "game/quests.py",
    "game/random_events.py",
    "game/rl_bridge.py",
    "game/safety_hri.py",
    "game/schedules.py",
    "game/sprite_vault.py",
    "game/stardew_systems.py",
    "game/terrain.py",
    "game/ui_renderer.py",
    "game/vfx.py",
    "game/world_builder.py",
    "game/data/items.json",
    "game/data/npcs.json",
    "game/data/quests.json",
    "game/data/random_events.json",
    "main.py",
    "kaggle_train.py",
]


def pack_kaggle_dataset(zip_name: str = "farmbot_rl_kaggle_dataset.zip") -> Path:
    """Đóng gói toàn bộ mô-đun RL + logic thực của `game/` (Headless NPC/Schedules/AGV, không cần ảnh `.png`)."""
    out_zip = PROJECT_ROOT / zip_name
    with zipfile.ZipFile(out_zip, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for rel_path in KAGGLE_INCLUDE_ITEMS:
            full_path = PROJECT_ROOT / rel_path
            if full_path.exists():
                zf.write(full_path, arcname=rel_path)

    size_kb = out_zip.stat().st_size / 1024.0
    print("=" * 76)
    print(f"[OK] Đã đóng gói Dataset Kaggle (RL + Headless Game Engine) : {out_zip} ({size_kb:.1f} KB)")
    print("     (Đã bao gồm toàn bộ logic `game/` NPC, `schedules.py`, `maps.py`, AGV; lược bỏ ảnh `sprites/`)")
    print("=" * 76)
    return out_zip


def bundle_trained_outputs(output_dir: Path, bundle_name: str = "farmbot_trained_rl_bundle.zip") -> Path:
    """Nén toàn bộ thư mục models/, logs/, results/ sau khi train để tải về từ Kaggle."""
    bundle_path = output_dir / bundle_name
    with zipfile.ZipFile(bundle_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for folder in ("models", "logs", "results"):
            folder_path = output_dir / folder
            if not folder_path.exists():
                continue
            for file_path in folder_path.rglob("*"):
                if file_path.is_file():
                    arcname = file_path.relative_to(output_dir).as_posix()
                    zf.write(file_path, arcname=arcname)

    size_mb = bundle_path.stat().st_size / (1024.0 * 1024.0)
    print("=" * 76)
    print(f"[OK] Đã đóng gói kết quả huấn luyện : {bundle_path} ({size_mb:.2f} MB)")
    print("     Giải nén file này vào thư mục gốc dự án để dùng ngay trong Game [P]!")
    print("=" * 76)
    return bundle_path


def run_kaggle_pipeline(
    timesteps: int = 500000,
    n_envs: int = 4,
    device: str = "auto",
    output_dir: str | None = None,
    bc_steps: int = 3500,
    eval_episodes: int = 30,
    include_dqn: bool = False,
    no_subproc: bool = False,
    seed: int = 42,
):
    if output_dir is None:
        kaggle_work = Path("/kaggle/working")
        out_root = kaggle_work if kaggle_work.exists() else PROJECT_ROOT
    else:
        out_root = Path(output_dir)

    out_root.mkdir(parents=True, exist_ok=True)
    models_dir = out_root / "models"
    logs_dir = out_root / "logs"
    results_dir = out_root / "results"

    algos = ["PPO", "DQN"] if include_dqn else ["PPO"]
    modes = ["full_context", "no_context"]

    for algo in algos:
        for mode in modes:
            train_model(
                algo=algo,
                mode=mode,
                timesteps=timesteps,
                seed=seed,
                eval_freq=max(2000, timesteps // 10),
                n_eval_episodes=15,
                n_envs=n_envs,
                device=device,
                output_dir=out_root,
                bc_steps=bc_steps,
                use_subproc=not no_subproc,
            )

    # Chạy Benchmark trên cả 3 tập: Bản đồ Game (Maps 1-4), Validation (10-12) và Test (13-15)
    for idx, split_name in enumerate(("game", "val", "test")):
        run_benchmark_suite(
            split=split_name,
            episodes=eval_episodes,
            seed=2026 + idx * 2500,
            algo="PPO",
            output_dir=str(results_dir),
            models_dir=str(models_dir),
        )

    # Xuất các biểu đồ PNG (learning_curve.png & benchmark_comparison_*.png)
    generate_all_plots(logs_dir=str(logs_dir), results_dir=str(results_dir))

    # Nếu chạy ở thư mục khác PROJECT_ROOT hoặc trên Kaggle, đóng gói thành 1 file zip
    bundle_trained_outputs(out_root)


def parse_args():
    parser = argparse.ArgumentParser(
        description="Pipeline Huấn luyện & Đánh giá RL cho FarmBot Town trên Kaggle"
    )
    parser.add_argument(
        "--pack-dataset",
        action="store_true",
        help="Chỉ tạo file zip mã nguồn rút gọn để upload lên Kaggle Dataset",
    )
    parser.add_argument(
        "--timesteps",
        type=int,
        default=500000,
        help="Tổng số bước huấn luyện cho mỗi cấu hình RL (mặc định: 500000)",
    )
    parser.add_argument(
        "--n-envs",
        type=int,
        default=4,
        help="Số môi trường song song (mặc định: 4 cho 4 nhân vCPU Kaggle)",
    )
    parser.add_argument(
        "--device",
        type=str,
        default="auto",
        choices=["auto", "cpu", "cuda"],
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default=None,
        help="Thư mục lưu kết quả (tự động nhận /kaggle/working nếu chạy trên Kaggle)",
    )
    parser.add_argument(
        "--bc-steps",
        type=int,
        default=3500,
        help="Số bước Warm-Start từ chuyên gia trước khi học RL",
    )
    parser.add_argument(
        "--eval-episodes",
        type=int,
        default=30,
        help="Số episodes đánh giá cho mỗi tập Benchmark",
    )
    parser.add_argument(
        "--include-dqn",
        action="store_true",
        help="Huấn luyện thêm cả DQN bên cạnh PPO",
    )
    parser.add_argument(
        "--no-subproc",
        action="store_true",
        help="Dùng DummyVecEnv thay vì SubprocVecEnv",
    )
    parser.add_argument("--seed", type=int, default=42)
    return parser.parse_args()


def main():
    args = parse_args()
    if args.pack_dataset:
        pack_kaggle_dataset()
        return

    run_kaggle_pipeline(
        timesteps=args.timesteps,
        n_envs=args.n_envs,
        device=args.device,
        output_dir=args.output_dir,
        bc_steps=args.bc_steps,
        eval_episodes=args.eval_episodes,
        include_dqn=args.include_dqn,
        no_subproc=args.no_subproc,
        seed=args.seed,
    )


if __name__ == "__main__":
    main()

