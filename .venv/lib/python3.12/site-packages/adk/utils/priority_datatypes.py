"""
Priority Queue & Dict, extension datatype of heap

main usage:
    push:   push the data with priority into the container(queue or dict)
    pop:    pop and return the data with lowest priority from the container
    peek:   return the data with lowest priority

difference:
    PriorityQueue:          push(data, priority), pop return (data, priority)
    SimplePriorityQueue:    push(priority), pop return priority
    PriorityDict:           push(key, data, priority), pop return (key, data, priority)
    SimplePriorityDict:     push(key, priority), pop return (key, priority)

    *Dict:  PriorityDict and SimplePriorityDict can use just like built in dict

todo:   improve document

last update:    2020-10-23
"""

from collections.abc import MutableMapping
from itertools import count

__all__ = ['PriorityQueue', 'PriorityDict', 'SimplePriorityQueue', 'SimplePriorityDict', 'DEFAULT_MARKER']

# DEFAULT_MARKER = object()
DEFAULT_MARKER = '--+--<<==##** from adk **##==>>--+--'


class MinMaxMarker:
    def __init__(self, is_min=True):
        self.is_min = is_min

    def __eq__(self, other):
        return self is other

    def __le__(self, other):
        return self.is_min

    def __lt__(self, other):
        return self is not other and self.is_min

    def __ge__(self, other):
        return not self.is_min

    def __gt__(self, other):
        return self is not other and not self.is_min

    def __repr__(self):
        return 'Min' if self.is_min else 'Max'


class PriorityQueue:
    """
    Parameters:
        value_is_prior: value is priority or not
        prior_key:      if not None, priority will be value[prior_key]
        format_in:      when got only 1 argument in push, it is tuple or not
        format_ou:      the output is just like input or format output,
                        i.e. when missing prior, output is 'value' or ('value', None)
        none_is_less:   used in compare priority when None v.s. others
        complex_prior:  used when priority likes 1, (1, 2, None), [0, None, 3] ...
        empty_return:   the value returned when Index & Key Errors raised, no default value
    Main Functions:
        push(value[, priority])     insert or update data
        pop() & pop_wrap()          get and then delete the lowest priority data
        peek() & peek_wrap()        get the lowest priority data
        get() & get_wrap()          = peek() & peek_wrap(), for consistent API with subclasses
        popitem() & popitem_wrap()  = pop() & pop_wrap(), for consistent API with subclasses
        f                           queue.f = queue with format_in=True and format_ou=True
    Other Functions:
        peek_prior()                    get the lowest priority, raise Index Error when empty
        set_empty_return(empty_return)  reset parameter empty_return, can use no value (not None)
        extend(values)                  for v in values: push(v or *v)
        to_list() & to_list_wrap()      return all data in list (use pop or pop_wrap)
    Notes:
        main functions can set keyword argument "default" to avoid Index & Key Errors
        function with _wrap will return: (key, value, raw_priority, modified priority, index)
        parent: ((i - 1) >> 1)
        left:   ((i << 1) + 1)
        right:  ((i + 1) << 1)
    """

    __min_marker = MinMaxMarker(is_min=True)
    __max_marker = MinMaxMarker(is_min=False)

    def __init__(self, *args, maxsize=0, value_is_prior=False, prior_key=None,
                 format_in=False, format_ou=False,
                 none_is_less=False, complex_prior=False,
                 empty_return=DEFAULT_MARKER,
                 **kwargs):
        self._count = count()
        self.heap = []
        self.var_idx = 0

        self.maxsize = maxsize
        self.v_is_p = value_is_prior
        self.p_key = prior_key
        self.no_ind_prior = bool(prior_key is not None or value_is_prior)

        self._format_in = format_in
        self._format_ou = format_ou

        self.none_is_less = none_is_less
        self._none_wrap = self.__min_marker if none_is_less else self.__max_marker
        self.complex_prior = complex_prior

        self._empty_return = empty_return
        self._init(*args, **kwargs)

        if '_F_Wrap' not in self.__class__.__dict__:
            self.__class__._F_Wrap = type('_F_Wrap', (self.__class__,), {
                '__init__': lambda *a, **kw: None,
                'format_in': lambda *a, **kw: True,
                'format_ou': lambda *a, **kw: True,
            })

        self.f = self.__class__._F_Wrap()
        self.f.__dict__ = self.__dict__

    def _init(self, *args, **kwargs):
        if len(args) > 1:
            raise TypeError('extend expected at most 1 arguments, got %d' % len(args))
        if args:
            self.extend(args[0])

    def format_in(self):
        return self._format_in

    def format_ou(self):
        return self._format_ou

    def extend(self, values):
        if self.p_key:
            for v in values:
                self.push(v)
        else:
            for v in values:
                self.push(*v)

    def to_list(self):
        return [self.pop() for _ in range(len(self))]

    def to_list_wrap(self):
        return [self.pop_wrap() for _ in range(len(self))]

    def set_empty_return(self, empty_return=DEFAULT_MARKER):
        self._empty_return = empty_return

    def _default_or_error(self, default, errors):
        if default == DEFAULT_MARKER:
            if self._empty_return == DEFAULT_MARKER:
                raise errors
            else:
                return self._empty_return
        else:
            return default

    # args: i.e. [key,] value
    def _wrap(self, *args, prior=DEFAULT_MARKER):
        if self.no_ind_prior:
            prior = prior if prior != DEFAULT_MARKER else args[-1] if self.v_is_p else args[-1][self.p_key]
            prior_wrap = self._prior_wrap(prior)
            # return [*args, prior_wrap, len(self)]
        else:
            prior = None if prior == DEFAULT_MARKER else prior
            prior_wrap = self._prior_wrap(prior)
            # return [*args, prior, prior_wrap, len(self)]
        return [*args, prior, prior_wrap, len(self)]

    def _unwrap(self, wrapper, fmt=DEFAULT_MARKER, skip=0):
        fmt = self.format_ou() if fmt == DEFAULT_MARKER else fmt
        idx = self.var_idx

        if fmt:
            res = (*wrapper[:idx], wrapper[idx][idx]) if self.no_ind_prior else \
                (*wrapper[:idx], wrapper[idx][idx], wrapper[idx + 1])
            if skip:
                res = res[skip:]
            if len(res) == 1:
                res = res[0]
        else:
            res = wrapper[idx]
            if skip:
                res = res[skip:]
            if len(res) == 1:
                res = res[0]
            elif res[-1] is self._none_wrap:
                res = tuple(d for d in res if d is not self._none_wrap)
        return res

    def _prior_wrap(self, prior):
        _cnt = self._count.__next__()
        if self.complex_prior and isinstance(prior, (tuple, list)):
            _pri = ((self._none_wrap if p is None else p for p in prior), _cnt) if prior else self._none_wrap, _cnt
        else:
            _pri = (self._none_wrap if prior is None else prior), _cnt
        return _pri

    def peek_prior(self):
        return self.heap[0][-3]

    @staticmethod
    def _prior_lt(a, b):
        try:
            return a < b
        except TypeError:
            return a[-1] < b[-1]

    def _lt(self, pos_a, pos_b):
        return self._prior_lt(self.heap[pos_a][-2], self.heap[pos_b][-2])

    def _update_pos(self, idx: int, value):
        # assert isinstance(idx, int)
        self.heap[idx] = value
        self.heap[idx][-1] = idx

    def _siftdown(self, start_pos, pos):
        new_item = self.heap[pos]
        # Follow the path to the root, moving parents down until finding a place
        # new_item fits.
        while pos > start_pos:
            parent_pos = (pos - 1) >> 1
            parent = self.heap[parent_pos]
            if self._prior_lt(new_item[-2], parent[-2]):  # no _wrap_prior
                self._update_pos(pos, parent)
                pos = parent_pos
                continue
            break
        self._update_pos(pos, new_item)

    def _siftup(self, pos):  # min_heapify
        end_pos = len(self.heap)
        start_pos = pos
        new_item = self.heap[pos]
        # Bubble up the smaller child until hitting a leaf.
        # child_pos = 2 * pos + 1
        child_pos = (pos << 1) + 1  # leftmost child position
        while child_pos < end_pos:
            # Set child_pos to index of smaller child.
            right_pos = child_pos + 1
            # if right_pos < end_pos and not self.heap[child_pos] < self.heap[right_pos]:
            if right_pos < end_pos and self._lt(right_pos, child_pos):
                child_pos = right_pos
            # Move the smaller child up.
            self._update_pos(pos, self.heap[child_pos])
            pos = child_pos
            child_pos = (pos << 1) + 1
        # The leaf at pos is empty now.  Put new_item there, and bubble it up
        # to its final resting place (by sifting its parents down).
        # self.heap[pos] = new_item
        self._update_pos(pos, new_item)
        self._siftdown(start_pos, pos)

    def popitem_wrap(self):
        wrapper = self.heap[0]
        if len(self.heap) == 1:
            self.heap.pop()
        else:
            self._update_pos(0, self.heap.pop(-1))
            self._siftup(0)
        self._clean_ref(wrapper)
        return wrapper

    def popitem(self):
        wrapper = self.popitem_wrap()
        return self._unwrap(wrapper)

    def peek_wrap(self, default=DEFAULT_MARKER):
        try:
            return self.heap[0]
        except IndexError as errors:
            return self._default_or_error(default, errors)

    def peek(self, default=DEFAULT_MARKER):
        try:
            return self._unwrap(self.heap[0])
        except IndexError as errors:
            return self._default_or_error(default, errors)

    def push(self, *args, prior=DEFAULT_MARKER, fmt=DEFAULT_MARKER):
        args_ln = len(args)
        if not 0 < args_ln < 3:
            raise TypeError('push expected 1~2 arguments, got %d' % args_ln)
        if self.no_ind_prior and args_ln > 1:
            raise TypeError('push expected 1 argument if prior_is_value or prior_key is not None, got %d' % args_ln)

        fmt_in = self.format_in() if fmt == DEFAULT_MARKER else fmt

        if args_ln == 1:
            if fmt_in and not self.no_ind_prior:  # confirm args[0] is iterable
                args = args[0]
                if len(args) > 1:
                    prior = prior if prior != DEFAULT_MARKER else args[-1]
                else:
                    args = (args[0], self._none_wrap)
                    prior = prior if prior != DEFAULT_MARKER else None
            else:
                prior = prior if prior != DEFAULT_MARKER else (
                    args[0] if self.v_is_p else args[0][self.p_key]) if self.no_ind_prior else None
        else:
            prior = prior if prior != DEFAULT_MARKER else args[-1]

        if self.maxsize and len(self) >= self.maxsize:
            self.pop()

        self.heap.append(self._wrap(args, prior=prior))
        self._siftdown(0, len(self) - 1)

    def pop_wrap(self):
        return self.popitem_wrap()

    def pop(self):
        return self.popitem()

    def _clean_ref(self, wrapper):
        pass

    def __len__(self):
        return len(self.heap)

    def __iter__(self):
        return iter(self.heap)

    def clear(self):
        self.heap.clear()


class PriorityDict(PriorityQueue, MutableMapping):
    """
    Some usages like dict:
        dict[key] = value   -->>    pri_dict[key] = (value, priority)  # normally, a little different !!!
                                    pri_dict[key] = value  # if value_is_prior or prior_key is not None
        value = dict[key]   -->>    value = pri_dict[key]
        del dict[key]       -->>    del pri_dict[key]
        methods like pop(key), popitem(), get(key, default=value)...
    Parameters:
        value_is_prior: value is priority or not
        prior_key:      if not None, priority will be value[prior_key]
        format_in:      when got only 1 argument in push or __setitem__, it is tuple or not
        format_ou:      the output is just like input or format output,
                        i.e. when missing prior, output is (key, value) or (key, value, None)
        none_is_less:   used in compare priority when None v.s. others
        complex_prior:  used when priority likes 1, (1, 2, None), [0, None, 3] ...
        empty_return:   the value returned when Index & Key Errors raised, no default value
    Main Functions:
        push(key, value[, priority])    insert or update data
        get(key) & get_wrap(key)        query data
        pop(key) & pop_wrap(key)        get and then delete by key, if no argument pop() = popitem()
        popitem() & popitem_wrap()      get and then delete the lowest priority data
        peek() & peek_wrap()            get the lowest priority data
        f                               dic_foo.f = dic_foo with format_in=True and format_ou=True
    Other Functions:
        peek_prior()                    get the lowest priority, raise Index Error when empty
        set_empty_return(empty_return)  reset parameter empty_return, can use no value (not None)
        extend(values)                  for v in values: push(v or *v)
        update(*args, **kwargs)         like update in dict
        to_list() & to_list_wrap()      return all data in list (use pop or pop_wrap)
    Notes:
        main functions can set keyword argument "default" to avoid Index & Key Errors
        function with _wrap will return: (key, value, raw_priority, modified priority, index)
        parent: ((i - 1) >> 1)
        left:   ((i << 1) + 1)
        right:  ((i + 1) << 1)
    """

    class PriorSetter:
        def __init__(self, pri_dic):
            self.pri_dic: PriorityDict = pri_dic

        def __getitem__(self, key):
            return self.pri_dic.dic[key][-3]

        def __setitem__(self, key, prior):
            return self.pri_dic.__setitem__(key, prior=prior)

        def __repr__(self):
            return {k: self.pri_dic.dic[k][-3] for k in self.pri_dic}.__repr__()

    def _init(self, *args, **kwargs):
        self.var_idx = 1
        self.dic = {}
        self.update(*args, **kwargs)
        self.p = self.PriorSetter(self)

    def _clean_ref(self, wrapper):
        del self.dic[wrapper[0]]

    def extend(self, values):
        for v in values:
            self.push(*v)

    def get_wrap(self, key, default=DEFAULT_MARKER):
        try:
            return self.dic[key]
        except (KeyError, IndexError) as errors:
            return self._default_or_error(default, errors)

    def get(self, key, default=DEFAULT_MARKER):
        try:
            return self[key]
        except (KeyError, IndexError) as errors:
            return self._default_or_error(default, errors)

    def peek_wrap(self, key=DEFAULT_MARKER, default=DEFAULT_MARKER):
        try:
            return self.heap[0] if key == DEFAULT_MARKER else self.dic[key]
        except (KeyError, IndexError) as errors:
            return self._default_or_error(default, errors)

    def peek(self, key=DEFAULT_MARKER, default=DEFAULT_MARKER):
        try:
            return self._unwrap(self.heap[0]) if key == DEFAULT_MARKER else \
                self._unwrap(self.dic[key])
        except (KeyError, IndexError) as errors:
            return self._default_or_error(default, errors)

    def pop_wrap(self, key=DEFAULT_MARKER, default=DEFAULT_MARKER):
        try:
            if key == DEFAULT_MARKER:
                return self.popitem_wrap()
            else:
                value = self.get_wrap(key)
                del self[key]
                return value
        except (KeyError, IndexError) as errors:
            return self._default_or_error(default, errors)

    def pop(self, key=DEFAULT_MARKER, default=DEFAULT_MARKER):
        try:
            if key == DEFAULT_MARKER:
                return self.popitem()
            else:
                value = self[key]
                del self[key]
                return value
        except (KeyError, IndexError) as errors:
            return self._default_or_error(default, errors)

    def push(self, *args, prior=DEFAULT_MARKER, fmt=DEFAULT_MARKER):
        args_ln = len(args)
        if not 0 < args_ln < 4:
            raise TypeError('push expected 1~3 arguments, got %d' % args_ln)
        if self.no_ind_prior and args_ln > 2:
            raise TypeError('push expected 2 arguments if prior_is_value or prior_key is not None, got %d' % args_ln)

        fmt_in = self.format_in() if fmt == DEFAULT_MARKER else fmt

        if args_ln == 1 and fmt_in:
            args = args[0]

        key = args[0]

        if len(args) == 1:
            if prior == DEFAULT_MARKER:
                if key in self.dic:
                    return
                else:
                    prior = None
            value = DEFAULT_MARKER
        else:
            value = args  # check format_ou move to __setitem__
            prior = prior if prior != DEFAULT_MARKER else args[-1] if len(args) == 3 \
                else (args[-1] if self.v_is_p else args[-1][self.p_key]) if self.no_ind_prior else self._none_wrap

        if self.maxsize and len(self) >= self.maxsize and key not in self.dic:
            self.pop()

        self.__setitem__(key, value, prior=prior)  # assert prior is not default

    def __iter__(self):
        return iter(self.dic)

    def clear(self):
        self.heap.clear()
        self.dic.clear()

    def __getitem__(self, key):
        return self._unwrap(self.dic[key], skip=1)

    def __setitem__(self, key, value=DEFAULT_MARKER, prior=DEFAULT_MARKER, fmt=DEFAULT_MARKER):
        _not_new = key in self.dic

        if prior != DEFAULT_MARKER:  # from push
            _dft_pri = prior is self._none_wrap
            if not _not_new:
                if value == DEFAULT_MARKER:
                    if self.p_key:
                        raise ValueError('expected not only key')
                    value = (key, None)
            elif _dft_pri:  # value is (key, value) and prior is self._none_wrap
                v_saved = self.dic[key][1]
                if len(v_saved) == 3:
                    value = (*value, v_saved[-1])
        elif self.no_ind_prior:
            _dft_pri = False
            value = (key, value)
        elif self.format_in() if fmt == DEFAULT_MARKER else fmt:  # que[key] = (value, [prior])
            _dft_pri = len(value) == 1  # if fmt, assert value is tuple
            if _dft_pri:
                value = (key, value[0], self._none_wrap)
            else:
                value = (key, *value[-2:])
                prior = value[-1]
        else:  # que[key] = value
            _dft_pri = True
            if _not_new:
                v_saved = self.dic[key][1]
                value = (key, value) if len(v_saved) < 3 else (key, value, v_saved[-1])
            else:
                value = (key, value)

        if value == DEFAULT_MARKER:
            v_saved = self.dic[key][1]
            value = v_saved if len(v_saved) < 3 else (*v_saved[:2], prior)

        wrapper = self._wrap(key, value, prior=prior)

        if _not_new and (_dft_pri or self.dic[key][-3] == wrapper[-3]):
            self.dic[key][1] = wrapper[1]
        else:
            if _not_new:
                self.pop(key)
            self.dic[key] = wrapper
            self.heap.append(wrapper)
            self._siftdown(0, len(self) - 1)

    def __delitem__(self, key):
        wrapper = self.dic[key]
        pos = wrapper[-1]
        while pos:
            parent_pos = (pos - 1) >> 1
            self._update_pos(pos, self.heap[parent_pos])
            pos = parent_pos
        self.heap[pos] = wrapper  # pos=0 and wrapper will dropped, no need update index
        self.popitem()

    def __repr__(self):
        return dict(self).__repr__()


class SimplePriorityQueue(PriorityQueue):
    def __init__(self, *args, **kwargs):
        if 'value_is_prior' in kwargs:
            super().__init__(*args, **kwargs)
        else:
            super().__init__(*args, value_is_prior=True, **kwargs)


class SimplePriorityDict(PriorityDict):
    def __init__(self, *args, **kwargs):
        if 'value_is_prior' in kwargs:
            super().__init__(*args, **kwargs)
        else:
            super().__init__(*args, value_is_prior=True, **kwargs)
