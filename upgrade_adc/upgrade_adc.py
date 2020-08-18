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
tgz_file_name = 'DCManager_v_1_3_201_20200807-0640.tgz'
vxms = [
        {'ip': '10.124.82.245', 'port': '30945', 'username': 'root', 'password': 'Testvxrail123!'}
        ]

def main():

    download_tgz()
    for vxm in vxms:

        vxm_ip = vxm.get('ip')
        vxm_port = vxm.get('port')
        vxm_username = vxm.get('username')
        vxm_password = vxm.get('password')

        logging.info('Start to upgrade vxm: {} !'.format(vxm_port))
        send_files_to_vxm(vxm_ip, vxm_port, vxm_username, vxm_password)
        downgrade_adc('root', vxm_ip, 'Testvxrail123!', vxm_port)
        upgrade_patch('root', vxm_ip, 'Testvxrail123!', vxm_port)
        update_ace_war('root', vxm_ip, 'Testvxrail123!', vxm_port)


    # time.sleep(120)
    # for vxm in vxms:
    #     vxm_ip = vxm.get('ip')
    #     vxm_port = vxm.get('port')
    #     vxm_password = vxm.get('password')
    #     logging.info('Start to check vmx: {} status !'.format(vxm_port))
    #     check_vxm('root', vxm_ip, vxm_password, vxm_port)

def update_ace_war(user, ip, passwd, port):
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
    remote_path = '/home/mystic'
    local_path = FILE_PATH + '/scripts/*'
    send_file(vxm_ip, vxm_port, username, vxm_password, local_path, remote_path)


def upgrade_patch(user, ip, passwd, port):
    time.sleep(3)
    cmd_upgrade_patch = '/mystic/telemetry/DCManager/venv/bin/python /home/mystic/update_script.py; echo $?'
    with SSHExecutor(ip, port, user, passwd) as ssh_runner:
        cmd_return = ssh_runner.exec_command(cmd_upgrade_patch)
        if cmd_return == 0:
            logging.info("upgrade patch command run successfully!")


def downgrade_adc(user, ip, passwd, port):
    with SSHExecutor(ip, port, user, passwd) as ssh_runner:
        cmd_return = ssh_runner.exec_command("sudo -u tcserver /bin/bash /home/mystic/downgrade_adc.sh {}; echo $?".format(tgz_file_name))
        logging.info(cmd_return)
        if cmd_return == 0:
            logging.info("downgrade adc command run successfully!")


def send_file(ip, port, username, password, local_file, remote_file):
    cmd = 'sshpass -p {} scp -P {} {} {}@{}:{}'.format(password, port, local_file, username, ip, remote_file)
    logging.info(cmd)
    r = os.system(cmd)
    logging.info('send file result: {}'.format(r))
    return r


def download_tgz():
    download_path = 'https://amaas-eos-drm1.cec.lab.emc.com/artifactory/VxRail-ACE-pypi-staging-local-drm/' \
                    'release/DCManager/release_1.3.202/patch/python23/test/'
    if os.path.exists(FILE_PATH+'/scripts/'+tgz_file_name):
        logging.info("tgz file has been already downloaded. skip download!")
    else:
        download_file = download_path + tgz_file_name
        logging.info('start to download {}'.format(download_file))
        os.chdir(FILE_PATH + '/scripts')
        logging.info (os.getcwd())
        download_result = os.system('wget {} --no-check-certificate'.format(download_file))
        logging.info('download_result: {}'.format(download_result))
        if os.path.exists(FILE_PATH + '/' + tgz_file_name):
            logging.info("download success !")
        else:
            logging.error("download failed !")


if __name__ == '__main__':
    main()