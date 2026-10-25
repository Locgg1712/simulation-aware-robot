# Kết quả Đánh giá Benchmark (Tập `TEST`)

| Phương pháp (Baseline) | Success (%) | Collision (%) | Timeout (%) | Nav Time (s) | Path Len (m) | Social Intrusion (%) | Group Split | Smart Wait | Mean Reward |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Baseline 1: A* + Basic Avoidance** | 20.0 | 80.0 | 0.0 | 19.45 | 16.28 | 11.52 | 0.10 | 4.60 | -71.18 |
| **Baseline 2: A* + Social Rules** | 40.0 | 60.0 | 0.0 | 18.48 | 15.53 | 7.43 | 0.00 | 7.60 | -16.07 |
| **Baseline 3: A* + RL (No Social Context)** | 0.0 | 80.0 | 20.0 | 16.03 | 4.05 | 2.81 | 0.30 | 2.90 | -98.83 |
| **Baseline 4: A* + RL (Full Context)** | 0.0 | 100.0 | 0.0 | 6.42 | 5.77 | 7.17 | 0.20 | 0.50 | -103.85 |
