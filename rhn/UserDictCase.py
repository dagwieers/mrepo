# This file implements a case insensitive dictionary on top of the
# UserDict standard python class
#
# Copyright (c) 2001-2005, Red Hat Inc.
# All rights reserved.
#
# $Id: UserDictCase.py 191145 2010-03-01 10:21:24Z msuchy $

import string

from types import StringType
from UserDict import UserDict

# A dictionary with case insensitive keys
class UserDictCase(UserDict):
    def __init__(self, data = None):
        self.kcase = {}
        UserDict.__init__(self, data)
    # some methods used to make the class work as a dictionary
    def __setitem__(self, key, value):
        lkey = key
        if isinstance(key, StringType):
            lkey = string.lower(key)
        self.data[lkey] = value
        self.kcase[lkey] = key
    def __getitem__(self, key):
        if isinstance(key, StringType):
            key = string.lower(key)
        if not self.data.has_key(key):
            return None
        return self.data[key]   
    def __delitem__(self, key):
        if isinstance(key, StringType):
            key = string.lower(key)
        del self.data[key]
        del self.kcase[key]
    get = __getitem__
    def keys(self):
        return self.kcase.values()
    def items(self):
        return self.get_hash().items()
    def has_key(self, key):
        if isinstance(key, StringType):
            key = string.lower(key)
        return self.data.has_key(key)
    def clear(self):
        self.data.clear()
        self.kcase.clear()        
    # return this data as a real hash
    def get_hash(self):
        return reduce(lambda a, (ik, v), hc=self.kcase:
                      a.update({ hc[ik] : v}) or a, self.data.items(), {})
                              
    # return the data for marshalling
    def __getstate__(self):
        return self.get_hash()
    # we need a setstate because of the __getstate__ presence screws up deepcopy
    def __setstate__(self, state):
        self.__init__(state)
    # get a dictionary out of this instance ({}.update doesn't get instances)
    def dict(self):
        return self.get_hash()
    def update(self, dict):
        for (k, v) in dict.items():
            lk = k
            if isinstance(k, StringType):
                lk = string.lower(k)
            self.data[lk] = v
            self.kcase[lk] = k
    # Expose an iterator. This would normally fail if there is no iter()
    # function defined - but __iter__ will never be called on python 1.5.2
    def __iter__(self):
        return iter(self.data)
