
from __future__ import absolute_import, unicode_literals

import os

###################################
# Provision Exceptions
###################################

# try to find some rare code so the watchdog knows it's an error
DIE_ON_ERROR_CODE = 41


class ProvisionError(Exception):
    """ General Exception during Provision """
    def __init__(self, msg):
        super(ProvisionError, self).__init__(msg)
        self.message = msg

    def __str__(self):
        return self.message


class CommandFailure(ProvisionError):
    def __init__(self, msg):
        super(CommandFailure, self).__init__(msg)


class DhcpLeaseChanged(ProvisionError):
    def __init__(self, msg, mac, ip):
        super(DhcpLeaseChanged, self).__init__(msg, mac, ip)
        self.msg = msg
        self.mac = mac
        self.ip = ip


class TaskCanceled(ProvisionError):
    """Task has been canceled"""
    def __init__(self, msg):
        super(TaskCanceled, self).__init__(msg)


class TimeoutError(ProvisionError):
    """Task timeout"""
    def __init__(self, msg):
        super(TimeoutError, self).__init__(msg)


class RemoteCommmandError(ProvisionError):
    """ Command failed in remote """
    def __init__(self, msg, cmdstr, retcode, output):
        super(RemoteCommmandError, self).__init__(msg)
        self.retcode = retcode
        self.cmdstr = cmdstr
        self.output = output


class DHCPLeaseMissingError(ProvisionError):
    pass


def exit_python(errcode=DIE_ON_ERROR_CODE):
    """ Critical error happened """
    os._exit(errcode)  # pylint: disable=W0212
