# Copyright 2014 Mirantis Inc.
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

from tempest import clients_share as clients
from tempest.common.utils import data_utils
from tempest import config_share as config
from tempest import exceptions
from tempest.exceptions import share_exceptions
from tempest import test

CONF = config.CONF


class BaseSharesTest(test.BaseTestCase):
    """Base test case class for all Manila API tests."""

    _interface = "json"
    force_tenant_isolation = False
    protocols = ["nfs", "cifs"]
    resources_of_tests = []

    @classmethod
    def verify_nonempty(cls, *args):
        if not all(args):
            msg = "Missing API credentials in configuration."
            raise cls.skipException(msg)

    @classmethod
    def setUpClass(cls):
        if not any(p in CONF.share.enable_protocols for p in cls.protocols):
            skip_msg = "Manila is disabled"
            raise cls.skipException(skip_msg)
        super(BaseSharesTest, cls).setUpClass()
        if not hasattr(cls, "os"):
            cls.username = CONF.identity.username
            cls.password = CONF.identity.password
            cls.tenant_name = CONF.identity.tenant_name
            cls.verify_nonempty(cls.username, cls.password, cls.tenant_name)
            cls.os = clients.Manager(interface=cls._interface)
        if CONF.share.multitenancy_enabled:
            if not CONF.service_available.neutron:
                raise cls.skipException("Neutron support is required")
            sc = cls.os.shares_client
            nc = cls.os.network_client
            share_network_id = cls.provide_share_network(sc, nc)
            cls.os.shares_client.share_network_id = share_network_id
        cls.shares_client = cls.os.shares_client

    @classmethod
    def tearDownClass(cls):
        super(BaseSharesTest, cls).tearDownClass()
        cls.clear_resources()

    @classmethod
    def provide_share_network(cls, shares_client, network_client):
        """Used for finding/creating share network for multitenant driver.

        This method creates/gets entity share-network for one tenant. This
        share-network will be used for creation of service vm.

        :param shares_client: shares client, which requires share-network
        :param network_client: network client from same tenant as shares
        :returns: str -- share network id for shares_client tenant
        :returns: None -- if single-tenant driver used
        :raises: share_exceptions.NoAvailableNetwork
        """

        sc = shares_client

        if not CONF.share.multitenancy_enabled:
            # Assumed usage of a single-tenant driver
            share_network_id = None
        elif sc.share_network_id:
            # Share-network already exists, use it
            share_network_id = sc.share_network_id
        else:
            # Get data of suitable network
            net_id = subnet_id = share_network_id = None
            __, networks = network_client.list_networks()
            if "networks" in networks.keys():
                networks = networks["networks"]
            for network in networks:
                if ("active" in network["status"].lower() and
                    not network["router:external"]):
                    net_id = network["id"]
                    if len(network["subnets"]) > 0:
                        subnet_id = network["subnets"][0]
            if (net_id is None or subnet_id is None):
                #TODO(vponomaryov): create suitable network?
                raise share_exceptions.NoAvailableNetwork()

            # Try get suitable share-network
            __, share_networks = sc.list_share_networks_with_detail()
            for share_network in share_networks:
                if (net_id in share_network["neutron_net_id"] and
                    subnet_id in share_network["neutron_subnet_id"]):
                    share_network_id = share_network["id"]

            # Create suitable share-network
            if share_network_id is None:
                sn_name = "autogenerated_by_tempest"
                sn_desc = "This share-network was created by tempest"
                __, sn = sc.create_share_network(name=sn_name,
                                                 description=sn_desc,
                                                 neutron_net_id=net_id,
                                                 neutron_subnet_id=subnet_id)
                share_network_id = sn["id"]

        return share_network_id

    @classmethod
    def create_share_wait_for_active(cls, share_protocol=None, size=1,
                                     name=None, snapshot_id=None,
                                     description=None, metadata={},
                                     share_network_id=None, client=None):
        if client is None:
            client = cls.shares_client
        if description is None:
            description = "Tempest's share"
        r, s = client.create_share(share_protocol=share_protocol, size=size,
                                   name=name, snapshot_id=snapshot_id,
                                   description=description,
                                   metadata=metadata,
                                   share_network_id=share_network_id)
        resource = {"type": "share", "body": s, "deleted": False}
        cls.resources_of_tests.insert(0, resource)  # last in first out (LIFO)
        client.wait_for_share_status(s["id"], "available")
        return r, s

    @classmethod
    def create_snapshot_wait_for_active(cls, share_id, name=None,
                                        description=None, force=False,
                                        client=None):
        if client is None:
            client = cls.shares_client
        if description is None:
            description = "Tempest's snapshot"
        r, s = client.create_snapshot(share_id, name, description, force)
        resource = {"type": "snapshot", "body": s, "deleted": False}
        cls.resources_of_tests.insert(0, resource)  # last in first out (LIFO)
        client.wait_for_snapshot_status(s["id"], "available")
        return r, s

    @classmethod
    def create_share_network(cls, client=None, **kwargs):
        if client is None:
            client = cls.shares_client
        resp, sn = client.create_share_network(**kwargs)
        resource = {"type": "share_network", "body": sn, "deleted": False}
        cls.resources_of_tests.insert(0, resource)  # last in first out (LIFO)
        return resp, sn

    @classmethod
    def create_security_service(cls, ss_type="ldap", client=None, **kwargs):
        if client is None:
            client = cls.shares_client
        resp, ss = client.create_security_service(ss_type, **kwargs)
        resource = {"type": "security_service", "body": ss, "deleted": False}
        cls.resources_of_tests.insert(0, resource)  # last in first out (LIFO)
        return resp, ss

    @classmethod
    def clear_resources(cls, client=None):
        if client is None:
            client = cls.shares_client
        # Here we expect, that all resources were added as LIFO
        # due to restriction of deletion resources, that is in the chain
        for index, res in enumerate(cls.resources_of_tests):
            if not(res["deleted"]):
                try:
                    if res["type"] is "share":
                        client.delete_share(res["body"]['id'])
                    elif res["type"] is "snapshot":
                        client.delete_snapshot(res["body"]['id'])
                    elif res["type"] is "share_network":
                        client.delete_share_network(res["body"]['id'])
                    elif res["type"] is "security_service":
                        client.delete_security_service(res["body"]['id'])
                except exceptions.NotFound:
                    pass
                cls.resources_of_tests[index]["deleted"] = True
                client.wait_for_resource_deletion(res["body"]['id'])

    @classmethod
    def generate_share_network_data(self):
        data = {
            "name": data_utils.rand_name("sn-name"),
            "description": data_utils.rand_name("sn-desc"),
            "neutron_net_id": data_utils.rand_name("net-id"),
            "neutron_subnet_id": data_utils.rand_name("subnet-id"),
        }
        return data

    @classmethod
    def generate_security_service_data(self):
        data = {
            "name": data_utils.rand_name("ss-name"),
            "description": data_utils.rand_name("ss-desc"),
            "dns_ip": data_utils.rand_name("ss-dns_ip"),
            "server": data_utils.rand_name("ss-server"),
            "domain": data_utils.rand_name("ss-domain"),
            "sid": data_utils.rand_name("ss-sid"),
            "password": data_utils.rand_name("ss-password"),
        }
        return data


class BaseSharesAltTest(BaseSharesTest):
    """Base test case class for all Shares Alt API tests."""

    @classmethod
    def setUpClass(cls):
        cls.username = CONF.identity.alt_username
        cls.password = CONF.identity.alt_password
        cls.tenant_name = CONF.identity.alt_tenant_name
        cls.verify_nonempty(cls.username, cls.password, cls.tenant_name)
        cls.os = clients.AltManager(interface=cls._interface)
        alt_share_network_id = CONF.share.alt_share_network_id
        cls.os.shares_client.share_network_id = alt_share_network_id
        super(BaseSharesAltTest, cls).setUpClass()


class BaseSharesAdminTest(BaseSharesTest):
    """Base test case class for all Shares Admin API tests."""

    @classmethod
    def setUpClass(cls):
        cls.username = CONF.identity.admin_username
        cls.password = CONF.identity.admin_password
        cls.tenant_name = CONF.identity.admin_tenant_name
        cls.verify_nonempty(cls.username, cls.password, cls.tenant_name)
        cls.os = clients.AdminManager(interface=cls._interface)
        admin_share_network_id = CONF.share.admin_share_network_id
        cls.os.shares_client.share_network_id = admin_share_network_id
        super(BaseSharesAdminTest, cls).setUpClass()