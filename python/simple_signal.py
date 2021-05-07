class Signal(object):
	def __init__(self):
		super(Signal, self).__init__()
		self.endpoints = []

	def connect(self, enpoint):
		self.endpoints.append(enpoint)

	def disconnect(self, endpoint):
		if endpoint in self.endpoints:
			self.endpoints.remove(endpoint)

	def emit(self):
		for enpoint in self.endpoints:
			enpoint()


if __name__ == '__main__':
	import time
	
	def staticprint(text):
		return lambda: print(text)
	
	sig = Signal()
	sig.connect(staticprint("SIGNAL"))

	while True:
		sig.emit()
		time.sleep(1)
