code_given_objects = """
GIVEN_INITIAL_BOARDS : DSList(N_BOARDS, Board) = [
    Board(length=20,
          bad_intervals=[
            Interval(5,6),
            Interval(15,16)
      ],
          curved_intervals=[
            Interval(10,12),
            Interval(18,20)
          ]
    ),
    Board(length=25,
          bad_intervals=[
          Interval(10,14),
          Interval(18,20)
          ],
          curved_intervals=[
          Interval(7,9),
          Interval(18,20)
          ],
    ),
    # Board(length=25,
    #       bad_intervals=[
    #       Interval(8,10),
    #       Interval(18,20)
    #       ],
    #       curved_intervals=[
    #       Interval(5,7),
    #       Interval(12,14)
    #       ]
    # )
]
# GIVEN_PIECES : DSList(N_PIECES, Piece) = [
#     Piece(length=5, quality=1),
#     Piece(length=10, quality=1),
# ]
"""