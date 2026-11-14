import numpy as np
from classes import BoundaryGenerator, Point, Triangulator, Triangle,  Mesh, Task, Integrator, FEMSolver


def force(x, y):
	return np.sin(np.pi * y), x**0.1

def boundary_velocity(x, y):
	return 0.7 * x ** 1.1, 2 * y ** 1.05


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
print(solution.size)




