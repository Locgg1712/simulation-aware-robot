# Phase 5: Lớp bọc chuẩn Gymnasium ContextAwareNavEnv(gym.Env)
# rl/gym_env.py
from pathlib import Path
import random
from typing import Any
import gymnasium as gym
from gymnasium import spaces
import numpy as np
import yaml

from environment.topology import (
    GAME_TOPOLOGIES,
    TRAIN_TOPOLOGIES,
    VAL_TOPOLOGIES,
    TEST_TOPOLOGIES,
)
from environment.world import World
from objects.robot import RobotAction
from .state_builder import StateBuilder
from .reward_calculator import RewardCalculator

PROJECT_ROOT = Path(__file__).resolve().parent.parent


class ContextAwareNavEnv(gym.Env):
    """
    Môi trường chuẩn Gymnasium cho bài toán Context-Aware Robot Navigation
    trong thế giới FarmBot Town (Maps 1-4) & các kịch bản xã hội (Topologies 5-15):
    - Observation Space: Box(low=-5.0, high=5.0, shape=(128,), dtype=np.float32)
    - Action Space:
        + Discrete(6): FORWARD, TURN_LEFT, TURN_RIGHT, SLOW_DOWN, STOP, WAIT
        + Hoặc Box(2,) nếu bật continuous_actions=True
    """

    metadata = {"render_modes": ["None"], "render_fps": 30}

    def __init__(
        self,
        config_path: str = "configs/default_config.yaml",
        rl_config_path: str = "configs/rl_hyperparams.yaml",
        split: str = "train",
        topology_id: int | None = None,
        include_social_context: bool = True,
        continuous_actions: bool = False,
        render_mode: str | None = None,
    ):
        super().__init__()

        self.config = self._load_yaml(config_path)
        self.rl_config = self._load_yaml(rl_config_path)

        self.split = split
        self.fixed_topology_id = topology_id
        self.include_social_context = bool(include_social_context)
        self.continuous_actions = bool(continuous_actions)
        self.render_mode = render_mode

        # Khởi tạo World, StateBuilder và RewardCalculator
        self.world = World(self.config)
        self.world.use_social_astar = self.include_social_context
        self.state_builder = StateBuilder(
            include_social_context=self.include_social_context
        )

        reward_cfg = dict(self.rl_config.get("reward_weights", {}))
        reward_cfg["use_social_reward"] = self.include_social_context
        self.reward_calculator = RewardCalculator(reward_cfg)

        # Định nghĩa Không gian Quan sát 106 chiều (Robot-centric State Space)
        self.observation_space = spaces.Box(
            low=-5.0,
            high=5.0,
            shape=(StateBuilder.STATE_DIM,),
            dtype=np.float32,
        )

        # Định nghĩa Không gian Hành động (Mục 9.2)
        if self.continuous_actions:
            v_max = float(self.config["robot"]["v_max"])
            omega_max = float(self.config["robot"]["omega_max"])
            self.action_space = spaces.Box(
                low=np.array([0.0, -omega_max], dtype=np.float32),
                high=np.array([v_max, omega_max], dtype=np.float32),
                dtype=np.float32,
            )
        else:
            self.action_space = spaces.Discrete(len(RobotAction))

        self.episode_reward: float = 0.0
        self.last_reward_breakdown: dict = {}

    @staticmethod
    def _load_yaml(path_str: str) -> dict:
        path = Path(path_str)
        if not path.exists():
            alt = PROJECT_ROOT / path_str
            if alt.exists():
                path = alt
            else:
                return {}
        with open(path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}

    def _select_topology_id(self) -> int:
        if self.fixed_topology_id is not None:
            return int(self.fixed_topology_id)
        if self.split == "game":
            return random.choice(GAME_TOPOLOGIES)
        if self.split == "train":
            # Ưu tiên lấy mẫu cả 4 bản đồ Game FarmBot Town (1..4) lẫn các bản đồ Train (5..9)
            weighted_pool = GAME_TOPOLOGIES + TRAIN_TOPOLOGIES
            return random.choice(weighted_pool)
        if self.split == "val":
            return random.choice(VAL_TOPOLOGIES)
        if self.split == "test":
            return random.choice(TEST_TOPOLOGIES)
        return random.randint(1, 15)

    def reset(
        self,
        *,
        seed: int | None = None,
        options: dict[str, Any] | None = None,
    ) -> tuple[np.ndarray, dict[str, Any]]:
        super().reset(seed=seed)

        topo_id = None
        if options and "topology_id" in options:
            topo_id = int(options["topology_id"])
        else:
            topo_id = self._select_topology_id()

        self.world.use_social_astar = self.include_social_context
        self.world.reset(seed=seed, topology_id=topo_id)
        self.episode_reward = 0.0
        self.last_reward_breakdown = {
            "r_total": 0.0,
            "r_terminal": 0.0,
            "r_progress": 0.0,
            "r_time": 0.0,
            "r_social": 0.0,
            "r_group": 0.0,
            "r_context": 0.0,
        }

        obs = self.state_builder.build(self.world)
        info = self.world.get_info()
        info["reward_breakdown"] = self.last_reward_breakdown
        info["episode_reward"] = round(self.episode_reward, 2)

        return obs, info

    def step(
        self, action: int | np.ndarray
    ) -> tuple[np.ndarray, float, bool, bool, dict[str, Any]]:
        robot = self.world.robot
        assert robot is not None

        prev_goal_dist = robot.distance_to_goal()
        prev_subgoal_dist = self.world.subgoal_info["dist_to_subgoal"]

        # Áp dụng hành động liên tục hoặc rời rạc
        discrete_act: int | None = None
        if self.continuous_actions:
            act_arr = np.asarray(action, dtype=np.float32).flatten()
            robot.set_continuous_velocity(float(act_arr[0]), float(act_arr[1]))
            self.world.step(action=None)
        else:
            discrete_act = int(action)
            self.world.step(action=discrete_act)

        # Tính toán Reward & xây dựng vector Observation 106 chiều
        reward, breakdown = self.reward_calculator.compute(
            world=self.world,
            action=discrete_act,
            prev_goal_dist=prev_goal_dist,
            prev_subgoal_dist=prev_subgoal_dist,
        )
        self.episode_reward += reward
        self.last_reward_breakdown = breakdown

        obs = self.state_builder.build(self.world)

        terminated = bool(self.world.is_collision or self.world.is_goal_reached)
        truncated = bool(
            (not terminated) and (self.world.step_count >= self.world.max_steps)
        )

        info = self.world.get_info()
        info["reward_breakdown"] = breakdown
        info["episode_reward"] = round(self.episode_reward, 2)
        info["is_success"] = bool(self.world.is_goal_reached)

        return obs, float(reward), terminated, truncated, info

    def render(self):
        return None

    def close(self):
        pass
