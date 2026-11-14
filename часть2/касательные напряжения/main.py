import numpy as np
from generator import load_boundary
from classes import BoundaryGenerator, Point, Triangulator, Triangle,  Mesh, Task, Integrator, FEMSolver
import matplotlib.pyplot as plt
import plot






a = np.ones([6,6])
b = np.ones([1,2])
c = np.outer(a,b)

def mu(x, y):
	return 1.0 + 0.1 * y

def force(x, y):
	return 0, np.sin(x)

def boundary_velocity(x, y):
	if y > 1.98:
		return 0.0, 0.0
	else:
		x_center = 2.5
		a = 1.5
		b = 1.0 
		tx = y / b**2
		ty = -(x - x_center) / a**2
		length = np.sqrt(tx**2 + ty**2)
		return tx / length * 0.1, ty / length * 0.15 + 0.02



def adaptate_for_class(func):
	def f(point: Point):
		return func(point.x, point.y)
	return f



triangulator = Triangulator()
mesh = triangulator.get_mesh(BoundaryGenerator())

d1 = []
n1 = []
for point in mesh.points:
	if point.isBoundary:
		if point.boundary_type == 0:
			d1.append((point.x, point.y))
		else:
			n1.append((point.x, point.y))

d1 = np.array(d1)
n1 = np.array(n1)



xd1, yd1 = d1[:,0], d1[:,1]
xn1, yn1 = n1[:,0], n1[:,1]







mesh.add_triangles_midpoints()

d2 = []
n2 = []

for point in mesh.middles:
	if point.isBoundary:
		if point.boundary_type == 0:
			d2.append((point.x, point.y))
		else:
			n2.append((point.x, point.y))




d2 = np.array(d2)
n2 = np.array(n2)


xd2, yd2 = d2[:,0], d2[:,1]
xn2, yn2 = n2[:,0], n2[:,1]









mesh.make_basises()



task = Task(
	mesh,
	adaptate_for_class(boundary_velocity),
	mu=mu,
	force=force
)
integrator = Integrator()
solver = FEMSolver(task, integrator)

solution = solver.solve(p_in=2, p_out=0.0)





plot.plot_solution(solution)

'''
plt.scatter(xd1,yd1,color="blue")
plt.scatter(xn1,yn1,color="red")
plt.scatter(xd2,yd2,color="green")
plt.scatter(xn2,yn2,color="yellow")
'''
plt.show()



