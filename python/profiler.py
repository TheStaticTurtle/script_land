import enum
import time
import typing
from dataclasses import dataclass

class ProfilerException(Exception):
	pass

class Profiler:
	@dataclass
	class Event:
		class EventType(enum.Enum):
			INTERNAL_MARKER = 0
			EVENT = 1
		facility: str
		name: str
		absolute_timestamp: float
		relative_timestamp: float
		time_since_last_event: typing.Optional[float]
		type: EventType
		cached: bool

		@property
		def __dict__(self):
			return {
				"type": self.type.name,
				"facility": self.facility,
				"name": self.name,
				"absolute_timestamp": 0 if self.absolute_timestamp is None else round(self.absolute_timestamp, 2),
				"relative_timestamp": 0 if self.relative_timestamp is None else round(self.relative_timestamp, 2),
				"time_since_last_event": 0 if self.time_since_last_event is None else round(self.time_since_last_event, 2),
				"cached": self.cached,
			}

	def __init__(self):
		self.events = []
		self.start_timestamp = None
		self.last_event = None

	def log_event(self, name, facility="", event_type=Event.EventType.EVENT, cached: bool = False):
		if self.start_timestamp is None:
			raise ProfilerException("Can't log exception without starting it first")

		timestamp = time.time()
		time_since_last_event = (timestamp - self.last_event.absolute_timestamp) * 1000
		self.last_event = Profiler.Event(
			facility=facility,
			name=name,
			absolute_timestamp=self.last_event.absolute_timestamp if cached else timestamp,
			relative_timestamp=self.last_event.relative_timestamp if cached else (timestamp - self.start_timestamp) * 1000,
			time_since_last_event=0 if cached else time_since_last_event,
			type=event_type,
			cached=cached
		)
		self.events.append(self.last_event)

	def start(self):
		self.start_timestamp = time.time()
		self.last_event = Profiler.Event(
			facility="",
			name="start",
			absolute_timestamp=self.start_timestamp,
			relative_timestamp=0,
			time_since_last_event=None,
			type=Profiler.Event.EventType.INTERNAL_MARKER,
			cached=False
		)
		self.events.append(self.last_event)

	def end(self):
		self.log_event("end", event_type=Profiler.Event.EventType.INTERNAL_MARKER)

	@property
	def duration(self) -> float:
		return round((self.events[-1].absolute_timestamp - self.events[0].absolute_timestamp) * 1000, 2)

	@property
	def __dict__(self):
		return {
			"start_timestamp": self.start_timestamp,
			"duration": self.duration,

			"events": [event.__dict__ for event in self.events if event.type != Profiler.Event.EventType.INTERNAL_MARKER]
		}
