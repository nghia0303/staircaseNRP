from pysat.card import *
from src.encoding.baseline_encoding import BaselineEncoding
from src.include.common import AddClause, AuxVariable

class PysatEncoding(BaselineEncoding):

    def __init__(self, str_encoding_type=""):
        if str_encoding_type == "":
            self.encoding_type = EncType.cardnetwrk
        else:
            '''
            pairwise    = 0
            seqcounter  = 1
            sortnetwrk  = 2
            cardnetwrk  = 3
            bitwise     = 4
            ladder      = 5
            totalizer   = 6
            mtotalizer  = 7
            kmtotalizer = 8
            native      = 9
            '''
            if "pairwise" in str_encoding_type:
                self.encoding_type = EncType.pairwise
            elif "seqcounter" in str_encoding_type:
                self.encoding_type = EncType.seqcounter
            elif "sortnetwrk" in str_encoding_type:
                self.encoding_type = EncType.sortnetwrk
            elif "cardnetwrk" in str_encoding_type:
                self.encoding_type = EncType.cardnetwrk
            elif "bitwise" in str_encoding_type:
                self.encoding_type = EncType.bitwise
            elif "ladder" in str_encoding_type:
                self.encoding_type = EncType.ladder
            elif "totalizer" in str_encoding_type:
                self.encoding_type = EncType.totalizer
            elif "mtotalizer" in str_encoding_type:
                self.encoding_type = EncType.mtotalizer
            elif "kmtotalizer" in str_encoding_type:
                self.encoding_type = EncType.kmtotalizer
            elif "native" in str_encoding_type:
                self.encoding_type = EncType.native

        pass

    def encode_at_most_k(self, var: list[int], k: int, aux: AuxVariable, add_clause: AddClause):
        last_used_var = aux.get_last_used_var()
        cnf = CardEnc.atmost(lits=[var], bound=k, encoding=self.encoding_type, top_id=aux.get_last_used_var())
        for clause in cnf.clauses:
            add_clause.add(clause)
            for x in clause:
                last_used_var = max(last_used_var, x)
        aux.set_first_new_var(last_used_var + 1)

    def encode_at_least_k(self, var: list[int], k: int, aux: AuxVariable, add_clause: AddClause):
        last_used_var = aux.get_last_used_var()
        cnf = CardEnc.atleast(lits=[var], bound=k, encoding=self.encoding_type, top_id=aux.get_last_used_var())
        for clause in cnf.clauses:
            add_clause.add(clause)
            for x in clause:
                last_used_var = max(last_used_var, x)
        aux.set_first_new_var(last_used_var + 1)

    def encode_exactly_k(self, var: list[int], k: int, aux: AuxVariable, add_clause: AddClause):
        last_used_var = aux.get_last_used_var()
        cnf = CardEnc.equals(lits=[var], bound=k, encoding=self.encoding_type, top_id=aux.get_last_used_var())
        for clause in cnf.clauses:
            add_clause.add(clause)
            for x in clause:
                last_used_var = max(last_used_var, x)
        aux.set_first_new_var(last_used_var + 1)