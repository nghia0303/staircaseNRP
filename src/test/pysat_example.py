
from pysat.formula import CNF

def main():
    """
    Create an example using pysat to encode and solve directly with pysat API.
    """

    formula = [
        [1, 2, 3],
        [-1, 2],
        [-2, 3],
        [-3, -1],
        [1, -2, -3]
    ]

    cnf = CNF(from_clauses=formula)

    formula.append([4, 6])

    print(cnf.clauses)




    pass

if __name__ == "__main__":
    main()
