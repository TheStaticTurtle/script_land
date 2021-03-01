import digitalio

def enum(**enums):
    return type('Enum', (), enums)

Port = enum(P0=0b00, P1=0b01)
Resolution = enum(BIT_7=127, BIT_8=255)
Wiper = enum(Rheostat=0, Potentiometer=1)

ADDRESS_MASK   = 0B11110000
COMMAND_MASK   = 0B00001100
CMDERR_MASK    = 0B00000010
DATA_MASK      = 0B00000001
DATA_MASK_WORD = 0x01FF

TCON_SHUTDOWN_MASK   = 0B1000
TCON_TERMINAL_A_MASK = 0B0100
TCON_TERMINAL_B_MASK = 0B0001
TCON_WIPER_MASK      = 0B0010

ADDRESS_POT0_WIPER   = 0B0000
ADDRESS_POT1_WIPER   = 0B0001
ADDRESS_TCON         = 0B0100
ADDRESS_STATUS       = 0B0101

COMMAND_WRITE     = 0B00
COMMAND_READ      = 0B11
COMMAND_INCREMENT = 0B01
COMMAND_DECREMENT = 0B10

STATUS_SHUTDOWN_MASK = 0B10

class MCP4XXX(object):
	"""docstring for MCP4XXX"""
	def __init__(self, spi, cs=None, resolution=Resolution.BIT_8, wiper=Wiper.Potentiometer):
		super(MCP4XXX, self).__init__()
		self.spi = spi
		self.pin_chipselect = None

		self.wiper = wiper
		self.resolution = resolution

		self.pin_cs = digitalio.DigitalInOut(cs)
		self.pin_cs.direction = digitalio.Direction.OUTPUT
		self.pin_cs.value = True
	
	@property
	def max_value(self):
		return self.resolution + self.wiper
	
	def _select(self):
		while not self.spi.try_lock():
			pass
		self.spi.configure(baudrate=5000000, polarity=0, phase=0, bits=8)
		self.pin_cs.value = False

	def _deselect(self):
		self.pin_cs.value = True
		self.spi.unlock()

	def destroy(self):
		self.pin_cs.deinit()
		self.spi.unlock()

	def _build_command(self, address, command, data=None):
		data_bytes = [ ((address << 4) & ADDRESS_MASK) | ((command << 2) & COMMAND_MASK) | CMDERR_MASK ]
		if data != None:
			data_bytes.append((data & DATA_MASK_WORD) & 0xFF)
		return data_bytes

	def _transfer(self, address, command, data=None):
		byts = self._build_command(address, command, data=data)
		rbuf = bytearray(len(byts))
		self._select()
		self.spi.write_readinto(bytes(byts),rbuf)
		self._deselect()
		return list(rbuf)

	def increment(self, port=Port.P0):
		self._transfer(port, COMMAND_INCREMENT)

	def decrement(self, port=Port.P0):
		self._transfer(port, COMMAND_DECREMENT)

	def set(self, value, port=Port.P0):
		self._transfer(port, COMMAND_WRITE, data=int(min(value, self.max_value)))

	def get(self, port=Port.P0):
		return self._transfer(port, COMMAND_READ, data=DATA_MASK_WORD)[1]

	def _set_tcon(self, mask, value, port=Port.P0):
		if(port == Port.P1): # The values for pot #1 are 4 bits higher in the TCON register.
			mask <<= 4

		tcon = self._get_tcon()
		if value:
			self._transfer(ADDRESS_TCON, COMMAND_WRITE, data=tcon | mask)
		else:
			self._transfer(ADDRESS_TCON, COMMAND_WRITE, data=tcon & (~mask & 0xFF))

	def _get_tcon(self, mask=None, port=Port.P0):
		tcon_byte = self._transfer(ADDRESS_TCON, COMMAND_READ, data=DATA_MASK_WORD)[1]
		if mask==None:
			return tcon_byte
		else:
			if(port == Port.P1): # The values for pot #1 are 4 bits higher in the TCON register.
				mask <<= 4;
			return tcon_byte & mask

	@property
	def hardware_shutdown_status(self):
		return bool(self._transfer(ADDRESS_STATUS, COMMAND_READ, data=DATA_MASK_WORD)[1] & STATUS_SHUTDOWN_MASK)

	def get_shutdown(self, port=Port.P0):
		return not self._get_tcon(mask=TCON_SHUTDOWN_MASK, port=port)

	def set_shutdown(self, shutdown, port=Port.P0):
		self._set_tcon(TCON_SHUTDOWN_MASK, not shutdown, port=port)

	def get_wiper_connected(self, port=Port.P0):
		return bool(self._get_tcon(mask=TCON_WIPER_MASK, port=port))

	def set_wiper_connected(self, connected, port=Port.P0):
		self._set_tcon(TCON_WIPER_MASK, connected, port=port)

	def get_A_connected(self, port=Port.P0):
		return bool(self._get_tcon(mask=TCON_TERMINAL_A_MASK, port=port))

	def set_A_connected(self, connected, port=Port.P0):
		self._set_tcon(TCON_TERMINAL_A_MASK, connected, port=port)

	def get_B_connected(self, port=Port.P0):
		return bool(self._get_tcon(mask=TCON_TERMINAL_B_MASK, port=port))

	def set_B_connected(self, connected, port=Port.P0):
		self._set_tcon(TCON_TERMINAL_B_MASK, connected, port=port)

if __name__ == '__main__':
	print("Tested on a raspberry pico. Check the pins")
	import board
	import busio
	spi = busio.SPI(clock=board.GP2, MOSI=board.GP3, MISO=board.GP4)
	res = MCP4XXX(spi,cs=board.GP5)

	print("Hardware shutdown status:\t",res.hardware_shutdown_status)
	print("Shutdown status:\t\t",res.get_shutdown(port=Port.P0),"\t",res.get_shutdown(port=Port.P1))
	print("Wiper connected:\t\t",res.get_wiper_connected(port=Port.P0),"\t",res.get_wiper_connected(port=Port.P1))
	print("A connected:\t\t\t",res.get_A_connected(port=Port.P0),"\t",res.get_A_connected(port=Port.P1))
	print("B connected:\t\t\t",res.get_B_connected(port=Port.P0),"\t",res.get_B_connected(port=Port.P1))
	print("Values:\t\t\t\t",res.get(port=Port.P0),"\t",res.get(port=Port.P1))