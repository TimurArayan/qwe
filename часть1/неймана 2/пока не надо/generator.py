import numpy as np





def get_square():
	
	x_bordes = [1,4]
	y_borders = [0,2]
	borders = [x_bordes, y_borders]
	points_on_border = [300,200]

	points = []

	for border in borders:
		static_index = borders.index(border)
		dynamic_index = (static_index + 1) % 2

		for border_side_value in border:
			for i in range(points_on_border[dynamic_index]+1):
				c1 = border_side_value
				c2 = borders[dynamic_index][0] + (borders[dynamic_index][1] -  borders[dynamic_index][0]) * i / points_on_border[dynamic_index]
				p = [0,0]
				p[static_index] = c1
				p[dynamic_index] = c2
				p = np.array(p, dtype = np.float64)

				if static_index == 1 and border.index(border_side_value) == 0:
					continue

				points.append(p)

	points = np.array(points, dtype = np.float64)

	return points







import matplotlib.pyplot as plt





def get_ellips():
	x_values = []
	y_values = []

	'''
	(x - 2.5) ** 2 + y**2 * 1.5 ** 2 = 1.5**2
	'''

	for i in np.linspace(0,np.pi, 300):
		x_values.append(2.5 + 1.5 * np.cos(i))
		y_values.append(np.sin(i))

	return np.array(x_values, dtype=np.float64), np.array(y_values, dtype=np.float64)


if __name__ == "__main__":


	
	points1 = get_square()

	x_values1 = points1[:, 0]
	y_values1 = points1[:, 1]

	x_values2, y_values2 = get_ellips()

	x_values = np.concatenate([x_values1, x_values2])
	y_values = np.concatenate([y_values1, y_values2])

	plt.scatter(x_values, y_values, s=2)
	plt.axis('equal')
	plt.show()

	x_values.reshape(-1)
	y_values.reshape(-1)


	boundary = []

	for x, y in np.column_stack([x_values, y_values]):
		line = {'x': x, 'y': y}
		boundary.append(line)



	import pandas
	df = pandas.DataFrame(boundary)
	df.to_csv('boundary.csv', index=False)