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

import base64
import hashlib
import hmac
import json
import random


# XXX: received unknown/invalid credential cookie
def make_auth_cookie():
    '''
    Creates an authentication cookie for /login.
    '''
    try:
        urandom = open('/dev/urandom', 'rb')
        key = urandom.read(128)
        urandom.close()

    except IOError:
        return ''

    if not hasattr(make_auth_cookie, 'nonce_seed'):
        random.seed()
        make_auth_cookie.nonce_seed = int(random.random() * 10**16)
    else:
        make_auth_cookie.nonce_seed += 1

    nonce_seed = make_auth_cookie.nonce_seed
    hmac_id = hmac.HMAC(key, str(nonce_seed), hashlib.sha256).digest()

    cookie = 'v=2;k=%s' % hmac_id

    return base64.b64encode(cookie)


def make_auth_credentials(username, password):
    '''
    Creates a basic authorization credentials.
    '''
    return base64.b64encode(username + ':' + password)


def make_json(**kw):
    '''
    Creates a JSON encoded string from kwargs.
    '''
    keys = {k.replace('_', '-'): v for k, v in kw.iteritems() if v is not None}
    return json.dumps(keys)

def read_json(json_msg):
    '''
    Returns decoded JSON object.
    '''
    return json.loads(json_msg)
