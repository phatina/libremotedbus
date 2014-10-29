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

'''
Cockpit Client setup script.
'''

from setuptools import setup


setup(
    name='cockpit-client',
    description='Cockpit Client',
    version='0.0.1',
    license='GPLv2+',
    url='https://github.com/phatina/libcockpitclient',
    author='Peter Hatina',
    author_email='phatina@redhat.com',
    classifiers=[
        'License :: OSI Approved :: GNU General Public License v2 or later (GPLv2+)',
        'Operating System :: POSIX :: Linux',
        'Topic :: System :: Systems Administration',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.2',
        'Intended Audience :: Developers',
        'Environment :: Console',
    ],
    install_requires=['websocket-client >= 0.14.1'],
    namespace_packages=['cockpit'],
    packages=(
        [ 'cockpit'
        , 'cockpit.client'
        , 'cockpit.client.http'
        , 'cockpit.client.sock'
        , 'cockpit.remote'
    ]),
    scripts=['example']
)
