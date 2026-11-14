import numpy as np
from classes import BoundaryGenerator, Point, Triangulator, Triangle,  Mesh, Task, Integrator, FEMSolver


def force(x, y):
	return 6 * np.sin(np.pi * y), x**2

def boundary_velocity(x, y):
	return y**0.2,0
	'''
	if x - 1 < 0.01:
		return 2, np.cos(y) ** 2
	elif 4 - x < 0.01:
		return -1.2, -np.sin(y)  
	elif 2 - y < 0.01:
		return np.abs(np.sin(x)), -0.1
	else:
		return -0.2, 0
	'''


def adaptate_for_class(func):
	def f(point: Point):
		return func(point.x, point.y)

	return f


boundaryGenerator = BoundaryGenerator()
boundary = boundaryGenerator.generate_boundary()

triangulator = Triangulator()
mesh = triangulator.get_mesh(boundary)
mesh.add_triangles_midpoints()
mesh.make_basises()

task = Task(
	mesh,
	adaptate_for_class(boundary_velocity),
	nu=1.0,
	force=force
)
integrator = Integrator()
solver = FEMSolver(task, integrator)

solution = solver.solve()




def plot_solution(solution):
	import matplotlib.pyplot as plt
	import matplotlib.tri as mtri

	mesh = solution.mesh

	# Координаты всех узлов скорости.
	x = np.array([point.x for point in mesh.points])
	y = np.array([point.y for point in mesh.points])

	# Индекс точки в массиве координат для matplotlib.
	point_index = {
		point: i for i, point in enumerate(mesh.points)
	}

	triangles = []
	fine_triangles = []

	for triangle in mesh.triangles:
		a, b, c = [
			point_index[point]
			for point in triangle.vertices
		]

		ab, bc, ca = [
			point_index[point]
			for point in triangle.edge_midpoints
		]

		triangles.append([a, b, c])

		# Разбиение для отображения скорости.
		fine_triangles.extend([
			[a, ab, ca],
			[ab, b, bc],
			[ca, bc, c],
			[ab, bc, ca],
		])

	coarse_mesh = mtri.Triangulation(x, y, triangles)
	fine_mesh = mtri.Triangulation(x, y, fine_triangles)

	# Значения в том же порядке, что и mesh.points.
	vx = np.array([solution.speed_x[point.id] for point in mesh.points])
	vy = np.array([solution.speed_y[point.id] for point in mesh.points])
	speed = np.sqrt(vx**2 + vy**2)

	# Давление задано только в вершинах.
	vertices = list(dict.fromkeys(
		point
		for triangle in mesh.triangles
		for point in triangle.vertices
	))

	vertex_index = {
		point: i for i, point in enumerate(vertices)
	}

	pressure_triangles = [
		[vertex_index[point] for point in triangle.vertices]
		for triangle in mesh.triangles
	]

	pressure_mesh = mtri.Triangulation(
		[point.x for point in vertices],
		[point.y for point in vertices],
		pressure_triangles
	)

	pressure = np.array([
		solution.pressure[point.id]
		for point in vertices
	])

	fig, axes = plt.subplots(1, 3, figsize=(15, 4))

	# 1. Сетка.
	axes[0].triplot(coarse_mesh, color="steelblue", linewidth=0.5)
	axes[0].set_title("Сетка")

	# 2. Модуль скорости.
	speed_plot = axes[1].tripcolor(
		fine_mesh, speed, shading="gouraud", cmap="viridis"
	)
	fig.colorbar(speed_plot, ax=axes[1], label="|v|")
	axes[1].set_title("Модуль скорости")

	# Показываем стрелки не во всех узлах, чтобы они не сливались.
	step = 5

	axes[1].quiver(
		x[::step],
		y[::step],
		vx[::step],
		vy[::step],
		color="white",
		pivot="mid",
		scale=None
	)

	# 3. Давление.
	pressure_plot = axes[2].tripcolor(
		pressure_mesh, pressure, shading="gouraud", cmap="coolwarm"
	)
	fig.colorbar(pressure_plot, ax=axes[2], label="p")
	axes[2].set_title("Давление")

	for ax in axes:
		ax.set_aspect("equal")
		ax.set_xlabel("x")
		ax.set_ylabel("y")

	fig.tight_layout()
	plt.show()



plot_solution(solution)




