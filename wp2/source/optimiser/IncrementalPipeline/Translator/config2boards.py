from typing import List, Dict, Any, Tuple
from IncrementalPipeline.Objects.board import Board
# Replace with the actual module where your Board class is defined


def convert_inputboards_to_boards(
        input_data: Dict[str, Any]
        ) -> List[List[Board]]:
    """
    Convert JSON-like input data containing InputBoards into
    a list of lists of Board objects.

    Each RawBoard is converted into a Board instance, where:
    - Quality == 2 parts go into bad_parts
    - Quality == 3 parts go into curved_parts
    - Quality == 1 parts are ignored

    Args:
        input_data (dict): The input data containing "InputBoards".

    Returns:
        List[List[Board]]: A list of lists containing Board objects.
    """
    result: List[List[Board]] = []

    for board_entry in input_data:
        raw = board_entry["RawBoard"]
        bad_parts: List[Tuple[float, float]] = []
        curved_parts: List[Tuple[float, float]] = []

        for part in raw.get("ScanBoardParts", []):
            interval = tuple(part["Interval"])
            quality = part.get("Quality", 1)
            if quality == 2:
                bad_parts.append(interval)
            elif quality == 3:
                curved_parts.append(interval)

        board = Board(length=raw["Length"],
                      bad_parts=bad_parts,
                      curved_parts=curved_parts)
        result.append(board)

    return result


def convert_inputboards_list_to_boards_list(
        inputboards: List[Dict[str, Any]]
        ) -> List[Board]:
    result: List[Board] = []
    for inputboard in inputboards:
        boards = convert_inputboards_to_boards(inputboard)
        result.extend(boards)
    return result


if __name__ == "__main__":
    # Example input data
    input_data = [
            {
                "Position": 0,
                "RawBoard": {
                    "Id": 0,
                    "Length": 600,
                    "Width": 25,
                    "Height": 3,
                    "ScanBoardParts": [
                        {
                            "Id": 0,
                            "StartPosition": 0,
                            "EndPosition": 600,
                            "Quality": 1,
                            "Length": 600,
                            "Interval": [
                                0,
                                600
                            ]
                        }
                    ]
                }
            },
            {
                "Position": 1,
                "RawBoard": {
                    "Id": 1,
                    "Length": 600,
                    "Width": 25,
                    "Height": 3,
                    "ScanBoardParts": [
                        {
                            "Id": 0,
                            "StartPosition": 0,
                            "EndPosition": 300,
                            "Quality": 1,
                            "Length": 300,
                            "Interval": [
                                0,
                                300
                            ]
                        },
                        {
                            "Id": 0,
                            "StartPosition": 300,
                            "EndPosition": 310,
                            "Quality": 2,
                            "Length": 10,
                            "Interval": [
                                300,
                                310
                            ]
                        },
                        {
                            "Id": 0,
                            "StartPosition": 310,
                            "EndPosition": 350,
                            "Quality": 1,
                            "Length": 40,
                            "Interval": [
                                310,
                                350
                            ]
                        },
                        {
                            "Id": 0,
                            "StartPosition": 350,
                            "EndPosition": 450,
                            "Quality": 3,
                            "Length": 100,
                            "Interval": [
                                350,
                                450
                            ]
                        },
                        {
                            "Id": 0,
                            "StartPosition": 450,
                            "EndPosition": 600,
                            "Quality": 1,
                            "Length": 150,
                            "Interval": [
                                450,
                                600
                            ]
                        },
                    ]
                }
            },
            {
                "Position": 2,
                "RawBoard": {
                    "Id": 2,
                    "Length": 600,
                    "Width": 25,
                    "Height": 3,
                    "ScanBoardParts": [
                        {
                            "Id": 0,
                            "StartPosition": 0,
                            "EndPosition": 600,
                            "Quality": 1,
                            "Length": 600,
                            "Interval": [
                                0,
                                600
                            ]
                        }
                    ]
                }
            },
            {
                "Position": 3,
                "RawBoard": {
                    "Id": 3,
                    "Length": 600,
                    "Width": 25,
                    "Height": 3,
                    "ScanBoardParts": [
                        {
                            "Id": 0,
                            "StartPosition": 0,
                            "EndPosition": 600,
                            "Quality": 1,
                            "Length": 600,
                            "Interval": [
                                0,
                                600
                            ]
                        }
                    ]
                }
            },
            {
                "Position": 4,
                "RawBoard": {
                    "Id": 4,
                    "Length": 600,
                    "Width": 25,
                    "Height": 3,
                    "ScanBoardParts": [
                        {
                            "Id": 0,
                            "StartPosition": 0,
                            "EndPosition": 600,
                            "Quality": 1,
                            "Length": 600,
                            "Interval": [
                                0,
                                600
                            ]
                        }
                    ]
                }
            }
        ]

    boards = convert_inputboards_to_boards(input_data)

    for board in boards:
        print(f"Board Length: {board.length}\n"
              f"Bad Parts: {board.bad_parts}\n"
              f"Curved Parts: {board.curved_parts}\n")

    input_data2 = [
        {
            'Position': 0,
            'RawBoard': {
                'Id': 1,
                'Length': 600,
                'Width': 25,
                'Height': 3,
                'ScanBoardParts': [
                    {'Id': 1, 'StartPosition': 0, 'EndPosition': 57,
                     'Quality': 1, 'Length': 57, 'Interval': [0, 57]},
                    {'Id': 2, 'StartPosition': 57, 'EndPosition': 69,
                     'Quality': 2, 'Length': 12, 'Interval': [57, 69]},
                    {'Id': 3, 'StartPosition': 69, 'EndPosition': 84,
                     'Quality': 1, 'Length': 15, 'Interval': [69, 84]},
                    {'Id': 4, 'StartPosition': 84, 'EndPosition': 95,
                     'Quality': 2, 'Length': 11, 'Interval': [84, 95]},
                    {'Id': 5, 'StartPosition': 95, 'EndPosition': 176,
                     'Quality': 1, 'Length': 81, 'Interval': [95, 176]},
                    {'Id': 6, 'StartPosition': 176, 'EndPosition': 277,
                     'Quality': 3, 'Length': 101, 'Interval': [176, 277]},
                    {'Id': 7, 'StartPosition': 277, 'EndPosition': 340,
                     'Quality': 1, 'Length': 63, 'Interval': [277, 340]},
                    {'Id': 8, 'StartPosition': 340, 'EndPosition': 474,
                     'Quality': 3, 'Length': 134, 'Interval': [340, 474]},
                    {'Id': 9, 'StartPosition': 474, 'EndPosition': 489,
                     'Quality': 1, 'Length': 15, 'Interval': [474, 489]},
                    {'Id': 10, 'StartPosition': 489, 'EndPosition': 589,
                     'Quality': 3, 'Length': 100, 'Interval': [489, 589]},
                    {'Id': 11, 'StartPosition': 589, 'EndPosition': 600,
                     'Quality': 1, 'Length': 11, 'Interval': [589, 600]}
                ]
            }
        },
        {
            'Position': 1,
            'RawBoard': {
                'Id': 2,
                'Length': 600,
                'Width': 25,
                'Height': 3,
                'ScanBoardParts': [
                    {'Id': 12, 'StartPosition': 0, 'EndPosition': 195,
                     'Quality': 1, 'Length': 195, 'Interval': [0, 195]},
                    {'Id': 13, 'StartPosition': 195, 'EndPosition': 210,
                     'Quality': 2, 'Length': 15, 'Interval': [195, 210]},
                    {'Id': 14, 'StartPosition': 210, 'EndPosition': 255,
                     'Quality': 1, 'Length': 45, 'Interval': [210, 255]},
                    {'Id': 15, 'StartPosition': 255, 'EndPosition': 270,
                     'Quality': 2, 'Length': 15, 'Interval': [255, 270]},
                    {'Id': 16, 'StartPosition': 270, 'EndPosition': 600,
                     'Quality': 1, 'Length': 330, 'Interval': [270, 600]}
                ]
            }
        },
        {
            'Position': 2,
            'RawBoard': {
                'Id': 3,
                'Length': 600,
                'Width': 25,
                'Height': 3,
                'ScanBoardParts': [
                    {'Id': 17, 'StartPosition': 0, 'EndPosition': 279,
                     'Quality': 1, 'Length': 279, 'Interval': [0, 279]},
                    {'Id': 18, 'StartPosition': 279, 'EndPosition': 419,
                     'Quality': 3, 'Length': 140, 'Interval': [279, 419]},
                    {'Id': 19, 'StartPosition': 419, 'EndPosition': 600,
                     'Quality': 1, 'Length': 181, 'Interval': [419, 600]}
                ]
            }
        },
        {
            'Position': 3,
            'RawBoard': {
                'Id': 4,
                'Length': 600,
                'Width': 25,
                'Height': 3,
                'ScanBoardParts': [
                    {'Id': 20, 'StartPosition': 0, 'EndPosition': 8,
                     'Quality': 1, 'Length': 8, 'Interval': [0, 8]},
                    {'Id': 21, 'StartPosition': 8, 'EndPosition': 18,
                     'Quality': 2, 'Length': 10, 'Interval': [8, 18]},
                    {'Id': 22, 'StartPosition': 18, 'EndPosition': 600,
                     'Quality': 1, 'Length': 582, 'Interval': [18, 600]}
                ]
            }
        },
        {
            'Position': 4,
            'RawBoard': {
                'Id': 5,
                'Length': 600,
                'Width': 25,
                'Height': 3,
                'ScanBoardParts': [
                    {'Id': 23, 'StartPosition': 0, 'EndPosition': 46,
                     'Quality': 1, 'Length': 46, 'Interval': [0, 46]},
                    {'Id': 24, 'StartPosition': 46, 'EndPosition': 58,
                     'Quality': 2, 'Length': 12, 'Interval': [46, 58]},
                    {'Id': 25, 'StartPosition': 58, 'EndPosition': 92,
                     'Quality': 1, 'Length': 34, 'Interval': [58, 92]},
                    {'Id': 26, 'StartPosition': 92, 'EndPosition': 112,
                     'Quality': 2, 'Length': 20, 'Interval': [92, 112]},
                    {'Id': 27, 'StartPosition': 112, 'EndPosition': 381,
                     'Quality': 1, 'Length': 269, 'Interval': [112, 381]},
                    {'Id': 28, 'StartPosition': 381, 'EndPosition': 491,
                     'Quality': 3, 'Length': 110, 'Interval': [381, 491]},
                    {'Id': 29, 'StartPosition': 491, 'EndPosition': 600,
                     'Quality': 1, 'Length': 109, 'Interval': [491, 600]}
                ]
            }
        }
    ]

    boards2 = convert_inputboards_to_boards(input_data2)
    for board in boards2:
        print(f"Board Length: {board.length}\n"
              f"Bad Parts: {board.bad_parts}\n"
              f"Curved Parts: {board.curved_parts}\n")
        print(board.__dict__)
