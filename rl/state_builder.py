# Phase 5 & Mục 12.1: Chuyển đổi sang Robot-centric frame (128 chiều mở rộng cho FarmBot Town)
# rl/state_builder.py
import math
import numpy as np

from environment.world import World
from objects.semi_static_object import SemiStaticObject
from objects.dynamic_object import DynamicObject
from human.human_agent import HumanAgent


class StateBuilder:
    """
    Xây dựng vector trạng thái mở rộng Robot-centric S_t^ext có kích thước cố định 128 chiều
    (Mục 6.1 & Mục 12.1 trong Context-Aware-Robot-Navigation-Simulation.md):
    1. Khối 1 – Robot & Sub-goal State (6 chiều):
       [d_subgoal/D_max, sin(d_theta_sg), cos(d_theta_sg), d_goal/D_max, v/v_max, omega/omega_max]
    2. Khối 2 – Local Static Raycast (16 chiều):
       16 tia LiDAR chuẩn hóa theo R_sensor trong đoạn [0, 1]
    3. Khối 3 – Top-K Semi-static / Dynamic Objects (K = 3, mỗi vật thể 8 chiều -> 24 chiều):
       [dx_rel, dy_rel, dvx_rel, dvy_rel, radius, is_semi_static, is_dynamic, is_passable]
    4. Khối 4 – Top-M Humans / NPC Cư dân (M = 5, mỗi người 12 chiều -> 60 chiều):
       [dx_rel, dy_rel, dvx_rel, dvy_rel, sin(d_theta_h), cos(d_theta_h), OneHot(Activity)_3, OneHot(Context)_3]
    5. Khối 5 – Front Fan HRI Status (4 chiều):
       [d_npc/5.0, delta_alpha_npc/pi, delta_alpha_robot/pi, in_fan_ok]
    6. Khối 6 – Age & Social Safety Radar của NPC gần nhất (4 chiều):
       [is_adult, is_elder, is_child, R_safe/2.0]
    7. Khối 7 – Trạng thái Khay đồ, Đồng hồ Ngày-Đêm, Thời tiết Mưa/Tối, Mùa & Trái Tim An Toàn (6 chiều):
       [inv_ratio, has_quest_item, clock_norm, is_rain_or_night, season_idx_norm, safety_hearts_norm]
    8. Khối 8 – Vector Sự kiện Ngẫu nhiên Động CMDP (8 chiều):
       [event_active, event_type_id_norm, dx_event_rel/20.0, dy_event_rel/20.0, d_event/20.0,
        event_time_left_norm, event_reward_norm, is_ospace_hazard]
    Tổng cộng: 6 + 16 + 24 + 60 + 4 + 4 + 6 + 8 = 128 chiều (float32).
    """

    STATE_DIM = 128
    TOP_K_OBJECTS = 3
    OBJECT_FEATURE_DIM = 8
    TOP_M_HUMANS = 5
    HUMAN_FEATURE_DIM = 12

    def __init__(self, include_social_context: bool = True):
        # Nếu include_social_context = False (Baseline 3: RL No-Context),
        # các chiều ngữ cảnh xã hội, HRI, độ tuổi và sự kiện được đặt bằng 0.0
        self.include_social_context = bool(include_social_context)

    @staticmethod
    def _rotate_to_robot_frame(
        dx_world: float, dy_world: float, robot_theta: float
    ) -> tuple[float, float]:
        """
        Xoay vector (dx_world, dy_world) sang hệ tọa độ cục bộ của Robot:
        - Trục X_robot hướng thẳng theo mũi Robot (robot_theta).
        - Trục Y_robot hướng sang bên trái của Robot.
        """
        cos_t = math.cos(robot_theta)
        sin_t = math.sin(robot_theta)
        x_rel = dx_world * cos_t + dy_world * sin_t
        y_rel = -dx_world * sin_t + dy_world * cos_t
        return x_rel, y_rel

    def build(self, world: World) -> np.ndarray:
        robot = world.robot
        if robot is None:
            return np.zeros(self.STATE_DIM, dtype=np.float32)

        d_max = math.hypot(world.width, world.height)
        r_sensor = max(1e-5, robot.sensor_radius)
        v_max = max(1e-5, robot.v_max)
        omega_max = max(1e-5, robot.omega_max)

        robot_vx = robot.v * math.cos(robot.theta)
        robot_vy = robot.v * math.sin(robot.theta)

        # ----------------------------------------------------------------------
        # KHỐI 1: TRẠNG THÁI BẢN THÂN ROBOT & SUB-GOAL (6 CHIỀU)
        # ----------------------------------------------------------------------
        d_subgoal_norm = min(
            1.0, world.subgoal_info["dist_to_subgoal"] / max(1e-5, d_max)
        )
        ang_subgoal = world.subgoal_info["angle_to_subgoal"]
        sin_sg = math.sin(ang_subgoal)
        cos_sg = math.cos(ang_subgoal)
        d_goal_norm = min(1.0, robot.distance_to_goal() / max(1e-5, d_max))
        v_norm = np.clip(robot.v / v_max, 0.0, 1.0)
        omega_norm = np.clip(robot.omega / omega_max, -1.0, 1.0)

        robot_goal_vec = np.array(
            [d_subgoal_norm, sin_sg, cos_sg, d_goal_norm, v_norm, omega_norm],
            dtype=np.float32,
        )

        # ----------------------------------------------------------------------
        # KHỐI 2: 16 TIA LIDAR RAYCAST CỤC BỘ (16 CHIỀU)
        # ----------------------------------------------------------------------
        if len(world.lidar_distances) == 16:
            lidar_vec = np.array(
                [min(1.0, d / r_sensor) for d in world.lidar_distances],
                dtype=np.float32,
            )
        else:
            lidar_vec = np.ones(16, dtype=np.float32)

        # ----------------------------------------------------------------------
        # KHỐI 3: TOP-K VẬT THỂ BÁN TĨNH / ĐỘNG GẦN NHẤT (3 x 8 = 24 CHIỀU)
        # ----------------------------------------------------------------------
        objects_vec = np.zeros(
            self.TOP_K_OBJECTS * self.OBJECT_FEATURE_DIM, dtype=np.float32
        )

        candidates: list[tuple[float, SemiStaticObject | DynamicObject]] = []
        for door in world.local_perception.get("semi_static", []):
            dist = math.hypot(door.x - robot.x, door.y - robot.y)
            candidates.append((dist, door))
        for dyn in world.local_perception.get("dynamic", []):
            dist = math.hypot(dyn.x - robot.x, dyn.y - robot.y)
            candidates.append((dist, dyn))

        candidates.sort(key=lambda item: item[0])
        top_k_objs = [item[1] for item in candidates[: self.TOP_K_OBJECTS]]

        for i, obj in enumerate(top_k_objs):
            dx_w = obj.x - robot.x
            dy_w = obj.y - robot.y
            dx_rel, dy_rel = self._rotate_to_robot_frame(dx_w, dy_w, robot.theta)

            if isinstance(obj, DynamicObject):
                dvx_w = obj.vx - robot_vx
                dvy_w = obj.vy - robot_vy
                dvx_rel, dvy_rel = self._rotate_to_robot_frame(
                    dvx_w, dvy_w, robot.theta
                )
                is_semi = 0.0
                is_dyn = 1.0
                is_passable = 0.0
            else:
                dvx_rel, dvy_rel = self._rotate_to_robot_frame(
                    -robot_vx, -robot_vy, robot.theta
                )
                is_semi = 1.0
                is_dyn = 0.0
                is_passable = 1.0 if obj.passable else 0.0

            base_idx = i * self.OBJECT_FEATURE_DIM
            objects_vec[base_idx : base_idx + self.OBJECT_FEATURE_DIM] = [
                np.clip(dx_rel / r_sensor, -1.5, 1.5),
                np.clip(dy_rel / r_sensor, -1.5, 1.5),
                np.clip(dvx_rel / v_max, -2.5, 2.5),
                np.clip(dvy_rel / v_max, -2.5, 2.5),
                np.clip(obj.radius / r_sensor, 0.0, 1.0),
                is_semi,
                is_dyn,
                is_passable,
            ]

        # ----------------------------------------------------------------------
        # KHỐI 4: TOP-M CON NGƯỜI / NPC CƯ DÂN GẦN NHẤT (5 x 12 = 60 CHIỀU)
        # ----------------------------------------------------------------------
        humans_vec = np.zeros(
            self.TOP_M_HUMANS * self.HUMAN_FEATURE_DIM, dtype=np.float32
        )

        detected_humans: list[HumanAgent] = world.local_perception.get("humans", [])[
            : self.TOP_M_HUMANS
        ]

        for j, h in enumerate(detected_humans):
            dx_w = h.x - robot.x
            dy_w = h.y - robot.y
            dx_rel, dy_rel = self._rotate_to_robot_frame(dx_w, dy_w, robot.theta)

            dvx_w = h.vx - robot_vx
            dvy_w = h.vy - robot_vy
            dvx_rel, dvy_rel = self._rotate_to_robot_frame(
                dvx_w, dvy_w, robot.theta
            )

            rel_theta = math.atan2(
                math.sin(h.theta - robot.theta), math.cos(h.theta - robot.theta)
            )
            sin_ht = math.sin(rel_theta)
            cos_ht = math.cos(rel_theta)

            if self.include_social_context:
                act_onehot = h.activity_one_hot()
                ctx_onehot = h.context_one_hot_3()
            else:
                act_onehot = [0.0, 0.0, 0.0]
                ctx_onehot = [0.0, 0.0, 0.0]

            base_idx = j * self.HUMAN_FEATURE_DIM
            humans_vec[base_idx : base_idx + self.HUMAN_FEATURE_DIM] = [
                np.clip(dx_rel / r_sensor, -1.5, 1.5),
                np.clip(dy_rel / r_sensor, -1.5, 1.5),
                np.clip(dvx_rel / v_max, -3.5, 3.5),
                np.clip(dvy_rel / v_max, -3.5, 3.5),
                sin_ht,
                cos_ht,
                *act_onehot,
                *ctx_onehot,
            ]

        # ----------------------------------------------------------------------
        # KHỐI 5..8: NGỮ CẢNH MỞ RỘNG FARMBOT TOWN (4 + 4 + 6 + 8 = 22 CHIỀU)
        # ----------------------------------------------------------------------
        if self.include_social_context:
            hri = getattr(world, "hri_status", {})
            d_npc_norm = float(np.clip(hri.get("d_npc", 5.0) / 5.0, 0.0, 1.0))
            d_alpha_npc_norm = float(
                np.clip(hri.get("delta_alpha_npc", 0.0) / math.pi, -1.0, 1.0)
            )
            d_alpha_rob_norm = float(
                np.clip(hri.get("delta_alpha_robot", 0.0) / math.pi, -1.0, 1.0)
            )
            in_fan_flag = 1.0 if hri.get("in_fan_ok", False) else 0.0
            fan_vec = np.array(
                [d_npc_norm, d_alpha_npc_norm, d_alpha_rob_norm, in_fan_flag],
                dtype=np.float32,
            )

            age_radar = hri.get("nearest_age_radar", [1.0, 0.0, 0.0, 1.25 / 2.0])
            age_vec = np.array(age_radar, dtype=np.float32)

            clock_norm = float(
                np.clip((getattr(world, "clock_hour", 8.0) - 6.0) / 18.0, 0.0, 1.0)
            )
            is_rain_or_night = (
                1.0
                if (
                    getattr(world, "is_rain", False)
                    or getattr(world, "clock_hour", 8.0) >= 19.0
                )
                else 0.0
            )
            season_norm = float(
                np.clip(getattr(world, "season_idx", 0) / 3.0, 0.0, 1.0)
            )
            hearts_norm = float(
                np.clip(getattr(world, "safety_hearts", 3) / 3.0, 0.0, 1.0)
            )
            farm_env_vec = np.array(
                [
                    float(np.clip(getattr(world, "inv_ratio", 0.5), 0.0, 1.0)),
                    1.0 if getattr(world, "has_quest_item", True) else 0.0,
                    clock_norm,
                    is_rain_or_night,
                    season_norm,
                    hearts_norm,
                ],
                dtype=np.float32,
            )

            ev = getattr(world, "active_event", None)
            if ev is not None:
                ex_w = float(ev["x"]) - robot.x
                ey_w = float(ev["y"]) - robot.y
                ex_rel, ey_rel = self._rotate_to_robot_frame(ex_w, ey_w, robot.theta)
                d_ev = math.hypot(ex_w, ey_w)
                dur = max(1.0, float(ev.get("duration", 85.0)))
                t_left_norm = float(np.clip(float(ev.get("time_left", 0.0)) / dur, 0.0, 1.0))
                events_vec = np.array(
                    [
                        1.0,
                        float(np.clip(float(ev.get("type_id", 1)) / 7.0, 0.0, 1.0)),
                        float(np.clip(ex_rel / 20.0, -1.0, 1.0)),
                        float(np.clip(ey_rel / 20.0, -1.0, 1.0)),
                        float(np.clip(d_ev / 20.0, 0.0, 1.0)),
                        t_left_norm,
                        float(np.clip(float(ev.get("reward_norm", 0.5)), 0.0, 1.0)),
                        float(ev.get("is_ospace_hazard", 0.0)),
                    ],
                    dtype=np.float32,
                )
            else:
                events_vec = np.zeros(8, dtype=np.float32)
        else:
            fan_vec = np.zeros(4, dtype=np.float32)
            age_vec = np.zeros(4, dtype=np.float32)
            farm_env_vec = np.zeros(6, dtype=np.float32)
            events_vec = np.zeros(8, dtype=np.float32)

        state = np.concatenate(
            [
                robot_goal_vec,
                lidar_vec,
                objects_vec,
                humans_vec,
                fan_vec,
                age_vec,
                farm_env_vec,
                events_vec,
            ],
            axis=0,
        ).astype(np.float32)
        return state
