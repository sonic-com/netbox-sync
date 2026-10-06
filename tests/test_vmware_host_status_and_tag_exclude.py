# -*- coding: utf-8 -*-
#  Copyright (c) 2020 - 2026 netbox-sync team. All rights reserved.
#
#  netbox-sync.py
#
#  This work is licensed under the terms of the MIT license.
#  For a copy, see file LICENSE.txt included in this
#  repository or visit: <https://opensource.org/licenses/MIT>.

"""
host_status_preserve keeps a hand-set NetBox device status (i.e. 'decommissioning')
instead of overwriting it with the host's connection state on every run.
host_exclude_by_tag_filter is parsed into a list of tag names, like
vm_exclude_by_tag_filter, and not compiled as a regex like the other *_filter options.
"""
from types import SimpleNamespace

import pytest

from module.config.parser import ConfigParser
from module.netbox.inventory import NetBoxInventory
from module.netbox.object_classes import NBDevice, NBDeviceType, NBManufacturer, NBSite
from module.sources.vmware.config import VMWareConfig
from module.sources.vmware.connection import VMWareHandler

CONFIG = """
[netbox]
host_fqdn = netbox.example.com
api_token = xyz

[source/vc]
type = vmware
host_fqdn = vcenter.example.com
username = u
password = p
host_exclude_by_tag_filter = Netbox: No Sync, other tag
host_status_preserve = planned, Inventory, decommissioning
"""


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


def _source(inventory, status_preserve=None):
    src = object.__new__(VMWareHandler)
    src.inventory = inventory
    src.name = "test"
    src.source_tag = "Source: test"
    src.object_cache = dict()
    src.settings = SimpleNamespace(
        match_host_by_serial=True, overwrite_device_platform=False, host_role_relation=list(),
        host_interface_exclude_filter=None, set_primary_ip="never",
        host_status_preserve=status_preserve,
    )
    return src


def _sync_host(inventory, status_preserve, current_status):
    site = inventory.add_object(NBSite, data={"name": "site1"}, read_from_netbox=True)
    manufacturer = inventory.add_object(NBManufacturer, data={"name": "Dell"}, read_from_netbox=True)
    device_type = inventory.add_object(NBDeviceType, data={"model": "R650", "manufacturer": manufacturer},
                                       read_from_netbox=True)
    existing = inventory.add_object(NBDevice, data={"name": "esx1", "site": site, "device_type": device_type,
                                                    "status": current_status}, read_from_netbox=True)

    _source(inventory, status_preserve).add_device_vm_to_inventory(
        NBDevice, object_data={"name": "esx1", "site": {"name": "site1"}, "status": "active"},
        pnic_data=dict(), vnic_data=dict())

    status = existing.data.get("status")
    return status.get("value") if isinstance(status, dict) else status


def test_listed_host_status_is_preserved(inventory):
    assert _sync_host(inventory, ["decommissioning"], "decommissioning") == "decommissioning"


def test_unlisted_host_status_follows_connection_state(inventory):
    assert _sync_host(inventory, ["decommissioning"], "offline") == "active"


def test_host_options_are_parsed(tmp_path):
    config_file = tmp_path / "settings.ini"
    config_file.write_text(CONFIG)
    parser = ConfigParser()
    parser.file_list.clear()
    parser.content.clear()
    parser.config_errors.clear()
    parser.config_warnings.clear()
    parser.parsing_finished = False
    parser.add_config_file(str(config_file))
    parser.read_config()

    handler = VMWareConfig()
    handler.source_name = "vc"
    settings = handler.parse(do_log=False)

    assert settings.host_exclude_by_tag_filter == ["Netbox: No Sync", "other tag"]
    assert settings.host_status_preserve == ["planned", "inventory", "decommissioning"]
