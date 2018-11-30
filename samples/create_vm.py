#!/usr/bin/env python
# William lam
# www.virtuallyghetto.com

"""
vSphere SDK for Python program for creating tiny VMs (1vCPU/128MB) with random
names using the Marvel Comics API
"""

import atexit
import hashlib
import json

import random
import time
import ssl
import requests
from pyVim import connect
from pyVmomi import vim

from tools import cli
from tools import tasks


def get_args():
    """
    Use the tools.cli methods and then add a few more arguments.
    """
    parser = cli.build_arg_parser()

    parser.add_argument('--vm-name',
                        required=True,
                        action='store',
                        help='qapi')

    parser.add_argument('--datastore',
                        required=True,
                        action='store',
                        help='datastore, ex: datastore1')

    parser.add_argument('--datastore-dir',
                        required=True,
                        action='store',
                        help='datastore directory path, ex: vm_1')

    parser.add_argument('--disk-file',
                        required=True,
                        action='store',
                        help='name of disk file, ex: disk1.vmdk')

    args = parser.parse_args()

    return cli.prompt_for_password(args)


def findDatastore(content, name):
    """

    :param content:
    :type content: pyVmomi.VmomiSupport.vim.ServiceInstanceContent
    :param name:
    :type name: str
    :return:
    :rtype:
    """

    try:
        # Get the list of all datacenters we have available to us
        datacenter_view = content.viewManager.CreateContainerView(
            content.rootFolder,
            [vim.Datacenter],
            True)

        # Find the datastore and datacenter we are using
        for dc in datacenter_view.view:
            try:
                datastore_view = content.viewManager.CreateContainerView(
                    dc,
                    [vim.Datastore],
                    True)
                datastore = next((x for x in datastore_view.view if x.info.name == name), None)
                if datastore:
                    return dc, datastore
            finally:
                datastore_view.Destroy()
    finally:
        # Clean up the views now that we have what we need
        datacenter_view.Destroy()

    return None, None


def create_dummy_vm(name, service_instance, datastore, vm_folder, resource_pool, vm_path, disk_file):
    # bare minimum VM shell, no disks. Feel free to edit
    vmx_file = vim.vm.FileInfo(logDirectory=None,
                               snapshotDirectory=None,
                               suspendDirectory=None,
                               vmPathName=vm_path)

    scsi_spec = vim.vm.device.VirtualDeviceSpec()
    scsi_spec.operation = vim.vm.device.VirtualDeviceSpec.Operation.add
    scsi_spec.device = vim.vm.device.VirtualLsiLogicController()
    scsi_spec.device.deviceInfo = vim.Description()
    scsi_spec.device.slotInfo = vim.vm.device.VirtualDevice.PciBusSlotInfo()
    scsi_spec.device.slotInfo.pciSlotNumber = 16
    scsi_spec.device.controllerKey = 100
    scsi_spec.device.unitNumber = 3
    scsi_spec.device.busNumber = 0
    scsi_spec.device.hotAddRemove = True
    scsi_spec.device.sharedBus = 'noSharing'
    scsi_spec.device.scsiCtlrUnitNumber = 7

    disk_spec = vim.vm.device.VirtualDeviceSpec()
    disk_spec.fileOperation = "create"
    disk_spec.operation = vim.vm.device.VirtualDeviceSpec.Operation.add
    disk_spec.device = vim.vm.device.VirtualDisk()
    disk_spec.device.backing = vim.vm.device.VirtualDisk.FlatVer2BackingInfo()
    disk_spec.device.backing.datastore = datastore
    disk_spec.device.backing.fileName = "{0}/{1}".format(vm_path, disk_file)
    disk_spec.device.backing.thinProvisioned = True
    disk_spec.device.backing.diskMode = 'persistent'
    disk_spec.device.unitNumber = 1
    disk_spec.device.capacityInKB = 41943040
    disk_spec.device.controllerKey = scsi_spec.device.key

    config = vim.vm.ConfigSpec(name=name, memoryMB=4096, numCPUs=2,
                               deviceChange=[scsi_spec, disk_spec],
                               annotation='qapi created vm',
                               files=vmx_file,
                               version='vmx-11',
                               guestId='windows9_64Guest')

    print("Creating VM {}...".format(name))
    task = vm_folder.CreateVM_Task(config=config, pool=resource_pool)
    tasks.wait_for_tasks(service_instance, [task])

    # 11/23/18 - left off
    # map disk files to guestId
    # vms are being created in new directories, _1, etc. instead of in existing.
    # test bootability


def main():
    """
    Simple command-line program for creating Dummy VM based on Marvel character
    names
    """

    args = get_args()

    service_instance = None
    sslContext = None
    verify_cert = None

    if args.disable_ssl_verification:
        sslContext = ssl.SSLContext(ssl.PROTOCOL_SSLv23)
        sslContext.verify_mode = ssl.CERT_NONE
        verify_cert = False
        # disable urllib3 warnings
        if hasattr(requests.packages.urllib3, 'disable_warnings'):
            requests.packages.urllib3.disable_warnings()

    try:
        service_instance = connect.SmartConnect(host=args.host,
                                                user=args.user,
                                                pwd=args.password,
                                                port=int(args.port),
                                                sslContext=sslContext)
    except IOError as e:
        pass
    if not service_instance:
        print("Could not connect to the specified host using specified "
              "username and password")
        raise SystemExit(-1)

    atexit.register(connect.Disconnect, service_instance)

    content = service_instance.RetrieveContent()

    datacenter, datastore = findDatastore(content, args.datastore)
    vmfolder = datacenter.vmFolder
    hosts = datacenter.hostFolder.childEntity
    resource_pool = hosts[0].resourcePool
    vm_dir = "[{0}] {1}".format(args.datastore, args.datastore_dir)
    create_dummy_vm(args.vm_name, service_instance, datastore, vmfolder, resource_pool, vm_dir, args.disk_file)

    return 0


# Start program
if __name__ == "__main__":
    main()
