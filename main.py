from __future__ import annotations
from datetime import datetime, timedelta, timezone
from collections.abc import Iterator
from typing import Any
from bitarray import bitarray

_EPOCH = 1043107200
_UNIT = 900


class YotsubaTime:
    time: int

    def __init__(self, time: int | datetime | timedelta | YotsubaTime):
        if isinstance(time, datetime):
            delta = time.astimezone(timezone.utc) - datetime.fromtimestamp(_EPOCH, tz=timezone.utc)
            self.time = -((-delta) // timedelta(seconds=_UNIT))  # exact ceiling division
        elif isinstance(time, timedelta):
            self.time = -((-time) // timedelta(seconds=_UNIT))
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

    def __init__(self, name: str, start:  datetime, end: datetime):
        self.name = name
        self.start = YotsubaTime(start)
        self.end = YotsubaTime(end)

class RepeatingOffTime:
    name: str
    start: YotsubaTime
    duration: YotsubaTime
    repeat_every_days: int
    

    def __init__(self, name: str, start: datetime, duration: int, repeat_every_days: int):
        self.name = name
        self.start = YotsubaTime(start)
        self.duration = YotsubaTime(duration)
        self.repeat_every_days = repeat_every_days

class OnceTask:
    name: str
    schedule_after: YotsubaTime | None
    due_date: YotsubaTime
    duration: YotsubaTime
    minimum_split_size: int | None # None means no minimum split size, use entire duration

    def __init__(self, name: str, due_date: datetime, duration: int, minimum_split_size: int | None = 1, schedule_after: datetime | None = None):
        self.name = name
        self.due_date = YotsubaTime(due_date)
        self.duration = YotsubaTime(duration)
        self.minimum_split_size = minimum_split_size
        self.schedule_after = YotsubaTime(schedule_after) if schedule_after is not None else None

class RepeatingTask:
    name: str
    start: YotsubaTime
    first_due_date: YotsubaTime
    duration: YotsubaTime
    due_date_repeats_every: YotsubaTime
    minimum_split_size: int | None # None means no minimum split size, use entire duration

    def __init__(self, name: str, start: datetime, first_due_date: datetime, duration: int, due_date_repeats_every: timedelta, minimum_split_size: int | None = 1):
        self.name = name
        self.start = YotsubaTime(start)
        self.first_due_date = YotsubaTime(first_due_date)
        self.duration = YotsubaTime(duration)
        self.due_date_repeats_every = YotsubaTime(due_date_repeats_every)
        self.minimum_split_size = minimum_split_size

class _TaskSplit:
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
    _task_splits: list[_TaskSplit]
    _is_split_visible: bitarray

    def __init__(self, tasks: list[OnceTask | RepeatingTask], start: YotsubaTime, end: YotsubaTime):
        self._task_splits = []

        for task in tasks:
            if isinstance(task, OnceTask):
                self._task_splits += TaskSplitCollection.create_splits_for_once_task(task, start)
            else:
                self._task_splits += TaskSplitCollection.create_splits_for_repeating_task(task, start, end)
        self._is_split_visible = bitarray(len(self._task_splits))
        self._is_split_visible.setall(True)

    def __iter__(self) -> Iterator[_TaskSplit]:
        for split, visible in zip(self._task_splits, self._is_split_visible):
            if visible:
                yield split

    def visible_indexed(self) -> Iterator[tuple[int, _TaskSplit]]:
        for i, (split, visible) in enumerate(zip(self._task_splits, self._is_split_visible)):
            if visible:
                yield i, split

    def hide(self, index: int): self._is_split_visible[index] = False
    
    def show(self, index: int): self._is_split_visible[index] = True

    @staticmethod
    def create_splits_given_duration(task: OnceTask | RepeatingTask, schedule_after: YotsubaTime, schedule_before: YotsubaTime, minimum_split_size: YotsubaTime) -> list[_TaskSplit]:
        '''Given a task, a schedule_after time, a schedule_before time, and a minimum split size, creates splits for the task.
        
        Multiple other methods require this functionality, so this method is split out to avoid code duplication.
        '''
        duration_left = task.duration
        splits: list[_TaskSplit] = []
        
        while (duration_left - minimum_split_size) >= 0:
            splits.append(_TaskSplit(task, schedule_after, schedule_before, minimum_split_size))
            duration_left -= minimum_split_size

        if duration_left > 0:
            splits.append(_TaskSplit(task, schedule_after, schedule_before, duration_left))

        return splits

    @staticmethod
    def create_splits_for_once_task(task: OnceTask, start_time: YotsubaTime) -> list[_TaskSplit]:
        return TaskSplitCollection.create_splits_given_duration(
            task, 
            task.schedule_after if task.schedule_after is not None else start_time, 
            task.due_date, 
            YotsubaTime(task.minimum_split_size) if task.minimum_split_size is not None else task.duration
        )

    @staticmethod
    def create_splits_for_repeating_task(task: RepeatingTask, start_time: YotsubaTime, end_time: YotsubaTime) -> list[_TaskSplit]:
        splits: list[_TaskSplit] = []
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

    def get_task_splits(self) -> list[_TaskSplit]:
        return self._task_splits

class TaskSplitIterator:
    index: int
    collection: TaskSplitCollection

    def __init__(self, collection: TaskSplitCollection):
        self.collection = collection
        self.index = 0

    def __iter__(self):
        return self

    def __next__(self) -> _TaskSplit:
        while self.index < len(self.collection._task_splits): # pyright: ignore[reportPrivateUsage]
            if self.collection._is_split_visible[self.index]: # pyright: ignore[reportPrivateUsage]
                split = self.collection._task_splits[self.index] # pyright: ignore[reportPrivateUsage]
                self.index += 1
                return split
            self.index += 1
        raise StopIteration


# class Schedule:
#     _events_by_time: list[OnceOffTime | RepeatingOffTime | OnceTask | RepeatingTask | None]
#     _times_by_event: dict[OnceOffTime | RepeatingOffTime | OnceTask | RepeatingTask, list[YotsubaTime]]
#     _first_time: YotsubaTime

#     def __init__(self, tasks: list[OnceTask | RepeatingTask], off_times: list[OnceOffTime | RepeatingOffTime], first_time: datetime):
#         first_time = YotsubaTime(first_time)

#         last_due_date = max([task.due_date for task in tasks if isinstance(task, OnceTask)], default=first_time)

#         self._events_by_time = [None] * (last_due_date - first_time)

        


def _test_yotsuba_time():
    current_time = datetime.now()

    print('Current time:', current_time.strftime('%Y-%m-%d %H:%M:%S'))

    yotsuba_time = YotsubaTime(current_time)

    print('Yotsuba time:', yotsuba_time.time)
    print('Yotsuba time as datetime:', yotsuba_time.to_datetime().strftime('%Y-%m-%d %H:%M:%S'))



    print()



    parse_string = "2024-06-01 00:00:01"
    parsed_time = datetime.strptime(parse_string, "%Y-%m-%d %H:%M:%S")
    yotsuba_time_from_string = YotsubaTime(parsed_time)

    print('Parsed time:', parsed_time.strftime('%Y-%m-%d %H:%M:%S'))
    print('Yotsuba time from string:', yotsuba_time_from_string.time)
    print('Yotsuba time from string as datetime:', yotsuba_time_from_string.to_datetime().strftime('%Y-%m-%d %H:%M:%S'))

def _test_split_create():
    task = OnceTask("Test Task", datetime.now() + timedelta(hours=1), 14)
    splits = TaskSplitCollection.create_splits_for_once_task(task, YotsubaTime(datetime.now()))
    for split in splits:
        print(f"Split: {split.task.name}, Start: {split.schedule_after}, End: {split.schedule_before}, Duration: {split.duration}")

_test_split_create()