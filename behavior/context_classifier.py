# Phase 3: Phân loại ALONE, APPROACHING, CROSSING, INTERACTING
# behavior/context_classifier.py
import math
from typing import Sequence
from objects.robot import Robot
from human.human_agent import HumanAgent, HumanActivity, SocialContext
from human.groups import HumanGroup


def classify_all_humans_context(
    humans: Sequence[HumanAgent],
    groups: Sequence[HumanGroup],
    robot: Robot | None,
):
    """
    Tự động suy luận và gán nhãn SocialContext cho từng người ở mỗi bước thời gian dt
    theo đúng quy tắc toán học tại Mục 7.1 của Tài liệu Đặc tả:
    1. INTERACTING: 2-4 người ở trạng thái STANDING, khoảng cách d_ij in [0.8m, 2.0m],
       góc nhìn theta hướng vào tâm chung của nhóm.
    2. GROUP: >= 2 người cùng di chuyển với khoảng cách d_ij < 1.5m và |theta_i - theta_j| < 25 deg.
    3. CROSSING: Quỹ đạo dự đoán trong 3.0s tới của người và vector hướng đi của robot
       cắt nhau tại điểm giao có |t_robot - t_human| < 1.5s.
    4. APPROACHING: Khoảng cách tới robot d < 5.0m, v_human > 0.2 m/s và vector vận tốc
       hướng ngược về vị trí robot với góc lệch < 30 deg.
    5. ALONE: Các trường hợp còn lại.
    """
    # Bước 1: Mặc định gán ALONE và kiểm tra điều kiện nhóm (INTERACTING / GROUP)
    interacting_ids: set[int] = set()
    group_ids: set[int] = set()

    # Kiểm tra từ danh sách nhóm đã cấu trúc
    for grp in groups:
        if len(grp.members) >= 2:
            if grp.group_type.value == "INTERACTING":
                for m in grp.members:
                    interacting_ids.add(m.id)
            elif grp.group_type.value == "GROUP":
                for m in grp.members:
                    group_ids.add(m.id)

    # Kiểm tra động giữa các cặp người gần nhau (nếu tự hình thành nhóm)
    n = len(humans)
    for i in range(n):
        hi = humans[i]
        if hi.x < 0.0 or hi.y < 0.0:
            continue
        for j in range(i + 1, n):
            hj = humans[j]
            if hj.x < 0.0 or hj.y < 0.0:
                continue
            dist_ij = math.hypot(hi.x - hj.x, hi.y - hj.y)
            # Điều kiện INTERACTING: STANDING, d_ij in [0.6m, 2.2m], nhìn về nhau
            if (
                hi.activity == HumanActivity.STANDING
                and hj.activity == HumanActivity.STANDING
                and 0.6 <= dist_ij <= 2.2
            ):
                cx = 0.5 * (hi.x + hj.x)
                cy = 0.5 * (hi.y + hj.y)
                ang_i = _angle_diff(hi.theta, math.atan2(cy - hi.y, cx - hi.x))
                ang_j = _angle_diff(hj.theta, math.atan2(cy - hj.y, cx - hj.x))
                if ang_i < math.radians(40.0) and ang_j < math.radians(40.0):
                    interacting_ids.add(hi.id)
                    interacting_ids.add(hj.id)

            # Điều kiện GROUP: Cùng di chuyển, d_ij < 1.5m, lệch hướng < 25 độ
            elif (
                hi.speed > 0.2
                and hj.speed > 0.2
                and dist_ij < 1.5
                and _angle_diff(hi.theta, hj.theta) < math.radians(25.0)
            ):
                group_ids.add(hi.id)
                group_ids.add(hj.id)

    # Bước 2: Đánh giá tương tác trực tiếp với Robot (CROSSING / APPROACHING)
    for h in humans:
        if h.x < 0.0 or h.y < 0.0:
            h.social_context = SocialContext.ALONE
            continue
        if h.id in interacting_ids:
            h.social_context = SocialContext.INTERACTING
            continue

        # Ngay cả khi người đi trong GROUP, nếu đang cắt ngang hoặc lao thẳng vào Robot ở gần
        # thì ưu tiên cảnh báo CROSSING / APPROACHING, ngược lại giữ nhãn GROUP
        if robot is not None:
            if _is_crossing_robot_path(h, robot):
                h.social_context = SocialContext.CROSSING
                continue
            if _is_approaching_robot(h, robot):
                h.social_context = SocialContext.APPROACHING
                continue

        if h.id in group_ids:
            h.social_context = SocialContext.GROUP
        else:
            h.social_context = SocialContext.ALONE


def _is_approaching_robot(human: HumanAgent, robot: Robot) -> bool:
    """
    Kiểm tra điều kiện APPROACHING:
    - Khoảng cách tới robot d < 5.0m
    - Người đang di chuyển v_human > 0.2 m/s
    - Vector vận tốc hướng về phía robot với góc lệch < 30 độ
    """
    if human.speed <= 0.20:
        return False

    dx = robot.x - human.x
    dy = robot.y - human.y
    dist = math.hypot(dx, dy)
    if dist >= 5.0 or dist < 1e-5:
        return False

    angle_to_robot = math.atan2(dy, dx)
    angle_error = _angle_diff(human.theta, angle_to_robot)
    return angle_error < math.radians(30.0)


def _is_crossing_robot_path(human: HumanAgent, robot: Robot) -> bool:
    """
    Kiểm tra điều kiện CROSSING:
    Quỹ đạo dự đoán trong 3.0s tới của người và tia hướng mũi của robot cắt nhau
    tại một điểm giao có khoảng cách thời gian |t_robot - t_human| < 1.5s.
    """
    if human.speed <= 0.20:
        return False

    dist_hr = math.hypot(human.x - robot.x, human.y - robot.y)
    if dist_hr > 6.0:
        return False

    # Vector đơn vị hướng mũi của Robot và hướng đi của Human
    r_dx = math.cos(robot.theta)
    r_dy = math.sin(robot.theta)
    h_dx = math.cos(human.theta)
    h_dy = math.sin(human.theta)

    # Giải hệ phương trình giao điểm của 2 tia:
    # P_robot + s_r * u_robot = P_human + s_h * u_human
    det = r_dx * (-h_dy) - r_dy * (-h_dx)
    if abs(det) < 0.15:  # Gần như song song -> không phải cắt ngang (Crossing)
        return False

    rhs_x = human.x - robot.x
    rhs_y = human.y - robot.y
    s_r = (rhs_x * (-h_dy) - rhs_y * (-h_dx)) / det
    s_h = (r_dx * rhs_y - r_dy * rhs_x) / det

    # Điểm giao phải nằm ở phía trước mặt cả Robot và Human
    if s_r <= 0.0 or s_h <= 0.0:
        return False

    # Ước lượng thời gian tới điểm giao (giả sử robot di chuyển ở tốc độ mục tiêu >= 0.6 m/s)
    eff_robot_v = max(0.6, robot.v)
    t_robot = s_r / eff_robot_v
    t_human = s_h / human.speed

    if t_human > 3.0 or t_robot > 3.5:
        return False

    return abs(t_robot - t_human) < 1.5


def _angle_diff(a: float, b: float) -> float:
    """Trả về độ lệch góc tuyệt đối trong đoạn [0, pi]."""
    diff = math.atan2(math.sin(a - b), math.cos(a - b))
    return abs(diff)