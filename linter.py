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

import os

from SublimeLinter.lint import Linter, highlight, util


class Gometalinter(Linter):
    """Provides an interface to gometalinter."""

    syntax = ('go', 'gosublime-go', 'gotools')
    cmd = 'gometalinter * .'
    regex = r'(?:[^:]+):(?P<line>\d+):(?P<col>\d+)?:(?:(?P<warning>warning)|(?P<error>error)):\s*(?P<message>.*)'
    error_stream = util.STREAM_BOTH
    default_type = highlight.ERROR

    def __init__(self, view, syntax):
        """Initialize and load GOPATH from settings if present."""
        Linter.__init__(self, view, syntax)

        gopath = self.get_view_settings().get('gopath')
        if gopath:
            if self.env:
                self.env['GOPATH'] = gopath
            else:
                self.env = {'GOPATH': gopath}
            print('sublimelinter: GOPATH={}'.format(self.env['GOPATH']))
        else:
            print('sublimelinter: using system GOPATH={}'.format(os.environ.get('GOPATH', '')))

    def run(self, cmd, code):
        files = [f for f in os.listdir(os.path.dirname(self.filename)) if f.endswith('.go')]
        return self.tmpdir(cmd, files, code)
