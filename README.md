# Context-Aware Robot Navigation Simulation & FarmBot Town

Dự án tích hợp 2 chế độ: Mô phỏng nghiên cứu điều hướng Robot tự hành nhận biết ngữ cảnh vật lý & xã hội (Social Navigation RL) và Trò chơi nhập vai hoàn chỉnh phong cách Stardew Valley (**FarmBot Town: Robot Nông Trại Tốt Bụng**).

---

## 🎮 Hướng Dẫn Khởi Chạy 2 Chế Độ (How to Run)

Dự án hỗ trợ chạy song song 2 chế độ độc lập tùy theo mục đích nghiên cứu học thuật hoặc trải nghiệm gameplay:

### Chế độ 1: Trò chơi Hoàn chỉnh — FarmBot Town: Robot Nông Trại Tốt Bụng
Trải nghiệm game nhập vai 2D Top-Down phong cách Stardew Valley với thế giới 5 Bản đồ liên thông, chu kỳ Ngày - Đêm, Thời tiết, 4 Mùa, 12 NPC có biểu cảm & lịch trình sống, Mini-game Câu cá, Xưởng mộc Robin, và 7 Sự kiện Ngẫu nhiên Biến động Thế giới.

```bash
# Khởi chạy trò chơi FarmBot Town (chọn 1 trong 2 lệnh)
python -m game
# hoặc
python stardew_game.py
```

* **Phím điều khiển chính:** `W/A/S/D` (di chuyển), `Shift/X` (đi chậm an toàn), `Space` (phanh/câu cá), `E` (tương tác/nhận đơn/hái quả), `G` (tặng quà NPC), `J` (Sổ tay thị trấn 3 Tab), `U` (Xưởng Robin), `O` (Sự kiện ngẫu nhiên), `P` (bật AI Tự Hành Autopilot).
* Chi tiết đặc tả thiết kế & bảng phím tắt: xem tại [`Context_game_farmbot.md`](Context_game_farmbot.md).

---

### Chế độ 2: Môi trường Nghiên cứu & Huấn luyện — RL Navigation Simulator
Môi trường giả lập huấn luyện học tăng cường (Reinforcement Learning) cho Robot di chuyển tự hành trong không gian đông người, nhận biết ngữ cảnh vật lý, vùng không gian cá nhân (Gaussian Personal Space) và vùng tương tác nhóm (Social O-Space).

```bash
# Khởi chạy Simulator nghiên cứu & huấn luyện RL
python main.py
```

---

## 📌 Lộ Trình Nghiên Cứu RL (RL Simulation Roadmap)
- **Phase 1:** Simulator cơ bản & Vật lý 2D (Hoàn thành)
- **Phase 2:** Hệ thống Đối tượng Bán tĩnh, Động & 15 Topology Procedural
- **Phase 3:** Mô hình Con người & Không gian Xã hội (Gaussian + O-Space)
- **Phase 4:** Path Planning (A* + Local Sub-goal) & Rule-based Baselines
- **Phase 5:** Môi trường Gymnasium (106-dim Robot-Centric State & Multi-objective Reward)
- **Phase 6:** Huấn luyện DQN / PPO
- **Phase 7:** Đánh giá Benchmark trên 4 Baselines
