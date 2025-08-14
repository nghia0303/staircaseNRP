import sys
import gurobipy as gp
from gurobipy import GRB
import time
import psutil
import os

process = psutil.Process(os.getpid())
mem_before = process.memory_info().rss / (1024 * 1024)
start_processing_time = time.perf_counter()
start_total_time = time.perf_counter()
# Parameters
number_nurses = int(sys.argv[1]) # Number of nurses
number_days = int(sys.argv[2]) # Number of days
result_file_path = sys.argv[3] if len(sys.argv) > 3 else "result.txt"


# Hard configurations
number_days_per_week = 7
# number_days = number_weeks * number_days_per_week
number_shifts_per_day = 3 # 0: day, 1: evening, 2: night
off_day_index = number_shifts_per_day # 3: off day

# Data
NURSES = range(number_nurses)         
DAYS = range(number_days)     
SHIFTS = range(number_shifts_per_day)

model = gp.Model("nurse_scheduling")
x = model.addVars(NURSES, DAYS, SHIFTS, vtype=GRB.BINARY, name="x")

# Objective: Max 1 shift per nurse per day
for n in NURSES:
    for d in DAYS:
        model.addConstr(gp.quicksum(x[n, d, s] for s in SHIFTS) <= 1)

# Objective: Max 6 shifts per nurse per 7 days
for n in NURSES:
    for start in range(number_days - 6):
        model.addConstr(
            gp.quicksum(x[n, d, s] for d in range(start, start+7) for s in SHIFTS) <= 6
        )

# Objective: Min 4 off days per nurse per 14 days
for n in NURSES:
    for start in range(number_days - 13):
        model.addConstr(
            gp.quicksum(x[n, d, s] for d in range(start, start+14) for s in SHIFTS) <= 10
        )

# Objective: Betweeen 4 and 8 evening shifts per nurse per 14 days
for n in NURSES:
    for start in range(number_days - 13):
        evening_shifts = gp.quicksum(x[n, d, 1] for d in range(start, start+14))
        model.addConstr(evening_shifts >= 4)
        model.addConstr(evening_shifts <= 8)

# Objective: Min 20 shifts per nurse per 28 days
for n in NURSES:
    for start in range(number_days - 27):
        # print(f"Start: {start}, Nurse: {n}")
        # for d in range(start, start + 28):
        #     for s in SHIFTS:
        #         print(f"x[{n}, {d}, {s}]: {x[n, d, s]}")
        model.addConstr(
            gp.quicksum(x[n, d, s] for d in range(start, start+28) for s in SHIFTS) >= 20
        )

# Objective: Between 1 and 4 night shift every 14 days
for n in NURSES:
    for start in range(number_days - 13):
        night_shifts = gp.quicksum(x[n, d, 2] for d in range(start, start+14))
        model.addConstr(night_shifts >= 1)
        model.addConstr(night_shifts <= 4)

# Objective: Between 2 and 4 evening or night shifts every 7 days
for n in NURSES:
    for start in range(number_days - 6):
        # evening_shifts = gp.quicksum(x[n, d, 1] for d in range(start, start+7))
        # model.addConstr(evening_shifts >= 2)
        # model.addConstr(evening_shifts <= 4)

        evening_or_night_shifts = []
        for d in range(start, start + 7):
            evening_or_night_shifts.append(x[n, d, 1])
            evening_or_night_shifts.append(x[n, d, 2])
        # print(f"Evening or Night Shifts for Nurse {n} from Day {start} to {start + 6}: {evening_or_night_shifts}")
        model.addConstr(gp.quicksum(evening_or_night_shifts) >= 2)
        model.addConstr(gp.quicksum(evening_or_night_shifts) <= 4)


# Objective: No consecutive night shifts
for n in NURSES:
    for d in range(number_days - 1): 
        model.addConstr(x[n, d, 2] + x[n, d+1, 2] <= 1)

end_processing_time = time.perf_counter()

print("------------------Gurobi Log------------------")
start_optimizing_time = time.perf_counter()
model.optimize()

end_optimizing_time = time.perf_counter()
end_total_time = time.perf_counter()
mem_after = process.memory_info().rss / (1024 * 1024)

print("------------------Specifications------------------")
processing_time = (end_processing_time - start_processing_time) * 1000  # Convert to milliseconds
optimization_time = (end_optimizing_time - start_optimizing_time) * 1000  # Convert to milliseconds
total_time = (end_total_time - start_total_time) * 1000  # Convert to milliseconds
print(f"Processing Time     : {processing_time:.2f} milliseconds")
print(f"Optimization Time   : {optimization_time:.2f} milliseconds")
print(f"Total Time          : {total_time:.2f} milliseconds")
print(f"Memory Usaged       : {mem_after - mem_before:.2f} MB")

result_line = f"{number_nurses},{number_weeks},Gurobi,,,,{processing_time:.3f}, {optimization_time:.3f}, {total_time:.3f}\n"
with open(result_file_path, "a") as result_file:
    result_file.write(result_line)

def verify_solution(x, NURSES, DAYS, SHIFTS):
    print("------------------Verifying solution------------------")
    errors = 0
    number_days = len(DAYS)

    for n in NURSES:
        # C1: Max 1 shift per nurse per day
        for d in DAYS:
            total = sum(x[n, d, s].X for s in SHIFTS)
            if total > 1 + 1e-6:
                print(f"C1 Violation: Nurse {n}, Day {d}, shifts assigned = {total}")
                errors += 1

        # C2: Max 6 shifts in any 7 consecutive days
        for start in range(number_days - 6):
            total = sum(x[n, d, s].X for d in range(start, start + 7) for s in SHIFTS)
            if total > 6 + 1e-6:
                print(f"C2 Violation: Nurse {n}, Days {start}-{start+6}, shifts = {total}")
                errors += 1

        # C3: Min 4 off-days in any 14 consecutive days => Max 10 shifts
        for start in range(number_days - 13):
            total = sum(x[n, d, s].X for d in range(start, start + 14) for s in SHIFTS)
            if total > 10 + 1e-6:
                print(f"C3 Violation: Nurse {n}, Days {start}-{start+13}, shifts = {total}")
                errors += 1

        # C4: Between 4 and 8 evening shifts (shift 1) in 14 days
        for start in range(number_days - 13):
            evening = sum(x[n, d, 1].X for d in range(start, start + 14))
            if not (4 - 1e-6 <= evening <= 8 + 1e-6):
                print(f"C4 Violation: Nurse {n}, Days {start}-{start+13}, evening shifts = {evening}")
                errors += 1

        # C5: At least 20 total shifts in 28 days
        for start in range(number_days - 27):
            total = sum(x[n, d, s].X for d in range(start, start + 28) for s in SHIFTS)
            if total < 20 - 1e-6:
                print(f"C5 Violation: Nurse {n}, Days {start}-{start+27}, shifts = {total}")
                errors += 1

        # C6: Between 1 and 4 night shifts (shift 2) in 14 days
        for start in range(number_days - 13):
            night = sum(x[n, d, 2].X for d in range(start, start + 14))
            if not (1 - 1e-6 <= night <= 4 + 1e-6):
                print(f"C6 Violation: Nurse {n}, Days {start}-{start+13}, night shifts = {night}")
                errors += 1

        # C7: Between 2 and 4 evening shifts in 7 days
        # New C7: Between 2 and 4 evening or night shifts in 7 days
        for start in range(number_days - 6):
            # evening = sum(x[n, d, 1].X for d in range(start, start + 7))
            # if not (2 - 1e-6 <= evening <= 4 + 1e-6):
            #     print(f"C7 Violation: Nurse {n}, Days {start}-{start+6}, evening shifts = {evening}")
            #     errors += 1
            evening_or_night = sum(x[n, d, 1].X + x[n, d, 2].X for d in range(start, start + 7))
            if not (2 - 1e-6 <= evening_or_night <= 4 + 1e-6):
                print(f"C7 Violation: Nurse {n}, Days {start}-{start+6}, evening or night shifts = {evening_or_night}")
                errors += 1

        # C8: No consecutive night shifts
        for d in range(number_days - 1):
            total = x[n, d, 2].X + x[n, d + 1, 2].X
            if total > 1 + 1e-6:
                print(f"C8 Violation: Nurse {n}, consecutive night shifts on Days {d}-{d+1}")
                errors += 1

    if errors == 0:
        print("All constraints are satisfied.")
    else:
        print(f"Total violations found: {errors}")

def print_solution(x, NURSES, DAYS, SHIFTS):
    print("------------------Schedule------------------")
    for n in NURSES:
        schedule = f"Nurse {n}: "
        for d in DAYS:
            shift = off_day_index
            for s in SHIFTS:
                if x[n, d, s].X > 0.5:
                    if shift == off_day_index:
                        shift = s
                    else:
                        raise ValueError("Duplicate shifts found for a nurse on a day.")
            schedule += shift.__str__() + " "
        print(schedule.strip())

if model.status == GRB.INFEASIBLE:
    print("Model is infeasible.")
else:
    verify_solution(x, NURSES, DAYS, SHIFTS)
    # print_solution(x, NURSES, DAYS, SHIFTS)

