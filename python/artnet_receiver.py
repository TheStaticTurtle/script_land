import socket
from threading import Thread
import time
import sys
import time
import struct


class ArtnetPacket:
	ARTNET_HEADER = b'Art-Net\x00'
	OP_OUTPUT = 0x0050

	def __init__(self):
		self.op_code = None
		self.ver = None
		self.sequence = None
		self.physical = None
		self.universe = None
		self.length = None
		self.data = None
		self.dmx = None

	def __str__(self):
		return "<ArtnetPacket Sequence:"+str(self.sequence)+" Physical:"+str(self.physical)+" Universe:"+str(self.universe)+" Length:"+str(self.length)+" Dmx:"+str(self.dmx)+">"

	def __repr__(self):
		return str(self)

	@staticmethod
	def unpack_raw_artnet_packet(raw_data):

		if struct.unpack('!8s', raw_data[:8])[0] != ArtnetPacket.ARTNET_HEADER:
			return None

		packet = ArtnetPacket()

		# We can only handle data packets
		(packet.op_code,) = struct.unpack('!H', raw_data[8:10])
		if packet.op_code != ArtnetPacket.OP_OUTPUT:
			return None

		(packet.op_code, packet.ver, packet.sequence, packet.physical, packet.universe, packet.length) = struct.unpack('!HHBBHH', raw_data[8:18])
		(packet.universe,) = struct.unpack('<H', raw_data[14:16])
		(packet.data,) = struct.unpack('{0}s'.format(int(packet.length)), raw_data[18:18 + int(packet.length)])

		packet.dmx = [int(str(b)) for b in packet.data]

		return packet


class Receiver(Thread):
	def __init__(self):
		Thread.__init__(self)
		UDP_IP = "127.0.0.1"
		UDP_PORT = 0x1936

		self.running = True
		self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
		self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
		self.sock.bind((UDP_IP, UDP_PORT))
		self.callback = None

	def stop(self):
		self.running = False

	def run(self):
		while self.running:
			data, addr = self.sock.recvfrom(1024)
			packet = ArtnetPacket.unpack_raw_artnet_packet(data)
			if packet is not None:
				if self.callback is not None:
					self.callback(packet)
