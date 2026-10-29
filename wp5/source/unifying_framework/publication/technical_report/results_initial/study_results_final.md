# Size-study results: MiniZinc vs LNS

_Solver cp-sat, MiniZinc budget 120.0s/instance_

| Class | Set | Instance | Size | MiniZinc Quality | MiniZinc Bound | MiniZinc Time (s) | LNS Quality | LNS Time (s) | LNS Stop | Gap (%) |
|---|---|---|---|---|---|---|---|---|---|---|
| cvrp | small | E-n13-k4 | 13 / 4 / 6000 | 279.0 | 139.0 | 123.9263 | 247.0 | 3.6291 | stop_criterion | 77.70 |
| cvrp | small | random_euclidean_cvrp_8 | 8 / 4 / 10 | 370.0 | 370.0 | 2.2398 | 370.0 | 1.8423 | stop_criterion | 0.00 |
| cvrp | medium | random_euclidean_cvrp_15 | 15 / 10 / 17 | <no_solution> | 274.0 | 137.7895 | 555.0 | 10.1431 | stop_criterion | 102.55 |
| cvrp | medium | random_euclidean_cvrp_20 | 20 / 5 / 25 | <no_solution> | 300.0 | 134.1788 | 554.0 | 9.6386 | stop_criterion | 84.67 |
| jssp | small | jssp_10x5 | 10 / 5 | 37.0 | 37.0 | 56.5554 | 38.0 | 9.2919 | stop_criterion | 2.70 |
| jssp | small | jssp_2x2 | 2 / 2 | 6.0 | 6.0 | 0.7777 | 6.0 | 0.4880 | stop_criterion | 0.00 |
| jssp | small | jssp_5x4 | 5 / 4 | 22.0 | 22.0 | 1.2344 | 22.0 | 1.9066 | stop_criterion | 0.00 |
| jssp | medium | la01 | 10 / 5 | 727.0 | 413.0 | 130.2423 | 689.0 | 9.4905 | stop_criterion | 66.83 |
| jssp | medium | la02 | 10 / 5 | 666.0 | 394.0 | 129.5558 | 686.0 | 9.7288 | stop_criterion | 74.11 |
| jssp | medium | la03 | 10 / 5 | 706.0 | 349.0 | 129.4788 | 648.0 | 9.5321 | stop_criterion | 85.67 |
| jssp | medium | la04 | 10 / 5 | 625.0 | 369.0 | 129.4051 | 621.0 | 9.8149 | stop_criterion | 68.29 |
| jssp | medium | la05 | 10 / 5 | 606.0 | 380.0 | 130.0443 | 593.0 | 9.5829 | stop_criterion | 56.05 |
| jssp | medium | orb01 | 10 / 10 | 1173.0 | 695.0 | 470.5026 | 1198.0 | 47.7592 | stop_criterion | 72.37 |
| 2dbp | small | 2d_bpp_inst_cl_06_020_06.ins2D | 300x300 / 20 | <no_solution> | 0.0 | 157.3849 | 1.0 | 69.1330 | stop_criterion | inf |
| 2dbp | small | 2d_bpp_inst_cl_06_020_10.ins2D | 300x300 / 20 | 1.0 | 1.0 | 97.8615 | 1.0 | 62.5340 | stop_criterion | 0.00 |
| 2dbp | medium | 2d_bpp_inst_cl_04_020_08.ins2D | 100x100 / 20 | <no_solution> | 0.0 | 152.3384 | 1.0 | 59.7394 | stop_criterion | inf |
| 2dbp | medium | 2d_bpp_inst_cl_05_020_08.ins2D | 100x100 / 20 | 5.0 | 5.0 | 107.7868 | 5.0 | 13.3435 | stop_criterion | 0.00 |
| 2dbp | medium | 2d_bpp_inst_cl_10_020_09.ins2D | 100x100 / 20 | 6.0 | 0.0 | 158.2481 | 6.0 | 12.8442 | stop_criterion | inf |
