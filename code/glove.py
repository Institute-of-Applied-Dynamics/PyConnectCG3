"""
This module implements the class `Glove` for intercommunication with CyberGlove III.
"""

import sys
import socket
import threading
import struct
from netifaces import interfaces, ifaddresses, AF_INET


class Glove:
	"""
	The class :class:`Glove<cyberglove.glove.Glove>` implements functionality to connect to the CyberGlove III\
	hardware, to send commands and to receive data.
	"""
	def __init__(self):
		self.client_socket = None

	def connect_glove(self, ip_address_pc, localport=49500):
		"""
		Connect the CyberGlove III by creating a socket and listen on the given port.
		Both the static IP address of the computer and the port must be given to the CyberGlove by writing the \
		information onto the flash card that is inserted into the glove's microcontroller.\
		This method waits until a client connects.
		It then returns True.
		Args:
			ip_address_pc (str):	IP address of the computer to verify (e.g. "192.168.1.2")
			localport (int):		port to open (defaults to 49500)
		Returns:
			bool:	True if glove has connected successfully
		"""
		# 1. check if ip_address_pc is actually an IP address of the computer that is used
		ips = []													# list holding IP addresses of the computer
		for ifaceName in interfaces():
			addresses = [i['addr'] for i in ifaddresses(ifaceName).setdefault(AF_INET, [{'addr': 'No IP addr'}])]
			# fill ips[] with all IP addresses of the computer in all networks
			ips.append(''.join(addresses))
		if ip_address_pc not in ips:
			print("Your glove can not be connected.")
			print(f"Make sure you are connected with the network and check if your IP-address is {ip_address_pc}.")
			return False
		# 2. create socket and listen for incoming connections
		srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)		# IPv4, TCP
		srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)  	# reuse the socket when it is closed
		srv.bind(('', localport))									# make sure the socket is reachable by any address
		srv.listen(1)												# queue only 1 connect request before refusing connections
		# check twice a second if CTRL-C was pressed and handle the exception
		srv.settimeout(0.1)											# (Windows only issue: see https://stackoverflow.com/a/61539628)
		print(f"Waiting for connection on port {localport}...")
		print("Please switch on your CyberGlove\n")
		try:
			while True:												# when socket times out, repeat accepting incoming connections
				try:
					# accept incoming requests, save address of client to addr, and the socket connection to self.client_socket
					self.client_socket, addr = srv.accept()
					print(f"Connected by {addr}!")
					self.client_socket.settimeout(None)				# remove timeout from socket
					break
				except socket.timeout:								# repeat in while-loop when socket times out
					pass
		except KeyboardInterrupt:
			# when user aborts, close the socket and return False
			if self.client_socket is not None:
				self.client_socket.close()
			sys.stderr.write("Server closed with KeyboardInterrupt!\n")
			return False
		first_msg = self.client_socket.recv(1024)
		if first_msg != b'o':										# verify if the glove sent the connection confirmation message >>b'o'
			self.client_socket.close()
			self.client_socket = None
			print("Glove did not respond correctly when a connection was established")
			print("Try restarting the data glove.")
			return False
		return True

	def disconnect_glove(self):
		"""
		Closes the socket in use and with it the connection to the CyberGlove III.

		Returns:
			None
		"""
		if self.client_socket is not None:
			self.client_socket.close() 		# close the socket, when it's existent
			self.client_socket = None		# set it to None
		else:
			sys.stderr.write("Glove was already disconnected.\n")
		return

	def _send_receive_raw(self, command: str):
		"""
		Sends the given command to the glove and returns the answer

		Args:
			command (string):	command to send to the glove
		Returns:
			array:			answer as byte-array
		"""
		try:
			self.client_socket.send(bytes(command, 'ascii'))	# send the command as ascii-encoded byte-array
			data = self.client_socket.recv(1024)				# receive answer (undefined length, end of message indicated by null-byte)
			if not data:
				sys.stderr.write("error when receiving data\n")
				raise Exception
			return data
		except socket.error as msg:								# probably got disconnected
			sys.stderr.write(f"ERROR: {msg}\n")
		except KeyboardInterrupt:
			sys.stderr.write("Stopped by KeyboardInterrupt")

	def _send_receive(self, command: str):
		"""
		Sends the given command to the glove, reads the answer and cuts off unnecessary bytes
		(repeated command-bytes and last terminating null-byte)

		Args:
			command (string):	command to send to the glove
		Returns:
			array:				sanitized byte-array of answer
		"""
		data = self._send_receive_raw(command)
		return data[len(command):-1]									# cut-off repeated command-bytes and terminating null-byte

	def get_one_dataset(self):
		"""
		Requests exactly one 8-bit dataset from the CyberGlove III.
		Sends command 'G', handles errors (e.g. incomplete datasets) and returns the dataset as list.

		Returns:
			list:	array consisting of 22 values between 1 and 255
		Raises:
			socket.error:	socket-error
		"""
		try:
			# check if socket exists (glove is connected)
			if self.client_socket is None:
				sys.stderr.write("Error: No glove connected\n")
				return False
			# send the command 'G' to the glove as ascii-encoded byte-array to request one 8-bit dataset
			self.client_socket.send(bytes('G', 'ascii'))
			msg = self.client_socket.recv(1)				# the glove will only return b'G' (repetition of the command)
			msg += self.client_socket.recv(23)				# data is sent afterwards (22 sensor values + terminating null-byte)
			# unpack the byte values by interpreting them as unsigned chars, save them as integer values into an array
			raw_data = struct.unpack('@' + "B" * len(msg), msg)
			# check if raw_data is valid (command at the beginning (char G = 71), length == 24 values)
			#  and the last one is a terminating null-byte
			if raw_data[0] != 71 or len(raw_data) != 24 or raw_data[23] != 0:
				self.client_socket.recv(1024)				# flush the socket, get all the messages and loose them
				return self.get_one_dataset()				# call the method itself recursively
			return raw_data[1:-1]							# cut the command at the beginning and the terminating null-byte
		except socket.error as msg:							# catch socket-errors, like disconnected glove and more...
			sys.stderr.write('ERROR: {}\n'.format(msg))
			raise

	def _thread_read_data(self, stop_event, fp):
		"""
		Helper function to read data from the glove and write it to a file.
		Executed in a thread.

		Args:
			stop_event (_type_): Event to stop the thread
			fp (_type_): File pointer to the file to write the data to
		"""
		while not stop_event.is_set():
			data = self.get_one_dataset()
			fp.write(str(data) + "\n")

	def write_continuous_datasets(self, file: str):
		"""
		Continuously requests single datasets from glove and writes them to the given file.
		Uses a thread to read and write the data and an input to stop the thread.
		
		Args:
			file (str): Path to file where the data should be written to
		"""
		with open(file, "w") as fp:
			pill2kill = threading.Event()
			thread = threading.Thread(target=self._thread_read_data, args=(pill2kill, fp))
			input(f"Please press enter to start.")
			thread.start()
			input("Please press enter to stop the measurement.")
			pill2kill.set()
			thread.join()
			pill2kill.clear()

	def get_glove_information(self):
		"""
		Gets information-text from the CyberGlove-microcontroller.
		Sends command '?i' and returns the decoded answer.

		Returns:
			str:	decoded answer
		"""
		return self._send_receive('?i').decode()						# decoding byte-array to string-representation

	def get_amount_of_sensors(self):
		"""
		Gets the amount of sensors the connected glove.
		Sends command '?S' and returns the answer.

		Returns:
			int:	either 18 or 22
		"""
		return ord(self._send_receive('?S'))							# ord() to get int from byte-character

	def get_status(self):
		"""
		Queries the current status of the CyberGlove.
		Sends command '?G' and returns the corresponding answer.

		Returns:
			str:	status string
		"""
		result = ord(self._send_receive('?G'))							# ord() to get int from byte-character
		if result == 0:
			return "Cyberglove not plugged in and not initialized properly"
		elif result == 1:
			return "Cyberglove not plugged in but initialized properly"
		elif result == 2:
			return "Cyberglove plugged in but not initialized properly"
		elif result == 3:
			return "Cyberglove plugged in and initialized properly"
		else:
			return f"Error - unexpected answer: {result}"

	def get_righthanded(self):
		"""
		Returns True if the CyberGlove is tailored for a right hand.
		Sends command '?R' and returns the corresponding answer.

		Returns:
			bool:	True if the glove is right-handed
		"""
		return ord(self._send_receive('?R')) == 1						# ord() to get int from byte-character

	def get_version_number(self):
		"""
		Queries the version of the CyberGlove.
		Sends command '?V' and returns the sanitized answer.

		Returns:
			tuple:	(Glove-Firmware, internal information format version number)
		"""
		return struct.unpack("!" + "H" * 2, self._send_receive('?V'))

	def start_prompt(self):
		"""
		Starts a command prompt to enter commands and receive answers.
		Use 'exit' to exit the prompt.

		Returns:
			None
		"""
		print("Starting command prompt. To exit, just type 'exit'.")
		try:
			while True:
				command = input('>> ')
				if command == 'exit':
					return
				print(self._send_receive_raw(command))
		except KeyboardInterrupt:
			print("Stopped prompt by KeyboardInterrupt")
			return
