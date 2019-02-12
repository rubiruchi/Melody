import ctypes
import sys
import os
import time
from libs import shared_buf as sb
from defines import *


class shared_buffer(object):
    def __init__(self, bufName, isProxy):
        self.sharedBufName = bufName

        if isProxy:
            self.isProxy = 1
        else:
            self.isProxy = 0

        self.shared_buf = sb
        self.shared_buf.init()

    def open(self):

        result = self.shared_buf.open(self.sharedBufName, self.isProxy)
        return result

    def close(self):
        self.shared_buf.close()

    def read(self):
        ret = self.shared_buf.read(self.sharedBufName, self.isProxy)
        time.sleep(0.1)
        return ret

    def write(self, msg, dstID=PROXY_NODE_ID):
        return self.shared_buf.write(self.sharedBufName, str(msg), len(str(msg)), self.isProxy, dstID)


class shared_buffer_array(object):
    def __init__(self):
        self.sharedBufs = []
        self.sharedBufNames = []
        self.shared_buf = sb
        self.shared_buf.init()

    def open(self, bufName, isProxy):

        if isProxy:
            self.sharedBufs.append((bufName, 1))
        else:
            self.sharedBufs.append((bufName, 0))

        self.sharedBufNames.append(bufName)
        result = self.shared_buf.open(bufName, isProxy)
        return result

    def close(self):
        self.shared_buf.close()

    def read(self, bufName):
        idx = self.sharedBufNames.index(bufName)
        assert (idx >= 0 and idx < len(self.sharedBufNames))
        isProxy = self.sharedBufs[idx][1]

        return self.shared_buf.read(bufName, isProxy)

    def read_until(self, bufName, cool_off_time=0.01):
        while True:
            id, msg = self.read(bufName)
            if msg != '':
                return id, msg
            time.sleep(cool_off_time)

    def write(self, bufName, msg, dstID=PROXY_NODE_ID):
        idx = self.sharedBufNames.index(bufName)
        assert (idx >= 0 and idx < len(self.sharedBufNames))
        isProxy = self.sharedBufs[idx][1]

        return self.shared_buf.write(bufName, str(msg), len(str(msg)), isProxy, dstID)
