"""
Matching a VM by primary IP is the last step of the cascade in
add_device_vm_to_inventory() and had no guard against landing on an object another
VM was already matched to in the same run.

A cloned VM is the worst case: a replica, or a backup appliance instant recovery
mount, has a different name, different MACs and a different instance UUID, so it
fails the first three steps, but its guest tools report the same IP as the VM it
was cloned from. It therefore matched the original's NetBox object and renamed it,
and the original renamed it back on the next run, so the object flapped forever.
"""
from types import SimpleNamespace

import pytest

from module.netbox.inventory import NetBoxInventory
from module.netbox.object_classes import NBCluster, NBClusterType, NBIPAddress, NBSite, NBVM
from module.sources.vmware.connection import VMWareHandler

ORIGINAL = "a.lab.example.net"
CLONE = "a.lab.example.net_3c77be33aece48669514fe9cd00dc9ab"
SHARED_IP = "10.0.0.5/24"


@pytest.fixture
def inventory():
    def _reset():
        inv = NetBoxInventory()
        inv.base_structure = {}
        inv.source_list = []
        inv.init()
        inv.netbox_api_version = "4.3.0"
        return inv
    inv = _reset()
    yield inv
    _reset()


def _source(inventory):
    src = object.__new__(VMWareHandler)
    src.inventory = inventory
    src.name = "test"
    src.source_tag = "Source: test"
    src.object_cache = dict()
    src.settings = SimpleNamespace(
        match_vm_by_serial=True, match_vm_by_mac_address=True, match_vm_by_ip_address=True,
        vm_role_relation=list(), vm_interface_exclude_filter=None,
        overwrite_vm_platform=True, overwrite_vm_interface_name=True,
        vm_status_on_create=None, vm_status_preserve=None, set_primary_ip="never",
    )
    return src


def _netbox_vm_with_primary_ip(inv):
    """The production VM as it already exists in NetBox, with SHARED_IP as primary."""
    site = inv.add_object(NBSite, data={"name": "site1"}, read_from_netbox=True)
    ctype = inv.add_object(NBClusterType, data={"name": "vmware"}, read_from_netbox=True)
    cluster = inv.add_object(NBCluster, data={"name": "c1", "type": ctype, "scope": site},
                             read_from_netbox=True)
    ip = inv.add_object(NBIPAddress, data={"address": SHARED_IP}, read_from_netbox=True)
    vm = inv.add_object(NBVM, data={"name": ORIGINAL, "cluster": cluster, "status": "active",
                                    "serial": "5020dfd2-79a1-c8b3-f223-e509d6da2ea9",
                                    "primary_ip4": ip},
                        read_from_netbox=True)
    return cluster, vm


def _parse(src, cluster, name, serial):
    """One add_device_vm_to_inventory() call, as the VMware source makes it."""
    src.add_device_vm_to_inventory(
        NBVM,
        object_data={"name": name, "cluster": cluster, "status": "active", "serial": serial},
        vnic_data=dict(), nic_ips=dict(), p_ipv4=SHARED_IP.split("/")[0], disk_data=list())


def test_clone_does_not_steal_the_object_of_the_vm_it_was_cloned_from(inventory):
    src = _source(inventory)
    _, original = _netbox_vm_with_primary_ip(inventory)
    cluster = original.data.get("cluster")

    # the production VM is parsed first and claims its own object by name + cluster
    _parse(src, cluster, ORIGINAL, "5020dfd2-79a1-c8b3-f223-e509d6da2ea9")
    # then the clone: different name, no MACs, different instance UUID, same guest IP
    _parse(src, cluster, CLONE, "502fa0bd-0b39-dced-3c1a-9e6365520719")

    assert original.data.get("name") == ORIGINAL, \
        "the clone renamed the NetBox object of the VM it was cloned from"
    assert {vm.data.get("name") for vm in inventory.get_all_items(NBVM)} == {ORIGINAL, CLONE}, \
        "the clone should have become its own object"


def test_primary_ip_still_matches_an_object_nothing_else_claimed(inventory):
    # control: the guard must not break the fallback it is narrowing. A VM renamed in
    # vCenter still has to find its NetBox object by primary IP.
    src = _source(inventory)
    _, original = _netbox_vm_with_primary_ip(inventory)
    cluster = original.data.get("cluster")

    _parse(src, cluster, "renamed-in-vcenter.example.net", "5020dfd2-79a1-c8b3-f223-e509d6da2ea9")

    assert original.data.get("name") == "renamed-in-vcenter.example.net", \
        "a primary IP match on an unclaimed object must still update that object"
    assert len(list(inventory.get_all_items(NBVM))) == 1, \
        "a renamed VM must not produce a second object"
