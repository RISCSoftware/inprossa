from pydantic import BaseModel
import typing
from models.Interval import Interval

class BeamConfiguration(BaseModel):
    # Length of the beam
    BeamLength: int
    # (unused) Width of the beam
    BeamWidth: int
    # (unused) Height of the beam
    BeamHeight: int
    # Number of layers in beam
    NumberOfLayers: int
    # Number of beams
    NumberOfBeams: int
    # Space at the beginning of the beam, where no two boards must meet
    BeamSkipStart: int
    # Space at the end of the beam, where no two boards must meet
    BeamSkipEnd: int    
    ## Thickness of the saw blade
    #SawBladeThickness: int
    # Minimum length of a wooden board in a layer
    MinLengthOfBoardInLayer: int
    # Distance between two board touches
    GapToBoardAbutInConsecutiveLayers: int
    # Maximum shift of a cut of a curved board
    MaxShiftCurvedCut: int
    # Static forbidden zones in each layer of every beam
    StaticForbiddenZones: list[Interval]
