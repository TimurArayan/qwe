from __future__ import annotations
import numpy as np
from numpy.typing import NDArray 
import csv
import scipy
from dataclasses import dataclass
from collections.abc import Callable

from scipy.integrate import dblquad
from types import SimpleNamespace

import generator

class BoundaryGenerator:
	def generate_boundary(self):
		# Граница определяется по рёбрам сетки после загрузки CSV.
		return None


class Triangulator:
	def get_mesh(self, boundary):
		mesh = Mesh()
		points_by_coords = {}

		with open('triangles.csv', 'r', newline='', encoding='utf-8') as f:
			reader = csv.DictReader(f)
			for triangle_id, row in enumerate(reader):
				vertices = []
				for i in range(1, 4):
					coords = (float(row[f'x{i}']), float(row[f'y{i}']))
					if coords not in points_by_coords:
						point = Point(*coords, False)
						points_by_coords[coords] = point
						mesh.points.append(point)
					vertices.append(points_by_coords[coords])
				mesh.triangles.append(Triangle(triangle_id, vertices))

		return mesh




class Point:
    next_id = 0  # общий счётчик для всех объектов Point

    def __init__(self, x, y, isBoundary):
        self.id = Point.next_id
        Point.next_id += 1

        self.x = x
        self.y = y
        self.isBoundary = isBoundary



class Mesh:
	points: list[Point]
	triangles: list[Triangle]
	middles: list[Point]

	def __init__(self):
		self.points = []
		self.triangles = []
		self.middles = []

		# Ребро -> количество треугольников.
		self.edge_counts = {}

		# Ребро -> созданная для него середина.
		self.edge_midpoints = {}

	def add_triangles_midpoints(self):
		# Если в вершинах хранятся ID, заменяем их объектами Point.
		points_by_id = {point.id: point for point in self.points}

		for triangle in self.triangles:
			triangle.vertices = tuple(
				points_by_id[vertex] if isinstance(vertex, int) else vertex
				for vertex in triangle.vertices
			)

		# Считаем, сколько раз встречается каждое ребро.
		self.edge_counts = {}

		for triangle in self.triangles:
			for i in range(3):
				p1 = triangle.vertices[i]
				p2 = triangle.vertices[(i + 1) % 3]

				edge = tuple(sorted((p1.id, p2.id)))
				self.edge_counts[edge] = self.edge_counts.get(edge, 0) + 1

		# Вершины граничных рёбер тоже принадлежат границе.
		points_by_id = {point.id: point for point in self.points}
		for edge, count in self.edge_counts.items():
			if count == 1:
				for point_id in edge:
					points_by_id[point_id].isBoundary = True

		# Создаём середины и связываем их с треугольниками.
		for triangle in self.triangles:
			triangle.get_midpoints(self)


	def make_basises(self):
		for triangle in self.triangles:
			triangle.get_basis()




class Task:

	mesh: Mesh
	nu: float

	def __init__(self, mesh: Mesh, boundary_boundary, nu: float, force):
		self.mesh = mesh
		self.nu = nu
		self.force = force

		if callable(boundary_boundary):
			self.boundary_values = {}

			for point in mesh.points:
				if point.isBoundary:
					self.boundary_values[point] = boundary_boundary(point)
		else:
			self.boundary_values = boundary_boundary

	def get_boundary_values(self):
		return self.boundary_values

	
	





		

class FEMSolver:

	def __init__(self, task : Task, intergrator : Integrator):
		self.task = task
		self.intergrator = intergrator
		return None


	def prepare_slae_1(self):
		middles = len(self.task.mesh.middles)
		nodes = len(self.task.mesh.points) - middles
		size = len(self.task.mesh.points)

		system = np.zeros((2 * size + nodes, 2 * size + nodes))
		system_B = np.zeros(2 * size + nodes)

		for triangle in self.task.mesh.triangles:
			# Узлы и базисные функции давления.
			pp = triangle.vertices
			pfs = triangle.basis.pressure_basis.functions

			# Узлы и базисные функции скорости.
			sp = triangle.vertices + triangle.edge_midpoints
			sfs = triangle.basis.speed_basis.functions

			# Блоки вязкости.
			for i in range(6):
				grad_i = sfs[i].get_basis_gradient()

				for j in range(6):
					grad_j = sfs[j].get_basis_gradient()

					def integrand(x, y):
						point = SimpleNamespace(x=x, y=y)

						gi = grad_i(point)
						gj = grad_j(point)

						return gi[0] * gj[0] + gi[1] * gj[1]

					integral = self.intergrator.integrate(triangle, integrand)

					system[sp[i].id, sp[j].id] += self.task.nu * integral
					system[sp[i].id + size, sp[j].id + size] += self.task.nu * integral

			# Блоки связи давления и скорости.
			for i in range(3):
				pressure_function = pfs[i].get_basis_function()

				for j in range(6):
					grad_j = sfs[j].get_basis_gradient()

					def integrand1(x, y):
						point = SimpleNamespace(x=x, y=y)
						return pressure_function(point) * grad_j(point)[0]

					def integrand2(x, y):
						point = SimpleNamespace(x=x, y=y)
						return pressure_function(point) * grad_j(point)[1]

					integral1 = self.intergrator.integrate(triangle, integrand1)
					integral2 = self.intergrator.integrate(triangle, integrand2)

					system[sp[j].id, pp[i].id + 2 * size] -= integral1
					system[sp[j].id + size, pp[i].id + 2 * size] -= integral2

					system[pp[i].id + 2 * size, sp[j].id] += integral1
					system[pp[i].id + 2 * size, sp[j].id + size] += integral2

			# Правая часть.
			for i in range(6):
				basis_function = sfs[i].get_basis_function()

				def rhs_x(x, y):
					point = SimpleNamespace(x=x, y=y)
					fx, fy = self.task.force(x, y)
					return fx * basis_function(point)

				def rhs_y(x, y):
					point = SimpleNamespace(x=x, y=y)
					fx, fy = self.task.force(x, y)
					return fy * basis_function(point)

				integral_x = self.intergrator.integrate(triangle, rhs_x)
				integral_y = self.intergrator.integrate(triangle, rhs_y)

				system_B[sp[i].id] += integral_x
				system_B[sp[i].id + size] += integral_y

		return system, system_B


	def apply_boundary_conditions(self, system, system_B):
		size = len(self.task.mesh.points)

		def apply_dirichlet(index, value):
			# Учитываем известное значение в остальных уравнениях.
			system_B[:] -= system[:, index] * value

			# Задаём уравнение: неизвестная = value.
			system[index, :] = 0.0
			system[:, index] = 0.0
			system[index, index] = 1.0
			system_B[index] = value

		# Задаём обе компоненты скорости на границе.
		for point, (speed_x, speed_y) in self.task.boundary_values.items():
			apply_dirichlet(point.id, speed_x)
			apply_dirichlet(point.id + size, speed_y)

		# Фиксируем давление в первой вершине.
		p_mean = 2.0
		pressure_index = 2 * size
		apply_dirichlet(pressure_index, p_mean)


	def solve(self):
		system, system_B = self.prepare_slae_1()

		self.apply_boundary_conditions(system, system_B)

		solution = np.linalg.solve(system, system_B)

		return solution





class Integrator:
	def integrate(self, triangle, function):
		p1, p2, p3 = triangle.vertices

		determinant = (
			(p2.x - p1.x) * (p3.y - p1.y)
			- (p3.x - p1.x) * (p2.y - p1.y)
		)

		if determinant == 0:
			raise ValueError("Вершины не образуют треугольник")

		area = abs(determinant) / 2

		# Три точки квадратуры внутри треугольника.
		quadrature_points = (
			((4*p1.x + p2.x + p3.x) / 6,
			 (4*p1.y + p2.y + p3.y) / 6),

			((p1.x + 4*p2.x + p3.x) / 6,
			 (p1.y + 4*p2.y + p3.y) / 6),

			((p1.x + p2.x + 4*p3.x) / 6,
			 (p1.y + p2.y + 4*p3.y) / 6)
		)

		values_sum = 0.0

		for x, y in quadrature_points:
			values_sum += function(x, y)

		return area / 3 * values_sum
















class Triangle:
	id : int
	vertices : tuple[Point, Point, Point]
	edge_midpoints : tuple[Point, Point, Point]
	basis : Basis
	pressure_coeffs : NDArray
	horizontal_speed_coeffs: NDArray
	vertical_speed_coeffs: NDArray

	def __init__(self, id, vertices):
		self.id = id
		self.vertices = vertices

	def get_basis(self):
		basis = Basis(self.vertices, self.edge_midpoints)
		basis.get_pressure_basis()
		basis.get_speed_basis()
		self.basis = basis

	def get_midpoints(self, setka: Mesh):
		midpoints = []

		for i in range(3):
			p1 = self.vertices[i]
			p2 = self.vertices[(i + 1) % 3]

			# Порядок концов не важен: ребро A–B то же, что B–A.
			edge = tuple(sorted((p1.id, p2.id)))

			if edge in setka.edge_midpoints:
				# Середина уже создана соседним треугольником.
				midpoint = setka.edge_midpoints[edge]
			else:
				mix = (p1.x + p2.x) / 2
				miy = (p1.y + p2.y) / 2

				# Граничное ребро принадлежит одному треугольнику.
				is_boundary = setka.edge_counts[edge] == 1

				midpoint = Point(mix, miy, is_boundary)

				setka.points.append(midpoint)
				setka.middles.append(midpoint)
				setka.edge_midpoints[edge] = midpoint

			midpoints.append(midpoint)

		self.edge_midpoints = tuple(midpoints)




	






	def get_solution_functions(self):

		def isInTriangle():
			return True

		def solution_functions(point: Point):
			if isInTriangle() == False:
				raise Exception("точка не в треугольнике")

			pressure_values = [polynom.get_basis_function()(point)
				for polynom in self.basis.pressure_basis.functions]

			speed_values = [polynom.get_basis_function()(point)
				for polynom in self.basis.speed_basis.functions]

			pressure = np.dot(pressure_values, self.pressure_coeffs)
			speed_x = np.dot(speed_values, self.horizontal_speed_coeffs)
			speed_y = np.dot(speed_values, self.vertical_speed_coeffs)

			return pressure, speed_x, speed_y

		return solution_functions

			




class Basis:
	pressure_basis : P1_basis
	speed_basis : P2_basis


	vertices: tuple[Point, Point, Point]
	edge_midpoints:  tuple[Point, Point, Point]

	def __init__(self, vertices, edge_midpoints):
		self.vertices = vertices
		self.edge_midpoints = edge_midpoints

	def get_pressure_basis(self):
		self.pressure_basis = P1_basis(self.vertices)
		self.pressure_basis.fit_functions_list()


	def get_speed_basis(self):
		self.speed_basis = P2_basis(self.vertices, self.edge_midpoints)
		self.speed_basis.fit_functions_list()




class P2_basis:
	functions : list[QuadraticPolynom]

	vertices: tuple[Point, Point, Point]
	edge_midpoints : tuple[Point, Point, Point]


	def __init__(self, vertices, edge_midpoints):
		self.vertices = vertices
		self.edge_midpoints = edge_midpoints


	def fit_functions_list(self):
		self.functions = []
		for i in range(6):
			_function = QuadraticPolynom(self.vertices, self.edge_midpoints)
			_function.get_coeffs(i)
			self.functions.append(_function)




class P1_basis:
	functions : list[LinearPolynom]
	vertices: tuple[Point, Point, Point]
	def __init__(self, vertices):
		self.vertices = vertices

	def fit_functions_list(self):
		self.functions = []
		self.ones = [[True, False, False], [False, True, False], [False,False,True]]
		for i in range(3):
			_function = LinearPolynom(self.vertices)
			_function.get_coeffs(i)
			self.functions.append(_function)



class QuadraticPolynom:
	c1 : float
	c2 : float
	c3 : float
	c4 : float
	c5 : float
	c6 : float

	vertices: tuple[Point, Point, Point]
	edge_midpoints : tuple[Point, Point, Point]

	def __init__(self, vertices, edge_midpoints):
		self.vertices = vertices
		self.edge_midpoints = edge_midpoints


	def get_coeffs(self, i: int):
		if i < 0 or i >= 6:
			raise ValueError("Локальный номер должен быть от 0 до 5")

		points = self.vertices + self.edge_midpoints

		matrix = np.array([
			[1, p.x, p.y, p.x**2, p.x * p.y, p.y**2] for p in points], dtype=float)

		values = np.zeros(6)
		values[i] = 1.0

		coeffs = np.linalg.solve(matrix, values)

		self.c1, self.c2, self.c3, self.c4, self.c5, self.c6 = coeffs



	def get_basis_function(self):
		def basis_function(point) -> float:
			x = point.x
			y = point.y
			return (self.c1 + self.c2 * x + self.c3 * y + self.c4 * x**2 + self.c5 * x * y + self.c6 * y**2)
		return basis_function

	def get_basis_gradient(self):
		def basis_gradient(point) -> tuple[float, float]:
			x = point.x
			y = point.y
			return (self.c2 + 2 * self.c4 * x + self.c5 * y, self.c3 + self.c5 * x + 2 * self.c6 * y)

		return basis_gradient



class LinearPolynom:
	c1 : float
	c2 : float
	c3 : float

	vertices: tuple[Point, Point, Point]

	def __init__(self,vertices):
		self.vertices = vertices

	def get_coeffs(self, i: int):
		p1, p2, p3 = self.vertices

		determinant = ((p2.x - p1.x) * (p3.y - p1.y)
			- (p3.x - p1.x) * (p2.y - p1.y))

		if determinant == 0:
			raise ValueError("Вершины не образуют треугольник")

		if i == 0:
			a, b = p2, p3
		elif i == 1:
			a, b = p3, p1
		elif i == 2:
			a, b = p1, p2
		else:
			raise ValueError("Локальный номер должен быть 0, 1 или 2")

		self.c1 = (a.x * b.y - b.x * a.y) / determinant
		self.c2 = (a.y - b.y) / determinant
		self.c3 = (b.x - a.x) / determinant

	
	def get_basis_function(self):
		def basis_function(point) -> float:
			return self.c1 + self.c2 * point.x + self.c3 * point.y
		return basis_function

	def get_basis_gradient(self):
		def basis_gradient(point) -> tuple[float, float]:
			return (self.c2, self.c3)

		return basis_gradient



