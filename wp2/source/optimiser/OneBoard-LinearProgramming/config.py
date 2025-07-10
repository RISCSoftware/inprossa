import math


# Example data setup

# --- INPUT BOARD ---
# intervals that need to be discarded
intervals = [(53,55), (60, 70)] #, (111,123), (312, 411), (478, 479), (500, 510), (600, 700), (800, 900), (1000, 1100)]
# number of intervals in the input board
n_intervals = len(intervals)
# length of the input board
input_length = 760
# input board with intervals and length
input_board = {"length": input_length, "intervals": intervals}

# --- BEAM CONFIGURATION ---
# length of output beam
beam_length = 200
# maximum length of a used piece
max_length = 200
# minimum length of a used piece
min_length = 50
# total number of layers to be formed completely
n_layers = 3
# number of layers each beam must have
n_layers_per_beam = 2
# global danger zones, no cuts should be in this interval of the beam
global_danger = [(54, 140)]
# number of cuts to be made (cuts might be duplicated)
n_cuts = math.ceil(input_length / min_length)
# maximum number of pieces per layer
pieces_per_layer = math.ceil(beam_length / min_length)