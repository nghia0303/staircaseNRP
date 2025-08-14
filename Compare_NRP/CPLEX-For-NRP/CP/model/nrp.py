import time
import sys
import os

from docplex.cp.config import context
context.solver.local.execfile = "/home/nghia/cplex/CPLEX_Studio2211/cpoptimizer/bin/x86-64_linux/cpoptimizer"
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))
from docplex.cp.model import CpoModel

# === Parameters ===
NURSES = int(sys.argv[1])
DAYS = int(sys.argv[2])
MIN_SHIFTS_28DAYS = 20
# MIN_SHIFTS_28DAYS = int(sys.argv[3])

start_time = time.perf_counter()

DAYS_PER_WEEK = 7
# DAYS = WEEKS * DAYS_PER_WEEK
SHIFTS = ['D', 'E', 'N']

# === Create CPO model ===
mdl = CpoModel(name="NurseScheduling_CPO")

# === Decision variables ===
# x[n,d,s] = 1 nếu nurse n làm ca s trong ngày d
# Dùng dict cho thuận tiện như MP
x = {}
for n in range(NURSES):
    for d in range(DAYS):
        for s in SHIFTS:
            x[(n, d, s)] = mdl.binary_var(name=f"x_{n}_{d}_{s}")

# === Constraints ===

# 0. Mỗi nurse tối đa 1 ca/ngày
for n in range(NURSES):
    for d in range(DAYS):
        mdl.add(mdl.sum(x[(n, d, s)] for s in SHIFTS) <= 1)

# 1. Mỗi nurse tối đa 6 ca trong mọi 7 ngày liên tiếp
for n in range(NURSES):
    for start in range(DAYS - 6):
        mdl.add(mdl.sum(x[(n, d, s)] for d in range(start, start + 7) for s in SHIFTS) <= 6)

# 2. Mỗi nurse nghỉ ít nhất 4 ngày trong mọi 14 ngày liên tiếp (=> tối đa 10 ca/14 ngày)
for n in range(NURSES):
    for start in range(DAYS - 13):
        mdl.add(mdl.sum(x[(n, d, s)] for d in range(start, start + 14) for s in SHIFTS) <= 10)

# 3. Mỗi nurse làm ít nhất 4 ca E trong mọi 14 ngày liên tiếp
for n in range(NURSES):
    for start in range(DAYS - 13):
        mdl.add(mdl.sum(x[(n, d, 'E')] for d in range(start, start + 14)) >= 4)

# 4. Mỗi nurse làm nhiều nhất 8 ca E trong mọi 14 ngày liên tiếp
for n in range(NURSES):
    for start in range(DAYS - 13):
        mdl.add(mdl.sum(x[(n, d, 'E')] for d in range(start, start + 14)) <= 8)

# 5. Mỗi nurse đạt tối thiểu số ca yêu cầu trong mọi 28 ngày liên tiếp
for n in range(NURSES):
    for start in range(DAYS - 27):
        mdl.add(mdl.sum(x[(n, d, s)] for d in range(start, start + 28) for s in SHIFTS) >= MIN_SHIFTS_28DAYS)

# 6. Mỗi nurse tối đa 4 ca N trong mọi 14 ngày liên tiếp
for n in range(NURSES):
    for start in range(DAYS - 13):
        mdl.add(mdl.sum(x[(n, d, 'N')] for d in range(start, start + 14)) <= 4)

# 7. Mỗi nurse ít nhất 1 ca N trong mọi 14 ngày liên tiếp
for n in range(NURSES):
    for start in range(DAYS - 13):
        mdl.add(mdl.sum(x[(n, d, 'N')] for d in range(start, start + 14)) >= 1)

# 8. Mỗi nurse ít nhất 2 ca E trong mọi 7 ngày liên tiếp
for n in range(NURSES):
    for start in range(DAYS - 6):
        mdl.add(mdl.sum(x[(n, d, 'E')] for d in range(start, start + 7)) >= 2)

# 9. Mỗi nurse nhiều nhất 4 ca E or N trong mọi 7 ngày liên tiếp
# for n in range(NURSES):
#     for start in range(DAYS - 6):
#         mdl.add(mdl.sum(x[(n, d, 'E')] for d in range(start, start + 7)) <= 4)
for n in range(NURSES):
    for start in range(DAYS - 6):
        total_EN = mdl.sum(x[(n, d, 'E')] + x[(n, d, 'N')] for d in range(start, start + 7))
        mdl.add(total_EN >= 2)
        mdl.add(total_EN <= 4)


# 10. Không làm 2 ca N trong 2 ngày liên tiếp
for n in range(NURSES):
    for d in range(DAYS - 1):
        mdl.add(x[(n, d, 'N')] + x[(n, d + 1, 'N')] <= 1)

# === Objective (tùy chọn): minimize tổng số ca làm việc ===
# mdl.add(mdl.minimize(mdl.sum(x[(n, d, s)] for n in range(NURSES) for d in range(DAYS) for s in SHIFTS)))

# === Solve ===
# Có thể đặt tham số: TimeLimit, Workers, LogVerbosity...
msol = mdl.solve(LogVerbosity="Quiet")

end_time = time.perf_counter()
print(f"Total time: {(end_time - start_time) * 1000:.2f} (ms)")

# === Output sample solution ===
if msol and msol.is_solution():
    print("Solution found")
    # for n in range(NURSES):
    #     schedule = []
    #     for d in range(DAYS):
    #         assignment = "O"
    #         for s in SHIFTS:
    #             if int(msol.get_value(x[(n, d, s)])) == 1:
    #                 assignment = s
    #                 break
    #         schedule.append(assignment)
    #     print(f"Nurse {n+1}: {' '.join(schedule)}")
else:
    print("No solution found")
