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

import os
import socket
import ssl
import sys
import websocket

from cockpit.client.http import parse_url


class WebSocket(websocket.WebSocket):
    '''
    WebSocket class based on websocket. It overrides few method due to lack of
    some specific API we use.
    '''

    def connect(self, url, **options):
        '''
        See websocket.WebSocket.connect(). This overriden method exists, because
        python-websocket-client-0.14.1 can't turn off certificate verification.
        Other difference is, that no handshake is performed in this call. User
        needs to call WebSocket.handshake() by hand.
        '''

        self.scheme,       \
            self.hostname, \
            self.port,     \
            self.resource, \
            is_secure = parse_url(url)

        proxy_host = options.get('http_proxy_host', None)
        proxy_port = options.get('http_proxy_port', 0)
        if not proxy_host:
            addrinfo_list = socket.getaddrinfo(self.hostname, self.port, 0, 0, socket.SOL_TCP)
        else:
            proxy_port = proxy_port and proxy_port or 80
            addrinfo_list = socket.getaddrinfo(proxy_host, proxy_port, 0, 0, socket.SOL_TCP)

        if not addrinfo_list:
            raise WebSocketException('Host not found.: ' + hostname + ':' + str(port))

        family = addrinfo_list[0][0]
        self.sock = socket.socket(family)
        self.sock.settimeout(self.timeout)
        for opts in websocket.DEFAULT_SOCKET_OPTION:
            self.sock.setsockopt(*opts)
        for opts in self.sockopt:
            self.sock.setsockopt(*opts)

        # TODO: we need to support proxy
        address = addrinfo_list[0][4]
        self.sock.connect(address)

        if proxy_host:
            self._tunnel(self.hostname, self.port)

        if is_secure:
            if websocket.HAVE_SSL:
                sslopt = dict(cert_reqs=ssl.CERT_REQUIRED,
                              ca_certs=os.path.join(os.path.dirname(__file__), 'cacert.pem'))
                sslopt.update(self.sslopt)
                self.sock = ssl.wrap_socket(self.sock, **sslopt)
                if sslopt['cert_reqs'] != ssl.CERT_NONE:
                    websocket.match_hostname(self.sock.getpeercert(), self.hostname)
            else:
                raise WebSocketException('SSL not available.')

    def handshake(self, **options):
        scheme = options.pop('scheme', self.scheme)
        hostname = options.pop('hostname', self.hostname)
        port = options.pop('port', self.port)

        options['origin'] = '%s://%s:%s' % (scheme, hostname, port)

        self._handshake(hostname, port, self.resource, **options)
