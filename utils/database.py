from typing import Any
import pickle
import plyvel

class PlyvelDict:
    # TODO: maybe add a proxy helper for modifying nested keys, (e.g. db['foo']['bar'] = 'thing'): set, del
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

        return item

    def __setitem__(self, key: str, value: Any):
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