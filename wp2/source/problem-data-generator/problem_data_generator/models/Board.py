from pydantic import BaseModel, computed_field
from enum import Enum
import typing

class BoardPartQuality(Enum):
    # The board part is good and can be used in a beam
    GOOD = 1
    # The board part is of bad quality and must not be used
    BAD = 2
    # The board part is curved and must be cut
    CURVE = 3
    # The board part is scrap (used for good parts, which are discarded)
    SCRAP = 4

class InputBoardPart(BaseModel):
    Id: int
    StartPosition: int
    EndPosition: int
    Quality: BoardPartQuality

    @computed_field
    @property
    def Length(self) -> int:
        return self.EndPosition - self.StartPosition
    
    @computed_field
    @property
    def Interval(self) -> tuple[int, int]:
        return (self.StartPosition, self.EndPosition)

class Board(BaseModel):
    Id: int
    Length: int
    Width: int
    Height: int
    ScanBoardParts: list[InputBoardPart]
