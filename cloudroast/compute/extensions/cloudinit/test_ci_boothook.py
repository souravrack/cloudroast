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

import base64

from cafe.drivers.unittest.decorators import tags
from cloudcafe.common.tools.datagen import rand_name
from cloudroast.compute.fixtures import ComputeFixture


class CloudInitBoothookTest(ComputeFixture):

    @classmethod
    def setUpClass(cls):
        """
        Perform actions that setup the necessary resources for testing.

        The following resources are created during this setup:
            - Creates a keypair.
            - Creates an active server.
        """
        super(CloudInitBoothookTest, cls).setUpClass()
        init_st = cls.config_drive_behaviors.read_cloud_init_for_config_drive(
            cls.cloud_init_config.boothook_script)
        cls.user_data_contents = init_st
        user_data = base64.b64encode(cls.user_data_contents)
        cls.key = cls.keypairs_client.create_keypair(rand_name("key")).entity
        cls.resources.add(cls.key.name,
                          cls.keypairs_client.delete_keypair)
        cls.server_response = cls.server_behaviors.create_active_server(
            config_drive=True,
            key_name=cls.key.name,
            user_data=user_data)
        cls.server = cls.server_response.entity
        cls.user_data_filepath = '{0}/openstack/latest/user_data'.format(
            cls.config_drive_config.base_path_to_mount)
        cls.resources.add(cls.server.id,
                          cls.servers_client.delete_server)

    @tags(type='smoke', net='yes')
    def test_boothook_input_format(self):
        """
        Verify the Cloud Boothook Input Format is working as expected.

        Will mount the config drive then get the remote instance to be able
        to get the file details.  After verifying the contents of the file
        are as expected, verify that the user data directory exists and the
        part-001 file is in the directory.

        The following assertions occur:
            - 200 status code response from the create server call.
            - Content of the user data file retrieved is the same as set in
                setup.
            - The part-001 file is present in the user data directory.
            - The content of the part-001 file has a word.
        """
        message = "Expected {0} to be {1}, was {2}."
        self.config_drive_behaviors.mount_config_drive(
            server=self.server, servers_config=self.servers_config,
            key=self.key.private_key,
            source_path=self.config_drive_config.mount_source_path,
            destination_path=self.config_drive_config.base_path_to_mount)
        remote_client = self.server_behaviors.get_remote_instance_client(
            self.server, self.servers_config, key=self.key.private_key)
        instanse_user_data = remote_client.get_file_details(
            self.user_data_filepath)
        self.assertEqual(instanse_user_data.content,
                         self.user_data_contents,
                         msg=message.format('Configuration do not match',
                                            instanse_user_data.content,
                                            self.user_data_contents))
        boothook_file_present = remote_client.is_file_present(
            "/var/lib/cloud/instances/{0}/boothooks/part-001".format(
                self.server.id))
        self.assertTrue(boothook_file_present,
                        msg="Boothook file present on the instance")
        boothook = remote_client.get_file_details(
            "/var/lib/cloud/instances/{0}/boothooks/part-001".format(
                self.server.id)).content
        self.assertIn('hello_boothook!', boothook,
                      msg="boothook script is processed")
