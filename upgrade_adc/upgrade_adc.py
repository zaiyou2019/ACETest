import os
import sys
import time
import logging
from utils.utils import SSHExecutor
from utils.errors import RemoteCommmandError
import subprocess


FILE_PATH = str(os.path.dirname(os.path.realpath(__file__)))
LOG_PATH = FILE_PATH + '/log/'
logging.basicConfig(level=logging.INFO,format='%(asctime)s - %(filename)s[line:%(lineno)d] - %(levelname)s: %(message)s')

# Please check the following information before upgrade adc !!!
tgz_file_name = 'DCManager_v_1_3_201_20200904-0630.tgz'

vxms = [
        {'ip': '10.124.82.245', 'port': '30351', 'username': 'root', 'password': 'Testvxrail123!'}
        ]

def main():
    download_tgz()
    for vxm in vxms:

        vxm_ip = vxm.get('ip')
        vxm_port = vxm.get('port')
        vxm_username = vxm.get('username')
        vxm_password = vxm.get('password')

        logging.info('Start to upgrade vxm: {} !'.format(vxm_port))
        downgrade_adc(vxm_ip, vxm_port, vxm_username, vxm_password)
        upgrade_patch(vxm_ip, vxm_port, vxm_username, vxm_password)
        send_files_to_vxm(vxm_ip, vxm_port, vxm_username, vxm_password)
        update_ace_war(vxm_ip, vxm_port, vxm_username, vxm_password)


def prepare_env():
    # 1. revert snapshot
    # 2. register esrs
    # 3. update adc
    # 4. create common user in VC
    # 5. manager credential

    pass


def manager_credential():
    add_credential()
    validate_credential()


def add_credential(ip, port, user, passwd):
    # for pre-FP
    cmd_put_credential = 'curl -k -X PUT "https://localhost/ace/private/v1/lockbox/credentials" ' \
          '-H "accept: application/json" -H "Content-Type: application/json" ' \
          '-H \'Authorization: Basic YWRtaW5pc3RyYXRvckB2c3BoZXJlLmxvY2FsOlRlc3R2eHJhaWwxMjMh\' ' \
          '-d \'{"lockbox_name":"ACE","credentials":[' \
          '{"credential_name":"vxm_root_user","username":"root","password":"VGVzdHZ4cmFpbDEyMyE="},' \
          '{"credential_name":"vc_admin_user","username":"wendy@vsphere.local","password":"VGVzdHZ4cmFpbDEyMyE="},' \
          '{"credential_name":"vcsa_root_user","username":"root","password":"VGVzdHZ4cmFpbDEyMyE="},' \
          '{"credential_name":"psc_root_user","username":"root","password":"VGVzdHZ4cmFpbDEyMyE="}]}\''
    with SSHExecutor(ip, port, user, passwd) as ssh_runner:
        cmd_return = ssh_runner.exec_command(cmd_put_credential)
        if not cmd_return:
            logging.info('add credential successfully')


def validate_credential(ip, port, user, passwd):
    cmd_validate = 'curl -k -X POST "https://localhost/ace/private/v1/lockbox/credentials/validate" ' \
                   '-H "Content-Type: application/json" -H "Authorization: Basic YWRtaW5pc3RyYXRvckB2c3BoZXJlLmxvY2FsOlRlc3R2eHJhaWwxMjMh" ' \
                   '-d \'{"lockbox_name": "ACE","credential_names": ["vc_admin_user","vxm_root_user","vcsa_root_user","psc_root_user"]}\''
    with SSHExecutor(ip, port, user, passwd) as ssh_runner:
        cmd_return = ssh_runner.exec_command(cmd_validate)

def add_user_in_vc(ip, port, user, passwd):
    user_name = 'wendy21'
    cmd_get_user = '/usr/lib/vmware-vmafd/bin/dir-cli user find-by-name --account {} ' \
                   '--login administrator@vsphere.local --password Testvxrail123!'.format(user_name)
    cmd_add_user = '/usr/lib/vmware-vmafd/bin/dir-cli user create --account {} --first-name {} --last-name {} ' \
                   '--user-password Testvxrail123! ' \
                   '--login administrator@vsphere.local --password Testvxrail123!'.format(user_name, user_name, user_name)
    with SSHExecutor(ip, port, user, passwd) as ssh_runner:
        try:
            cmd_return = ssh_runner.exec_command(cmd_get_user)
            logging.info(cmd_return)
        except Exception as e:
            if not e.message.find('NO_SUCH_USER') == -1:
                cmd_return = ssh_runner.exec_command(cmd_add_user)
                if cmd_return.find('successfully'):
                    logging.info(cmd_return)

def get_credential():
    cmd = '"https://localhost/ace/private/v1/lockbox/credentials?lockbox_name=ACE&credential_names=' \
          'vxm_root_user,vcsa_root_user,psc_root_user,vc_admin_user" -H "accept: application/json" ' \
          '-H "Authorization: Basic YWRtaW5pc3RyYXRvckB2c3BoZXJlLmxvY2FsOlRlc3R2eHJhaWwxMjMh"'

def update_ace_war(ip, port, user, passwd):
    local_path = FILE_PATH + '/scripts/ace.war'
    remote_path = '/home/mystic'
    send_file(ip, port, user, passwd, local_path, remote_path)
    cmd_upgrade_patch = 'sudo -u tcserver cp /home/mystic/ace.war /usr/lib/vmware-marvin/marvind/webapps/'
    with SSHExecutor(ip, port, user, passwd) as ssh_runner:
        cmd_return = ssh_runner.exec_command(cmd_upgrade_patch)
        if cmd_return == 0:
            logging.info("command run successfully!")

# def check_vxm(user, ip, passwd, port):
#     ssh = ssh_cmd(user, ip, passwd, port)
#     ssh.sendline('python /home/mystic/checkEnvStatus.py')
#     ssh.close()


def send_files_to_vxm(vxm_ip, vxm_port, username, vxm_password):
    file_lcm_wa = '/home/mystic/PycharmProjects/railai-testcases/qa-tools/py_lcm_workaround.py'
    file_send_msg = FILE_PATH + '/scripts/' + 'send_message_start_collection.py'
    remote_path = '/home/mystic'
    files = [file_lcm_wa, file_send_msg]
    for local_file in files:
        send_file(vxm_ip, vxm_port, username, vxm_password, local_file, remote_path)


def upgrade_patch(ip, port, user, passwd):
    dcmanager_version = '_'.join(tgz_file_name.split('_')[0:-1]) + '.tgz'
    cmd = 'sed -e "s/DCManager_v.*tgz/{}/" {}/scripts/update_script.py > {}/scripts/update_script.py.new'.format(dcmanager_version, FILE_PATH, FILE_PATH)
    os.system(cmd)

    local_path = FILE_PATH + '/scripts/update_script.py.new'
    remote_path = '/home/mystic/update_script.py'
    send_file(ip, port, user, passwd, local_path, remote_path)

    remote_path = '/home/mystic'
    local_path = FILE_PATH + '/scripts/' + tgz_file_name
    send_file(ip, port, user, passwd, local_path, remote_path)

    patch = '_'.join(tgz_file_name.split('_')[0:-1]) + '.tgz'
    cmd_mkdir = 'sudo -u tcserver mkdir -p /mystic/telemetry/DCManager/tmp/adc_patches'
    cmd_mv_patch = 'mv /home/mystic/{} /mystic/telemetry/DCManager/tmp/adc_patches/{}'.format(tgz_file_name, patch)
    cmd_upgrade_patch = '/mystic/telemetry/DCManager/venv/bin/python /home/mystic/update_script.py; echo $?'
    cmd_list = [cmd_mkdir, cmd_mv_patch, cmd_upgrade_patch]
    with SSHExecutor(ip, port, user, passwd) as ssh_runner:
        for cmd in cmd_list:
            cmd_return = ssh_runner.exec_command(cmd)
            if cmd_return == 0:
                logging.info("command run successfully!")


def downgrade_adc(ip, port, user, passwd):
    local_path = FILE_PATH + '/scripts/downgrade_adc.sh'
    remote_path = '/home/mystic'
    send_file(ip, port, user, passwd, local_path, remote_path)
    with SSHExecutor(ip, port, user, passwd) as ssh_runner:
        cmd_return = ssh_runner.exec_command("sudo -u tcserver /bin/bash /home/mystic/downgrade_adc.sh {}; echo $?".format(tgz_file_name))
        logging.info(cmd_return)


def send_file(ip, port, username, password, local_file, remote_file):
    os.system('ssh-keygen -f "/home/mystic/.ssh/known_hosts" -R "[{}]:{}"'.format(ip, port))
    cmd = 'sshpass -p {} scp -P {} {} {}@{}:{}'.format(password, port, local_file, username, ip, remote_file)
    logging.info(cmd)
    r = os.system(cmd)
    logging.info('send file result: {}'.format(r))
    return r


def download_tgz():
    version = tgz_file_name.split('_')[2:5]
    if int(version[2]) % 2 == 1:
        version[2] = str(int(version[2])+1)
        prd_type = 'test'
    else:
        prd_type = 'prod'
    dcmanager_version = '.'.join(version)
    download_path = 'https://amaas-eos-drm1.cec.lab.emc.com/artifactory/VxRail-ACE-pypi-staging-local-drm/' \
                    'release/DCManager/release_{}/patch/python23/{}/'.format(dcmanager_version, prd_type)
    if os.path.exists(FILE_PATH+'/scripts/'+tgz_file_name):
        logging.info("tgz file has been already downloaded. skip download!")
    else:
        download_file = download_path + tgz_file_name
        logging.info('start to download {}'.format(download_file))
        os.chdir(FILE_PATH + '/scripts')
        logging.info(os.getcwd())
        download_result = os.system('wget {} --no-check-certificate'.format(download_file))
        logging.info('download_result: {}'.format(download_result))
        if os.path.exists(FILE_PATH + '/scripts/' + tgz_file_name):
            logging.info("download success !")
        else:
            logging.error("download failed !")


if __name__ == '__main__':
    main()