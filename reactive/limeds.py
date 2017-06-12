#!/usr/bin/env python3
# Copyright (C) 2017  Ghent University
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
import sys
from time import sleep
from uuid import uuid4
import requests

from charmhelpers.core import hookenv, unitdata
from charmhelpers.core.hookenv import status_set, log

from charms.reactive import when, when_not, set_state, remove_state
from charms.reactive.helpers import data_changed


@when('dockerhost.available')
@when_not('limeds.ready')
def limeds_running(dh_relation):
    conf = hookenv.config()
    containers = dh_relation.get_running_containers()
    if containers:
        for unit, container in containers.items():
            wait_until_limeds_initialised('http://{}:{}'.format(
                container['host'],
                container['ports']['8080'], ))
        status_set('active', 'Ready ({})'.format(conf.get('image')))
        set_state('limeds.ready')


@when(
    'limeds.ready',
    'dockerhost.available',
    'endpoint.available', )
def configure_endpoint_relationship(dh_relation, endpoint_relation):
    """ Note: this is a relationship with a CLIENT consuming the LimeDS http interface."""
    containers = dh_relation.get_running_containers()
    # WARNING! This will only send the info of the last container!
    for container in containers:
        endpoint_relation.configure(
            hostname=container['host'],
            private_address=container['host'],
            port=container['ports']['8080'])


@when(
    'limeds.ready',
    'dockerhost.available',
    'limeds-server.available', )
def configure_client_relationship(dh_relation, limeds_server_relation):
    """ Note: this is a relationship with a CLIENT consuming LimeDS."""
    containers = dh_relation.get_running_containers()
    # WARNING! This will only send the info of the last container!
    for container in containers:
        limeds_server_relation.configure(
            'http://{}:{}'.format(
                container['host'],
                container['ports']['8080'], )
        )


@when(
    'limeds-server.available', )
@when_not(
    'limeds.ready', )
def reset_client_relationship(limeds_server_relation):
    """ Note: this is a relationship with a CLIENT consuming LimeDS."""
    limeds_server_relation.reset()


def wait_until_limeds_initialised(base_url):
    status_set('waiting', 'Waiting for LimeDS to complete initialisation.')
    deploy_url = get_deploy_url(
                     base_url=base_url, 
                     installable_id="org.ibcn.limeds.codecs.base64",
                     installable_version="latest")
    print("Waiting for LimeDS to complete initialisation.. This shouldn't take long.")
    print(deploy_url)
    success = False
    while not success:
        try:
            response = requests.put(deploy_url)
            if response.status_code == 200:
                success = True
            else:
                print(response.status_code)
                print(response.text)
        except (requests.exceptions.ConnectionError) as err:
            print(err)
            print("retrying..")
        sys.stdout.flush()
        if not success:
            sleep(1)
    print('LimeDS is initialised!')


def get_deploy_url(base_url, installable_id, installable_version):
    deploy_url = "{limeds_url}/_limeds/installables"\
                 "/{installable_id}/{installable_version}".format(
                     limeds_url=base_url,
                     installable_id=installable_id,
                     installable_version=installable_version)
    return deploy_url
