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
        "-v",
        "--verify",
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


def upload_file(from_path, dest_path, ftp):
    """ Uploads one file to ftp server

    :type from_path: str or unicode
    :type dest_path: str or unicode
    :type ftp: ftput.FTP
    :rtype: bool
    """
    return ftp.store(from_path, dest_path)


def upload(src, conn_str, verify, debug):
    """

    :type src: str or unicode
    :type conn_str: str or unicode
    :type verify: bool
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
    if os.path.isfile(src):
        if not os.path.basename(dest['path']):
            dest['path'] += os.path.basename(src)
        return upload_file(src, dest['path'], ftp)
    elif os.path.isdir(src):
        # upload dir
        pass
    sys.stderr.write("Error: 'def upload' incorrect file path\n" +
                     src + "\n")
    sys.exit(2)


def download_file(from_path, dest_path, ftp):
    """

    :type from_path: str or unicode
    :type dest_path: str or unicode
    :type ftp: ftput.FTP
    :rtype: bool
    """
    return ftp.retrieve(from_path, dest_path)


def download(conn_str, dest, verify, debug):
    """

    :type conn_str: str or unicode
    :type dest: str or unicode
    :type verify: bool
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
        # download dir
        print(src['path'], "is dir")
        pass
    else:
        if os.path.isfile(dest):
            sys.stderr.write("Error: file '" + dest + "' already exist\n")
            sys.exit(111)
        if os.path.isdir(dest):
            dest = os.path.join(dest, os.path.basename(src['path']))
        return download_file(src['path'], dest, ftp)
    sys.stderr.write("Error: 'def download' incorrect file path\n" +
                     src['path'] + "\n")
    sys.exit(2)
    pass


def main():
    args = get_options().parse_args()
    if args.fromm is None:
        sys.stderr.write("Error: 'from' isn't set\n")
        sys.exit(3)
    elif args.to is None:
        sys.stderr.write("Error: 'to' isn't set\n")
        sys.exit(3)
    if args.fromm.startswith('ftp://'):
        download(args.fromm, args.to, args.verify, args.debug)
    elif args.to.startswith('ftp://'):
        upload(args.fromm, args.to, args.verify, args.debug)
    else:
        sys.stderr.write("Error: 'from' and 'to' are not ftp:// connection string\n")
        sys.exit(3)

if __name__ == "__main__":
    main()