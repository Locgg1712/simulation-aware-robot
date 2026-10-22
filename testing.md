# Tài liệu Kiểm thử Hệ thống (Phase 1 – Phase 7)

Tài liệu này quy định các kịch bản kiểm thử chức năng, kiểm thử tích hợp và tiêu chuẩn nghiệm thu (Pass/Fail) cho toàn bộ 7 giai đoạn phát triển của dự án **Context-Aware Robot Navigation Simulation**.

---

## 1. Chuẩn bị Môi trường & Phím tắt Kiểm thử

### 1.1. Cài đặt thư viện
```bash
pip install -r requirements.txt
```

### 1.2. Bảng phím tắt trong giao diện Pygame (`main.py`)
| Phím | Chức năng | Ghi chú kiểm thử |
| :--- | :--- | :--- |
| `W` / `↑` | Hành động `FORWARD` ($v = 1.0\text{ m/s}, \omega = 0$) | Chỉ hoạt động ở Mode `1` |
| `A` / `←` | Hành động `TURN_LEFT` ($v = 0.5\text{ m/s}, \omega = +\pi/3$) | Chỉ hoạt động ở Mode `1` |
| `→` | Hành động `TURN_RIGHT` ($v = 0.5\text{ m/s}, \omega = -\pi/3$) | Chỉ hoạt động ở Mode `1` |
| `X` / `↓` | Hành động `SLOW_DOWN` ($v = 0.3\text{ m/s}, \omega = 0$) | Chỉ hoạt động ở Mode `1` |
| `S` | Hành động `STOP` ($v = 0.0\text{ m/s}, \omega = 0$) | Phanh khẩn cấp ở Mode `1` |
| `Không bấm` | Hành động `WAIT` ($v = 0.0\text{ m/s}, \omega = 0$) | Đứng chờ chủ động ở Mode `1` |
| `1` | Chuyển sang **Manual Mode** (Bàn phím) | Kiểm thử vật lý & cảm biến |
| `2` | Chuyển sang **Baseline 1** (`A* + Basic Avoidance`) | Kiểm thử Phase 4 |
| `3` | Chuyển sang **Baseline 2** (`A* + Social Rules`) | Kiểm thử Phase 4 |
| `4` | Chuyển sang **RL Policy** (`PPO / DQN`) | Kiểm thử Phase 6 |
| `D` | Bật / Tắt **Debug Mode** | Hiển thị LiDAR, Grid, A*, Social Space |
| `T` | Chuyển sang **Topology tiếp theo** ($1 \rightarrow 15$) | Kiểm thử 15 mẫu bản đồ |
| `R` | **Reset Episode** | Sinh ngẫu nhiên kịch bản mới trên Topology hiện tại |
| `SPACE` | **Pause / Resume** | Tạm dừng để quan sát thông số trên HUD |
| `ESC` | Thoát chương trình | Đóng cửa sổ mô phỏng |

---

## 2. Chi tiết Kiểm thử từng Phase

### Phase 1: Simulator Cơ bản & Vật lý 2D

**Mục tiêu kiểm thử:** Xác nhận hệ tọa độ thực $20.0\text{ m} \times 20.0\text{ m}$, lưới nền `Occupancy Grid` $80 \times 80$, động học Robot 6 hành động rời rạc, quét 16 tia LiDAR Raycast và xử lý va chạm hình học.

**Lệnh chạy:**
```bash
python main.py
```

**Các bước thực hiện:**
1. Nhấn phím `1` để chuyển về chế độ điều khiển tay (`Manual`).
2. Nhấn phím `D` để bật `Debug Mode`, quan sát lưới ô vuông xám (`Occupancy Grid`), vòng tròn cảm biến $R_{\text{sensor}} = 6.0\text{ m}$ và 16 tia LiDAR màu đỏ.
3. Sử dụng các phím `W`, `A`, `→`, `X`, `S` để điều khiển Robot di chuyển qua lại, xoay trái/phải và giảm tốc.
4. Lái Robot chạm thử vào tường chữ nhật và cột tròn để kiểm tra trạng thái `COLLISION`.
5. Nhấn `R` để reset, sau đó lái Robot chạm vào vòng tròn màu xanh lá (`Goal`) để kiểm tra trạng thái `GOAL REACHED`.

**Tiêu chuẩn nghiệm thu (Pass Criteria):**
* [x] Tọa độ $x, y$ và góc hướng $\theta \in [-\pi, \pi]$ trên HUD cập nhật mượt ở tốc độ $\Delta t = 0.1\text{ s}$.
* [x] 16 tia LiDAR cắt chính xác tại bề mặt tường và cột tròn, không xuyên qua vật cản tĩnh.
* [x] Khi chạm tường hoặc biên bản đồ, trạng thái chuyển ngay sang `COLLISION`, vận tốc Robot về $0$.
* [x] Khi khoảng cách tới đích $d_{\text{goal}} < R_{\text{robot}} + R_{\text{goal}}$, trạng thái chuyển sang `GOAL REACHED (+100.0)`.

---

### Phase 2: Đối tượng Bán tĩnh, Động & Sinh Bản đồ Procedural (15 Topologies)

**Mục tiêu kiểm thử:** Xác nhận máy trạng thái hữu hạn (FSM) của cửa tự động, chuyển động + dự đoán quỹ đạo của vật thể động (`AGV`) và tính hợp lệ của 15 Topology Templates.

**Lệnh chạy:**
```bash
python main.py
```

**Các bước thực hiện:**
1. Quan sát cửa tự động (`SemiStaticObject`): theo dõi sự chuyển đổi trạng thái `CLOSED` (đỏ) $\rightarrow$ `OPENING` (cam) $\rightarrow$ `OPEN` (viền xanh lá) $\rightarrow$ `CLOSING` (cam).
2. Khi cửa đang `CLOSED`, chiếu tia LiDAR vào cửa để xác nhận tia bị chặn lại; khi cửa `OPEN`, tia LiDAR đi xuyên qua cửa.
3. Quan sát các vật thể động màu tím (`DynamicObject`) di chuyển giữa các Waypoint và chuỗi chấm tròn dự đoán quỹ đạo phía trước mặt chúng.
4. Nhấn phím `T` liên tục 15 lần để duyệt qua toàn bộ Topology từ `1` đến `15` (Train: 1–9, Val: 10–12, Test: 13–15). Ở mỗi Topology, nhấn `R` 3–5 lần để kiểm tra `SpawnManager`.

**Tiêu chuẩn nghiệm thu (Pass Criteria):**
* [x] Robot bị báo `COLLISION` nếu cố đi qua cửa ở trạng thái `CLOSED`, `OPENING`, `CLOSING`, và đi qua an toàn khi `OPEN`.
* [x] Không có bất kỳ vật thể động nào được sinh ra trong bán kính $< 2.0\text{ m}$ quanh Robot ở thời điểm $t = 0$ (`Safe Margin Check`).
* [x] Mọi kịch bản sinh ra ở cả 15 Topology đều không bị kẹt Start/Goal trong tường và luôn có đường đi khả thi (`Path Feasibility Check`).

---

### Phase 3: Mô hình Con người, Không gian Xã hội & Context Classifier

**Mục tiêu kiểm thử:** Kiểm chứng mô hình chuyển động Social Force của con người, vùng không gian cá nhân Gaussian bất đối xứng, vùng cấm O-Space của nhóm tương tác và bộ phân loại ngữ cảnh tự động.

**Lệnh chạy:**
```bash
python main.py
```

**Các bước thực hiện:**
1. Bật `Debug Mode` (phím `D`) và quan sát 3 nhóm hành vi của người: `STANDING` (xanh ngọc), `WALKING` (cam), `RUNNING` (đỏ tươi).
2. So sánh hình dạng đường bao elip Gaussian quanh người đang `RUNNING` và người đang `STANDING`.
3. Quan sát nhóm 2–3 người đứng nói chuyện (`INTERACTING`) có vòng tròn đỏ bán trong suốt bao quanh (`O-Space`) và vạch nối giữa các thành viên.
4. Nhấn phím `1` (`Manual`), lái Robot tiến lại gần hoặc cắt ngang mũi di chuyển của một người đang đi bộ để quan sát nhãn ngữ cảnh trên đầu người đó đổi sang `APPROACHING` hoặc `CROSSING`.
5. Lái Robot đi vào vùng elip màu cam của cá nhân hoặc đi xuyên qua vòng tròn đỏ `O-Space` của nhóm người đang nói chuyện, đồng thời quan sát dòng `SOCIAL` trên HUD.

**Tiêu chuẩn nghiệm thu (Pass Criteria):**
* [x] Vùng Gaussian phía trước mặt người giãn dài tỷ lệ thuận với vận tốc ($\sigma_{\text{front}} = 0.8 + 0.5 v_h$).
* [x] Nhãn ngữ cảnh tự động chuyển sang `APPROACHING` khi $d < 5.0\text{ m}$, góc lệch $< 30^\circ$ và chuyển sang `CROSSING` khi quỹ đạo giao nhau có $\vert{}\Delta \tau\vert{} < 1.5\text{ s}$.
* [x] Khi Robot xâm phạm vùng cá nhân, HUD cảnh báo `PERSONAL INTRUSION` với mức phạt từ $-0.5$ đến $-2.0$.
* [x] Khi Robot xâm phạm vòng tròn `O-Space` hoặc cắt ngang nhóm nói chuyện, HUD cảnh báo `O-SPACE / GROUP VIOLATION (-5.0)`.

---

### Phase 4: Path Planning (A* + Sliding Sub-goal) & 2 Rule-based Baselines

**Mục tiêu kiểm thử:** Kiểm tra đường dẫn toàn cục A*, điểm dẫn đường cục bộ trượt theo khoảng cách $L_{\text{lookahead}} = 2.5\text{ m}$ và so sánh hành vi giữa **Baseline 1** (Phím `2`) với **Baseline 2** (Phím `3`).

**Lệnh chạy:**
```bash
python main.py
```

**Các bước thực hiện:**
1. Bật `Debug Mode` (phím `D`): kiểm tra đường gấp khúc màu xanh lá đậm (`Global A* Path`) nối từ Robot tới Goal và chấm tròn màu vàng cam (`Local Sub-goal`) nằm trên đường A* cách Robot $2.5\text{ m}$.
2. Nhấn phím `2` để chạy **Baseline 1 (`A* + Basic Avoidance`)**: quan sát cách đường A* và Robot phản ứng khi gặp nhóm người `INTERACTING` hoặc người cắt ngang.
3. Nhấn phím `R` rồi nhấn phím `3` để chạy **Baseline 2 (`A* + Social Rules`)**: quan sát đường A* tự động vòng qua ngoài vùng `O-Space` và cách Robot chủ động dừng chờ (`WAIT` / `SLOW_DOWN`) khi gặp cửa đang đóng hoặc người đang `CROSSING`.

**Tiêu chuẩn nghiệm thu (Pass Criteria):**
* [x] Đường A* giữ khoảng cách an toàn với mép tường tĩnh nhờ lớp đệm chi phí (`Wall Inflation`), giúp Robot không bị quẹt tường khi rẽ ở góc chữ L hoặc chữ T.
* [x] Điểm `Local Sub-goal` trượt mượt dọc theo đường A* ở khoảng cách $2.5\text{ m}$ phía trước Robot.
* [x] Ở chế độ **Baseline 2 (Phím `3`)**, đường A* tự động bẻ cong tránh vùng `O-Space` và Robot dừng chờ an toàn trước cửa `CLOSED`/`OPENING`.

---

### Phase 5: Môi trường Gymnasium, State 106 chiều & Đa mục tiêu Reward

**Mục tiêu kiểm thử:** Xác nhận lớp `ContextAwareNavEnv` tuân thủ chuẩn API của Gymnasium/Stable-Baselines3, vector quan sát có đúng kích thước $(106,)$ trong hệ tọa độ Robot-centric và hàm phần thưởng tính toán chính xác từng thành phần.

**Lệnh chạy kiểm định tự động:**
```bash
python main.py --check-env
```

**Các bước thực hiện:**
1. Chạy lệnh `python main.py --check-env` trên terminal và kiểm tra kết quả trả về từ `stable_baselines3.common.env_checker.check_env()`.
2. Kiểm tra kích thước của 4 khối trong Vector State $S_t$: Khối Robot & Goal ($6$), Khối LiDAR ($16$), Khối Top-3 Objects ($24$), Khối Top-5 Humans ($60$).
3. Mở giao diện trực quan `python main.py`, quan sát dòng `REWARD` trên HUD khi Robot tiến gần đích (`prog > 0`), khi chờ cửa mở hoặc chờ người cắt ngang (`wait = +0.2`), và khi xâm phạm không gian xã hội.

**Tiêu chuẩn nghiệm thu (Pass Criteria):**
* [x] Lệnh `python main.py --check-env` báo `[OK] Vượt qua bài kiểm tra check_env() của Stable-Baselines3 không lỗi!`.
* [x] Vector quan sát trả về có `shape == (106,)`, `dtype == float32`, không chứa giá trị `NaN` hoặc `Inf`.
* [x] Khi `include_social_context=False` (dùng cho Baseline 3), 6 chiều One-Hot của mỗi người trong Khối 4 đều bằng $0.0$.
* [x] `Smart Wait Bonus (+0.2)` được cộng chính xác khi Robot chọn `WAIT`/`SLOW_DOWN` trước cửa đang mở hoặc người đang `CROSSING`.

---

### Phase 6: Huấn luyện Reinforcement Learning (Baseline 3 & Baseline 4)

**Mục tiêu kiểm thử:** Kiểm tra quy trình huấn luyện mô hình RL (PPO/DQN) trên tập Training Topologies ($1\text{--}9$), lưu checkpoint tự động và nạp lại model để điều khiển trực tiếp qua phím `4` trên Pygame.

**Lệnh chạy huấn luyện thử nghiệm (Smoke Test):**
```bash
python -m rl.train_eval --algo PPO --mode full_context --timesteps 10000
python -m rl.train_eval --algo PPO --mode no_context --timesteps 10000
```

**Các bước thực hiện:**
1. Chạy lệnh huấn luyện ngắn (`10000` timesteps) cho cả 2 chế độ: `no_context` (**Baseline 3**) và `full_context` (**Baseline 4**).
2. Kiểm tra thư mục `models/` xem file trọng số `.zip` và log huấn luyện đã được sinh ra hay chưa.
3. Chạy `python main.py`, nhấn phím `4` (`RL Policy`) để kiểm tra khả năng nạp model đã huấn luyện và suy luận hành động ở tốc độ thời gian thực ($10\text{ Hz}$).

**Tiêu chuẩn nghiệm thu (Pass Criteria):**
* [x] Quá trình huấn luyện chỉ lấy mẫu ngẫu nhiên các Topology thuộc tập Training ($1\text{--}9$).
* [x] Hàm phần thưởng trung bình mỗi episode (`ep_rew_mean`) có xu hướng tăng dần và tỷ lệ va chạm giảm dần theo số bước huấn luyện.
* [x] Khi nhấn phím `4` trong `main.py`, Robot tự động di chuyển về đích dưới sự điều khiển của mạng chính sách RL mà không bị giật khung hình.

---

### Phase 7: Đánh giá Benchmark Toàn diện & Trực quan hóa Kết quả

**Mục tiêu kiểm thử:** Chạy đánh giá định lượng tự động cả **4 Baselines** trên tập **Validation Topologies ($10\text{--}12$)** và **Testing - Unseen Topologies ($13\text{--}15$)**, xuất bảng so sánh các chỉ số (Metrics) và vẽ biểu đồ tổng hợp.

**Lệnh chạy Benchmark & Vẽ biểu đồ:**
```bash
python -m evaluation.benchmark_runner --episodes 50 --split val
python -m evaluation.benchmark_runner --episodes 50 --split test
python -m visualization.plot_results
```

**Các chỉ số bắt buộc kiểm tra trong báo cáo xuất ra:**
1. **Hiệu quả điều hướng:** `Success Rate (%)`, `Navigation Time (s)`, `Path Length (m)`.
2. **Mức độ an toàn:** `Collision Rate (%)`, `Timeout Rate (%)`.
3. **Tuân thủ ngữ cảnh & xã hội:** `Social Space Intrusion Ratio (%)`, `Group Splitting Count`, `Smart Wait Count`.

**Tiêu chuẩn nghiệm thu (Pass Criteria):**
* [x] Script `benchmark_runner.py` chạy hoàn tất trên cả 4 phương pháp (Baseline 1, Baseline 2, Baseline 3, Baseline 4) với cùng tập hạt giống ngẫu nhiên (`seed`) để đảm bảo công bằng.
* [x] Kết quả định lượng thể hiện rõ: **Baseline 4 (`A* + RL Full Context`)** đạt `Social Space Intrusion Ratio` và `Group Splitting Count` thấp hơn rõ rệt so với **Baseline 1** và **Baseline 3**, đồng thời có `Success Rate` trên tập Unseen Topologies ($13\text{--}15$) cao hơn **Baseline 2**.
* [x] Script `plot_results.py` xuất thành công các file ảnh biểu đồ (`.png`) và bảng tổng hợp kết quả (`.csv` / `.md`).

---

## 3. Script Kiểm thử Tự động Nhanh (Smoke Test Suite)

Bạn có thể chạy đoạn lệnh một dòng dưới đây trên terminal để kiểm tra tự động toàn bộ luồng tích hợp từ **Phase 1 đến Phase 5** trong vòng 5 giây:

```bash
python -c "
from environment.topology import TRAIN_TOPOLOGIES, VAL_TOPOLOGIES, TEST_TOPOLOGIES
from rl.gym_env import ContextAwareNavEnv
from behavior.rule_based_agent import RuleBasedAgent
from stable_baselines3.common.env_checker import check_env

env = ContextAwareNavEnv(split='train', include_social_context=True)
check_env(env, warn=True)

for topo_id in range(1, 16):
    obs, info = env.reset(seed=100 + topo_id, options={'topology_id': topo_id})
    assert obs.shape == (106,), f'Sai kich thuoc state tai topology {topo_id}'
    agent = RuleBasedAgent(mode='social')
    for _ in range(15):
        act = int(agent.select_action(env.world))
        obs, rew, term, trunc, info = env.step(act)
        if term or trunc:
            break

env.close()
print('TAT CA 15 TOPOLOGY VA GYM ENV (PHASE 1 -> PHASE 5) DEU PASS 100%!')
"
```