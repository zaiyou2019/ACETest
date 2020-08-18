#! /usr/bin/python2.7

from __future__ import print_function
import os
import atexit
import ssl
import sys
import time
import traceback
import subprocess
import math
import Cookie
import getpass
from optparse import OptionParser
from datetime import datetime

PYTHON_PATH = "/usr/lib/vmware-marvin/marvind/webapps/ROOT/WEB-INF/classes/scripts/lib/python2.7/site-packages"
sys.path.insert(0, PYTHON_PATH)

from pyVmomi import vim, vmodl, VmomiSupport, SoapStubAdapter, pbm
from pyVim import connect

####### Global #######
vc_ip = ""
vc_usr = ""
vc_pwd = ""
flag_skip_take_snapshot = False
controller_key_input_value = -1
####### Global #######


class VCSDKWrapper():
    '''
        Class handling VC SDK connections and calls
    '''
    def __init__(self, vc_ip, vc_usr, vc_pwd):
        print_message("Try to connect to VC {0} with user {1}".format(vc_ip, vc_usr))
        self.vc_ip = vc_ip
        self.vc_usr = vc_usr
        self.vc_pwd = vc_pwd
        self.service_instance = self.get_vc_connection()
        self.content = self.service_instance.RetrieveContent()

    
    def get_vc_connection(self):
        ssl._create_default_https_context = ssl._create_unverified_context
        service_instance = connect.SmartConnect(host=self.vc_ip, user=self.vc_usr, pwd=self.vc_pwd)
        atexit.register(connect.Disconnect, service_instance)
        return service_instance


    def get_pbm_connection(self):
        vpxd_stub = self.service_instance._stub
        session_cookie = vpxd_stub.cookie.split('"')[1]
        if not session_cookie:
            raise Exception("Failed to get vpxd cookie from vCenter connection.")

        cookie = Cookie.SimpleCookie()
        cookie["vmware_soap_session"] = session_cookie
        VmomiSupport.GetHttpContext()["cookies"] = cookie
        VmomiSupport.GetRequestContext()["vcSessionCookie"] = session_cookie

        pbm_stub = SoapStubAdapter(
            host=self.vc_ip,
            version="pbm.version.version1",
            path="/pbm/sdk",
            poolSize=0,
            sslContext=ssl._create_unverified_context())
        pbm_service_instance = pbm.ServiceInstance("ServiceInstance", pbm_stub)
        pbm_content = pbm_service_instance.RetrieveContent()
        atexit.register(connect.Disconnect, pbm_service_instance)
        return (pbm_service_instance, pbm_content)


    def get_obj_by_moref(self, vim_type, moref):
        container = self.content.viewManager.CreateContainerView(self.content.rootFolder, vim_type, True)
        for obj in container.view:
            if obj._moId == moref:
                return obj
        return None


    def wait_for_task(self, task, timeout=600):
        """
        Wait a VC task finishing.
        This will raise the exception if it failed.
        """
        expiry = time.time() + timeout
        while time.time() < expiry:
            print_message(".", end="")
            if task.info.state in ('success', 'error'):
                break
            time.sleep(1)
        else:
            raise Exception('Task "{0}" failed to complete before timeout'.format(str(task)))
        if task.info.state == 'error':
            raise task.info.error

    
    def call_CreateSnapshot_Task(self, vm_obj, name, desc, memory=True):
        task = vm_obj.CreateSnapshot_Task(name=name, description=desc, memory=memory, quiesce=False)
        self.wait_for_task(task)


    def call_ReconfigVM_Task(self, vm_obj, config_spec):
        task = vm_obj.ReconfigVM_Task(spec=config_spec)
        self.wait_for_task(task)

    
    def get_storage_policy_id(self, resource_type, policy_name_list):
        pbm_service_instance, pbm_content = self.get_pbm_connection()
        profile_manager = pbm_content.profileManager
        profile_id_list = profile_manager.PbmQueryProfile(resourceType=pbm.profile.ResourceType(resourceType=resource_type))

        if len(profile_id_list) <= 0:
            print_message("Failed to get VM storage policy")
            return ""

        profile_list = profile_manager.PbmRetrieveContent(profileIds=profile_id_list)
        for profile in profile_list:
            if profile.name in policy_name_list:
                print_message("Get profile {}".format(profile.name))
                return profile.profileId.uniqueId

        print_message("Did not get VxRail manager storage policy {0}".format(" or ".join(policy_name_list)))
        return ""


class ScriptRunner():
    '''
        Util class to run generate script file and run shell script
    '''
    @staticmethod
    def generate_script_file(script_content, script_file_name):
        if not os.path.exists(script_file_name):
            with open(script_file_name, 'w') as wf:
                wf.write(script_content)


    @staticmethod
    def run_shell_script(cmds):
        print_message("Run cmd {}".format(' '.join(cmds)))
        try:
            p = subprocess.Popen(cmds, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            output, errors = p.communicate()
            print_message("Stdout:\n{}".format(output)) # stdout is required result
            print_message("Stderr:\n{}".format(errors)) # stderr is log
            if p.returncode == 0:
                print_message("Run cmd {} succeeded.".format(' '.join(cmds)))
            return (p.returncode, output)
        except subprocess.CalledProcessError as ex:
            print_message("Exception occurred during command execution: {}".format(str(ex)))
            traceback.print_exc()
            return (-1, str(ex))


class SQLRunner():
    '''
        Util class to run SQL and get data from mystic/marvin
    '''

    DB_NAME_MARVIN = "marvin"
    DB_NAME_MYSTIC = "mysticmanager"

    @staticmethod
    def select(db_name, sql_statement):
        cmds = ["psql", "-U", "postgres", db_name, "-t", "-c", sql_statement]
        return_code, result = ScriptRunner.run_shell_script(cmds)
        if return_code == 0:
            return result.strip()
        else:
            print_message("Faile to run SQL {}:\n{}".format(sql_statement, result))
            return None


class VxRailManager():
    ####### Return code and message #######
    COMPLETE_IS_SET = (0, "Tomcat workDir is set. No need to modify.")
    COMPLETE_IS_ENOUGH = (0, "Free system disk space is more than 8GB. No need to modify Tomcat workDir.")
    COMPLETE_BUT_NOT_SUCCEED = (0, "Modifying tomcat workdir is not completed. Please change it manually.")
    SUCCEED_MODIFY_TOMCAT_WORKDIR = (0, "Modifying tomcat workdir succeeded.")
    ####### Return code and message #######

    ####### Static #######
    SYSTEM_AVAILABLE_SIZE_THRESHOLD_IN_GB = 8
    TOMCAT_CONFIG_FILE='/usr/lib/vmware-marvin/marvind/conf/server.xml'
    SCRIPT_DIR = os.path.dirname(os.path.realpath(__file__))
    CHANGE_WORKDIR_SCRIPT_NAME = os.path.join(SCRIPT_DIR, "changeWorkDir.sh")
    CHANGE_WORKDIR_SCRIPT_CONTENT = """\
    #!/bin/sh

    TOMCAT_CONFIG_FILE='/usr/lib/vmware-marvin/marvind/conf/server.xml'
    TOMCAT_CONFIG_BAK_FILE='/usr/lib/vmware-marvin/marvind/conf/server.xml.bak'
    TOMCAT_CONFIG_MATCHED_LINE='<Host appBase="webapps"'
    TOMCAT_CONFIG_ADDED_LINE='workDir="/data/store2/work"'

    cp $TOMCAT_CONFIG_FILE $TOMCAT_CONFIG_BAK_FILE
    sed -i "/$TOMCAT_CONFIG_MATCHED_LINE/a $TOMCAT_CONFIG_ADDED_LINE" $TOMCAT_CONFIG_FILE

    """
    ####### Static #######

    
    def __init__(self):
        pass


    def start_stop_vmware_marvin_service(self, op="start"):
        ops = ["start", "stop", "restart"]
        if op not in ops:
            raise Exception("Operation {0} for vmware-marvin is not supported.".format(op))
        
        cmd = "service vmware-marvin {0}".format(op)
        cmds = ["systemctl", op, "vmware-marvin"]
        ScriptRunner.run_shell_script(cmds)


    def change_tomcat_workdir(self):
        print_message("*********** Start to modify tomcat work directory ***********\n")
        try:
            if self.__is_tomcat_workdir_set():
                print_message(VxRailManager.COMPLETE_IS_SET[1])
                return
            else:
                print_message("Tomcat workDir is not set.")

            if self.__is_system_disk_space_enough():
                print_message(VxRailManager.COMPLETE_IS_ENOUGH[1])
                return
            else:
                print_message("System disk space is not enough.")

            print_message("Tomcat workDir is not set and system disk space is not enough, modify tomcat workDir to /data/store2/work.")
            self.start_stop_vmware_marvin_service("stop")
            self.__modify_tomcat_workdir()
            self.start_stop_vmware_marvin_service("start")
            print_message(VxRailManager.SUCCEED_MODIFY_TOMCAT_WORKDIR[1])
            return
        except Exception as ex:
            traceback.print_exc()
            return_message(*VxRailManager.COMPLETE_BUT_NOT_SUCCEED)
        finally:
            print_message("*********** End of modifying tomcat work directory ***********\n")
        

    def __modify_tomcat_workdir(self):
        ScriptRunner.generate_script_file(VxRailManager.CHANGE_WORKDIR_SCRIPT_CONTENT, VxRailManager.CHANGE_WORKDIR_SCRIPT_NAME)
        cmds = ["sh", VxRailManager.CHANGE_WORKDIR_SCRIPT_NAME]
        return_code, output = ScriptRunner.run_shell_script(cmds)
        if return_code != 0:
            raise Exception("Failed to modify tomcat workDir: {}".format(output))
        print_message("\n{0}".format(output))
        print_message("Modifying tomcat workDir succeeded.")


    def __is_tomcat_workdir_set(self):
        try:
            cmds = ["grep", "workDir", VxRailManager.TOMCAT_CONFIG_FILE]
            return_code, output = ScriptRunner.run_shell_script(cmds)
            if return_code != 0 or not output:
                return False
            else:
                return True
        except Exception as ex:
            traceback.print_exc()
            return False


    def __is_system_disk_space_enough(self):
        try:
            size_stat = os.statvfs("/")
            system_available_size_in_GB = math.ceil(float(size_stat.f_bavail * size_stat.f_frsize) / 1024 / 1024 / 1024)
            print_message("Total size of / is {} GB.".format(system_available_size_in_GB))
            if system_available_size_in_GB >= VxRailManager.SYSTEM_AVAILABLE_SIZE_THRESHOLD_IN_GB:
                return True
            else:
                return False
        except Exception as ex:
            traceback.print_exc()
            return False


class DiskExpander():
    ####### Return code and message #######
    ERROR_VC_CONNECTION = (10000, "Exception occurred during connecting VC or fecting content.")
    ERROR_DISK_EXPANSION_NEEDED = (10001, "Exception occurred during judge if disk expansion is needed.")
    ERROR_VXM_MOREF_NOT_FOUND = (10002, "Failed to get VxRail Manager virtual machine moref.")
    ERROR_VM_NOT_FOUND = (10003, "Cannot find VM.")
    ERROR_ADD_DISK_FAILURE = (10004, "Exception occurred during adding new disk for VM.")
    ERROR_CONFIG_LOGIC_VOLUME_FAILURE = (10005, "Exception occurred during config logic volume for VM.")
    ERROR_SNAPSHOT_FAILURE = (10006, "Exception occrred during take snapshot. Take snapshot manually and use '-s' to skip taking snapshot.")
    SUCCEED_NO_NEED_EXPAND_DISK = (0, "Disk space has been expanded. No need to expand.")
    SUCCEED_EXPAND_DISK = (0, "Expanding disk for VM completed succeefully.")
    ####### Return code and message #######

    ####### Static #######
    DATA_STORE2_PATH = "/data/store2"
    VXM_SNAPSHOT_NAME = "before_disk_expansion"
    VXM_SNAPSHOT_DESCRIPTION = "Snapshot taken before disk expansion in case unexpected failure."
    SQL_STATEMENT_GET_VXM_MOREF = "select morefid from virtual_machine where system_vm_type = 'VXRAIL_MANAGER';"
    PROFILE_RESOURCE_TYPE = "STORAGE"
    VXRAIL_STORAGE_PROFILE_NAME = "VXRAIL-SYSTEM-STORAGE-PROFILE"
    VXRAIL_STORAGE_PROFILE_NAME_1 = "MARVIN-SYSTEM-STORAGE-PROFILE"
    NEW_DISK_SIZE_IN_KB = 30 * 1024 * 1024  # 30GB
    SCRIPT_DIR = os.path.dirname(os.path.realpath(__file__))
    CONFIG_LOGIC_VOLUMNE_SCRIPT_NAME = os.path.join(SCRIPT_DIR, "configLogicVolume.sh")
    CONFIG_LOGIC_VOLUME_OPERATION_EXTEND = "extend"
    CONFIG_LOGIC_VOLUME_OPERATION_CLEAR = "clear"
    CONFIG_LOGIC_VOLUME_SCRIPT_CONTENT = """\
    #!/bin/sh

    #Usage: ./configLogicVolume.sh extend
    DATA_VG_NAME='data_vg'
    LV_NAME_STORE2='store2'
    DATA_STORE2_LV="/dev/$DATA_VG_NAME/$LV_NAME_STORE2"
    PV_NAME_SDB="/dev/sdb"

    get_disk_name(){
        disk_name_list=`fdisk -l|awk -F ' ' '/^Disk/{print $2}' | sed 's/.$//' | awk '/^\/dev\/sd/{print}'`
        disk_name=`echo $disk_name_list | awk '{print $1}'`
        for dn in $disk_name_list
        do
            if [ $dn \> $disk_name ]; then
                disk_name=$dn
            fi
        done
        echo "$disk_name"
    }

    get_physical_volume(){
        pv_list=`pvs | pvs | awk 'NR>1 {print $1}'`
        pv_name=`echo $pv_list | awk '{print $1}'`
        for pv in $pv_list
        do
            if [ $pv \> $pv_name ]; then
                pv_name=$pv
            fi
        done
        echo "$pv_name"
    }

    echo_message(){
        echo $1 >&2
    }

    return_message() {
        echo $1
    }

    extend_volume(){
        echo_message "Start extending logical volume $DATA_STORE2_LV"

        echo_message "Scan new disk"
        host_list=`ls /sys/class/scsi_host`
        for host in $host_list
        do
            echo "- - -" > /sys/class/scsi_host/$host/scan
        done

        disk_name=$(get_disk_name)
        echo_message ">>> New disk is $disk_name"

        echo_message ">>> Creating pv..."
        if ! result="$(pvcreate $disk_name)" ; then
            return_message "Failed to create physical volume for $disk_name: $result"
            exit -1
        fi

        echo_message ">>> Extend volume group $DATA_VG_NAME"
        if ! result="$(vgextend $DATA_VG_NAME $disk_name)" ; then
            return_message "Failed to extend volume group $DATA_VG_NAME: $reuslt"
            exit -1
        fi

        echo_message ">>> Add space to logic volume $DATA_STORE2_LV"
        if ! result="$(lvextend -l +100%FREE -r $DATA_STORE2_LV)" ; then
            return_message "Failed to add space to logic volume $DATA_STORE2_LV: $reuslt"
            exit -1
        fi
    }

    clear(){
        echo_message "Start clearing $DATA_STORE2_LV"

        pv_name=$(get_physical_volume)
        echo_message ">>> Added physical volume is $pv_name"

        echo_message ">>> Reduce $pv_name from $DATA_VG_NAME"
        vgreduce $DATA_VG_NAME $pv_name

        echo_message ">>> Remove physical volume $pv_name"
        pvremove $pv_name
    }

    echo_message -e "Config logical volume script, input value: $1"
    if [ $1 == 'extend' ]; then
        extend_volume
    elif [ $1 == 'clear' ]; then
        clear
    else
        echo "Input invalid value: $1"
        exit 1
    fi
    """
    ####### Static #######

    def __init__(self, vc_ip, vc_usr, vc_pwd):
        self.vc_ip = vc_ip
        self.vc_usr = vc_usr
        self.vc_pwd = vc_pwd
        self.vc_sdk_wrapper = VCSDKWrapper(self.vc_ip, self.vc_usr, self.vc_pwd)
    
    
    def expand_disk(self):
        print_message("*********** Start to expand disk ***********\n")
        unit_number = -1
        vm_obj = None

        # 0. If disk expansion needed
        try:
            size_stat = os.statvfs(DiskExpander.DATA_STORE2_PATH)
            data_store2_total_size_in_GB = math.ceil(float(size_stat.f_blocks * size_stat.f_frsize) / 1024 / 1024 / 1024)
            print_message("Total size of {} is {} GB.".format(DiskExpander.DATA_STORE2_PATH, data_store2_total_size_in_GB))
            if data_store2_total_size_in_GB > 30:
                print_message(DiskExpander.SUCCEED_NO_NEED_EXPAND_DISK[1])
                return
        except Exception as ex:
            traceback.print_exc()
            return_message(*DiskExpander.ERROR_DISK_EXPANSION_NEEDED)

        # 1. Get VM object from VC
        try:
            vm_moref = SQLRunner.select(SQLRunner.DB_NAME_MARVIN, DiskExpander.SQL_STATEMENT_GET_VXM_MOREF)
            if not vm_moref:
                return_message(*DiskExpander.ERROR_VXM_MOREF_NOT_FOUND)
            print_message("Get VxRail Manager moref: {}".format(vm_moref))
            vm_obj = self.vc_sdk_wrapper.get_obj_by_moref([vim.VirtualMachine], vm_moref)
        except Exception as ex:
            traceback.print_exc()
            return_message(*DiskExpander.ERROR_VC_CONNECTION)
        
        if not vm_obj:
            return_message(*DiskExpander.ERROR_VM_NOT_FOUND)

        # 2. Take snapshot if needed
        try:
            if not flag_skip_take_snapshot:
                print_message("Take snapshot of {}".format(vm_obj.name))
                snapshot_name_suffix = datetime.now().strftime("%Y%m%d%H%M%S")
                snapshot_name = "{}_{}".format(DiskExpander.VXM_SNAPSHOT_NAME, snapshot_name_suffix)
                self.vc_sdk_wrapper.call_CreateSnapshot_Task(vm_obj, snapshot_name, DiskExpander.VXM_SNAPSHOT_DESCRIPTION)
                print_message("Taking snapshot of {} completed successfully".format(vm_obj.name))
            else:
                print_message("Skip taking snapshot.")
        except Exception as ex:
            traceback.print_exc()
            return_message(*DiskExpander.ERROR_SNAPSHOT_FAILURE)

        # 3. Add disk for VM via VC
        try:
            unit_number = self.__add_disk_to_vm(vm_obj, DiskExpander.NEW_DISK_SIZE_IN_KB)
        except Exception as ex:
            traceback.print_exc()
            if unit_number != -1:
                self.__remove_disk_from_vm(vm_obj, unit_number)
            return_message(*DiskExpander.ERROR_ADD_DISK_FAILURE)

        # 4. Config logic volume in VM
        try:
            self.__config_logic_volume()
        except Exception as ex:
            traceback.print_exc()
            if unit_number != -1:
                self.__remove_disk_from_vm(vm_obj, unit_number)
            return_message(*DiskExpander.ERROR_CONFIG_LOGIC_VOLUME_FAILURE)
        
        print_message("*********** End to expand disk ***********\n")
        #return_message(*DiskExpander.SUCCEED_EXPAND_DISK)


    def __add_disk_to_vm(self, vm_obj, disk_size_in_kb):
        print_message("Adding disk to VM {0} ...".format(vm_obj.name))
        storage_profile_name_list = [DiskExpander.VXRAIL_STORAGE_PROFILE_NAME, DiskExpander.VXRAIL_STORAGE_PROFILE_NAME_1]
        policy_unique_id = self.vc_sdk_wrapper.get_storage_policy_id(DiskExpander.PROFILE_RESOURCE_TYPE, storage_profile_name_list)
        controller_key, unit_number = self.__get_controllerkey_unitnumber(vm_obj)
        add_disk_spec = self.__get_add_disk_spec(controller_key, unit_number, disk_size_in_kb, policy_unique_id)

        print_message("---- unit number: {0}".format(unit_number))
        print_message("---- controller key: {0}".format(controller_key))
        print_message("---- capacity size: {0}".format(disk_size_in_kb / 1024 / 1024))
        print_message("---- storage policy id: {0}".format(policy_unique_id))

        self.vc_sdk_wrapper.call_ReconfigVM_Task(vm_obj, add_disk_spec)
        print_message("Adding disk succeeded.")

        return unit_number


    def __remove_disk_from_vm(self, vm_obj, unit_number):
        print_message("Removing disk from VM {0} ...".format(vm_obj.name))
        remove_disk_spec = self.__get_remove_disk_spec(vm_obj, unit_number)
        self.vc_sdk_wrapper.call_ReconfigVM_Task(vm_obj, remove_disk_spec)
        print_message("Removing disk succeeded.")


    def __get_controllerkey_unitnumber(self, vm_obj):
        controller_key = ""
        unit_number = -1

        if controller_key_input_value != -1:
            controller_key = controller_key_input_value

        for dev in vm_obj.config.hardware.device:
            # We need to choose virtual disk only
            if isinstance(dev, vim.vm.device.VirtualDisk) and hasattr(dev.backing, 'fileName'):
                if not controller_key:
                    print_message("Using controller key of the first virtual disk: {0}, backing fileName: {1}".format(dev.deviceInfo.label, dev.backing.fileName))
                    controller_key = dev.controllerKey
                if unit_number < int(dev.unitNumber) + 1:
                    unit_number = int(dev.unitNumber) + 1
        return (controller_key, unit_number)


    def __get_add_disk_spec(self, controller_key, unit_number, disk_size_in_kb, policy_unique_id):
        disk_spec = vim.vm.device.VirtualDeviceSpec()
        disk_spec.fileOperation = vim.VirtualDeviceConfigSpecFileOperation.create
        disk_spec.operation = vim.VirtualDeviceConfigSpecOperation.add
        
        disk_spec.device = vim.vm.device.VirtualDisk()
        disk_spec.device.unitNumber = unit_number
        disk_spec.device.controllerKey = controller_key
        disk_spec.device.capacityInKB = disk_size_in_kb
        
        disk_spec.device.backing = vim.vm.device.VirtualDisk.FlatVer2BackingInfo()
        disk_spec.device.backing.thinProvisioned = True
        disk_spec.device.backing.diskMode = 'persistent'

        '''
            If get storage policy failed, use default disk mode.
            (This is a compromise to systems that deploy OVA but not create and apply
            VxRail Manager Storage Profile)
        '''
        if policy_unique_id:
            storage_profile_spec = vim.vm.DefinedProfileSpec()
            storage_profile_spec.profileId = policy_unique_id
            disk_spec.profile.append(storage_profile_spec)

        config_spec = vim.vm.ConfigSpec()
        config_spec.deviceChange.append(disk_spec)

        return config_spec


    def __get_remove_disk_spec(self, vm_obj, unit_number):
        virtual_device = None
        for dev in vm_obj.config.hardware.device:
            if isinstance(dev, vim.vm.device.VirtualDisk) and dev.unitNumber == unit_number:
                virtual_device = dev
                break
        
        if not virtual_device:
            raise Exception("Cannot find disk with unit number {0}".format(unit_number))

        disk_spec = vim.vm.device.VirtualDeviceSpec()
        disk_spec.operation = vim.VirtualDeviceConfigSpecOperation.remove
        disk_spec.device = virtual_device

        config_spec = vim.vm.ConfigSpec()
        config_spec.deviceChange.append(disk_spec)

        return config_spec


    def __config_logic_volume(self):
        print_message("\nStart to config logic volume ...")
        ScriptRunner.generate_script_file(DiskExpander.CONFIG_LOGIC_VOLUME_SCRIPT_CONTENT, DiskExpander.CONFIG_LOGIC_VOLUMNE_SCRIPT_NAME)
        cmds = ["sh", DiskExpander.CONFIG_LOGIC_VOLUMNE_SCRIPT_NAME, DiskExpander.CONFIG_LOGIC_VOLUME_OPERATION_EXTEND]
        return_code, output = ScriptRunner.run_shell_script(cmds)
        if return_code != 0:
            cmds = ["sh", DiskExpander.CONFIG_LOGIC_VOLUMNE_SCRIPT_NAME, DiskExpander.CONFIG_LOGIC_VOLUME_OPERATION_CLEAR]
            ScriptRunner.run_shell_script(cmds)
            raise Exception("Failed to config logic volume: {}".format(output))
        print_message("\n{0}".format(output))
        print_message("Config logic volume succeeded.")


def expand_disk():
    disk_expander = DiskExpander(vc_ip, vc_usr, vc_pwd)
    disk_expander.expand_disk()


def change_workdir():
    vxm = VxRailManager()
    vxm.change_tomcat_workdir()


def prepare():
    print_message("*********** Start to prepare for running script ***********\n")


def done():
    print_message("*********** Running script succeeded ***********\n")


def print_message(*args, **kwargs):
    print(*args, file=sys.stderr, **kwargs)


def return_message(code, message):
    print(message, file=sys.stdout)
    sys.exit(code)


def is_run_as_root():
    cmds = ["id", "-u"]
    return_code, output = ScriptRunner.run_shell_script(cmds)
    if return_code == 0 and int(output) == 0:
        print_message("Script is running as root.")
    else:
        return_message(-1, "Need to run as root.")


def create_option_parser():
    parser = OptionParser()
    parser.add_option('-c', '--address', dest="address", action='store',
                      help='Address of VC to connect to')
    parser.add_option('-u', '--username', dest="username", action='store',
                      help='User name to use when connecting to VC')
    parser.add_option('-p', '--password', dest="password", action='store',
                      help='Password to use when connecting to VC')
    parser.add_option('-k', '--controller-key', action='store',
                      help='(Optional) Specify the controller key value when adding a disk')
    parser.add_option('-s', '--skip-snapshot', action='store_true',
                        help='Skip to take snapshot before disk expansion')
    return parser

def main():
    global vc_ip, vc_usr, vc_pwd, flag_skip_take_snapshot, controller_key_input_value

    is_run_as_root()
    parser = create_option_parser()
    options, args = parser.parse_args()

    if not options.address or not options.username:
        parser.print_help()
        sys.exit(-1)

    vc_ip = options.address
    vc_usr = options.username

    if not options.password:
        vc_pwd = getpass.getpass("Enter vCenter {} password: ".format(vc_usr))
    else:
        vc_pwd = options.password
    if options.skip_snapshot:
        flag_skip_take_snapshot = True
    if options.controller_key:
        if not options.controller_key.isdigit():
            parser.print_help()
            sys.exit(-1)
        controller_key_input_value = int(options.controller_key)

    prepare()
    expand_disk()
    change_workdir()
    done()


if __name__ == "__main__":
    main()