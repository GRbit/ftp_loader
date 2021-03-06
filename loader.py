# TODO fucking spaceweb pureFTP recursive ls() fix
# TODO resuming file transfer on specific bytes
# TODO delete log file when all transfer completed

import sys
import os
import argparse
import hashlib
import pickle
from threading import Timer
import time
sys.path.append(os.getcwd())

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
        help="ftp/path to directory/file will be loaded"
    )
    args.add_argument(
        "-f",
        "--fromm",
        type=str,
        default=None,
        help="ftp/path from directory/file will be loaded"
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
        help="resume from log file, 1 to resume (default), 0 to not resume"
    )
    args.add_argument(
        "--tries",
        type=int,
        default=5,
        help="number of tries to transfer files"
    )
    return args


def parse_connection(conn):
    """ Parse strings like ftp://user:pass@host:port/path

    :type conn: str
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
        if not path:
            path = '/'
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


def d_print(s):
    """
    :type s: str
    """
    t = str(time.strftime('%H:%M:%S') + str(time.clock())[1:]).ljust(17)
    print(t + "DEBUG: " + s )


class Logger:

    def __init__(self, start_hash, logpath='', resume=True):
        self.logfile = None
        self.log = dict()
        self.old_log = dict()
        self.logpath = logpath
        self.resume = resume
        self.start_hash = start_hash
        self.end = False

    def start(self):
        if self.logpath:
            self.logfile = open(self.logpath, 'rb+')
        else:
            h = self.start_hash
            if sys.version[0] == '3':
                h = h.encode('utf-8')
            h = hashlib.md5(h)
            f = h.hexdigest() + ".progress"
            if self.resume and os.path.exists(f):
                self.logfile = open(f, 'rb+')
            else:
                while os.path.exists(f):
                    h = hashlib.md5(h.digest())
                    f = h.hexdigest() + ".progress"
                    # TODO check if it's folder or whatever
                self.logfile = open(f, 'wb+')
        if not self.log:
            try:
                self.log = pickle.load(self.logfile)
            except EOFError:
                # file is new or empty
                self.log = dict()
        self.old_log = self.log.copy()
        self.end = False
        self.write_logs()

    def stop(self):
        self.end = True
        self.logfile.seek(0)
        pickle.dump(self.log, self.logfile, 0)
        self.old_log = self.log.copy()
        self.logfile.close()

    def write_logs(self):
        if not self.end:
            thread_log = self.log.copy()
            thread_old_log = self.old_log.copy()
            if not thread_old_log == thread_log:
                self.logfile.seek(0)
                pickle.dump(thread_log, self.logfile, 0)
                self.old_log = thread_log.copy()
            Timer(0.33, self.write_logs).start()


def check_logs(func):
    def checked_transfer(self, src, dest):
        task = src + " to " + dest
        if task not in self.logger.log:
            self.logger.log[task] = False
        # TODO check if log is a number, so resume transfer from this number
        if not self.logger.log[task]:
            if self.debug > 0:
                d_print("STARTED " + func.__name__ + " ON TASK " + task)
            self.logger.log[task] = func(self, src, dest)
            if self.debug > 0:
                d_print("ENDED " + func.__name__ + " ON TASK " + task)
                d_print("RETURNED " + str(self.logger.log[task]))
        return self.logger.log[task]
    return checked_transfer


class TransferTask:

    def __init__(self, src, dest, overwrite=None, logpath='', resume=True, debug=False):
        """
        :type src: str
        :type dest: str
        :type overwrite: bool
        :type debug: int
        """
        self.ftp = None
        self.conn_param = None
        self.src = src
        self.dest = dest
        self.task_key = self.src + " to " + self.dest
        self.overwrite = overwrite
        self.logger = Logger(self.src + self.dest + os.getcwd(),
                            logpath,
                            resume)
        self.resume = resume
        self.debug = debug

    @property
    def finished(self):
        """
        :rtype: bool
        """
        if self.task_key in self.logger.log:
            return self.logger.log[self.task_key]
        else:
            return False

    def connect(self, conn_str):
        """

        :type conn_str:
        :return: list of str
        """
        self.conn_param = parse_connection(conn_str)
        if not self.conn_param:
            sys.stderr.write("Error: can't parse connection string\n" +
                             conn_str + "\n")
            sys.exit(2)
        if self.debug > 0:
            d_print("Parsed connection:")
            print(self.conn_param)
        self.ftp = ftput.FTP(
            host=self.conn_param['host'],
            user=self.conn_param['user'],
            passwd=self.conn_param['passwd'],
            port=self.conn_param['port'],
            debug=self.debug
        )
        self.logger.start()

    def start(self):
        if self.src.startswith('ftp://'):
            self.connect(self.src)
            self.download(self.conn_param['path'], self.dest)
        elif self.dest.startswith('ftp://'):
            self.connect(self.dest)
            self.upload(self.src, self.conn_param['path'])
        else:
            sys.stderr.write("Error: 'from' and 'to' are not ftp:// connection string\n")
            sys.exit(3)
        self.logger.stop()

    def check_overwrite(self, path):
        """
        :type path: str
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

    def transferred(self, src, dest):
        task = src + " to " + dest
        if task in self.logger.log and self.logger.log[task]:
            return True
        return False

    @check_logs
    def upload_file(self, src, dest):
        """ Uploads one file to ftp server

        :type src: str
        :type dest: str
        :rtype: bool
        """
        if self.ftp.exist(dest):
            if self.check_overwrite(dest):
                if self.debug > 0:
                    d_print("OVERWRITE " + dest)
                self.ftp.rm(dest)
            else:
                return True
        return self.ftp.store(src, dest)

    @check_logs
    def upload_dir(self, src, dest):
        """ Uploads dir to ftp server

        :type src: str
        :type dest: str
        :rtype: bool
        """
        if self.ftp.exist(dest) and not self.ftp.isdir(dest):
            if self.check_overwrite(dest):
                if self.debug > 0:
                    d_print("OVERWRITE " + dest)
                self.ftp.rm(dest)
            else:
                return True
        self.ftp.mkdir(dest)
        complete = True
        for name in os.listdir(src):
            src_name = os.path.join(src, os.path.basename(name))
            dest_name = os.path.join(dest, os.path.basename(name))
            if self.transferred(src_name, dest_name):
                if self.debug > 0:
                    d_print("ALREADY TRANSFERRED " + src_name + " to " + dest_name)
                t = True
            elif os.path.isdir(src_name):
                t = self.upload_dir(src_name, dest_name)
            else:
                t = self.upload_file(src_name, dest_name)
            complete = complete and t
        return complete

    def upload(self, src, dest_path):
        """

        :type src: str
        :type dest_path: str
        :rtype: bool
        """
        if self.ftp.isdir(dest_path):
            dest_path = os.path.join(dest_path, os.path.basename(src))
        if os.path.isdir(src):
            finished = self.upload_dir(src, dest_path)
            self.logger.log[self.task_key] = finished
        elif os.path.isfile(src):
            finished = self.upload_file(src, dest_path)
            self.logger.log[self.task_key] = finished
        else:
            sys.stderr.write("Error: upload path doesn't exist or incorrect\n")
            sys.exit(1)
        self.logger.log[self.task_key] = finished
        return finished

    @check_logs
    def download_file(self, src, dest):
        """

        :type src: str
        :type dest: str
        :rtype: bool
        """
        if os.path.exists(dest):
            if self.check_overwrite(dest):
                if self.debug > 0:
                    d_print("OVERWRITE " + dest)
                os.remove(dest)
            else:
                return True
        try:
            return self.ftp.retrieve(src, dest)
        except ftput.error.FileUnavailable:
            return False

    @check_logs
    def download_dir(self, src, dest):
        """

        :type src: str
        :type dest: str
        :rtype bool
        """
        if not os.path.isdir(dest) and not os.path.exists(dest):
            os.mkdir(dest)
        elif os.path.isfile(dest):
            if self.check_overwrite(dest):
                os.remove(dest)
                os.mkdir(dest)
            else:
                return True
        complete = True
        for name in self.ftp.ls(src):
            src_name = os.path.join(src, os.path.basename(name))
            dest_name = os.path.join(dest, os.path.basename(name))
            if (os.path.basename(src_name) == '.') or (os.path.basename(src_name) == '..'):
                continue
            if self.transferred(src_name, dest_name):
                if self.debug > 0:
                    d_print("ALREADY TRANSFERRED " + src_name + " to " + dest_name)
                t = True
            elif self.ftp.isdir(src_name):
                t = self.download_dir(src_name, dest_name)
            else:
                t = self.download_file(src_name, dest_name)
            complete = complete and t
        return complete

    def download(self, src_path, dest):
        """

        :type src_path: str
        :type dest: str
        :rtype: bool
        """
        if os.path.isdir(dest):
            dest = os.path.join(dest, os.path.basename(src_path))
        if self.ftp.isdir(src_path):
            finished =  self.download_dir(src_path, dest)
        else:
            finished = self.download_file(src_path, dest)
        self.logger.log[self.task_key] = finished
        return finished


def main():
    args = get_options().parse_args()
    if args.fromm is None:
        sys.stderr.write("Error: 'from' isn't set\n")
        sys.exit(3)
    elif args.to is None:
        sys.stderr.write("Error: 'to' isn't set\n")
        sys.exit(3)
    print("\nTransfer starting. Connecting to server...")
    t = TransferTask(args.fromm, args.to, args.overwrite, args.logfile, args.resume, args.debug)
    tries = 0
    print("\nConnected successfully. Starting file transfer...")

    while not t.finished and tries < args.tries:
        if args.debug and tries > 0:
            print("\nDEBUG 1:\nTransfer not completed... Try number: " + str(tries) + "\n")
        t.start()
        tries += 1

    if t.finished:
        print("\nTransfer successfully completed. Try number: " + str(tries) + "\n")
        if sys.version[0] == '2':
            choice = raw_input("Delete log file? [Yes]/No : ")
        else:
            choice = input("Delete log file? [Yes]/No : ")
        if choice.lower().startswith('n'):
            os.remove(t.logger.logfile.name)
    else:
        print("\nTransfer stopped and NOT completed. Tries exceeded: " + str(tries) + "\n")
        print("Files that was'n transferred:")
        for p, c in t.logger.log.items():
            if c == False:
                print(p)

if __name__ == "__main__":
    main()
