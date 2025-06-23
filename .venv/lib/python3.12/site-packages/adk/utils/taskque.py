"""
------------------------------------------------------------------------------------------------------------
Main usage:
    Task Queue with key-value mapping, priority, speed limit, timeout and callbacks

TaskQue(
    maxsize=0,              max size of queue

    lock=None,              mutex lock for queue, Lock or RLock
    spd_lim=False,          use speed limit or not, i.e. for flow control
    spd_freq=0.1,           check speed every 'spd_freq' seconds
    max_puts=0,             max number of 'put' calls in 'spd_freq' seconds
    max_gets=0,             max number of 'get' calls in 'spd_freq' seconds

    auto_key=True,         auto generate unique key for 'put' or not
    use_retain=True,        retain data for further use (wait accept) after 'get' calls or not
    use_trace=True,         use trace (record timestamp and last_op...) or not
    default_cb=None,        default callback, i.e. {'timeout_cb':print}
    max_retain=10000,       max size of retain data
    retry_time=0,           if 'accept' isn't called in 'retry_time' seconds after 'get',
                            put the data back to queue
    time_limit=None,        every data expire after 'time_limit' seconds

    executor=None,          executor, run callbacks, default is new instance of ThreadCron
    workers=1,              number of threads, argument in ThreadCron
    ou_que=None,            output queue, argument in ThreadCron
)

Main methods:
    put(self, *args, block=True, timeout=None, time_limit=None, wait_free=None, update_only=False, **kwargs)
        time_limit:     expire time after 'put' success, 'timeout' is only for 'put'
        wait_free:      put data after the queue has been 'wait_free' seconds free
        update_only:    just update, do not put new data, may raise KeyError
        args:           key, value[, prior] or value[, prior] if use 'auto_key'
        kwargs:         put_cb, get_cb, accept_cb, timeout_cb, finalize_cb
        return:         key

    get(self, key={default}, block=True, timeout=None, wait_free=None, typ=None)
        key:            typ = 'get' if key is {default} else 'drop'
        wait_free:      get data after the queue has been 'wait_free' seconds free
        typ:            set the typ manual
        return:         tuple(key, value, priority)

    accept(key)         inform that the data from 'get' is treated

Callbacks:
    callbacks will receive only one argument, and the key of callback = typ + '_cb'

    put_cb, update_cb, get_cb, drop_cb, accept_cb, retry_cb, timeout_cb:
                        receive tuple(key, value, priority)

    finalize_cb:        receive dict with keys ('uid', 'kvp', 'trace', 'msg')
------------------------------------------------------------------------------------------------------------
Classes:
    PriorityQueue:      Queue with Priority, the data with lowest priority first out
    PriorityDict:       PriorityQueue + Mapping, can get data with key
    QueBase:            Base class of other queue, with mutex lock and speed limit
                        args: maxsize, lock, spd_lim, spd_freq, max_puts, max_gets
                        subclass should implement _init, _qsize, _contain, _put, _get, _peek
    PriQue:             PriorityQueue with mutex lock and speed limit
    PriDict:            PriorityDict with mutex lock and speed limit
------------------------------------------------------------------------------------------------------------
Functions:
    init_loop:          Create a Thread with EventLoop, then return this loop
------------------------------------------------------------------------------------------------------------
Author: Jolle 2019-08-16
------------------------------------------------------------------------------------------------------------
Change logs:
    2019-10-05:         Threads add kwarg daemon=True
    2019-10-11:         update prior_warp, add kwarg complex_wrap=False, add peek_prior()
    2019-10-12:         add kwarg value_is_prior=False, add pri_dic[key] = (value, priority)
    2019-10-13:         deprecated use_coroutine, loop, loop_freq, cb_container, cb_workers, cb_queue
                        add ThreadCron
    2019-11-27:         uid_maker = count() -->  (str(i) for i in count())
    2019-11-29:         fix bug: self._none_wrap = self.__min_marker...
                        new features...
    2020-04-15:         new versions of PriorityQueue and PriorityDict
    2020-10-23:         drop something
    2020-12-09:         in TaskQue, put(*args, prior=prior) will get *args
------------------------------------------------------------------------------------------------------------
"""

from itertools import count
from datetime import datetime
from collections import deque
from contextlib import contextmanager
from time import monotonic as _time, sleep as _sleep
import threading
from .priority_datatypes import PriorityQueue, PriorityDict, DEFAULT_MARKER
from .cron_executor import ThreadCron

__all__ = ['TaskQue', 'QueBase', 'PriQue', 'PriDict']


# DEFAULT_MARKER = object()


class QueBase:
    """
    Parameters:
        maxsize         max size of queue
        lock            mutex lock for queue, Lock or RLock
        spd_lim         use speed limit or not, i.e. for flow control
        spd_freq        check speed every 'spd_freq' seconds
        max_puts        max number of 'put' calls in 'spd_freq' seconds
        max_gets        max number of 'get' calls in 'spd_freq' seconds
    Main Functions:
        put(*args, block=True, timeout=None, wait_free=None, **kwargs)          insert or update data
        get(key={default}, block=True, timeout=None, wait_free=None, **kwargs)  get the lowest priority data
        peek(key={default}, block=True, timeout=None)                           peek the lowest priority data
    Main methods to override:
        _init           initialization
        _qsize          size of queue
        _put            put
        _get            get
        _peek           peek
    Other methods to override:
        _contain        check the data is already in queue or not
        _accept         inform that the data from 'get' is treated
        _finalize       finalization
        ...
    """
    __marker = object()

    class Full(Exception):
        pass

    class Empty(Exception):
        pass

    def __init__(self, maxsize=0, lock=None,
                 spd_lim=False, spd_freq=0.1, max_puts=0, max_gets=0,
                 **kwargs):
        self.maxsize = maxsize
        self._init(maxsize, **kwargs)

        # self.mutex = lock or threading.RLock()
        self.mutex = lock or threading.Lock()
        self.not_empty = threading.Condition(self.mutex)
        self.not_full = threading.Condition(self.mutex)

        self.context_mutex = threading.Lock()
        self._frozen = False

        # self._timer = threading.Event().wait
        self._timer = _sleep

        self.spd_lim, self.spd_freq = spd_lim, spd_freq
        self.max_puts, self.max_gets = int(max_puts), int(max_gets)
        self._put_idx: int = 0
        self._get_idx: int = 0
        self._put_time: list = [-1] * max(self.max_puts, 1)
        self._get_time: list = [-1] * max(self.max_gets, 1)

        self._put_cnt = 0
        self._get_cnt = 0

    def speed_limit(self, spd_lim=False, spd_freq=.0, max_puts=0, max_gets=0):
        self.spd_lim = spd_lim
        self.spd_freq = spd_freq or self.spd_freq
        self.max_puts = int(max_puts) or self.max_puts
        self.max_gets = int(max_gets) or self.max_gets

        _last_pt, _last_gt = self._put_time[self._put_idx - 1], self._get_time[self._get_idx - 1]
        self._put_idx: int = 0
        self._get_idx: int = 0
        self._put_time = [-1] * max(self.max_puts - 1, 0) + [_last_pt]
        self._get_time = [-1] * max(self.max_gets - 1, 0) + [_last_gt]

    def freeze(self):
        with self.mutex:
            self._frozen = True

    def unfreeze(self):
        with self.mutex:
            self._frozen = False

    @contextmanager
    def nowait_only(self):
        with self.context_mutex:
            self.freeze()
            yield
            self.unfreeze()

    @contextmanager
    def mutex_lock(self):
        with self.mutex:
            yield

    def put(self, *args, block=True, timeout=None, wait_free=None, **kwargs):
        with self.not_full:
            if self._contain(*args):
                res = self._put(*args, **kwargs)
            else:
                _s_time = _time()
                if wait_free is None:
                    _flag = self.not_full.wait_for(self._put_enabled, timeout) if block else self._not_full()
                    if not _flag:
                        raise TimeoutError if self._frozen else self.Full
                elif block:
                    if timeout is None or timeout <= 0:
                        _put_mark = self._put_cnt
                        _start_time = self._put_time[self._put_idx - 1] + wait_free
                        while not self._put_enabled() or _time() < _start_time:
                            remain_time = _start_time - _time()
                            if remain_time <= 0:
                                self.not_full.wait()
                            else:
                                self.not_full.wait_for(lambda: False, remain_time)
                            if _put_mark != self._put_cnt:
                                _put_mark = self._put_cnt
                                _start_time = self._put_time[self._put_idx - 1] + wait_free
                    else:
                        _put_mark = self._put_cnt
                        _start_time = self._put_time[self._put_idx - 1] + wait_free
                        end_time = _time() + timeout
                        while not self._put_enabled() or _time() < _start_time:
                            _rt_o = end_time - _time()
                            _rt_s = _start_time - _time()

                            if _rt_o <= 0:
                                raise TimeoutError if self._put_enabled() else self.Full
                            elif _rt_s > 0:
                                if _rt_s > _rt_o:
                                    self.not_full.wait_for(lambda: False, _rt_o)
                                    raise TimeoutError if self._put_enabled() else self.Full
                                self.not_full.wait_for(lambda: False, _rt_s)
                            else:
                                self.not_full.wait(_rt_o)

                            if _put_mark != self._put_cnt:
                                _put_mark = self._put_cnt
                                _start_time = self._put_time[self._put_idx - 1] + wait_free
                elif not self._not_full():
                    raise self.Full

                if self.spd_lim and self.max_puts:
                    _e_time = self._put_time[self._put_idx] + self.spd_freq
                    _now = _time()
                    if _e_time > _now:
                        if timeout is not None and timeout > 0 and _s_time + timeout < _e_time:
                            raise TimeoutError
                        else:
                            self._timer(_e_time - _now)

                    self._put_time[self._put_idx] = _time()
                    self._put_idx = int((self._put_idx + 1) % self.max_puts)

                res = self._put(*args, **kwargs)
                self._put_cnt += 1
                self.not_empty.notify()
            return res

    def put_nowait(self, *args, **kwargs):
        return self.put(*args, block=False, **kwargs)

    def get(self, key=DEFAULT_MARKER, block=True, timeout=None, wait_free=None, **kwargs):
        with self.not_empty:
            _s_time = _time()
            if wait_free is None:
                _flag = self.not_empty.wait_for(self._get_enabled, timeout) if block else self._qsize()
                if not _flag:
                    raise TimeoutError if self._frozen else self.Empty
            elif block:
                if timeout is None or timeout <= 0:
                    _get_mark = self._get_cnt
                    _start_time = self._get_time[self._get_idx - 1] + wait_free
                    while not self._get_enabled() or _time() < _start_time:
                        remain_time = _start_time - _time()
                        if remain_time <= 0:
                            self.not_empty.wait()
                        else:
                            self.not_empty.wait_for(lambda: False, remain_time)
                        if _get_mark != self._get_cnt:
                            _get_mark = self._get_cnt
                            _start_time = self._get_time[self._get_idx - 1] + wait_free
                else:
                    _get_mark = self._get_cnt
                    _start_time = self._get_time[self._get_idx - 1] + wait_free
                    end_time = _time() + timeout
                    while not self._get_enabled() or _time() < _start_time:
                        _rt_o = end_time - _time()
                        _rt_s = _start_time - _time()

                        if _rt_o <= 0:
                            raise TimeoutError if self._get_enabled() else self.Empty
                        elif _rt_s > 0:
                            if _rt_s > _rt_o:
                                self.not_empty.wait_for(lambda: False, _rt_o)
                                raise TimeoutError if self._get_enabled() else self.Empty
                            self.not_empty.wait_for(lambda: False, _rt_s)
                        else:
                            self.not_empty.wait(_rt_o)

                        if _get_mark != self._get_cnt:
                            _get_mark = self._get_cnt
                            _start_time = self._get_time[self._get_idx - 1] + wait_free
            elif not self._qsize():
                raise self.Empty

            if self.spd_lim and self.max_gets:
                _e_time = self._get_time[self._get_idx] + self.spd_freq
                _now = _time()
                if _e_time > _now:
                    if timeout is not None and timeout > 0 and _s_time + timeout < _e_time:
                        raise TimeoutError
                    else:
                        self._timer(_e_time - _now)

                self._get_time[self._get_idx] = _time()
                self._get_idx = int((self._get_idx + 1) % self.max_gets)

            res = self._get(key=key, **kwargs)
            self._get_cnt += 1
            # self.not_full.notify()
            if self._not_full():
                self.not_full.notify()
            return res

    def get_nowait(self, key=DEFAULT_MARKER, **kwargs):
        return self.get(key=key, block=False, **kwargs)

    def peek(self, key=DEFAULT_MARKER, block=True, timeout=None):
        with self.not_empty:
            _flag = self.not_empty.wait_for(self._get_enabled, timeout) if block else self._qsize()
            if not _flag:
                raise TimeoutError if self._frozen else self.Empty
            return self._peek(key=key)

    def peek_nowait(self, key=DEFAULT_MARKER):
        return self.peek(key=key, block=False)

    def _empty(self):
        return not self._qsize()

    def _full(self):
        return 0 < self.maxsize <= self._qsize()

    def _not_full(self):
        return not self.maxsize or self.maxsize > self._qsize()

    def _put_enabled(self):
        return not self._frozen and self._not_full()

    def _get_enabled(self):
        return not self._frozen and self._qsize()

    def accept(self, *args, **kwargs):
        with self.mutex:
            self._accept(*args, **kwargs)

    def finalize(self, *args, **kwargs):
        with self.mutex:
            self._finalize(*args, **kwargs)

    # Override these methods to implement other queue organizations
    # (e.g. stack or priority queue).
    # These will only be called with appropriate locks held

    # Initialize the queue representation
    def _init(self, maxsize, **kwargs):
        self.queue = deque()

    def _qsize(self):
        return len(self.queue)

    # Item is in queue
    def _contain(self, *args):
        return False

    # Put a new item in the queue
    def _put(self, *args, **kwargs):
        self.queue.append(*args)

    # Get an item from the queue
    def _get(self, key=DEFAULT_MARKER, **kwargs):
        return self.queue.popleft()

    # Peek an item from the queue
    def _peek(self, key=DEFAULT_MARKER):
        pass

    # do something when received data from 'get'
    def _accept(self, *args, **kwargs):
        pass

    # do finalization if needed
    def _finalize(self, *args, **kwargs):
        pass


class TaskQue(QueBase):
    def _init(self, maxsize=0, auto_key=True, use_retain=True, use_trace=True, default_cb=None,
              max_retain=10000, retry_time=0, time_limit=None,
              # use_coroutine=True, loop=None, loop_freq=0.005,
              # cb_container='auto', cb_workers=1, cb_queue=None,
              executor=None, workers=1, ou_que=None,
              **kwargs,
              ):
        self.uid_maker = (str(i) for i in count())
        self.auto_key = auto_key

        self.use_retain = use_retain
        self.use_trace = use_trace

        self.default_cb = default_cb if default_cb is not None else {}
        self.max_retain = max_retain

        self.retry_time = retry_time

        self.data = {}
        # self.retain = PriorityDict(complex_prior=False, )
        # self.queue = PriorityDict(return_prior=True, complex_prior=False, )
        # self.retain = PriorityDict(format_in=True, format_ou=True)
        # self.queue = PriorityDict(format_in=True, format_ou=True)
        self.retain = PriorityDict()
        self.queue = PriorityDict()

        self.trace = {}
        self.running_cbs = {}

        self.time_limit = time_limit

        self.executor = executor or ThreadCron(workers=workers, ou_que=ou_que)

        # self.heap = []
        # self.heap_lock = threading.Lock()
        #
        # self.use_coroutine = use_coroutine
        # self.loop = init_loop(loop=loop) if self.use_coroutine and self.time_limit else None
        # self.loop_freq = loop_freq
        # if self.use_coroutine and self.time_limit and self.loop_freq:
        #     self.loop.call_soon_threadsafe(asyncio.create_task,
        #                                    _run_delay_calls(self, self.heap, self.heap_lock, self.loop_freq))
        #
        # self.heap_not_empty = threading.Event()
        # if not self.use_coroutine and self.time_limit:
        #     threading.Thread(target=_thd_delay_calls,
        #                      args=(self, self.heap, self.heap_lock, self.loop_freq, self.heap_not_empty),
        #                      daemon=True).start()
        #
        # if cb_container in ('current', 'coroutine', 'thread', 'queue'):
        #     self.cb_container = cb_container
        # else:
        #     self.cb_container = 'queue' if cb_queue is not None else 'thread' if cb_workers else \
        #         'coroutine' if use_coroutine else 'current'
        #
        # self.cb_queue = cb_queue if cb_queue is not None else Queue()
        # self.cb_workers = cb_workers
        # self.cb_threads = []
        #
        # if self.cb_container == 'thread' and self.cb_workers:
        #     for i in range(self.cb_workers):
        #         _thd = threading.Thread(target=_cb_worker, args=(self.cb_queue,), daemon=True)
        #         _thd.start()
        #         self.cb_threads.append(_thd)

    def _parse(self, *args, **kwargs):
        if self.auto_key:
            if not 1 <= len(args) <= 2:
                raise TypeError('put expected 1~2 arguments if auto_key, got %d' % len(args))
            key, value = self.uid_maker.__next__(), args[0]
            # prior = kwargs['prior'] if 'prior' in kwargs else \
            #     args[-1] if len(args) == 2 else None
            kvp = (key, *args)
        else:
            if not 2 <= len(args) <= 3:
                raise TypeError('put expected 2~3 arguments if auto_key, got %d' % len(args))
            key, value = args[0], args[1]
            # prior = kwargs['prior'] if 'prior' in kwargs else \
            #     args[-1] if len(args) == 3 else None
            kvp = args
        res = {'uid': key,
               # 'kvp': (key, value, prior),
               'kvp': kvp,
               'kw': {'prior': kwargs['prior']} if 'prior' in kwargs else {},
               'put_cb': kwargs.get('put_cb', None),
               'get_cb': kwargs.get('get_cb', None),
               'accept_cb': kwargs.get('accept_cb', None),
               'timeout_cb': kwargs.get('timeout_cb', None),
               'finalize_cb': kwargs.get('finalize_cb', None),
               }
        return res

    def _gen_trace(self, key):
        if key not in self.trace:
            self.trace[key] = {
                # 'put': None,
                # 'update': None,
                # 'get': None,
                # 'drop': None,
                # 'accept': None,
                # 'last_op': None,
                'msg': 'unfinished',
            }

    def set_default_cb(self, default_cb=None):
        with self.mutex_lock():
            # self.default_cb = default_cb if default_cb is not None else {}
            self.__setattr__('default_cb', default_cb if default_cb is not None else {})

    def update_default_cb(self, upd_cb: dict):
        with self.mutex_lock():
            self.default_cb.update(upd_cb)

    def run_callback(self, cb=None, data=None, typ=''):
        cb_dft = self.default_cb.get(typ + '_cb', None)
        if cb_dft:
            self._run_cb(cb_dft, data)
        if cb:
            self._run_cb(cb, data)

    def _run_cb(self, cb, data):
        if cb:
            # if self.cb_container == 'coroutine':
            #     self.loop.call_soon_threadsafe(cb, data)
            # elif self.cb_container == 'current':
            #     cb(data)
            # else:
            #     self.cb_queue.put(('run', cb, data))
            self.executor.call_soon(('run', cb, data))

    # def _call_later(self, delay, cb, key):
    #     with self.mutex_lock():
    #         self.running_cbs[key] = self.loop.call_later(delay, cb, key)

    def _delay_call(self, delay, func_name, *args):
        # if self.loop_freq:
        #     with self.heap_lock:
        #         heappush(self.heap, (_time() + delay, func_name, *args))
        # elif self.use_coroutine:
        #     self.loop.call_soon_threadsafe(self._call_later, delay, self.__getattribute__(func_name), *args)
        # else:
        #     with self.heap_lock:
        #         heappush(self.heap, (_time() + delay, func_name, *args))
        #     self.heap_not_empty.set()
        func = self.__getattribute__(func_name)
        return self.executor.call_later(('run', func, *args), delay=delay)

    def _put(self, *args, time_limit=None, update_only=False, **kwargs):
        dic = self._parse(*args, **kwargs)
        key = dic['uid']
        time_limit = time_limit if time_limit is not None else self.time_limit

        if key in self.retain:
            raise KeyError('%s is in progress' % key)
        elif update_only and key not in self.data:
            raise KeyError('%s is not in queue' % key)
        _typ = 'update' if key in self.data else 'put'

        self.data[key] = dic
        self.queue.push(*dic['kvp'], **dic['kw'])

        if self.use_trace:
            self._gen_trace(key)
            self.trace[key][_typ] = datetime.now().strftime('%H:%M:%S.%f')
            self.trace[key]['last_op'] = _typ

        if self.time_limit:
            # if self.loop_freq:
            #     with self.heap_lock:
            #         heappush(self.heap, (_time() + time_limit, 'timeout', key))
            # elif self.use_coroutine:
            #     self.loop.call_soon_threadsafe(self._call_later, time_limit, self.timeout, key)
            # else:
            #     with self.heap_lock:
            #         heappush(self.heap, (_time() + time_limit, 'timeout', key))
            #     self.heap_not_empty.set()

            # self._delay_call(time_limit, 'timeout', key)
            _cb_id = self._delay_call(time_limit, 'timeout', key)
            if key in self.running_cbs:
                self.running_cbs[key]['timeout'] = _cb_id
            else:
                self.running_cbs[key] = {'timeout': _cb_id}

        self.run_callback(dic['put_cb'], dic['kvp'], _typ)
        return key

    def _get(self, key=DEFAULT_MARKER, typ=None):
        kvp = self.queue.pop(key=key)
        dic = self.data[kvp[0]]

        _key = key if key != DEFAULT_MARKER else kvp[0]
        _typ = typ or ('get' if key == DEFAULT_MARKER else 'drop')

        if self.use_trace:
            self.trace[_key][_typ] = datetime.now().strftime('%H:%M:%S.%f')
            self.trace[_key]['last_op'] = _typ

        if self.use_retain and _typ == 'get':
            if len(self.retain) >= self.max_retain:
                _drop_kvp = self.retain.pop()
                self._finalize(_drop_kvp[0], msg='clean')
            self.retain[_key] = dic
            # self.retain[_key] = (dic, None)

            if self.retry_time:
                # if self.loop_freq:
                #     with self.heap_lock:
                #         heappush(self.heap, (_time() + self.retry_time, 'retry', _key))
                # elif self.use_coroutine:
                #     self.loop.call_soon_threadsafe(self._call_later, self.retry_time, self.retry, _key)
                # else:
                #     with self.heap_lock:
                #         heappush(self.heap, (_time() + self.retry_time, 'retry', _key))
                #     self.heap_not_empty.set()

                # self._delay_call(self.retry_time, 'retry', _key)
                _cb_id = self._delay_call(self.retry_time, 'retry', _key)
                if _key in self.running_cbs:
                    self.running_cbs[_key]['retry'] = _cb_id
                else:
                    self.running_cbs[_key] = {'retry': _cb_id}

        self.run_callback(dic['get_cb'], kvp, _typ)

        if not self.use_retain or _typ == 'drop':
            self._finalize(_key, cln=False, msg='ok' if _typ == 'get' else 'drop')

        return dic['kvp']

    def _accept(self, key):
        dic = self.data[key]  # may raise KeyError
        if self.use_trace:
            self.trace[key]['accept'] = datetime.now().strftime('%H:%M:%S.%f')
            self.trace[key]['last_op'] = 'accept'

        self.run_callback(dic['accept_cb'], dic['kvp'], 'accept')

        self._finalize(key, msg='ok')

    def timeout(self, key):
        with self.mutex_lock():
            if key in self.running_cbs:
                self.running_cbs[key].pop('timeout')  # without key check
            if key in self.data:
                dic = self.data[key]
                if self.use_trace:
                    self.trace[key]['timeout'] = datetime.now().strftime('%H:%M:%S.%f')

                self.run_callback(dic.get('timeout_cb', None), dic['kvp'], 'timeout')

                self._finalize(key, msg='timeout')

    def retry(self, key):
        with self.mutex_lock():
            if key in self.running_cbs:
                self.running_cbs[key].pop('retry')  # without key check
            if key in self.data and key in self.retain:
                dic = self.data[key]
                self.retain.pop(key)
                self.queue.push(*dic['kvp'], **dic['kw'])
                if self.use_trace:
                    self.trace[key]['retry'] = datetime.now().strftime('%H:%M:%S.%f')
                    self.trace[key]['last_op'] = 'retry'

                self.not_empty.notify()  # take no account of speed limit, may update later

                self.run_callback(dic.get('retry_cb', None), dic['kvp'], 'retry')

    def _finalize(self, key, cln=True, msg=''):
        if cln:
            if key in self.queue:
                self.queue.pop(key=key)
            elif key in self.retain:
                self.retain.pop(key)

        if self.use_trace and msg:
            self.trace[key]['msg'] = msg

        _dic = self.data.pop(key)
        _trc = self.trace.pop(key) if self.use_trace else {}

        if key in self.running_cbs:
            _rcb = self.running_cbs.pop(key)
            # _rcb.cancel()
            for k in _rcb:
                self.executor.cancel(_rcb[k])

        if self.retry_time:
            self.not_full.notify()

        data = {'uid': _dic['uid'], 'kvp': _dic['kvp'], 'trace': _trc, 'msg': msg}
        self.run_callback(_dic['finalize_cb'], data, 'finalize')


class PriQue(QueBase):
    def _init(self, maxsize, **kwargs):
        self.queue = PriorityQueue()

    def _qsize(self):
        return len(self.queue)

    def _contain(self, *args):
        return False

    def _put(self, *args):
        self.queue.push(*args)

    def _get(self, key=DEFAULT_MARKER, **kwargs):
        return self.queue.popitem()

    def _peek(self, key=DEFAULT_MARKER):
        return self.queue.peek()


class PriDict(QueBase):
    def _init(self, maxsize, **kwargs):
        self.queue = PriorityDict(**kwargs)

    def _qsize(self):
        return len(self.queue)

    def _contain(self, *args):
        return args[0] in self.queue

    def _put(self, *args):
        self.queue.push(*args)

    def _get(self, key=DEFAULT_MARKER, **kwargs):
        return self.queue.pop(key=key)

    def _peek(self, key=DEFAULT_MARKER):
        return self.queue.peek(key=key)

# def _cb_worker(que):
#     while True:
#         try:
#             typ, cb, data = que.get()
#             if typ == 'stop':
#                 break
#             cb(data)
#         except Exception as e:
#             print(type(e), e)
#
#
# def _thd_delay_calls(que, heap, heap_lock, freq=0.1, not_empty: threading.Event = None):
#     while True:
#         _now = _time()
#         _lis = []
#         with heap_lock:
#             _empty_flag = False if heap else True
#             while heap and heap[0][0] < _now:
#                 _lis.append(heappop(heap))
#         for _data in _lis:
#             que.__getattribute__(_data[1])(_data[-1])
#         if _empty_flag:
#             not_empty.wait(1)
#         elif freq:
#             _delay_time = _now + freq - _time()
#             if _delay_time > 0:
#                 _sleep(_delay_time)
#
#
# async def _run_delay_calls(que, heap, heap_lock, freq=0.1):
#     while True:
#         _now = _time()
#         _lis = []
#         with heap_lock:
#             while heap and heap[0][0] < _now:
#                 _lis.append(heappop(heap))
#         for _data in _lis:
#             que.__getattribute__(_data[1])(_data[-1])
#         await asyncio.sleep(_now + freq - _time())
