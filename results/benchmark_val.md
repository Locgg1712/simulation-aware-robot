# Kết quả Đánh giá Benchmark (Tập `VAL`)

| Phương pháp (Baseline) | Success (%) | Collision (%) | Timeout (%) | Nav Time (s) | Path Len (m) | Social Intrusion (%) | Group Split | Smart Wait | Mean Reward |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Baseline 1: A* + Basic Avoidance** | 70.0 | 30.0 | 0.0 | 15.81 | 15.13 | 0.84 | 0.10 | 3.10 | +53.80 |
| **Baseline 2: A* + Social Rules** | 90.0 | 10.0 | 0.0 | 16.53 | 15.51 | 0.06 | 0.00 | 3.40 | +101.05 |
| **Baseline 3: A* + RL (No Social Context)** | 30.0 | 60.0 | 10.0 | 15.67 | 14.30 | 2.28 | 0.10 | 0.80 | -32.25 |
| **Baseline 4: A* + RL (Full Context)** | 40.0 | 60.0 | 0.0 | 17.28 | 15.85 | 2.44 | 0.10 | 0.00 | -14.08 |
