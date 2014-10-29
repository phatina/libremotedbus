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

import socket
import urlparse
from BaseHTTPServer import BaseHTTPRequestHandler
from collections import OrderedDict

# HTTP responses dict.
responses = BaseHTTPRequestHandler.responses

# HTTP string versions
HTTP_0_9 = 'HTTP/0.9'
HTTP_1_0 = 'HTTP/1.0'
HTTP_1_1 = 'HTTP/1.1'

# HTTP message types
HTTP_REQUEST, HTTP_RESPONSE = range(2)

# HTTP headers with values.
HEADER_NAME_CONTENT_LENGTH = 'Content-Length'
HEADER_NAME_CONTENT_TYPE = 'Content-Type'
HEADER_NAME_TRANSFER_ENCODING = 'Transfer-Encoding'
HEADER_VALUE_CHUNKED = 'chunked'
HEADER_VALUE_CONTENT_LANGUAGE = 'Content-Language'

CRLF = '\r\n'

# RFC 2616 doesn't define chunk size limit. Let's pick one.
CHUNK_MAX = 4 * 1024


class HTTPError(Exception):
    '''
    cockpit.client.http exception.
    '''


class HTTPInitialLine(object):
    def __init__(self, http_version):
        self.http_version = http_version


class HTTPRequestLine(HTTPInitialLine):
    '''
    HTTP request line object.
    '''
    def __init__(self, method, uri, http_version):
        super(HTTPRequestLine, self).__init__(http_version)
        self.method = method
        self.uri = uri

    def __str__(self):
        return '%s %s %s' % (self.method, self.uri, self.http_version)


class HTTPResponseLine(HTTPInitialLine):
    '''
    HTTP respone line object.
    '''
    def __init__(self, http_version, status_code, reason_phrase=''):
        super(HTTPResponseLine, self).__init__(http_version)
        self.status_code = status_code
        self.reason_phrase = reason_phrase

    def __str__(self):
        if self.http_version in (HTTP_1_0, HTTP_1_1):
            response = '%s %d' % (self.http_version, self.status_code)
            if self.status_code in responses:
                response += ' %s' % responses[self.status_code][0]
        elif http_version == HTTP_0_9:
            response = '%s %d' % (self.http_version, self.status_code)
        return response


class HTTPMessage(object):
    '''
    HTTP message class.
    '''

    def __init__(self, init_line, headers=None, body=None):
        self.init_line = init_line
        self.headers = OrderedDict(headers or {})
        self.body = body or ''

    def __getitem__(self, name):
        '''
        Returns a HTTP header.
        '''
        return self.headers[name]

    def __setitem__(self, name, value):
        '''
        Updates or adds a new HTTP header.
        '''
        self.headers[name] = value

    @property
    def http_version(self):
        '''
        Returns HTTP version of the message.
        '''
        return self.init_line.http_version

    @property
    def is_chunked(self):
        '''
        Returns True, if the headers contain 'chunked' encoding entry.
        '''
        return is_chunked(self.headers)


class HTTPSender(object):
    '''
    Helper class for HTTP message sending
    '''

    def __init__(self, message, wfile):
        self.message = message

        if isinstance(wfile, socket.socket):
            self.wfile = wfile.makefile()
        else:
            self.wfile = wfile

    def send_data(self, data):
        self.wfile.write(data)

    def send_crlf(self):
        '''
        Sends CRLF symbols.
        '''
        self.send_data(CRLF)

    def send_chunk(self, chunk=''):
        '''
        Sends a one chunk of the message.
        '''
        self.send_data('%x' % len(chunk))
        self.send_data(CRLF)
        self.send_data(chunk)
        self.send_data(CRLF)

    def send_message_body(self):
        '''
        Sends a response body.
        '''
        if not self.message.is_chunked or \
                self.message.http_version != HTTP_1_1:
            self.send_data(self.message.body)
        else:
            pos = 0
            msg_len = len(self.message.body)
            while pos < msg_len:
                if msg_len - pos >= CHUNK_MAX:
                    to_send = CHUNK_MAX
                else:
                    to_send = msg_len - pos
                # Send a chunk of data.
                self.send_chunk(self.message.body[pos:pos+to_send])
                pos += to_send

            # Terminating chunk
            self.send_chunk()

    def send_header(self, name, value):
        '''
        Sends a HTTP header.
        '''
        if self.message.http_version == HTTP_0_9:
            return
        self.send_data('%s: %s' % (name, value))
        self.send_crlf()

    def send_end_headers(self):
        '''
        Sends HTTP headers terminator.
        '''
        if self.message.http_version == HTTP_0_9:
            return
        self.send_crlf()

    def send_message_headers(self):
        '''
        Sends HTTP headers.
        '''
        for name, value in self.message.headers.iteritems():
            self.send_header(name, value)
        self.send_end_headers()

    def send_message_init_line(self):
        '''
        Sends a HTTP response status line.
        '''
        self.send_data(str(self.message.init_line))
        self.send_crlf()

    def send(self):
        '''
        Sends a response header and message.
        '''
        self.send_message_init_line()
        self.send_message_headers()
        self.send_message_body()


class HTTPReader(object):
    '''
    HTTP message reader.
    '''
    def __init__(self, rfile):
        if isinstance(rfile, socket.socket):
            self.rfile = rfile.makefile()
        else:
            self.rfile = rfile

    def recv_data(self, length):
        return self.rfile.read(length)

    def recv_data_line(self):
        return self.rfile.readline()

    def recv_init_line(self):
        '''
        Reads a initial line of the HTTP message. Returns a HTTPInitialLine
        object.
        '''
        init_line = self.recv_data_line().rstrip(CRLF)

        if init_line.startswith('HTTP'):
            # We got a HTTP response
            status_line = init_line.split(' ', 2)

            http_version = status_line[0]
            status_code = int(status_line[1])
            reason_phrase = ''
            if http_version in (HTTP_1_1, HTTP_1_0) and len(status_line) == 3:
                reason_phrase = status_line[2]
            rval = HTTPResponseLine(http_version, status_code, reason_phrase)
        else:
            # We got a HTTP Request
            method, uri, http_version = init_line.split(' ')
            rval = HTTPRequestLine(method, uri, http_version)

        return rval

    def recv_headers(self):
        '''
        Reads HTTP headers. Returns a dict containing those headers.
        '''
        def get_next_header_line():
            return self.recv_data_line().rstrip(CRLF)

        headers = {}
        while True:
            header_line = get_next_header_line()
            if not header_line:
                break

            name, value = header_line.split(':', 1)
            headers[name] = value.lstrip()

        return headers

    def recv_body_chunked(self):
        '''
        Reads a chunked HTTP body.
        '''
        def get_next_chunk():
            chunk_size = int(self.recv_data_line().rstrip(CRLF), base=16)
            chunk = self.recv_data(chunk_size)
            self.recv_data(2)  # Read the last CRLF before next chunk.
            return chunk

        message = ''
        while True:
            buf = get_next_chunk()
            if not buf:
                break
            message += buf

        return message

    def recv_body(self, headers):
        '''
        Reads a HTTP body.
        '''
        content_length = int(headers.get(HEADER_NAME_CONTENT_LENGTH, '0'))
        chunked = is_chunked(headers)

        if content_length:
            return self.rfile.read(content_length)
        elif chunked:
            return self.recv_body_chunked()
        else:
            block_size = 1024
            def get_next_block():
                return self.rfile.read(block_size)

            message = ''
            while True:
                buf = get_next_block()
                if len(buf) != block_size:
                    break
                message += buf

        return message

    def recv(self):
        '''
        Reads a HTTP message and returns a HTTPMessage object.
        '''
        init_line = self.recv_init_line()
        headers = self.recv_headers()
        body = self.recv_body(headers)

        return HTTPMessage(init_line, headers, body)


def parse_url(url):
    '''
    Returns a tuple containing scheme, hostname, port, resource and boolean
    flag, if the scheme is secure.
    '''
    if ':' not in url:
        raise ValueError('url is invalid')

    scheme, url = url.split(':', 1)

    parsed = urlparse.urlparse(url, scheme='http')
    if parsed.hostname:
        hostname = parsed.hostname
    else:
        raise ValueError('hostname is invalid')
    port = 0
    if parsed.port:
        port = parsed.port

    is_secure = False
    if scheme in ('http', 'ws'):
        scheme = 'http'
        if not port:
            port = 80
    elif scheme in ('https', 'wss'):
        scheme = 'https'
        is_secure = True
        if not port:
            port = 443
    else:
        raise ValueError('scheme %s is invalid' % scheme)

    if parsed.path:
        resource = parsed.path
    else:
        resource = '/'

    if parsed.query:
        resource += '?' + parsed.query

    return scheme, hostname, port, resource, is_secure


def is_chunked(headers):
    return headers.get(
        HEADER_NAME_TRANSFER_ENCODING) == \
        HEADER_VALUE_CHUNKED or \
        headers.get(
            HEADER_NAME_TRANSFER_ENCODING.lower()) == \
            HEADER_VALUE_CHUNKED

def is_success(message):
    '''
    Returns True, if response HTTP message is of success type.
    '''
    if not isinstance(message.init_line, HTTPResponseLine):
        return False
    status_code = message.init_line.status_code
    return status_code >= 200 and status_code < 300


def send_message(message, wfile):
    '''
    Sends a HTTP message.
    '''
    sender = HTTPSender(message, wfile)
    sender.send()



def recv_message(rfile):
    '''
    Receives a HTTP message.
    '''
    reader = HTTPReader(rfile)
    return reader.recv()


def raise_from_message(message):
    '''
    Raises a HTTPError from HTTPMessage object.
    '''
    raise HTTPError(
        message.init_line.status_code,
        message.init_line.reason_phrase)
