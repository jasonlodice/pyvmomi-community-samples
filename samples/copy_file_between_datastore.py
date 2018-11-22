#!/usr/bin/env python

from __future__ import print_function  # This import is for python2.*
import atexit
import requests
import ssl
import os.path
from pyVim import connect
from pyVmomi import vim
from pyVmomi import vmodl

from tools import cli
from pyVim.task import WaitForTask


def get_args():
    parser = cli.build_arg_parser()
    parser.add_argument('--source-datastore',
                        required=True,
                        action='store',
                        help='Source  Datastore name')

    parser.add_argument('--destination-datastore',
                        required=True,
                        action='store',
                        help='Destination  Datastore name')

    parser.add_argument('--source-file',
                        required=True,
                        action='store',
                        help='source path')

    parser.add_argument('--destination-file',
                        required=True,
                        action='store',
                        help='destination path')

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

    return None


def copyFile(content, datacenter, source_path, dest_path):
    def OnTaskProgressUpdate(task, status):
        if status != 'created':
            print("Task {0} is {1}% complete.".format(task.info.descriptionId, status))

    file_manager = content.fileManager
    # ensure target directory exists
    path = os.path.dirname(dest_path)
    file_manager.MakeDirectory(path, datacenter, createParentDirectories=True)
    task = file_manager.CopyDatastoreFile_Task(source_path, datacenter, dest_path, datacenter, force=True)
    WaitForTask(task, onProgressUpdate=OnTaskProgressUpdate)
    taskResult = task.info.result


def main():
    args = get_args()

    try:
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

        # Ensure that we cleanly disconnect in case our code dies
        atexit.register(connect.Disconnect, service_instance)

        content = service_instance.RetrieveContent()
        (source_dc, source_datastore) = findDatastore(content, args.source_datastore)
        (dest_dc, destination_datastore) = findDatastore(content, args.destination_datastore)

        source_path = "[{0}] {1}".format(source_datastore.name, args.source_file)
        dest_path = "[{0}] {1}".format(destination_datastore.name, args.destination_file)
        copyFile(content, source_dc, source_path, dest_path)

    except vmodl.MethodFault as e:
        print("Caught vmodl fault : " + e.msg)
        raise SystemExit(-1)

    raise SystemExit(0)


if __name__ == "__main__":
    main()
