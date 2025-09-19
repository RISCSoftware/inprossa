class Interval:
    def __init__(self, start: int, end: int):
        self.start = start
        self.end = end

class Board:
    def __init__(self,
                 length: int,
                 bad_intervals: list[Interval] = [],
                 curved_intervals: list[Interval] = []):
        self.length = length
        self.bad_intervals = bad_intervals
        self.curved_intervals = curved_intervals

class Piece:
    def __init__(self,
                 length: int = 0,
                 quality: bool = True):
        self.length = length
        self.quality = quality

class CutList:
    def __init__(self,
                 position_list: list[int]):
        self.position_list = position_list