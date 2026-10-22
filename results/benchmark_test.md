# Kết quả Đánh giá Benchmark (Tập `TEST`)

| Phương pháp (Baseline) | Success (%) | Collision (%) | Timeout (%) | Nav Time (s) | Path Len (m) | Social Intrusion (%) | Group Split | Smart Wait | Mean Reward |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Baseline 1: A* + Basic Avoidance** | 20.0 | 80.0 | 0.0 | 18.95 | 15.98 | 9.33 | 0.40 | 3.14 | -91.10 |
| **Baseline 2: A* + Social Rules** | 46.0 | 54.0 | 0.0 | 18.90 | 15.97 | 4.42 | 0.08 | 4.94 | -8.78 |
| **Baseline 3: A* + RL (No Social Context)** | 0.0 | 24.0 | 76.0 | 47.98 | 0.81 | 2.98 | 0.04 | 6.64 | -57.73 |
| **Baseline 4: A* + RL (Full Context)** | 0.0 | 40.0 | 60.0 | 46.79 | 2.64 | 1.92 | 0.02 | 10.88 | -67.70 |
