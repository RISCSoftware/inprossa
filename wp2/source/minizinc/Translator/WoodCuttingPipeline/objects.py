code_objects = f"""
class Interval:
    def __init__(self,
                 start: DSInt(0, MAX_BOARD_LENGTH),
                 end: DSInt(0, MAX_BOARD_LENGTH)
                 ):
        self.start = start
        self.end = end

class Board:
    def __init__(self,
                 length: DSInt(0, MAX_BOARD_LENGTH),
                 bad_intervals: DSList(MAX_N_INTERVALS, Interval) = [],
                 curved_intervals: DSList(MAX_N_INTERVALS, Interval) = []):
        self.length = length
        self.bad_intervals = bad_intervals
        self.curved_intervals = curved_intervals

class Piece:
    def __init__(self,
                 length: DSInt(0, MAX_BOARD_LENGTH) = 0,
                 quality: DSBool = True):
        self.length = length
        self.quality = quality

class CutList:
    def __init__(self,
                 MAX_N_CUTS: int):
        self.position_list: DSList(MAX_N_CUTS, DSInt(0, MAX_BOARD_LENGTH))
"""

