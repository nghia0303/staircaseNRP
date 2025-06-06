from enum import Enum, auto
from typing import Callable

from pypblib import pblib
from pysat.pb import EncType

from src.encoding.binary_encoding import BinaryEncoding
from src.encoding.binomial_encoding import BinomialEncoding
from src.encoding.commander_encoding import CommanderEncoding
from src.encoding.nsc_encoding import NSCEncoding
from src.encoding.pblib_encoding import PBLibEncoding
from src.encoding.product_encoding import ProductEncoding
from src.encoding.sc_encoding import SCEncoding
from src.encoding.at_most_seq_card_encoding import AtMostSeqCard
from src.encoding.pblib_encoding_pysat import PBLibCardEncodingPysat
from src.include.common import AuxVariable, AddClause


class EncodingType(Enum):
	BINARY = auto()
	BINOMIAL = auto()
	COMMANDER = auto()
	NEW_SEQUENCE_COUNTER = auto()
	PRODUCT = auto()
	SEQUENCE_COUNTER = auto()
	PBLIB_ADD = auto()
	PBLIB_BDD = auto()
	PBLIB_CARD = auto()
	PBLIB_CARD_PYSAT = auto()
	PYSAT = auto()
	AT_MOST_SEQ_CARD_SEQUENTIAL_COUNTER = auto()


def str_to_type_enum(encoding_type: str) -> EncodingType:
	if "binary" in encoding_type:
		return EncodingType.BINARY
	if "binomial" in encoding_type:
		return EncodingType.BINOMIAL
	if "commander" in encoding_type:
		return EncodingType.COMMANDER
	if "nsc" in encoding_type:
		return EncodingType.NEW_SEQUENCE_COUNTER
	if "product" in encoding_type:
		return EncodingType.PRODUCT
	if "sc" in encoding_type:
		return EncodingType.SEQUENCE_COUNTER
	if "pblib_add" in encoding_type:
		return EncodingType.PBLIB_ADD
	if "pblib_bdd" in encoding_type:
		return EncodingType.PBLIB_BDD
	if "pblib_card_pysat" in encoding_type:
		return EncodingType.PBLIB_CARD_PYSAT
	if "pblib_card" in encoding_type:
		return EncodingType.PBLIB_CARD
	if "pysat_" in encoding_type:
		return EncodingType.PYSAT
	if "at_most_seq_card" in encoding_type:
		return EncodingType.AT_MOST_SEQ_CARD_SEQUENTIAL_COUNTER
	raise RuntimeError(f"No such encoding: {encoding_type}")


class Encoder:
	def __init__(self, encoding_type: EncodingType, str_encoding_type: str = ""):
		if encoding_type == EncodingType.BINARY:
			self.internal_encoder = BinaryEncoding()
		elif encoding_type == EncodingType.BINOMIAL:
			self.internal_encoder = BinomialEncoding()
		elif encoding_type == EncodingType.COMMANDER:
			self.internal_encoder = CommanderEncoding()
		elif encoding_type == EncodingType.NEW_SEQUENCE_COUNTER:
			self.internal_encoder = NSCEncoding()
		elif encoding_type == EncodingType.PRODUCT:
			self.internal_encoder = ProductEncoding()
		elif encoding_type == EncodingType.SEQUENCE_COUNTER:
			self.internal_encoder = SCEncoding()
		elif encoding_type == EncodingType.PBLIB_ADD:
			config = pblib.PBConfig()
			config.set_AMK_Encoder(pblib.AMK_BEST)
			self.internal_encoder = PBLibEncoding(config)
		elif encoding_type == EncodingType.PBLIB_BDD:
			config = pblib.PBConfig()
			config.set_AMK_Encoder(pblib.AMK_BDD)
			self.internal_encoder = PBLibEncoding(config)
		elif encoding_type == EncodingType.PBLIB_CARD:
			config = pblib.PBConfig()
			config.set_AMK_Encoder(pblib.AMK_CARD)
			self.internal_encoder = PBLibEncoding(config)
		elif encoding_type == EncodingType.PBLIB_CARD_PYSAT:
			self.internal_encoder = PBLibCardEncodingPysat()
		elif encoding_type == EncodingType.PYSAT:
			self.internal_encoder = PBLibCardEncodingPysat(str_encoding_type)
		elif encoding_type == EncodingType.AT_MOST_SEQ_CARD_SEQUENTIAL_COUNTER:
			self.internal_encoder = AtMostSeqCard.SequentialCounter()
		else:
			raise RuntimeError(f"No such encoding: {encoding_type}")

	def encode_at_most_k(self, var: list[int], k: int, aux: AuxVariable, add_clause: AddClause):
		self.internal_encoder.encode_at_most_k(var, k, aux, add_clause)

	def encode_at_least_k(self, var: list[int], k: int, aux: AuxVariable, add_clause: AddClause):
		self.internal_encoder.encode_at_least_k(var, k, aux, add_clause)

	def encode_exactly_k(self, var: list[int], k: int, aux: AuxVariable, add_clause: AddClause):
		self.internal_encoder.encode_exactly_k(var, k, aux, add_clause)

	def encode_range(self, var: list[int], k: int, m: int, aux: AuxVariable, add_clause: AddClause):
		self.internal_encoder.encode_range(var, k, m, aux, add_clause)

	def encode_at_most_k_raw(self, var: list[int], k: int, first_new_var: int, formula: list[list[int]]) -> int:
		aux = AuxVariable(first_new_var)
		add_clause = AddClause(formula)
		self.internal_encoder.encode_at_most_k(var, k, aux, add_clause)
		return aux.get_total_added_var()

	def encode_at_least_k_raw(self, var: list[int], k: int, first_new_var: int, formula: list[list[int]]) -> int:
		aux = AuxVariable(first_new_var)
		add_clause = AddClause(formula)
		self.internal_encoder.encode_at_least_k(var, k, aux, add_clause)
		return aux.get_total_added_var()

	def encode_exactly_k_raw(self, var: list[int], k: int, first_new_var: int, formula: list[list[int]]) -> int:
		aux = AuxVariable(first_new_var)
		add_clause = AddClause(formula)
		self.internal_encoder.encode_exactly_k(var, k, aux, add_clause)
		return aux.get_total_added_var()

	def encode_range_raw(self, var: list[int], k: int, m: int, first_new_var: int, formula: list[list[int]]) -> int:
		aux = AuxVariable(first_new_var)
		add_clause = AddClause(formula)
		self.internal_encoder.encode_range(var, k, m, aux, add_clause)
		return aux.get_total_added_var()

	@staticmethod
	def encode_hybrid(var: list[int], k: int, first_new_var: int, formula: list[list[int]]) -> int:
		nsc = NSCEncoding()
		aux = AuxVariable(first_new_var)
		add_clause = AddClause(formula)
		nsc.encode_hybrid(var, k, aux, add_clause)
		return aux.get_total_added_var()

	def get_normal_encode_function(self, encode_type: str) -> Callable[[list[int], int, int, list[list[int]]], int]:
		if "amk" in encode_type or "at_most_k" in encode_type:
			return self.encode_at_most_k_raw
		if "alk" in encode_type or "at_least_k" in encode_type:
			return self.encode_at_least_k_raw
		if "ek" in encode_type or "exactly_k" in encode_type:
			return self.encode_exactly_k_raw
		if "hybrid" in encode_type:
			return Encoder.encode_hybrid
		raise RuntimeError(f"Encoder: no such function: {encode_type}")

	def get_range_encode_function(self) -> Callable[[list[int], int, int, int, list[list[int]]], int]:
		return self.encode_range
