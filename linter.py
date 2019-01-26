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
import shlex
import tempfile

from SublimeLinter.lint import Linter, highlight, util
from SublimeLinter.lint.persist import settings


class Gometalinter(Linter):
    """Provides an interface to gometalinter."""

    cmd = 'gometalinter --fast .'
    regex = r'(?:[^:]+):(?P<line>\d+):(?P<col>\d+)?:(?:(?P<warning>warning)|(?P<error>error)):\s*(?P<message>.*)'
    error_stream = util.STREAM_BOTH
    default_type = highlight.ERROR
    defaults = {
        'selector': 'source.go'
    }

    def run(self, cmd, code):
        if settings.get('lint_mode') == 'background':
            return self._live_lint(cmd, code)
        else:
            return self._in_place_lint(cmd)

    def _dir_env(self):
        settings = self.get_view_settings()
        dir = os.path.dirname(self.filename)
        env = self.get_environment(settings)
        return dir, env

    def _live_lint(self, cmd, code):
        dir, env = self._dir_env()
        if not dir:
            print('gometalinter: skipped linting of unsaved file')
            return
        filename = os.path.basename(self.filename)
        cmd = cmd + ['-I', '^'+filename]
        print('gometalinter: live linting {} in {}: {}'.format(filename, dir, ' '.join(map(shlex.quote, cmd))))
        files = [f for f in os.listdir(dir) if f.endswith('.go')]
        if len(files) > 40:
            print("gometalinter: too many files ({}), live linting skipped".format(len(files)))
            return ''
        return tmpdir(cmd, dir, files, self.filename, code, env=env)

    def _in_place_lint(self, cmd):
        dir, env = self._dir_env()
        if not dir:
            print('gometalinter: skipped linting of unsaved file')
            return
        filename = os.path.basename(self.filename)
        cmd = cmd + ['-I', '^'+filename]
        print('gometalinter: in-place linting {}: {}'.format(filename, ' '.join(map(shlex.quote, cmd))))
        out = util.communicate(cmd, output_stream=util.STREAM_STDOUT, env=env, cwd=dir)
        return out or ''


def tmpdir(cmd, dir, files, filename, code, env=None):
    """Run an external executable using a temp dir filled with files and return its output."""
    with tempfile.TemporaryDirectory(dir=dir, prefix=".gometalinter-") as tmpdir:
        for f in files:
            target = os.path.join(tmpdir, f)
            f = os.path.join(dir, f)

            if os.path.basename(target) == os.path.basename(filename):
                # source file hasn't been saved since change, so update it from our live buffer
                with open(target, 'wb') as f:
                    if isinstance(code, str):
                        code = code.encode('utf8')

                    f.write(code)
            else:
                os.link(f, target)

        out = util.communicate(cmd, output_stream=util.STREAM_STDOUT, env=env, cwd=tmpdir)
    return out or ''
