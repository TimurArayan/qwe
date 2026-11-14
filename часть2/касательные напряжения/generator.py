import numpy as np


def load_boundary():
	all = []

	for x in np.linspace(1,4,200):
		all.append({'x': x, 'y': 2, 'type': 'dirichle', 'space': 'stokes'})

	for x in np.array([1,4]):
		for y in np.linspace(1,2,300):
			all.append({'x': x, 'y': y, 'type': 'neuman', 'space': 'stokes'})


	for t in np.linspace(0,np.pi, 300):
		x = 2.5 + 1.5 * np.cos(t)
		y = np.sin(t)
		all.append({'x': x, 'y': y, 'type': 'interface', 'space': 'common'})


	for x in np.linspace(1,4,100):
		all.append({'x': x, 'y': 0, 'type': 'neuman', 'space': 'darcy'})


	import pandas
	df = pandas.DataFrame(all)
	df.to_csv('boundary.csv', index=False)




