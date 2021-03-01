import digitalio
import time
import sys

class M62429(object):
	"""docstring for MS62429"""
	def __init__(self, pin_data, pin_clock, speed=0.001):
		super(M62429, self).__init__()
		self.pin_data = digitalio.DigitalInOut(pin_data)
		self.pin_data.direction = digitalio.Direction.OUTPUT
		self.pin_clock = digitalio.DigitalInOut(pin_clock)
		self.pin_clock.direction = digitalio.Direction.OUTPUT
		self.speed = speed
	
	def deinit(self):
		self.pin_data.deinit()
		self.pin_clock.deinit()

	def setVolumeLeft(self, volume):
		self.setVolumeInternal(volume, channel=0, both=False)

	def setVolumeRight(self, volume):
		self.setVolumeInternal(volume, channel=1, both=False)

	def setVolume(self, volume):
		self.setVolumeInternal(volume, channel=0, both=True)

	def setVolumeInternal(self, volume, channel=0, both=False):
		volume = 0 if volume > 100 else (((volume * 83) // -100) + 83)
		data = 0
		data |= (1 << 0) if channel else (0 << 0)  # D0 (channel select: 0=ch1, 1=ch2)
		data |= (0 << 1) if both else (1 << 1)     # D1 (individual/both select: 0=both, 1=individual)
		data |= ((21 - (volume // 4)) << 2)         # D2...D6 (0...84 in steps of 4)
		data |= ((3 - (volume % 4)) << 7)          # D7 & D8 (0...3)
		data |= (0b11 << 9);                       # D9 and D10 must both be 1
		print(data)

		for bit in range(0,11):
			time.sleep(self.speed)
			self.pin_data.value = False
			time.sleep(self.speed)
			self.pin_clock.value = False
			time.sleep(self.speed)
			self.pin_data.value = 1 if ((data >> bit) & 0x01) else 0
			time.sleep(self.speed)
			self.pin_clock.value = True
		
		time.sleep(self.speed)
		self.pin_data.value = True
		time.sleep(self.speed)
		self.pin_clock.value = False