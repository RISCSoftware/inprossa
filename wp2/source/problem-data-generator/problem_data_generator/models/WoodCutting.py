from pydantic import BaseModel
from models.BeamConfiguration import BeamConfiguration
from models.InputBoard import InputBoard

class WoodCutting(BaseModel):
    BeamConfiguration: BeamConfiguration
    InputBoards: list[InputBoard]