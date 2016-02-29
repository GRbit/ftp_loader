# TODO overwrite check
# TODO log info about transmitted data
# TODO resume using log files

import sys
import os
import argparse

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
        type=bool,
        default=False,
        help="path from directory/file will be loaded"
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


class TransferTask:

    def __init__(self, src, dest, overwrite, debug):
        """
        :type src: str or unicode
        :type dest: str or unicode
        :type overwrite: bool
        :type debug: int
        """
        self.src = src
        self.dest = dest
        self.overwrite = overwrite
        self.debug = debug
        self.ftp = None

    def start(self):
        if self.src.startswith('ftp://'):
            self.download(self.src, self.dest)
        elif self.dest.startswith('ftp://'):
            self.upload(self.src, self.dest)
        else:
            sys.stderr.write("Error: 'from' and 'to' are not ftp:// connection string\n")
            sys.exit(3)

    def upload_file(self, src, dest):
        """ Uploads one file to ftp server

        :type src: str or unicode
        :type dest: str or unicode
        :rtype: bool
        """
        return self.ftp.store(src, dest)

    def upload_dir(self, src, dest):
        """ Uploads dir to ftp server

        :type src: str or unicode
        :type dest: str or unicode
        :rtype: bool
        """
        if not self.ftp.isdir(dest) and not self.ftp.isfile(dest):
            self.ftp.mkdir(dest)
        elif self.ftp.isfile(dest):
            if self.overwrite:
                self.ftp.rm(dest)
                self.ftp.mkdir(dest)
            else:
                # TODO overwrite handle
                return True
        for name in os.listdir(src):
            if os.path.isdir(os.path.join(src, name)):
                self.upload_dir(os.path.join(src, name), os.path.join(dest, name))
            else:
                self.upload_file(os.path.join(src, name), os.path.join(dest, name))
        return True

    def upload(self, src, conn_str):
        """

        :type src: str or unicode
        :type conn_str: str or unicode
        :rtype: bool
        """
        self.dest = parse_connection(conn_str)
        if self.debug:
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

    def download_file(self, src, dest):
        """

        :type src: str or unicode
        :type dest: str or unicode
        :rtype: bool
        """
        return self.ftp.retrieve(src, dest)

    def download_dir(self, src, dest):
        """

        :type src: str or unicode
        :type dest: str or unicode
        :rtype bool"
        """
        if not os.path.isdir(dest) and not os.path.isfile(dest):
            os.mkdir(dest)
        elif os.path.isfile(dest):
            if self.overwrite:
                os.remove(dest)
                os.mkdir(dest)
            else:
                # TODO overwrite handle
                return True
        for name in self.ftp.ls(src):
            if (os.path.basename(name) == '.') or (os.path.basename(name) == '..'):
                continue
            if self.ftp.isdir(name):
                self.download_dir(name, os.path.join(dest, os.path.basename(name)))
            else:
                self.download_file(name, os.path.join(dest, os.path.basename(name)))
        return True

    def download(self, conn_str, dest):
        """

        :type conn_str: str or unicode
        :type dest: str or unicode
        """
        self.src = parse_connection(conn_str)
        if self.debug:
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
    t = TransferTask(args.fromm, args.to, args.overwrite, args.debug)
    t.start()

if __name__ == "__main__":
    main()
