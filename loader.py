# TODO check log to ensure that all data copied
# TODO resuming file transfer on specific bytes

import sys
import os
import argparse
import hashlib
import pickle
from threading import Timer

import ftput


def get_options():
    """Parse options with argparse

    :rtype: argparse.ArgumentParser
    """
    args = argparse.ArgumentParser(
        usage="ftput --fromm ftp://from --to to",
        description="script to upload/download files via FTP"
    )
    args.add_argument(
        "-t",
        "--to",
        type=str,
        default=None,
        help="path to directory/file will be loaded"
    )
    args.add_argument(
        "-f",
        "--fromm",
        type=str,
        default=None,
        help="path from directory/file will be loaded"
    )
    args.add_argument(
        "-d",
        "--debug",
        type=int,
        default=0,
        help="set debug level"
    )
    args.add_argument(
        "-o",
        "--overwrite",
        default=None,
        action='store_true',
        help="if enabled, then overwrite"
    )
    args.add_argument(
        "-l",
        "--logfile",
        type=str,
        default='',
        help="path to logfile"
    )
    args.add_argument(
        "-r",
        "--resume",
        type=bool,
        default=True,
        help="resume from ready log file"
    )
    return args


def parse_connection(conn):
        """ Parse strings like ftp://user:pass@host:port/path

        :type conn: str or unicode
        :rtype: dict
        """
        conn = str(conn)
        if conn.startswith('ftp://'):
            conn = conn[6:]
        else:
            return False
        if '@' in conn:
            auth, host = conn.rsplit('@', 1)
            if ':' in auth:
                user, passwd = auth.split(':', 1)
            else:
                user = auth
                passwd = ''
        else:
            host = conn
            user = 'anonymous'
            passwd = ''
        if '/' in host:
            host, path = host.split('/', 1)
        else:
            path = '/'
        if ':' in host:
            host, port = host.split(':', 1)
            port = int(port)
        else:
            port = 21
        parsed_conn = {'user': user,
                       'passwd': passwd,
                       'host': host,
                       'port': port,
                       'path': path}
        return parsed_conn


def check_logs(func):
    def checked_transfer(self, src, dest):
        task = src + " to " + dest
        if task not in self.log:
            self.log[task] = False
        # TODO check if log is a number, so resume transfer from this number
        if not self.log[task]:
            self.log[task] = func(self, src, dest)
        return self.log[task]
    return checked_transfer


class TransferTask:

    def __init__(self, src, dest, overwrite=None, logfile='', resume=True, debug=False):
        """
        :type src: str or unicode
        :type dest: str or unicode
        :type overwrite: bool
        :type debug: int
        """
        self.ftp, self.log, self.old_log, self.logfile = None, None, None, None
        self.src = src
        self.dest = dest
        self.overwrite = overwrite
        self.debug = debug
        self.end = False
        self.init_log(logfile, resume)

    def init_log(self, logfile, resume):
        if logfile:
            self.logfile = open(logfile, 'rb+')
            self.log = pickle.load(self.logfile)
        else:
            h = self.src + self.dest + os.getcwd()
            if sys.version[0] == '3':
                h = h.encode('utf-8')
            h = hashlib.md5(h)
            f = h.hexdigest() + ".progress"
            if resume and os.path.exists(f):
                self.logfile = open(f, 'rb+')
                try:
                    self.log = pickle.load(f)
                except AttributeError:
                    self.log = dict()
            else:
                while os.path.exists(h.hexdigest() + ".progress"):
                    h = hashlib.md5(h.digest())
                    # TODO check if it's folder or whatever
                f = h.hexdigest() + ".progress"
                self.logfile = open(f, 'wb+')
                self.log = dict()
        self.old_log = self.log.copy()
        self.write_logs()

    def write_logs(self):
        if not self.old_log == self.log:
            self.logfile.seek(0)
            pickle.dump(self.log, self.logfile, 0)
            self.old_log = self.log.copy()
        if not self.end:
            Timer(1.0, self.write_logs).start()

    def start(self):
        if self.src.startswith('ftp://'):
            self.download(self.src, self.dest)
        elif self.dest.startswith('ftp://'):
            self.upload(self.src, self.dest)
        else:
            sys.stderr.write("Error: 'from' and 'to' are not ftp:// connection string\n")
            sys.exit(3)
        self.end = True

    def check_overwrite(self, path):
        """

        :type path: str or unicode
        :rtype: bool
        """
        if self.overwrite is None:
            if sys.version[0] == '2':
                choice = raw_input("Overwrite '" + path + "'? Yes/[No]/All/None : ")
            else:
                choice = input("Overwrite '" + path + "'? Yes/[No]/All/None : ")
            choice = choice.lower()
            if choice.startswith('y'):
                return True
            elif choice.startswith('a'):
                self.overwrite = True
                return True
            elif choice.startswith('non'):
                self.overwrite = False
                return False
            else:
                return False
        return self.overwrite

    @check_logs
    def upload_file(self, src, dest):
        """ Uploads one file to ftp server

        :type src: str or unicode
        :type dest: str or unicode
        :rtype: bool
        """
        if self.debug > 0:
            print("Start upload file", src, "to", dest)
        if self.ftp.isfile(dest) or self.ftp.isdir(dest):
            if self.overwrite or (self.overwrite is None) and self.check_overwrite(dest):
                if self.debug > 0:
                    print(dest, "will be overwritten")
                self.ftp.rm(dest)
            else:
                return True
        return self.ftp.store(src, dest)

    @check_logs
    def upload_dir(self, src, dest):
        """ Uploads dir to ftp server

        :type src: str or unicode
        :type dest: str or unicode
        :rtype: bool
        """
        if self.debug > 0:
            print("Start upload dir", src, "to", dest)
        if not self.ftp.isdir(dest) and not self.ftp.isfile(dest):
            self.ftp.mkdir(dest)
        elif self.ftp.isfile(dest):
            if self.overwrite or (self.overwrite is None) and self.check_overwrite(dest):
                if self.debug > 0:
                    print(dest, "overwritten")
                self.ftp.rm(dest)
                self.ftp.mkdir(dest)
            else:
                return True
        complete = True
        for name in os.listdir(src):
            if os.path.isdir(os.path.join(src, name)):
                t = self.upload_dir(os.path.join(src, name), os.path.join(dest, name))
            else:
                t = self.upload_file(os.path.join(src, name), os.path.join(dest, name))
            complete = complete and t
        return complete

    @check_logs
    def upload(self, src, conn_str):
        """

        :type src: str or unicode
        :type conn_str: str or unicode
        :rtype: bool
        """
        self.dest = parse_connection(conn_str)
        if self.debug > 0:
            print("Parsed connection:\n", self.dest)
        if not self.dest:
            sys.stderr.write("Error: can't parse connection string\n" +
                             conn_str + "\n")
            sys.exit(2)
        self.ftp = ftput.FTP(
            host=self.dest['host'],
            user=self.dest['user'],
            passwd=self.dest['passwd'],
            port=self.dest['port'],
            debug=self.debug
        )
        if self.ftp.isdir(self.dest['path']):
            self.dest['path'] = os.path.join(self.dest['path'], os.path.basename(src))
        if os.path.isfile(src):
            return self.upload_file(src, self.dest['path'])
        elif os.path.isdir(src):
            return self.upload_dir(src, self.dest['path'])
        sys.stderr.write("Error: 'upload()' incorrect file path\n" +
                         src + "\n")
        sys.exit(2)

    @check_logs
    def download_file(self, src, dest):
        """

        :type src: str or unicode
        :type dest: str or unicode
        :rtype: bool
        """
        if self.debug > 0:
            print("Start download file", src, "to", dest)
        if os.path.exists(dest):
            if self.overwrite or (self.overwrite is None) and self.check_overwrite(dest):
                if self.debug > 0:
                    print(dest, "will be overwritten")
                self.ftp.rm(dest)
            else:
                return True
        return self.ftp.retrieve(src, dest)

    @check_logs
    def download_dir(self, src, dest):
        """

        :type src: str or unicode
        :type dest: str or unicode
        :rtype bool
        """
        if self.debug > 0:
            print("Start download dir", src, "to", dest)
        if not os.path.isdir(dest) and not os.path.exists(dest):
            os.mkdir(dest)
        elif os.path.isfile(dest):
            if self.overwrite or (self.overwrite is None) and self.check_overwrite(dest):
                os.remove(dest)
                os.mkdir(dest)
            else:
                return True
        complete = True
        for name in self.ftp.ls(src):
            if (os.path.basename(name) == '.') or (os.path.basename(name) == '..'):
                continue
            if self.ftp.isdir(name):
                t = self.download_dir(name, os.path.join(dest, os.path.basename(name)))
            else:
                t = self.download_file(name, os.path.join(dest, os.path.basename(name)))
            complete = complete and t
        return complete

    @check_logs
    def download(self, conn_str, dest):
        """

        :type conn_str: str or unicode
        :type dest: str or unicode
        """
        self.src = parse_connection(conn_str)
        if self.debug > 0:
            print("Parsed connection:\n", self.src)
        if not self.src:
            sys.stderr.write("Error: 'download()' can't parse connection string\n" +
                             conn_str + "\n")
            sys.exit(2)
        self.ftp = ftput.FTP(
            host=self.src['host'],
            user=self.src['user'],
            passwd=self.src['passwd'],
            port=self.src['port'],
            debug=self.debug
        )
        if self.ftp.isdir(self.src['path']):
            if os.path.isdir(dest):
                dest = os.path.join(dest, os.path.basename(self.src['path']))
            return self.download_dir(self.src['path'], dest)
        else:
            if os.path.isfile(dest) and not self.overwrite:
                sys.stderr.write("Error: file '" + dest + "' already exist\n")
                sys.exit(111)
            if os.path.isdir(dest):
                dest = os.path.join(dest, os.path.basename(self.src['path']))
            return self.download_file(self.src['path'], dest)


def main():
    args = get_options().parse_args()
    if args.fromm is None:
        sys.stderr.write("Error: 'from' isn't set\n")
        sys.exit(3)
    elif args.to is None:
        sys.stderr.write("Error: 'to' isn't set\n")
        sys.exit(3)
    t = TransferTask(args.fromm, args.to, args.overwrite, args.logfile, args.debug)
    t.start()

if __name__ == "__main__":
    main()
