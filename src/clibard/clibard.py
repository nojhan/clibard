#!/usr/bin/env python3

from enum import IntEnum
import datetime

import dbus
import gi.repository.GLib
from dbus.mainloop.glib import DBusGMainLoop

def receive(bus, notification):
    # print(notification, flush = True)
    # print("---------------------------------------------", flush = True)
    # print("Member:", notification.get_member(), flush = True)
    # print("Interface:", notification.get_interface(), flush = True)

    if notification.get_member() == "Notify" and notification.get_interface() == 'org.freedesktop.Notifications':
        # print("Notification")
        args = notification.get_args_list()
        # print("Args list:", args, flush = True)

        app = str(args[0])
        replaces_id = int(args[1])
        # icon = str(args[2])
        summary = str(args[3])
        body = str(args[4])
        actions = args[5]
        hints = dict(args[6])
        expire_timeout = int(args[7])

        date = datetime.datetime.now()
        urgency = {0: "low", 1: "normal", 2: "critical", None: "unknown"}

        print(f"[{date}][{app}]:\n\t{summary}\n\t« {body} »", flush=True)


if __name__ == "__main__":
    DBusGMainLoop(set_as_default=True)

    bus = dbus.SessionBus()
    bus.add_match_string_non_blocking("eavesdrop=true, interface='org.freedesktop.Notifications', member='Notify'")
    bus.add_message_filter(receive)

    mainloop = gi.repository.GLib.MainLoop()
    mainloop.run()

