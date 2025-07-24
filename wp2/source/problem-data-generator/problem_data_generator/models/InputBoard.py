from pydantic import BaseModel
import typing
from models.Board import Board

class InputBoard(BaseModel):
    """
    Wraps a board and includes more information. 
    Position refers to the current input position, which may be a buffer
    """
    Position: int
    RawBoard: Board
