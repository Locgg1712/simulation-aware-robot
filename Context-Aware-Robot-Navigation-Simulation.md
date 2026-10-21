# Context-Aware Robot Navigation Simulation
**(Tài liệu Đặc tả Kỹ thuật & Hướng dẫn Triển khai Hệ thống)**

---

## 1. Tổng quan

- **Tên đề tài (Tiếng Anh):** Context-Aware Robot Navigation Simulation
- **Tên đề tài (Tiếng Việt):** Mô phỏng điều hướng robot theo ngữ cảnh
- **Từ khóa:** `Robot Navigation`, `Context-Aware Navigation`, `Human-Aware Navigation`, `Social Navigation`, `Reinforcement Learning`, `Dynamic Environment`, `Object State`, `Human Behavior`, `2D Simulation`.

### 1.1. Mô tả tóm tắt
Đề tài xây dựng một **môi trường mô phỏng 2D** cho robot tự hành, trong đó robot có khả năng nhận diện và phân loại các đối tượng theo trạng thái **tĩnh (static)**, **bán tĩnh (semi-static)** và **động (dynamic)**, đồng thời nhận biết con người như một nhóm đối tượng đặc biệt cùng các ngữ cảnh như đi bộ, chạy, tiếp cận, cắt ngang và tương tác theo nhóm. Dựa trên thông tin môi trường, robot tính toán đường đi bằng các thuật toán như `A*` (vai trò baseline/global planner) và sử dụng **Reinforcement Learning (RL)** để học chính sách ra quyết định hành vi phù hợp (di chuyển, tránh, giảm tốc, dừng, chờ hoặc đổi hướng) nhằm đảm bảo tính an toàn, hiệu quả và chuẩn mực xã hội.

### 1.2. Tư tưởng cốt lõi
Dự án không đơn thuần giải bài toán:
> *"Có vật cản thì tránh."*

Mà hướng tới chuỗi nhận thức và hành vi hoàn chỉnh:
> **"Robot nhìn thấy gì $\rightarrow$ Vật thể đó đang ở trạng thái nào $\rightarrow$ Con người đang làm gì $\rightarrow$ Ngữ cảnh hiện tại là gì $\rightarrow$ Robot nên ứng xử như thế nào?"**

Trong đó, **RL** là phương pháp học chính sách hành vi cục bộ, còn toàn bộ dự án là một hệ thống mô phỏng khép kín có khả năng hiểu môi trường và ra quyết định.

---

## 2. Mục tiêu dự án

### 2.1. Mục tiêu tổng quát
Xây dựng một simulator 2D hoàn chỉnh (chuẩn hóa theo giao diện `Gymnasium`) cho phép robot tự hành hoạt động trong môi trường đa đối tượng, học cách điều hướng, tránh va chạm và ứng xử phù hợp với ngữ cảnh xã hội của con người.

### 2.2. Các mục tiêu cụ thể
1. Xây dựng môi trường 2D dạng top-down kết hợp **bản đồ lưới (Occupancy Grid)** và **chuyển động liên tục (Continuous Kinematics)**.
2. Xây dựng hệ thống sinh bản đồ và đối tượng ngẫu nhiên có kiểm soát (Procedural Generation) từ 15 mẫu Topology.
3. Mô hình hóa 4 nhóm thực thể: `Static`, `Semi-static`, `Dynamic` và `Human`.
4. Xây dựng máy trạng thái (State Machine) cho các vật thể bán tĩnh (cửa, rào chắn, đèn tín hiệu).
5. Xây dựng mô hình chuyển động và dự đoán quỹ đạo (Trajectory Prediction) cho vật thể động.
6. Xây dựng mô hình hành vi và vùng không gian xã hội (Social Space) của con người.
7. Xây dựng tầng nhận diện ngữ cảnh xã hội cơ bản (Behavior/Context Engine).
8. Xây dựng hệ thống tìm đường toàn cục (`A*`) kết hợp điểm dẫn đường cục bộ (`Local Sub-goal`).
9. Xây dựng môi trường RL với không gian trạng thái lấy robot làm tâm (Robot-centric State Space).
10. Thiết kế hàm phần thưởng (Reward Function) đa mục tiêu: tiến độ, an toàn vật lý và chuẩn mực xã hội.
11. Huấn luyện agent bằng các thuật toán RL (ưu tiên `DQN` cho hành động rời rạc và `PPO` cho mở rộng liên tục).
12. So sánh thực nghiệm giữa RL và các phương pháp truyền thống (`A*` thuần, `A*` + Rules).
13. Đánh giá khả năng tổng quát hóa (Generalization) trên các cấu trúc bản đồ chưa từng xuất hiện khi huấn luyện.

---

## 3. Phạm vi dự án

### 3.1. Trong phạm vi (In-Scope)
- **Môi trường:** Không gian 2D góc nhìn top-down, sinh tự động theo thủ tục (procedural), đa dạng topology, chứa đầy đủ vật thể tĩnh/bán tĩnh/động, cá nhân và nhóm người.
- **Robot:** Mô hình hình tròn có tọa độ $(x, y)$, góc hướng $\theta \in [-\pi, \pi]$, vận tốc dài $v$, vận tốc góc $\omega$, bán kính $R_{\text{robot}}$, điểm đích (Goal) và bán kính cảm biến $R_{\text{sensor}}$.
- **Nhận thức của Robot:** Nhận biết loại đối tượng, vị trí, kích thước, vận tốc, hướng di chuyển, trạng thái vật lý và ngữ cảnh xã hội trong vùng cảm nhận.
- **Quyết định của Robot:** Đi tiếp (`Forward`), rẽ trái (`Turn Left`), rẽ phải (`Turn Right`), giảm tốc (`Slow Down`), dừng (`Stop`), chờ (`Wait`), tránh hoặc đổi đường.

### 3.2. Ngoài trọng tâm (Out-of-Scope / Mở rộng sau)
Các thành phần sau chỉ đóng vai trò mở rộng nếu còn thời gian:
- SLAM 2D/3D đầy đủ từ dữ liệu LiDAR thô.
- Computer Vision / YOLO thời gian thực ngay từ giai đoạn đầu (giai đoạn chính dùng Ground-Truth Perception từ Simulator).
- Phần cứng thực tế (Camera thật, TurtleBot 4) ở giai đoạn cốt lõi.
- Phát minh thuật toán tìm đường `A*` mới hoặc thuật toán tối ưu RL mới.

---

## 4. Kiến trúc hệ thống tổng thể

```text
                     ┌──────────────────────────┐
                     │      2D ENVIRONMENT      │
                     │ (Grid Map + Continuous)  │
                     └────────────┬─────────────┘
                                  │
                                  ↓
                     ┌──────────────────────────┐
                     │    OBJECT PERCEPTION     │
                     │ (Ground-Truth / Sensor)  │
                     └────────────┬─────────────┘
                                  │
                                  ↓
                     ┌──────────────────────────┐
                     │     STATE ESTIMATION     │
                     │  (Robot-Centric Frame)   │
                     └────────────┬─────────────┘
                                  │
                    ┌─────────────┴─────────────┐
                    ↓                           ↓
             Physical State               Human Context
                    │                           │
        ┌───────────┼───────────┐               │
        ↓           ↓           ↓               ↓
     Static    Semi-static   Dynamic        Activity
                                                +
                                          Social Context
                    │                           │
                    └─────────────┬─────────────┘
                                  ↓
                     ┌──────────────────────────┐
                     │   GLOBAL PATH PLANNING   │
                     │  A* -> Local Sub-goal    │
                     └────────────┬─────────────┘
                                  ↓
                     ┌──────────────────────────┐
                     │   BEHAVIOR / RL POLICY   │
                     │    (DQN / PPO Agent)     │
                     └────────────┬─────────────┘
                                  ↓
                     ┌──────────────────────────┐
                     │      ROBOT ACTUATION     │
                     └──────────────────────────┘
```

---

## 5. Cơ chế Vật lý & Không gian (Hướng dẫn triển khai)

Để vừa chạy `A*` nhanh vừa giúp robot và con người di chuyển mượt mà, hệ thống sử dụng **kiến trúc không gian lai (Hybrid Grid-Continuous Space)**:

1. **Hệ tọa độ thực (Continuous World):**
   - Bản đồ có kích thước thực $W \times H$ (ví dụ: $20.0\text{ m} \times 20.0\text{ m}$).
   - Bước thời gian mô phỏng cố định: $\Delta t = 0.1\text{ s}$ ($10\text{ Hz}$).
   - Mọi thực thể (Robot, Dynamic Object, Human) có tọa độ thực $(x, y) \in \mathbb{R}^2$ và cập nhật vị trí theo động học:
     $$x_{t+1} = x_t + v_t \cos(\theta_t) \Delta t$$
     $$y_{t+1} = y_t + v_t \sin(\theta_t) \Delta t$$
     $$\theta_{t+1} = \text{atan2}(\sin(\theta_t + \omega_t \Delta t), \cos(\theta_t + \omega_t \Delta t))$$

2. **Bản đồ lưới nền (Underlying Occupancy Grid):**
   - Chia không gian $W \times H$ thành các ô lưới có độ phân giải $\Delta g = 0.25\text{ m}$ hoặc $0.5\text{ m}$ (tạo ma trận $80 \times 80$ hoặc $40 \times 40$).
   - Lưới này chỉ đánh dấu `Static Objects` và trạng thái hiện tại của `Semi-static Objects` (ví dụ cửa đang đóng = vật cản, cửa mở = ô trống) để thuật toán `A*` tìm đường cực nhanh.

---

## 6. Phân loại và Mô hình hóa Đối tượng

### 6.1. Static Object (Vật thể tĩnh)
- **Đặc điểm:** Vị trí cố định, vận tốc bằng $0$, trạng thái không đổi trong suốt episode.
- **Ví dụ:** Tường, nhà, cây, đá, cột, hồ nước, chướng ngại vật cố định.
- **Mô hình dữ liệu:**
  - Vị trí $(x, y) = \text{const}$, vận tốc $v = 0$.
  - Hình học: Hình chữ nhật `BoundingBox(x, y, w, h)` (cho tường/cửa) hoặc hình tròn `Circle(x, y, r)` (cho cột/cây).
- **Ứng xử của Robot:** Coi là vùng cấm tuyệt đối (impassable region).

### 6.2. Semi-static Object (Vật thể bán tĩnh)
- **Đặc điểm:** Vị trí cố định nhưng **trạng thái thông hành thay đổi theo thời gian** (Finite State Machine - FSM).
- **Ví dụ:** Cửa tự động (Đóng $\leftrightarrow$ Mở), thanh chắn barrier (Hạ $\leftrightarrow$ Nâng), đèn giao thông nội bộ (Đỏ $\leftrightarrow$ Xanh).
- **Mô hình Máy trạng thái (ví dụ Cửa tự động):**
  ```text
  CLOSED (Không thể đi qua)
     ↓ (timer / trigger)
  OPENING (Đang mở - Chưa an toàn)
     ↓
  OPEN (Có thể đi qua)
     ↓
  CLOSING (Đang đóng - Nguy hiểm)
     ↓
  CLOSED
  ```
- **Thuộc tính cần cấp cho Robot:** `state` $\in \{\text{OPEN}, \text{OPENING}, \text{CLOSED}, \text{CLOSING}\}$, và `passable` $\in \{\text{True}, \text{False}\}$.
- **Ứng xử của Robot:** Quyết định `WAIT` nếu thời gian chờ dự kiến ngắn hơn việc đi đường vòng, hoặc `REROUTE` nếu cửa khóa/đóng quá lâu (`WAIT timeout`).

### 6.3. Dynamic Object (Vật thể động thông thường)
- **Đặc điểm:** Có chuyển động đáng kể nhưng không mang ngữ cảnh xã hội phức tạp như con người.
- **Ví dụ:** Xe đẩy hàng tự động, robot khác, vật nuôi/động vật.
- **Thông tin theo dõi & Dự đoán:**
  - Trạng thái hiện tại: Vị trí $(x_t, y_t)$, vận tốc $v_t$, góc hướng $\theta_t$.
  - **Dự đoán quỹ đạo (Trajectory Prediction):** Giả định vận tốc không đổi trong ngắn hạn $T_{\text{pred}} \in [1.0\text{ s}, 3.0\text{ s}]$, vị trí dự đoán ở bước tương lai $k \cdot \Delta t$ là:
    $$\hat{x}_{t+k} = x_t + v_t \cos(\theta_t) (k \Delta t), \quad \hat{y}_{t+k} = y_t + v_t \sin(\theta_t) (k \Delta t)$$

---

## 7. Mô hình Con người (Human Model) & Ngữ cảnh Xã hội

Con người **không** được coi là một `Dynamic Obstacle` thuần túy mà được biểu diễn bởi cấu trúc 3 tầng:

```text
Human Entity
│
├── 1. Physical State
│   ├── Position (x, y)
│   ├── Velocity (v_x, v_y) & Speed ||v||
│   ├── Orientation (θ)
│   └── Radius (r_human ≈ 0.3m)
│
├── 2. Activity (Hành vi cá nhân)
│   ├── STANDING  (v ≈ 0 m/s)
│   ├── WALKING   (v ≈ 0.8 – 1.4 m/s)
│   └── RUNNING   (v ≈ 2.0 – 3.0 m/s)
│
└── 3. Social Context (Ngữ cảnh tương tác với Robot & Người khác)
    ├── ALONE        (Đi/đứng độc lập)
    ├── APPROACHING  (Đang tiến về phía robot)
    ├── CROSSING     (Đang cắt ngang mũi di chuyển của robot)
    ├── GROUP        (Di chuyển cùng nhau thành nhóm)
    └── INTERACTING  (Đang đứng nói chuyện/tương tác với nhau)
```

### 7.1. Quy tắc toán học tự động gán nhãn Ngữ cảnh (Context Classifier)
Trong `Behavior Engine`, mỗi bước thời gian $\Delta t$, hệ thống tự động suy luận nhãn ngữ cảnh của từng người đối với Robot dựa trên hình học:
- **`APPROACHING`:** Khoảng cách tới robot $d < 5.0\text{ m}$, người đang di chuyển ($v_{\text{human}} > 0.2\text{ m/s}$) và vector vận tốc của người hướng ngược về phía vị trí robot (tích vô hướng $\vec{v}_{\text{human}} \cdot (\vec{p}_{\text{robot}} - \vec{p}_{\text{human}}) > 0$ với góc lệch $< 30^\circ$).
- **`CROSSING`:** Quỹ đạo dự đoán trong $3.0\text{ s}$ tới của người và vector hướng đi của robot cắt nhau tại một điểm giao có khoảng cách thời gian đến điểm giao $\Delta \tau = |t_{\text{robot}} - t_{\text{human}}| < 1.5\text{ s}$.
- **`INTERACTING`:** $2$ đến $4$ người ở trạng thái `STANDING`, khoảng cách giữa họ $d_{ij} \in [0.8\text{ m}, 2.0\text{ m}]$, và góc nhìn $\theta$ của họ hướng vào tâm chung của nhóm.
- **`GROUP`:** $\ge 2$ người cùng di chuyển với khoảng cách $d_{ij} < 1.5\text{ m}$ và độ lệch hướng $|\theta_i - \theta_j| < 25^\circ$.

### 7.2. Mô hình Không gian Xã hội (Social Space Modeling)
Để robot biết giữ khoảng cách lịch sự và không cắt ngang nhóm người, hệ thống định nghĩa hàm chi phí không gian xã hội $C_{\text{social}}(x, y)$:

1. **Không gian cá nhân (Individual Personal Space):**
   Sử dụng hàm Gaussian 2D bất đối xứng quanh vị trí người $(x_h, y_h)$, kéo dài về phía trước hướng di chuyển $\theta_h$ theo vận tốc $v_h$:
   - Độ lệch chuẩn phía trước: $\sigma_{\text{front}} = \sigma_0 + k_v \cdot v_h$ (với $\sigma_0 = 0.8\text{ m}, k_v = 0.5\text{ s}$ — người chạy cần khoảng trống phía trước lớn hơn người đi bộ).
   - Độ lệch chuẩn phía sau và hai bên: $\sigma_{\text{rear}} = 0.5\text{ m}$, $\sigma_{\text{side}} = 0.6\text{ m}$.
   - Khi khoảng cách từ robot đến người rơi vào vùng $C_{\text{social}} > \text{threshold}$, robot nhận phạt `Social Violation Penalty`.

2. **Không gian tương tác nhóm (Group O-Space):**
   - Khi một nhóm $M$ người đang `INTERACTING` hoặc đi theo `GROUP`, tâm nhóm được tính bằng:
     $$C_x = \frac{1}{M}\sum_{i=1}^M x_i, \quad C_y = \frac{1}{M}\sum_{i=1}^M y_i$$
   - Bán kính vùng cấm xã hội của nhóm:
     $$R_{\text{group}} = \max_{i} \sqrt{(x_i - C_x)^2 + (y_i - C_y)^2} + d_{\text{margin}}$$
   - Nếu robot đi vào hình tròn tâm $(C_x, C_y)$ bán kính $R_{\text{group}}$ (đặc biệt là đi xuyên qua đoạn thẳng nối hai người đang nói chuyện), robot bị phạt nặng (`Group Splitting / Crossing Penalty`).

### 7.3. Chuyển động của Con người trong Simulator
Để tránh việc con người trong simulator đi xuyên tường hoặc đi đâm vào nhau:
- Mỗi người (hoặc nhóm người) được gán một danh sách điểm đến (`waypoints`) sinh ngẫu nhiên trên vùng trống.
- Áp dụng **Social Force Model rút gọn**: Vận tốc thực tế của người là tổng hợp của lực hút về waypoint của họ và lực đẩy nhẹ khi gần tường hoặc gần người khác.

---

## 8. Kết nối Path Planning (`A*`) và Reinforcement Learning

Một vấn đề phổ biến khi dùng RL trên bản đồ nhiều phòng/hành lang là nếu chỉ truyền hướng tới đích cuối (Global Goal), robot sẽ đâm vào tường cụt. Giải pháp chuẩn trong dự án này là cơ chế **Sliding Local Sub-goal (Điểm dẫn đường cục bộ trượt dọc đường A*)**:

```text
Global Goal (🎯)
     ↑
A* Planner (chạy trên lưới Static + Semi-static đóng)
     ↑
Global Path: [p_0, p_1, p_2, ..., p_k, ..., p_N]
     ↑
Trích xuất Local Sub-goal (điểm p_k cách Robot khoảng L = 2.5m)
     ↑
Truyền (distance_to_subgoal, angle_to_subgoal) vào RL State
```

- **Vai trò của `A*`:** Tìm chuỗi các ô lưới nối từ vị trí Robot đến `Goal` mà không va chạm tường tĩnh. Khi gặp `Semi-static Object` (như cửa đóng nhưng có thể mở), `A*` gán trọng số chi phí đi qua ô cửa cao hơn bình thường một chút nhưng vẫn cho phép đi qua để robot biết tiến lại gần cửa.
- **Vai trò của `Local Sub-goal`:** Ở mỗi bước, lấy điểm nằm trên đường `A*` cách robot một khoảng nhìn trước $L_{\text{lookahead}} = 2.5\text{ m}$.
- **Vai trò của `RL Policy`:** Quan sát `Local Sub-goal` kết hợp với các đối tượng động và con người xung quanh để quyết định hành động tức thời (đi bám theo sub-goal, vòng tránh nhóm người rồi quay lại đường A*, hoặc dừng chờ cửa mở/người chạy qua).

---

## 9. Thiết kế Reinforcement Learning (Gymnasium Standard)

### 9.1. Không gian Trạng thái (State Space - Robot-Centric)
Toàn bộ thông tin đầu vào của mạng Neural (DQN/PPO) được quy về **hệ tọa độ cục bộ lấy Robot làm tâm và hướng mũi Robot làm trục chuẩn** để đảm bảo tính bất biến không gian (giúp generalize sang bản đồ mới).

Vector trạng thái $S_t$ có kích thước cố định, bao gồm 3 khối:

1. **Trạng thái bản thân Robot & Mục tiêu ($\mathbb{R}^6$):**
   - $d_{\text{subgoal}} / D_{\text{max}}$: Khoảng cách tới `Local Sub-goal` (chuẩn hóa về $[0, 1]$).
   - $\sin(\Delta \theta_{\text{subgoal}}), \cos(\Delta \theta_{\text{subgoal}})$: Góc lệch từ hướng mũi robot tới `Local Sub-goal`.
   - $d_{\text{goal}} / D_{\text{max}}$: Khoảng cách tới đích cuối.
   - $v_t / v_{\text{max}}, \omega_t / \omega_{\text{max}}$: Vận tốc dài và vận tốc góc hiện tại của robot.

2. **Cảm biến chướng ngại vật tĩnh cục bộ ($\mathbb{R}^{16}$):**
   - $16$ tia Raycast (tương tự LiDAR 2D nhẹ) quét $360^\circ$ quanh robot trong bán kính $R_{\text{sensor}} = 6.0\text{ m}$ để nhận diện khoảng cách tới tường và vật cản tĩnh gần nhất.

3. **Top-$K$ Đối tượng Bán tĩnh / Động & Top-$M$ Con người gần nhất:**
   - Chọn $K = 3$ vật thể (`Semi-static` / `Dynamic`) và $M = 5$ con người (`Human`) có mức độ rủi ro/khoảng cách gần robot nhất trong bán kính $R_{\text{sensor}}$. Nếu thực tế có ít hơn $K$ hoặc $M$ đối tượng, điền giá trị $0$ (**Zero-Padding**).
   - Mỗi vật thể thứ $i \in \{1..K\}$ biểu diễn bởi vector ($\mathbb{R}^8$):
     $$[\Delta x_i, \Delta y_i, \Delta v_{xi}, \Delta v_{yi}, r_i, \text{is\_semi\_static}, \text{is\_dynamic}, \text{is\_passable}]$$
   - Mỗi con người thứ $j \in \{1..M\}$ biểu diễn bởi vector ($\mathbb{R}^{12}$):
     $$[\Delta x_j, \Delta y_j, \Delta v_{xj}, \Delta v_{yj}, \sin(\Delta \theta_j), \cos(\Delta \theta_j), \text{OneHot(Activity)}_3, \text{OneHot(Context)}_3]$$
     *(Trong đó $(\Delta x, \Delta y)$ và $(\Delta v_x, \Delta v_y)$ đều đã xoay theo góc $\theta_{\text{robot}}$)*.

$\Rightarrow$ Tổng số chiều của vector State $S_t$: $6 + 16 + (3 \times 8) + (5 \times 12) = 106$ chiều (cực kỳ nhẹ, huấn luyện bằng MLP trên CPU/GPU rất nhanh).

### 9.2. Không gian Hành động (Action Space)
- **Giai đoạn chính (Discrete Action Space - `gym.spaces.Discrete(6)`):**
  - `0 = FORWARD`: Đặt $v = v_{\text{max}} \ (1.0\text{ m/s})$, $\omega = 0$.
  - `1 = TURN_LEFT`: Đặt $v = 0.5\text{ m/s}$, $\omega = +\pi/3\text{ rad/s}$.
  - `2 = TURN_RIGHT`: Đặt $v = 0.5\text{ m/s}$, $\omega = -\pi/3\text{ rad/s}$.
  - `3 = SLOW_DOWN`: Đặt $v = 0.3\text{ m/s}$, $\omega = 0$.
  - `4 = STOP`: Đặt $v = 0\text{ m/s}$, $\omega = 0$ (phanh khẩn cấp tránh va chạm).
  - `5 = WAIT`: Đặt $v = 0\text{ m/s}$, $\omega = 0$ (chờ có chủ đích trước cửa đang đóng hoặc người đang cắt ngang).
- **Giai đoạn mở rộng (Continuous Action Space - `gym.spaces.Box`):**
  - Điều khiển trực tiếp $(v, \omega) \in [0, v_{\text{max}}] \times [-\omega_{\text{max}}, \omega_{\text{max}}]$.

### 9.3. Thiết kế Hàm Phần thưởng (Reward Function)
Hàm phần thưởng tại mỗi bước thời gian $t$ là tổng có trọng số của các thành phần:
$$R_t = R_{\text{terminal}} + R_{\text{progress}} + R_{\text{time}} + R_{\text{social}} + R_{\text{context}}$$

| Thành phần | Công thức / Điều kiện | Giá trị khuyến nghị | Ý nghĩa huấn luyện |
| :--- | :--- | :---: | :--- |
| **Goal Reward** | $d_{\text{goal}} < R_{\text{robot}} + R_{\text{goal}}$ | $+100.0$ | Hoàn thành nhiệm vụ (Kết thúc episode). |
| **Collision Penalty** | Va chạm tường, vật thể, cửa đóng hoặc người | $-100.0$ | Đảm bảo an toàn tuyệt đối (Kết thúc episode). |
| **Progress Reward** | $w_p \cdot (d_{\text{subgoal}}^{(t-1)} - d_{\text{subgoal}}^{(t)})$ | $w_p = +2.5$ | Khuyến khích robot tiến dọc theo đường dẫn `A*`. |
| **Time Penalty** | Phạt cố định mỗi bước $\Delta t$ | $-0.05$ | Tránh robot đứng yên vô lý hoặc đi lòng vòng. |
| **Social Space Penalty** | Xâm nhập vùng Gaussian của từng người | $-0.5 \sim -2.0$ | Giữ khoảng cách lịch sự (nhiều hơn khi người chạy). |
| **Group Splitting Penalty** | Đi xuyên qua O-Space của nhóm `INTERACTING` | $-5.0$ / bước | Tuyệt đối không cắt ngang giữa 2 người đang nói chuyện. |
| **Smart Wait Bonus** | Chọn `WAIT`/`SLOW_DOWN` khi có `CROSSING` hoặc cửa `OPENING` | $+0.2$ / bước | Khuyến khích hành vi nhường đường và chờ cửa mở hợp lý. |

### 9.4. Lựa chọn Thuật toán RL
Do không gian trạng thái có các biến liên tục ($106$ chiều):
1. **Baseline RL 1 — `DQN` (Deep Q-Network):** Phù hợp hoàn hảo với `Discrete(6)` Action Space, dễ huấn luyện và hội tụ nhanh.
2. **Baseline RL 2 — `PPO` (Proximal Policy Optimization):** Ứng viên chính của dự án, hoạt động cực kỳ ổn định khi môi trường có tính ngẫu nhiên cao (Procedural Generation) và dùng được cho cả Discrete lẫn Continuous Action Space.

---

## 10. Sinh Bản đồ Ngẫu nhiên (Procedural Map Generation) & Phân tập Dữ liệu

Để chứng minh robot **hiểu ngữ cảnh** chứ không **học thuộc lòng bản đồ**, hệ thống sử dụng 15 Topology Templates chia thành 3 tập độc lập:

### 10.1. Phân chia 15 Topology Templates
- **Tập Training (Topology 1 – 9):**
  1. `Open Area`: Khu vực mở có vật cản tĩnh rải rác.
  2. `Straight Corridor`: Hành lang thẳng có người đi ngược chiều.
  3. `Narrow Passage`: Lối đi hẹp chỉ vừa 1 đối tượng đi qua (buộc phải nhường đường).
  4. `L-Corner`: Góc khuất chữ L.
  5. `T-Junction`: Ngã ba hành lang.
  6. `Cross Intersection`: Ngã tư giao cắt (nhiều tình huống `CROSSING`).
  7. `Single Door Room`: Đi từ phòng ra hành lang qua 1 cửa bán tĩnh (`Semi-static Door`).
  8. `Two-Room Connected`: Hai phòng nối nhau có nhóm người nói chuyện.
  9. `Pillar Hall`: Sảnh nhiều cột lớn và nhóm người di chuyển.
- **Tập Validation (Topology 10 – 12):**
  10. `Double Bottleneck`: Hai nút thắt cổ chai liên tiếp có cửa tự động.
  11. `Three-Room Office`: Bố cục văn phòng 3 phòng + hành lang chữ T.
  12. `Courtyard with Dynamic Lanes`: Sân chung có luồng vật thể động chạy cắt ngang liên tục.
- **Tập Testing — Unseen Topologies (Topology 13 – 15):**
  13. `H-Shaped Complex`: Hành lang hình chữ H có nhiều nhánh rẽ thay thế (kiểm tra khả năng `REROUTE` khi cửa khóa hoặc có đám đông chắn lối).
  14. `Multi-Room Maze-like`: Cấu trúc 4–5 phòng liên thông.
  15. `Crowded Plaza & Gates`: Kết hợp sảnh đông nhóm người tương tác, người chạy và nhiều cổng bán tĩnh.

### 10.2. Quy trình kiểm tra của `Spawn Manager`
Trước khi bắt đầu mỗi Episode, `Spawn Manager` thực hiện kiểm tra 4 bước:
1. **Collision Check:** Đối tượng sinh ra không đè lên tường hoặc đè lên nhau.
2. **Safe Margin Check:** Không sinh vật cản động hoặc người nằm trong bán kính $2.0\text{ m}$ quanh vị trí xuất phát của Robot để tránh va chạm tức thời ở $t = 0$.
3. **Path Feasibility Check:** Chạy thử `A*` trên bản đồ tĩnh (coi các cửa bán tĩnh là có thể mở) từ `Start` đến `Goal`. Nếu không tồn tại đường đi hợp lệ $\rightarrow$ Hủy và sinh lại (`Retry`).

---

## 11. Kiến trúc Thư mục Dự án Chuẩn

```text
context_aware_robot/
│
├── configs/
│   ├── default_config.yaml      # Tham số vật lý, kích thước bản đồ, sensor
│   └── rl_hyperparams.yaml      # Tham số huấn luyện DQN / PPO, trọng số Reward
│
├── environment/
│   ├── __init__.py
│   ├── world.py                 # Quản lý vòng lặp thời gian thực & Grid nền
│   ├── topology.py              # Định nghĩa 15 Topology Templates (1-9, 10-12, 13-15)
│   ├── map_generator.py         # Biến thể hóa kích thước phòng, vị trí tường/cửa
│   ├── spawn_manager.py         # Sinh Robot, Goal, Objects, Humans & kiểm tra A*
│   └── physics.py               # Động học 2D, kiểm tra va chạm Hình tròn - Hình chữ nhật
│
├── objects/
│   ├── __init__.py
│   ├── base_object.py           # Lớp cơ sở (id, x, y, radius, type)
│   ├── static_object.py         # Tường, cột, cây, vật cản cố định
│   ├── semi_static_object.py    # Cửa tự động, barrier (kèm FSM chuyển trạng thái)
│   ├── dynamic_object.py        # Vật thể chuyển động + hàm dự đoán quỹ đạo
│   └── robot.py                 # Trạng thái và động học của Robot
│
├── human/
│   ├── __init__.py
│   ├── human_agent.py           # Lớp con người (Physical + Activity + Social Context)
│   ├── motion_model.py          # Di chuyển theo Waypoint + Social Force tránh va chạm
│   ├── groups.py                # Quản lý nhóm đi chung và nhóm đứng tương tác (O-Space)
│   └── social_space.py          # Tính toán hàm Gaussian bất đối xứng & vi phạm xã hội
│
├── perception/
│   ├── __init__.py
│   ├── ground_truth.py          # Trích xuất đối tượng trong bán kính R_sensor + Raycast
│   └── trajectory_predictor.py  # Dự đoán vị trí tương lai trong 1–3 giây
│
├── planning/
│   ├── __init__.py
│   ├── astar.py                 # Tìm đường toàn cục trên Occupancy Grid
│   └── subgoal_selector.py      # Trích xuất Local Sub-goal trượt dọc đường A*
│
├── behavior/
│   ├── __init__.py
│   ├── context_classifier.py    # Phân loại ALONE, APPROACHING, CROSSING, INTERACTING
│   └── rule_based_agent.py      # Baseline 1 & 2 (A* + Collision Avoidance / Social Rules)
│
├── rl/
│   ├── __init__.py
│   ├── gym_env.py               # Lớp bọc chuẩn Gymnasium (reset, step, render)
│   ├── state_builder.py         # Chuyển đổi sang Robot-centric frame (106 chiều)
│   ├── reward_calculator.py     # Tính toán chi tiết từng thành phần Reward
│   └── train_eval.py            # Script huấn luyện và lưu model với Stable-Baselines3
│
├── evaluation/
│   ├── __init__.py
│   ├── metrics.py               # Tính Navigation, Safety, Social, Generalization metrics
│   └── benchmark_runner.py      # Chạy tự động 4 Baselines trên tập Validation & Test
│
├── visualization/
│   ├── __init__.py
│   ├── pygame_renderer.py       # Vẽ Normal Mode & Debug Mode (Vector, O-Space, Path)
│   └── plot_results.py          # Vẽ biểu đồ Learning Curve và bảng so sánh Metrics
│
└── main.py                      # Điểm chạy chính (chọn chế độ: manual, rule, train, eval)
```

---

## 12. Lộ trình Triển khai Chi tiết (Implementation Roadmap)

Để quá trình viết code trơn tru và kiểm thử được ngay sau mỗi bước, dự án được chia làm **7 Phase cốt lõi** (và 2 Phase mở rộng):

### Phase 1: Simulator cơ bản & Vật lý 2D (`environment/`, `objects/robot.py`, `visualization/`)
- **Công việc:**
  - Cài đặt `World`, `Robot`, `Goal`, và `StaticObject` (tường bao, chướng ngại vật).
  - Cài đặt kiểm tra va chạm hình học (Circle-Circle và Circle-Rectangle).
  - Xây dựng giao diện `PygameRenderer` cho phép điều khiển Robot bằng bàn phím để test vật lý.
- **Tiêu chuẩn hoàn thành:** Mở cửa sổ Pygame, điều khiển robot đi tới Goal, đâm vào tường báo va chạm.

### Phase 2: Hệ thống Đối tượng & Bản đồ Procedural (`topology.py`, `semi_static_object.py`, `dynamic_object.py`)
- **Công việc:**
  - Cài đặt `SemiStaticObject` (Cửa đóng/mở theo chu kỳ thời gian) và `DynamicObject`.
  - Cài đặt 15 `Topology` và `SpawnManager` để mỗi lần nhấn `Reset` tạo ra một bản đồ mới.
- **Tiêu chuẩn hoàn thành:** Bản đồ tự sinh ngẫu nhiên, cửa tự đóng/mở, vật thể động di chuyển mượt mà.

### Phase 3: Mô hình Con người & Không gian Xã hội (`human/`, `behavior/context_classifier.py`)
- **Công việc:**
  - Cài đặt `HumanAgent` với các hành vi `STANDING`, `WALKING`, `RUNNING` và nhóm `GROUP`, `INTERACTING`.
  - Cài đặt bộ phân loại ngữ cảnh tự động (`APPROACHING`, `CROSSING`) và hàm tính vùng `SocialSpace` (Gaussian + O-Space).
  - Bổ sung **Debug Mode** trên Pygame: Bấm phím `D` để bật/tắt hiển thị vòng tròn Social Space, O-Space của nhóm người, vector vận tốc và quỹ đạo dự đoán chấm bi.
- **Tiêu chuẩn hoàn thành:** Quan sát trực quan trên Pygame thấy vùng không gian xã hội biến đổi theo tốc độ người đi/chạy và bao quanh nhóm người nói chuyện.

### Phase 4: Path Planning (`A*`) & Baseline Truyền thống (`planning/`, `behavior/rule_based_agent.py`)
- **Công việc:**
  - Cài đặt `A*` trên lưới nền và bộ trích xuất `Local Sub-goal`.
  - Xây dựng **Baseline 1** (`A*` + tránh vật cản cơ bản) và **Baseline 2** (`A*` + tập luật xã hội cứng: dừng khi có người cắt ngang, đi vòng qua O-Space).
- **Tiêu chuẩn hoàn thành:** Robot tự động đi từ Start đến Goal theo đường `A*` mà không cần người điều khiển.

### Phase 5: Môi trường Gymnasium, State & Reward (`rl/gym_env.py`, `state_builder.py`, `reward_calculator.py`)
- **Công việc:**
  - Đóng gói toàn bộ Simulator thành lớp `ContextAwareNavEnv(gym.Env)`.
  - Viết hàm chuyển đổi tọa độ sang hệ quy chiếu Robot-centric ($106$ chiều) và hàm tính `Reward`.
  - Dùng công cụ `check_env()` của `Stable-Baselines3` để kiểm tra tính chuẩn xác của môi trường.
- **Tiêu chuẩn hoàn thành:** Vượt qua bài kiểm tra `check_env()` không lỗi, kiểm tra giá trị Reward in ra màn hình khớp với tình huống thực tế.

### Phase 6: Huấn luyện RL (`rl/train_eval.py`)
- **Công việc:**
  - Huấn luyện **Baseline 3** (RL thuần: tắt thông tin ngữ cảnh xã hội trong State) và **Baseline 4** (RL + Full Context).
  - Lưu log quá trình huấn luyện vào `TensorBoard` để theo dõi `Episode Reward`, `Success Rate`, và `Collision Rate`.
- **Tiêu chuẩn hoàn thành:** Agent hội tụ, biết tự đi vòng qua nhóm người nói chuyện, biết chờ cửa mở và nhường đường cho người chạy cắt ngang.

### Phase 7: Đánh giá Thực nghiệm & Xuất Báo cáo (`evaluation/`)
- **Công việc:**
  - Chạy kịch bản Benchmark cố định $N = 200$ episodes trên tập Validation (Topology 10–12) và tập Testing (Topology 13–15) cho cả 4 Baselines:
    1. **Baseline 1:** `A*` + Basic Collision Avoidance.
    2. **Baseline 2:** `A*` + Handcrafted Social Rules.
    3. **Baseline 3:** `RL` (No Social/Activity Context).
    4. **Baseline 4:** `RL + Context` (Proposed Method).
  - Thu thập 4 nhóm chỉ số:
    - **Navigation:** Success Rate (%), Path Length (m), Time to Goal (s), Average Reward.
    - **Safety:** Collision Rate (%), Minimum Obstacle Distance (m), Near-Collision Rate (%).
    - **Social:** Social Space Intrusion Rate (%), Group Splitting Rate (%), Unnecessary Stops.
    - **Generalization:** Độ sụt giảm hiệu năng trên Topology 13–15 chưa từng thấy.

*(Phase 8 — Tích hợp YOLO/Tracking và Phase 9 — Kết nối ROS2/TurtleBot 4 sẽ được phát triển mở rộng sau khi hoàn tất 7 Phase cốt lõi).*

---

## 13. Chế độ Hiển thị Trực quan (Visualization & Debug Mode)

Giao diện Pygame hỗ trợ chuyển đổi linh hoạt bằng phím tắt trong lúc chạy mô phỏng:

| Phím tắt | Chức năng | Chi tiết hiển thị |
| :---: | :--- | :--- |
| `SPACE` | Pause / Resume | Tạm dừng mô phỏng để quan sát trạng thái tại một thời điểm. |
| `D` | Toggle Debug Mode | Bật/tắt toàn bộ lớp phủ thông tin kỹ thuật (Trajectory, Social Space, Raycast, Sub-goal). |
| `R` | Reset Episode | Sinh ngẫu nhiên một bản đồ và kịch bản mới ngay lập tức. |
| `1 - 4` | Switch Agent Mode | Chuyển đổi trực tiếp giữa: `1: Manual`, `2: A* Basic`, `3: A* Social Rules`, `4: RL Policy`. |

---

## 14. Các Giả thuyết Khoa học Cần Chứng minh (Research Hypotheses)

Toàn bộ kết quả thực nghiệm ở Phase 7 nhằm trả lời và kiểm chứng 4 giả thuyết:
- **H1 (Object State):** Robot được cung cấp trạng thái của vật thể bán tĩnh (`OPEN/CLOSED/OPENING`) và vận tốc vật thể động sẽ có tỷ lệ thành công và thời gian hoàn thành tốt hơn robot chỉ dùng khoảng cách thuần túy.
- **H2 (Human & Social Context):** Việc đưa `Activity` và `Social Context` vào State cùng `Social Penalty` trong Reward giúp giảm mạnh tỷ lệ cắt ngang nhóm người (`Group Splitting Rate`) và xâm phạm không gian cá nhân so với RL thông thường.
- **H3 (Procedural Generalization):** Huấn luyện trên 9 Topology ngẫu nhiên hóa giúp chính sách RL giữ được tỷ lệ thành công cao khi kiểm thử trên 3 Topology hoàn toàn mới (Topology 13–15).
- **H4 (Complementarity):** `A*` thuần đạt hiệu quả tối ưu trong môi trường tĩnh hoàn toàn, nhưng `RL + Context` vượt trội về độ an toàn và tính chuẩn mực xã hội trong môi trường động có mật độ tương tác con người cao.