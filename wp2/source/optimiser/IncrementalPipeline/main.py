
from IncrementalPipeline.Machines.IncrementalMachine import IncrementalMachine
from IncrementalPipeline.Objects.board import Board

from IncrementalPipeline.configs.default_pipeline import pipeline
# input_list = [Piece(length=90),
#               Piece(length=20, good=0),
#               Piece(length=200),
#               Piece(length=0),
#               Piece(length=0),
#               Piece(length=0),
#               Piece(length=100),
#               Piece(length=0),
#               Piece(length=0),
#               Piece(length=0),
#               Piece(length=250),
#               Piece(length=0),
#               Piece(length=0),
#               Piece(length=100),
#               Piece(length=110)]

board1 = Board(length=500,
               bad_parts=[(100, 110), (120, 130), (330, 350), (450, 480)],
               # 100 waste but 110 if no reorder
               curved_parts=[])
board2 = Board(length=500,
               bad_parts=[(100, 150), (400, 440)],  # 90 waste
               curved_parts=[])
input_list = [board1,
              board2,
              board1,
              board2,]

if __name__ == "__main__":
    incremental_machine = IncrementalMachine(pipeline, input_list=input_list)

    incremental_machine.process()
