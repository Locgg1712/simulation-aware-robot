# Phase 2-3: Dự đoán vị trí tương lai trong 1-3 giây
# perception/trajectory_predictor.py
import math


def predict_constant_velocity_trajectory(
    x: float,
    y: float,
    v: float,
    theta: float,
    dt: float = 0.1,
    horizon_sec: float = 2.5,
    num_samples: int = 6,
) -> list[tuple[float, float]]:
    """
    Tính danh sách tọa độ dự đoán (hat_x, hat_y) trong khoảng thời gian T_pred.
    """
    if v < 1e-3:
        return []
    total_steps = max(1, int(round(horizon_sec / dt)))
    stride = max(1, total_steps // num_samples)
    preds: list[tuple[float, float]] = []
    vx = v * math.cos(theta)
    vy = v * math.sin(theta)
    for k in range(stride, total_steps + 1, stride):
        t_offset = k * dt
        preds.append((x + vx * t_offset, y + vy * t_offset))
    return preds