from pydantic import BaseModel

class Interval(BaseModel):
    Begin: int
    End: int
    