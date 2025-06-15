from encoding.all import str_to_type_enum, Encoder
from include.addline import write_full
from include.common import AuxVariable, AddClause


def create_at_most(encoding_type_str, n, var, k):

    encoder = Encoder(str_to_type_enum(encoding_type_str))
    formula = []
    aux = AuxVariable(first_new_var=n+1)
    add_clause = AddClause(formula)

    encoder.encode_at_most_k(var, k, aux, add_clause)
    total_var = aux.get_last_used_var()

    write_full(total_var, formula, f"tmp/at_most_pysat_{encoding_type_str}.cnf")

def create_at_least(encoding_type_str, n, var, k):
    encoder = Encoder(str_to_type_enum(encoding_type_str))
    formula = []
    aux = AuxVariable(first_new_var=n+1)
    add_clause = AddClause(formula)

    encoder.encode_at_least_k(var, k, aux, add_clause)
    total_var = aux.get_last_used_var()

    write_full(total_var, formula, f"tmp/at_least_pysat_{encoding_type_str}.cnf")


def main():
    n = 10
    var = []
    for i in range(n):
        var.append(i+1)
    k = 3

    encoding_type_str = "pysat_pb_bdd"

    create_at_most(encoding_type_str, n, var, k)

    create_at_least(encoding_type_str, n, var, k)

    encoding_type_str = "pblib_bdd"

    create_at_most(encoding_type_str, n, var, k)

    create_at_least(encoding_type_str, n, var, k)

    pass


if __name__ == "__main__":
    main()