#
# linter.py
# Linter for SublimeLinter3, a code checking framework for Sublime Text 3
#
# Written by Alec Thomas
# Copyright (c) 2014 Alec Thomas
#
# License: MIT
#

"""This module exports the Gometalinter plugin class."""

from os import listdir
from os.path import dirname
from SublimeLinter.lint import Linter, util, highlight
from subprocess import check_output


class Gometalinter(Linter):
    """Provides an interface to gometalinter."""

    syntax = ('go', 'gosublime-go')
    cmd = 'gometalinter * .'
    regex = r'(?:[^:]+):(?P<line>\d+):(?P<col>\d+)?:(?:(?P<warning>warning)|(?P<error>error)):\s*(?P<message>.*)'
    error_stream = util.STREAM_BOTH
    default_type = highlight.ERROR

    def run(self, cmd, code):
        files = [f for f in listdir(dirname(self.filename)) if f.endswith('.go')]
        return self.tmpdir(cmd, files, code)
