from pypblib import pblib

from src.encoding.all import Encoder, EncodingType
from src.encoding.nsc_encoding import NSCEncoding, get_calc_clause_build, get_calc_clause_at_least, \
	get_calc_clause_range
from src.encoding.pblib_encoding import PBLibEncoding
from src.include.common import AuxVariable, AddClause, myrange_inclusive


class StaircaseEncoding:
	class Window:
		def __init__(self):
			self.upper_part: NSCEncoding = None
			self.lower_part: NSCEncoding = None

		def encode_window_at_most(self, var: list[int], window_num: int, window_size: int, cap: int, num_window: int, aux: AuxVariable, add_clause: AddClause):
			start_of_window = window_num * window_size  # inclusive
			end_of_window = start_of_window + window_size  # exclusive
			if end_of_window > len(var):
				end_of_window = len(var)
			var_now = var[start_of_window:end_of_window]
			if window_num == 0:  # first window, no upper_part
				self.upper_part = None
				self.lower_part = NSCEncoding(False)
				self.lower_part.encode_at_most_k(var_now[::-1], cap, aux, add_clause)

			elif window_num == num_window - 1:  # last window, no lower_part
				full = True if len(var_now) < window_size else False
				self.upper_part = NSCEncoding(full)
				self.lower_part = None
				self.upper_part.encode_at_most_k(var_now, cap, aux, add_clause)
			else:
				self.upper_part = NSCEncoding(True)
				self.lower_part = NSCEncoding(False)
				# The reason we reverse var_now is because of
				#  | 4
				#  | 4 5
				#  | 4 5 6 |
				#      5 6 |
				#        6 |
				# we need 6 <= k, then 5 6 <= k, then 4 5 6 <= k
				self.upper_part.encode_at_most_k(var_now[:-1], cap, aux, add_clause)
				self.lower_part.encode_at_most_k(var_now[::-1], cap, aux, add_clause)

		def encode_window(self, var: list[int], window_num: int, window_size: int, floor: int, cap: int, num_window: int, aux: AuxVariable, add_clause: AddClause):
			# variable: (M *  range_v(w, floor) + (M - 2) * build(w - 1, floor ) )
			# clause: ( alk_c(w, floor) + alk_c(w - 1, floor ) )
			start_of_window = window_num * window_size  # inclusive
			end_of_window = start_of_window + window_size  # exclusive
			if end_of_window > len(var):
				end_of_window = len(var)
			var_now = var[start_of_window:end_of_window]
			if window_num == 0:  # first window, no upper_part
				self.upper_part = None
				self.lower_part = NSCEncoding(False)
				# temp = add_clause.get_added_clause()
				# print(f"cap floor: {cap}, {floor}")
				self.lower_part.build(var_now[::-1], cap, aux, add_clause)
				# self.lower_part.encode_ensure_at_most_k(var_now[0])
				self.lower_part.encode_ensure_at_most_k(None)
				self.lower_part.encode_ensure_at_least_k(floor)
				# print(add_clause.get_added_clause() - temp)
			elif window_num == num_window - 1:  # last window, no lower_part
				self.upper_part = NSCEncoding()
				self.lower_part = None
				self.upper_part.build(var_now, cap, aux, add_clause)
				if len(var_now) == window_size:
					self.upper_part.encode_ensure_at_least_k(floor)
				self.upper_part.encode_ensure_at_most_k(None)
			else:
				self.upper_part = NSCEncoding(True)
				self.lower_part = NSCEncoding(False)
				# The reason we reverse var_now is because of
				#  | 4
				#  | 4 5
				#  | 4 5 6 |
				#      5 6 |
				#        6 |
				# we need 6 <= k, then 5 6 <= k, then 4 5 6 <= k
				self.upper_part.build(var_now[:-1], cap, aux, add_clause)
				self.lower_part.build(var_now[::-1], cap, aux, add_clause)
				self.lower_part.encode_ensure_at_most_k(None)
				self.lower_part.encode_ensure_at_least_k(floor)

		def encode_window_at_least(self, var: list[int], window_num: int, window_size: int, floor: int, num_window: int, aux: AuxVariable, add_clause: AddClause):
			# w windows (window_size, floor), w - 2 windows (window_size - 1, floor)
			start_of_window = window_num * window_size  # inclusive
			end_of_window = start_of_window + window_size  # exclusive
			if end_of_window > len(var):
				end_of_window = len(var)
			var_now = var[start_of_window:end_of_window]
			if window_num == 0:  # first window, no upper_part
				self.upper_part = None
				self.lower_part = NSCEncoding(False)
				self.lower_part.build(var_now[::-1], floor, aux, add_clause)
				self.lower_part.encode_ensure_at_least_k(floor)
			elif window_num == num_window - 1:  # last window, no lower_part
				full = True if len(var_now) < window_size else False
				self.upper_part = NSCEncoding(full)
				self.lower_part = None
				self.upper_part.build(var_now, floor, aux, add_clause)
				if len(var_now) == window_size:
					self.upper_part.encode_ensure_at_least_k(floor)
			else:
				self.upper_part = NSCEncoding(True)
				self.lower_part = NSCEncoding(False)
				# The reason we reverse var_now is because of
				#  | 4
				#  | 4 5
				#  | 4 5 6 |
				#      5 6 |
				#        6 |
				# we need 6 <= k, then 5 6 <= k, then 4 5 6 <= k
				self.upper_part.build(var_now[:-1], floor, aux, add_clause)
				self.lower_part.build(var_now[::-1], floor, aux, add_clause)
				self.lower_part.encode_ensure_at_least_k(floor)

	def __init__(self):
		self.var = None
		self.n = 0
		self.window_size = 0
		self.floor = 0
		self.cap = 0
		self.num_window = 0
		self.aux: AuxVariable = AuxVariable(0)
		self.add_clause: AddClause = AddClause([])
		self.windows: list[StaircaseEncoding.Window] = []

	def __encode_window_at_most(self, window_num: int):
		"""
		Windows look like this
		       Window 1        Window 2        Window 3        Window 4
		       1   2   3   |               |               |
		           2   3   |   4           |               |
		               3   |   4   5       |               |
		                   |   4   5   6   |               |
		                   |       5   6   |   7           |
		                   |           6   |   7   8       |
		                   |               |   7   8   9   |
		                   |               |       8   9   |   10
		                   |               |           9   |   10  11
		"""
		window = StaircaseEncoding.Window()
		window.encode_window_at_most(self.var, window_num, self.window_size, self.cap, self.num_window, self.aux, self.add_clause)
		self.windows.append(window)

	def __encode_window(self, window_num: int):
		"""
		Windows look like this
		       Window 1        Window 2        Window 3        Window 4
		       1   2   3   |               |               |
		           2   3   |   4           |               |
		               3   |   4   5       |               |
		                   |   4   5   6   |               |
		                   |       5   6   |   7           |
		                   |           6   |   7   8       |
		                   |               |   7   8   9   |
		                   |               |       8   9   |   10
		                   |               |           9   |   10  11
		"""
		window = StaircaseEncoding.Window()
		window.encode_window(self.var, window_num, self.window_size, self.floor, self.cap, self.num_window, self.aux, self.add_clause)
		self.windows.append(window)

	def __encode_window_at_least(self, window_num: int):
		"""
		Windows look like this
		       Window 1        Window 2        Window 3        Window 4
		       1   2   3   |               |               |
		           2   3   |   4           |               |
		               3   |   4   5       |               |
		                   |   4   5   6   |               |
		                   |       5   6   |   7           |
		                   |           6   |   7   8       |
		                   |               |   7   8   9   |
		                   |               |       8   9   |   10
		                   |               |           9   |   10  11
		"""
		window = StaircaseEncoding.Window()
		window.encode_window_at_least(self.var, window_num, self.window_size, self.floor, self.num_window, self.aux, self.add_clause)
		self.windows.append(window)

	def __glue_window_at_most(self, window_num: int):
		"""
		Glue the lower_part of windows[window_num] to the upper_part of windows[window_num + 1]
		"""
		# u_e = min(cap, w - cap)
		# ( ( u_e * (u_e + 1) + (w - 1 - u_e * 2) * u_e ) )
		left = self.windows[window_num].lower_part.get_variable()
		right = self.windows[window_num + 1].upper_part.get_variable()
		step = self.window_size - 1
		cap = self.cap
		for i in range(step):
			left_var_for_step = left.get_n() - i - 1
			right_var_for_step = i + 1
			if left_var_for_step < 1 or right_var_for_step > right.get_n():
				break
			for j in myrange_inclusive(0, cap - 1):
				current_formula = []
				left_formula = left.get_at_most_n_k(left_var_for_step, cap - j - 1)
				right_formula = right.get_at_most_n_k(right_var_for_step, j)
				# print(f"left: {left_var_for_step} {cap-j-1}, right: {right_var_for_step} {j}")
				# print(f"left: {left_formula}, right: {right_formula}")
				if len(left_formula) > 0 and len(right_formula) > 0:
					for _ in left_formula:
						current_formula.append(_)
					for _ in right_formula:
						current_formula.append(_)

					# print(f"at most added: ", end='')
					# for _ in current_formula:
					# 	print(_, end=' ')
					# print()
					self.add_clause.add_list(current_formula)
				else:
					pass

	def __glue_window_at_least(self, window_num: int):
		"""
		Glue the lower_part of windows[window_num] to the upper_part of windows[window_num + 1]
		"""
		# ( (w - 1) * floor )
		left = self.windows[window_num].lower_part.get_variable()
		right = self.windows[window_num + 1].upper_part.get_variable()
		step = self.window_size - 1
		floor = self.floor
		for i in range(step):
			left_var_for_step = (left.get_n()) - i - 1
			right_var_for_step = i + 1
			if left_var_for_step < 1 or right_var_for_step > right.get_n():
				break
			only_left = None
			only_right = None
			both_left_right = []
			# print(f"at_least: l_r: {left_var_for_step}, {right_var_for_step}")
			for j in myrange_inclusive(1, floor):
				current_formula = []
				left_formula = left.get_at_least_n_k(left_var_for_step, j)
				right_formula = right.get_at_least_n_k(right_var_for_step, floor - j + 1)
				for _ in left_formula:
					current_formula.append(_)
				for _ in right_formula:
					current_formula.append(_)
				if len(left_formula) > 0 and len(right_formula) > 0:
					both_left_right.append(current_formula)
				elif len(left_formula) > 0:
					only_left = current_formula
				elif len(right_formula) > 0:
					if only_right is None:
						only_right = current_formula
				else:
					raise RuntimeError(f"glue_window_at_least: {current_formula}")
			aug = 0
			if only_left is not None:
				self.add_clause.add_list(only_left)
				# print(only_left)
				aug += 1
			aug += len(both_left_right)
			for current_formula in both_left_right:
				self.add_clause.add_list(current_formula)
				# print(current_formula)
			if only_right is not None:
				self.add_clause.add_list(only_right)
				# print(only_right)
				aug += 1

	def _do_glue_at_least(self):
		for window_num in range(0, self.num_window - 1):
			self.__glue_window_at_least(window_num)

	def _do_glue_at_most(self):
		for window_num in range(0, self.num_window - 1):
			self.__glue_window_at_most(window_num)


	# At most
	def encode_staircase(self, var: list[int], window_size: int, cap: int, aux: AuxVariable, add_clause: AddClause):
		self.var = var
		self.n = len(var)
		self.window_size = window_size
		self.cap = cap
		self.num_window = (self.n + window_size - 1) // window_size
		self.aux = aux
		self.add_clause = add_clause
		self.windows = []

		if window_size == cap:
			return 0

		for window_num in range(0, self.num_window):
			self.__encode_window_at_most(window_num)

		for window_num in range(0, self.num_window - 1):
			self.__glue_window_at_most(window_num)

	def encode_staircase_range(self, var: list[int], window_size: int, floor: int, cap: int, aux: AuxVariable, add_clause: AddClause):
		self.var = var
		self.n = len(var)
		self.window_size = window_size
		self.floor = floor
		self.cap = cap
		self.num_window = (self.n + window_size - 1) // window_size
		self.aux = aux
		self.add_clause = add_clause
		self.windows = []

		# (n / w - 1) * ...
		for window_num in range(0, self.num_window):
			self.__encode_window(window_num)

		# (n / w - 1) * ...
		self._do_glue_at_least()

		self._do_glue_at_most()

		# variable: 2n cap − 2w cap + cap^2 − cap + 2 + (n cap − n cap^2 − 2n) / w
		# clause: 9n cap + n floor − 2n + 2w − 9w cap - w floor + 4cap^2 + 5cap + floor + 1 − (4n cap^2 + 5n cap + n floor + n) / w

	def encode_staircase_at_least(self, var: list[int], window_size: int, floor: int, aux: AuxVariable, add_clause: AddClause):
		self.var = var
		self.n = len(var)
		self.window_size = window_size
		self.floor = floor
		self.num_window = (self.n + window_size - 1) // window_size
		self.aux = aux
		self.add_clause = add_clause
		self.windows = []

		# (n / w - 1) * ...
		for window_num in range(0, self.num_window):
			self.__encode_window_at_least(window_num)

		# (n / w - 1) * ...
		self._do_glue_at_least()

		# variable: 2n floor − 2w floor + floor^2 − floor + 2 + (n floor − n floor^2 − 2n) / w
		# clause: 9n floor − 2n + 2w − 9w floor + 4floor^2 + 5floor + 1 − (4n floor^2 + 5n floor + n) / w

	def staircase(self, var: list[int], window_size: int, cap: int, first_new_var: int, clause: list[list[int]]) -> int:
		aux = AuxVariable(first_new_var)
		add_clause = AddClause(clause)
		self.encode_staircase(var, window_size, cap, aux, add_clause)
		return aux.get_total_added_var()

	def staircase_brute_nsc(self, var: list[int], window_size: int, cap: int, first_new_var: int, formula: list[list[int]]) -> int:
		self.var = var
		self.n = len(var)
		self.window_size = window_size
		self.cap = cap
		self.num_window = (self.n + window_size - 1) // window_size
		self.aux = AuxVariable(first_new_var)
		self.add_clause = AddClause(formula)

		for i in myrange_inclusive(0, self.n - window_size):
			nsc = NSCEncoding(False)
			var_now = [var[i+j] for j in range(window_size)]
			nsc.encode_at_most_k(var_now, cap, self.aux, self.add_clause)

		return self.aux.get_total_added_var()

	def staircase_brute_pblib(self, var: list[int], window_size: int, cap: int, first_new_var: int, formula: list[list[int]]) -> int:
		self.var = var
		self.n = len(var)
		self.window_size = window_size
		self.cap = cap
		self.num_window = (self.n + window_size - 1) // window_size
		self.aux = AuxVariable(first_new_var)
		self.add_clause = AddClause(formula)

		for i in myrange_inclusive(0, self.n - window_size):
			config = pblib.PBConfig()
			config.set_AMK_Encoder(pblib.AMK_CARD)
			encoder = PBLibEncoding(config)
			var_now = [var[i+j] for j in range(window_size)]
			encoder.encode_at_most_k(var_now, cap, self.aux, self.add_clause)

		return self.aux.get_total_added_var()
