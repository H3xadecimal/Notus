from collections import UserDict, UserList
from typing import List, Union
from functools import wraps
import pickle
import plyvel


def maybe_decode_all(list_: List[Union[int, bytes]]) -> List[Union[int, str]]:
    return [x.decode() if isinstance(x, bytes) else x for x in list_]


def call_super_and_put(func):
    @wraps(func)
    def decorator(self, *args, **kwargs):
        ret = getattr(super(self.__class__, self), func.__name__)(*args, **kwargs)
        self._put()
        
        return ret

    return decorator


class PlyvelDict:
    """
    Wrapper for plyvel to emulate a dictionary interface to LevelDB.
    """

    def __init__(self, path: str):
        self._db = plyvel.DB(path, create_if_missing=True)

    def _get(self, key: str):
        """
        Private get function, for removing intermediate `self._db` stuff + auto encoding keys.
        """
        return self._db.get(key.encode())

    def __del__(self):
        self._db.close()

    def __getitem__(self, key: str):
        item = self._get(key)

        if item is None:
            raise KeyError(key)

        item = pickle.loads(item)

        if isinstance(item, dict):
            return PlyvelDictResult(self._db, key, item)
        elif isinstance(item, list):
            return PlyvelListResult(self._db, key, item)

        return item

    def __setitem__(self, key: str, value):
        self._db.put(key.encode(), pickle.dumps(value))

    def __delitem__(self, key: str):
        self._db.delete(key.encode())

    def __contains__(self, key: str):
        return self._get(key) is not None

    def __iter__(self):
        return self._db.iterator()

    def __len__(self):
        return sum(1 for _ in self._db.iterator(include_value=False))

    def __reversed__(self):
        return self._db.iterator(reverse=True)

    def __repr__(self):
        return f'{self.__class__.__name__}({self._db.name!r}{" closed" if self._db.closed else ""})'


class PlyvelResult:
    """
    Base implementation of proxies for some collections returned by PlyvelDict.
    """
    def __init__(self, db: PlyvelDict, key: str, initial_data, keys: List[bytes] = []):
        self._keys = keys
        self._key = key.encode() if isinstance(key, str) else key # Pre-encode key to reduce repetition
        self._db = db

        super().__init__(initial_data)

    def _put(self):
        if not self._keys:
            self._db.put(self._key, pickle.dumps(self.data))
        else:
            self._db.put(self._keys[0], pickle.dumps(self.data))

    def __getitem__(self, key):
        item = super().__getitem__(key)

        if isinstance(item, dict):
            return PlyvelDictResult(self._db, key, item, self._keys + [self._key])
        elif isinstance(item, list):
            return PlyvelListResult(self._db, key, item, self._keys + [self._key])
        else:
            return item

    def __setitem__(self, key: str, value):
        super().__setitem__(key, value)

        if not self._keys:
            self._db.put(self._key, pickle.dumps(self.data))
        else:
            item = pickle.loads(self._db.get(self._keys[0]))
            keys = maybe_decode_all(self._keys + [self._key])
            ref = item

            for key_ in keys[1:]:
                ref = ref[key_]

            ref[key] = value
            self._db.put(self._keys[0], pickle.dumps(item))            

    def __delitem__(self, key: str):
        super().__delitem__(key)
        
        if not self._keys:
            self._db.put(self._key, pickle.dumps(self.data))
        else:
            item = pickle.loads(self._db.get(self._keys[0]))
            keys = maybe_decode_all(self._keys + [self._key])
            ref = item

            for key_ in keys[1:]:
                ref = ref[key_]

            del ref[key]
            self._db.put(self._keys[0], pickle.dumps(item))

    def __repr__(self):
        return f'{type(self).__name__}({self.data})'

    def to_original(self):
        """Get unwrapped data."""
        return self.data


class PlyvelDictResult(PlyvelResult, UserDict):
    """
    Intermediate value for dictionaries returned by `PlyvelDict`
    """
    @call_super_and_put
    def pop(): pass

    @call_super_and_put
    def popitem(): pass

    @call_super_and_put
    def clear(): pass

    @call_super_and_put
    def update(): pass


class PlyvelListResult(PlyvelResult, UserList):
    """
    Intermediate value for lists returned by `PlyvelDict`
    """
    @call_super_and_put
    def append(): pass

    @call_super_and_put
    def insert(): pass

    @call_super_and_put
    def pop(): pass

    @call_super_and_put
    def remove(): pass

    @call_super_and_put
    def clear(): pass

    @call_super_and_put
    def reverse(): pass

    @call_super_and_put
    def sort(): pass

    @call_super_and_put
    def extend(): pass

    # TODO: maybe also do this for stuff like += and -=