import numpy as np


######################################################################################################
# linear flexion and pure separation
######################################################################################################
# s and a are lists of 4 elements
def calc_g_and_o_lin(s, a):
	def _solve_direct_inverse(A, y):
		y = y[:, np.newaxis]  # turn y into a column vector
		return np.dot((np.dot(np.linalg.inv(np.dot(A.T, A)), A.T)), y)

	assert len(a) == len(s)
	regression_matrix = np.ones((len(s), 2))
	regression_matrix[:, 0] = a
	(a, b) = _solve_direct_inverse(regression_matrix, s)
	gain = 1.0 / a
	offset = - b / a
	return gain, offset


def calc_alpha(sensor_value, gain, offset):
	return sensor_value * gain + offset


######################################################################################################
# separation
######################################################################################################
# s, sl, sr and a are lists with six elements
def calc_sep(s,sl,sr,a, g_l, g_r, o_l, o_r):

	def _solve_direct_inverse(A, y):
		y = y[:, np.newaxis]  # turn y into a column vector
		return np.dot((np.dot(np.linalg.inv(np.dot(A.T, A)), A.T)), y)

	regression_matrix = np.empty((0, 4))
	for t in range(len(s)):
		flex_angle_l = calc_alpha(sl[t], g_l, o_l)
		flex_angle_r = calc_alpha(sr[t], g_r, o_r)
		flex_angle_diff = flex_angle_l - flex_angle_r
		line = np.array([[a[t], flex_angle_diff ** 2, flex_angle_diff, 1]])
		regression_matrix = np.append(regression_matrix, line, axis=0)

	(a, c1, c2, b) = _solve_direct_inverse(regression_matrix, s).flatten()
	gain = 1.0 / a
	correction2 = - c1 / a
	correction1 = - c2 / a
	offset = - b / a
	return gain, correction1, correction2, offset


def calc_phi(s, s_l, s_r, gain, correction1, correction2, offset):
	angle_diff = s_l - s_r
	return gain * s + correction1 * (angle_diff**2) + correction2 * angle_diff + offset


######################################################################################################
# usage example
######################################################################################################

# flexion (linear)
s = np.array([34, 44, 54, 64])									# create sample sensor data
a = np.array([10, 30, 50, 70])									# creating array holding the prescribed angles
g, o = calc_g_and_o_lin(s, a)									# calculate gain from calibration measurements
s = 64  														# obtained sensor value from measurement
alpha = calc_alpha(s, g, o)										# convert sensor value into angle
print(alpha)

# separation
g_l, g_r, o_l, o_r = 0.98, 1.28, -58.23, -47.64					# example values for neighbored MCP gains and offsets
s = np.array([55, 178, 68, 189, 89, 210])						# measured separation sensor values
s_l = np.array([34, 60, 28, 70, 38, 75])						# measured flexion sensor values left MCP
s_r = np.array([56, 89, 48, 93, 57, 97])						# measured flexion sensor values right MCP
a = np.array([0, 0, 20, 20, 30, 30])							# prescribed separation angles

g, c1, c2, o = calc_sep(s, s_l, s_r, a, g_l, g_r, o_l, o_r)		# determining gain, offset and neighboring correction factors
phi = calc_phi(55, 34, 56, g, c1, c2, o)						# convert sensor value into angle
print(phi)
