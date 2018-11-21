#!/usr/bin/env python

from __future__ import print_function  # This import is for python2.*
import atexit
import requests
import ssl

from pyVim import connect
from pyVmomi import vim
from pyVmomi import vmodl

from tools import cli


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
    try:
        # Get the list of all datacenters we have available to us
        datacenters_object_view = content.viewManager.CreateContainerView(
            content.rootFolder,
            [vim.Datacenter],
            True)

        # Find the datastore and datacenter we are using
        for dc in datacenters_object_view.view:
            try:
                datastores_object_view = content.viewManager.CreateContainerView(
                    dc,
                    [vim.Datastore],
                    True)
                datastore = next((x for x in datastores_object_view.view if x.info.name == name), None)
                if datastore:
                    return datastore
            finally:
                datastores_object_view.Destroy()
    finally:
        # Clean up the views now that we have what we need
        datacenters_object_view.Destroy()

    return None

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
        source_datastore = findDatastore(content, args.source_datastore)
        destination_datastore = findDatastore(content, args.destination_datastore)
      
    except vmodl.MethodFault as e:
        print("Caught vmodl fault : " + e.msg)
        raise SystemExit(-1)

    raise SystemExit(0)


if __name__ == "__main__":
    main()


# This may or may not be useful to the person who writes the download example
# def download(remote_file_path, local_file_path):
#    resource = "/folder/%s" % remote_file_path.lstrip("/")
#    url = self._get_url(resource)
#
#    if sys.version_info >= (2, 6):
#        resp = self._do_request(url)
#        CHUNK = 16 * 1024
#        fd = open(local_file_path, "wb")
#        while True:
#            chunk = resp.read(CHUNK)
#            if not chunk: break
#            fd.write(chunk)
#        fd.close()
#    else:
#        urllib.urlretrieve(url, local_file_path)
#

# This may or may not be useful to the person who tries to use a service
# request in the future

# Get the service request set up
#        service_request_spec = vim.SessionManager.HttpServiceRequestSpec(
#            method='httpPut', url=http_url)
#        ticket = session_manager.AcquireGenericServiceTicket(
#            service_request_spec)
