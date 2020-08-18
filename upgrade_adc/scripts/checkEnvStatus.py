import os
import subprocess
import logging
logging.basicConfig(level=logging.INFO,format='%(asctime)s - %(filename)s[line:%(lineno)d] - %(levelname)s: %(message)s')


def __run_cmd(cmdstr):
    try:
        logging.debug('Running: ' + cmdstr)
        output = subprocess.check_output(cmdstr, stderr=subprocess.STDOUT, shell=True)
        return output
    except subprocess.CalledProcessError as e:
        logging.error('Command failed output:\n' + e.output, exc_info=1)
        raise


def run_cmd_with_user(user, cmdstr):
    return __run_cmd('su {} -c {}'.format(user, cmdstr) + ' 2>&1')

def check_log():
    pass


def check_tcserver_permission():
    pass


def check_status():
    print("\n******** ADC Status ********")
    check_adc_status = 'sh /mystic/telemetry/DCManager/bin/status.sh'
    run_cmd_with_user('tcserver', check_adc_status)

    print("\n******** Lockbox Status ********")
    check_lockbox_status = 'sh /mystic/lockbox/bin/check_status.sh'
    run_cmd_with_user('tcserver', check_lockbox_status)


def check_version():
    adc_version_file = '/mystic/telemetry/DCManager/conf/application.yml'
    if os.path.exists(adc_version_file):
        print('\n******** adc version ********')
        cmd_get_adc_version = 'cat {}'.format(adc_version_file)
        adc_version = run_cmd_with_user('tcserver', cmd_get_adc_version)
        print('this is {}'.format(adc_version))
    else:
        print('\nadc version not found !')

    lockbox_version_file = '/mystic/lockbox/conf/lockbox.yml'
    if os.path.exists(lockbox_version_file):
        print('\n******** lockbox version ********')
        cmd_get_lockbox_version = 'cat {}'.format(lockbox_version_file)
        lockbox_version = run_cmd_with_user('tcserver', cmd_get_lockbox_version)
    else:
        print('\nlockbox version not found !')

    radar_version_file = '/mystic/radar/conf/radar.yml'
    if os.path.exists(radar_version_file):
        print('\n\n******** radar version ********')
        cmd_get_radar_version = 'cat {}'.format(radar_version_file)
        radar_version = run_cmd_with_user('tcserver', cmd_get_radar_version)
    else:
        print('\n\nradar version not found !')


# def run_cmd_with_user(user_name, cmd):
#     result = os.system(r"su {} -c '{}' ".format(user_name, cmd))
#     # write_log(log_name, 'info', 'user {} run cmd - {}'.format(user_name,cmd))
#     return result


def main():
    check_version()
    check_status()
    check_tcserver_permission()
    check_log()


if __name__ == '__main__':

    main()
