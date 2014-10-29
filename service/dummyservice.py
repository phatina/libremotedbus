#!/usr/bin/python

import dbus
import dbus.service
import dbus.mainloop.glib
import gobject


class DummyService(dbus.service.Object):
    '''
    Dummy D-Bus service.
    '''
    def __init__(self):
        bus_name = dbus.service.BusName('org.dummy.service', bus=dbus.SystemBus())
        dbus.service.Object.__init__(self, bus_name, '/org/dummy/service')

    @dbus.service.method(
        'org.dummy.service',
        out_signature='s')
    def DummyMethod(self, *args, **kwargs):
        '''
        Dummy method.
        '''
        print 'DummyMethod() called with', args, kwargs
        return 'some return value'


if __name__ == '__main__':
    dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)

    loop = gobject.MainLoop()

    # Instantiate a dummy service.
    service = DummyService()

    try:
        # Run in a event loop.
        loop.run()
    except KeyboardInterrupt:
        print '\rQuitting...'
        loop.quit()
