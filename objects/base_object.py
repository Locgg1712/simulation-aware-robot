from enum import Enum


class ObjectType(Enum):
    STATIC = "static"
    SEMI_STATIC = "semi_static"
    DYNAMIC = "dynamic"
    HUMAN = "human"
    ROBOT = "robot"


class BaseObject:
    """Lớp cơ sở cho toàn bộ thực thể trong môi trường 2D."""

    def __init__(
        self,
        obj_id: int,
        x: float,
        y: float,
        radius: float,
        obj_type: ObjectType,
        name: str = "",
    ):
        self.id = obj_id
        self.x = float(x)
        self.y = float(y)
        self.radius = float(radius)
        self.obj_type = obj_type
        self.name = name or f"{obj_type.value}_{obj_id}"

    @property
    def position(self) -> tuple[float, float]:
        return (self.x, self.y)
