from __future__ import absolute_import, unicode_literals

import os
import time
# import socket
# import rpyc
# import threading

import subprocess

from contextlib import contextmanager
from paramiko import SSHClient as SSHClientBase, AutoAddPolicy
import logging
logging.basicConfig(level=logging.INFO,format='%(asctime)s - %(filename)s[line:%(lineno)d] - %(levelname)s: %(message)s')

from errors import ProvisionError, RemoteCommmandError, TimeoutError, exit_python
#
# from logs import log, TaggedLogger

# build_logger = log


# those PSNT are not intended to be used
# SPECIAL_PSNTS = ('N/A', 'REPLACEMENT', '', None)


# version helper
# class Version(object):
#     def __init__(self, verstr):
#         fields = verstr.split('.')
#         length = len(fields)
#         if length == 1:
#             self.major = fields[0]
#             self.minor = '0'
#             self.patch = '0'
#             self.build = '0'
#         elif length == 2:
#             self.major = fields[0]
#             self.minor = fields[1]
#             self.patch = '0'
#             self.build = '0'
#         elif length == 3:
#             self.major = fields[0]
#             self.minor = fields[1]
#             self.patch = fields[2]
#             self.build = '0'
#         elif length == 4:
#             self.major = fields[0]
#             self.minor = fields[1]
#             self.patch = fields[2]
#             self.build = fields[3]
#         else:
#             raise ProvisionError('Invalide version: ' + verstr)
#
#     def __str__(self):
#         return '.'.join([self.major, self.minor, self.patch, self.build])
#
#     def do_compare(self, other):
#         """
#         Function: do_compare
#         Summary:
#             Compare the version with other.
#         Returns:
#             0   if this == other
#             -1  if this < other
#             1   if this > other
#         """
#         def try_compare(this_comp, other_comp):
#             try:
#                 return cmp(int(this_comp), int(other_comp))
#             except ValueError:
#                 return cmp(this_comp, other_comp)
#         def compare(field):
#             return try_compare(getattr(self, field),
#                                getattr(other, field))
#         result = compare('major')
#         if result != 0:
#             return result
#         result = compare('minor')
#         if result != 0:
#             return result
#         result = compare('patch')
#         if result != 0:
#             return result
#         result = compare('build')
#         if result != 0:
#             return result
#         return 0
#
#     def __eq__(self, other):
#         return self.do_compare(other) == 0
#
#     def __ne__(self, other):
#         return self.do_compare(other) != 0
#
#     def __lt__(self, other):
#         return self.do_compare(other) < 0
#
#     def __gt__(self, other):
#         return self.do_compare(other) > 0
#
#     def __le__(self, other):
#         return self.do_compare(other) <= 0
#
#     def __ge__(self, other):
#         return self.do_compare(other) >= 0
#
#
# def get_installed_version():
#     version_str = subprocess.check_output('rpm -q buildsystem --queryformat="%{VERSION}.%{RELEASE}"',
#                                           shell=True)
#     return version_str
#
#
# class RetryFailureException(Exception):
#     def __init__(self, msg, orig_ex):
#         super(RetryFailureException, self).__init__(msg, orig_ex)
#         self.message = msg
#         self.orig_ex = orig_ex
#
#     def __str__(self):
#         return self.message
#
#
# class BackoffRetrier(object):
#     def __init__(self, func, tries=15, backoff=1, desc=None):
#         self.func = func
#         self.desc = desc
#         self.tries = tries
#         self.backoff = backoff
#
#     def __call__(self, *args, **kwargs):
#         desc = self.desc or self.func.__name__
#         for count in xrange(self.tries):
#             try:
#                 return self.func(*args, **kwargs)
#             except Exception as ex:
#                 time.sleep(count * self.backoff)
#                 err = ex.output if hasattr(ex, 'output') else str(ex)  # pylint: disable=no-member
#                 build_logger.info('Retrying {0} for {1} due to:\n"{2}"'.format(desc, count, err))
#                 continue
#         raise RetryFailureException('{0} failed after retries. Last error: "{1}"'.format(desc, err), ex)
#
#
# # helper for probing ports
# def probe_port(addr, port, tries=2):
#     assert isinstance(addr, str)
#     try:
#         for _ in xrange(tries):
#             conn = socket.create_connection((addr, port), 1)
#             time.sleep(0.5)
#             conn.close()
#         return True
#     except (socket.error, socket.timeout):
#         return False
#
#
# def probe_rpyc_port(addr, tries=2):
#     return probe_port(addr, rpyc.classic.DEFAULT_SERVER_PORT, tries)
#
#
# def wait_for_port(addr, port, timeout=600, interval=10):
#     expiry = time.time() + timeout
#     build_logger.info('Start waiting for port {0}:{1} ...'.format(addr, port))
#     while time.time() < expiry:
#         if probe_port(addr, port):
#             build_logger.info('Port {0}:{1} has up'.format(addr, port))
#             return
#         time.sleep(interval)
#     raise TimeoutError('Port {0}:{1} has not up before timeout'.format(addr, port))
#
# def wait_for_port_down(addr, port, timeout=600, interval=1):
#     expiry = time.time() + timeout
#     build_logger.info('Start waiting for port {0}:{1} down...'.format(addr, port))
#     while time.time() < expiry:
#         if not probe_port(addr, port):
#             build_logger.info('Port {0}:{1} has down'.format(addr, port))
#             return
#         time.sleep(interval)
#     raise TimeoutError('Port {0}:{1} has not down before timeout'.format(addr, port))
#
# class RPyConnection(object):
#     def __init__(self, addr, keepalive=False):
#         assert isinstance(addr, str)
#         self.addr = addr
#         self.keepalive = keepalive
#         self.conn = None
#
#     def connect(self):
#         self.conn = rpyc.classic.connect(self.addr, keepalive=self.keepalive)
#
#     def disconnect(self):
#         self.conn.close()
#         self.conn = None
#
#     def __enter__(self):
#         self.connect()
#         return self.conn
#
#     def __exit__(self, exception_type, exception_value, traceback):
#         self.disconnect()
#
#
# def gen_app_id(sn, prefix='EMC'):
#     def base36encode(number, alphabet='0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ'):
#         """Converts an integer to a base36 string."""
#         if not isinstance(number, (int, long)):
#             raise TypeError('number must be an integer')
#         base36 = ''
#         while number != 0:
#             number, i = divmod(number, len(alphabet))
#             base36 = alphabet[i] + base36
#         if len(base36) > 6:
#             raise RuntimeError("Can not hold in 6 chars string")
#         if len(base36) == 6:
#             return base36
#         length = 6 - len(base36)
#         while length > 0:
#             base36 = '0' + base36
#             length = length - 1
#         return base36
#     base_str = sn[5:]
#     if not base_str.isdigit():
#         src = hash(base_str) % 0x81BF1000  # mas of 6 digit of base32
#     else:
#         src = int(base_str)
#     return prefix + base36encode(src) + '04'
#
#
# class closing(object):
#     def __init__(self, obj, on_success=None, on_error=None, on_any=None):
#         self.obj = obj
#         if on_any is not None:
#             assert on_success is None
#             assert on_error is None
#             on_success = on_error = on_any
#         else:
#             assert on_success is not None
#             assert on_error is not None
#         if on_success is not None:
#             self.close_func = on_success
#         else:
#             self.close_func = lambda x: x.close()
#         self.on_error = on_error
#
#     def __enter__(self):
#         return self.obj
#
#     def __exit__(self, exc_type, exc_inst, tback):
#         if exc_type is not None and self.on_error is not None:
#             self.on_error(self.obj)
#         else:
#             self.close_func(self.obj)
#
#
# class SimpleExistGuard(object):
#     def __init__(self, enter_func, exit_func, *args, **kwargs):
#         self.enter_func = enter_func
#         self.exit_func = exit_func
#         self.args = args
#         self.kwargs = kwargs
#
#     def __enter__(self):
#         self.enter_func(*self.args, **self.kwargs)
#         return self
#
#     def __exit__(self, exc_type, exc_inst, tback):
#         self.exit_func(*self.args, **self.kwargs)
#
#
# class IgnoreException(object):
#     def __init__(self, exceptions):
#         super(IgnoreException, self).__init__()
#         self.exceptions = exceptions
#
#     def __enter__(self):
#         return self
#
#     def __exit__(self, exc_typ, exc_val, tback):
#         if isinstance(exc_val, self.exceptions):
#             build_logger.debug('Ignored exception', exc_info=1)
#             return True


class SSHClient(SSHClientBase):
    def __init__(self):
        super(SSHClient, self).__init__()
        self.set_missing_host_key_policy(AutoAddPolicy())


class SSHExecutor(object):
    CHANNEL_BUF_SIZE = 65535

    def __init__(self, hostname, port, username, password):
        self.sshc = SSHClient()
        self.hostname = hostname
        self.port = port
        self.username = username
        self.password = password
        self.channel = None

    def login(self):
        self.sshc.connect(hostname=self.hostname, port=self.port, username=self.username,
                          password=self.password, allow_agent=True,
                          look_for_keys=False)

    def logout(self):
        if self.channel is not None:
            self.channel.close()
            self.channel = None
        self.sshc.close()

    # use SSHClient to execute command
    def exec_command(self, cmdstr):
        logging.info('Running: ' + cmdstr)
        _, stdout, stderr = self.sshc.exec_command(cmdstr)
        output = stdout.read().strip()
        retcode = stdout.channel.recv_exit_status()
        if retcode != 0:
            output = stderr.read().strip()
            if len(output) == 0:
                output = stdout.read().strip()
            msg = 'Command failed with:\n{0}'.format(output)
            raise RemoteCommmandError(msg, cmdstr, retcode, output)
        # output = stdout.read().strip()
        if isinstance(output, bytes):
            output = str(output, encoding='utf8')
        if len(output) > 0:
            logging.debug('Command output:\n' + output)
        return output

    def exec_sudo_command(self, cmdstr, root_password):
        logging.info('Running: ' + cmdstr)
        stdin, stdout, stderr = self.sshc.exec_command(cmdstr,get_pty=True)
        stdin.write(root_password+'\n')
        retcode = stdout.channel.recv_exit_status()
        if retcode != 0:
            output = stderr.read().strip()
            if len(output) == 0:
                output = stdout.read().strip()
            msg = 'Command failed with:\n{0}'.format(output)
            raise RemoteCommmandError(msg, cmdstr, retcode, output)
        output = stdout.read().strip()
        if len(output) > 0:
            logging.debug('Command output:\n' + output)
        return output

    # use SSHClient to execute command with line output
    def exec_command_output_lines(self, cmdstr):
        logging.info('Running: ' + cmdstr)
        _, stdout, stderr = self.sshc.exec_command(cmdstr)
        for line in iter(lambda: stdout.readline(), ""):
            logging.debug(line.rstrip())
        retcode = stdout.channel.recv_exit_status()
        if retcode != 0:
            output = stderr.read().strip()
            if len(output) == 0:
                output = stdout.read().strip()
            msg = 'Command failed with:\n{0}'.format(output)
            raise RemoteCommmandError(msg, cmdstr, retcode, output)
        return True

    def invoke_shell(self, term='vt100'):
        if self.channel is None:
            logging.debug('Invoking shell...')
            self.channel = self.sshc.invoke_shell(term)
            while not self.channel.recv_ready():
                logging.debug('Not ready to receive data from channel, please wait...')
                time.sleep(2)
            resp = self.channel.recv(self.CHANNEL_BUF_SIZE).strip()
            return resp

    # use channel to send command by an interactive shell session
    def send_command(self, cmdstr):
        logging.info('Running: ' + cmdstr)
        output = ''
        if self.channel is not None:
            self.channel.settimeout(90)
            # send command
            self.channel.send(cmdstr + '\r')
            # in case of invalid command ,we need set timeout mechanism
            timeout = True
            expire = time.time() + 90
            while expire > time.time():
                if self.channel.recv_ready():
                    timeout = False
                    break
                else:
                    logging.info('Not ready to receive response for command: {0}, please wait...'.format(cmdstr))
                    time.sleep(5)
            if timeout:
                raise TimeoutError('Sending command {0} timeout'.format(cmdstr))
            output = self.channel.recv(self.CHANNEL_BUF_SIZE).strip()
        if len(output) > 0:
            logging.debug('Command output:\n' + output)
        return output

    @contextmanager
    def file(self, fpath, mode='r'):
        sftpc = self.open_sftp()
        fp = sftpc.file(fpath, mode)
        yield fp
        fp.close()
        sftpc.close()

    def __enter__(self):
        self.login()
        return self

    def __exit__(self, exc_typ, exc_val, tback):
        if self.channel is not None:
            self.channel.close()
            self.channel = None
        self.sshc.close()

    def open_sftp(self):
        return self.sshc.open_sftp()


# class RPyCExecutor(object):
#     def __init__(self, hostname, keepalive=True):
#         self.hostname = hostname
#         self.keepalive = keepalive
#         self.conn = None
#
#     def connect(self):
#         self.conn = rpyc.classic.connect(self.hostname, keepalive=self.keepalive)
#
#     def disconnect(self):
#         self.conn.close()
#         self.conn = None
#
#     def exec_command(self, cmdstr):
#         build_logger.info('Running: ' + cmdstr)
#         proc = self.conn.modules.subprocess.Popen(cmdstr, shell=True,  # pylint: disable=no-member
#                                                   stdout=self.conn.modules.subprocess.PIPE,  # pylint: disable=no-member
#                                                   stderr=self.conn.modules.subprocess.STDOUT)  # pylint: disable=no-member
#         stdout, _ = proc.communicate()
#         retcode = proc.returncode
#         if retcode != 0:
#             msg = 'Command failed with:\n{0}'.format(stdout)
#             raise RemoteCommmandError(msg, cmdstr, retcode, stdout)
#         if len(stdout) > 0:
#             build_logger.debug('Command output:\n' + stdout)
#         return stdout
#
#     @contextmanager
#     def file(self, fpath, mode='r'):
#         fh = self.conn.builtins.open(fpath, mode)  # pylint: disable=E1101
#         yield fh
#         fh.close()
#
#     def __enter__(self):
#         self.connect()
#         return self
#
#     def __exit__(self, exc_typ, exc_val, tback):
#         self.disconnect()
#
#
# class MultithreadNodesTasks(object):
#
#     class Task(threading.Thread):
#         def __init__(self, desc, functor, param, name_func=None, logger=None, die_on_error=False):
#             super(MultithreadNodesTasks.Task, self).__init__()
#             if logger is None:
#                 logger = build_logger.get()
#             if name_func is not None:
#                 name = name_func(param)
#                 self.logger = TaggedLogger(name, logger)
#             else:
#                 self.logger = logger
#             self.desc = desc
#             self.functor = functor
#             self.param = param
#             self.exc = None
#             self.die_on_error = die_on_error
#
#         def run(self):
#             # overried logger
#             build_logger.set(self.logger)
#             try:
#                 self.functor(self.param)
#             except Exception as ex:
#                 self.logger.exception('Failed processing {0}:'.format(self.desc))  # pylint: disable=E1101
#                 self.exc = ex
#             if self.exc is not None and self.die_on_error:
#                 exit_python()
#
#     def __init__(self, desc, functor, die_on_error=False):
#         self.desc = desc
#         self.functor = functor
#         self.workers = []
#         self.die_on_error = die_on_error
#
#     def apply(self, params, name_func=None, logger=None):
#         for param in iter(params):
#             thrd = self.Task(self.desc, self.functor, param, name_func, logger, self.die_on_error)
#             thrd.start()
#             self.workers.append((thrd, param))
#
#     def wait(self, on_complete=None):
#         assert on_complete is None or callable(on_complete)
#         failed_count = 0
#         finished_workers = []
#         while len(finished_workers) < len(self.workers):
#             for thrd, param in self.workers:
#                 if thrd in finished_workers:
#                     continue
#                 thrd.join(1)
#                 if not thrd.is_alive():
#                     finished_workers.append(thrd)
#                     if on_complete is not None:
#                         on_complete(param, thrd.exc)
#                     if thrd.exc is not None:
#                         failed_count += 1
#         if failed_count > 0:
#             raise ProvisionError('Failed processing ' + self.desc)
#
#
# def indent_block(strs, indent=4):
#     return '\n'.join(' ' * indent + s for s in strs.splitlines())
