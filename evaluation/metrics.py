# Phase 7: Tính Navigation, Safety, Social, Generalization metrics
import math
import numpy as np


class EpisodeTracker:
    def __init__(self):
        self.reset()

    def reset(self):
        self.steps = 0
        self.sim_time = 0.0
        self.path_length = 0.0
        self.total_reward = 0.0
        self.social_intrusion_steps = 0
        self.group_splitting_events = 0
        self.smart_wait_steps = 0
        self._prev_pos: tuple[float, float] | None = None
        self._prev_splitting = False

    def update(
        self,
        robot_pos: tuple[float, float],
        dt: float,
        step_reward: float,
        social_status: dict,
        reward_breakdown: dict,
    ):
        self.steps += 1
        self.sim_time += dt
        self.total_reward += float(step_reward)

        if self._prev_pos is not None:
            self.path_length += math.hypot(
                robot_pos[0] - self._prev_pos[0],
                robot_pos[1] - self._prev_pos[1],
            )
        self._prev_pos = (float(robot_pos[0]), float(robot_pos[1]))

        if social_status.get("personal_intrusion") or social_status.get("ospace_intrusion"):
            self.social_intrusion_steps += 1

        curr_splitting = bool(
            social_status.get("group_splitting") or social_status.get("ospace_intrusion")
        )
        if curr_splitting and not self._prev_splitting:
            self.group_splitting_events += 1
        self._prev_splitting = curr_splitting

        if float(reward_breakdown.get("r_context", 0.0)) > 0.0:
            self.smart_wait_steps += 1

    def finalize(self, is_goal_reached: bool, is_collision: bool, topology_id: int) -> dict:
        is_success = bool(is_goal_reached and not is_collision)
        is_col = bool(is_collision)
        is_timeout = bool(not is_success and not is_col)
        intrusion_ratio = 100.0 * self.social_intrusion_steps / max(1, self.steps)

        return {
            "topology_id": int(topology_id),
            "is_success": is_success,
            "is_collision": is_col,
            "is_timeout": is_timeout,
            "steps": self.steps,
            "navigation_time": round(self.sim_time, 2),
            "path_length": round(self.path_length, 3),
            "total_reward": round(self.total_reward, 3),
            "social_intrusion_steps": self.social_intrusion_steps,
            "social_intrusion_ratio": round(intrusion_ratio, 2),
            "group_splitting_count": self.group_splitting_events,
            "smart_wait_count": self.smart_wait_steps,
        }


def aggregate_metrics(episodes_data: list[dict]) -> dict:
    n = len(episodes_data)
    if n == 0:
        return {}

    success_eps = [ep for ep in episodes_data if ep["is_success"]]
    nav_times = [ep["navigation_time"] for ep in (success_eps if success_eps else episodes_data)]
    path_lengths = [ep["path_length"] for ep in (success_eps if success_eps else episodes_data)]

    total_steps_all = sum(ep["steps"] for ep in episodes_data)
    total_intrusion_steps = sum(ep["social_intrusion_steps"] for ep in episodes_data)

    return {
        "episodes": n,
        "success_rate": round(100.0 * sum(1 for ep in episodes_data if ep["is_success"]) / n, 2),
        "collision_rate": round(100.0 * sum(1 for ep in episodes_data if ep["is_collision"]) / n, 2),
        "timeout_rate": round(100.0 * sum(1 for ep in episodes_data if ep["is_timeout"]) / n, 2),
        "navigation_time": round(float(np.mean(nav_times)), 2),
        "path_length": round(float(np.mean(path_lengths)), 2),
        "social_intrusion_ratio": round(
            100.0 * total_intrusion_steps / max(1, total_steps_all), 2
        ),
        "group_splitting_count": round(
            float(np.mean([ep["group_splitting_count"] for ep in episodes_data])), 2
        ),
        "smart_wait_count": round(
            float(np.mean([ep["smart_wait_count"] for ep in episodes_data])), 2
        ),
        "mean_reward": round(
            float(np.mean([ep["total_reward"] for ep in episodes_data])), 2
        ),
    }