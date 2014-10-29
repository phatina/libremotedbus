# ##### BEGIN LICENSE BLOCK #####
#
# Copyright (C) 2014 Peter Hatina <phatina@redhat.com>
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.  #
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, see <http://www.gnu.org/licenses/>.
#
# ##### END LICENSE BLOCK #####

from cockpit.client import CockpitClient
from cockpit.client import util


class RemoteDBus(object):
    '''
    Class for D-Bus remoting via Cockpit.
    '''

    def __init__(self, url, username, password, service, no_verification=False,
                 bus='session', debug=False):
        self.client = CockpitClient(url, no_verification, debug)
        self.client.connect(username, password)
        self.channel_id = self.client.open_channel_dbus_json3(
            username=username, password=password,
            bus=bus, service=service)

    def close(self):
        '''
        Closes a channel and disconnects from cockpit-ws.
        '''
        self.client.close_channel_with_id(self. channel_id)
        self.client.disconnect()

    def __call__(self, path, interface, method, args, require_response=True):
        '''
        Performs a remote D-Bus call.
        '''
        self.client.send_message(
            self.channel_id,
            util.make_json(
                call=[path, interface, method, args],
                id='cookie' if require_response else None))

        if require_response:
            # TODO: implement
            return self.client.recv_message()
