import click
import random
from models.BeamConfiguration import BeamConfiguration
from models.InputBoard import InputBoard
from models.Board import Board
from models.Board import InputBoardPart
from models.Board import BoardPartQuality
from models.Interval import Interval
from models.WoodCutting import WoodCutting

@click.command()
@click.option("--beams", default=1, help="Number of beams (default=1)")
@click.option("--beamlength", default=500, help="Length of the beams (default=500)")
@click.option("--layers", default=5, help="Number of layers per beam (default=5)")
@click.option("--boards", default=10, help="Number of input boards (default=10)")
@click.option("--board-length", default=600, help="Length of input boards (default=600)")
@click.option("--beamskipstart", default=10, help="Forbidden zone at the beginning of the beam (default=10)")
@click.option("--beamskipend", default=10, help="Forbidden zone at the end of the beam (default=10)")
@click.option("--minlengthofboardinlayer", default=10, help="Minimum length of a board (default=10)")
@click.option("--gap", default=10, help="Minimum gap to board abut in two consecutive layers (default=10)")
@click.option("--maxshiftcurvedcut", default=50, help="Maximum shift of a curved cut (default=50)")
@click.option("--f", default="90 110 190 210 290 310 390 410", help="List of forbidden intervals (default='90 110 190 210 290 310 390 410')")
@click.option("--noinputboards", default=5, help="Number of input boards (default=5)")
@click.option("-o", "--output", default="woodcutting.json", help="Output filename (default='woodcutting.json')")
@click.option("-r", "--randomseed", default=0, help="Random seed (default=0)")
@click.option("-b", "--bad", default=1, help="Average number of bad errors per board (default=1)")
@click.option("-l", "--bad-max-length", default=20, help="Maximum length of bad errors (default=20)")
@click.option("--bad-min-length", default=10, help="Minimum length of bad errors (default=10)")
@click.option("-c", "--curved", default=0, help="Average number of curved errors per board (default=0)")
@click.option("-e", "--curved-max-length", default=150, help="Maximum length of curved errors (default=150)")
@click.option("--curved-min-length", default=100, help="Minimum length of curved errors (default=100)")
def create(beams, beamlength, layers, boards, board_length, beamskipstart, beamskipend, minlengthofboardinlayer, gap, maxshiftcurvedcut, f, noinputboards, output, randomseed, bad, bad_max_length, bad_min_length, curved, curved_min_length, curved_max_length) -> None:
    #command_line_options = {'beams': beams, 'beamlength': beamlength, 'layers': layers, 'boards': boards}
    #click.echo("generate wood cutting problem")
    #click.echo(f"command_line_options={command_line_options}")
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

    # random.seed(randomseed) 
    # inputboards = list()
    # for i in range(noinputboards):


    #     ibp0 = InputBoardPart(Id=0, StartPosition=0, EndPosition=600, Quality=BoardPartQuality.GOOD)
    #     # ibp1 = InputBoardPart(Id=1, StartPosition=250, EndPosition=260, Quality=BoardPartQuality.BAD)
    #     # ibp2 = InputBoardPart(Id=2, StartPosition=260, EndPosition=400, Quality=BoardPartQuality.CURVE)
    #     # ibp3 = InputBoardPart(Id=3, StartPosition=400, EndPosition=405, Quality=BoardPartQuality.BAD)
    #     # ibp4 = InputBoardPart(Id=4, StartPosition=405, EndPosition=500, Quality=BoardPartQuality.GOOD)
    #     rb = Board(Id=i, Length=600, Width=25, Height=3, ScanBoardParts=[ibp0]) #, ibp1, ibp2, ibp3, ibp4])
    #     ib = InputBoard(Position=i, RawBoard=rb)
    #     inputboards.append(ib)
    # woodcutting = WoodCutting(BeamConfiguration=beam_configuration, InputBoards=inputboards)
    
    # parameter:
    error_rate_per_distance = 0.1 # error rate per meter
    base_distance = 100
    bad_probability = 0.8 # probability that the error is a bad part
    curve_probability = 0.2 # probability that the error is a curve error
    randomseed = 0

    inputboards = list()
    running_distance = 0
    random.seed(randomseed)
    board_part_id = 0
    board_id = 0
    for i in range(noinputboards):
        board_parts = []

        temp_board_distance = 0
        board_distance = 0
        board_finished = False
        while not board_finished:
            r = random.random()
            if r < error_rate_per_distance: # there is an error
                error_type = random.random()
                if error_type < bad_probability:
                    # bad part error
                    # get a position for the error, consider the remaining part
                    max_end_position = min(board_length, temp_board_distance + base_distance)
                    error_position = random.randint(board_distance, max_end_position)
                    max_error_end_position = min(board_length, error_position + bad_max_length)
                    error_length = random.randint(bad_min_length, max_error_end_position - error_position)

                    board_part_id += 1
                    ibp = InputBoardPart(Id=board_part_id, StartPosition=board_distance, EndPosition=error_position, Quality=BoardPartQuality.GOOD)
                    board_parts.append(ibp)
                    board_part_id += 1
                    ibp = InputBoardPart(Id=board_part_id, StartPosition=error_position, EndPosition=error_position+error_length, Quality=BoardPartQuality.BAD)
                    board_parts.append(ibp)
                    # calculate remaining length
                    board_distance = error_position + error_length
                    temp_board_distance = board_distance
                else:
                    # curve error
                    pass
            else:
                 temp_board_distance += base_distance

            if temp_board_distance + base_distance > board_length:
                board_part_id += 1
                ibp = InputBoardPart(Id=board_part_id, StartPosition=board_distance, EndPosition=board_length, Quality=BoardPartQuality.GOOD)
                board_parts.append(ibp)
                board_finished = True

        board_id += 1
        rb = Board(Id=board_id, Length=board_length, Width=25, Height=3, ScanBoardParts=board_parts)
        inputboards.append(rb)

    inputboards = [InputBoard(Position=x, RawBoard=b) for x, b in enumerate(inputboards)]
    woodcutting = WoodCutting(BeamConfiguration=beam_configuration, InputBoards=inputboards)
    click.echo(woodcutting)
    from rich import print
    print(woodcutting)
    # with open(output, "wt") as of:
    #     of.write(woodcutting.model_dump_json())

if __name__ == "__main__":
    #click.echo("InProSSA problem data generator")
    create()

