import datetime
import time
from typing import Dict, Optional

import requests
import ephem
import logging
import json
import math
import utils

logger = logging.getLogger(__name__)


class SatelliteVisibleException(Exception):
	pass

class SatelliteInvisibleException(Exception):
	pass


class PassInformation:
	def __init__(self, _overhead: bool, pass_info: Optional[tuple], time_table: Dict[datetime.datetime, Dict[str, int]], current_frequency, current_elevation=None, info_logger=None):
		self.logger = info_logger
		self.overhead = _overhead
		self.current_frequency = current_frequency
		self.time_table = time_table
		self.time_table_times = list(time_table.keys())

		if _overhead:
			self.current_elevation = current_elevation

			self.aos_time = None
			self.aos_in_seconds = 0
			self.aos_azimuth = 0

			self.time_left = self.time_table_times[-1] - self.time_table_times[0]
			self.max_el = 0  # TODO Calculate via the time table
			self.max_el_time = None  # TODO Calculate via the time table

			self.los_time = self.time_table_times[-1]
			self.los_in_seconds = (ephem.now().datetime() - self.time_table_times[-1]).total_seconds()
			self.los_azimuth = self.time_table[self.time_table_times[-1]]["azimuth"]

		else:
			# pass_info is the result of pyephem next_pass()
			aos_time, aos_azimuth, max_el_time, max_el, los_time, los_azimuth = pass_info
			self.aos_time = aos_time.datetime()
			self.aos_in_seconds = (aos_time.datetime() - ephem.now().datetime()).total_seconds()
			self.aos_azimuth = math.degrees(aos_azimuth)

			self.duration = los_time.datetime() - aos_time.datetime()
			self.max_el = math.degrees(max_el)
			self.max_el_time = max_el_time.datetime()

			self.los_time = los_time.datetime()
			self.los_in_seconds = (ephem.now().datetime() - los_time.datetime()).total_seconds()
			self.los_azimuth = math.degrees(aos_azimuth)

		pass

	def log(self):
		_logger = self.logger
		if not _logger:
			_logger = logging

		if self.overhead:
			_logger.info("Current pass elevation: %s Frequency: %s Time until LOS: %s" % (
				self.current_elevation,
				self.current_frequency,
				utils.sec_to_human(int(self.time_left.total_seconds()))
			))
		else:
			_logger.info("Next pass is at %s UTC (in %s) Max altitude will be: %s Duration of the pass is: %s" % (
				self.aos_time.strftime('%H:%M:%S %d/%m/%Y'),
				utils.sec_to_human(self.aos_in_seconds),
				self.max_el,
				utils.sec_to_human(self.duration.total_seconds())
			))

	@property
	def time_table_pretty(self) -> str:
		ret = "| {:<20} | {:<8} | {:<8} |\n".format('Time', 'Az', 'El')
		ret += "| "+('-'*20)+" | "+('-'*8)+" | "+('-'*8)+" |\n"
		for k, v in self.time_table.items():
			ret += "| {:<20} | {:<8} | {:<8} |\n".format(k.strftime('%H:%M:%S %d/%m/%Y'), round(v["azimuth"], 3), round(v["elevation"], 3))
		return ret

	@property
	def time_table_mini_pretty(self) -> str:
		max_count = 15
		skip_count_per_loop = len(self.time_table.items()) // max_count

		ret = "| {:<20} | {:<8} | {:<8} |\n".format('Time', 'Az', 'El')
		ret += "| "+('-'*20)+" | "+('-'*8)+" | "+('-'*8)+" |\n"
		loop = iter(self.time_table.items())
		for k, v in loop:
			ret += "| {:<20} | {:<8} | {:<8} |\n".format(k.strftime('%H:%M:%S %d/%m/%Y'), round(v["azimuth"], 3), round(v["elevation"], 3))
			for i in range(skip_count_per_loop):
				try:
					next(loop)
				except StopIteration:
					break

		k = self.time_table_times[-1]
		v = self.time_table[k]
		ret += "| {:<20} | {:<8} | {:<8} |\n".format(k.strftime('%H:%M:%S %d/%m/%Y'), round(v["azimuth"], 3), round(v["elevation"], 3))

		return ret

class CustomSatellite:
	SATNOGS_TRANSMITTER_URL = "https://db.satnogs.org/api/transmitters/?format=json&satellite__norad_cat_id="

	def __init__(self, name, noradId, pyephem_sat):
		super(CustomSatellite, self).__init__()
		self.logger = logging.getLogger("TLESat ("+name+")")

		self.name = name
		self.noradId = noradId
		self.pyephem_sat = pyephem_sat
		self.frequency = None
		self.update_frequency()

	def update_frequency(self, force_to: int = None):
		if force_to:
			self.frequency = force_to
			self.logger.info("Forced downlink frequency to %s" % force_to)
		else:
			req = requests.get(CustomSatellite.SATNOGS_TRANSMITTER_URL + str(self.noradId))
			frequencies = json.loads(req.text)

			for frequency in frequencies:
				if frequency["status"] == "active":
					self.logger.info("Selected downlink frequency %s with name %s" % (frequency["downlink_low"], frequency["description"]))
					self.frequency = frequency["downlink_low"]
					break

	def doppler_frequency(self, observer: Optional[ephem.Observer], skip_compute=False):
		if not skip_compute or observer is not None:
			observer.date = time.strftime('%Y/%m/%d %H:%M:%S', time.gmtime())
			self.pyephem_sat.compute(observer)
		C = 300000000.0
		return int(self.frequency - self.pyephem_sat.range_velocity * self.frequency / C)  # doppler

	def is_overhead(self, observer: Optional[ephem.Observer], skip_compute=False):
		if not skip_compute or observer is not None:
			observer.date = time.strftime('%Y/%m/%d %H:%M:%S', time.gmtime())
			self.pyephem_sat.compute(observer)
		return math.degrees(self.pyephem_sat.alt) > 0

	def get_next_or_current_pass_time_table(self, observer: ephem.Observer, granularity: datetime.timedelta = datetime.timedelta(0, 1, 0)):
		original_observer_date = observer.date

		# If the sat is not overhead yet advance the time until it is
		if not self.is_overhead(observer):
			next_pass = observer.next_pass(self.pyephem_sat)
			observer.date = next_pass[0].datetime() + datetime.timedelta(0, 1, 0)
			self.pyephem_sat.compute(observer)

		time_table = {}
		future_time = observer.date
		while math.degrees(self.pyephem_sat.alt) > 0:
			observer.date = observer.date.datetime() + granularity
			self.pyephem_sat.compute(observer)
			time_table[future_time.datetime()] = {
				"elevation": math.degrees(self.pyephem_sat.alt),
				"azimuth": 0  # TODO Fix azimuth in time table
			}

			future_time = observer.date

		observer.date = original_observer_date
		self.pyephem_sat.compute(observer)

		return {
			"los_time": future_time.datetime(),
			"time_table": time_table
		}

	def next_pass(self, observer: ephem.Observer) -> PassInformation:
		if self.is_overhead(observer):
			raise SatelliteVisibleException("%s is visible and can not compute next pass fully" % self.name)
		else:
			time_table = self.get_next_or_current_pass_time_table(observer)
			observer.date = time.strftime('%Y/%m/%d %H:%M:%S', time.gmtime())
			self.pyephem_sat.compute(observer)
			return PassInformation(
				False,
				observer.next_pass(self.pyephem_sat),
				time_table["time_table"],
				self.doppler_frequency(None, skip_compute=True),
				info_logger=self.logger
			)

	def current_pass(self, observer: ephem.Observer) -> PassInformation:
		if not self.is_overhead(observer):
			raise SatelliteInvisibleException("%s is not visible and can not compute current pass fully" % self.name)
		else:
			time_table = self.get_next_or_current_pass_time_table(observer)
			observer.date = time.strftime('%Y/%m/%d %H:%M:%S', time.gmtime())
			self.pyephem_sat.compute(observer)
			return PassInformation(
				True,
				None,
				time_table["time_table"],
				self.doppler_frequency(None, skip_compute=True),
				current_elevation=math.degrees(self.pyephem_sat.alt),
				info_logger=self.logger
			)


class TLEManger:
	def __init__(self, filters=None):
		super(TLEManger, self).__init__()
		self.logger = logging.getLogger(TLEManger.__name__)

		self.tle_url = "https://www.celestrak.com/NORAD/elements/active.txt"
		self.tle_last_update = 0
		self.tle_update_every = 60 * 60 * 1
		self.satellites = {}

		self.filters = filters
		self.update_tle()

	def parse_tle(self, text: str) -> Dict[str, CustomSatellite]:
		_satellites = {}
		try:
			lines = iter(text.split("\n"))
			while True:
				sat_name = next(lines).replace("\r", "").rstrip()
				if self.filters is not None and sat_name not in self.filters:
					next(lines)
					next(lines)
					continue
				if sat_name:
					line2 = next(lines)
					line3 = next(lines)
					_satellites[sat_name] = CustomSatellite(
						sat_name,
						int(line3.split(" ")[1]),
						ephem.readtle(sat_name, line2, line3)
					)
					self.logger.info("Loaded tle for: " + sat_name + " NORAD ID: " + line3.split(" ")[1])
				else:
					break
		except StopIteration:
			pass
		return _satellites

	def update_tle(self):
		if (self.tle_last_update + self.tle_update_every) < time.time():
			self.tle_last_update = time.time()
			self.logger.info('Updating tle')

			try:
				req = requests.get(self.tle_url)
				self.satellites = self.parse_tle(req.text)
				self.logger.info('TLE Update success')
			except Exception as e:
				self.logger.error('TLE Update failed', e)

	@property
	def iss(self) -> CustomSatellite:
		return self.satellites["ISS (ZARYA)"]

	@property
	def noaa15(self) -> CustomSatellite:
		return self.satellites["NOAA 15"]

	@property
	def noaa18(self) -> CustomSatellite:
		return self.satellites["NOAA 18"]

	@property
	def noaa19(self) -> CustomSatellite:
		return self.satellites["NOAA 19"]

	@property
	def meteorM2(self) -> CustomSatellite:
		return self.satellites["METEOR-M 2"]


if __name__ == "__main__":
	logging.basicConfig(format='[%(asctime)s] [%(levelname)05s] [%(name)-20s] %(message)s', level=logging.DEBUG)
	logging.getLogger("urllib3.connectionpool").setLevel(logging.WARNING)
	myloc = ephem.Observer()

	dpr = 180.0 / math.pi

	# Paris location
	myloc.lon = 2.3504 / dpr
	myloc.lat = 48.8754 / dpr
	myloc.elevation = 42

	tle = TLEManger(filters=["NOAA 15", "NOAA 18", "NOAA 18", "METEOR-M 2"])

	while True:
		time.sleep(5)
		tle.update_tle()

		for _satellite in tle.satellites:
			satellite = tle.satellites[_satellite]
			if satellite.is_overhead(myloc):
				satellite.current_pass(myloc).log()
			else:
				satellite.next_pass(myloc).log()

		# overhead = tle.meteorM2.is_overhead(myloc)
		# if not overhead:
		# 	tle.meteorM2.next_pass(myloc).log()
		# 	# print(tle.meteorM2.next_pass(myloc).time_table_mini_pretty)
		# else:
		# 	tle.meteorM2.current_pass(myloc).log()
