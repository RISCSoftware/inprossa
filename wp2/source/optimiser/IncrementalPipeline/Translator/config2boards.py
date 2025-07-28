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
        result.append([board])  # Wrap each board in a list

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
        print(f"Board Length: {board[0].length}\n"
              f"Bad Parts: {board[0].bad_parts}\n"
              f"Curved Parts: {board[0].curved_parts}\n")
