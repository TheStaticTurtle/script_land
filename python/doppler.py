#!/usr/bin/python3
import math
import socket
import ephem
import time
import sys
import ssl
import zmq
import pmt
import requests

C = 300000000.0
F0 = 137.1e6

class tle_reader(object):
    """
    For keeping ephem two line element sets up to date
    """
    def __init__(self,
                 tle_name="NOAA 19 [+]",
                 tle_file="https://celestrak.com/NORAD/elements/noaa.txt",
                 tle_max_age=3600):
        self._tle_name = tle_name
        self._tle_file = tle_file
        self._tle_max_age = tle_max_age
        self._tle = None
        self.reload()

    def build_index(self, tle_lines):
        index = {}
        for i in range(0, len(tle_lines), 3):
            index[tle_lines[i].strip()] = (tle_lines[i + 1], tle_lines[i + 2])
        return index

    def reload(self):
        print("Loading: %s" % self._tle_file)

        try:
            tle_lines = requests.get(self._tle_file).text.splitlines()
            # with urllib.request.urlopen(self._tle_file, context=ctx) as response:
            #     tle_lines = response.read().decode("utf-8").splitlines()

            index = self.build_index(tle_lines)
            tle_data = index[self._tle_name]
            self._tle = ephem.readtle(self._tle_name, tle_data[0], tle_data[1])
        except Exception as e:
            print(e)

        self._tle_age = time.time()

    @property
    def tle(self):
        return self._tle

    @property
    def tle_expired(self):
        return time.time() - self._tle_age > self._tle_max_age


class remote(object):
    """
    For remote control of rtl_fm command line program
    """
    def __init__(self,host="tcp://*:5556"):
        self._host = host
        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.PUSH)
        self.socket.bind("tcp://*:5556")
        self.slave = "RTL-SDR_1"

    def set_freq(self, freq):
        # freq = 106.8e6
        print(self.slave+":frequency:"+str(freq))
        self.socket.send (pmt.serialize_str(pmt.to_pmt(self.slave+":frequency:"+str(freq))))

    def __del__(self):
        self.socket.close()
        self.context.term()


rtl = remote()
noaa = tle_reader(tle_name="NOAA 19 [+]", tle_max_age=5520)  # 92 minutes

if noaa.tle is None:
    sys.exit(0)

myloc = ephem.Observer()
dpr = 180.0 / math.pi
myloc.lon = 7.395691 / dpr
myloc.lat = 47.967760 / dpr
myloc.elevation = 200

running = True

try:
    while running:
        time.sleep(1)
        myloc.date = time.strftime('%Y/%m/%d %H:%M:%S', time.gmtime())

        noaa.tle.compute(myloc)
        alt = math.degrees(noaa.tle.alt)

        # if alt > 0:  # iss is flying over our location

        new_freq = int(F0 - noaa.tle.range_velocity * F0 / C)  # doppler
        print( new_freq, round(alt, 2), myloc.date)
        rtl.set_freq(new_freq)  # set new frequency in rtl_fm

        # elif noaa.tle_expired:
            # noaa.reload()  # we could be running for days / weeks
        # else:
            # print(alt)
            # time.sleep(1)  # do nothing, wait for noaa to arrive
except KeyboardInterrupt:
    running = False

print("Bye")
