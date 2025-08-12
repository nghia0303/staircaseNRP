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
from pysat.solvers import Solver



sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))
from src.include.allSATSolver import LocalSolver
from src.encoding.nsc_encoding import NSCEncoding
from src.encoding.staircase_encoding import StaircaseEncoding
from src.include.common import AuxVariable, AddClause
from src.encoding.all import Encoder, str_to_type_enum

class Variables:
    """
     Each var represents whether the nurse works on a specific day.
    """
    def __init__(self, horizon: int, aux: AuxVariable):
        self.horizon = horizon
        self.aux = aux
        self.work_days = []
        for day in range(1, horizon + 1):
            self.work_days.append(aux.get_new_variable())

    def get_all_variables(self):
        """
        Get all variables representing the nurse's work schedule.
        """
        return self.work_days

    def get_variable(self, day: int):
        """
        Get the variable representing whether the nurse works on a specific day.
        """
        if 1 <= day <= self.horizon:
            return self.work_days[day - 1]
        else:
            raise ValueError(f"Day {day} is out of bounds for horizon {self.horizon}.")

class NRP:
    def __init__(self, horizon: int, constraint: int=1, encoding_mode: str='staircase', second_encoding_mode: str='nsc', solver_name: str='g421', use_local_solver: bool=False, use_tseintin: bool=False, chunk_width: int=5,):
        self.horizon = horizon
        self.constraint = constraint
        self.aux = AuxVariable(1)
        self.variables = Variables(horizon, self.aux)
        self.clauses = []
        self.encoding_mode = encoding_mode
        self.second_encoding_mode = second_encoding_mode
        self.solver_name = solver_name
        self.use_local_solver = use_local_solver
        self.use_tseintin = use_tseintin
        self.chunk_width  = chunk_width

        self.add_clauses = AddClause(self.clauses)
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

    def get_clauses(self):
        # if not self.added_constraints:
        #     raise ValueError("Constraints have not been added yet. Call add_constraints() before getting clauses.")
        return self.clauses

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

        self.add_among_working_day_calendar_week(4, 5)
        self.add_C_x(self.constraint)
        # between 4 and 5 days during each calendar week



        self.added_constraints = True
        pass

    def add_C_x(self, x: int):
        """
            x ~ Class C-I, C-II, or C-III
        """
        self.add_at_most_x_working_day_per_y_day(self.ubs[x-1][0], self.ubs[x-1][1], self.encoding_mode)
        # print(f"Adding at most {self.ubs[x-1][0]} working days per {self.ubs[x-1][1]} days for class C-{x} with encoding mode {self.encoding_mode}")
        self.add_at_least_x_working_day_per_y_day(self.lbs[x-1][0], self.lbs[x-1][1], self.encoding_mode)
        # print(f"Adding at least {self.lbs[x-1][0]} working days per {self.lbs[x-1][1]} days for class C-{x} with encoding mode {self.encoding_mode}")
        pass

    def add_among_working_day_calendar_week(self, x: int, y: int):
        number_of_weeks = self.horizon // 7
        for week in range(number_of_weeks):
            start_day = week * 7 + 1
            end_day = start_day + 6
            week_days = [self.variables.get_variable(day) for day in range(start_day, end_day + 1)]
            encoder = Encoder(str_to_type_enum(self.second_encoding_mode))
            encoder.encode_range(week_days, x,  y, self.aux, self.add_clauses)

    def add_at_most_x_working_day_per_y_day(self, x: int, y: int, encoding_mode: str):
        """
        Add constraint that the nurse works at most x out of every y consecutive days.
        """
        if encoding_mode == 'staircase':
            var = self.variables.get_all_variables()
            encoder = StaircaseEncoding()
            encoder.encode_staircase(var, y, x, self.aux, self.add_clauses)
        else:
            var = self.variables.get_all_variables()
            encoder = Encoder(str_to_type_enum(encoding_mode))
            encoder.encode_at_most_k(var, x, self.aux, self.add_clauses)


    def add_at_least_x_working_day_per_y_day(self, x: int, y: int, encoding_mode: str):
        """
        Add constraint that the nurse works at least x out of every y consecutive days.
        """
        if encoding_mode == 'staircase':
            var = self.variables.get_all_variables()
            encoder = StaircaseEncoding()
            encoder.encode_staircase_at_least(var, y, x, self.aux, self.add_clauses)
        else:
            var = self.variables.get_all_variables()
            encoder = Encoder(str_to_type_enum(encoding_mode))
            encoder.encode_at_most_k(var, x, self.aux, self.add_clauses)

    def separate_clauses(self, clauses: list[int], width: int):
        """
            Separate long clauses into smaller ones by Tseitin Method

            x1 x2 x3 x4 x5 x6 x7 x8 x9 x10
            becomes:
            x1 x2 x3 x4 y1
            - y1 x5 x6 x7 x8 y2
            - y2 x9 x10

            where y1 and y2 are auxiliary variables.

        """
        separated_clauses = []

        last_idx = (len(clauses) - 1) // width * width
        if width == len(clauses):
            return [clauses]
        last_aux_var = None
        for i in range(0, len(clauses), width):
            clause_chunk = clauses[i:i + width]
            if i == 0:
                # First chunk, just add the variables
                aux_var = self.aux.get_new_variable()
                # clause_chunk.append(aux_var)
                last_aux_var = aux_var
                separated_clauses.append([aux_var] + clause_chunk)
            elif i == last_idx:
                clause_chunk.append(-last_aux_var)
                separated_clauses.append(clause_chunk)
                pass
            else:
                # clause_chunk.append(-last_aux_var)
                aux_var = self.aux.get_new_variable()
                separated_clauses.append([-last_aux_var] + clause_chunk + [aux_var])
                # clause_chunk.append(aux_var)
                last_aux_var = aux_var
            # separated_clauses.append(clause_chunk)
        return separated_clauses

    def to_cnf(self, cnf_path: str):
        """
        Write the CNF clauses to a file.
        """
        if not self.added_constraints:
            raise ValueError("Constraints have not been added yet. Call add_constraints() before writing to CNF.")

        with open(cnf_path, 'w') as f:
            f.write(f"p cnf {self.aux.get_last_used_var()} {len(self.clauses)}\n")
            for clause in self.clauses:
                f.write(" ".join(map(str, clause)) + " 0\n")

    def solve_one_solution(self):

        """
        Solve the NRP and return the first solution found.
        """
        solution_count = 0
        time_to_first_solution = None

        if not self.use_local_solver:
            pysat_solver = Solver(
                name=self.solver_name,
                bootstrap_with=self.get_clauses()
            )

            result = pysat_solver.solve()

            if result:
                solution_count = 1

            time_to_first_solution = time.perf_counter()

        else:
            if not os.path.exists('tmp/cnf'):
                os.mkdir('tmp/cnf')

            self.to_cnf('tmp/cnf/nrp.cnf')

            local_solver = LocalSolver()
            ret = 0
            res = []

            ret, res = local_solver.solve(
                    solver_name=self.solver_name,
                    cnf_path='tmp/cnf/nrp.cnf',
                    output_directory='tmp/cnf'
                )

            if ret == 2560:  # SATISFIABLE
                solution_count = 1
                time_to_first_solution = time.perf_counter()


        return solution_count, time_to_first_solution

    def solve(self):
        if not self.added_constraints:
            raise ValueError("Constraints have not been added yet. Call add_constraints() before solving.")


        solution_count = 0
        time_to_first_solution = None

        # print(self.separate_clauses([1, 2, 3, 4, 5, 6, 7, 8, 9, 10], 3))



        if not self.use_local_solver:
            pysat_solver = Solver(
                name=self.solver_name,
                bootstrap_with=self.get_clauses()
            )

            for model in pysat_solver.enum_models():
                time_to_first_solution = time.perf_counter()
                # blocking_clause = [-lit for lit in model if abs(lit) <= self.horizon]
                blocking_clause = []
                for day in range(1, self.horizon+1):
                    if model[self.variables.get_variable(day)-1] > 0:
                        blocking_clause.append(-self.variables.get_variable(day))
                    else:
                        blocking_clause.append(self.variables.get_variable(day))


                # print(blocking_clause)
                # print(f"Blocking clause: {blocking_clause}")
                if self.use_tseintin:
                    separated_clauses = self.separate_clauses(blocking_clause, self.chunk_width)
                    for clause in separated_clauses:
                        # print(clause)
                        pysat_solver.add_clause(clause)
                else:
                    pysat_solver.add_clause(blocking_clause)

                solution_count += 1


                # print(solution_count)
                # solution = []
                # for day in range(1, self.horizon + 1):
                #     solution.append(model[self.variables.get_variable(day)-1])

                # print(f"Solution {solution_count + 1}: {self.validate_solution(solution)}")

                # print(f"Solution {solution_count}")
                # with open('tmp/solution.txt', 'a') as f:
                #     # f.write(f"Solution: {model}\n")
                #     solution = []
                #     for day in range(1, self.horizon + 1):
                #         solution.append(model[self.variables.get_variable(day)-1])
                #
                #         # f.write(str(model[self.variables.get_variable(day)-1]) + " ")
                #         # # if model[self.variables.get_variable(day)] > 0:
                #         # #     f.write(f"Day {day}: Work\n")
                #         # # else:
                #         # #     f.write(f"Day {day}: Off\n")
                #     f.write(f"Solution {solution_count}: ")
                #     f.write(" ".join(map(str, solution)) + "\n")

                # del blocking_clause
                # del separated_clauses
        else:
            # print("Hello")
            if not os.path.exists('tmp/cnf'):
                os.mkdir('tmp/cnf')

            self.to_cnf('tmp/cnf/nrp.cnf')

            solvable = True

            local_solver = LocalSolver()
            ret = 0
            res = []

            ret, res = local_solver.solve(
                    solver_name=self.solver_name,
                    cnf_path='tmp/cnf/nrp.cnf',
                    output_directory='tmp/cnf'
                )
            # while solvable:
            #     # print(solution_count)
            #     # Add the blocking clause to prevent the same solution from being found again
            #     if res != []:
            #         blocking_clause = []
            #         for day in range(1, self.horizon + 1):
            #             if res[self.variables.get_variable(day)-1] > 0:
            #                 blocking_clause.append(-self.variables.get_variable(day))
            #             else:
            #                 blocking_clause.append(self.variables.get_variable(day))
            #
            #         if self.use_tseintin:
            #             separated_clauses = self.separate_clauses(blocking_clause, self.chunk_width)
            #             for clause in separated_clauses:
            #                 # print(clause)
            #                 self.add_clauses.add_list(clause)
            #         else:
            #             self.add_clauses.add_list(blocking_clause)
            #
            #     self.to_cnf("tmp/cnf/nrp.cnf")
            #
            #     ret, res = local_solver.solve(
            #         solver_name=self.solver_name,
            #         cnf_path='tmp/cnf/nrp.cnf',
            #         output_directory='tmp/cnf'
            #     )
            #     # print(ret)
            #     if ret == 5120:
            #         solvable = False
            #         break
            #
            #     solution_count += 1
            #     time_to_first_solution = time.perf_counter()
            #
            #     print(f"Solution {solution_count}: {res}")
            #     # Validate the solution
            #     # if not self.validate_solution(res):
            #     #     raise ValueError(f"Solution {solution_count} is invalid: {res}")


        return solution_count, time_to_first_solution



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

    if len(sys.argv) > 3:
        # encoding_mode = sys.argv[3]
        if "_" in sys.argv[3]:
            encoding_mode = sys.argv[3].split("_")[0]
            second_encoding_mode = sys.argv[3].split("_")[1]
        else:
            encoding_mode = sys.argv[3]
            second_encoding_mode = 'nsc'
    else:
        encoding_mode = 'staircase'
        second_encoding_mode = 'nsc'



    if len(sys.argv) > 4:
        solver_name = sys.argv[4]
    else:
        solver_name = 'g421'

    if len(sys.argv) > 5:
        use_local_solver = sys.argv[5].lower() == 'true'
    else:
        use_local_solver = False

    if len(sys.argv) > 6:
        use_tseintin = sys.argv[6].lower() == 'true'
    else:
        use_tseintin = False
    if len(sys.argv) > 7:
        chunk_width = int(sys.argv[7])
    else:
        chunk_width = 5

    if len(sys.argv) > 8:
        solve_one_solution = sys.argv[8].lower() == 'true'
    else:
        solve_one_solution = False

    print(sys.argv)
    print(f"Running NRP with horizon={horizon}, constraint={constraint}, encoding_mode={encoding_mode}, second_encoding_mode={second_encoding_mode}, solver_name={solver_name}, use_local_solver={use_local_solver}, use_tseintin={use_tseintin}, chunk_width={chunk_width}")

    start_time = time.perf_counter()
    nrp = NRP(
        horizon=horizon, constraint=constraint, encoding_mode=encoding_mode, second_encoding_mode=second_encoding_mode,
        solver_name=solver_name, use_local_solver=use_local_solver,
        use_tseintin=use_tseintin, chunk_width=chunk_width
    )
    nrp.add_constraints()

    if not solve_one_solution:
        sol_count, time_to_first_solve = nrp.solve()
    else:
        sol_count, time_to_first_solve = nrp.solve_one_solution()
    end_time = time.perf_counter()

    print(f"\"time\" : {(end_time - start_time)*1000:.0f}")
    print(f"\"timeToFirstSol\" : {(time_to_first_solve-start_time)*1000:.0f}")
    print(f"\"solns\" : {sol_count}")


if __name__ == "__main__":
    main()

