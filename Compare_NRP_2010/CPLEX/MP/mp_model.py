"""
 Nurse scheduling problem from [Hoda et al. CP 2010] [Van Hoeve et al. Constraints 2009].

* Determine the work schedule for a single nurse over time horizon {1..H}.
    * Class C-I:
    *   - work at most 6 out of each 8 consecutive days
    *   - work at least 22 out of each 30 consecutive days
    * Class C-II:
    *   - work at most 6 out of each 9 consecutive days
    *   - work at least 20 out of each 30 consecutive days
    * Class C-III:
    *   - work at most 7 out of each 9 consecutive days
    *   - work at least 22 out of each 30 consecutive days
    * In each class, we need to work between 4 and 5 days during each calendar week.
    * The planning horizon H ranges from 40 to 80 days.

"""
import time
import sys
import os

from cplex.exceptions import CplexSolverError
from docplex.mp.model import Model



sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))




class NRP:
    def __init__(self, horizon: int, constraint: int=1):
        self.horizon = horizon
        self.constraint = constraint

        self.added_constraints = False
        self.ubs = [
            # Upper bounds for the number of working days in each class
            [6, 8],  # Class C-I
            [6, 9],  # Class C-II
            [7, 9]   # Class C-III
        ]
        self.lbs = [
            # Lower bounds for the number of working days in each class
            [22, 30],  # Class C-I
            [20, 30],  # Class C-II
            [22, 30]   # Class C-III
        ]

        self.model = Model(name="AmongNurse")
        # self.model.context.cplex_parameters.threads = 1
        self.x = self.model.binary_var_list(self.horizon, name="x")


    def get_variables_of_day(self, day: int):
        """
        Get the variable for a specific day.
        """
        if day < 1 or day > self.horizon:
            raise ValueError(f"Day {day} is out of bounds for horizon {self.horizon}.")
        return self.x[day - 1]

    def add_constraints(self):
        # C-I
        # self.add_C_x(1)
        #
        # # C-II
        # self.add_C_x(2)
        #
        # # C-III
        # self.add_C_x(3)

        if self.constraint not in [1, 2, 3]:
            raise ValueError("Constraint must be one of [1, 2, 3].")

        self.add_C_x(self.constraint)

        self.add_among_working_day_calendar_week(4, 5)


        self.added_constraints = True
        pass

    def add_C_x(self, x: int):
        """
            x ~ Class C-I, C-II, or C-III
        """
        self.add_at_most_x_working_day_per_y_day(self.ubs[x-1][0], self.ubs[x-1][1])
        # print(f"Adding at most {self.ubs[x-1][0]} working days per {self.ubs[x-1][1]} days for class C-{x} with encoding mode {self.encoding_mode}")
        self.add_at_least_x_working_day_per_y_day(self.lbs[x-1][0], self.lbs[x-1][1])
        # print(f"Adding at least {self.lbs[x-1][0]} working days per {self.lbs[x-1][1]} days for class C-{x} with encoding mode {self.encoding_mode}")
        pass

    def add_among_working_day_calendar_week(self, x: int, y: int):
        number_of_weeks = self.horizon // 7
        for week in range(number_of_weeks):
            start_day = week * 7 + 1
            end_day = start_day + 6
            week_days = [self.get_variables_of_day(day) for day in range(start_day, end_day + 1)]

            week_days_sum = self.model.sum(week_days)

            # print(f"Adding among working day calendar week constraint for week {week + 1} with {x} to {y} working days.")
            self.model.add_constraint(week_days_sum >= x, f"at_least_{x}_working_days_week_{week + 1}")
            self.model.add_constraint(week_days_sum <= y, f"at_most_{y}_working_days_week_{week + 1}")


    def add_at_most_x_working_day_per_y_day(self, x: int, y: int):
        """
        Add constraint that the nurse works at most x out of every y consecutive days.
        """
        for start in range(self.horizon - y + 1):
            end = start + y
            tmp = self.x[start:end]
            # print(f"Adding at most {x} working days per {y} days from day {start + 1} to {end}.")
            # print(f"Variables: {tmp}")
            working_days = self.model.sum(tmp)
            self.model.add_constraint(working_days <= x, f"at_most_{x}_working_days_per_{y}_days_{start + 1}_{end}")
        pass

    def add_at_least_x_working_day_per_y_day(self, x: int, y: int):
        """
        Add constraint that the nurse works at least x out of every y consecutive days.
        """
        for start in range(self.horizon - y + 1):
            end = start + y
            tmp = self.x[start:end]
            # print(f"Adding at least {x} working days per {y} days from day {start + 1} to {end}.")
            # print(f"Variables: {tmp}")
            working_days = self.model.sum(tmp)
            self.model.add_constraint(working_days >= x, f"at_least_{x}_working_days_per_{y}_days_{start + 1}_{end}")


        pass

    def solns(self):
        """
        Get the number of solutions found by the model.
        """
        if not self.added_constraints:
            raise ValueError("Constraints have not been added to the model.")

        cpx = self.model.get_cplex()
        cpx.parameters.mip.pool.intensity.set(4)
        cpx.parameters.mip.pool.absgap.set(16)
        cpx.parameters.mip.limits.populate.set(1000000)

        try:
            cpx.populate_solution_pool()
            numsol = cpx.solution.pool.get_num()
            # print(f"Number of solutions found: {numsol}")
            return numsol
            # print("Solutions:")
            solutions = []
            #
            # for i in range(numsol):
            #     sol = cpx.solution.pool.get_values(i)
            #     print(sol)

        except CplexSolverError:
            print("Exception raised during populate")
            return 0


    def solve_one_solution(self):

        # Get one solution
        solution = self.model.solve()
        if solution is None:
            # print("No solution found.")
            return 0
        else:
            return 1
        print("Solution found:")
        # for day in range(1, self.horizon + 1):
        #     var = self.get_variables_of_day(day)
        #     print(f"Day {day}: {var.solution_value}")

    def solve(self):

        if not self.added_constraints:
            raise ValueError("Constraints have not been added to the model.")

        # Get one solution
        # solution = self.model.solve(log_output=True)
        # if solution is None:
        #     print("No solution found.")
        #     return None
        # print("Solution found:")
        # for day in range(1, self.horizon + 1):
        #     var = self.get_variables_of_day(day)
        #     print(f"Day {day}: {var.solution_value}")

        # self.model.populate_solution_pool()


        solns = self.solns()

        # solution_count = self.model.solution.SolutionPool.size()
        #
        # print(f"Solution count: {solution_count}")

        return solns




        pass

    def validate_solution(self, solution):
        """
        Validate the solution against the constraints.
        """
        # Check if the solution has the correct length
        # if len(solution) != self.horizon:
        #     return False

        # Check C-I, C-II, C-III constraints
        # for i in range(3):
        #     if not self.validate_C_x(solution, i + 1):
        #         return False

        # if not self.validate_C_x(solution, 1):
        #     return False

        # # Check C-II
        # if not self.validate_C_x(solution, 2):
        #     return False
        # # Check C-III
        # if not self.validate_C_x(solution, 3):
        #     return False


        # Check among working day calendar week constraints
        if not self.validate_among_working_day_calendar_week(solution, 4, 5):
            return False

        return True

    def validate_C_x(self, solution, x: int):
        """
        Validate the C-I, C-II, or C-III constraints.
        """
        max_working_days = self.ubs[x-1][0]
        consecutive_days = self.ubs[x-1][1]

        for start in range(self.horizon - consecutive_days + 1):
            end = start + consecutive_days
            tmp = solution[start:end]
            working_days = 0
            for day in tmp:
                if day > 0:
                    working_days += 1


            # print(f'{tmp}')

            if working_days > max_working_days:
                raise ValueError(f"Constraint C-{x} max violated: {working_days} working days in days {start + 1} to {end}.")
                return False

        min_working_days = self.lbs[x-1][0]
        consecutive_days = self.lbs[x-1][1]

        for start in range(self.horizon - consecutive_days + 1):
            end = start + consecutive_days
            tmp = solution[start:end]
            working_days = 0
            for day in tmp:
                if day > 0:
                    working_days += 1

            # print(f'{tmp}')

            if working_days < min_working_days:
                raise ValueError(f"Constraint C-{x} min violated: {working_days} working days in days {start + 1} to {end}.")
                return False


        return True

    def validate_among_working_day_calendar_week(self, solution, x: int, y: int):
        """
        Validate the among working day calendar week constraints.
        """
        number_of_weeks = self.horizon // 7
        for week in range(number_of_weeks):
            start_day = week * 7
            end_day = start_day + 7
            week_days = solution[start_day:end_day]

            working_days = 0
            for day in week_days:
                if day > 0:
                    working_days += 1

            if working_days < x or working_days > y:
                # print(f"Week {week + 1} violates the among working day calendar week constraints: {week_days}")
                return False

        return True

def main():

    if len(sys.argv) > 1:
        horizon = int(sys.argv[1])
    else:
        horizon = 40

    if len(sys.argv) > 2:
        constraint = int(sys.argv[2])
    else:
        constraint = 1

    solve_one_solution = False
    if len(sys.argv) > 3:
        if sys.argv[3] == 'true':
            solve_one_solution = True


    start_time = time.perf_counter()

    nrp = NRP(
        horizon=horizon, constraint=constraint
    )

    nrp.add_constraints()
    if solve_one_solution:
        sol_count = nrp.solve_one_solution()
    else:
        sol_count = nrp.solve()

    # nrp = NRP(
    #     horizon=horizon, constraint=constraint, encoding_mode=encoding_mode,
    #     solver_name=solver_name, use_local_solver=use_local_solver,
    #     use_tseintin=use_tseintin, chunk_width=chunk_width
    # )
    # nrp.add_constraints()
    # sol_count = nrp.solve()
    end_time = time.perf_counter()

    print(f"\"time\" : {(end_time - start_time)*1000:.0f}")
    print(f"\"timeToFirstSol\" : 0")
    print(f"\"solns\" : {sol_count}")



if __name__ == "__main__":
    main()

