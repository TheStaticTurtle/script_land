import socket
from threading import Thread
import time


class Chat(Thread):
	def __init__(self, channel_id="thestaticturtle", oauth="none", username="TestBot"):
		Thread.__init__(self)
		self._channel_id = channel_id
		self._username = username
		self._oauth = oauth
		self._ircsock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		self.is_connected = False
		self.handler = None
		self.running = True

	def _send_stuff(self, data):
		print("< " + data)
		self._ircsock.send(bytes(data + "\n", "UTF-8"))

	def _join(self):
		self._send_stuff("JOIN #" + self._channel_id)

	def _handle_line(self, data):
		print("> " + data)

		if ":tmi.twitch.tv 376 "+self._username in data:
			self._join()

		if "PING :tmi.twitch.tv" in data:
			self._send_stuff("PONG :tmi.twitch.tv")

		if ":"+self._username+".tmi.twitch.tv 366 "+self._username+" #"+self._channel_id+" :End of /NAMES list" in data:
			self.is_connected = True

		if self.handler is not None and "PRIVMSG #"+self._channel_id+ " :" in data:
			self.handler(data.split("PRIVMSG #"+self._channel_id+ " :")[1])

	def send_text(self, text):
		self._send_stuff("PRIVMSG #" + self._channel_id + " :" + text[0:450])

	def stop(self):
		self.running = False

	def run(self):
		self._ircsock.connect(("irc.chat.twitch.tv", 6667))
		self._send_stuff("PASS " + self._oauth)
		self._send_stuff("NICK " + self._username)

		msg = b''
		while self.running:
			msg += self._ircsock.recv(1)
			if msg[-1] == 10:
				self._handle_line(msg.decode("UTF-8")[:-1])
				msg = b''
