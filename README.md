Remote D-Bus
============

This project is a **Proof of Concept** for D-Bus remoting via
[Cockpit][cockpit].  This isn't a final implementation, nor full-feature
Cockpit client.  If we decide to continue, compiled language will be certainly
chosen.


Background
----------

D-Bus remoting is implemented as forwarding D-Bus calls via Cockpit's
*dbus-json3* payload.  No other payloads are used.

**NOTE:** For further information, see [Cockpit][cockpit] or
[Cockpit][cockpitswalter].


Example of usage
----------------

This section briefly illustrates how to create a `RemoteDBus` and perform a
remote D-Bus call.  The example also uses a Dummy D-Bus service (it's
implementation can be found in the source tree).

``` python
from cockpit.remote import RemoteDBus

# Create a remote D-Bus object for a dummy service.
remote = RemoteDBus(
    url='ws://hostname:9090/socket',
    username='admin',
    password='h4x0r',
    service='org.dummy.service',
    bus='system',
    no_verification=True,
    debug=False)

# Perform a remote D-Bus call.
print remote(
    '/org/dummy/service',
    'org.dummy.service',
    'org.dummy.service.DummyMethod',
    [],
    require_response=False)

# Close the session.
remote.close()
```

[cockpit]: https://github.com/cockpit-project/cockpit
[cockpitswalter]: https://github.com/stefwalter/cockpit
