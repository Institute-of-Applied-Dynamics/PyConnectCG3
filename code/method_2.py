import numpy as np
from scipy import optimize


def calc_s_rel(s, s_neutral):
	return s - s_neutral


######################################################################################################
# linear flexion and pure separation
######################################################################################################
def calc_g_lin(s1, s2, a1, a2):
	try:
		return (a2 - a1) / (s2 - s1)
	except ZeroDivisionError:
		print("ZeroDivisionError: incorrect measurement, sensor values are identical.")
		raise


def calc_theta(s, g):
	return s * g


######################################################################################################
# separation
######################################################################################################
# s, s_l and s_r are lists
def calc_c_sep(s, s_l, s_r, g):

	def separation_polynomial(x, c1, c2, c3, c4, c5):
		return g * x['m'] + c1 * x['l'] + c2 * x['r'] + c3 * (x['l']**2) + c4 * (x['r']**2) + c5 * x['l'] * x['r']

	# create one dict to hold all sensor values
	s_values = {'l': s_l, 'm': s, 'r': s_r}
	# create array of n zeros where n is the amount of datasets
	angles = np.zeros(len(s))
	# perform curve_fit (minimization with Levenberg-Marquardt)
	c_factors, _ = optimize.curve_fit(separation_polynomial, s_values, angles)
	return c_factors


def calc_phi(s, s_l, s_r, g, c1, c2, c3, c4, c5):
	return g * s + c1 * s_l + c2 * s_r + c3 * s_l**2 + c4 * s_r**2 + c5 * s_l * s_r


######################################################################################################
# thumb CMC
######################################################################################################
# s and s_adj are lists
def calc_c_thumb(s, s_adj):

	def thumb_polynomial(s, adj_f):
		return s['self'] + adj_f * s['adj_sensor']

	# create dict to hold the sensor values
	s_values = {'self': s, 'adj_sensor': s_adj}
	# create array of n zeros where n is the amount of datasets
	angles = np.zeros(len(s_values['self']))
	# perform curve_fit (minimization with Levenberg-Marquardt)
	res, _ = optimize.curve_fit(thumb_polynomial, s_values, angles)
	return res


def calc_psi(s, s_adj, g, c):
	return g * (s + c * s_adj)


######################################################################################################
# thumb closed loop
######################################################################################################
# s is a list
def calc_g_closed_loop(s):
	def calc_distance(s, g_f, g_a):
		# this function depends on the way the distance is meant to be calculated
		# different hand models, software and calculations can be used to obtain the distance between
		# the thumb's and the index finger's fingertips, here dummy with random output
		# !!! curve_fit() may throw the warning 'Covariance of the parameters could not be estimated' !!!
		import random
		distance = random.randint(0, 2)
		return distance

	# create array of n zeros where n is the amount of datasets captured over time
	# (this is the optimal distance to be optimized to)
	distances = np.zeros(len(s[0]))

	# perform curve_fit (minimization with Levenberg-Marquardt)
	res, _ = optimize.curve_fit(calc_distance, s, distances)
	# output list containing the calculated gain for CMC_roll and for CMC_abduction
	return res


######################################################################################################
# usage example
######################################################################################################

# flexion (linear)
relative_sensor_value_lin = calc_s_rel(s=176, s_neutral=78) 	# convert sensor value from measurement
g = calc_g_lin(s1=37, s2=135, a1=0, a2=35)						# calculate gain from calibration measurements
alpha = calc_theta(relative_sensor_value_lin, g)				# convert relative sensor value into angle
print(alpha)

# separation (cross talk)
g_separation = calc_g_lin(s1=34, s2=189, a1=0, a2=17)			# calculate gain from calibration measurement
s = np.array([62, 63, 66, 68, 69, 70, 72, 73])					# recorded data of separation sensor
s_l = np.array([28, 29, 32, 27, 28, 29, 31, 28])				# recorded data of left neighbored flexion sensor
s_r = np.array([14, 16, 18, 14, 15, 17, 13, 16])				# recorded data of right neighbors flexion sensor
c = calc_c_sep(s, s_l, s_r, g_separation)						# calculate C_abd / C_flex to adjust cross-talk influence
# calculate the separation angle of one measurement:
phi = calc_phi(s=82, s_l=34, s_r=24, g=g_separation, c1=c[0], c2=c[1], c3=c[2], c4=c[3], c5=c[4])
print(phi)

# thumb CMC (cross talk) [both applicable for roll and abduction, here shown for abduction)
g_thumb = calc_g_lin(s1=34, s2=127, a1=0, a2=60)				# calculate gain from calibration measurements
s = np.array([62, 63, 66, 68, 69, 70, 72, 73])					# recorded data of the CMC abduction sensor
s_other_sensor = np.array([14, 16, 18, 14, 15, 17, 13, 16])		# recorded data of the roll sensor
c = calc_c_thumb(s, s_other_sensor)								# calculate the correction factor of roll influencing abduction
																# angle calculation not yet possible
# thumb closed-loop
s0 = np.array([34, 37, 39, 38, 41])								# recorded data of roll CMC sensor
s1 = np.array([28, 24, 26, 27, 29])								# recorded data of thumb MCP sensor
s2 = np.array([78, 75, 74, 79, 80])								# recorded data of thumb PIP sensor
s3 = np.array([53, 59, 63, 52, 55])								# recorded data of abduction CMC sensor
s4 = np.array([22, 22, 23, 26, 31])								# recorded data of index finger MCP
s5 = np.array([123, 124, 119, 118, 126])						# recorded data of index finger PIP
s6 = 0.87 * s5 - 25.27											# calculated data of index finger DIP
s10 = np.array([12, 17, 24, 16, 27])							# recorded data of abduction MCP_2_3
s = np.array([s0, s1, s2, s3, s4, s5, s6, s10])					# pack all recorded sensor values
g_CMC_abd, g_CMC_roll = calc_g_closed_loop(s)					# calculate CMC gains with closed-loop distance minimization

psi = calc_psi(24, 13, g_thumb, c)								# convert two relative CMC sensor values into abduction angle
print(psi)
