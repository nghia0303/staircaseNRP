from src.encoding.baseline_encoding import BaselineEncoding
from src.include.common import AddClause, AuxVariable, not_, myrange_inclusive


def _backtrack_internal(pos: int, n: int, k: int, chosen: list[int], res: list[list[int]]) -> None:
	if len(chosen) >= k:
		li = []
		for x in chosen:
			li.append(x)
		res.append(li)
		return
	for i in myrange_inclusive(pos, n):
		if len(chosen) + (n - i + 1) < k:
			break
		chosen.append(i)
		_backtrack_internal(i + 1, n, k, chosen, res)
		chosen.pop()


def _backtrack_comb(n: int, k: int) -> list[list[int]]:
	res: list[list[int]] = []
	_backtrack_internal(1, n, k, [], res)
	return res


class BinomialEncoding(BaselineEncoding):
	class GetVariableBinomial:
		def __init__(self, x: list[int]):
			self.__x = x
			self.__n = len(x)

		def x(self, i: int) -> int:
			"""
			i from 1 to n
			"""
			if not (1 <= i <= self.__n):
				raise RuntimeError(f"binomial: i is {i} while n is {self.__n}")
			return self.__x[i - 1]

		def not_x(self, i: int) -> int:
			return not_(self.x(i))

	def encode_at_most_k(self, var: list[int], k: int, _aux: AuxVariable, add_clause: AddClause):
		n = len(var)
		# At most k true <=> every comb(n, k + 1) has at least 1 false
		comb: list[list[int]] = _backtrack_comb(n, k + 1)
		g = BinomialEncoding.GetVariableBinomial(var)

		for xs in comb:
			cl = []
			for i in xs:
				cl.append(g.not_x(i))
			add_clause.add_list(cl)


	def encode_at_least_k(self, var: list[int], k: int, _aux: AuxVariable, add_clause: AddClause):
		n = len(var)
		# At least k true <=> every comb(n, n - k + 1) has at least 1 true
		comb: list[list[int]] = _backtrack_comb(n, n - k + 1)
		g = BinomialEncoding.GetVariableBinomial(var)

		for xs in comb:
			cl = []
			for x in xs:
				cl.append(g.x(x))
			add_clause.add_list(cl)
