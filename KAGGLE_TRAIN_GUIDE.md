# HƯỚNG DẪN CHUẨN HUẤN LUYỆN REINFORCEMENT LEARNING (RL) TRÊN KAGGLE
### Dự án: FarmBot Town – Context-Aware Robot Navigation Simulation (128 Chiều)

---

## 1. Tổng Quan Kiến Trúc Huấn Luyện Không Cần Giao Diện (Headless)

Trong quá trình huấn luyện RL quy mô lớn (500.000+ timesteps), **hoàn toàn không cần render màn hình Pygame hay tải các file ảnh `.png`** (`sprites/`):
* Toàn bộ bản đồ nông trại (`game/maps.py`), lịch trình di chuyển theo giờ (`game/schedules.py`), xe kéo tự hành `FarmCartAGV`, thú nuôi `FarmAnimal`, tương tác xã hội của 12 cư dân `VillagerNPC` và 7 sự kiện ngẫu nhiên động (`game/random_events.py`) đã được đóng gói trong **`HeadlessGameSession`** (`game/rl_bridge.py`).
* Tốc độ mô phỏng đạt **hơn 3.000 – 5.000 bước/giây** trên CPU Kaggle, nhanh gấp hơn 100 lần so với chạy có giao diện đồ họa.
* Vector quan sát chuẩn **128 chiều** ($\mathbf{S}_t^{\text{ext}} \in \mathbb{R}^{128}$) được đồng nhất 100% giữa lúc Train (`StateBuilder.build()`) và lúc Deploy trong Game (`GameRLNavigator.build_observation()`).
* Quy trình tích hợp sẵn **Warm-Start Behavioral Cloning (BC)** từ chuyên gia `RuleBasedAgent` (đạt tỷ lệ an toàn vật lý tuyệt đối 0% va chạm) trước khi chính sách RL bắt đầu tự khám phá tối ưu.

---

## 2. Bước 1: Chuẩn Bị & Tải File Lên Kaggle Dataset

Mã nguồn nhẹ gọn phục vụ huấn luyện đã được đóng gói sẵn trong file zip:
```
D:\Projects\simulation aware robot\farmbot_rl_kaggle_dataset.zip (~283 KB)
```
*(Nếu bạn sửa code và muốn đóng gói lại, chỉ cần chạy lệnh: `python kaggle_train.py --pack-dataset`)*.

### Các bước tạo Dataset trên Kaggle:
1. Đăng nhập vào [Kaggle](https://www.kaggle.com/).
2. Nhấn vào menu **Datasets** $\rightarrow$ chọn **New Dataset**.
3. Đặt tiêu đề (Title): `farmbot-rl-dataset`.
4. Kéo thả file `farmbot_rl_kaggle_dataset.zip` vào khu vực upload.
5. Nhấn nút **Create** và đợi Kaggle hoàn tất xử lý (chỉ mất khoảng 5–10 giây).

---

## 3. Bước 2: Thiết Lập Kaggle Notebook

1. Vào mục **Code** trên Kaggle $\rightarrow$ chọn **New Notebook**.
2. Ở thanh bên phải (**Notebook options**):
   * **Accelerator:** Chọn **CPU** (Kaggle cung cấp 4 vCPUs rất mạnh mẽ, chạy PPO MLP 256x256 trên CPU ổn định và nhanh hơn GPU do không tốn overhead chuyển dữ liệu qua PCIe). *Bạn cũng có thể chọn GPU T4 x2 nếu muốn.*
   * **Internet:** Bật **ON** (để pip cài đặt thư viện).
   * **Environment:** Chọn **Always use latest environment**.
3. Nhấn **+ Add Data** ở góc trên bên phải $\rightarrow$ tìm chọn dataset `farmbot-rl-dataset` bạn vừa tạo ở Bước 1.

---

## 4. Bước 3: Nội Dung Các Ô Lệnh (Notebook Cells)

Bạn hãy tạo 4 ô lệnh (Cells) trong Notebook và chạy tuần tự:

### Cell 1: Cài Đặt Thư Viện Dependencies
```python
# Cell 1: Cài đặt Stable-Baselines3, Gymnasium và các thư viện cần thiết
!pip install --quiet stable-baselines3 gymnasium pyyaml
```

---

### Cell 2: Giải Nén Mã Nguồn Vào Thư Mục Làm Việc
```python
# Cell 2: Giải nén dataset vào /kaggle/working/
import os
import zipfile
from pathlib import Path

working_dir = Path("/kaggle/working")
input_dir = Path("/kaggle/input")

# Tìm file zip trong thư mục input
zip_candidates = list(input_dir.glob("**/*farmbot*.zip")) + list(input_dir.glob("**/*.zip"))
assert len(zip_candidates) > 0, "Không tìm thấy file dataset zip trong /kaggle/input!"

dataset_zip = zip_candidates[0]
print(f"Đang giải nén: {dataset_zip} -> {working_dir}")

with zipfile.ZipFile(dataset_zip, 'r') as zf:
    zf.extractall(working_dir)

os.chdir(working_dir)
print("Các thư mục đã sẵn sàng:")
!ls -lh
```

---

### Cell 3: Chạy Kiểm Tra Môi Trường & Huấn Luyện Toàn Diện

#### Lựa chọn A: Smoke Test Nhanh (Kiểm tra thông luồng trong 1–2 phút)
```python
# Chạy thử nghiệm ngắn để kiểm tra toàn bộ luồng huấn luyện, benchmark và vẽ biểu đồ
!python kaggle_train.py --timesteps 10000 --bc-steps 1000 --eval-episodes 10 --n-envs 4
```

#### Lựa chọn B: Huấn Luyện Đầy Đủ Chuẩn Nghiệm Thu (500.000 Timesteps)
```python
# Huấn luyện toàn trình cả PPO Full Context (128d) và Baseline No Context
# Tự động lưu Best Model, Benchmark 4 Baselines trên 3 tập maps và vẽ biểu đồ PNG
!python kaggle_train.py --timesteps 500000 --n-envs 4 --bc-steps 3500 --eval-episodes 30
```

> **Ghi chú về thời gian chạy:** Với `n_envs = 4` trên CPU Kaggle, mỗi 100.000 bước mất khoảng 5–7 phút. Quá trình chạy 500.000 bước hoàn tất trong khoảng 30–45 phút.

---

### Cell 4: Kiểm Tra Kết Quả & Tải Về Trọng Số Mô Hình
Sau khi Cell 3 kết thúc, toàn bộ kết quả đã được tự động nén thành file:
`/kaggle/working/farmbot_trained_rl_bundle.zip`

Chạy lệnh kiểm tra kích thước và danh sách file:
```python
# Cell 4: Kiểm tra kết quả huấn luyện
from pathlib import Path
bundle = Path("/kaggle/working/farmbot_trained_rl_bundle.zip")
print(f"File Bundle kết quả: {bundle} ({bundle.stat().st_size / (1024*1024):.2f} MB)")

# Hiển thị bảng tổng hợp Benchmark trên bản đồ Game
print("\n--- BÁO CÁO BENCHMARK TRÊN BẢN ĐỒ GAME (MAPS 1-4) ---")
!cat /kaggle/working/results/benchmark_game.md

# Hiển thị bảng tổng hợp Benchmark trên tập Kiểm thử (Topologies 13-15)
print("\n--- BÁO CÁO BENCHMARK TRÊN TẬP KIỂM THỬ (TEST) ---")
!cat /kaggle/working/results/benchmark_test.md
```

**Cách tải file về máy tính cá nhân:**
* Ở cây thư mục bên phải (**Output** / `/kaggle/working`), nhấn vào dấu 3 chấm cạnh file `farmbot_trained_rl_bundle.zip` $\rightarrow$ chọn **Download**.

---

## 5. Bước 4: Tích Hợp Mô Hình Đã Huấn Luyện Vào Game Tại Máy Cá Nhân

1. Giải nén trực tiếp file `farmbot_trained_rl_bundle.zip` vào thư mục gốc của dự án:
   ```
   d:\Projects\simulation aware robot\
   ```
   Nó sẽ ghi đè và cập nhật chính xác các thư mục:
   * `models/ppo_full_context.zip` & `models/best_ppo_full_context/best_model.zip` (Mô hình RL 128 chiều tối ưu)
   * `models/ppo_no_context.zip` (Mô hình Baseline 3 đối chứng)
   * `results/` (Các bảng số liệu `benchmark_game.md`, `.csv`, `.json`)
   * `results/plots/` (Biểu đồ `learning_curve.png`, `benchmark_comparison_*.png`)

2. **Chạy nghiệm thu trong Game FarmBot Town:**
   ```bash
   python -m game
   ```
   * Nhấn phím **`P`** để bật chế độ **Auto-Pilot RL**: Robot tự động lập kế hoạch qua A* toàn cục, đồng thời mạng nơ-ron PPO 128 chiều quan sát chuyển động của NPC, thú nuôi, AGV, vùng quạt tương tác HRI để chủ động né tránh, nhường đường và bám đích hoàn toàn mượt mà!

3. **Chạy mô phỏng kiểm thử 15 Topologies (Pygame):**
   ```bash
   python main.py
   ```
   * Nhấn phím **`4`** để giao toàn quyền điều khiển cho mô hình RL PPO vừa huấn luyện.

---

## 6. Bảng Giải Thích Tham Số Dòng Lệnh `kaggle_train.py`

| Tham số | Mặc định | Ý nghĩa |
| :--- | :---: | :--- |
| `--timesteps` | `500000` | Tổng số bước huấn luyện cho mỗi cấu hình RL (`full_context` và `no_context`). |
| `--n-envs` | `4` | Số môi trường chạy song song (tối ưu cho 4 vCPUs của máy ảo Kaggle). |
| `--bc-steps` | `3500` | Số bước học bắt chước chuyên gia (Behavioral Cloning Warm-Start) trước khi chạy RL. |
| `--eval-episodes` | `30` | Số tập kịch bản đánh giá cho mỗi phương pháp trong Benchmark (`game`, `val`, `test`). |
| `--include-dqn` | `False` | Tùy chọn huấn luyện thêm thuật toán DQN bên cạnh PPO. |
| `--pack-dataset` | `False` | Chỉ đóng gói file `farmbot_rl_kaggle_dataset.zip` tại máy local mà không train. |

---

## 7. Các Lưu Ý Kỹ Thuật Quan Trọng Đã Được Đồng Bộ

1. **Vận tốc NPC & Đơn vị vật lý:**
   * Tỷ lệ vận tốc thực tế của NPC so với Robot được chuẩn hóa ở mức **`0.195 m/s`** (tương đương `~0.20` tốc độ tối đa của Robot `1.0 m/s`), giải quyết triệt để lỗi chênh lệch tốc độ trước đây.
2. **NPC về nhà ban đêm:**
   * Khi NPC hết giờ làm việc và về nhà (`is_home_at_night = True`), NPC được chuyển ra khỏi bản đồ vật lý, loại bỏ hoàn toàn hiện tượng va chạm với vật cản vô hình.
3. **Phần thưởng mở rộng 128 chiều:**
   * Hàm phần thưởng tích hợp đầy đủ $R_{\text{fan}} = +15.0$, thưởng tiếp cận trực diện $+2.0\cos(\Delta\alpha)$, phạt áp sát sau lưng $-3.0$, phạt tốc độ cao gần người già/trẻ em $R_{\text{elder\_safe}} = -4.0$, thưởng giảm tốc $+1.0$, và thưởng vượt qua chướng ngại vật sự kiện $+5.0$, giúp mô hình `full_context` vượt trội rõ rệt so với `no_context`.

