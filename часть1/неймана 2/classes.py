from __future__ import annotations
import numpy as np
from numpy.typing import NDArray 
import csv
import scipy
from dataclasses import dataclass
from collections.abc import Callable

from scipy.integrate import dblquad
from types import SimpleNamespace





class Solution:

	def __init__(self, mesh: Mesh, solution_vector: NDArray):
		self.mesh = mesh
		self.solution_vector = solution_vector
		size = len(self.mesh.points)
		self.speed_x = self.solution_vector[:size].copy()
		self.speed_y = self.solution_vector[size:2 * size].copy()
		self.pressure = self.solution_vector[2 * size:].copy()
		

	def reshenie(self, point):
		
		

		for triangle in self.mesh.triangles:
			if triangle.contains(point):
				speed_nodes = triangle.vertices + triangle.edge_midpoints
				pressure_nodes = triangle.vertices

				
				speed_values = triangle.thbasis.speed_functions(point)
				pressure_values = triangle.thbasis.pressure_functions(point)

				
				speed_x_coeffs = [self.speed_x[node.id] for node in speed_nodes]
				speed_y_coeffs = [self.speed_y[node.id] for node in speed_nodes]
				pressure_coeffs = [self.pressure[node.id] for node in pressure_nodes]

				vx = np.dot(speed_x_coeffs, speed_values)
				vy = np.dot(speed_y_coeffs, speed_values)
				p = np.dot(pressure_coeffs, pressure_values)

				return vx, vy, p

		raise ValueError("Точка находится вне сетки")

	def get_reshenie_func(self):
		def func(x, y):
			temp_point = SimpleNamespace(x=x, y=y)
			return self.reshenie(temp_point)

		return func



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

					# Пустая ячейка — внутренняя точка.
					type_value = row[f'boundary_type{i}'].strip()

					if type_value == '':
						is_boundary = False
						boundary_type = None
					else:
						is_boundary = True
						boundary_type = int(type_value)

					if coords not in points_by_coords:
						point = Point(
							*coords,
							is_boundary,
							boundary_type
						)
						points_by_coords[coords] = point
						mesh.points.append(point)

					vertices.append(points_by_coords[coords])

				mesh.triangles.append(Triangle(triangle_id, vertices))

		return mesh




class Point:
	next_id = 0 

	def __init__(self, x, y, isBoundary, boundary_type=None):
		if not isBoundary and boundary_type is not None:
			raise ValueError("Неграничные узлы не имеют типа ГУ")

		if isBoundary and boundary_type not in (0, 1):
			raise ValueError("Для граничного узла укажите: 0 — Дирихле, 1 — Нейман")

		self.id = Point.next_id
		Point.next_id += 1

		self.x = x
		self.y = y
		self.isBoundary = isBoundary
		self.boundary_type = boundary_type
       		




class Mesh:

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
			pressure_nodes = triangle.vertices
			speed_nodes = triangle.vertices + triangle.edge_midpoints
			basis = triangle.thbasis

			# Блоки вязкости.
			for i in range(6):
				for j in range(6):

					def speed_integrand(x, y):
						point = SimpleNamespace(x=x, y=y)
						gradients = basis.speed_functions_gradient(point)

						grad_i = gradients[i]
						grad_j = gradients[j]

						return np.dot(grad_i, grad_j)

					speed_integral = self.intergrator.integrate(
						triangle, speed_integrand
					)

					ii = speed_nodes[i].id
					jj = speed_nodes[j].id

					system[ii, jj] += self.task.nu * speed_integral
					system[ii + size, jj + size] += self.task.nu * speed_integral

			# Блоки связи давления и скорости.
			for k in range(3):
				for j in range(6):

					def pressure_integrand_x(x, y):
						point = SimpleNamespace(x=x, y=y)

						pressure_value = basis.pressure_functions(point)[k]
						grad_j = basis.speed_functions_gradient(point)[j]

						return pressure_value * grad_j[0]

					def pressure_integrand_y(x, y):
						point = SimpleNamespace(x=x, y=y)

						pressure_value = basis.pressure_functions(point)[k]
						grad_j = basis.speed_functions_gradient(point)[j]

						return pressure_value * grad_j[1]

					pressure_integral_x = self.intergrator.integrate(
						triangle, pressure_integrand_x
					)
					pressure_integral_y = self.intergrator.integrate(
						triangle, pressure_integrand_y
					)

					speed_id = speed_nodes[j].id
					pressure_id = pressure_nodes[k].id + 2 * size

					system[speed_id, pressure_id] -= pressure_integral_x
					system[speed_id + size, pressure_id] -= pressure_integral_y

					system[pressure_id, speed_id] += pressure_integral_x
					system[pressure_id, speed_id + size] += pressure_integral_y

			# Правая часть.
			for i in range(6):

				def rhs_integrand_x(x, y):
					point = SimpleNamespace(x=x, y=y)
					fx, fy = self.task.force(x, y)

					return fx * basis.speed_functions(point)[i]

				def rhs_integrand_y(x, y):
					point = SimpleNamespace(x=x, y=y)
					fx, fy = self.task.force(x, y)

					return fy * basis.speed_functions(point)[i]

				rhs_integral_x = self.intergrator.integrate(
					triangle, rhs_integrand_x
				)
				rhs_integral_y = self.intergrator.integrate(
					triangle, rhs_integrand_y
				)

				system_B[speed_nodes[i].id] += rhs_integral_x
				system_B[speed_nodes[i].id + size] += rhs_integral_y

		return system, system_B






	def apply_boundary_conditions(self, system, system_B):
		size = len(self.task.mesh.points)

		def apply_dirichlet(index, value):
			system_B[:] -= system[:, index] * value

			
			system[index, :] = 0.0
			system[:, index] = 0.0
			system[index, index] = 1.0
			system_B[index] = value

		
		for point, (speed_x, speed_y) in self.task.boundary_values.items():
			if point.boundary_type == 0:
				apply_dirichlet(point.id, speed_x)
				apply_dirichlet(point.id + size, speed_y)

		




	def add_neumann_conditions(self, system_B, p_in, p_out):
		size = len( self.task.mesh.points)
		
		for triangle in self.task.mesh.triangles:
			speed_nodes = triangle.vertices + triangle.edge_midpoints
			speed_functions = triangle.thbasis.speed_functions

			for edge_index in range(3):
				p1 = triangle.vertices[edge_index]
				p2 = triangle.vertices[(edge_index + 1) % 3]
				middle = triangle.edge_midpoints[edge_index]

				
				if not middle.isBoundary or middle.boundary_type != 1:
					continue

				eps = 1e-9
				if abs(p1.x - 1.0) < eps and abs(p2.x - 1.0) < eps:
					pressure = p_in
					nx, ny = -1.0, 0.0
				elif abs(p1.x - 4.0) < eps and abs(p2.x - 4.0) < eps:
					pressure = p_out
					nx, ny = 1.0, 0.0
				else:
					raise ValueError("Не удалось определить вход или выход")



				# На ребре ненулевые только две функции вершин и функция его середины.
				local_indices = (edge_index, (edge_index + 1) % 3, 3 + edge_index)

				for local_index in local_indices:
					point = speed_nodes[local_index]
					
					def integrand(x, y):
						temp_point = SimpleNamespace(x=x, y=y)
						return speed_functions(temp_point)[local_index]

					integral = self.intergrator.integrate_edge(p1, p2, integrand)

					system_B[point.id] -= pressure * nx * integral
					system_B[point.id + size] -= pressure * ny * integral







	def solve(self, p_in, p_out):
		system, system_B = self.prepare_slae_1()

		self.add_neumann_conditions(system_B, p_in, p_out)
		self.apply_boundary_conditions(system, system_B)

		solution_vector = np.linalg.solve(system, system_B)

		return Solution(self.task.mesh, solution_vector)





class Integrator:
	def integrate(self, triangle, function):

		p1, p2, p3 = triangle.vertices

		area = abs(triangle.determinant) / 2

		
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




	def integrate_edge(self, p1, p2, function):

		length = np.hypot(p2.x - p1.x, p2.y - p1.y)

		# точки Гаусса
		t1 = 0.5 - 1.0 / (2.0 * np.sqrt(3.0))
		t2 = 0.5 + 1.0 / (2.0 * np.sqrt(3.0))

		def value(t):
			x = p1.x + t * (p2.x - p1.x)
			y = p1.y + t * (p2.y - p1.y)
			return function(x, y)

		return length / 2.0 * (value(t1) + value(t2))















class Triangle:
	#next_id = 0

	def __init__(self, id, vertices):
		self.id = id
		#Triangle.next_id += 1
		self.vertices = vertices
		self.determinant = (vertices[1].x - vertices[0].x) * (vertices[2].y - vertices[0].y) - (vertices[2].x - vertices[0].x) * (vertices[1].y - vertices[0].y)

	def get_basis(self):
		self.thbasis = THBasis(self)


	def get_midpoints(self, setka: Mesh):
		self.edge_midpoints = tuple([])
		midpoints = []
		eps = 1e-9

		for i in range(3):
			p1 = self.vertices[i]
			p2 = self.vertices[(i + 1) % 3]

			# Порядок концов ребра не важен.
			edge = tuple(sorted((p1.id, p2.id)))

			if edge in setka.edge_midpoints:
				midpoint = setka.edge_midpoints[edge]
			else:
				mix = (p1.x + p2.x) / 2
				miy = (p1.y + p2.y) / 2

				is_boundary = setka.edge_counts[edge] == 1

				if is_boundary:
					is_inlet = (
						abs(p1.x - 1.0) < eps
						and abs(p2.x - 1.0) < eps
					)
					is_outlet = (
						abs(p1.x - 4.0) < eps
						and abs(p2.x - 4.0) < eps
					)

					if is_inlet or is_outlet:
						boundary_type = 1  # Нейман
					else:
						boundary_type = 0  # Дирихле
				else:
					boundary_type = None

				midpoint = Point(mix, miy, is_boundary, boundary_type)

				setka.points.append(midpoint)
				setka.middles.append(midpoint)
				setka.edge_midpoints[edge] = midpoint

			midpoints.append(midpoint)

		self.edge_midpoints = tuple(midpoints)



	def contains(self, point):
		p1, p2, p3 = self.vertices

		lambda1 = ((p2.x - point.x) * (p3.y - point.y) - (p3.x - point.x) * (p2.y - point.y)) / self.determinant
		lambda2 = ((p3.x - p1.x) * (point.y - p1.y) - (point.x - p1.x) * (p3.y - p1.y)) / self.determinant
		lambda3 = 1.0 - lambda1 - lambda2

		eps = 1e-10
		return (lambda1 >= -eps and lambda2 >= -eps and lambda3 >= -eps)


'''
# В треугольнике
vertcies = [(0,1),(1,0),(1,1)]

## Составляем оптиитзировапнно матрица кэффов
A = np.ndarray([3,3])
for i in range(3):
	for j in range(3):
		A[i,j] = vertcies[(i+1) % 3][j] * vertcies[(i+2) % 3][j+1] - vertcies[(i+2) % 3][j] * vertcies[(i+1) % 3][j+1]


		A[i,j] = vertcies[(i+1) % 3][j] * vertcies[(i+2) % 3][j+1] - vertcies[(i+2) % 3][j] * vertcies[(i+1) % 3][j+1]

		A[i,j] = vertcies[(i+1) % 3][1] - vertcies[(i+1) % 3][j]


0:  0 и 1 - 0 и 1
1: 1 и 1
2: 0 и 0
'''


class THBasis:
	def __init__(self, triangle : Triangle):
		self.triangle = triangle
		self.get_pressure_basis()
		self.get_speed_basis()

	def get_pressure_basis(self):
		temp = []
		p1, p2, p3 = self.triangle.vertices

		for i in range(3):
			a, b = self.triangle.vertices[(i+1) % 3], self.triangle.vertices[(i+2) % 3]

			c1 = (a.x * b.y - b.x * a.y) / self.triangle.determinant
			c2 = (a.y - b.y) / self.triangle.determinant
			c3 = (b.x - a.x) / self.triangle.determinant

			temp.append((c1,c2,c3))

		temp = np.array(temp)
		


		def pressure_functions(point):
			vector = [1,point.x,point.y]
			return np.dot(temp, vector)

		self.pressure_functions = pressure_functions




	def get_speed_basis(self):
		temp = np.zeros([6,6])
		points = self.triangle.vertices + self.triangle.edge_midpoints
		matrix = np.array([[1, p.x, p.y, p.x**2, p.x * p.y, p.y**2] for p in points], dtype=float)
		for i in range(6):
			
			values = np.zeros(6)
			values[i] = 1.0
			coeffs = np.linalg.solve(matrix, values)
			temp[i,:] = np.array(coeffs)

			
		
		def speed_functions(point):
			vector = [1,point.x,point.y, point.x * point.x,  point.x * point.y, point.y * point.y]
			return np.dot(temp, vector)

		self.speed_functions = speed_functions


		def speed_functions_gradient(point):
			T = np.array([[0,0], [1, 0], [0,1], [2 * point.x, 0], [point.y, point.x], [0,2 * point.y]])
			return temp @ T

		self.speed_functions_gradient = speed_functions_gradient



		



