from collections import UserDict, UserList
import pickle
import plyvel


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
    def __init__(self, db: PlyvelDict, key: str, initial_data):
        self._key = key.encode()  # Pre-encode key to reduce repetition
        self._db = db

        super().__init__(initial_data)

    def __setitem__(self, key: str, value):
        super().__setitem__(key, value)
        self._db.put(self._key, pickle.dumps(self.data))

    def __delitem__(self, key: str):
        super().__delitem__(key)
        self._db.put(self._key, pickle.dumps(self.data))

    def __repr__(self):
        return f'{type(self).__name__}({self.data})'


class PlyvelDictResult(PlyvelResult, UserDict):
    """
    Intermediate value for dictionaries returned by `PlyvelDict`
    TODO: deep nesting
    """
    pass


class PlyvelListResult(PlyvelResult, UserList):
    """
    Intermediate value for lists returned by `PlyvelDict`
    TODO: deep nesting
    """
    pass