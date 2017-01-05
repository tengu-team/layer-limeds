#!/usr/bin/env python3 pylint:disable=c0111
# Copyright (C) 2016  Ghent University
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

import pwd
import os

from subprocess import check_call

from charmhelpers.core import hookenv, unitdata

from charms.reactive import hook
from charms.reactive import when, when_not
from charms.reactive import set_state, remove_state, is_state

@hook('config.changed')
def reconfigure_docker_host():
    hookenv.log(hookenv.relation_get('dockerhost'))
    if is_state('dockerhost.available') and is_state('limeds.ready'):
        conf = hookenv.config()
        hookenv.status_set('maintenance', 'Reconfiguring LimeDS [{}].'.format(conf.get('image')))
        remove_state('limeds.ready')

@when_not('dockerhost.available')
def no_host_connected():
    hookenv.status_set('blocked', 'Please connect the LimeDS charm to a docker host.')
    if is_state('limeds.ready'):
        remove_state('limeds.ready')

@when('dockerhost.available')
@when_not('limeds.ready')
def host_connected(dh):
    conf = hookenv.config()
    hookenv.log('configure_docker_host invoked for unit {}!!'.format(hookenv.local_unit()))
    hookenv.status_set('maintenance', 'Sending configuration to host.')
    
    name = hookenv.local_unit().replace("/","-")
    ports = ['8080', '8443']
    docker_host, docker_host_ports = dh.send_configuration(name, conf.get('image'), ports, conf.get('username'), \
                                                           conf.get('secret'), True, True)
    kv = unitdata.kv()
    kv.set('docker_host', docker_host)
    kv.set('docker_host_ports', docker_host_ports)

    hookenv.log('The IP of the docker host is {}.'.format(docker_host))

    hookenv.status_set('active', 'LimeDS [{}] ready.'.format(conf.get('image')))
    set_state('limeds.ready')
    
@when('endpoint.available', 'limeds.ready')
def configure_endpoint(endpoint):
    #endpoint.configure(port=hookenv.config('http_port'))
    kv = unitdata.kv()
    docker_host = kv.get('docker_host')
    docker_host_ports = kv.get('docker_host_ports')
    hookenv.log('The IP of the docker host is {}.'.format(docker_host))
    relation_info = {
        'hostname': docker_host,
        'port': docker_host_ports['8080'],
    }
    endpoint.set_remote(**relation_info)

