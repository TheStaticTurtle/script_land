import time


class SameDataLimiter():
	def __init__(self, wait_for_x_same_message=5):
		self.wait_for_x_same_message = wait_for_x_same_message
		self.data = None
		self.same_write_counter = 0

	def write(self, data):
		if data == self.data:
			self.same_write_counter += 1
		else:
			self.data = data
			self.same_write_counter = 0

	def read(self):
		if self.same_write_counter == 3:
			self.same_write_counter += 1
			return self.data
		return None


class RateLimiter():
	def __init__(self, message_per_seconds=2, discard_blocked_message=True):
		self.message_per_seconds = message_per_seconds
		self.discard_blocked_message = discard_blocked_message
		self._last_message = 0
		self._queue = []

		self._d = 1.0 / message_per_seconds

	def write(self, data):
		if self._last_message + self._d < time.time():
			if self.discard_blocked_message:
				self._queue = [data]
			else:
				self._queue.append(data)
		else:
			if not self.discard_blocked_message:
				self._queue.append(data)

	def read(self):
		return self._queue.pop()


class QueueRateLimiter():
	def __init__(self, message_per_seconds=2):
		self.message_per_seconds = message_per_seconds
		self._last_message = 0
		self._queue = []

		self._d = 1.0 / message_per_seconds

	def queueEverything(self, data):
		self._queue.append(data)

	def __iter__(self):
		return self

	def __next__(self):
		if len(self._queue) == 0:
			raise StopIteration
		if self._last_message + self._d < time.time():
			self._last_message = time.time()
			return self._queue.pop()
		return None
