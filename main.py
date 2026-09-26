from __future__ import annotations
from datetime import datetime, timedelta, timezone
from collections.abc import Iterator
from typing import Any
from bitarray import bitarray

_EPOCH = 1043107200
_UNIT = 900
_UNIT_DELTA = timedelta(seconds=_UNIT)

class YotsubaTime:
    time: int

    def __init__(self, time: int | datetime | timedelta | YotsubaTime, floor: bool = False):
        if isinstance(time, datetime):
            delta = time.astimezone(timezone.utc) - datetime.fromtimestamp(_EPOCH, tz=timezone.utc)
            self.time = delta // _UNIT_DELTA if floor else -((-delta) // _UNIT_DELTA)
        elif isinstance(time, timedelta):
            self.time = time // _UNIT_DELTA if floor else -((-time) // _UNIT_DELTA)
        elif isinstance(time, YotsubaTime):
            self.time = time.time
        else:
            self.time = int(time)

    def __add__(self, other: int | datetime | timedelta | YotsubaTime) -> YotsubaTime:
        if isinstance(other, int):
            return YotsubaTime(self.time + other)
        elif isinstance(other, (datetime, timedelta)):
            return YotsubaTime(self.time + YotsubaTime(other).time)
        elif isinstance(other, YotsubaTime):
            return YotsubaTime(self.time + other.time)
        return NotImplemented

    __radd__ = __add__

    def __sub__(self, other: int | datetime | timedelta | YotsubaTime) -> YotsubaTime:
        if isinstance(other, int):
            return YotsubaTime(self.time - other)
        elif isinstance(other, (datetime, timedelta)):
            return YotsubaTime(self.time - YotsubaTime(other).time)
        elif isinstance(other, YotsubaTime):
            return YotsubaTime(self.time - other.time)
        return NotImplemented

    def __floordiv__(self, other: int) -> YotsubaTime:
        return YotsubaTime(self.time // other)

    def __mul__(self, other: int) -> YotsubaTime:
        return YotsubaTime(self.time * other)

    __rmul__ = __mul__

    def to_datetime(self) -> datetime:
        return datetime.fromtimestamp(self.time * _UNIT + _EPOCH)

    def __lt__(self, other: int | datetime | timedelta | YotsubaTime) -> bool:
        if isinstance(other, YotsubaTime):
            return self.time < other.time
        elif isinstance(other, int):
            return self.time < other
        elif isinstance(other, (datetime, timedelta)):
            return self.time < YotsubaTime(other).time
        return NotImplemented

    def __gt__(self, other: int | datetime | timedelta | YotsubaTime) -> bool:
        if isinstance(other, YotsubaTime):
            return self.time > other.time
        elif isinstance(other, int):
            return self.time > other
        elif isinstance(other, (datetime, timedelta)):
            return self.time > YotsubaTime(other).time
        return NotImplemented

    def __le__(self, other: int | datetime | timedelta | YotsubaTime) -> bool:
        if isinstance(other, YotsubaTime):
            return self.time <= other.time
        elif isinstance(other, int):
            return self.time <= other
        elif isinstance(other, (datetime, timedelta)):
            return self.time <= YotsubaTime(other).time
        return NotImplemented

    def __ge__(self, other: int | datetime | timedelta | YotsubaTime) -> bool:
        if isinstance(other, YotsubaTime):
            return self.time >= other.time
        elif isinstance(other, int):
            return self.time >= other
        elif isinstance(other, (datetime, timedelta)):
            return self.time >= YotsubaTime(other).time
        return NotImplemented

    def __eq__(self, other: Any) -> bool:
        if isinstance(other, YotsubaTime):
            return self.time == other.time
        elif isinstance(other, int):
            return self.time == other
        elif isinstance(other, (datetime, timedelta)):
            return self.time == YotsubaTime(other).time
        return NotImplemented

    def __hash__(self) -> int:
        return hash(self.time)

    def __repr__(self) -> str:
        return f"{self.time}YT"

class OnceOffTime:
    name: str
    start: YotsubaTime
    end: YotsubaTime

    def __init__(self, name: str, start: datetime, end: datetime):
        if end <= start:
            raise ValueError('OnceOffTime end must be after start')

        self.name = name
        self.start = YotsubaTime(start)
        self.end = YotsubaTime(end)

class RepeatingOffTime:
    name: str
    start: YotsubaTime
    duration: YotsubaTime
    repeat_every: YotsubaTime
    

    def __init__(self, name: str, start: datetime, duration: int, repeat_every: timedelta):
        if duration <= 0:
            raise ValueError('RepeatingOffTime duration must be positive')
        if repeat_every <= timedelta(0):
            raise ValueError('RepeatingOffTime repeat_every must be positive')

        self.name = name
        self.start = YotsubaTime(start)
        self.duration = YotsubaTime(duration)
        self.repeat_every = YotsubaTime(repeat_every)

class OnceTask:
    name: str
    schedule_after: YotsubaTime | None
    due_date: YotsubaTime
    duration: YotsubaTime
    minimum_split_size: int | None # None means no minimum split size, use entire duration

    def __init__(self, name: str, due_date: datetime, duration: int, minimum_split_size: int | None = 1, schedule_after: datetime | None = None):
        if duration <= 0:
            raise ValueError('duration must be positive')
        if minimum_split_size is not None and minimum_split_size <= 0:
            raise ValueError('minimum_split_size must be positive')
        if schedule_after is not None and schedule_after > due_date:
            raise ValueError('schedule_after must be before due_date')

        self.name = name
        self.due_date = YotsubaTime(due_date, floor=True)
        self.duration = YotsubaTime(duration)
        self.minimum_split_size = minimum_split_size
        self.schedule_after = YotsubaTime(schedule_after) if schedule_after is not None else None

class RepeatingTask:
    name: str
    start: YotsubaTime
    first_due_date: YotsubaTime
    duration: YotsubaTime
    due_date_repeats_every: YotsubaTime #TODO: Allow repeat at a particular time of day. Can screw up if repeats every is 24 hours when the user wants it to repeat at particular time of day, and daylight savings happens
    minimum_split_size: int | None # None means no minimum split size, use entire duration

    def __init__(self, name: str, start: datetime, first_due_date: datetime, duration: int, due_date_repeats_every: timedelta, minimum_split_size: int | None = 1):
        if duration <= 0:
            raise ValueError('duration must be positive')
        if minimum_split_size is not None and minimum_split_size <= 0:
            raise ValueError('minimum_split_size must be positive')
        if due_date_repeats_every <= timedelta(0):
            raise ValueError('due_date_repeats_every must be positive')

        self.name = name
        self.start = YotsubaTime(start)
        self.first_due_date = YotsubaTime(first_due_date, floor=True)
        self.duration = YotsubaTime(duration)
        self.due_date_repeats_every = YotsubaTime(due_date_repeats_every)
        self.minimum_split_size = minimum_split_size

class TaskSplit:
    task: OnceTask | RepeatingTask
    schedule_after: YotsubaTime
    schedule_before: YotsubaTime
    duration: YotsubaTime

    def __init__(self, task: OnceTask | RepeatingTask, start: YotsubaTime, end: YotsubaTime, duration: YotsubaTime):
        self.task = task
        self.schedule_after = start
        self.schedule_before = end
        self.duration = duration

class TaskSplitCollection:
    _task_splits: list[TaskSplit]
    _is_split_visible: bitarray
    _count_visible: int

    def __init__(self, tasks: list[OnceTask | RepeatingTask], start: YotsubaTime, end: YotsubaTime):
        self._task_splits = []

        for task in tasks:
            if isinstance(task, OnceTask):
                self._task_splits += TaskSplitCollection.create_splits_for_once_task(task, start)
            else:
                self._task_splits += TaskSplitCollection.create_splits_for_repeating_task(task, start, end)
        self._is_split_visible = bitarray(len(self._task_splits))
        self._is_split_visible.setall(True)
        self._count_visible = len(self._task_splits)

    def __iter__(self) -> Iterator[TaskSplit]:
        for split, visible in zip(self._task_splits, self._is_split_visible):
            if visible:
                yield split

    def visible_indexed(self) -> Iterator[tuple[int, TaskSplit]]:
        for i, (split, visible) in enumerate(zip(self._task_splits, self._is_split_visible)):
            if visible:
                yield i, split

    def has_visible_splits(self) -> bool:
        return self._count_visible > 0

    def hide(self, index: int):
        if not self._is_split_visible[index]:
            raise ValueError(f'Attempt to hide split at index {index} when it is already hidden')

        self._is_split_visible[index] = False
        self._count_visible -= 1
    
    def show(self, index: int): 
        if self._is_split_visible[index]:
            raise ValueError(f'Attempt to show split at index {index} when it is already visible')

        self._is_split_visible[index] = True
        self._count_visible += 1

    @staticmethod
    def create_splits_given_duration(task: OnceTask | RepeatingTask, schedule_after: YotsubaTime, schedule_before: YotsubaTime, minimum_split_size: YotsubaTime) -> list[TaskSplit]:
        '''Given a task, a schedule_after time, a schedule_before time, and a minimum split size, creates splits for the task.
        
        Multiple other methods require this functionality, so this method is split out to avoid code duplication.
        '''
        duration_left = task.duration
        splits: list[TaskSplit] = []
        
        while (duration_left - minimum_split_size) >= 0:
            splits.append(TaskSplit(task, schedule_after, schedule_before, minimum_split_size))
            duration_left -= minimum_split_size

        if duration_left > 0:
            splits.append(TaskSplit(task, schedule_after, schedule_before, duration_left))

        return splits

    @staticmethod
    def create_splits_for_once_task(task: OnceTask, start_time: YotsubaTime) -> list[TaskSplit]:
        return TaskSplitCollection.create_splits_given_duration(
            task, 
            task.schedule_after if task.schedule_after is not None else start_time, 
            task.due_date, 
            YotsubaTime(task.minimum_split_size) if task.minimum_split_size is not None else task.duration
        )

    @staticmethod
    def create_splits_for_repeating_task(task: RepeatingTask, start_time: YotsubaTime, end_time: YotsubaTime) -> list[TaskSplit]:
        splits: list[TaskSplit] = []
        current_schedule_after = task.start
        current_schedule_before = task.first_due_date

        while current_schedule_after < end_time:
            # Basically we can sort of treat RepeatingTasks as multiple OnceTasks,
            # where the schedule_after is the last occurence's due date, and the schedule_before is this occurence's due date.


            if current_schedule_before > start_time:  # skip periods that ended before the window
                splits += TaskSplitCollection.create_splits_given_duration(
                    task,
                    max(current_schedule_after, start_time),
                    min(current_schedule_before, end_time),
                    YotsubaTime(task.minimum_split_size) if task.minimum_split_size is not None else task.duration
                )
            
            current_schedule_after = current_schedule_before
            current_schedule_before += task.due_date_repeats_every

        return splits

    def get_task_splits(self) -> list[TaskSplit]:
        return self._task_splits

class Schedule:
    _events_by_time: list[OnceOffTime | RepeatingOffTime | OnceTask | RepeatingTask | None]
    _times_by_event: dict[OnceOffTime | RepeatingOffTime | OnceTask | RepeatingTask, list[YotsubaTime]]
    _first_time: YotsubaTime

    def __init__(self, tasks: list[OnceTask | RepeatingTask], off_times: list[OnceOffTime | RepeatingOffTime], first_time: datetime):
        self._first_time = YotsubaTime(first_time)

        last_due_date = max([task.due_date for task in tasks if isinstance(task, OnceTask)], default=self._first_time)

        self._events_by_time = [None] * (last_due_date - self._first_time).time

        # place down offtimes
        for off_time in off_times:
            if isinstance(off_time, OnceOffTime):
                self.place_once_offtime(off_time)
            else:
                self.place_repeating_offtime(off_time)

        backtrack_result = self._backtrack_place_splits(TaskSplitCollection(tasks, self._first_time, last_due_date))

        if not backtrack_result:
            raise ValueError("Could not place all tasks in the schedule given the constraints.")

        self._generate_times_by_event()

    def _find_next_gap(self, start_index: int, duration: int, stop_index: int) -> int | None:
        '''Searches the events_by_time list for the next gap of at least 
        'duration' length, starting from 'start_index' and not exceeding 
        'stop_index'. Returns the index of the start of the gap if found, 
        otherwise returns None.
        
        Automatically accounts for duration of the task. Thus, do not adjust stop_index to account for duration; this method will do that automatically.'''

        last_start = min(stop_index, len(self._events_by_time)) - duration

        for i in range(start_index, last_start + 1):
            if all(self._events_by_time[j] is None for j in range(i, i + duration)):
                return i
        return None

    def _place_task_at_range(self, task: OnceTask | RepeatingTask, start: int, stop: int):
        '''Places tasks in the schedule on the range [start, stop). Raises ValueError if the range is already occupied or out of bounds]'''
        for i in range(start, stop):
            if i >= len(self._events_by_time):
                raise ValueError(f"Index {i} is out of bounds for events_by_time with length {len(self._events_by_time)}")

            if self._events_by_time[i] is not None:
                raise ValueError(f"Time slot at index {i} is already occupied by {self._events_by_time[i]}")

            self._events_by_time[i] = task

    def _remove_task_from_range(self, start: int, stop: int):
        for i in range(start, stop):
            if i >= len(self._events_by_time):
                raise ValueError(f"Index {i} is out of bounds for events_by_time with length {len(self._events_by_time)}")

            if self._events_by_time[i] is None:
                raise ValueError(f"Time slot at index {i} is already empty")

            self._events_by_time[i] = None


    def _backtrack_place_splits(self, split_collection: TaskSplitCollection) -> bool:
        for i, split in split_collection.visible_indexed():
            schedule_after_index = (split.schedule_after - self._first_time).time
            schedule_before_index = min((split.schedule_before - self._first_time).time, len(self._events_by_time))

            next_gap = self._find_next_gap(schedule_after_index, split.duration.time, schedule_before_index)

            # Within this while loop, we will be placing the split
            # Thus no further recursive calls should use the same split, so we hide it from the split collection
            split_collection.hide(i)

            while next_gap is not None:
                self._place_task_at_range(split.task, next_gap, next_gap + split.duration.time)

                if self._backtrack_place_splits(split_collection):
                    return True

                # If we are here, then the split placement did not lead to a solution
                # Don't backtrack yet; instead, remove the task from the range and try a next gap
                self._remove_task_from_range(next_gap, next_gap + split.duration.time)

                # Try the next gap
                next_gap = self._find_next_gap(next_gap + 1, split.duration.time, schedule_before_index)

            # If we are here, then we have tried all gaps for this split and none led to a solution
            # Thus we show the split for future recursive calls
            split_collection.show(i)

        # got to end of the split collection, so EITHER all splits have been placed
        # OR there are still splits left to place, but we couldn't find a gap for any of them, so we backtrack
        if (not split_collection.has_visible_splits()):
            return True
        return False

    def _generate_times_by_event(self):
        self._times_by_event = {}
        for index, event in enumerate(self._events_by_time):
            if event is not None:
                if event not in self._times_by_event:
                    self._times_by_event[event] = []
                self._times_by_event[event].append(self._first_time + index)


    def place_once_offtime(self, off_time: OnceOffTime):
        '''Places a OnceOffTime in the schedule. If the off time is outside the bounds of the schedule, it will be truncated to fit within the schedule.'''

        start_index: int = max(0, (off_time.start - self._first_time).time)
        end_index: int = min((off_time.end - self._first_time).time, len(self._events_by_time))

        for i in range(start_index, end_index):
            self._events_by_time[i] = off_time

    def place_repeating_offtime(self, off_time: RepeatingOffTime):
        '''Places a RepeatingOffTime in the schedule. If the off time is outside the bounds of the schedule, it will be truncated to fit within the schedule.'''

        current_start_index: int = max(0, (off_time.start - self._first_time).time)

        while current_start_index < len(self._events_by_time):
            for i in range(current_start_index, min(current_start_index + off_time.duration.time, len(self._events_by_time))):
                self._events_by_time[i] = off_time

            current_start_index += off_time.repeat_every.time

    def get_event_at_time(self, time: YotsubaTime) -> OnceOffTime | RepeatingOffTime | OnceTask | RepeatingTask | None:
        index: int = (time - self._first_time).time
        if 0 <= index < len(self._events_by_time):
            return self._events_by_time[index]
        else:
            raise ValueError(f"Time {time} is out of bounds for the schedule.")

    def get_times_for_event(self, event: OnceOffTime | RepeatingOffTime | OnceTask | RepeatingTask) -> list[YotsubaTime]:
        if event in self._times_by_event:
            return self._times_by_event[event]
        else:
            raise ValueError(f"Event {event} is not in the schedule.")