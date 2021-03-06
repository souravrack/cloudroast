"""
Copyright 2015 Rackspace

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""
import time

from cafe.drivers.unittest.decorators import tags
from cloudroast.networking.networks.fixtures import NetworkingComputeFixture


# For TCP testing
TCP_PORT1 = '993'
TCP_PORT2 = '994'
TCP_PORT_RANGE = '992-995'

# UDP ports for sending a file: port 750 within UDP egress rule, 749 not
UDP_PORT_750 = '750'
UDP_PORT_749 = '749'

# Operation now in progress if a reply from a port outside the rule
TCP_RULE_EXPECTED_DATA = ['992 (tcp) timed out: Operation now in progress',
                          '993 port [tcp/*] succeeded!',
                          '994 port [tcp/*] succeeded!',
                          '995 (tcp) failed: Connection refused']

TCP_EXPECTED_DATA = ['992 (tcp) failed: Connection refused',
                     '993 port [tcp/*] succeeded!',
                     '994 port [tcp/*] succeeded!',
                     '995 (tcp) failed: Connection refused']


class SecurityGroupsEgressIPv6Test(NetworkingComputeFixture):
    @classmethod
    def setUpClass(cls):
        super(SecurityGroupsEgressIPv6Test, cls).setUpClass()

        base_name = 'sg_egress_v6_{0}'
        keypair_name = base_name.format('keypair')
        network_name = base_name.format('net')

        cls.network = cls.create_server_network(name=network_name, ipv6=True)
        cls.keypair = cls.create_keypair(name=keypair_name)

        server_labels = ['listener', 'sender', 'icmp_sender', 'other_sender']
        server_names = [base_name.format(label) for label in server_labels]

        # Creating servers on the same isolated network and
        # getting a dict with the server name as key and server obj as value
        servers = cls.create_multiple_servers(server_names=server_names,
                                              keypair_name=cls.keypair.name,
                                              networks=[cls.network.id])

        # Setting the servers as class attributes identified by server label
        for label, name in zip(server_labels, server_names):
            setattr(cls, label, servers[name])

        # Creating the security group and rules for IPv6 TCP testing
        cls.fixture_log.debug('Creating the security groups and rules')
        sg_tcp_ipv6_req = cls.sec.behaviors.create_security_group(
            name='sg_tcp_ipv6_egress',
            description='SG for testing IPv6 TCP egress rules')
        cls.sec_group_tcp_ipv6 = sg_tcp_ipv6_req.response.entity
        cls.delete_secgroups.append(cls.sec_group_tcp_ipv6.id)

        egress_tcp_ipv6_rule_req = (
            cls.sec.behaviors.create_security_group_rule(
                security_group_id=cls.sec_group_tcp_ipv6.id,
                direction='egress', ethertype='IPv6', protocol='tcp',
                port_range_min=993, port_range_max=995))
        egress_tcp_rule = egress_tcp_ipv6_rule_req.response.entity
        cls.delete_secgroups_rules.append(egress_tcp_rule.id)

        # Creating the security group rule for IPv6 UDP testing
        egress_udp_ipv6_rule_req = (
            cls.sec.behaviors.create_security_group_rule(
                security_group_id=cls.sec_group_tcp_ipv6.id,
                direction='egress', ethertype='IPv6', protocol='udp',
                port_range_min=750, port_range_max=752))
        egress_udp_rule = egress_udp_ipv6_rule_req.response.entity
        cls.delete_secgroups_rules.append(egress_udp_rule.id)

        cls.create_ping_ssh_ingress_rules(
            sec_group_id=cls.sec_group_tcp_ipv6.id)

        # Creating the security group and rules for IPv6 ICMP testing
        sg_icmp_ipv6_req = cls.sec.behaviors.create_security_group(
            name='sg_icmp_ipv6_egress',
            description='SG for testing IPv6 ICMP egress rules')
        cls.sec_group_icmp_ipv6 = sg_icmp_ipv6_req.response.entity
        cls.delete_secgroups.append(cls.sec_group_icmp_ipv6.id)

        egress_icmp_ipv6_rule_req = (
            cls.sec.behaviors.create_security_group_rule(
                security_group_id=cls.sec_group_icmp_ipv6.id,
                direction='egress', ethertype='IPv6', protocol='icmp'))
        egress_icmp_ipv6_rule = egress_icmp_ipv6_rule_req.response.entity
        cls.delete_secgroups_rules.append(egress_icmp_ipv6_rule.id)

        # ICMP ingress rules are also required to see the reply
        egress_icmp_ipv6_rule_req = (
            cls.sec.behaviors.create_security_group_rule(
                security_group_id=cls.sec_group_icmp_ipv6.id,
                direction='ingress', ethertype='IPv6', protocol='icmp'))
        egress_icmp_ipv6_rule = egress_icmp_ipv6_rule_req.response.entity
        cls.delete_secgroups_rules.append(egress_icmp_ipv6_rule.id)

        cls.create_ping_ssh_ingress_rules(
            sec_group_id=cls.sec_group_icmp_ipv6.id)

        cls.security_group_ids = [cls.sec_group_tcp_ipv6.id,
                                  cls.sec_group_icmp_ipv6.id]

        cls.sec_group_tcp_ipv6 = cls.sec.behaviors.get_security_group(
            cls.security_group_ids[0]).response.entity
        cls.sec_group_icmp_ipv6 = cls.sec.behaviors.get_security_group(
            cls.security_group_ids[1]).response.entity

        # Defining the server personas
        cls.fixture_log.debug('Defining the server personas for quick port '
                              'and IP address access')

        # Persona labels as keys and the server to create the persona as value
        persona_servers = {'lp': cls.listener, 'op': cls.other_sender,
                           'sp': cls.sender, 'spi': cls.icmp_sender}
        persona_kwargs = dict(inet=True, network=cls.network,
                              inet_port_count=1, inet_fix_ipv6_count=1)

        # Getting a dict with persona label as key and persona object as value
        personas = cls.create_multiple_personas(
            persona_servers=persona_servers, persona_kwargs=persona_kwargs)

        # Setting the personas as class attributes identified by persona label
        for persona_label, persona in personas.items():
            setattr(cls, persona_label, persona)

        # Creating personas as class attributes, for ex. cls.lp, etc.
        cls.fixture_log.debug('Defining the server personas for quick port '
                              'and IP address access')
        persona_servers = {'lp': cls.listener, 'op': cls.other_sender,
                           'sp': cls.sender, 'spi': cls.icmp_sender}
        persona_kwargs = dict(inet=True, network=cls.network,
                              inet_port_count=1, inet_fix_ipv4_count=1)

        cls.create_multiple_personas(persona_servers=persona_servers,
                                     persona_kwargs=persona_kwargs)

        # Updating server ports with security groups
        ports_to_update = [{'port_ids': [cls.sp.pnet_port_ids[0],
                                         cls.sp.snet_port_ids[0],
                                         cls.sp.inet_port_ids[0]],
                            'security_groups': [cls.security_group_ids[0]]},
                           {'port_ids': [cls.spi.pnet_port_ids[0],
                                         cls.spi.snet_port_ids[0],
                                         cls.spi.inet_port_ids[0]],
                            'security_groups': [cls.security_group_ids[1]]}]

        for ports in ports_to_update:
            cls.update_server_ports_w_sec_groups(
                port_ids=ports['port_ids'],
                security_groups=ports['security_groups'])

        # Wait time for security groups to be enabled on server ports
        delay_msg = 'data plane delay {0}'.format(
            cls.sec.config.data_plane_delay)
        cls.fixture_log.debug(delay_msg)
        time.sleep(cls.sec.config.data_plane_delay)

    def setUp(self):
        """ Creating the remote clients """
        super(SecurityGroupsEgressIPv6Test, self).setUp()
        self.fixture_log.debug('Creating the Remote Clients')
        self.lp_rc = self.servers.behaviors.get_remote_instance_client(
            server=self.listener, ip_address=self.lp.pnet_fix_ipv4[0],
            username=self.ssh_username, key=self.keypair.private_key,
            auth_strategy=self.auth_strategy)
        self.op_rc = self.servers.behaviors.get_remote_instance_client(
            server=self.other_sender, ip_address=self.op.pnet_fix_ipv4[0],
            username=self.ssh_username, key=self.keypair.private_key,
            auth_strategy=self.auth_strategy)

        self.fixture_log.debug('Sender Remote Clients require ingress and '
                               'egress rules working for ICMP and ingress '
                               'rules for TCP')
        self.sp_rc = self.servers.behaviors.get_remote_instance_client(
            server=self.sender, ip_address=self.sp.pnet_fix_ipv4[0],
            username=self.ssh_username, key=self.keypair.private_key,
            auth_strategy=self.auth_strategy)
        self.spi_rc = self.servers.behaviors.get_remote_instance_client(
            server=self.icmp_sender, ip_address=self.spi.pnet_fix_ipv4[0],
            username=self.ssh_username, key=self.keypair.private_key,
            auth_strategy=self.auth_strategy)

    @tags('publicnet', 'isolatednet')
    def test_remote_client_connectivity_v6(self):
        """
        @summary: Testing the remote clients
        """

        servers = [self.listener, self.other_sender, self.sender,
                   self.icmp_sender]
        remote_clients = [self.lp_rc, self.op_rc, self.sp_rc, self.spi_rc]

        # Empty string for servers without security group
        sec_groups = ['', '', self.sec_group_tcp_ipv6,
                      self.sec_group_icmp_ipv6]

        result = self.verify_remote_clients_auth(
            servers=servers, remote_clients=remote_clients,
            sec_groups=sec_groups)

        self.assertFalse(result)

    @tags('publicnet')
    def test_publicnet_ping_v6(self):
        """
        @summary: Testing ping from other sender without security rules
        """
        ip_address = self.lp.pnet_fix_ipv6[0]
        self.verify_ping(remote_client=self.op_rc, ip_address=ip_address,
                         ip_version=6)

    @tags('isolatednet')
    def test_isolatednet_ping_v6(self):
        """
        @summary: Testing ping from other sender without security rules
        """
        ip_address = self.lp.inet_fix_ipv6[0]
        self.verify_ping(remote_client=self.op_rc, ip_address=ip_address,
                         ip_version=6)

    @tags('publicnet')
    def test_publicnet_ping_w_icmp_egress_v6(self):
        """
        @summary: Testing ICMP egress rule on publicnet
        """
        ip_address = self.lp.pnet_fix_ipv6[0]
        self.verify_ping(remote_client=self.spi_rc, ip_address=ip_address,
                         ip_version=6)

    @tags('isolatednet')
    def test_isolatednet_ping_w_icmp_egress_v6(self):
        """
        @summary: Testing ICMP egress rule on isolatednet
        """
        ip_address = self.lp.inet_fix_ipv6[0]
        self.verify_ping(remote_client=self.spi_rc, ip_address=ip_address,
                         ip_version=6)

    @tags('publicnet')
    def test_publicnet_ports_w_tcp_v6(self):
        """
        @summary: Testing TCP ports on publicnet
        """
        self.verify_tcp_connectivity(listener_client=self.lp_rc,
                                     sender_client=self.op_rc,
                                     listener_ip=self.lp.pnet_fix_ipv6[0],
                                     port1=TCP_PORT1, port2=TCP_PORT2,
                                     port_range=TCP_PORT_RANGE,
                                     expected_data=TCP_EXPECTED_DATA,
                                     ip_version=6)

    @tags('isolatednet')
    def test_isolatednet_ports_w_tcp_v6(self):
        """
        @summary: Testing TCP ports on isolatednet
        """
        self.verify_tcp_connectivity(listener_client=self.lp_rc,
                                     sender_client=self.op_rc,
                                     listener_ip=self.lp.inet_fix_ipv6[0],
                                     port1=TCP_PORT1, port2=TCP_PORT2,
                                     port_range=TCP_PORT_RANGE,
                                     expected_data=TCP_EXPECTED_DATA,
                                     ip_version=6)

    @tags('publicnet')
    def test_publicnet_ports_w_tcp_egress_v6(self):
        """
        @summary: Testing TCP egress rule on publicnet
        """
        self.verify_tcp_connectivity(listener_client=self.lp_rc,
                                     sender_client=self.sp_rc,
                                     listener_ip=self.lp.pnet_fix_ipv6[0],
                                     port1=TCP_PORT1, port2=TCP_PORT2,
                                     port_range=TCP_PORT_RANGE,
                                     expected_data=TCP_RULE_EXPECTED_DATA,
                                     ip_version=6)

    @tags('isolatednet')
    def test_isolatednet_ports_w_tcp_egress_v6(self):
        """
        @summary: Testing TCP egress rule on isolatednet
        """
        self.verify_tcp_connectivity(listener_client=self.lp_rc,
                                     sender_client=self.sp_rc,
                                     listener_ip=self.lp.inet_fix_ipv6[0],
                                     port1=TCP_PORT1, port2=TCP_PORT2,
                                     port_range=TCP_PORT_RANGE,
                                     expected_data=TCP_RULE_EXPECTED_DATA,
                                     ip_version=6)

    @tags('isolatednet')
    def test_isolatednet_udp_port_750_v6(self):
        """
        @summary: Testing UDP from other sender without security rules
                  over isolatednet on port 750
        """

        file_content = 'Security Groups UDP 750 testing from other sender'
        expected_data = 'XXXXX{0}'.format(file_content)

        # UDP rule NOT applied to sender so the port is not limited here
        self.verify_udp_connectivity(
            listener_client=self.lp_rc, sender_client=self.op_rc,
            listener_ip=self.lp.inet_fix_ipv6[0], port=UDP_PORT_750,
            file_content=file_content, expected_data=expected_data,
            ip_version=6)

    @tags('isolatednet')
    def test_isolatednet_udp_port_749_v6(self):
        """
        @summary: Testing UDP from other sender without security rules
                  over isolatednet on port 749
        """

        file_content = 'Security Groups UDP 749 testing from other sender'
        expected_data = 'XXXXX{0}'.format(file_content)

        # Other sender server has no rules applied, both ports should work
        self.verify_udp_connectivity(
            listener_client=self.lp_rc, sender_client=self.op_rc,
            listener_ip=self.lp.inet_fix_ipv6[0], port=UDP_PORT_749,
            file_content=file_content, expected_data=expected_data,
            ip_version=6)

    @tags('isolatednet')
    def test_isolatednet_udp_port_750_w_udp_egress_v6(self):
        """
        @summary: Testing UDP from sender with security egress rules on
                  port 750 that is part of the egress rule
        """

        file_content = 'Security Groups UDP 750 testing from sender'
        expected_data = 'XXXXX{0}'.format(file_content)

        self.verify_udp_connectivity(
            listener_client=self.lp_rc, sender_client=self.sp_rc,
            listener_ip=self.lp.inet_fix_ipv6[0], port=UDP_PORT_750,
            file_content=file_content, expected_data=expected_data,
            ip_version=6)

    @tags('isolatednet')
    def test_isolatednet_udp_port_749_w_udp_egress_v6(self):
        """
        @summary: Testing UDP from sender with security egress rules on
                  port 749 that is NOT part of the egress rule
        """

        file_content = 'Security Groups UDP 749 testing from other sender'
        expected_data = ''

        # Port 749 NOT within rule, data should not be transmitted
        self.verify_udp_connectivity(
            listener_client=self.lp_rc, sender_client=self.sp_rc,
            listener_ip=self.lp.inet_fix_ipv6[0], port=UDP_PORT_749,
            file_content=file_content, expected_data=expected_data,
            ip_version=6)

    @tags('publicnet')
    def test_publicnet_udp_port_750_v6(self):
        """
        @summary: Testing UDP from other sender without security rules
                  over publicnet on port 750
        """

        file_content = 'Security Groups UDP 750 testing from other sender'
        expected_data = 'XXXXX{0}'.format(file_content)

        # UDP rule NOT applied to sender so the port is not limited here
        self.verify_udp_connectivity(
            listener_client=self.lp_rc, sender_client=self.op_rc,
            listener_ip=self.lp.pnet_fix_ipv6[0], port=UDP_PORT_750,
            file_content=file_content, expected_data=expected_data,
            ip_version=6)

    @tags('publicnet')
    def test_publicnet_udp_port_749_v6(self):
        """
        @summary: Testing UDP from other sender without security rules
                  over publicnet on port 749
        """

        file_content = 'Security Groups UDP 749 testing from other sender'
        expected_data = 'XXXXX{0}'.format(file_content)

        # Other sender server has no rules applied, both ports should work
        self.verify_udp_connectivity(
            listener_client=self.lp_rc, sender_client=self.op_rc,
            listener_ip=self.lp.pnet_fix_ipv6[0], port=UDP_PORT_749,
            file_content=file_content, expected_data=expected_data,
            ip_version=6)

    @tags('publicnet')
    def test_publicnet_udp_port_750_w_udp_egress_v6(self):
        """
        @summary: Testing UDP from sender with security egress rules on
                  port 750 that is part of the egress rule
        """

        file_content = 'Security Groups UDP 750 testing from sender'
        expected_data = 'XXXXX{0}'.format(file_content)

        self.verify_udp_connectivity(
            listener_client=self.lp_rc, sender_client=self.sp_rc,
            listener_ip=self.lp.pnet_fix_ipv6[0], port=UDP_PORT_750,
            file_content=file_content, expected_data=expected_data,
            ip_version=6)

    @tags('publicnet')
    def test_publicnet_udp_port_749_w_udp_egress_v6(self):
        """
        @summary: Testing UDP from sender with security egress rules on
                  port 749 that is NOT part of the egress rule
        """

        file_content = 'Security Groups UDP 749 testing from other sender'
        expected_data = ''

        # Port 749 NOT within rule, data should not be transmitted
        self.verify_udp_connectivity(
            listener_client=self.lp_rc, sender_client=self.sp_rc,
            listener_ip=self.lp.pnet_fix_ipv6[0], port=UDP_PORT_749,
            file_content=file_content, expected_data=expected_data,
            ip_version=6)
