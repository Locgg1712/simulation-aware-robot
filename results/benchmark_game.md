# Kết quả Đánh giá Benchmark (Tập `GAME`)

| Phương pháp (Baseline) | Success (%) | Collision (%) | Timeout (%) | Nav Time (s) | Path Len (m) | Social Intrusion (%) | Group Split | Smart Wait | Mean Reward |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Baseline 1: A* + Basic Avoidance** | 30.0 | 70.0 | 0.0 | 10.83 | 10.42 | 11.70 | 0.10 | 0.10 | -40.17 |
| **Baseline 2: A* + Social Rules** | 60.0 | 40.0 | 0.0 | 11.93 | 10.53 | 7.40 | 0.00 | 5.50 | +26.20 |
| **Baseline 3: A* + RL (No Social Context)** | 30.0 | 70.0 | 0.0 | 10.77 | 10.58 | 9.86 | 0.40 | 0.00 | -48.18 |
| **Baseline 4: A* + RL (Full Context)** | 30.0 | 70.0 | 0.0 | 10.90 | 10.43 | 8.07 | 0.20 | 3.10 | -40.61 |
