# Phase 3: Tính toán hàm Gaussian bất đối xứng & vi phạm xã hội
# human/social_space.py
import math
from typing import Sequence
from .human_agent import HumanAgent
from .groups import HumanGroup

# Tham số chuẩn theo mục 7.2 của Đặc tả Kỹ thuật
SIGMA_0 = 0.80      # Độ lệch chuẩn cơ sở phía trước (m)
K_V = 0.50          # Hệ số giãn phía trước theo vận tốc (s)
SIGMA_REAR = 0.50   # Độ lệch chuẩn phía sau (m)
SIGMA_SIDE = 0.60   # Độ lệch chuẩn hai bên (m)
SOCIAL_COST_THRESHOLD = 0.22  # Ngưỡng bắt đầu tính vi phạm vùng cá nhân


def get_gaussian_ellipse_axes(human: HumanAgent) -> tuple[float, float, float]:
    """
    Trả về (sigma_front, sigma_rear, sigma_side) của hàm Gaussian bất đối xứng
    quanh một người dựa trên tốc độ hiện tại v_h.
    """
    sigma_front = SIGMA_0 + K_V * human.speed
    return sigma_front, SIGMA_REAR, SIGMA_SIDE


def compute_personal_space_cost(px: float, py: float, human: HumanAgent) -> float:
    """
    Tính giá trị hàm chi phí không gian cá nhân C_social(px, py) in [0, 1]
    quanh vị trí người (x_h, y_h) với hướng di chuyển theta_h.
    """
    dx = px - human.x
    dy = py - human.y

    # Chuyển tọa độ điểm (px, py) vào hệ quy chiếu cục bộ của người (trục X_local dọc theo theta_h)
    cos_t = math.cos(human.theta)
    sin_t = math.sin(human.theta)
    x_local = dx * cos_t + dy * sin_t   # > 0 là phía trước mặt người, < 0 là phía sau lưng
    y_local = -dx * sin_t + dy * cos_t  # Phương ngang hai bên

    sigma_front, sigma_rear, sigma_side = get_gaussian_ellipse_axes(human)
    sigma_long = sigma_front if x_local >= 0.0 else sigma_rear

    exponent = -0.5 * (
        (x_local / max(1e-4, sigma_long)) ** 2
        + (y_local / max(1e-4, sigma_side)) ** 2
    )
    return math.exp(exponent)


def evaluate_social_violations(
    robot_x: float,
    robot_y: float,
    robot_radius: float,
    humans: Sequence[HumanAgent],
    groups: Sequence[HumanGroup],
    threshold: float = SOCIAL_COST_THRESHOLD,
) -> dict:
    """
    Kiểm tra và tính toán chi tiết mức độ vi phạm không gian xã hội tại vị trí Robot:
    - personal_intrusion: True nếu max C_social > threshold
    - max_social_cost: Giá trị C_social lớn nhất đối với tất cả con người
    - social_penalty: Giá trị phạt trong khoảng [-2.0, -0.5] khi xâm phạm vùng Gaussian
    - group_intrusion: True nếu Robot đi vào O-Space hoặc cắt ngang nhóm (Group Splitting)
    - group_penalty: -5.0 nếu vi phạm nhóm tương tác
    """
    max_cost = 0.0
    intruded_humans: list[int] = []

    for h in humans:
        if h.x < 0.0 or h.y < 0.0:
            continue
        cost = compute_personal_space_cost(robot_x, robot_y, h)
        if cost > max_cost:
            max_cost = cost
        if cost > threshold:
            intruded_humans.append(h.id)

    personal_intrusion = len(intruded_humans) > 0
    social_penalty = 0.0
    if personal_intrusion:
        # Nội suy tuyến tính mức phạt từ -0.5 đến -2.0 theo cường độ xâm phạm
        ratio = min(1.0, (max_cost - threshold) / max(1e-4, 1.0 - threshold))
        social_penalty = -(0.5 + 1.5 * ratio)

    group_splitting = False
    ospace_intrusion = False
    for grp in groups:
        if grp.is_robot_inside_ospace(robot_x, robot_y, robot_radius):
            ospace_intrusion = True
        if grp.is_robot_splitting_group(robot_x, robot_y):
            group_splitting = True

    group_penalty = -5.0 if (group_splitting or ospace_intrusion) else 0.0

    return {
        "personal_intrusion": personal_intrusion,
        "intruded_human_ids": intruded_humans,
        "max_social_cost": round(max_cost, 3),
        "social_penalty": round(social_penalty, 3),
        "ospace_intrusion": ospace_intrusion,
        "group_splitting": group_splitting,
        "group_penalty": round(group_penalty, 3),
    }