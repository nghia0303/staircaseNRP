import time

from docplex.mp.model import Model
import sys

# === Parameters ===
NURSES = int(sys.argv[1])
WEEKS = int(sys.argv[2])
MIN_SHIFTS_28DAYS = 20
# MIN_SHIFTS_28DAYS = int(sys.argv[3])

start_time = time.perf_counter()

DAYS_PER_WEEK = 7
DAYS = WEEKS * DAYS_PER_WEEK
SHIFTS = ['D', 'E', 'N']

# === Create model ===
mdl = Model(name="NurseScheduling")

# === Decision variables ===
# x[n][d][s] = 1 if nurse n works shift s on day d
x = mdl.binary_var_dict(((n, d, s) for n in range(NURSES) for d in range(DAYS) for s in SHIFTS), name='x')

# === Constraints ===

# 0. Each nurse works at most 1 shift per day
for n in range(NURSES):
    for d in range(DAYS):
        mdl.add_constraint(mdl.sum(x[n, d, s] for s in SHIFTS) <= 1)

# 1. Each nurse works at most 6 shifts per 7 consecutive days
for n in range(NURSES):
    for start in range(DAYS - 6):
        mdl.add_constraint(
            mdl.sum(x[n, d, s] for d in range(start, start + 7) for s in SHIFTS) <= 6
        )

# 2. Each nurse offs at least 4 days per 14 consecutive days
for n in range(NURSES):
    for start in range(DAYS - 13):
        mdl.add_constraint(
            mdl.sum(x[n, d, s] for d in range(start, start + 14) for s in SHIFTS) <= 10
        )

# 3. Each nurse works at least 4 evening shifts per 14 consecutive days
for n in range(NURSES):
    for start in range(DAYS - 13):
        mdl.add_constraint(
            mdl.sum(x[n, d, 'E'] for d in range(start, start + 14)) >= 4
        )

# 4. Each nurse works at most 8 evening shifts per 14 consecutive days
for n in range(NURSES):
    for start in range(DAYS - 13):
        mdl.add_constraint(
            mdl.sum(x[n, d, 'E'] for d in range(start, start + 14)) <= 8
        )

# 5. Each nurse must reach the number of required shifts per 28 consecutive days
for n in range(NURSES):
    for start in range(DAYS - 27): 
        mdl.add_constraint(
            mdl.sum(x[n, d, s] for d in range(start, start + 28) for s in SHIFTS) >= MIN_SHIFTS_28DAYS
        )

# 6. Each nurse works at most 4 night shifts per 14 consecutive days
for n in range(NURSES):
    for start in range(DAYS - 13):
        mdl.add_constraint(
            mdl.sum(x[n, d, 'N'] for d in range(start, start + 14)) <= 4
        )

# 7. Each nurse works at least 1 night shift per 14 consecutive days
for n in range(NURSES):
    for start in range(DAYS - 13):
        mdl.add_constraint(
            mdl.sum(x[n, d, 'N'] for d in range(start, start + 14)) >= 1
        )

# 8. Each nurse works at least 2 evening shifts per 7 consecutive days
for n in range(NURSES):
    for start in range(DAYS - 6):
        mdl.add_constraint(
            mdl.sum(x[n, d, 'E'] for d in range(start, start + 7)) >= 2
        )

# 9. Each nurse works at most 4 evening shifts per 7 consecutive days
for n in range(NURSES):
    for start in range(DAYS - 6):
        mdl.add_constraint(
            mdl.sum(x[n, d, 'E'] for d in range(start, start + 7)) <= 4
        )

# 10. Each nurse must not work two night shifts in any two consecutive days
for n in range(NURSES):
    for d in range(DAYS - 1):
        mdl.add_constraint(
            x[n, d, 'N'] + x[n, d + 1, 'N'] <= 1
        )

# Currently, no objective.
# === Objective: minimize total working days (or you can set another goal) ===
# mdl.minimize(mdl.sum(x[n, d, s] for n in range(NURSES) for d in range(DAYS) for s in SHIFTS))

# === Solve ===
solution = mdl.solve(log_output=True)

end_time = time.perf_counter()

print(f"Total time: {(end_time - start_time) * 1000:.2f} (ms)")

# === Output sample solution ===
if solution:
    for n in range(NURSES):
        schedule = []
        for d in range(DAYS):
            assigment = "O"
            for s in SHIFTS:
                if solution.get_value(x[n, d, s]) == 1:
                    assigment = s
            schedule.append(assigment)
        print(f"Nurse {n+1}: {' '.join(schedule)}")
else:
    print("No solution found")