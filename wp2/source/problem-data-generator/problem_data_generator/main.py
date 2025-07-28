import click
import random
import json
import os
from models.BeamConfiguration import BeamConfiguration
from models.InputBoard import InputBoard
from models.Board import Board
from models.Board import InputBoardPart
from models.Board import BoardPartQuality
from models.Interval import Interval
from models.WoodCutting import WoodCutting

JSON_DUMP_INDENT=2

@click.command()
@click.option("--beams", default=1, help="Number of beams (default=1)")
@click.option("--beamlength", default=500, help="Length of the beams (default=500)")
@click.option("--layers", default=5, help="Number of layers per beam (default=5)")
@click.option("--boards", default=10, help="Number of input boards (default=10)")
@click.option("--boardlength", default=600, help="Length of input boards (default=600)")
@click.option("--beamskipstart", default=10, help="Forbidden zone at the beginning of the beam (default=10)")
@click.option("--beamskipend", default=10, help="Forbidden zone at the end of the beam (default=10)")
@click.option("--minlengthofboardinlayer", default=10, help="Minimum length of a board (default=10)")
@click.option("--gap", default=10, help="Minimum gap to board abut in two consecutive layers (default=10)")
@click.option("--maxshiftcurvedcut", default=50, help="Maximum shift of a curved cut (default=50)")
@click.option("--f", default="90 110 190 210 290 310 390 410", help="List of forbidden intervals (default='90 110 190 210 290 310 390 410')")
@click.option("-o", "--output", default=None, help="Output filename (default=stdout)")
@click.option("-r", "--randomseed", default=0, help="Random seed (default=0)")
@click.option("-d", "--defect_rate", default=0.1, help="Average number of defects per distance (default=0.1)")
@click.option("-b", "--ratio_bad_curved", default=0.8, help="Ratio between bad errors and curved errors (default=0.8)")
@click.option("-l", "--bad-max-length", default=20, help="Maximum length of bad errors (default=20)")
@click.option("--bad-min-length", default=10, help="Minimum length of bad errors (default=10)")
@click.option("-e", "--curved-max-length", default=150, help="Maximum length of curved errors (default=150)")
@click.option("--curved-min-length", default=100, help="Minimum length of curved errors (default=100)")
@click.option("--compact", default=True, help="Write output in compact format or in a more readable way (default=True)")
def create(beams, beamlength, layers, boards, boardlength, beamskipstart, beamskipend, minlengthofboardinlayer, gap, maxshiftcurvedcut, f, output, randomseed, defect_rate, ratio_bad_curved, bad_max_length, bad_min_length, curved_min_length, curved_max_length, compact) -> None:
    # We check, if the file is already there, if it is the case then we terminate
    if output is not None and os.path.exists(output):
        click.echo(f"ERROR: Output file '{output}' already exists. Skip instance generation.")
        exit(10)

    f_str = f.split(" ")
    if len(f_str) % 2 != 0:
        click.echo(f"Error reading list of forbidden zones. Expected even number of entries, got {len(f_str)}: {f}")
        exit(1)
    forbiddenzones = tuple(Interval(Begin=int(x[0]), End=int(x[1])) for x in zip(f_str[0::2], f_str[1::2]))
    beam_configuration = BeamConfiguration(BeamLength=beamlength, 
                                           BeamWidth=0, 
                                           BeamHeight=0, 
                                           NumberOfLayers=layers, 
                                           NumberOfBeams=beams,
                                           BeamSkipStart=beamskipstart,
                                           BeamSkipEnd=beamskipend,
                                           MinLengthOfBoardInLayer=minlengthofboardinlayer,
                                           GapToBoardAbutInConsecutiveLayers=gap,
                                           MaxShiftCurvedCut=maxshiftcurvedcut,
                                           StaticForbiddenZones=forbiddenzones
                                           )
  
    # parameter:
    base_distance = 100
    min_length_good_part = 10
    randomseed = 0

    inputboards = list()
    running_distance = 0
    random.seed(randomseed)
    board_part_id = 0
    board_id = 0
    for i in range(boards):
        board_parts = []

        temp_board_distance = 0
        board_distance = 0
        board_finished = False
        while not board_finished:
            r = random.random()
            if r < defect_rate: # there is an error
                error_type = random.random()
                if error_type < ratio_bad_curved:
                    # bad part error
                    # get a position for the error, consider the remaining part
                    max_end_position = min(boardlength, temp_board_distance + base_distance)
                    error_position = random.randint(board_distance, max_end_position)
                    max_error_end_position = min(boardlength, error_position + bad_max_length)
                    error_length = random.randint(bad_min_length, max_error_end_position - error_position)

                    board_part_id += 1
                    ibp = InputBoardPart(Id=board_part_id, StartPosition=board_distance, EndPosition=error_position, Quality=BoardPartQuality.GOOD)
                    board_parts.append(ibp)
                    board_part_id += 1
                    ibp = InputBoardPart(Id=board_part_id, StartPosition=error_position, EndPosition=error_position+error_length, Quality=BoardPartQuality.BAD)
                    board_parts.append(ibp)
                    # calculate remaining length
                    board_distance = error_position + error_length
                    temp_board_distance = board_distance + min_length_good_part
                else:
                    # curve error
                    #max_end_position = min(boardlength, temp_board_distance + base_distance + curved_max_length)
                    # first we decide about the length of the curved error, so that it fits on the board
                    # 1. get the current maximum curved error length
                    max_curved_error_length = min(curved_max_length, boardlength - temp_board_distance)
                    # 2. get the curved error length based on max_curved_error_length and curved_min_length
                    curved_error_length = None
                    if max_curved_error_length >= curved_min_length:
                        if max_curved_error_length > curved_min_length:
                            curved_error_length = random.randint(curved_min_length, max_curved_error_length)
                        else:
                            curved_error_length = curved_min_length
                    if curved_error_length is not None:
                        max_error_start_position = min(boardlength - curved_error_length, temp_board_distance + base_distance)
                        error_position = random.randint(temp_board_distance, max_error_start_position)
                        board_part_id += 1
                        ibp = InputBoardPart(Id=board_part_id, StartPosition=board_distance, EndPosition=error_position, Quality=BoardPartQuality.GOOD)
                        board_parts.append(ibp)
                        board_part_id += 1
                        ibp = InputBoardPart(Id=board_part_id, StartPosition=error_position, EndPosition=error_position+curved_error_length, Quality=BoardPartQuality.CURVE)
                        board_parts.append(ibp)
                        board_distance = error_position + curved_error_length
                        temp_board_distance = board_distance + min_length_good_part
                    else:
                        click.echo("curved_error_length is None")

            else:
                 temp_board_distance += base_distance

            if temp_board_distance + base_distance > boardlength:
                board_part_id += 1
                ibp = InputBoardPart(Id=board_part_id, StartPosition=board_distance, EndPosition=boardlength, Quality=BoardPartQuality.GOOD)
                board_parts.append(ibp)
                board_finished = True

        board_id += 1
        rb = Board(Id=board_id, Length=boardlength, Width=25, Height=3, ScanBoardParts=board_parts)
        inputboards.append(rb)

    inputboards = [InputBoard(Position=x, RawBoard=b) for x, b in enumerate(inputboards)]
    woodcutting = WoodCutting(BeamConfiguration=beam_configuration, InputBoards=inputboards)


    problem_string = None
    if not compact: 
        problem_string = woodcutting.model_dump_json(indent=JSON_DUMP_INDENT)
    else:
        problem_string = woodcutting.model_dump_json()

    # Check if a file is there, if it is the case, terminate (this is because a file may be enger)
    if output is not None and os.path.exists(output):
        click.echo(f"ERROR: Output file '{output}' already exists. Skip instance generation.")
        exit(10)

    if output is not None:
        with open(output, 'xt') as of:
            of.write(problem_string)      
        click.echo(f"Problem instance file '{output}' successfully generated.")   
    else:
        print(problem_string)

    exit(0)

if __name__ == "__main__":
    #click.echo("InProSSA problem data generator")
    create()
