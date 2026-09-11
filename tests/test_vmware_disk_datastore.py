"""
vm_exclude_by_datastore_filter matches against the datastore a VM's virtual disks
live on, which is read out of the disk backing file name rather than from
obj.datastore (a lazy SOAP round trip per VM). The backing file name format is
"[datastore name] folder/disk.vmdk"; backings which carry no datastore, such as a
raw device mapping, must not be mistaken for one.
"""
import re

import pytest

from module.sources.vmware.connection import VMWareHandler

VEEAM = ("[VeeamBackup_a.proxy.example.net] "
         "a_lab_example_net_3c77be33aece48669514fe9cd00dc9ab/a.lab.example.net.vmdk")
REGULAR = "[vmstore-1] a.lab.example.net/a.lab.example.net.vmdk"
SNAPSHOT = "[VeeamBackup_a.proxy.example.net] x_example_net_950ad1f1/x.example.net-000001.vmdk"


@pytest.mark.parametrize("file_name, expected", [
    (VEEAM, "VeeamBackup_a.proxy.example.net"),
    (REGULAR, "vmstore-1"),
    (SNAPSHOT, "VeeamBackup_a.proxy.example.net"),
    ("[datastore with spaces] vm/vm.vmdk", "datastore with spaces"),
    # backings which carry no datastore
    (None, None),
    ("", None),
    ("/vmfs/devices/disks/naa.6000c29", None),
    ("[unterminated vm/vm.vmdk", None),
])
def test_get_datastore_name(file_name, expected):
    assert VMWareHandler.get_datastore_name(file_name) == expected


@pytest.mark.parametrize("pattern, excluded", [
    ("VeeamBackup_.*", True),
    (".*", True),
    ("vmstore-.*", False),
    # anchored at the start only, like every other netbox-sync filter
    ("Backup_.*", False),
])
def test_filter_decides_on_the_extracted_name(pattern, excluded):
    datastore = VMWareHandler.get_datastore_name(VEEAM)
    assert (re.compile(pattern).match(datastore) is not None) is excluded
