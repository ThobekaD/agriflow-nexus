"""
init_loop:      Start a new thread with async event loop

last update:    2020-10-23
"""

import threading
import asyncio

__all__ = ['init_loop', ]


def _create_loop(lp_dic, _is_running: threading.Event):
    lp = asyncio.new_event_loop()
    lp_dic['loop'] = lp
    lp.call_soon(_is_running.set)
    try:
        lp.run_forever()
    finally:
        lp.close()


def init_loop(loop=None):
    if loop is None:
        lp_dic = {'loop': None}
        _is_running = threading.Event()
        threading.Thread(target=_create_loop, args=(lp_dic, _is_running), daemon=True).start()
        _is_running.wait()
        return lp_dic['loop']
    else:
        return loop
