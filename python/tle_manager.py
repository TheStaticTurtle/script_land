import datetime
import time
import requests
import ephem
import logging
import json
import sys
import math
import utils
logger = logging.getLogger(__name__)


class CustomSatellite:
	def __init__(self, name, noradId, ephemSat):
		super(CustomSatellite, self).__init__()
		self.name = name
		self.noradId = noradId
		self.ephemSat = ephemSat
		self.frequency = None
		self.updateFrequency()

	def updateFrequency(self):
		req = requests.get("https://db.satnogs.org/api/transmitters/?format=json&satellite__norad_cat_id=" + str(self.noradId))
		frequencies = json.loads(req.text)

		for frequency in frequencies:
			if frequency["status"] == "active":
				self.frequency = frequency["downlink_low"]
				break

	def nextPassUTC(self, observer: ephem.Observer):
		observer.date = time.strftime('%Y/%m/%d %H:%M:%S', time.gmtime())
		self.ephemSat.compute(observer)
		npass = observer.next_pass(self.ephemSat)
		# self.ephemSat.compute(observer)
		# alt = math.degrees(self.ephemSat.alt)
		return {
			"f_time_utc": npass[0].datetime().strftime('%H:%M:%S %d/%m/%Y') ,
			"f_in_min": utils.sec_to_human((npass[0].datetime() -  ephem.now().datetime()).total_seconds()) ,
			"f_max_alt":  str((int(math.degrees(npass[3])*100))/100.0)+"deg",
			"f_duration": utils.sec_to_human((npass[4].datetime() - npass[0].datetime()).total_seconds()),

			"time_utc": npass[0].datetime() ,
			"in_min": (npass[0].datetime() -  ephem.now().datetime()).total_seconds(),
			"max_alt":  int(math.degrees(npass[3])*100)/100.0,
			"duration": (npass[4].datetime() - npass[0].datetime()).total_seconds()
		}

	def isOverHead(self, observer: ephem.Observer):
		observer.date = time.strftime('%Y/%m/%d %H:%M:%S', time.gmtime())
		self.ephemSat.compute(observer)
		alt = math.degrees(self.ephemSat.alt)
		return alt > 0

	def _getSettingTime(self, observer: ephem.Observer):
		if not self.isOverHead(observer):
			npass = observer.next_pass(self.ephemSat)
			observer.date = npass[0].datetime() + datetime.timedelta(0,1,0)

		end = observer.date
		while math.degrees(self.ephemSat.alt) >0:
			observer.date = observer.date.datetime() + datetime.timedelta(0,1,0)
			self.ephemSat.compute(observer)
			end = observer.date

		observer.date = time.strftime('%Y/%m/%d %H:%M:%S', time.gmtime())
		self.ephemSat.compute(observer)
		return end

	def getFrequency(self, observer: ephem.Observer):
		observer.date = time.strftime('%Y/%m/%d %H:%M:%S', time.gmtime())
		self.ephemSat.compute(observer)
		C = 300000000.0
		return int(self.frequency - self.ephemSat.range_velocity * self.frequency / C)  # doppler

	def overHeadStatus(self, observer: ephem.Observer):
		observer.date = time.strftime('%Y/%m/%d %H:%M:%S', time.gmtime())
		self.ephemSat.compute(observer)

		nset = self._getSettingTime(observer)
		alt = math.degrees(self.ephemSat.alt)

		return {
			"f_time_los": utils.sec_to_human((nset.datetime()-ephem.now().datetime()).total_seconds()) ,
			"f_current_elevation": str(int(alt*1000)/1000.0)+"deg",
			"f_frequency": str( self.getFrequency(observer)/1000000.0 ) + "MHz",

			"time_los": (nset.datetime() - ephem.now().datetime()).total_seconds() ,
			"current_elevation": int(alt*1000)/1000.0,
			"frequency": self.getFrequency(observer),
		}


class TLEManger():
	def __init__(self, filters=None):
		super(TLEManger, self).__init__()

		self.tle_url = "https://www.celestrak.com/NORAD/elements/active.txt"
		self.tle_last_update = 0
		self.tle_update_every = 60 * 60 * 1
		self.tle = {}

		self.filters = filters
		self.update_tle()

	def parseTLE(self, text):
		tle = {}
		try:
			lines = iter(text.split("\n"))
			while True:
				line1 = next(lines).replace("\r", "").rstrip()
				if self.filters is not None and line1 not in self.filters:
					next(lines)
					next(lines)
					continue
				if line1:
					line2 = next(lines)
					line3 = next(lines)
					tle[line1] = CustomSatellite(
						line1,
						int(line3.split(" ")[1]),
						ephem.readtle(line1, line2, line3)
					)
					logger.info("Loaded tle for: "+line1+ " NORAD: "+line3.split(" ")[1])
				else:
					break
		except StopIteration:
			pass
		return tle

	def update_tle(self):
		if (self.tle_last_update + self.tle_update_every) < time.time():
			self.tle_last_update = time.time()
			logger.info('Updating tle')

			try:
				req = requests.get(self.tle_url)
				self.tle = self.parseTLE(req.text)
				logger.info('TLE Update success')
			except Exception:
				logger.error('TLE Update failed' + str(sys.exc_info()[0]))

	@property
	def iss(self) -> CustomSatellite:
		return self.tle["ISS (ZARYA)"]

	@property
	def noaa15(self) -> CustomSatellite:
		return self.tle["NOAA 15 [B]"]

	@property
	def noaa18(self) -> CustomSatellite:
		return self.tle["NOAA 18 [B]"]

	@property
	def noaa19(self) -> CustomSatellite:
		return self.tle["NOAA 19 [+]"]


if __name__ == "__main__":
	logging.basicConfig(format='[%(asctime)s] [%(levelname)05s] [%(name)25s] %(message)s', level=logging.DEBUG)
	logging.getLogger("obswebsocket.core").setLevel(logging.WARNING)
	myloc = ephem.Observer()

	dpr = 180.0 / math.pi
	#PARIS
	myloc.lon = 2.3522 / dpr
	myloc.lat = 48.8566 / dpr
	myloc.elevation = 35

	tle = TLEManger(filters=["ISS (ZARYA)"])

	while True:
		time.sleep(5)
		tle.update_tle()

		overhead = tle.iss.isOverHead(myloc)
		current_status = tle.iss.overHeadStatus(myloc)
		next_pass = tle.iss.nextPassUTC(myloc)

		if overhead:
			logging.info("Current pass elevation: %s Frequency: %s Time until LOS: %s" % (
				current_status["f_current_elevation"], current_status["f_frequency"], current_status["f_time_los"]))
		else:
			logging.info("Next pass is at %s UTC (in %s) Max altitude will be: %s Duration of the pass is: %s" % (
				next_pass["f_time_utc"], next_pass["f_in_min"], next_pass["f_max_alt"], next_pass["f_duration"]))
