# vim: tabstop=4 shiftwidth=4 softtabstop=4

# Copyright 2010 United States Government as represented by the
# Administrator of the National Aeronautics and Space Administration.
# All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

from manila import flags

FLAGS = flags.FLAGS

flags.DECLARE('iscsi_num_targets', 'manila.volume.drivers.lvm')
flags.DECLARE('policy_file', 'manila.policy')
flags.DECLARE('volume_driver', 'manila.volume.manager')
flags.DECLARE('xiv_proxy', 'manila.volume.drivers.xiv')
flags.DECLARE('backup_service', 'manila.backup.manager')

def_vol_type = 'fake_vol_type'


def set_defaults(conf):
    conf.set_default('default_volume_type', def_vol_type)
    conf.set_default('volume_driver',
                     'manila.tests.fake_driver.FakeISCSIDriver')
    conf.set_default('iscsi_helper', 'fake')
    conf.set_default('connection_type', 'fake')
    conf.set_default('fake_rabbit', True)
    conf.set_default('rpc_backend', 'manila.openstack.common.rpc.impl_fake')
    conf.set_default('iscsi_num_targets', 8)
    conf.set_default('verbose', True)
    conf.set_default('sql_connection', "sqlite://")
    conf.set_default('sqlite_synchronous', False)
    conf.set_default('policy_file', 'manila/tests/policy.json')
    conf.set_default('xiv_proxy', 'manila.tests.test_xiv.XIVFakeProxyDriver')
    conf.set_default('backup_service', 'manila.tests.backup.fake_service')