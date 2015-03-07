COEFF_MATRIX = [
	[  1,  2,  3,  7, 17, 31, 53, 79],
	[  -2,  1,  5, 11, 19, 37, 59, 83],
	[  -3,  -5,  1, 13, 23, 41, 61, 89],
	[  -7, -11, -13,  1, 29, 43, 67, 97],
	[ -17, -19, -23, -29,  1, 47, 71,101],
	[ -31, -37, -41, -43, -47,  1, 73,103],
	[ -53, -59, -61, -67, -71, -73,  1,107],
	[ -79, -83, -89, -97,-101,-103,-107,  1],
]

def full_rank(matrix):
	matrix = [[x for x in y] for y in matrix]
	m = len(matrix)
	for i in range(m):
		for j in range(i):
			coeff = matrix[i][j]
			for k in range(m):
				matrix[i][k] -= coeff * matrix[j][k]
		coeff = matrix[i][i];
		if (coeff == 0):
			return False
		for k in range(m):
			matrix[i][k] /= coeff
	return True

n = len(COEFF_MATRIX)
import itertools
for k in range(2,n+1):
	for rows in itertools.combinations(range(n),k):
		for cols in itertools.combinations(range(n),k):
			matrix = [[x for x in range(k)] for y in range(k)]
			for ri, rd in enumerate(rows):
				for ci, cd in enumerate(cols):
					matrix[ri][ci] = COEFF_MATRIX[rd][cd]
			if (not full_rank(matrix)):
				print("Rank Check Failed:", matrix)
				input()
print("Done!")
