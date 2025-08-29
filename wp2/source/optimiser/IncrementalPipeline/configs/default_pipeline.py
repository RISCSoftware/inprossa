from IncrementalPipeline.Machines.Pipeline import Pipeline
from IncrementalPipeline.Machines.CheckingMachine import CheckingMachine
from IncrementalPipeline.Machines.ReorderingMachine import ReorderMachine
from IncrementalPipeline.Objects.piece import PieceVars
from IncrementalPipeline.Objects.board import BoardVars
from IncrementalPipeline.Machines.FilteringMachine import FilteringMachine
from IncrementalPipeline.Machines.CuttingMachine import CuttingMachine
from IncrementalPipeline.Tools.simple_computations import max_pieces_per_board


machine_changes_per_step = dict()
checking_machine = CheckingMachine(
    id=""
)
machine_changes_per_step[checking_machine.id] = (
    max_pieces_per_board,
    0
)

reordering_machine0_board = ReorderMachine(
    id="0",
    input_type=BoardVars
)
machine_changes_per_step[reordering_machine0_board.id] = (1, 1)

reordering_machine1 = ReorderMachine(
    id="1",
    input_type=PieceVars
)
machine_changes_per_step[reordering_machine1.id] = (
    max_pieces_per_board,
    max_pieces_per_board
)

reordering_machine2 = ReorderMachine(
    id="2",
    input_type=PieceVars
)
machine_changes_per_step[reordering_machine2.id] = (
    max_pieces_per_board,
    max_pieces_per_board
)

reordering_machine3 = ReorderMachine(
    id="3",
    input_type=PieceVars
)
machine_changes_per_step[reordering_machine3.id] = (
    max_pieces_per_board,
    max_pieces_per_board
)

filtering_machine = FilteringMachine(
    id=""
)
machine_changes_per_step[filtering_machine.id] = (
    max_pieces_per_board,
    max_pieces_per_board
)

cutting_machine = CuttingMachine(
    id=""
)
machine_changes_per_step[cutting_machine.id] = (
    1,
    max_pieces_per_board
)

pipeline_machines = [
    # reordering_machine0_board,
    cutting_machine,
    reordering_machine1,
    filtering_machine,
    checking_machine
]
pipeline_machine_changes_per_step = {
    machine.id: machine_changes_per_step[machine.id]
    for machine in pipeline_machines
}
pipeline = Pipeline(
    id="wood_processing_pipeline",
    machines=pipeline_machines,
    machine_changes_per_step=pipeline_machine_changes_per_step,
)
