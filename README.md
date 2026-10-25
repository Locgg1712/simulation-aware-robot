# Context-Aware Robot Navigation Simulation & FarmBot Town

Dự án tích hợp thống nhất giữa Trò chơi nhập vai 2D Top-Down (**FarmBot Town: Robot Nông Trại Tốt Bụng**) và Hệ thống Huấn luyện Học Tăng Cường Sâu **128 Chiều (128-Dim Context-Aware Social Navigation RL)** chạy trực tiếp trên nền logic của `game/` (Headless Game Engine).

---

## 🎮 1. Khởi Chạy Trò Chơi `FarmBot Town`

Trải nghiệm thế giới 5 Bản đồ liên thông, chu kỳ Ngày - Đêm, Thời tiết, 4 Mùa, 12 NPC có biểu cảm & lịch trình sống (`game/schedules.py`), Radar An toàn theo độ tuổi (`elder`/`child`/`adult`), Vùng Quạt Xanh Lá HRI (`game/safety_hri.py`), Mini-game Câu cá, Xưởng nâng cấp Robin và 7 Sự kiện Ngẫu nhiên Biến động Thế giới (`game/random_events.py`):

```bash
# Khởi chạy trò chơi FarmBot Town (chọn 1 trong 2 lệnh)
python main.py
# hoặc
python -m game
```

* **Phím điều khiển chính:** `W/A/S/D` (di chuyển), `Shift/X` (đi chậm an toàn), `Space` (phanh/câu cá), `E` (tương tác/nhận đơn/hái quả), `G` (tặng quà NPC), `J` (Sổ tay thị trấn 3 Tab), `U` (Xưởng Robin), `O` (Sự kiện ngẫu nhiên), `P` (bật AI Tự Hành Autopilot sử dụng mô hình RL 128 chiều).
* Chi tiết đặc tả kỹ thuật: xem tại [`Context-Aware-Robot-Navigation-Simulation.md`](Context-Aware-Robot-Navigation-Simulation.md) và [`Context_game_farmbot.md`](Context_game_farmbot.md).

---

## 🚀 2. Huấn Luyện RL 128 Chiều Trên Kaggle & Đánh Giá Benchmark (Headless)

Môi trường RL (`ContextAwareNavEnv` — Vector trạng thái **128 chiều**) đồng bộ trực tiếp với `HeadlessGameSession` của `game/` (bao gồm 4 Bản đồ nông trại/thị trấn, lộ trình tuần tra của `VillagerNPC`, lịch trình ngày/đêm `schedules.py`, xe kéo `FarmCartAGV`, nhóm tuổi `npcs.json`, Vùng Quạt HRI và 7 Sự kiện Ngẫu nhiên `random_events.py`) mà không cần mở cửa sổ Pygame hay tải file ảnh `.png`:

```bash
# 1. Đóng gói mã nguồn RL + Headless Game Engine (~160 KB, không cần thư mục ảnh sprites/) để upload lên Kaggle
python kaggle_train.py --pack-dataset

# 2. Chạy huấn luyện trọn gói trên Kaggle Notebook (4 nhân CPU SubprocVecEnv, lưu tại /kaggle/working)
python /kaggle/input/farmbot-rl/kaggle_train.py --timesteps 500000 --n-envs 4

# 3. Hoặc chạy kiểm tra / huấn luyện / đánh giá trực tiếp tại máy cá nhân:
python main.py --check-env
python -m rl.train_eval --algo PPO --mode full_context --timesteps 500000 --n-envs 4
python -m evaluation.benchmark_runner --split all --episodes 30
python -m visualization.plot_results
```
