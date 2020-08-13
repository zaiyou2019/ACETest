from vmwc import VMWareClient


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

    host = '10.124.82.245'
    port = '37898'
    username = 'administrator@vsphere.local'
    password = 'Testvxrail123!'
    vm_name = ['esx_V045001', 'esx_V045002', 'esx_V045003']
    snapshot_name = 'V450_47300'

    # revert_snapshot(host, port, username, password, vm_name, snapshot_name)
    # vm_poweron(host, port, username, password, vm_name)