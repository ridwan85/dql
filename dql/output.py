""" Formatting and displaying output """
from __future__ import unicode_literals
import os
import contextlib
import sys
import subprocess
import stat
import tempfile
from distutils.spawn import find_executable  # pylint: disable=E0611,F0401


def truncate(string, length, ellipsis='...'):
    """ Truncate a string to a length, ending with '...' if it overflows """
    if len(string) > length:
        return string[:length - len(ellipsis)] + ellipsis
    return string


class BaseFormat(object):

    """ Base class for formatters """

    def __init__(self, width=100, pagesize=1000):
        self.width = width
        self.pagesize = pagesize

    def write(self, results, ostream):
        """ Write results to an output stream """

        count = 0
        for result in results:
            self.format(result, ostream)
            count += 1
            if count > self.pagesize:
                return True
        return False

    def format(self, result, ostream):
        """ Format a single result and stick it in an output stream """
        raise NotImplementedError


class ExpandedFormat(BaseFormat):

    """ A layout that puts item attributes on separate lines """

    def format(self, result, ostream):
        ostream.write(self.width * '-' + '\n')
        max_key = max((len(k) for k in result.keys())) + 1
        for key, val in result.items():
            val = truncate(repr(val), self.width - max_key - 2)
            ostream.write("{0}: {1}\n".format(key.ljust(max_key), val))


class ColumnFormat(BaseFormat):

    """ A layout that puts item attributes in columns """

    def write(self, results, ostream):
        count = 0
        to_format = []
        all_columns = set()
        retval = False
        for result in results:
            to_format.append(result)
            all_columns.update(result.keys())
            count += 1
            if count > self.pagesize:
                retval = True
                break
        if to_format:
            self.format(to_format, all_columns, ostream)
        return retval

    def format(self, results, columns, ostream):
        col_width = int((self.width - 2) / len(columns)) - 2

        # Print the header
        first = True
        header = ''
        for col in columns:
            if first:
                header += '|'
                first = False
            header += ' '
            header += truncate(col.center(col_width), col_width)
            header += ' |'
        ostream.write(len(header) * '-' + '\n')
        ostream.write(header.encode('utf-8'))
        ostream.write('\n')
        ostream.write(len(header) * '-' + '\n')

        for result in results:
            ostream.write('|')
            for col in columns:
                ostream.write(' ')
                val = unicode(result.get(col, 'null')).ljust(col_width)
                ostream.write(truncate(val, col_width).encode('utf-8'))
                ostream.write(' |')
            ostream.write('\n')
        ostream.write(len(header) * '-' + '\n')


def get_default_display():
    """ Get the default display function for this system """
    if find_executable('less'):
        return less_display
    else:
        return stdout_display


@contextlib.contextmanager
def less_display():
    """ Use smoke and mirrors to acquire 'less' for pretty paging """
    # here's some magic. We want the nice paging from 'less', so we write
    # the output to a file and use subprocess to run 'less' on the file.
    # But the file might have sensitive data, so open it in 0600 mode.
    _, filename = tempfile.mkstemp()
    mode = stat.S_IRUSR | stat.S_IWUSR
    outfile = None
    outfile = os.fdopen(os.open(filename,
                                os.O_WRONLY | os.O_CREAT, mode), 'w')
    try:
        yield outfile
        outfile.flush()
        subprocess.call(['less', '-FXR', filename])
    finally:
        if outfile is not None:
            outfile.close()
        if os.path.exists(filename):
            os.unlink(filename)


@contextlib.contextmanager
def stdout_display():
    """ Print results straight to stdout """
    yield sys.stdout
