from glove import Glove
import threading

gl = Glove()
# argument has to be chosen as the IP address of the computer
# we recommend to assign a static IP address to your computer
if not gl.connect_glove("192.168.1.2"):
	print("Error establishing a connection to the glove")
	exit(1)

#######################
# measure one dataset #
#######################
dataset_1 = gl.get_one_dataset()
print(dataset_1)

#############################################################################################
# measure 10 datasets continuously with the highest possible frequency                      #
#############################################################################################
values = []
for _ in range(10):
	dataset_2 = gl.get_one_dataset()
	values.append(dataset_2)
print(values)

############################################################################################################
# measure continuously with the highest possible frequency (save to output.txt) until enter key is pressed #
############################################################################################################
gl.write_continuous_datasets(file="output.txt")

#####################################################
# call other functions provided by the glove-module #
#####################################################
print("Is righthanded glove: ", gl.get_righthanded())
print("Glove information: ", gl.get_glove_information())
# more ...
