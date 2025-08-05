from src.encoding.baseline_encoding import BaselineEncoding
from src.include.common import AddClause, AuxVariable, not_, myrange_inclusive


def get_calc_clause_build(n: int, k: int):
	return 4 * n * k - n - 2 * k ** 2 - 2


def get_calc_clause_at_least(n: int, k: int):
	return get_calc_clause_build(n, k) + 1


def get_calc_clause_range(n: int, k: int):
	return get_calc_clause_build(n, k) + 1 + n - k


class NSCEncoding(BaselineEncoding):
	class GetVariableNSC:
		def __init__(self, x: list[int], k: int, aux: AuxVariable):
			# (k * (k + 1))/2 + (n - k) * k - 1
			self._aux = aux
			self._x = x
			self._n = len(x)
			self._k = k
			self._r = []
			self._full = True
			for i in myrange_inclusive(1, self._n):
				r = []
				if i == 1:
					self._r.append([x[0]])
					continue
				for _ in myrange_inclusive(1, min(k, i)):
					r.append(aux.get_new_variable())
					# print(f"r[{i}][{_}]: {aux.get_last_used_var()}")
				self._r.append(r)
			# print(f"var: {x}")
			# for i in myrange_inclusive(1, self._n):
			# 	for j in myrange_inclusive(1, min(i, k)):
			# 		print(f"r[{i}][{j}] = {self._r[i - 1][j - 1]}")

		def __exit__(self):
			del self._r

		def get_n(self) -> int:
			return self._n

		def get_k(self) -> int:
			return self._k

		def x(self, i: int) -> int:
			"""
			i from 1 to n
			"""
			if not (1 <= i <= self._n):
				raise RuntimeError(f"sc: i is {i} while n is {self._n}")
			return self._x[i - 1]

		def r(self, i: int, j: int) -> int:
			"""
			i from 1 to n \n
			j from 1 to k
			"""
			if not (0 <= i - 1 < len(self._r)):
				raise RuntimeError(f"nsc: r: i is {i} while n is {self._n}")
			if not (0 <= j - 1 < len(self._r[i - 1])):
				raise RuntimeError(f"nsc: r: j is {j} while len is {len(self._r[i - 1])}")
			return self._r[i - 1][j - 1]

		def get_at_most_n_k(self, i: int, j: int) -> list[int]:
			"""
			i from 1 to n \n
			j from 0 to k
			"""
			if i == 1 and j == 0:
				return [self.not_x(1)]
			if i <= j:  # i variables at most j is always true if i <= j
				return []
			if not (1 <= i <= self._n):
				raise RuntimeError(f"nsc: gamk_n_k: i is {i} while n is {self._n}")
			if not (0 <= j < self._k):
				raise RuntimeError(f"nsc: gamk_n_k: j is {j} while k is {self._k}")
			return [not_(self._r[i - 1][j])]

		def get_at_least_n_k(self, i: int, j: int) -> list[int]:
			if i < j:  # i variables at least j is always false if i < j
				return []
			return [self.r(i, j)]

		def not_x(self, i: int) -> int:
			return not_(self.x(i))

		def not_r(self, i: int, j: int) -> int:
			return not_(self.r(i, j))

	def __init__(self, full: bool = False):
		self.g = None
		self.aux = None
		self.add_clause = None
		self._full = full
		self.debug_mode = False
		self.log_path: str = ""

	def get_variable(self) -> GetVariableNSC:
		return self.g

	def _encode_xi_to_ri1(self):
		# for i: 2 -> n:
		#   x[i] -> r[i][1]
		# n - 1
		for i in myrange_inclusive(2, self.g.get_n()):
			# print(f"x[{i}] -> r[{i}][1]")
			self.add_clause.add(self.g.not_x(i), self.g.r(i, 1))

	def _encode_copy_column(self):
		# for i: 2 -> n:
		#   for j: 1 -> min(i - 1, k):
		#     r[i-1][j] -> r[i][1]
		# k * (k - 1) / 2 + (n - k) * k
		for i in myrange_inclusive(2, self.g.get_n()):
			for j in myrange_inclusive(1, min(i - 1, self.g.get_k())):
				# print(f"r[{i-1}][{j}] -> r[{i}][{j}]: {[self.g.not_r(i - 1, j), self.g.r(i, j)]}")
				self.add_clause.add(self.g.not_r(i - 1, j), self.g.r(i, j))

	def _encode_count_one(self):
		# for i: 2 -> n:
		#   for j: 2 -> min(i, k):
		#     (x[i] and r[i-1][j-1]) -> r[i][j]
		# k * (k - 1) / 2 + (n - k) * (k - 1)
		for i in myrange_inclusive(2, self.g.get_n()):
			for j in myrange_inclusive(2, min(i, self.g.get_k())):
				# print(f"(x[{i}] and r[{i - 1}][{j - 1}]) -> r[{i}][{j}]")
				self.add_clause.add(self.g.not_x(i), self.g.not_r(i - 1, j - 1), self.g.r(i, j))

	def _encode_count_zero(self):
		# for i: 2 -> n:
		#   for j: 1 -> min(i - 1, k):
		#     (not x[i] and not r[i-1][j]) -> not r[i][j]
		# k * (k - 1) / 2 + (n - k) * k
		for i in myrange_inclusive(2, self.g.get_n()):
			for j in myrange_inclusive(1, min(i - 1, self.g.get_k())):
				# print(f"(not x[{i}] and not r[{i - 1}][{j}]) -> not r[{i}][{j}]")
				self.add_clause.add(self.g.x(i), self.g.r(i - 1, j), self.g.not_r(i, j))

	def _encode_not_xi_to_not_rii(self):
		# for i: 2 -> k:
		#  not x[i] -> not r[i][i]
		# k - 1
		for i in myrange_inclusive(2, min(self.g.get_k(), self.g.get_n())):
			# print(f"not x[{i}] -> not r[{i}][{i}]")
			self.add_clause.add(self.g.x(i), self.g.not_r(i, i))

	def _encode_advance_zero(self):
		# for i: 2 -> n:
		#   for j: 2 -> min(i, k):
		#     not r[i-1][j-1] -> not r[i][j]
		# k * (k - 1) / 2 + (n - k) * (k - 1)
		for i in myrange_inclusive(2, self.g.get_n()):
			for j in myrange_inclusive(2, min(i, self.g.get_k())):
				# print(f"not r[{i - 1}][{j - 1}] -> not r[{i}][{j}]")
				self.add_clause.add(self.g.r(i - 1, j - 1), self.g.not_r(i, j))

	def encode_ensure_at_most_k(self, x_np1: int | None):
		# for i: k + 1 -> n:
		#   x[i] -> not r[i-1][k]
		# x[n + 1] -> r[n][k]
		# n - k + 1
		if self.g.get_n() < self.g.get_k():
			return
		for i in myrange_inclusive(self.g.get_k() + 1, self.g.get_n()):
			self.add_clause.add(self.g.not_x(i), self.g.not_r(i - 1, self.g.get_k()))
		if x_np1 is not None:
			self.add_clause.add(not_(x_np1), self.g.not_r(self.g.get_n(), self.g.get_k()))

	def encode_ensure_at_least_k(self, k: int):
		if k <= self.g.get_k():
			self.add_clause.add_list(self.g.get_at_least_n_k(self.g.get_n(), k))
		else:
			print(f"warning: encode_ensure_at_least_k: k is {k} while upper_bound is {self.g.get_k()}")

	def encode_ensure_at_least_k_with_x_np1(self, k: int, x_np1: int):
		# r[n][k] or (r[n][k-1] and x[n+1])
		# <=> (r[n][k] or x[n+1]) and (r[n][k] or r[n][k-1])
		# <=> (r[n][k] or x[n+1]) and (r[n][k-1])
		if k >= 1:
			self.add_clause.add(self.g.r(self.g.get_n(), k), x_np1)
		if k - 1 >= 1:
			self.add_clause.add(self.g.r(self.g.get_n(), k - 1))

	def build(self, var: list[int], upper_bound: int, aux: AuxVariable, add_clause: AddClause):
		# if upper_bound > n:
		# 	upper_bound = n
		self.g = NSCEncoding.GetVariableNSC(var, upper_bound, aux)
		self.add_clause = add_clause
		temp = self.add_clause.get_added_clause()
		self._encode_xi_to_ri1()
		# 		print(self.add_clause.get_added_clause() - temp)
		temp = self.add_clause.get_added_clause()
		self._encode_copy_column()
		# 		print(self.add_clause.get_added_clause() - temp)
		temp = self.add_clause.get_added_clause()
		self._encode_count_one()
		# 		print(self.add_clause.get_added_clause() - temp)
		temp = self.add_clause.get_added_clause()
		self._encode_count_zero()
		# 		print(self.add_clause.get_added_clause() - temp)
		temp = self.add_clause.get_added_clause()
		self._encode_not_xi_to_not_rii()
		# 		print(self.add_clause.get_added_clause() - temp)
		temp = self.add_clause.get_added_clause()
		self._encode_advance_zero()
		# 		print(self.add_clause.get_added_clause() - temp)
		temp = self.add_clause.get_added_clause()

	# 4nk − n − 2k^2 − 2

	def encode_at_most_k(self, var: list[int], k: int, aux: AuxVariable, add_clause: AddClause):
		n = len(var)
		if k > n:
			k = n
		self.g = NSCEncoding.GetVariableNSC(var, k, aux)
		if k == 0:  # at most 0 true is everything false
			for i in myrange_inclusive(1, n):
				add_clause.add(self.g.not_x(i))
			return
		range_to_build = n if self._full else n - 1

		# (1)
		for i in myrange_inclusive(1, range_to_build):
			if k >= 1:
				self.log(f"x{i} -> r{i}_{1}: {[self.g.not_x(i), self.g.r(i, 1)]}")
				add_clause.add(self.g.not_x(i), self.g.r(i, 1))

		# (2)
		for i in myrange_inclusive(2, range_to_build):
			for j in myrange_inclusive(1, min(i - 1, k)):
				self.log(f"r{i - 1}_{j - 1} -> r{i}_{j}: {[self.g.not_r(i - 1, j), self.g.r(i, j)]}")
				add_clause.add(self.g.not_r(i - 1, j), self.g.r(i, j))

		# (3)
		for i in myrange_inclusive(2, range_to_build):
			for j in myrange_inclusive(2, min(i, k)):
				self.log(
					f"x{i} and r{i - 1}_{j - 1} -> r{i}_{j}: {[self.g.not_x(i), self.g.not_r(i - 1, j - 1), self.g.r(i, j)]}")
				add_clause.add(self.g.not_x(i), self.g.not_r(i - 1, j - 1), self.g.r(i, j))

		# (4)
		for i in myrange_inclusive(2, range_to_build):
			for j in myrange_inclusive(2, min(i, k)):
				self.log(
					f"not x{i} and not r{i - 1}_{j - 1} -> not r{i}_{j}: {[self.g.x(i), self.g.r(i - 1, j - 1), self.g.not_r(i, j)]}")
				add_clause.add(self.g.x(i), self.g.r(i - 1, j - 1), self.g.not_r(i, j))

		# (5)
		for i in myrange_inclusive(1, k):
			self.log(f"not x{i} -> not r{i}_{i}")
			if i <= range_to_build:
				add_clause.add(self.g.x(i), self.g.not_r(i, i))

		# (6)
		for i in myrange_inclusive(2, range_to_build):
			for j in myrange_inclusive(2, min(i, k)):
				self.log(f"not r{i - 1}_{j - 1} -> not r{i}_{j}: {[self.g.r(i - 1, j - 1), self.g.not_r(i, j)]}")
				add_clause.add(self.g.r(i - 1, j - 1), self.g.not_r(i, j))

		for i in myrange_inclusive(2, range_to_build):
			for j in myrange_inclusive(1, min(i - 1, k)):
				# not x[i] and not r[i - 1][j] -> not r[i][j]
				add_clause.add(self.g.x(i), self.g.r(i - 1, j), self.g.not_r(i, j))

		# (8)
		for i in myrange_inclusive(k + 1, n):
			if i >= 2:
				self.log(f"x{i} -> r{i - 1}_{k}: {[self.g.not_x(i), self.g.not_r(i - 1, k)]}")
				add_clause.add(self.g.not_x(i), self.g.not_r(i - 1, k))

	def encode_at_least_k(self, var: list[int], k: int, aux: AuxVariable, add_clause: AddClause):
		self.build(var[:-1], k, aux, add_clause)
		self.encode_ensure_at_least_k_with_x_np1(k, var[-1])

	# n = len(var)
	# self.g = NSCEncoding.GetVariableNSC(var, k, self._full, aux)
	# range_to_build = n if self._full else n - 1
	# if True:  # add a block here for ease manage
	# 	if k == 0:
	# 		return 0, 0
	# 	else:
	# 		for i in myrange_inclusive(1, n - 1):
	# 			if k >= 1:
	# 				# x[i] -> r[i][1]
	# 				add_clause.add(self.g.not_x(i), self.g.r(i, 1))
	#
	# 		for i in myrange_inclusive(1, min(n - 1, k)):
	# 			# not x[i] -> not r[i][i]
	# 			add_clause.add(self.g.x(i), self.g.not_r(i, i))
	#
	# 		for i in myrange_inclusive(2, n - 1):
	# 			for j in myrange_inclusive(1, min(i - 1, k)):
	# 				# r[i - 1][j] -> r[i][i]
	# 				add_clause.add(self.g.not_r(i - 1, j), self.g.r(i, j))
	#
	# 		for i in myrange_inclusive(2, n - 1):
	# 			for j in myrange_inclusive(2, min(i, k)):
	# 				# x[i] and r[i - 1][j - 1] -> r[i][i]
	# 				add_clause.add(self.g.not_x(i), self.g.not_r(i - 1, j - 1), self.g.r(i, j))
	#
	# 		for i in myrange_inclusive(2, n - 1):
	# 			for j in myrange_inclusive(1, min(i - 1, k)):
	# 				# not x[i] and not r[i - 1][j] -> not r[i][j]
	# 				add_clause.add(self.g.x(i), self.g.r(i - 1, j), self.g.not_r(i, j))
	#
	# 		for i in myrange_inclusive(2, n - 1):
	# 			for j in myrange_inclusive(2, min(i, k)):
	# 				add_clause.add(self.g.r(i - 1, j - 1), self.g.not_r(i, j))
	#
	# 		if 1 <= k <= n - 1:
	# 			add_clause.add(self.g.r(n - 1, k), self.g.x(n))
	# 		if 1 < k <= n - 1:
	# 			add_clause.add(self.g.r(n - 1, k), self.g.r(n - 1, k - 1))

	def encode_exactly_k(self, var: list[int], k: int, aux: AuxVariable, add_clause: AddClause):
		n = len(var)
		self.g = NSCEncoding.GetVariableNSC(var, k, self._full, aux)
		range_to_build = n if self._full else n - 1
		if True:  # add a block here for ease manage
			for i in myrange_inclusive(1, n - 1):
				if k >= 1:
					add_clause.add(self.g.not_x(i), self.g.r(i, 1))

			for i in myrange_inclusive(1, min(n - 1, k)):
				add_clause.add(self.g.x(i), self.g.not_r(i, i))

			for i in myrange_inclusive(2, n - 1):
				for j in myrange_inclusive(1, min(i - 1, k)):
					add_clause.add(self.g.not_r(i - 1, j), self.g.r(i, j))

			for i in myrange_inclusive(2, n - 1):
				for j in myrange_inclusive(2, min(i, k)):
					add_clause.add(self.g.not_x(i), self.g.not_r(i - 1, j - 1), self.g.r(i, j))

			for i in myrange_inclusive(2, n - 1):
				for j in myrange_inclusive(1, min(i - 1, k)):
					add_clause.add(self.g.x(i), self.g.r(i - 1, j), self.g.not_r(i, j))

			for i in myrange_inclusive(2, n - 1):
				for j in myrange_inclusive(2, min(i, k)):
					add_clause.add(self.g.r(i - 1, j - 1), self.g.not_r(i, j))

			if 1 <= k <= n - 1:
				add_clause.add(self.g.r(n - 1, k), self.g.x(n))
			if 1 < k <= n - 1:
				add_clause.add(self.g.r(n - 1, k), self.g.r(n - 1, k - 1))

			for i in myrange_inclusive(k + 1, n):
				if i >= 2:
					add_clause.add(self.g.not_x(i), self.g.not_r(i - 1, k))


	# k is lower bound, m is upper bound
	def encode_range(self, var: list[int], k: int, m: int, aux: AuxVariable, add_clause: AddClause):
		n = len(var)
		self.g = NSCEncoding.GetVariableNSC(var, m, aux)
		range_to_build = n if self._full else n - 1
		if True:  # add a block here for ease manage
			# (1)
			for i in myrange_inclusive(1, range_to_build):
				if m >= 1:
					add_clause.add(self.g.not_x(i), self.g.r(i, 1))

			for i in myrange_inclusive(1, min(range_to_build, k)):
				add_clause.add(self.g.x(i), self.g.not_r(i, i))

			for i in myrange_inclusive(2, range_to_build):
				for j in myrange_inclusive(1, min(i - 1, m)):
					add_clause.add(self.g.not_r(i - 1, j), self.g.r(i, j))

			for i in myrange_inclusive(2, range_to_build):
				for j in myrange_inclusive(2, min(i, m)):
					add_clause.add(self.g.not_x(i), self.g.not_r(i - 1, j - 1), self.g.r(i, j))

			for i in myrange_inclusive(2, range_to_build):
				for j in myrange_inclusive(1, min(i - 1, m)):
					add_clause.add(self.g.x(i), self.g.r(i - 1, j), self.g.not_r(i, j))

			for i in myrange_inclusive(2, range_to_build):
				for j in myrange_inclusive(2, min(i, m)):
					add_clause.add(self.g.r(i - 1, j - 1), self.g.not_r(i, j))

			if 1 <= k <= n - 1:
				add_clause.add(self.g.r(n - 1, k), self.g.x(n))
			if 1 < k <= n - 1:
				add_clause.add(self.g.r(n - 1, k), self.g.r(n - 1, k - 1))

			for i in myrange_inclusive(m + 1, n):
				if i >= 2:
					add_clause.add(self.g.not_x(i), self.g.not_r(i - 1, m))

	def encode_hybrid(self, var: list[int], k: int, aux: AuxVariable, add_clause: AddClause):
		n: int = len(var)
		if k <= n // 3:
			return self.encode_at_least_k(var, k, aux, add_clause)
		else:
			new_var = [-x for x in var]
			return self.encode_at_most_k(new_var, n - k, aux, add_clause)

	def turn_on_debug_mode(self, filename: str):
		self.debug_mode = True
		self.log_path = filename
		open(filename, "w")

	def turn_off_debug_mode(self):
		self.debug_mode = False

	def log(self, *args):
		if self.debug_mode:
			for value in args:
				print(value, end=' ', file=open(self.log_path, "a"))
			print(file=open(self.log_path, "a"))
