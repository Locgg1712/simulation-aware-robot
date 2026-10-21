from enum import Enum
import math
from .base_object import BaseObject, ObjectType


class ShapeType(Enum):
    CIRCLE = "circle"
    RECTANGLE = "rectangle"


class StaticObject(BaseObject):
    """
    Vật thể tĩnh (Static Object): vị trí cố định, vận tốc bằng 0.
    Hỗ trợ 2 dạng hình học: CIRCLE và RECTANGLE (BoundingBox).
    """

    def __init__(
        self,
        obj_id: int,
        shape: ShapeType,
        x: float,
        y: float,
        radius: float = 0.0,
        width: float = 0.0,
        height: float = 0.0,
        name: str = "static_obstacle",
    ):
        self.shape = shape
        if shape == ShapeType.RECTANGLE:
            self.rect_x = float(x)
            self.rect_y = float(y)
            self.width = float(width)
            self.height = float(height)
            center_x = self.rect_x + self.width / 2.0
            center_y = self.rect_y + self.height / 2.0
            bounding_radius = math.hypot(self.width / 2.0, self.height / 2.0)
            super().__init__(
                obj_id=obj_id,
                x=center_x,
                y=center_y,
                radius=bounding_radius,
                obj_type=ObjectType.STATIC,
                name=name,
            )
        else:
            self.rect_x = float(x - radius)
            self.rect_y = float(y - radius)
            self.width = float(radius * 2.0)
            self.height = float(radius * 2.0)
            super().__init__(
                obj_id=obj_id,
                x=x,
                y=y,
                radius=radius,
                obj_type=ObjectType.STATIC,
                name=name,
            )

    @property
    def bbox(self) -> tuple[float, float, float, float]:
        """Trả về (x_min, y_min, width, height)."""
        return (self.rect_x, self.rect_y, self.width, self.height)
