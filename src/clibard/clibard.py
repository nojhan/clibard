#!/usr/bin/env python3

import collections
# import rich
from rich.console import Console
import humanize
import datetime
from enum import IntEnum

import dbus
import gi.repository.GLib
from dbus.mainloop.glib import DBusGMainLoop

class N:
    def __init__(self, app = "my app", summary = "my summary", body = "my (potentially longer) body"):
        self.member = "Notify"
        self.interface = "org.freedesktop.Notifications"
        self.args_list = [
            app,
            0,
            "",
            summary,
            body,
            ["s"],
            {
                "urgency": 1,
                "sender-pid": 12345,
            },
            -1
        ]
    def get_member(self):
        return self.member

    def get_interface(self):
        return self.interface

    def get_args_list(self):
        return self.args_list

class Message:
    def __init__(self, notification):
        # print("Notification")
        args = notification.get_args_list()
        # print("Args list:", args, flush = True)

        self.app = str(args[0])
        self.replaces_id = int(args[1])
        # self.icon = str(args[2])
        self.summary = str(args[3])
        self.body = str(args[4])
        self.actions = args[5]
        self.hints = dict(args[6])
        self.expire_timeout = int(args[7])

        self.date = datetime.datetime.now()
        self.hdate = humanize.naturaltime(self.date)
        self.urgency = {0: "low", 1: "normal", 2: "critical", None: "unknown"}

    def print_on(self, console = Console()):
        console.print(f"[color(33)][white on color(33)]{self.hdate}:[bold black on color(33)]{self.app}[color(33) on color(254)][not bold black on color(254)]{self.summary}[color(254) on color(239)][white on color(239)]{self.body}[reset][color(239)]", end="")


class Broker:
    def __init__(self):
        self.deck = collections.deque()
        self.console = Console()

        DBusGMainLoop(set_as_default=True)

        bus = dbus.SessionBus()
        bus.add_match_string_non_blocking("eavesdrop=true, interface='org.freedesktop.Notifications', member='Notify'")
        bus.add_message_filter(self.receive)

    def run(self):
        mainloop = gi.repository.GLib.MainLoop()
        mainloop.run()

    def receive(self, bus, notification):
        # print(notification, flush = True)
        # print("---------------------------------------------", flush = True)
        # print("Member:", notification.get_member(), flush = True)
        # print("Interface:", notification.get_interface(), flush = True)

        if notification.get_member() == "Notify" and notification.get_interface() == 'org.freedesktop.Notifications':
            msg = Message(notification)
            self.deck.append(msg)
            self.print()

    def print(self):
        self.console.print(end = "\r")
        for msg in self.deck:
            msg.print_on(self.console)


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "--test":
        broker = Broker()
        broker.receive(None, N())
        broker.receive(None, N("other-app", "this is a test", "no much of a body"))
    else:
        broker = Broker()
        broker.run()
