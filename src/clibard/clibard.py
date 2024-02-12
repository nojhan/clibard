#!/usr/bin/env python3

import collections
# import rich
from rich.console import Console
from rich.style import Style
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


class Color:

    def ansi2rgb(ansi):
       if 232 <= ansi and ansi <= 255:
           # Greyscale domain.
           R = (ansi - 232) * 10 + 8
           G = R
           B = R
       elif 0 <= ansi and ansi <= 15:
           # Default 16 colors.
           ansi_16 = [(0,0,0),(128,0,0),(0,128,0),(128,128,0),(0,0,128),(128,0,128),(0,128,128),(192,192,192),(80,80,80),(255,0,0),(0,255,0),(255,255,0),(0,0,255),(255,0,255),(0,255,255),(255,255,255)]
           R,G,B = ansi_16[ansi]
       else:
           iR = (ansi - 16) / 36
           if iR > 0:
               R = 55 + iR*40
           else:
               R = 0

           iG = (ansi-16) % 36 / 6
           if iG > 0:
               G = 55 + iG*40
           else:
               G = 0

           iB = (ansi-16) % 6
           if iB > 0:
               B = 55 + iB*40
           else:
               B = 0

       return R,G,B

    def lum(dC):
        """Linearize an RGB component."""
        if dC <= 0.03928:
            return dC / 12.92
        else:
            return pow( (dC + 0.055)/1.055 , 2.4)

    def luminance(R, G, B):
        """RGB linear (reljative) luminance."""
        dR = R / 255
        dG = G / 255
        dB = B / 255

        lR = Color.lum(dR)
        lG = Color.lum(dG)
        lB = Color.lum(dB)

        return 0.2126 * lR + 0.7152 * lG + 0.0722 * lB

    def lightness(luminance):
        """Perceived lightness in [0,100] (i.e. [darkest, lightest])."""
        if luminance < 216/24389:
            return luminance * 24389 / 27
        else:
            return pow(luminance, 1/3) * 116 - 16

    def ansi_lightness(ansi):
        R,G,B = Color.ansi2rgb(ansi)
        return Color.lightness(Color.luminance(R,G,B))


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
        self.urgencies = {0: "low", 1: "normal", 2: "critical", None: "unknown"}
        self.urgency = self.urgencies[self.hints["urgency"]]

        self.last_color = "black"

        self.color = {
            # Urgencies
            "low": "105",
            "normal": "33",
            "critical": "220",
            "unknown": "69",
            "date": "21",
            "summary": "254",
            "body": "242",
            "none": "0"
        }

        self.style = {}
        for k in self.color:
            self.style[k] = f"color({self.color[k]})"

    def print_segment(self, key, text, console):
        console.print("",  style=f"{self.last_color} on {self.style[key]}", end="")

        # Automated black or white foreground.
        if Color.ansi_lightness(int(self.color[key])) >= 50:
            fg = "black"
        else:
            fg = "white"
        console.print(text, style=f"{fg} on {self.style[key]}", end="")

        self.last_color = f"{self.style[key]}"

    def print_on(self, console = Console()):
        hdate = humanize.naturaltime(self.date)
        self.print_segment("date", hdate, console)
        self.print_segment(self.urgency, self.app, console)
        self.print_segment("summary", self.summary, console)
        self.print_segment("body", self.body, console)
        # console.print(f"[color(21)][white on color(21)]{hdate}[color(21) on color(33)][bold color(232) on color(33)]{self.app}[color(33) on color(254)][not bold color(232) on color(254)]{self.summary}[color(254) on color(239)][white on color(239)]{self.body}[reset][color(239)]", end="")
        self.print_segment("none", "", console)


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
        self.console.print(">", end = "\r") # It is necssary to print something before the chariot return.
        for msg in self.deck:
            self.console.print(" ", end="")
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
