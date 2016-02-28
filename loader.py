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


def upload_file(src, dest, ftp):
    """ Uploads one file to ftp server

    :type src: str or unicode
    :type dest: str or unicode
    :type ftp: ftput.FTP
    :rtype: bool
    """
    return ftp.store(src, dest)


def upload_dir(src, dest, ftp, overwrite=False):
    """ Uploads dir to ftp server

    :type src: str or unicode
    :type dest: str or unicode
    :type ftp: ftput.FTP
    :type overwrite: bool
    :rtype: bool
    """
    if not ftp.isdir(dest) and not ftp.isfile(dest):
        ftp.mkdir(dest)
    elif ftp.isfile(dest):
        if overwrite:
            ftp.rm(dest)
            ftp.mkdir(dest)
        else:
            # TODO overwrite handle
            return True
    for name in os.listdir(src):
        if os.path.isdir(os.path.join(src, name)):
            upload_dir(os.path.join(src, name), os.path.join(dest, name), ftp)
        else:
            upload_file(os.path.join(src, name), os.path.join(dest, name), ftp)
    return True


def upload(src, conn_str, overwrite=False, debug=0):
    """

    :type src: str or unicode
    :type conn_str: str or unicode
    :type overwrite: bool
    :type debug: int
    :rtype: bool
    """
    dest = parse_connection(conn_str)
    if debug:
        print("Parsed connection:\n", dest)
    if not dest:
        sys.stderr.write("Error: can't parse connection string\n" +
                         conn_str + "\n")
        sys.exit(2)
    ftp = ftput.FTP(
        host=dest['host'],
        user=dest['user'],
        passwd=dest['passwd'],
        port=dest['port'],
        debug=debug
    )
    if ftp.isdir(dest['path']):
        dest['path'] = os.path.join(dest['path'], os.path.basename(src))
    if os.path.isfile(src):
        return upload_file(src, dest['path'], ftp)
    elif os.path.isdir(src):
        return upload_dir(src, dest['path'], ftp, overwrite)
    sys.stderr.write("Error: 'def upload' incorrect file path\n" +
                     src + "\n")
    sys.exit(2)


def download_file(src, dest, ftp):
    """

    :type src: str or unicode
    :type dest: str or unicode
    :type ftp: ftput.FTP
    :rtype: bool
    """
    return ftp.retrieve(src, dest)


def download_dir(src, dest, ftp, overwrite=False):
    """

    :type src: str or unicode
    :type dest: str or unicode
    :type ftp: ftput.FTP
    :type overwrite: bool
    :rtype bool"
    """
    if not os.path.isdir(dest) and not os.path.isfile(dest):
        os.mkdir(dest)
    elif os.path.isfile(dest):
        if overwrite:
            os.remove(dest)
            os.mkdir(dest)
        else:
            # TODO overwrite handle
            return True
    for name in ftp.ls(src):
        if ftp.isdir(name):
            download_dir(name, os.path.join(dest, os.path.basename(name)), ftp, overwrite)
        else:
            download_file(name, os.path.join(dest, os.path.basename(name)), ftp)
    return True


def download(conn_str, dest, overwrite=False, debug=0):
    """

    :type conn_str: str or unicode
    :type dest: str or unicode
    :type overwrite: bool
    :type debug: int
    """
    src = parse_connection(conn_str)
    if debug:
        print("Parsed connection:\n", src)
    if not src:
        sys.stderr.write("Error: 'def download' can't parse connection string\n" +
                         conn_str + "\n")
        sys.exit(2)
    ftp = ftput.FTP(
        host=src['host'],
        user=src['user'],
        passwd=src['passwd'],
        port=src['port'],
        debug=debug
    )
    if ftp.isdir(src['path']):
        if os.path.isdir(dest):
            dest = os.path.join(dest, os.path.basename(src['path']))
        return download_dir(src['path'], dest, ftp, overwrite)
    else:
        if os.path.isfile(dest) and not overwrite:
            sys.stderr.write("Error: file '" + dest + "' already exist\n")
            sys.exit(111)
        if os.path.isdir(dest):
            dest = os.path.join(dest, os.path.basename(src['path']))
        return download_file(src['path'], dest, ftp)


def main():
    args = get_options().parse_args()
    if args.fromm is None:
        sys.stderr.write("Error: 'from' isn't set\n")
        sys.exit(3)
    elif args.to is None:
        sys.stderr.write("Error: 'to' isn't set\n")
        sys.exit(3)
    if args.fromm.startswith('ftp://'):
        download(args.fromm, args.to, args.overwrite, args.debug)
    elif args.to.startswith('ftp://'):
        upload(args.fromm, args.to, args.overwrite, args.debug)
    else:
        sys.stderr.write("Error: 'from' and 'to' are not ftp:// connection string\n")
        sys.exit(3)

if __name__ == "__main__":
    main()
