

######################################################################################################
# affine flexion
######################################################################################################
def calibrate(s1, s2, a1, a2):
	try:
		gain = (a2 - a1) / (s2 - s1)
	except ZeroDivisionError:
		raise
	offset = a1 - (gain * s1)
	return gain, offset


def calc_alpha(s, gain, offset):
	return s * gain + offset


######################################################################################################
# example with fictional measurement data
######################################################################################################
g, o = calibrate(s1=37, s2=135, a1=0, a2=35) 					# calculate gain and offset from calibration measurements
s = 98															# obtained sensor value from measurement
alpha = calc_alpha(s, g, o)										# convert sensor value into angle
print(alpha)