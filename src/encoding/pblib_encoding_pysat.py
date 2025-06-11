from pysat.card import *
from src.encoding.baseline_encoding import BaselineEncoding
from src.include.common import AddClause, AuxVariable

from pysat.pb import PBEnc
from pysat.pb import EncType as PbEncType



class PBLibCardEncodingPysat(BaselineEncoding):
	def __init__(self, str_encoding_type=""):

		self.use_pysat_pb = False

		if str_encoding_type == "":
			self.encoding_type = EncType.cardnetwrk

		elif "pysat_pb" in str_encoding_type:
			'''
				best = 0
				bdd = 1
				seqcounter = 2
				sortnetwrk = 3
				adder = 4
				binmerge = 5
				native = 6
			'''

			self.use_pysat_pb = True

			if "best" in str_encoding_type:
				self.encoding_type = PbEncType.best
			elif "bdd" in str_encoding_type:
				self.encoding_type = PbEncType.bdd
			elif "seqcounter" in str_encoding_type:
				self.encoding_type = PbEncType.seqcounter
			elif "sortnetwrk" in str_encoding_type:
				self.encoding_type = PbEncType.sortnetwrk
			elif "adder" in str_encoding_type:
				self.encoding_type = PbEncType.adder
			elif "binmerge" in str_encoding_type:
				self.encoding_type = PbEncType.binmerge
			elif "native" in str_encoding_type:
				self.encoding_type = PbEncType.native


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
		if self.use_pysat_pb:
			cnf = PBEnc.atmost(lits=var, bound=k, encoding=self.encoding_type, top_id=aux.get_last_used_var())
		else:
			cnf = CardEnc.atmost(lits=var, bound=k, encoding=self.encoding_type, top_id=aux.get_last_used_var())
		for clause in cnf.clauses:
			add_clause.add_list(clause)
			for x in clause:
				last_used_var = max(last_used_var, x)
		aux.set_first_new_var(last_used_var + 1)

	def encode_at_least_k(self, var: list[int], k: int, aux: AuxVariable, add_clause: AddClause):
		last_used_var = aux.get_last_used_var()
		if self.use_pysat_pb:
			cnf = PBEnc.atleast(lits=var, bound=k, encoding=self.encoding_type, top_id=aux.get_last_used_var())
		else:
			cnf = CardEnc.atleast(lits=var, bound=k, encoding=self.encoding_type, top_id=aux.get_last_used_var())
		for clause in cnf.clauses:
			add_clause.add_list(clause)
			for x in clause:
				last_used_var = max(last_used_var, x)
		aux.set_first_new_var(last_used_var + 1)

	def encode_exactly_k(self, var: list[int], k: int, aux: AuxVariable, add_clause: AddClause):
		last_used_var = aux.get_last_used_var()
		if self.use_pysat_pb:
			cnf = PBEnc.equals(lits=var, bound=k, encoding=self.encoding_type, top_id=aux.get_last_used_var())
		else:
			cnf = CardEnc.equals(lits=var, bound=k, encoding=self.encoding_type, top_id=aux.get_last_used_var())
		# cnf = CardEnc.equals(lits=var, bound=k, encoding=self.encoding_type, top_id=aux.get_last_used_var())
		for clause in cnf.clauses:
			add_clause.add_list(clause)
			for x in clause:
				last_used_var = max(last_used_var, x)
		aux.set_first_new_var(last_used_var + 1)
