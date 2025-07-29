

from IncrementalPipeline.experiments.create_list_boards import (
    run_problem_data_generator
)
from IncrementalPipeline.experiments.time_solution import (
    time_solution,
    time_solution_after_warm_start
)


if __name__ == "__main__":
    timings = dict()
    warm_start_timings = dict()
    for i in range(2, 7):
        timings[i] = []
        warm_start_timings[i] = []
        for _ in range(5):
            # Create input of that size
            input_list = run_problem_data_generator(n_boards=i)
            # Time the solution
            print(f"Testing input size: {i}",
                  "type of input:",
                  type(input_list))
            _, total_time = time_solution(input_list)
            timings[i].append(total_time)
            time_taken = time_solution_after_warm_start(input_list)
            warm_start_timings[i].append(time_taken)
            print(f"Input size: {i}, Time taken: {total_time:.2f} seconds")
            print(f"Time taken after warm start: {time_taken:.2f} seconds")
        print("Timings without warm start:")
        print(timings[i])
        print("Timings with warm start:")
        print(warm_start_timings[i])
    print("Average timings without warm start:")
    for size, times in timings.items():
        print(f"Size {size}: {sum(times) / len(times)} seconds")
    print("Average timings with warm start:")
    for size, times in warm_start_timings.items():
        print(f"Size {size}: {sum(times) / len(times)} seconds")

    print("All timings without warm start:")
    print(timings)
    print("All timings with warm start:")
    print(warm_start_timings)


# Average timings without warm start:
# Size 2: 10.495698928833008 seconds
# Size 3: 45.58390393257141 seconds
# Size 4: 63.33114695549011 seconds
# Average timings with warm start:
# Size 2: 13.86924605369568 seconds
# Size 3: 23.178616428375243 seconds
# Size 4: 55.5579185962677 seconds
# All timings without warm start:
# {2: [9.60264801979065, 9.89658498764038, 10.519448041915894, 11.46068000793457, 10.999133586883545], 3: [43.44749331474304, 42.75236535072327, 45.622665882110596, 48.93681597709656, 47.160179138183594], 4: [57.358367681503296, 67.07378673553467, 59.6866979598999, 72.8607747554779, 59.67610764503479]}
# All timings with warm start:
# {2: [12.331409215927124, 12.454222440719604, 15.774994134902954, 14.227156639099121, 14.55844783782959], 3: [21.141704320907593, 26.517884492874146, 21.91102933883667, 26.768187046051025, 19.554276943206787], 4: [52.78040623664856, 49.75197720527649, 53.37619376182556, 62.40964341163635, 59.47137236595154]}
