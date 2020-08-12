from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.proxy import Proxy, ProxyType
import unittest
import time
import os
from vmwc import VMWareClient
from HtmlTestRunner import HTMLTestRunner

FILE_PATH = str(os.path.dirname(os.path.realpath(__file__)))

class activeMgmtTestCase(unittest.TestCase):

    def setUp(self):
        host = '10.124.82.245'
        port = '37898'
        username = 'administrator@vsphere.local'
        password = 'Testvxrail123!'
        vm_name = ['esx_V045001', 'esx_V045002', 'esx_V045003']
        snapshot_name = 'V450_47300'

        # revert_snapshot(host, port, username, password, vm_name, snapshot_name)
        # vm_poweron(host, port, username, password, vm_name)

        chromeOptions = webdriver.ChromeOptions()
        chromeOptions.add_argument("--proxy-server=http://10.124.82.245:40000")
        self.browser = webdriver.Chrome(chrome_options=chromeOptions)
        self.browser.maximize_window()
        self.addCleanup(self.browser.quit)

    def go_to_homepage(self):
        user_account = 'zhangw19'
        user_password = ''

        self.browser.get('https://myvxrail-staging.dell.com/')

        elem_username = self.find_element('ID', 'username')
        elem_username.send_keys(user_account)

        elem_password = self.find_element('ID', 'Password')
        elem_password.send_keys(user_password)

        btn_singon = self.find_element('XPATH', '//input[@type="submit"]')
        btn_singon.click()

        btn_accept = self.find_element('XPATH', '//button[1]')
        btn_accept.click()

        btn_closewelcome = self.find_element('XPATH', '//button')
        btn_closewelcome.click()

        link_goHome = self.find_element('CLASS_NAME', 'homepage-link')
        link_goHome.click()

        btn_closewelcome = self.find_element('XPATH', '//button')
        btn_closewelcome.click()

    def go_to_updates_page(self):
        elem_updates = self.find_element('NAME', 'updates')
        elem_updates.click()

        elem_clr_icon = self.find_element('XPATH', '//clr-icon[@shape="close"]')
        elem_clr_icon.click()

    def updates_page_selection(self, task_type, clusters_upgrade_path):
        for task in task_type:
            time.sleep(3)
            checkbox_task = self.find_element('XPATH', '//label[@name="{}"]'.format(task.upper()))
            checkbox_task.click()

        for cluster in clusters_upgrade_path:
            cluster_name =cluster.get('cluster_name')
            target_version = cluster.get('target_version')

            cluster_xpath = '//span[@title="{}"]'.format(cluster_name)
            checkbox_cluster = self.find_element('XPATH', cluster_xpath)
            checkbox_cluster.click()

            dropdown_version = self.find_element('XPATH', '//span[@title="{}"]//following::div[@name="dropdown-button-"][1]'.format(cluster_name))
            dropdown_version.click()

            select_version = self.find_element('XPATH', '//span[@title="{}"]//following::a[@name="{}"][1]'.format(cluster_name, target_version))
            select_version.click()

        btn_run_task = self.find_element('XPATH', '//button[text()="RUN TASK(S)"]')
        self.browser.execute_script("arguments[0].click();", btn_run_task)

    def wizard_selection(self, task_type):
        # task_type.sort()
        # task_type = '_'.join(task_type)
        if 'update' in task_type:
            btn_advisories_next = self.find_element('XPATH', '//button[text()="Next"]')
            btn_advisories_next.click()

            elem_vc_username = self.find_element('name', 'username')
            elem_vc_username.send_keys("administrator@vsphere.local")

            elem_vc_password =self.find_element('name', 'password')
            elem_vc_password.send_keys("Testvxrail123!")

            btn_enter = self.find_element('XPATH', '//button[text()="Enter"]')
            btn_enter.click()

            btn_verf_cred_next = self.find_element('XPATH', '//button[text()="Next"]')
            btn_verf_cred_next.click()

            btn_select_version_next = self.find_element('XPATH', '//button[text()="Next"]')
            btn_select_version_next.click()

            btn_summary_finish = self.find_element('XPATH', '//button[text()="Finish"]')
            btn_summary_finish.click()
        else:
            btn_advisories_next = self.find_element('XPATH', '//button[@class="btn btn-primary btn-sm"]')
            btn_advisories_next.click()


    def testUpdate(self):

        task_type = ['precheck']
        clusters_upgrade_path = [{'cluster_name': 'vcluster442', 'target_version': '4.7.410'}]
        self.go_to_homepage()
        self.go_to_updates_page()
        self.updates_page_selection(task_type=task_type, clusters_upgrade_path=clusters_upgrade_path)
        self.wizard_selection(task_type)

        # job_id = self.find_element('XPATH', '//span[@class="ng-star-inserted"]').get_attribute('value')

    def find_element(self, method, method_value):
        wait = WebDriverWait(self.browser, 20)
        if method.upper() == 'ID':
            element = wait.until(EC.element_to_be_clickable((By.ID, method_value)))
        elif method.upper() == 'XPATH':
            element = wait.until(EC.element_to_be_clickable((By.XPATH, method_value)))
        elif method.upper() == 'LINK_TEXT':
            element = wait.until(EC.element_to_be_clickable((By.LINK_TEXT, method_value)))
        elif method.upper() == 'NAME':
            element = wait.until(EC.element_to_be_clickable((By.NAME, method_value)))
        elif method.upper() == 'CLASS_NAME':
            element = wait.until(EC.element_to_be_clickable((By.CLASS_NAME, method_value)))
        else:
            raise ValueError('invalid find element method')

        return element

    def tearDown(self):
        self.browser.quit()


def revert_snapshot(host, port, username, password, vm_name, snapshot_name):
    with VMWareClient(host, username, password, port) as client:
        for vm in client.get_virtual_machines():
            if vm.name in vm_name:
                for snapshot in vm.get_snapshots():
                    if snapshot.name == snapshot_name:
                        snapshot.revert()


def vm_poweron(host, port, username, password, vm_name):
    with VMWareClient(host, username, password, port) as client:
        for vm in client.get_virtual_machines():
            if vm.name in vm_name:
                vm.power_on()

if __name__ == '__main__':
    # unittest.main(verbosity=2)
    report_file = 'test_active_mgmt.html'
    unittest.main(testRunner=HTMLTestRunner())
