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
import shutil
import tempfile
import subprocess

from SublimeLinter.lint import Linter, highlight, util
from SublimeLinter.lint.persist import settings


class Gometalinter(Linter):
    """Provides an interface to gometalinter."""

    syntax = ('go', 'gosublime-go', 'gotools', 'anacondago-go')
    cmd = 'gometalinter --fast .'
    regex = r'(?:[^:]+):(?P<line>\d+):(?P<col>\d+)?:(?:(?P<warning>warning)|(?P<error>error)):\s*(?P<message>.*)'
    error_stream = util.STREAM_BOTH
    default_type = highlight.ERROR

    def __init__(self, view, syntax):
        """Initialize and load GOPATH from settings if present."""
        Linter.__init__(self, view, syntax)

        if not self.env:
            self.env = os.environ.copy()

    def _set_env_for_view(self):
        gopath = self.get_view_settings().get('gopath')
        if gopath:
            self.env['GOPATH'] = gopath
            print('sublimelinter: (custom) GOPATH={}'.format(self.env['GOPATH']))
        else:
            print('sublimelinter: (system) GOPATH={}'.format(os.environ.get('GOPATH', '')))

        goroot = self.get_view_settings().get('goroot')
        if goroot:
            self.env['GOROOT'] = goroot
            print('sublimelinter: (custom) GOROOT={}'.format(self.env['GOROOT']))
        else:
            print('sublimelinter: (system) GOROOT={}'.format(os.environ.get('GOROOT', '')))

    def run(self, cmd, code):
        self._set_env_for_view()
        if settings.get('lint_mode') == 'background':
            return self._live_lint(cmd, code)
        else:
            return self._in_place_lint(cmd)

    def _live_lint(self, cmd, code):
        dir = os.path.dirname(self.filename)
        filename = os.path.basename(self.filename)
        cmd = cmd + ['-I', filename]
        print('gometalinter: live linting {}: {}'.format(filename, ' '.join(map(shlex.quote, cmd))))
        files = [f for f in os.listdir(dir) if f.endswith('.go')]
        if len(files) > 40:
            return ''
        return tmpdir(self, dir, cmd, files, self.filename, code)

    def _in_place_lint(self, cmd):
        dir = os.path.dirname(self.filename)
        filename = os.path.basename(self.filename)
        cmd = cmd + ['-I', filename]
        print('gometalinter: in-place linting {}: {}'.format(filename, ' '.join(map(shlex.quote, cmd))))
        out = communicate(cmd, output_stream=util.STREAM_STDOUT, env=self.env, cwd=dir)
        return out or ''


def tmpdir(self, dir, cmd, files, filename, code):
    """Run an external executable using a temp dir filled with files and return its output."""
    with tempfile.TemporaryDirectory(dir=dir, prefix=".gometalinter-") as tmpdir:
        for f in files:
            f = os.path.join(dir, f)
            target = os.path.join(tmpdir, os.path.basename(f))

            if os.path.basename(target) == os.path.basename(filename):
                # source file hasn't been saved since change, so update it from our live buffer
                with open(target, 'wb') as f:
                    if isinstance(code, str):
                        code = code.encode('utf8')

                    f.write(code)
            else:
                os.link(f, target)

        out = communicate(cmd, output_stream=util.STREAM_STDOUT, env=self.env, cwd=tmpdir)
    return out or ''


def communicate(cmd, code=None, output_stream=util.STREAM_STDOUT, env=None, cwd=None):
    """
    Return the result of sending code via stdin to an executable.
    The result is a string which comes from stdout, stderr or the
    combining of the two, depending on the value of output_stream.
    If env is None, the result of create_environment is used.
    """
    # On Windows, using subprocess.PIPE with Popen() is broken when not
    # sending input through stdin. So we use temp files instead of a pipe.
    if code is None and os.name == 'nt':
        if output_stream != util.STREAM_STDERR:
            stdout = tempfile.TemporaryFile()
        else:
            stdout = None

        if output_stream != util.STREAM_STDOUT:
            stderr = tempfile.TemporaryFile()
        else:
            stderr = None
    else:
        stdout = stderr = None

    out = popen(cmd, stdout=stdout, stderr=stderr,
                output_stream=output_stream, env=env, cwd=cwd)

    if out is not None:
        if code is not None:
            code = code.encode('utf8')

        out = out.communicate(code)

        if code is None and os.name == 'nt':
            out = list(out)

            for f, index in ((stdout, 0), (stderr, 1)):
                if f is not None:
                    f.seek(0)
                    out[index] = f.read()

        return util.combine_output(out)
    else:
        return ''


def popen(cmd, stdout=None, stderr=None, output_stream=util.STREAM_BOTH, env=None, cwd=None):
    """Open a pipe to an external process and return a Popen object."""
    info = None

    if os.name == 'nt':
        info = subprocess.STARTUPINFO()
        info.dwFlags |= subprocess.STARTF_USESTDHANDLES | subprocess.STARTF_USESHOWWINDOW
        info.wShowWindow = subprocess.SW_HIDE

    if output_stream == util.STREAM_BOTH:
        stdout = stdout or subprocess.PIPE
        stderr = stderr or subprocess.PIPE
    elif output_stream == util.STREAM_STDOUT:
        stdout = stdout or subprocess.PIPE
        stderr = subprocess.DEVNULL
    else:  # STREAM_STDERR
        stdout = subprocess.DEVNULL
        stderr = stderr or subprocess.PIPE

    if env is None:
        env = util.create_environment()

    try:
        return subprocess.Popen(
            cmd,
            stdin=subprocess.PIPE,
            stdout=stdout,
            stderr=stderr,
            startupinfo=info,
            env=env,
            cwd=cwd,
        )
    except Exception as err:
        msg = 'ERROR: could not launch ' + \
            repr(cmd) + '\nReason: ' + str(err) + \
            '\nPATH: ' + env.get('PATH', '')
        util.printf(msg)
        util.message(msg)
