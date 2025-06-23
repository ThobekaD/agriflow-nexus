"""
Thread Cron, for task queue

last update: 2020-10-23
"""

from itertools import count
from time import monotonic as _time
from queue import Queue
import threading
from .priority_datatypes import PriorityDict

__all__ = ['ThreadCron', 'run_thread_workers']


def _cb_worker(que):
    while True:
        try:
            typ, func, *args = que.get()
            if typ == 'stop':
                break
            func(*args)
        except Exception as e:
            print(type(e), e)


def run_thread_workers(num, que):
    for i in range(num):
        threading.Thread(target=_cb_worker, args=(que,), daemon=True).start()


class ThreadCron:
    def __init__(self, workers=1, ou_que=None):
        self.is_running = False
        self.data_comes = threading.Event()
        self.mutex = threading.Lock()

        self.uid_maker = count()

        self.heap = []
        self.que = PriorityDict(complex_prior=False)
        self._ou_que = ou_que or Queue()

        self.cron_thread = threading.Thread(target=self.run_thread_cron, daemon=True)

        self.worker_id_maker = count()
        self.workers = workers
        self.worker_threads = {}
        self.add_workers(workers)

    def start(self):
        with self.mutex:
            if not self.is_running:
                self.start_threads()
                self.is_running = True
        return self

    def start_threads(self):
        self.cron_thread.start()
        for k in self.worker_threads:
            self.worker_threads[k].start()

    @property
    def ou_que(self):
        return self._ou_que

    @ou_que.setter
    def ou_que(self, value):
        with self.mutex:
            self._ou_que = value

    def _worker(self, key):
        while True:
            try:
                typ, func, *args = self._ou_que.get()
                if typ in {'stop', 'exit', 'quit'}:
                    with self.mutex:
                        if typ != 'stop' or self.workers > 1:
                            self.worker_threads.pop(key)
                            self.workers = len(self.worker_threads)
                            break
                func(*args)
            except Exception as e:
                print(type(e), e)

    def add_workers(self, num):
        with self.mutex:
            _keys = (self.worker_id_maker.__next__() for _ in range(num))
            _threads = {k: threading.Thread(target=self._worker, args=(k,), daemon=True) for k in _keys}
            if _threads:
                if self.is_running:
                    for k in _threads:
                        _threads[k].start()
                self.worker_threads.update(_threads)
                self.workers = len(self.worker_threads)

    def run_thread_cron(self, check_freq=0.1):
        while True:
            _lis = []
            _now = _time()
            with self.mutex:
                while self.que and self.que.peek_prior() <= _now:
                    _lis.append(self.que.f.pop()[1])
                if self.que:
                    _next = self.que.peek_prior()
                else:
                    _next = _now + check_freq
                if self.data_comes.is_set():
                    self.data_comes.clear()
            for _data in _lis:
                self._ou_que.put(_data)
            self.data_comes.wait(min(_next - _time(), check_freq))

    def cancel(self, key):
        with self.mutex:
            return self.que.pop(key, default=False) is not False

    def call(self, typ_func_args, delay=None):
        return self.call_later(typ_func_args, delay=delay)

    def call_soon(self, typ_func_args):
        self._ou_que.put(typ_func_args)
        return True

    def call_later(self, typ_func_args, delay=None):
        if not self.is_running:
            self.start()
        if delay is None:
            res = self.call_soon(typ_func_args)
        else:
            try:
                _call_time = _time() + delay
                with self.mutex:
                    _key = self.uid_maker.__next__()
                    self.que.push(_key, typ_func_args, prior=_call_time)
                    self.data_comes.set()
                res = _key
            except Exception as e:
                res = None
                print(type(e), e)
        return res
