# Kết quả Đánh giá Benchmark (Tập `VAL`)

| Phương pháp (Baseline) | Success (%) | Collision (%) | Timeout (%) | Nav Time (s) | Path Len (m) | Social Intrusion (%) | Group Split | Smart Wait | Mean Reward |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Baseline 1: A* + Basic Avoidance** | 46.0 | 54.0 | 0.0 | 17.15 | 15.75 | 9.02 | 0.18 | 3.38 | -16.36 |
| **Baseline 2: A* + Social Rules** | 64.0 | 36.0 | 0.0 | 17.93 | 15.92 | 6.89 | 0.10 | 6.42 | +30.12 |
| **Baseline 3: A* + RL (No Social Context)** | 0.0 | 12.0 | 88.0 | 53.71 | 0.42 | 0.53 | 0.02 | 15.70 | -38.21 |
| **Baseline 4: A* + RL (Full Context)** | 0.0 | 30.0 | 70.0 | 47.23 | 2.00 | 0.72 | 0.02 | 7.92 | -54.08 |
