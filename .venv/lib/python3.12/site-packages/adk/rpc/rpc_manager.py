import threading
import traceback
from itertools import count
from multiprocessing.managers import BaseManager

from adk.utils import TaskQue, ThreadCron
from .rpc_cfg import rpc_connect_args

__all__ = ['TaskManager', 'start_rpc_server', 'start_rpc_worker', 'rpc_client', 'clt']


class TaskManager:
    def __init__(self, retry_time=5, time_limit=60):
        self.retry_time = retry_time
        self.time_limit = time_limit

        self.uid_maker = (str(i) for i in count())

        self.mutex = threading.Lock()
        self.executor = ThreadCron()

        self.que_dic = {'default': self.__create_que()}
        self.mtd_dic = {'default': set()}
        self.res_que = self.__create_que()

        self.events = {}
        self.data = {}

        threading.Thread(target=self.__receiver, daemon=True).start()

    def __receiver(self):
        while True:
            key, res = self.res_que.get()
            self.res_que.accept(key)
            self.__receive(key, res)

    def __receive(self, key, res):
        with self.mutex:
            if key in self.events:
                self.data[key] = res
                self.events[key].set()

    def __create_que(self):
        return TaskQue(retry_time=self.retry_time, time_limit=self.time_limit, auto_key=False, executor=self.executor)
        # return TaskQue(retry_time=self.retry_time, time_limit=self.time_limit, auto_key=False)

    def get_work_que(self, topic='default', methods=None, overwrite=True):
        methods = set(methods or {})
        with self.mutex:
            if topic in self.mtd_dic:
                if methods != self.mtd_dic[topic]:
                    if not overwrite:
                        raise ValueError('Methods do not match')
                    else:
                        self.mtd_dic[topic] = methods
            else:
                self.que_dic[topic] = self.__create_que()
                self.mtd_dic[topic] = methods
            return self.que_dic[topic]

    def get_res_que(self):
        return self.res_que

    def __send_to_work(self, data, prior=None, timeout=None, topic='default'):
        topic = data.get('topic', topic)
        with self.mutex:
            key = self.uid_maker.__next__()
            self.events[key] = threading.Event()
            self.que_dic[topic].put(key, data, prior=prior, timeout=timeout)
        return key

    def __clean_res(self, key):
        with self.mutex:
            if key in self.events:
                self.events.pop(key)
            if key in self.data:
                self.data.pop(key)

    def run(self, data, *args, prior=None, timeout=None, topic='default', **kwargs):
        data = {'method': data, 'args': args, 'kwargs': kwargs} if isinstance(data, str) else data
        res = {'message': 'method not found', 'result': None}
        topic = data.get('topic', topic)
        if topic in self.mtd_dic and data.get('method') in self.mtd_dic[topic]:
            key = self.__send_to_work(data, prior=prior, timeout=timeout, topic=topic)  # todo: check timeout design
            _flag = self.events[key].wait(self.time_limit if timeout is None else timeout)
            res = self.data[key] if _flag else {'message': 'timeout', 'result': None}
            self.__clean_res(key)
        return res

    def __worker_example(self):
        que_in = self.get_work_que(topic='test', methods=['print'])
        que_ou = self.res_que
        while True:
            key, data = que_in.get()
            que_in.accept(key)
            print('work for', key, data)
            que_ou.put(key, {'message': 'ok', 'result': None})

    def run_worker_example(self):
        threading.Thread(target=self.__worker_example, daemon=True).start()


_implemented_methods = (
    'set', 'get', 'clear',
    'get_work_que', 'get_res_que',
    'run', 'get_rpc_proxy'
)


class RPCServer(BaseManager):
    pass


class RPCClient(BaseManager):
    pass


for _m in _implemented_methods:
    RPCClient.register(_m)


def rpc_client(server_id=''):
    client = RPCClient(*rpc_connect_args(server_id=server_id))
    client.connect()
    return client


def start_rpc_worker(methods_map: dict = None, *, topic='default', server_id='', overwrite=True, **kwargs):
    methods_map = methods_map or kwargs
    if methods_map:
        methods = set(methods_map.keys())
        clt = rpc_client(server_id=server_id)
        que_in = clt.get_work_que(topic=topic, methods=methods, overwrite=overwrite)
        que_ou = clt.get_res_que()
        while True:
            try:
                key, data = que_in.get(timeout=1)
            except TaskQue.Empty:
                # print(traceback.format_exc())
                continue
            que_in.accept(key)
            mtd = data.get('method')
            args = data.get('args', [])
            kwargs = data.get('kwargs', {})
            print('work for:', key, data)
            try:
                res = methods_map[mtd](*args, **kwargs)
                que_ou.put(key, {'message': 'ok', 'result': res})
            except Exception as e:
                print(traceback.format_exc())
                que_ou.put(key, {'message': 'error', 'result': None})


class MethodsProxy:
    def __init__(self, cache_dic, task_mng):
        self.cache_dict = cache_dic
        self.task_manager = task_mng

    def set(self, k, v):
        self.cache_dict.__setitem__(k, v)

    def get(self, k):
        return self.cache_dict.get(k)

    def clear(self):
        self.cache_dict.clear()

    def run(self, *args, **kwargs):
        return self.task_manager.run(*args, **kwargs)

    # def get_work_que(self, topic='default', methods=None, overwrite=True):
    #     return self.task_manager.get_work_que(topic=topic, methods=methods, overwrite=overwrite)
    #
    # def get_res_que(self):
    #     return self.task_manager.get_res_que()


def start_rpc_server(retry_time=3, time_limit=30, server_id='default'):
    _task_manager = TaskManager(retry_time=retry_time, time_limit=time_limit)
    _cache_dict = {}

    # RPCServer.register('set', _cache_dict.__setitem__)
    # RPCServer.register('get', _cache_dict.get)
    # RPCServer.register('clear', _cache_dict.clear)
    RPCServer.register('get_work_que', _task_manager.get_work_que)
    RPCServer.register('get_res_que', _task_manager.get_res_que)
    # RPCServer.register('run', _task_manager.run)

    proxy = MethodsProxy(_cache_dict, _task_manager)
    # for mtd in ('set', 'get', 'clear', 'get_work_que', 'get_res_que', 'run',):
    for mtd in ('set', 'get', 'clear', 'run',):
        RPCServer.register(mtd, proxy.__getattribute__(mtd))

    RPCServer.register('get_rpc_proxy', lambda: proxy)

    print('RPC Server starting...')
    RPCServer(*rpc_connect_args(server=True, server_id=server_id)).get_server().serve_forever()


class RPCClt:
    def __init__(self, server_id='default'):
        self.server_id = server_id
        self.clt_raw = None
        self.clt = None
        self.is_connected = False

    def set_server_id(self, server_id):
        self.server_id = server_id
        return self

    def __setitem__(self, key, value):
        self.set(key, value)

    def __getitem__(self, key):
        return self.get(key)

    def check_connect(self):
        if not self.is_connected:
            self.clt_raw = RPCClient(*rpc_connect_args(server_id=self.server_id))
            self.clt_raw.connect()
            self.clt = self.clt_raw.get_rpc_proxy()
            self.is_connected = True
        return self

    def set(self, k, v):
        self.check_connect()
        self.clt.set(k, v)

    def get(self, k):
        self.check_connect()
        # return self.clt.get(k)._getvalue()
        return self.clt.get(k)

    def clear(self):
        self.check_connect()
        self.clt.clear()

    def run(self, data, *args, prior=None, timeout=None, topic='default', **kwargs):
        self.check_connect()
        try:
            # res = self.clt.run(data, *args, prior=prior, timeout=timeout, topic=topic, **kwargs)._getvalue()
            res = self.clt.run(data, *args, prior=prior, timeout=timeout, topic=topic, **kwargs)
            return res['result']
        except Exception:
            print(traceback.format_exc())

    def get_work_que(self, topic='default', methods=None, overwrite=True):
        self.check_connect()
        return self.clt_raw.get_work_que(topic=topic, methods=methods, overwrite=overwrite)

    def get_res_que(self):
        self.check_connect()
        return self.clt_raw.get_res_que()

    def get_rpc_proxy(self):
        self.check_connect()
        return self.clt


clt = RPCClt()
