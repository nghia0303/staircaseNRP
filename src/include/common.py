from openpyxl.styles import Alignment
from pysat.formula import CNF


def cl(x: list[int], file=None) -> None:
	for y in x:
		print(y, end=' ', file=file)
	print(0, file=file)


def not_(x: int) -> int:
	return -x


class AddClause:
	def __init__(self, formula: list[list[int]]):
		if formula is None:
			self.formula = []
		else:
			self.formula = formula

	def add_list(self, x: list[int]):
		if len(x) > 0:
			self.formula.append(x)

	def add(self, *args):
		self.add_list(list(args))

	def get_added_clause(self) -> int:
		return len(self.formula)

	def get_clause(self) -> list[list[int]]:
		return self.formula

# New AddClause can be used directly with pysat
# class AddClause:
# 	def __init__(self, formula: list[list[int]] = None):
# 		self.cnf= CNF()
#
# 	def add_list(self, x: list[int]):
# 		if len(x) > 0:
# 			self.cnf.append(x)
#
# 	def add(self, *args):
# 		self.add_list(list(args))
#
# 	def get_added_clause(self) -> int:
# 		return len(self.cnf.clauses)
#
# 	def get_clause(self) -> list[list[int]]:
# 		return self.cnf.clauses

class AuxVariable:
	def __init__(self, first_new_var: int):
		self._last_first_new_var = first_new_var
		self._first_new_var = first_new_var

	def get_new_variable(self) -> int:
		first_new_var = self._first_new_var
		self._first_new_var += 1
		return first_new_var

	def get_total_added_var(self) -> int:
		return self._first_new_var - self._last_first_new_var

	def get_last_used_var(self) -> int:
		return self._first_new_var - 1

	def get_first_new_var(self) -> int:
		return self._first_new_var

	def set_first_new_var(self, first_new_var: int):
		self._first_new_var = first_new_var


def myrange_inclusive(f: int, t: int):
	"""
	[f, t]
	"""
	return range(f, t + 1)


def write_to_cell(cell, value):
	cell.value = value
	if type(cell.value) == float:
		cell.number_format = 'General'
	cell.alignment = Alignment(horizontal="center")


def number_to_column_letter(n: int) -> str:
	result = ""
	while n > 0:
		n, remainder = divmod(n - 1, 26)
		result = chr(65 + remainder) + result

	return result


def pos_2d_to_pos_excel(x: int, y: int) -> str:
	ret = number_to_column_letter(y) + str(x)
	# print(f"({x}, {y}) -> {ret}")
	return ret
