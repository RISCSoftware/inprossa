from IncrementalPipeline.Machines.Pipeline import Pipeline
from IncrementalPipeline.Machines.CheckingMachine import CheckingMachine
from IncrementalPipeline.Machines.ReorderingMachine import ReorderMachine
from IncrementalPipeline.Objects.piece import Piece, PieceVars
from IncrementalPipeline.Objects.board import Board, BoardVars
from gurobipy import Model, GRB
from IncrementalPipeline.Machines.IncrementalMachine import IncrementalMachine
from IncrementalPipeline.Machines.FilteringMachine import FilteringMachine
from IncrementalPipeline.Machines.CuttingMachine import CuttingMachine

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

input_list = [Board(length=500,
                    bad_parts=[(90, 100), (120, 130), (330, 350), (450, 480)],
                    curved_parts=[]),
              Board(length=500,
                    bad_parts=[(100, 150), (400, 440)],
                    curved_parts=[])]

if __name__ == "__main__":
    checking_machine = CheckingMachine(
        id=""
    )
    reordering_machine1 = ReorderMachine(
        id="1",
        input_type=PieceVars
    )
    reordering_machine2 = ReorderMachine(
        id="2",
        input_type=PieceVars
    )
    reordering_machine3 = ReorderMachine(
        id="3",
        input_type=PieceVars
    )
    filtering_machine = FilteringMachine(
        id=""
    )
    cutting_machine = CuttingMachine(
        id=""
    )
    pipeline = Pipeline(
        id="wood_processing_pipeline",
        machines=[cutting_machine, reordering_machine1, filtering_machine, checking_machine]
    )
    model = Model()
    vars_input_list = [BoardVars(model, board=board, id=f"board-{i}") for i, board in enumerate(input_list)]
    pipeline.impose_conditions(model, input_list=vars_input_list)
    model.setParam('TimeLimit', 6)  # Set a time limit for the optimization
    model.optimize()

    incremental_machine = IncrementalMachine(pipeline, input_list=input_list)
    incremental_machine.optimize(remaining_time=20)



    if model.status == GRB.INFEASIBLE:
        print("Model is infeasible, computing IIS...")
        model.computeIIS()
        model.write("infeasible.ilp")
    else:

        for var in model.getVars():
            if var.VarName[:3] != "Che" and var.VarName[:3] != "Reo" and var.VarName[:3] != "Fil" and var.VarName[:3] != "Cut":
                print(f"{var.VarName} = {var.X}")