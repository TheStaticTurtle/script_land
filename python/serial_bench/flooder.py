import serial

PORT = "COM9"
SPEED = 2500000
SPEED = 115200
SPEED = 57600 
SPEED = 38400 
# SPEED = 19200
# SPEED = 9600

with serial.Serial(PORT, SPEED, timeout=1) as ser:
	while True:
		ser.write(b'a' * 32)