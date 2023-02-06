# -*- coding: utf-8 -*-
#  Copyright (c) 2020 - 2022 Ricardo Bartels. All rights reserved.
#
#  netbox-sync.py
#
#  This work is licensed under the terms of the MIT license.
#  For a copy, see file LICENSE.txt included in this
#  repository or visit: <https://opensource.org/licenses/MIT>.

from module.config import source_config_section_name
from module.config.base import ConfigBase
from module.config.option import ConfigOption
from module.sources.common.source_base import config_option_enabled, config_option_permitted_subnets


class CheckRedfishConfig(ConfigBase):

    section_name = source_config_section_name
    source_name = None

    options = [
        config_option_enabled,

        ConfigOption("type",
                     str,
                     description="type of source. This defines which source handler to use",
                     config_example="check_redfish",
                     mandatory=True),

        ConfigOption("inventory_file_path",
                     str,
                     description="define the full path where the check_redfish inventory json files are located",
                     mandatory=True),

        config_option_permitted_subnets,

        ConfigOption("overwrite_host_name",
                     bool,
                     description="""define if the host name discovered via check_redfish
                     overwrites the device host name in NetBox""",
                     default_value=False),

        ConfigOption("overwrite_power_supply_name",
                     bool,
                     description="""define if the name of the power supply discovered via check_redfish
                     overwrites the power supply name in NetBox""",
                     default_value=False),

        ConfigOption("overwrite_power_supply_attributes",
                     bool,
                     description="""define if existing power supply attributes are overwritten with data discovered
                     via check_redfish if False only data which is not preset in NetBox will be added""",
                     default_value=True),

        ConfigOption("overwrite_interface_name",
                     bool,
                     description="""define if the name of the interface discovered via check_redfish
                     overwrites the interface name in NetBox""",
                     default_value=False),

        ConfigOption("overwrite_interface_attributes",
                     bool,
                     description="""define if existing interface attributes are overwritten with data discovered
                     via check_redfish if False only data which is not preset in NetBox will be added""",
                     default_value=True)
    ]
