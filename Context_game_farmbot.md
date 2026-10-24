# ĐẶC TẢ THIẾT KẾ GAME: FARMBOT TOWN – ROBOT NÔNG TRẠI & THỊ TRẤN
**(Game Design & Technical Specification Document)**

---

## 1. Tổng quan Game (Game Overview)
* **Tên dự án:** *FarmBot Town: Robot Nông Trại Tốt Bụng*
* **Thể loại:** 2D Top-Down Cozy RPG / Helper & Delivery Simulation / Safe Human-Robot Interaction.
* **Phong cách đồ họa:** 16-bit Pixel-Art lấy cảm hứng từ *Stardew Valley* (thảm cỏ đa sắc độ, đường đá cuội, cây hoa anh đào, nhà mái ngói có chiều sâu Y-Sorting, nhân vật Robot trợ lý đáng yêu và dân làng có biểu cảm).
* **Ý tưởng cốt lõi:** Người chơi (hoặc AI Agent trong chế độ Simulation) hóa thân thành một chú Robot phục vụ sống tại một thị trấn nông trại. Hàng ngày, Robot di chuyển qua các bản đồ để nhận nhiệm vụ từ cư dân (thu hoạch trái cây, câu cá, chuyển phát vật phẩm), đi vào tận trong các căn nhà để giao đồ và tuân thủ nghiêm ngặt quy tắc an toàn – lịch sự khi tiếp xúc với con người.

---

## 2. Thiết kế Thế giới & Kiến trúc 5 Bản đồ Liên thông (Multi-Map System)

Thế giới game bao gồm **4 Bản đồ Ngoài trời (Outdoor Maps)** kết nối với nhau qua các cổng chuyển vùng và **1 Hệ thống Bản đồ Trong nhà (Indoor Houses)**:

```text
                  ┌─────────────────────────────┐
                  │   MAP 2: NÔNG TRẠI & VƯỜN   │
                  │  (Hái táo, cam, nông sản)   │
                  └──────────────┬──────────────┘
                                 │ (Lối đi Bắc)
┌────────────────────────┐       ↓       ┌─────────────────────────────┐
│  MAP 4: KHU DÂN CƯ     │ ←───────────→ │  MAP 1: QUẢNG TRƯỜNG TRUNG  │
│  (Đường ngõ & Nhà dân) │   (Lối Tây)   │  TÂM (Hub nhận nhiệm vụ)    │
└───────────┬────────────┘               └──────────────┬──────────────┘
            │ (Cửa vào nhà)                             │ (Lối đi Đông)
            ↓                                           ↓
┌────────────────────────┐               ┌─────────────────────────────┐
│  MAP 5: TRONG NHÀ      │               │  MAP 3: BẾN HỒ & CÂU CÁ     │
│  (Nội thất các căn nhà)│               │  (Cầu gỗ, bờ hồ, điểm câu)  │
└────────────────────────┘               └─────────────────────────────┘
```

### Chi tiết từng Bản đồ:
1. **Map 1 – Quảng trường Thị trấn (Town Square - Hub Trung tâm):**
   * Có đài phun nước trung tâm, bảng thông báo nhiệm vụ, cửa hàng Pierre và quán Saloon.
   * Nhiều NPC đi dạo hoặc đứng trò chuyện theo nhóm. Có 3 lối dẫn sang Map 2 (Bắc), Map 3 (Đông) và Map 4 (Tây).
2. **Map 2 – Nông trại & Vườn Cây Ăn Quả (Orchard & Crop Farm):**
   * Khu vực trồng cây ăn quả (táo đỏ, cam vàng, đào hồng), các luống nông sản (dâu tây, bí ngô), Nhà kính (Greenhouse) và Tháp ủ cỏ (Silo).
   * Có nông dân đi lại chăm sóc vườn và xe kéo nông sản di chuyển theo làn đường.
3. **Map 3 – Bến Hồ & Khu Câu Cá (Lakeside & Fishing Pier):**
   * Gồm mặt hồ nước xanh có hiệu ứng gợn sóng (vùng cấm đi vào), các cây cầu gỗ hẹp bắc ra giữa hồ và các điểm thả câu (`Fishing Spots`).
   * Thử thách khả năng điều khiển Robot đi qua cầu hẹp mà không va quệt vào các NPC đang đứng câu cá.
4. **Map 4 – Khu Dân Cư (Residential Village):**
   * Khu phố yên bình với đường lát đá cuội, hàng rào gỗ, cây hoa anh đào và mặt tiền của các ngôi nhà cư dân (Nhà Bác Đầu Bếp, Nhà Ông Lão Câu Cá, Nhà Thợ Mộc, Biệt Thự Thị Trưởng).
   * Mỗi ngôi nhà đều có **thảm đỏ trước cửa** đóng vai trò là cổng bước vào Map 5.
5. **Map 5 – Không gian Nội thất Trong Nhà (Indoor Houses):**
   * Khi Robot bước lên thảm đỏ trước cửa bất kỳ ngôi nhà nào và bấm vào cửa, màn hình chuyển cảnh **Fade-in** mở ra căn phòng nội thất ấm cúng ở giữa màn hình (xung quanh tối đen hoàn toàn).
   * Bên trong nhà có bàn ghế, kệ sách, bếp lò, thảm trải sàn và các NPC chủ nhà đang chờ nhận hàng. Không gian hẹp đòi hỏi Robot phải bật chế độ đi chậm (`SLOW_DOWN`).

---

## 3. Cơ chế Điều khiển Robot & Quy tắc Đứng Nhận Nhiệm Vụ

### 3.1. Điều khiển Robot
* Robot có bán kính va chạm $R_{\text{robot}} = 0.35\text{ m}$, tọa độ $(x, y)$, góc hướng mặt $\theta \in [-\pi, \pi]$ và vận tốc $v$.
* **Hệ thống phím bấm:**
  * `W / A / S / D` hoặc `↑ / ← / ↓ / →`: Di chuyển và xoay hướng Robot.
  * `Shift` hoặc `X`: Chuyển sang chế độ **Đi chậm an toàn** ($v = 0.3 \cdot v_{\text{max}}$) khi vào trong nhà hoặc tiếp cận gần người.
  * `Space`: Phanh dừng lập tức ($v = 0$).
  * `E`: Tương tác (Nhận nhiệm vụ, Giao vật phẩm, Hái trái cây, Thả/Kéo cần câu, Mở cửa vào nhà).

### 3.2. Quy tắc "Chỉ nhận/giao nhiệm vụ khi đứng trước mặt NPC một chút"
Để mô phỏng đúng chuẩn mực giao tiếp Người – Robot (Human-Robot Interaction), NPC **chỉ đồng ý giao việc hoặc nhận đồ** khi Robot bước vào **Vùng Tương Tác Hợp Lệ (Front Interaction Zone)** được vẽ trực quan bằng một hình quạt sáng màu xanh lá trước mặt NPC:

```text
                 [ Lưng NPC ]
                    ┌────┐
                    │NPC │  (Hướng mặt θ_npc)
                    └─┬──┘
                      │
                      ▼  Khoảng cách d ∈ [0.75m, 1.45m]
                 ╲         ╱
                  ╲  [OK] ╱   <-- Vùng quạt xanh lá trước mặt (Góc lệch ±35°)
                   ╲  🤖 ╱        (Robot phải dừng yên v ≈ 0 và hướng mặt về NPC)
```

Robot phải thỏa mãn đồng thời **4 điều kiện toán học** sau:
1. **Khoảng cách lịch sự ($d$):** Khoảng cách tâm-tới-tâm giữa Robot và NPC nằm trong khoảng:
   $$0.75\text{ m} \le d \le 1.45\text{ m}$$
   *(Đứng xa hơn $1.45\text{ m}$ là chưa tới tầm nói chuyện; đứng gần hơn $0.75\text{ m}$ là quá sát gây xâm phạm không gian cá nhân).*
2. **Đứng đúng phía trước mặt NPC ($\Delta \alpha_{\text{npc}}$):** Góc lệch giữa hướng mặt của NPC ($\theta_{\text{npc}}$) và vector từ NPC tới Robot phải nhỏ hơn hoặc bằng $35^\circ$:
   $$|\text{atan2}(y_{\text{robot}} - y_{\text{npc}}, x_{\text{robot}} - x_{\text{npc}}) - \theta_{\text{npc}}| \le 35^\circ$$
   *(Nếu đứng sau lưng hoặc bên hông NPC rồi bấm `E`, game sẽ hiện thông báo nhắc: "Hãy đi vòng ra phía trước mặt cư dân một chút để nói chuyện!").*
3. **Hướng mặt Robot nhìn về NPC ($\Delta \alpha_{\text{robot}}$):** Mũi Robot hướng về phía NPC với độ lệch góc $\le 45^\circ$.
4. **Dừng hẳn trước khi giao tiếp:** Vận tốc của Robot đạt trạng thái đứng yên ($v < 0.05\text{ m/s}$).

---

## 4. Cơ chế Va chạm, Đâm ngã, Cán qua người & Điều kiện Thua (Safety & Die Rules)

Hệ thống an toàn của Robot được quản lý qua **Thanh Uy Tín / Độ Bền An Toàn gồm $3$ Trái Tim (3 Safety Lives)** và phân làm **4 cấp độ xử phạt**:

| Cấp độ vi phạm | Tình huống | Điều kiện kích hoạt vật lý | Phản hồi trực quan & Vật lý | Hình phạt Điểm & Mạng |
| :--- | :--- | :--- | :--- | :--- |
| **1. Đứng/Đi quá sát** | Xâm phạm vùng cá nhân | $R_{\text{robot}} + r_{\text{npc}} < d < 0.70\text{ m}$ | NPC hiện biểu tượng giật mình `!` trên đầu và bước lùi nhẹ. | **$-5$ điểm / giây** |
| **2. Đâm ngã (Bump / Knockdown)** | Đi đâm trúng người ở tốc độ thường hoặc quệt trúng | Chạm hitbox ($d \le R_{\text{robot}} + r_{\text{npc}}$) khi $v < 0.85 \cdot v_{\text{max}}$ hoặc va lệch tâm | - **NPC bị ngã ngồi ra đất** trong $3.0\text{ s}$, hiện sao choáng `💫`.<br>- Robot bị bật nảy lùi lại $0.4\text{ m}$ và khóa di chuyển $1.0\text{ s}$. | **$-100$ điểm**<br>Trừ **$1$ Mạng** |
| **3. Đâm nhiều lần (Multi-Hit Die)** | Tái phạm đâm ngã dân làng nhiều lần | Tổng số lần làm ngã NPC chạm mốc **$3$ lần** (Mất hết $3$ Trái tim) | Hệ thống phát còi báo động mất an toàn và ngắt nguồn Robot. **GAME OVER (DIE)!** | **$-250$ điểm**<br>**THUA MÀN CHƠI** |
| **4. Cán thẳng qua người (Run Over)** | Phóng tốc độ cao đâm xuyên tâm hoặc cố tình đi đè qua người đang ngã | 1. Chạy tốc độ cao ($v \ge 0.85 \cdot v_{\text{max}}$) tông trực diện xuyên tâm NPC (góc lệch $< 20^\circ$).<br>2. Hoặc khi NPC đang nằm ngã trên đất mà Robot không dừng/lùi lại, đi đè vào cơ thể ($d < 0.65 \cdot (R_{\text{robot}} + r_{\text{npc}})$). | - Màn hình chớp đỏ khẩn cấp: **"VI PHẠM NGHIÊM TRỌNG: CÁN QUA CƯ DÂN!"**<br>- **DIE NGAY LẬP TỨC (Instant Game Over)** bất kể còn bao nhiêu mạng! | **$-500$ điểm** *(Điểm trừ cao nhất)*<br>**THUA NGAY LẬP TỨC** |

---

## 5. Hệ thống Nhiệm vụ Đa dạng & Cơ chế Gameplay (Quests & Minigames)

### 5.1. Khay Chứa Đồ của Robot (Robot Inventory)
* Robot có **4 ô chứa vật phẩm (4 Inventory Slots)** hiển thị ở thanh công cụ dưới đáy màn hình.
* Khi Robot đang giữ vật phẩm trong người, hình ảnh nhân vật Robot trên bản đồ sẽ **hiển thị đang bê hộp hàng / giỏ trái cây / cá tươi** trên tay.

### 5.2. Ba Nhóm Nhiệm vụ Chính
1. **Nhiệm vụ Thu hoạch Trái cây & Giao hàng (Fruit Harvesting Quest):**
   * *Luồng thực hiện:* Đứng trước mặt NPC giao việc ở Map 1 bấm `E` nhận nhiệm vụ $\rightarrow$ Di chuyển lên **Map 2 (Vườn cây)** $\rightarrow$ Tìm cây táo/cam đang có quả chín, đứng trước gốc cây bấm `E` ($1.5\text{ s}$ để thu hoạch vào giỏ) $\rightarrow$ Di chuyển sang **Map 4**, mở cửa bước vào **Map 5 (Trong nhà)** $\rightarrow$ Căn vị trí đứng trước mặt NPC nhận hàng bấm `E` để hoàn tất.
2. **Nhiệm vụ Câu Cá tại Bến Hồ (Lakeside Fishing Quest):**
   * *Luồng thực hiện:* Nhận lời nhờ từ Ông Lão hoặc Đầu Bếp $\rightarrow$ Sang **Map 3 (Bến Hồ)**, khéo léo đi qua cầu gỗ hẹp tới điểm câu (`Fishing Spot`) $\rightarrow$ Bấm `E` để thả cần câu xuống nước $\rightarrow$ Đợi $2\text{--}4\text{ s}$ đến khi phao câu nảy lên kèm ký hiệu `!!` và âm báo, bấm `E` kịp thời trong khoảng $0.8\text{ s}$ để kéo cá lên giỏ $\rightarrow$ Mang cá tươi đi giao cho người nhận.
3. **Nhiệm vụ Chuyển Phát Nhanh Liên Bản Đồ (Town Express Delivery):**
   * *Luồng thực hiện:* Nhận kiện hàng/bánh mì nóng từ một NPC ở cửa hàng (Map 1 hoặc trong nhà Map 5), tìm một NPC khác đang đi dạo ngoài đường hoặc ở bản đồ khác để giao trước khi hết thời gian thưởng thêm (Bonus Timer).

---

## 6. Bảng Quy đổi Điểm thưởng & Phạt (Scoring & AI Reward System)

Bảng điểm này dùng chung cho cả **Xếp hạng Người chơi (Rank S / A / B / C / F)** lẫn **Hàm Mục tiêu (Reward Function)** khi bật chế độ Robot Tự Hành:

| Hành vi / Sự kiện trong Game | Điểm số | Ghi chú |
| :--- | :---: | :--- |
| **Đứng đúng vùng trước mặt NPC & Nhận nhiệm vụ** | **$+20$** | Thưởng tư thế tiếp cận lịch sự đúng góc nhìn. |
| **Hái thành công 1 phần Trái cây / Nông sản (Map 2)** | **$+30$** | Hoàn thành mục tiêu thu thập nông trại. |
| **Câu thành công 1 con Cá tại Bến Hồ (Map 3)** | **$+50$** | Hoàn thành minigame câu cá. |
| **Giao đúng vật phẩm cho NPC ở Ngoài trời** | **$+150$** | Đứng đúng trước mặt người nhận và bấm giao. |
| **Giao đúng vật phẩm cho NPC ở Trong Nhà (Map 5)** | **$+250$** | Thưởng cao hơn do phải qua cửa và đi trong phòng hẹp. |
| **Giảm tốc / Dừng nhường đường khi cư dân cắt ngang** | **$+5$** | Thưởng hành vi di chuyển an toàn, văn minh. |
| **Đi quá sát cư dân ($d < 0.70\text{ m}$)** | **$-5$ / giây** | Phạt xâm phạm vùng không gian cá nhân. |
| **Đâm va làm cư dân bị ngã (Bump / Knockdown)** | **$-100$** | Mất $1$ mạng, NPC ngã ngồi $3\text{ s}$. |
| **Làm ngã cư dân đủ $3$ lần (Hết mạng $\rightarrow$ Die)** | **$-250$** | Bị ngắt nguồn và xử thua màn chơi. |
| **Cán thẳng qua người (Run Over $\rightarrow$ Instant Die)** | **$-500$** | **Điểm trừ nặng nhất** – Xử thua ngay lập tức! |

---

## 7. Cấu trúc Code Mô-đun (`game/`) & Lộ trình Phát triển

### 7.1. Kiến trúc Gói Mô-đun `game/` và Cơ sở Dữ liệu `game/data/`
Toàn bộ hình ảnh Pixel-Art được nạp trực tiếp từ thư mục `sprites/sprites/` (không dùng thư mục `assets/` cũ). Hệ thống mã nguồn được phân chia thành các mô-đun độc lập, phân tầng rõ ràng trong gói `game/`, đồng thời sử dụng cơ sở dữ liệu định dạng JSON trong `game/data/` để mở rộng nội dung linh hoạt:

#### A. Các Mô-đun Nền tảng & Điều phối Cốt lõi:
* `stardew_game.py`: Điểm khởi chạy ngắn gọn ở thư mục gốc (`python stardew_game.py` hoặc `python -m game.app`).
* `game/constants.py`: Hằng số kích thước màn hình (`1152x768`, `TILE_SIZE = 32`), quy đổi đơn vị vật lý ($1.0\text{ m} = 48\text{ px}$), thông số toán học Vùng Quạt Xanh HRI, danh sách 12 thư mục nhân vật (`ALL_NPC_FOLDERS`), thông số kinh tế, màu sắc và bảng điểm thưởng/phạt.
* `game/sprite_vault.py`: Lớp `SpriteVault` nạp, co giãn, nhuộm màu nội thất (`tinted`), cắt ô địa hình liền mạch (`texture_cell`) và lưu đệm toàn bộ tài nguyên từ `sprites/sprites/`.
* `game/entities.py`: Định nghĩa các thực thể game: `RobotPlayer`, `VillagerNPC`, `FarmCartAGV`, `FarmAnimal` (bò, heo, cừu, gà đi lại trong đồng cỏ), `PropObject`, `HarvestSpot`, `FishingSpot`, `MapPortal`, `FloatingText`.
* `game/world_builder.py` & `game/terrain.py`: Công cụ dựng bản đồ Stardew Valley (vách đá ngầm, bờ hồ có bọt sóng, cầu đá/cầu gỗ, hàng rào gỗ/trắng, thửa ruộng có vòi tưới `sprinkler` và bù nhìn `scarecrow`, chuồng trại).
* `game/maps.py`: Thiết kế chi tiết 4 Bản đồ Ngoài trời (Map 1..4) và 10 Giao diện Nội thất Trong Nhà riêng biệt (`INTERIOR_THEMES` cho Map 5: Nhà bếp Gus, Xưởng mộc Robin, Nhà gỗ Willy, Dinh thự Thị trưởng Lewis, Tạp hóa Pierre, Quán Stardrop Saloon, Kho vận JojaMart, Phòng khám Y tế...).
* `game/safety_hri.py`: Kiểm tra 4 điều kiện Vùng Quạt Xanh trước mặt NPC (`check_front_interaction`, `draw_npc_interaction_fan`) và xử lý 4 cấp độ va chạm / điều kiện thua (`update_safety_and_collisions`).
* `game/quests.py`: Hệ thống nhiệm vụ thu hoạch, câu cá, chuyển phát nhanh và xử lý phím bấm tương tác `[E]` (`handle_interact_action`).
* `game/autopilot.py`: Bộ điều khiển AI Tự Hành (`compute_autopilot_command` - phím `[P]`) hỗ trợ điều hướng an toàn tránh người và tự động thực hiện nhiệm vụ.
* `game/ui_renderer.py`: Kết xuất cảnh ngoài trời Y-Sorting, cảnh nội thất theo chủ đề từng căn nhà, vẽ lớp bóng đổ nhân vật, và giao diện HUD tự động ngắt dòng (`wrap_text`) chống tràn chữ.
* `game/app.py`: Lớp điều phối trung tâm `FarmBotTownGame` (tự động tắt IME Unikey/Telex khi vào cửa sổ game để nhận phím `W, A, S, D, E, R, F, P, X` tức thì).

#### B. Các Mô-đun Stardew Valley & Vòng Lặp Chơi Mới (Core Loop Modules):
* `game/game_state.py`: Quản lý `GameState` trung tâm, `InventorySlot` (hệ thống phẩm cấp sao: Thường, sao Bạc `★`, sao Vàng `★★`, Iridium `★★★`), `ForageItem` (hái lượm nấm hoang dã, quả mọng, hoa cúc vàng), bảo toàn trạng thái ruộng qua các Map (`persistent_harvest_state`), cơ chế rơi đồ khi va chạm Cấp 2, Tổng kết cuối ngày (`render_end_of_day_modal`) và Lưu/Tải 3 Slot Game (`game/saves/slot_1..3.json`).
* `game/dialogue.py`: Hộp thoại chân dung 12 NPC có biểu cảm sắc thái (`love`, `happy`, `surprised`, `sad`), nhãn nhóm tuổi trực quan (`[Người Cao Tuổi]`, `[Trẻ Nhỏ]`, `[Cư Dân]`), hệ thống hội thoại ngữ cảnh theo khung giờ / thời tiết / mốc tim tình cảm và tính năng Tặng Quà (`[G]`).
* `game/journal_ui.py`: Sổ Tay Thị Trấn & Bách Khoa Toàn Thư 3 Tab (`[J]`): Tab 1 - Hồ sơ 12 NPC & Radar An Toàn 8.7; Tab 2 - Thư viện Đơn hàng & Tin đồn Bí mật; Tab 3 - Quản lý Lưu/Tải 3 Slot & Cẩm nang Core Loop.
* `game/atmosphere.py`: Chu kỳ Ngày – Đêm (`07:00 – 22:00`), Ánh sáng động Radial Glow quanh đèn đường/cửa sổ & Đèn pha Robot ban đêm, Vòi tưới tự động Sprinkler phun nước làm ẩm đất, 4 Mùa luân chuyển (`Xuân`, `Hè`, `Thu`, `Đông` - phím `[K]`), Thời tiết Động (`[V]`) và Không khí Lễ Hội Hoa Anh Đào (`[L]`).
* `game/stardew_systems.py`: Mini-game Thanh Câu Cá Stardew Valley tương tác, Thùng Giao Hàng (Shipping Bin nhân hệ số sao chất lượng: `x1.25`, `x1.5`, `x2.0`) và Xưởng Mộc Robin (`[U]` - giảm giá 20% khi đạt mốc 3 ♥ với Robin).
* `game/schedules.py`: Lịch sinh hoạt cư dân theo giờ thực tế trong ngày và Bản đồ Radar Minimap thu nhỏ đa sắc (`[M]`).
* `game/audio.py`: Bộ tổng hợp âm thanh Procedural Audio (sóng âm đa hài) tạo SFX bước chân, hái quả, câu cá, ting-ting tiền vàng, lên tim, còi va chạm và nhạc nền ngũ cung êm dịu (`[B]`).
* `game/vfx.py`: Hiệu ứng chuyển vùng mượt Screen Fade, rung màn hình Screen Shake, hạt bụi bánh xe khi di chuyển, thông báo Popup góc màn hình (Stardew Toast Notifications) và Checklist Hướng dẫn Tân thủ 5 bước tương tác (`[H]`).
* `game/random_events.py`: Hệ thống Sự Kiện Ngẫu Nhiên & Biến Động Thế Giới (`RandomEventManager` - phím `[O]`).

#### C. Cơ sở Dữ liệu Định dạng JSON (`game/data/`):
* `game/data/items.json`: Danh mục toàn bộ vật phẩm trong game, phân loại (nông sản, trái cây, cá, quà tặng, đồ nhặt), giá bán cơ sở và mùa vụ xuất hiện.
* `game/data/npcs.json`: Hồ sơ chi tiết 12+ cư dân thị trấn: nhóm tuổi (`elder`, `child`, `adult`), bán kính an toàn HRI ưu tiên, tính cách, danh sách món yêu thích / ghét, tin đồn bí mật và lời thoại theo tình huống.
* `game/data/quests.json`: Thư viện nhiệm vụ chuẩn hóa gồm Đơn thường nhật và Đơn đặt hàng đặc biệt kích hoạt theo Mùa và mốc Tim thiện cảm.
* `game/data/random_events.json`: Cấu hình danh mục sự kiện ngẫu nhiên, điều kiện xuất hiện, bản đồ mục tiêu, thời hạn hoàn thành và giá trị phần thưởng.

### 7.2. Lộ trình 4 Bước Triển khai Cơ bản (Đã hoàn thành)
1. **Bước 1 (Thế giới 5 Map & Nội thất Đa dạng):** Dựng 4 Map ngoài trời liên thông (Quảng trường & Bờ sông, Đại nông trại & Ruộng cây trồng, Đảo rừng xanh & Bến hồ, Khu dân cư & Vườn hoa) và Map 5 (Mỗi ngôi nhà có một thiết kế nội thất riêng biệt).
2. **Bước 2 (Tương tác Trước mặt & Vật lý Va chạm/Ngã/Cán qua):** Hiển thị hình quạt xanh lá trước mặt NPC, cài đặt công thức kiểm tra góc đứng nhận việc, hiệu ứng NPC bị đâm ngã $3\text{ s}$, thanh 3 mạng và cơ chế xử thua ngay khi cán thẳng qua người.
3. **Bước 3 (Hệ thống Nhiệm vụ Hái quả, Thu hoạch Ruộng, Câu cá & Giao đồ):** Thêm 6 thửa ruộng nông sản (`stage_00..09`) và vườn cây ăn quả ở Map 2, điểm câu cá ở Map 3, khay 4 ô chứa đồ và bảng theo dõi nhiệm vụ góc phải màn hình.
4. **Bước 4 (Kết nối Chế độ Simulation AI):** Cho phép bấm phím `[P]` chuyển đổi trực tiếp giữa **Người Chơi Điều Khiển** và **AI Tự Hành** ngay trong thế giới *FarmBot Town*.

---

## 8. Đặc tả Nâng cấp Mở rộng Chuẩn Stardew Valley (Stardew-Authentic Expansion Roadmap)

Để nâng tầm trải nghiệm từ một bản đồ mô phỏng cố định thành một thế giới sống động đúng chất **Stardew Valley** (vừa cuốn hút người chơi, vừa tạo môi trường giàu ngữ cảnh cho thuật toán **Context-Aware Robot Navigation & Social RL**), hệ thống được quy hoạch mở rộng thêm **7 tính năng đặc trưng** sau:

### 8.1. Bản đồ Thế giới Mở rộng & Camera Cuộn Mượt + Minimap (Scrolling World & Lerp Camera)
* **Mở rộng kích thước bản đồ:** Thay vì giới hạn trong 1 khung hình cố định `36×24` ô (`1152×768 px`), mở rộng mỗi Map ngoài trời lên `60×40` ô (`1920×1280 px`) hoặc `72×48` ô (`2304×1536 px`).
* **Camera bám mượt (Smooth Lerp Camera):** Tâm góc nhìn $\mathbf{p}_{\text{cam}}$ nội suy mượt theo vị trí Robot:
  $$\mathbf{p}_{\text{cam}}(t + \Delta t) = \mathbf{p}_{\text{cam}}(t) + \left(1 - e^{-\lambda \Delta t}\right)\left(\mathbf{p}_{\text{robot}}(t) - \mathbf{p}_{\text{cam}}(t)\right)$$
  giới hạn trong biên bản đồ $[0, W_{\text{world}} - W_{\text{screen}}] \times [0, H_{\text{world}} - H_{\text{screen}}]$.
* **Minimap Radar thông minh:** Hiển thị bản đồ thu nhỏ ở góc màn hình với chấm xanh (Robot), chấm vàng nhấp nháy (`!` NPC giao việc), chấm xanh lá (`?` NPC nhận hàng), biểu tượng ruộng chín và cổng chuyển vùng.

### 8.2. Hộp Thoại Chân Dung Nhân Vật & Hệ Thống Tim Thiện Cảm (Portrait Dialogue & Friendship Hearts)
* **Khung hội thoại Stardew cổ điển:** Khi Robot dừng trong Vùng Quạt Xanh trước mặt NPC và bấm `[E]`, bật hộp thoại gỗ ở nửa dưới màn hình:
  * **Khung phải:** Ảnh chân dung lớn của NPC kèm tên, nghề nghiệp và **Thanh Tim Thiện Cảm (`0..5 ♥`)**.
  * **Khung trái:** Lời thoại hiển thị từng chữ (typewriter effect) phản ánh cảm xúc của cư dân và nút xác nhận Nhận việc / Giao hàng.
* **Cơ chế Điểm Thiện Cảm (Social Affinity):**
  * Đứng đúng cự ly lịch sự + Giao hàng đúng hạn: Tăng thiện cảm (`+1 ♥`), NPC tặng thêm phần thưởng phụ (bánh mì, nông sản hiếm).
  * Đi quá sát ($d < 0.70\text{ m}$) hoặc va quệt làm ngã NPC: Giảm thiện cảm (`-1..-2 ♥`), lần sau gặp NPC sẽ cảnh giác hoặc yêu cầu giữ khoảng cách xa hơn.

### 8.3. Chu Kỳ Ngày – Đêm, Ánh Sáng Động & Thời Tiết Theo Mùa (Day/Night Cycle, Lighting & Weather)
* **Chu kỳ thời gian & Ánh sáng môi trường:**
  * `06:00 – 15:00` (**Ban ngày**): Ánh nắng trong trẻo, tầm nhìn tối đa.
  * `15:00 – 18:00` (**Hoàng hôn**): Phủ lớp ánh sáng vàng cam ấm áp (`rgba(255, 165, 90, 45)`).
  * `18:00 – 24:00` (**Ban đêm**): Phủ lớp bóng tối xanh thẫm (`rgba(16, 22, 54, 130)`), tự động kích hoạt **quầng sáng Radial Light** ấm áp tại tất cả cột đèn đường (`lamp_post.png`), ô cửa sổ các ngôi nhà (`furn_window.png`) và **đèn pha hình nón phía trước Robot**.
* **Hiệu ứng Thời tiết & Môi trường vật lý:**
  * **Nắng gió mùa xuân:** Cánh hoa anh đào hồng (`cherry petals`) bay chéo nhẹ qua màn hình, tia nắng lấp lánh trên mặt nước.
  * **Mưa rào nông trại:** Hạt mưa rơi + đất ruộng tự động chuyển sang trạng thái ẩm ướt (`watered_soil.png`), đồng thời mặt cầu gỗ ở Map 3 có hệ số ma sát thấp hơn — buộc Robot hoặc thuật toán RL phải bật chế độ đi chậm (`SLOW_DOWN`) để không trượt bánh.

### 8.4. Chu trình Canh tác Nông trại, Vòi Tưới Tự Động & Thùng Giao Hàng (Farming & Shipping Bin)
* **Hiệu ứng Vòi tưới (`sprinkler.png`):** Các vòi tưới giữa ruộng định kỳ phun tia nước 4/8 hướng làm đất quanh vòi chuyển sang màu đất ẩm (`watered_soil.png`) và rút ngắn $35\%$ thời gian mọc lại của cây trồng (`stage_00 -> stage_09`).
* **Thùng Giao Hàng Nông Trại (Shipping Bin):** Đặt cạnh Nhà chính ở Map 2. Khi Robot thu hoạch dư nông sản hoặc cá tươi trong Khay 4 ô, Robot có thể mang tới Thùng Giao Hàng bấm `[E]` để ký gửi và nhận điểm thưởng / Vàng (`G`).

### 8.5. Mini-game Thanh Câu Cá Stardew Valley (Interactive Fishing Bar Mini-game)
* Khi phao câu tại Bến Hồ Map 3 nảy lên (`!!`) và người chơi bấm `[E]`, mở một **Thanh Câu Cá Dọc (Fishing Bar)** ngay cạnh Robot:
  * Biểu tượng con cá bơi lên xuống theo quỹ đạo ngẫu nhiên.
  * Người chơi giữ/nhả phím `Space` hoặc `E` để điều khiển thanh xanh lá bám theo vị trí con cá cho đến khi cột tiến độ bên cạnh đầy $100\%$ (hoặc tự động hoàn tất nếu đang bật chế độ `AI Tự Hành [P]`).

### 8.6. Lịch Sinh Hoạt Cư Dân Theo Giờ (Time-Based Daily NPC Schedules)
* Cư dân di chuyển giữa các bản đồ theo khung giờ trong ngày giống hệt *Stardew Valley*:
  * **Buổi sáng (`07:00 – 11:30`):** Cư dân ở trong nhà (Map 5) hoặc chăm sóc vườn rau trước sân (Map 2, Map 4).
  * **Buổi trưa – chiều (`11:30 – 17:30`):** Cư dân đi bộ ra Quảng trường (Map 1), qua cầu đá sang JojaMart hoặc ra Bến hồ (Map 3) câu cá.
  * **Buổi tối (`17:30 – 22:00`):** Cư dân tập trung tại Quán nước Stardrop Saloon hoặc trở về nhà riêng (Map 5).
* Cơ chế này tạo ra các luồng giao thông người đi bộ thay đổi theo giờ, là bài toán lý tưởng để huấn luyện và kiểm thử **Context-Aware Social Navigation RL**.

### 8.7. Xưởng Nâng Cấp Robot Của Thợ Mộc Robin (Robot Upgrades & Energy Management)
* Khi tích lũy đủ Điểm Uy Tín / Vàng từ các đơn hàng, Robot có thể ghé **Xưởng Mộc Robin (Map 4 -> Map 5)** để mở khóa nâng cấp:
  1. **Khay Hàng Mở Rộng (Cargo Rack Lv.2):** Nâng sức chứa từ `4 ô` lên `6 ô`.
  2. **Bộ Phanh Từ Tính (Magnetic Brake):** Giảm quán tính và rút ngắn thời gian thu hoạch từ `1.5s` xuống `0.9s`.
  3. **Cảm Biến HRI Mở Rộng (Social Radar):** Tự động làm chậm Robot khi đi vào bán kính $1.65\text{ m}$ quanh người già hoặc trẻ nhỏ ($1.25\text{ m}$ quanh người lớn) để tránh bị trừ điểm vùng cá nhân.

---

## 9. Vòng Lặp Chơi Cốt Lõi (Core Loop), Kiến Trúc Dữ Liệu & Hệ Sinh Thái Mở Rộng

Để kết nối toàn bộ các cơ chế thành một vòng lặp chơi chặt chẽ và có chiều sâu như **Stardew Valley**, dự án triển khai kiến trúc hướng dữ liệu (Data-Driven Architecture) và chu kỳ ngày – mùa liên tục:

### 9.1. Vòng Lặp Chơi Chuẩn (Core Gameplay Loop)
1. **Nhận Đơn (`!`)**: Gặp cư dân, dừng đúng Vùng Quạt Xanh và bấm `[E]` để nhận Đơn Thường hoặc **Đơn Đặc Biệt** (mở theo Mùa hoặc Mốc Tim $\ge 3\text{ }\heartsuit$).
2. **Thu Thập & Khám Phá**:
   - Thu hoạch cây trồng/vườn quả (`stage_00..09`), câu cá bằng Mini-game Thanh Câu Cá, hoặc nhặt **Vật Phẩm Hoang Dã (Foraging)**: Nấm Rừng (`mushroom`), Quả Mọng (`wild_berry`), Hoa Cúc Vàng (`golden_flower`).
   - Vật phẩm có **4 bậc Chất lượng**: Thường, **Sao Bạc (`★` $\times 1.25$ giá)**, **Sao Vàng (`★★` $\times 1.5$ giá)**, và **Iridium (`★★★` $\times 2.0$ giá)**.
3. **Giao Hàng Lịch Sự, Bán Nông Sản & Tặng Quà (`[G]`)**:
   - Giao hàng đúng hạn & đúng vùng quạt trước mặt để nhận **Vàng (`G`)**, **Điểm Uy Tín** và **Tim Thiện Cảm (`♥`)**.
   - Đem nông sản dư ra **Thùng Giao Hàng (Shipping Bin - Map 2)** bán lấy Vàng.
   - Chọn vật phẩm trên Hotbar (phím `Z` hoặc click chuột vào ô) và bấm **`[G]`** để tặng quà cho NPC theo sở thích (`loved_items`, `liked_items`, `hated_items`).
4. **Mốc Tim (`3 ♥`, `5 ♥`) & Nâng Cấp (`[U]`)**:
   - Đạt **3 ♥** với Thợ mộc Robin được **giảm giá 20%** toàn bộ nâng cấp tại Xưởng Robin; đạt **3 ♥ / 5 ♥** với cư dân nhận quà tri ân và mở khóa Đơn Đặt Hàng Đặc Biệt.
5. **Kết Thúc Ngày (`[N]` hoặc `22:00`) & Qua Ngày Mới**:
   - Hiển thị **Bảng Thống Kê Cuối Ngày (End-of-Day Summary Modal)**: tổng kết Doanh thu Vàng, Đơn hàng hoàn thành, Nông sản xuất xưởng, Thưởng An Toàn HRI (`+50G` nếu không va chạm).
   - Qua đêm, mọi thửa ruộng trên cả 4 Map lớn thêm giai đoạn/chín lại (`persistent_harvest_state`), sinh vật phẩm nhặt mới, chuyển sang Ngày tiếp theo (mỗi 5 ngày đổi Mùa: **Xuân → Hè → Thu → Đông**, Ngày 3 tổ chức **Lễ Hội Thị Trấn** tại Quảng Trường Map 1).

### 9.2. Kiến Trúc Dữ Liệu JSON & Trạng Thái Trung Tâm (`GameState`)
- **`game/data/items.json`**: Cơ sở dữ liệu vật phẩm, phân loại, giá gốc, mùa xuất hiện.
- **`game/data/npcs.json`**: Hồ sơ 12+ cư dân gồm nhóm tuổi (`elder` Người cao tuổi, `child` Trẻ nhỏ, `adult` Người lớn), bán kính an toàn ưu tiên, tính cách, món yêu thích/ghét, tin đồn bí mật và lời thoại theo ngữ cảnh.
- **`game/data/quests.json`**: Danh sách đơn hàng thường và đơn đặc biệt theo mùa/mốc tim.
- **`game/game_state.py`**: Quản lý trạng thái tập trung, đồng bộ trạng thái ruộng liên bản đồ và hỗ trợ **Lưu / Tải 3 Slot (`game/saves/slot_1..3.json`)** qua phím `[F5]` / `[F9]` hoặc trong Menu Sổ Tay `[J]`.

### 9.3. Cảm Giác Chơi (Game Feel), Âm Thanh & Giao Diện Sổ Tay
- **`game/audio.py` (`SoundAndMusicManager`)**: Bộ tổng hợp âm thanh sóng âm (Procedural Audio) tạo SFX bước chân, thu hoạch, quăng câu, cá cắn câu, đồng xu vàng `ting-ting!`, lên tim, va chạm và giai điệu nhạc nền theo mùa (bật/tắt bằng phím `[B]`).
- **`game/vfx.py` (`VFXAndTutorialManager`)**: Hiệu ứng màn hình chuyển vùng mượt (Screen Fade Transition), rung nhẹ khi va chạm (Screen Shake), hạt bụi bánh xe, rơi vật phẩm khi va chạm Cấp 2 (có thể nhặt lại), thông báo Popup nổi góc màn hình (Toast Notifications) và **Hướng Dẫn Tân Thủ 5 Bước (`[H]`)**.
- **`game/journal_ui.py` (`JournalAndCompendiumModal`)**: Sổ tay 3 Tab mở bằng phím **`[J]`** (Sổ Tay Cư Dân & Mốc Tim, Thư Viện Đơn Hàng & Tin Đồn, và Lưu/Tải 3 Slot Game).

---

## 10. Hệ Thống Sự Kiện Ngẫu Nhiên & Biến Động Thế Giới (Random & Dynamic World Events — Phím `[O]`)

Nhằm biến thị trấn nông trại thành một thế giới mở sinh động, luôn chứa đựng yếu tố bất ngờ và đem đến các thử thách điều hướng xã hội mới mẻ cho cả người chơi lẫn mô hình AI Reinforcement Learning, hệ thống tích hợp mô-đun quản lý sự kiện ngẫu nhiên `RandomEventManager` (`game/random_events.py` & `game/data/random_events.json`).

### 10.1. Cơ Chế Kích Hoạt & Luồng Sự Kiện (Event Trigger Mechanics)
Hệ thống vận hành dựa trên 3 phương thức kích hoạt linh hoạt:
1. **Tự động kích hoạt đầu ngày mới (75% Xác suất):** Mỗi sáng khi Robot thức dậy (chuyển sang ngày mới), thuật toán gieo xác suất ngẫu nhiên với tỷ lệ thành công 75% để chọn ra 1 sự kiện thời tiết, xã hội hoặc kinh tế đặc thù trong ngày.
2. **Kích hoạt tự động giữa ca làm việc:** Nếu đầu ngày chưa có sự kiện, hệ thống duy trì bộ đếm thời gian thực trong game để tự động kích hoạt biến cố bất ngờ vào khung giờ trưa – chiều (`11:00 – 14:00`) tạo tình huống cấp bách (ví dụ: bão rào đổ bộ hoặc đơn hàng cấp cứu y tế SOS).
3. **Kích hoạt tức thì bằng Phím Tắt hoặc HUD (`[O]`):** Người chơi và nhà nghiên cứu có thể bấm phím **`[O]`** trên bàn phím (hoặc click nút HUD `[O] Sự Kiện` màu tím trên thanh công cụ) để chủ động kích hoạt hoặc chuyển đổi nhanh tuần tự qua các sự kiện nhằm phục vụ kiểm thử phản ứng của Robot.
4. **Phản hồi trực quan & Chỉ dẫn mục tiêu:**
   - Khi một sự kiện kích hoạt, màn hình sẽ hiển thị **Banner Thông Báo Nổi (Amber World Event Banner)** với biểu tượng đặc trưng và mô tả tóm tắt nhiệm vụ.
   - Bản đồ Radar Minimap (`[M]`) tự động đánh dấu vị trí phát sinh sự kiện bằng chấm sao nhấp nháy màu tím/cam.
   - Hoàn thành sự kiện sẽ kích hoạt hiệu ứng âm thanh chúc mừng chiến thắng, cộng dồn điểm uy tín an toàn, tiền vàng và điểm tình cảm với cư dân liên quan.

### 10.2. Bảng Chi Tiết 7 Sự Kiện Ngẫu Nhiên Độc Đáo

| STT | Mã Sự Kiện (`event_id`) | Tên Sự Kiện & Biểu Tượng | Bản Đồ Diễn Ra | Bối Cảnh Cốt Truyện & Tình Huống | Nhiệm Vụ Robot & Thử Thách An Toàn HRI | Phần Thưởng Hoàn Thành |
| :---: | :--- | :--- | :---: | :--- | :--- | :--- |
| **1** | `iridium_meteor` | **Mưa Sao Băng & Khoáng Thạch Tím** 🌠 | **Map 2**<br>(Nông trại & Vườn cây) | Đêm qua một mảnh thiên thạch tím rơi xuống góc vườn nông trại, phát xạ năng lượng làm hoa cỏ và khoáng thạch xung quanh đột biến phát quang kỳ ảo. | Di chuyển lên Map 2, định vị vị trí thiên thạch rơi và thu hoạch các khoáng thạch / thảo mộc đột biến đạt phẩm cấp tối thượng **Iridium (`★★★`)**. | **`+120G`**<br>**`+80`** Điểm Uy Tín<br>01 Khoáng thạch Iridium (`★★★`) |
| **2** | `lost_item_search` | **Tìm Túi Đồ Đánh Rơi Của Bà Evelyn** 👜 | **Map 1**<br>(Quảng trường thị trấn) | Bà Evelyn trong lúc đi dạo ngắm hoa buổi sáng đã sơ ý đánh rơi chiếc túi thổ cẩm đựng các loại hạt giống hoa và thảo dược gia truyền. | Lùng sục khắp các góc khuất quanh đài phun nước Map 1, nhặt túi đồ và mang đến giao tận tay Bà Evelyn trong Vùng Quạt Xanh lịch sự. | **`+75G`**<br>**`+70`** Điểm Uy Tín<br>**`+150`** Điểm Tim Bà Evelyn |
| **3** | `runaway_animals` | **Cừu Non Tinh Nghịch Đi Lạc** 🐑 | **Map 2**<br>(Trục đường chính nông trại) | Một chú cừu non hiếu động của Nông trang Marnie lẻn qua khe hở hàng rào, đi lang thang giữa làn đường xe kéo AGV gây nguy cơ tắc nghẽn và mất an toàn. | Bật chế độ đi chậm an toàn `[Shift / X]`, nhẹ nhàng tiếp cận chú cừu từ phía trước (không đâm giật mình), dùng còi tín hiệu êm ái dẫn cừu trở lại chuồng. | **`+85G`**<br>**`+65`** Điểm Uy Tín<br>**`+120`** Điểm Tim Marnie |
| **4** | `traveling_merchant` | **Thương Nhân Du Mục Ghé Thăm** 🎪 | **Map 1**<br>(Góc chợ cạnh Saloon) | Cỗ xe tuần lộc chở đầy hàng hóa kỳ lạ của cô thương nhân du mục ghé bến đỗ thị trấn chỉ trong duy nhất ngày hôm nay, đem tới những thức quả lạ phương xa. | Di chuyển đến xe hàng tại Map 1, tương tác kết nối giao thương giữa nông thôn và thương gia du mục. | **`+90G`**<br>**`+60`** Điểm Uy Tín<br>Tặng 01 **Đào Tiên Sao Vàng (`★★`)** |
| **5** | `flash_express_order` | **Đơn Cấp Cứu Y Tế Khẩn Cấp `[SOS]`** 🚑 | **Map 1**<br>(Phòng khám Bác sĩ Harvey) | Bác sĩ Harvey tiếp nhận một ca điều trị khẩn cấp và cần chuyển phát siêu tốc gói huyết thanh thảo dược tới nhà một bệnh nhân trước khi cạn đồng hồ đếm ngược. | Tiếp nhận gói y tế tại phòng khám, di chuyển với tốc độ tối ưu nhưng phải tuyệt đối tuân thủ khoảng cách an toàn, không va quệt người đi đường. | **`+110G`** *(Thưởng gấp đôi)*<br>**`+90`** Điểm Uy Tín<br>**`+100`** Điểm Tim Bác Sĩ Harvey |
| **6** | `sudden_squall` | **Cơn Mưa Rào Lộc Xuân Bất Chợt** 🌧️ | **Map 3**<br>(Bến hồ & Trạm nước ven rừng) | Những đám mây tích điện bất ngờ đổ xuống một trận mưa rào mát lạnh; hơi ẩm bao phủ giúp toàn bộ ruộng cây trồng lớn vọt $2\times$ tốc độ thông thường. | Vận hành Robot cẩn thận trên mặt cầu gỗ trơn trượt của Map 3, đến trạm đo khí tượng ven hồ kiểm tra lưu lượng nước và van điều tiết chống ngập úng. | **`+70G`**<br>**`+65`** Điểm Uy Tín<br>Cây trồng toàn thị trấn lớn thêm $1$ giai đoạn |
| **7** | `spontaneous_gathering` | **Hội Họp Đột Xuất Giữa Quảng Trường** 👥 | **Map 1**<br>(Quảng trường trung tâm) | Nhóm cư dân và các bô lão thị trấn tự phát tụ tập thành một vòng tròn trò chuyện thân mật (Social O-Space) ngay giữa khu vực trung tâm đài phun nước. | Robot phải kích hoạt chế độ đi chậm `[X]`, không được đâm xuyên qua tâm vòng trò chuyện (phạt nặng O-Space), lịch sự đi vòng qua mép ngoài và cất tiếng chào. | **`+80G`**<br>**`+75`** Điểm Uy Tín<br>**`+110`** Điểm Tim Toàn Nhóm Cư Dân |

---

## 11. Bảng Tổng Hợp Toàn Bộ Phím Tắt & Điều Khiển Trong Game (`FarmBot Town`)

Bảng dưới đây liệt kê toàn bộ các phím bấm và tổ hợp tương tác có mặt trong trò chơi, bao gồm phím di chuyển, an toàn giao tiếp HRI, quản lý nông nghiệp Stardew Valley, cùng các công cụ gỡ lỗi (debug) và nghiên cứu AI:

| Phím Tắt | Phân Loại | Chức Năng Chi Tiết & Ý Nghĩa Tương Tác |
| :---: | :--- | :--- |
| **`W / A / S / D`**<br>*(hoặc phím mũi tên)* | **Di chuyển cơ bản** | Điều khiển Robot di chuyển 4 hướng (Lên / Trái / Xuống / Phải). Robot tự động xoay góc hướng mặt $\theta_{\text{robot}}$ mượt mà theo vector chuyển động. |
| **`Shift`** hoặc **`X`** | **An toàn HRI** | Bật / tắt chế độ **Đi Chậm An Toàn** ($v \le 0.3 \cdot v_{\text{max}}$). Bắt buộc sử dụng khi bước vào không gian hẹp Trong Nhà (Map 5) hoặc tiếp cận đám đông để tránh xâm phạm vùng cá nhân ($< 0.70\text{ m}$). |
| **`Space`** *(Phím Cách)* | **Phanh khẩn / Minigame** | - Bình thường: Phanh dừng lập tức ($v = 0$), đưa Robot về trạng thái đứng yên để đủ điều kiện giao tiếp.<br>- Trong Mini-game Câu Cá: Nhấp nhả phím Space để điều khiển thanh bắt cá xanh lá bám theo chú cá. |
| **`E`** | **Tương tác Đa năng** | Phím tương tác hành động cốt lõi:<br>- Đứng trong Vùng Quạt Xanh trước mặt NPC để nhận đơn / giao hàng / trò chuyện.<br>- Đứng trước luống cây / bụi quả bấm `[E]` để thu hoạch.<br>- Đứng tại Bến Hồ bấm `[E]` để thả cần / giật phao câu cá.<br>- Đứng trên thảm đỏ cửa nhà bấm `[E]` để mở cửa vào/ra Map 5. |
| **`G`** | **Tặng Quà (Gift)** | Tặng vật phẩm đang kích hoạt trên Hotbar cho NPC đang đối diện trong Vùng Quạt Xanh (tăng mạnh điểm Tim nếu đúng món `loved_items` hoặc `liked_items`). |
| **`Z`** *(hoặc Click Chuột)* | **Chọn Ô Hành Trang** | Chuyển đổi vị trí ô chọn kích hoạt (Active Inventory Slot) qua lại giữa các ô trên khay chứa đồ của Robot. |
| **`1` – `4`** *(hoặc `1` – `6`)* | **Phím Số Hotbar** | Chọn nhanh trực tiếp ô hành trang tương ứng từ số 1 đến 4 (hoặc đến 6 khi đã nâng cấp khay hàng Lv.2). |
| **`J`** | **Sổ Tay Thị Trấn** | Bật / tắt Giao diện Sổ Tay Cư Dân & Bách Khoa Toàn Thư 3 Tab (`Journal & Compendium`):<br>- Tab 1: Hồ sơ 12 Cư dân & Mốc Tim thiện cảm.<br>- Tab 2: Thư viện Đơn hàng & Tin đồn bí mật.<br>- Tab 3: Hệ thống Lưu / Tải 3 Slot Game & Hướng dẫn cơ chế Core Loop. |
| **`U`** | **Xưởng Mộc Robin** | Mở Bảng Mua Nâng Cấp Robot tại Xưởng Mộc của Robin: nâng cấp khay đồ lên 6 ô, phanh từ tính giảm quán tính, cảm biến HRI cảnh báo sớm. (Giảm giá 20% khi đạt 3 ♥ với Robin). |
| **`N`** | **Kết Thúc Ngày Sớm** | Cho Robot kết thúc ngày làm việc sớm (trước mốc tự động 22:00), mở **Bảng Thống Kê Cuối Ngày (End-of-Day Summary)** tổng kết doanh thu và tự động qua đêm sang ngày mới. |
| **`V`** | **Đổi Thời Tiết** | Chuyển đổi qua lại giữa thời tiết **Nắng Đẹp** và **Mưa Rào Nông Trại** (kiểm thử hiệu ứng đất ẩm ướt và độ ma sát mặt đường). |
| **`K`** | **Đổi Mùa Luân Phiên** | Đổi mùa theo vòng lặp tuần hoàn: **Xuân → Hè → Thu → Đông → Xuân** (thay đổi bảng màu cây cối, danh mục đơn hàng và nhạc nền theo mùa). |
| **`L`** | **Lễ Hội Thị Trấn** | Bật / tắt Chế độ **Lễ Hội Hoa Anh Đào** tại Quảng trường Map 1 (cánh hoa bay ngập tràn, cư dân tập trung đông đúc và bật nhạc hội tươi vui). |
| **`O`** | **Sự Kiện Ngẫu Nhiên** | Kích hoạt hoặc chuyển đổi nhanh tuần tự giữa **7 Sự Kiện Biến Động Thế Giới** (Mưa sao băng, Đơn SOS, Cừu lạc, Thương nhân du mục...). |
| **`M`** | **Bản Đồ Radar Minimap** | Bật / tắt Bản đồ Radar thu nhỏ ở góc màn hình: hiển thị vị trí Robot (chấm xanh), NPC giao việc (`!`), NPC nhận hàng (`?`) và các điểm thu hoạch. |
| **`H`** | **Hướng Dẫn Tân Thủ** | Bật / tắt Hộp thoại **Checklist 5 Bước Hướng Dẫn Tân Thủ** (di chuyển, hái nông sản, câu cá, giao hàng và nâng cấp khay đồ). |
| **`B`** | **Âm Thanh & Nhạc Nền** | Bật / tắt hệ thống Nhạc nền ngũ cung Procedural BGM và Bộ hiệu ứng âm thanh sống động SFX. |
| **`P`** | **AI Tự Hành (Autopilot)** | Chuyển đổi qua lại giữa chế độ **Người chơi lái thủ công** và **AI Tự Hành Điều Hướng Xã Hội (Social Autopilot)**. |
| **`F`** | **Vùng Quạt Xanh HRI** | Bật / tắt hiển thị hình quạt xanh tương tác lịch sự trước mặt NPC (hữu ích cho chế độ trực quan nghiên cứu hoặc chụp ảnh màn hình thẩm mỹ). |
| **`Tab`** | **Chuyển Bản Đồ Nhanh** | Nhảy nhanh qua lại giữa các Map (Map 1 → Map 2 → Map 3 → Map 4 → Map 5) phục vụ kiểm tra cảnh quan cấp tốc. |
| **`F5`** | **Lưu Nhanh (Quick Save)** | Lưu tức thì trạng thái toàn bộ thế giới (vị trí, tài chính, đơn hàng, mốc tim, trạng thái ruộng) vào Slot 1 (`game/saves/slot_1.json`). |
| **`F9`** | **Tải Nhanh (Quick Load)** | Tải lại ngay lập tức dữ liệu thế giới đã lưu từ Slot 1 mà không cần tải lại trò chơi. |
| **`R`** | **Đặt Lại (Reset Level)** | Đặt lại vị trí ban đầu của Robot và khởi động lại vòng lặp nhiệm vụ trên bản đồ hiện tại. |
| **`ESC`** | **Đóng Cửa Sổ / Thoát** | Đóng ngay các hộp thoại hoặc bảng giao diện đang mở (Sổ tay `[J]`, Hướng dẫn `[H]`, Nâng cấp `[U]`, Thoại NPC), hoặc thoát trò chơi khi đang ở ngoài màn hình chính. |
