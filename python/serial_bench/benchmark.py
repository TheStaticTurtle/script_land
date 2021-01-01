import serial
import time
PORT = "COM6"
SPEED = 2500000
SPEED = 115200
SPEED = 57600 
SPEED = 38400 
# SPEED = 19200
#SPEED = 9600

buf = []
t = time.time()

with serial.Serial(PORT, SPEED, timeout=0) as ser:
    while True:
        x = ser.read()
        if x:
            buf.append(x)
        if time.time() > t + 0.5:
            print("Rx at " + str(len(buf)*2) + " bytes/sec")
            t = time.time()
            buf = []