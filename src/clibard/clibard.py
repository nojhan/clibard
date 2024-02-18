#!/usr/bin/env python3

import copy
import signal
import datetime
import collections

import humanize
from rich.console import Console

import dbus
import gi.repository.GLib
from dbus.mainloop.glib import DBusGMainLoop

class N:
    def __init__(self, app = "unknown app", summary = "no info", body = "", urgency = 0):
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
                "urgency": urgency,
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
        self.urgencies = {0: "low", 1: "normal", 2: "critical"}
        if "urgency" in self.hints:
            self.urgency = self.urgencies[self.hints["urgency"]]
        else:
            self.urgency = self.urgencies[0]

        self.last_color = "black"

        self.color = {
            # Urgencies
            "low": 112,
            "normal": 33,
            "critical": 214,
            "unknown": 105,

            "summary_low": 193,
            "summary_normal": 81,
            "summary_critical": 228,
            "summary_unknown": 189,

            "date": 237,
            "summary": 254,
            "body": 242,
        }

        self._style = {}
        for k in self.color:
            self._style[k] = f"color({self.color[k]})"

    def __eq__(self, other):
        # Do not take date into account if it's already a duplicate.
        return  self.app     == other.app     \
            and self.summary == other.summary \
            and self.body    == other.body    \
            and self.urgency == other.urgency


    def style(self, key):
        if "reset" in key or "none" in key:
            return "reset"
        else:
            return self._style[key]


    def print_segment(self, key, text, console, prefix = ""):
        # print("\n>",key,":",text,"(",prefix,")")

        if key == "none":
            console.print("",  style=f"reset", end="")
            console.print("",  style=f"{self.last_color}", end="")
            return

        # if "reset" in self.last_color or "reset" in self.style(key):
        #     st = "reset"
        # else:
        st = f"{self.last_color} on {self.style(key)}"
        # print(">>",st)

        console.print("",  style=st, end="")

        # Automated black or white foreground.
        if Color.ansi_lightness(self.color[key]) >= 50:
            fg = "black"
        else:
            fg = "white"

        # if "reset" in prefix or "reset" in fg or "reset" in self.style(key):
        #     st = "reset"
        # else:
        st = f"{prefix} {fg} on {self.style(key)}"
        # print("\n>>",st)

        console.print(text, style=st, end="")

        self.last_color = f"{self.style(key)}"


    def print_on(self, console = None):
        hdate = humanize.naturaltime(self.date)
        if console != None:
            console.print(" ", end="")
            self.print_segment("date", hdate, console)
            self.print_segment(self.urgency, self.app, console, prefix = "bold")
            self.print_segment(f"summary_{self.urgency}", self.summary, console, prefix = "bold")
            self.print_segment("body", self.body, console)
            self.print_segment("none", "", console)

        return len(hdate) + len(self.app) + len(self.summary) + len(self.body) + 6


class Broker:
    def __init__(self, max_msg = 100, bounds = ""):

        self.max_msg = max_msg
        self.bounds = bounds

        self.deck = collections.deque()

        signal.signal(signal.SIGUSR1, self.sigusr1)

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
            mlen = msg.print_on(None)
            if len(self.deck) == 0:
                self.deck.append( (msg, mlen) )
            else:
                last_msg,last_mlen = self.deck.pop()
                self.deck.append( (last_msg, last_mlen) )
                if msg != last_msg: # We don't want duplicate in the last place.
                    self.deck.append( (msg, mlen) )
                    if len(self.deck) > self.max_msg:
                        self.deck.popleft()
            self.print()


    def sigusr1(self, signum, stack):
        self.deck.clear()
        self.print()


    def width(self, deck):
        w = 0
        for msg,mlen in deck:
            w += msg.print_on(None)
        return w


    def print(self):
        # print(len(self.deck),"message in deck")
        console = Console(highlight=False) # Re-instantiate in case the terminal window changed.
        if len(self.bounds) == 2:
            console.print(f"\r{self.bounds[0]}", end="\r")
        else:
            console.print(f"\r", end="\r")

        # Filter out messages that would not fit the terminal width.
        displayed = copy.deepcopy(self.deck)
        while self.width(displayed) >= console.size.width:
            displayed.popleft()

        # print(len(self.displayed),"message displayed")
        # Print what fits.
        width = 0
        for msg,mlen in displayed:
            width += msg.print_on(console)

        # Print overlapping spaces until the end.
        console.print(" "*(console.size.width-width-len(self.bounds)), end="")

        if len(self.bounds) == 2:
            console.print(f"{self.bounds[1]}\r", end="\r")
        else:
            console.print(f"\r", end="\r")


def test_messages(nb = 7):
    from faker import Faker
    import random
    fake = Faker()
    notifs = []
    for i in range(nb):
        lorem_app = fake.name()
        lorem_summary = fake.sentence(nb_words = 3, variable_nb_words = True)
        lorem_body = fake.sentence(nb_words = 7, variable_nb_words = True)
        notifs.append( N(lorem_app, lorem_summary, lorem_body, urgency = random.randint(0,2)) )
    return notifs


if __name__ == "__main__":
    import sys

    if len(sys.argv) == 3 and sys.argv[1] == "--test":
        broker = Broker(max_msg = 100, bounds = "><")
        notifs = test_messages(int(sys.argv[2]))
        for notif in notifs:
            broker.receive(None, notif)
        print("\n", end="")

    elif len(sys.argv) == 3 and sys.argv[1] == "--send":
        import os
        import time
        notifs = test_messages(int(sys.argv[2]))
        for notif in notifs:
            m = Message(notif)
            os.system(f"""notify-send "{m.summary}" "{m.body}" -u {m.urgency}""")
            time.sleep(0.1)
    else:
        broker = Broker()
        broker.run()
