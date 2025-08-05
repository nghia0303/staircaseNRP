import os


class LocalSolver:

    solver_path = {
        "kissat": "/home/nghia/Desktop/Crew/SAT/kissat/build/kissat",
        "cadical": "/home/nghia/Desktop/Crew/SAT/cadical/build/cadical",
        "glucose": "/home/nghia/Desktop/Crew/SAT/glucose/simp/glucose",
        "glucose_syrup": "/home/nghia/Desktop/Crew/SAT/glucose/parallel/glucose-syrup"
    }

    def __init__(self):
        pass

    @staticmethod
    def run(command: str) -> int:
        # print(command)
        return os.system(command)

    @staticmethod
    def get_all_number_in_file(file: str) -> list[list[int]]:
        args = []
        file = open(f'{file}', 'r')
        for line in file:
            if line.startswith("c") or line.startswith("p") or line.startswith("s"):
                continue

            # args = []
            for num in line.split():
                if num == "" or num == "\n" or num == "v" or num == "0":
                    continue
                args.append(int(num))
            # args.append(arg)
        file.close()
        return args

    def solve(self, solver_name: str, cnf_path: str, output_directory: str):
        output_file_name = cnf_path.split("/")[-1].replace(".cnf", ".out")
        output_folder = os.path.join(output_directory, solver_name)
        if not os.path.exists(output_folder):
            os.makedirs(output_folder)

        output_path = os.path.join(output_folder, output_file_name)

        if solver_name == "kissat" or solver_name == "cadical":
            command = f"{self.solver_path[solver_name]} -q {cnf_path} > {output_path}"
        elif solver_name == "glucose" or solver_name == "glucose_syrup":
            command = f"{self.solver_path[solver_name]} -model -verb=0 {cnf_path} | grep -E '^(s|v) ' > {output_path}"
        else:
            raise ValueError(f"Unknown solver: {solver_name}")

        ret = self.run(command)
        # print("Return code:", ret)
        res = self.get_all_number_in_file(output_path)

        if solver_name == "glucose" or solver_name == "glucose_syrup":
            # For glucose, we need to parse the output differently
            file = open(f'{output_path}', 'r')
            for line in file:
                if line.startswith("s UNSATISFIABLE"):
                    res = []
                    ret = 5120
                    break
                elif line.startswith("s SATISFIABLE"):
                    ret = 2560
                    continue
                # elif line.startswith("v "):
                #     res = [int(x) for x in line.split()[1:] if x != "0"]


        return [
            ret, res
        ]


    # def all_sat(self, solver_name: str, formula: list[list[int]], project: list[int], output_directory: str):
    #
    #     solvable = True
    #     ret = 0
    #     res = []
    #     while solvable:
    #         with open(os.path.join(output_directory, "temp.cnf"), "w") as f:
    #             # Write the CNF header
    #             f.write(f"p cnf {len(project)} {len(formula)}\n")
    #             for clause in formula:
    #                 f.write(" ".join(map(str, clause)) + " 0\n")
    #
    #         ret, res = self.solve(
    #             solver_name,
    #             os.path.join(output_directory, "temp.cnf"),
    #             output_directory
    #         )

    
def main():
    
    # solver = Solver()
    # # Example usage
    # ret, res = solver.solve(
    #     "kissat",
    #     "/home/nghia/Desktop/NRP_nghia/src/test/tmp/amongNurse.cnf",
    #     "/home/nghia/Desktop/NRP_nghia/src/test/tmp"
    # )
    #
    # print(f"Return code: {ret}, Results: {res}")



    pass

if __name__ == "__main__":
    main()