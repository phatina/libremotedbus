# ##### BEGIN LICENSE BLOCK #####
#
# Copyright (C) 2014 Peter Hatina <phatina@redhat.com>
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, see <http://www.gnu.org/licenses/>.
#
# ##### END LICENSE BLOCK #####

import ssl
import struct

from cockpit.client import constants
from cockpit.client import http
from cockpit.client import util
from cockpit.client.channel import DBusChannel
from cockpit.client.sock import WebSocket


class CockpitError(Exception):
    '''
    Base CockpitClient exception class.
    '''


class CockpitProtocolError(CockpitError):
    '''
    Cockpit protocol exception class.
    '''


class CockpitClient(object):
    '''
    Cockpit client class which implements (part of) Cockpit protocol.
    '''

    def __init__(self, url, no_verification=False, debug=False):
        sslopt = {}
        if no_verification:
            sslopt['cert_reqs'] = ssl.CERT_NONE
        self.channel_seed = 0
        self.creds = None
        self.debug = debug
        self.url = url
        self.ws = WebSocket(sslopt=sslopt)

    @property
    def is_connected(self):
        '''
        Property returning whether a CockpitClient is connected to cockpit-ws.
        '''
        return self.ws.sock is not None

    def connect(self, username, password):
        '''
        Connects to a cockpit-ws. Performs /login and WebSockets handshake.
        Verifies, if init command was issued. When an unsuccessful login is
        issued, CockpitProtocolError is raised.
        '''
        # Connect to cockpit-ws.
        self.ws.connect(self.url)

        # Do a /login, retrieve a cookie.
        cookie = self.login(username, password)

        # Perform a WebSocket handshake.
        self.ws.handshake(header=['Cookie: cockpit=%s' % cookie])

        # Check for init command. This is the first and required command sent
        # by cockpit-ws, which opens the session.
        chan_id, resp = self.recv_message()
        resp = util.read_json(resp)
        if chan_id not in ('', '0') or resp['command'] != 'init':
            raise CockpitProtocolError(-1, 'Missing init message from cockpit-ws')

        # Store channel seed, which will be used later for channel opening.
        self.channel_seed = int(resp['channel-seed'])

        # Respond to init command also with init.
        self.send_init_message(resp['version'])

        return resp

    def disconnect(self):
        '''
        Logs out and Disconnects from cockpit-ws.
        '''
        # Send logout command.
        self.logout()

        # Disconnect from cockpit-ws.
        self.ws.close()

    def login(self, username, password):
        '''
        Performs a login to cockpit-ws.
        '''
        assert self.is_connected, 'connect() must precede a login()'

        sock = self.ws.sock

        # Send a /login request.
        http.send_message(
            http.HTTPMessage(
                http.HTTPRequestLine('GET', '/login', http.HTTP_1_1), {
                    'Host':  '%s:%s' % (self.ws.hostname, self.ws.port),
                    'Cookie': 'cockpit=%s' % util.make_auth_cookie(),
                    'Authorization': 'Basic %s' % util.make_auth_credentials(
                        username, password),
                    'Connection': 'keep-alive',
                }),
            sock)

        # Receive a /login response.
        msg_login_resp = http.recv_message(sock)
        if not http.is_success(msg_login_resp):
            http.raise_from_message(msg_login_resp)

        # Extract a cookie
        try:
            cookie_header = msg_login_resp['Set-Cookie']
            cookie = cookie_header.split('cockpit=', 1)[1].split(';', 1)[0]
        except (KeyError, TypeError, IndexError):
            raise http.HTTPError(-1, 'Missing Cockpit cookie')

        # After a successful login, store current credentials.
        self.creds = (username, password)

        return cookie

    def logout(self, close_connection=True):
        '''
        Logs out from cockpit-ws. If close_connection is True, websocket will
        be also closed.
        '''
        if self.creds is None:
            # Nothing to do here.
            return

        self.send_control_message(
            util.make_json(
                command='logout',
                disconnect=close_connection))

        self.creds = None

    def ping(self):
        '''
        Sends a ping command.
        '''
        self.send_control_message(util.make_json(command='ping'))

    def get_next_channel_id(self):
        '''
        Returns a next unique channel ID.
        '''
        # Simplest method for unique channel ID.
        self.channel_seed += 1
        return str(self.channel_seed)

    def send_init_message(self, version):
        '''
        Sends a init command.
        '''
        self.send_control_message(
            util.make_json(
                command='init',
                version=0))

    def send_message(self, channel_id, data):
        '''
        Sends a message via channel_id.
        '''
        frame = '%s\n%s' % (str(channel_id), data)

        if self.debug:
            print '-' * 80
            print 'Channel:', channel_id if channel_id else 'control'
            print 'Payload:', data
            print '-' * 80
            print

        self.ws.send(frame.encode('utf8'))

    def send_control_message(self, payload):
        '''
        Sends a message via control channel.
        '''
        self.send_message('', payload)

    def recv_message(self):
        '''
        Receives a message. Returns a channel ID and a message.
        '''
        return self.ws.recv().split('\n', 1)

    def open_channel(self, *args, **kwargs):
        '''
        Opens a new channel. Channel ID is generated. See
        CockpitClient.open_channel_with_id().
        '''
        return self.open_channel_with_id(
            self.get_next_channel_id(),
            *args,
            **kwargs)

    def open_channel_with_id(self, channel_id, payload_type, user=None,
                             password=None, host=None, host_key=None,
                             **kwargs):
        '''
        Opens a new channel with channel_id and payload_type.
        '''
        self.send_control_message(
            util.make_json(
                command='open',
                channel=channel_id,
                payload=payload_type,
                host=host,
                user=user,
                **kwargs))

        # XXX: Stef: Always get a response about channel open status. Not only,
        # when an error occurs.

        return channel_id


    def open_channel_dbus_json3(self, *args, **kwargs):
        '''
        Opens a new dbus-json3 channel. Channel ID is generated. See
        CockpitClient.open_channel_dbus_json_with_id().
        '''
        return self.open_channel_dbus_json3_with_id(
            self.get_next_channel_id(),
            *args,
            **kwargs)

    def open_channel_dbus_json3_with_id(self, channel_id, bus, service,
                                        **kwargs):
        '''
        Opens a new dbus-json3 channel with channel_id for a dbus service,
        running at bus and identified by service.
        '''
        self.open_channel_with_id(
            channel_id,
            constants.PAYLOAD_DBUS_JSON3,
            bus=bus,
            name=service,
            **kwargs)

        return channel_id

    def close_channel_with_id(self, channel_id, closing_reason=''):
        '''
        Closes a channel_id channel with closing_reason.
        '''
        self.send_control_message(
            util.make_json(
                command='close',
                channel=str(channel_id),
                reason=closing_reason))
