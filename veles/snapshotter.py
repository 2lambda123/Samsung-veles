"""
Created on May 16, 2014

Copyright (c) 2014, Samsung Electronics, Co., Ltd.
"""


import bz2
import gzip
import lzma
import os
import six
import sys
import time

from veles.pickle2 import pickle
import veles.units as units


if (sys.version_info[0] + (sys.version_info[1] / 10.0)) < 3.3:
    FileNotFoundError = IOError  # pylint: disable=W0622


class Snapshotter(units.Unit):
    """Takes workflow snapshots.

    Defines:
        file_name - the file name of the last snapshot
        time: time of the last snapshot

    Must be defined before initialize():
        suffix - the file name suffix where to take snapshots

    Attributes:
        compress - the compression applied to pickles: None or '', gz, bz2, xz
        interval - take only one snapshot within this run() invocation number
        time_interval - take no more than one snapshot within this time window
    """

    CODECS = {
        None: lambda n, l: open(n, "wb"),
        "": lambda n, l: open(n, "wb"),
        "gz": lambda n, l: gzip.GzipFile(n, "wb", compresslevel=l),
        "bz2": lambda n, l: bz2.BZ2File(n, "wb", compresslevel=l),
        "xz": lambda n, l: lzma.LZMAFile(n, "wb", preset=l)
    }

    def __init__(self, workflow, **kwargs):
        kwargs["view_group"] = kwargs.get("view_group", "SERVICE")
        super(Snapshotter, self).__init__(workflow, **kwargs)
        self.directory = kwargs.get("directory", "/tmp")
        self.prefix = kwargs.get("prefix", "")
        self.compress = kwargs.get("compress", "gz")
        self.compress_level = kwargs.get("compress_level", 9)
        self.interval = kwargs.get("interval", 1)
        self.time_interval = kwargs.get("time_interval", 1)
        self.time = 0
        self._skipped_counter = 0
        self.file_name = ""
        self.suffix = None

    def initialize(self, **kwargs):
        super(Snapshotter, self).initialize(**kwargs)
        self.time = time.time()

    def run(self):
        self._skipped_counter += 1
        if self._skipped_counter < self.interval:
            return
        if time.time() - self.time < self.time_interval:
            return
        ext = ("." + self.compress) if self.compress else ""
        rel_file_name = "%s_%s.%d.pickle%s" % (
            self.prefix, self.suffix, 3 if six.PY3 else 2, ext)
        self.file_name = os.path.join(self.directory, rel_file_name)
        with self._open_file() as fout:
            pickle.dump(self.workflow, fout)
        self.info("Wrote %s" % self.file_name)
        file_name_link = os.path.join(
            self.directory, "%s_current.%d.pickle%s" % (
                self.prefix, 3 if six.PY3 else 2, ext))
        if os.path.exists(file_name_link):
            os.remove(file_name_link)
        os.symlink(rel_file_name, file_name_link)
        self.time = time.time()

    def _open_file(self):
        return Snapshotter.CODECS[self.compress](self.file_name,
                                                 self.compress_level)