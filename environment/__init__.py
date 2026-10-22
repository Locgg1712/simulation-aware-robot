"""Environment package exports with lazy loading to avoid import cycles."""

_PHYSICS_EXPORTS = {
    "check_circle_circle_collision",
    "check_circle_rect_collision",
    "check_robot_static_collision",
    "check_robot_full_collision",
    "cast_lidar_rays",
}
_TOPOLOGY_EXPORTS = {
    "TopologyID",
    "TOPOLOGY_NAMES",
    "TRAIN_TOPOLOGIES",
    "VAL_TOPOLOGIES",
    "TEST_TOPOLOGIES",
}


def __getattr__(name: str):
    if name in _PHYSICS_EXPORTS:
        from . import physics

        return getattr(physics, name)
    if name in _TOPOLOGY_EXPORTS:
        from . import topology

        return getattr(topology, name)
    if name == "MapGenerator":
        from .map_generator import MapGenerator

        return MapGenerator
    if name == "SpawnManager":
        from .spawn_manager import SpawnManager

        return SpawnManager
    if name == "World":
        from .world import World

        return World
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = sorted(
    _PHYSICS_EXPORTS
    | _TOPOLOGY_EXPORTS
    | {"MapGenerator", "SpawnManager", "World"}
)