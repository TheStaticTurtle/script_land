import socket
import logging


class SDRSharp:
	def __init__(self, host, port=4532, max_retry=5):
		self.host = host
		self.port = port
		self.max_retry = max_retry
		self.socket = None
		if self.connect():
			logging.info("Connected to %s:%s" % (self.host, self.port))

	def connect(self, _trynumber=0):
		logging.info("Trying to connect to %s:%s" % (self.host, self.port))
		try:
			self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
			self.socket.connect((self.host, self.port))
			return True
		except Exception as e:
			logging.info("Failed to connect to %s:%s (try %s): %s" % (self.host, self.port, _trynumber + 1, str(e)))
			if _trynumber < self.max_retry + 1:
				return self.connect(_trynumber=_trynumber)
			return False

	def setFrequency(self, frequency: int):
		try:
			self.socket.send(bytes("F " + str(int(frequency)), "utf-8"))
		except Exception as e:
			logging.info("Failed to set frequency %s" % (str(e)))
			if self.connect():
				logging.info("Reconnected to %s:%s" % (self.host, self.port))


if __name__ == "__main__":
	sdr = SDRSharp("192.168.1.88")
	sdr.setFrequency(101.1e6)
