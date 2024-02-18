CLI bard — See all your last notifications in the terminal
==========================================================

The *CLI bard* is a very simple command line application that displays the last
notifications received on the D-Bus (the common notification system under Linux).

It is not an interactive application, it just displays incoming notifications.
At any time, as much as possible of the last notifications are displayed.
The display refreshes when a notification is received.

The CLI bard is written in Python and is available under the AGPLv3 license.


Install
=======

The CLI bard relies on your terminal using a font patched with the "Powerline"
characters. The recommended fonts are the ones from the
[Nerd font project](https://www.nerdfonts.com/).


Usage
=====

Command arguments
-----------------

>  usage: clibard.py [-h] [-l {h,v,horizontal,vertical}] [--test NB_ITEMS] [--send NB_ITEMS]
> options:
>   -h, --help            show this help message and exit
>   -l {h,v,horizontal,vertical}, --layout {h,v,horizontal,vertical}
>                         How to display notifications. `horizontal` = as many of the last notifications that fit on a single line, clear out the old ones. `vertical` = keep
>                         printing new notifications on new lines.


Signaling
---------

The CLI bard does respond to POSIX "user signals".
Signals can be issued with the `kill` command, using the `--signal` flag along
with 10 (SIGUSR1) or 12 (SIGUSR2) as an argument.
SIGUSR1 will refresh the display, SIGUSR2 will erase any notification in the
cache and clear the display (if it can).

Note that with the horizontal layout, refreshing the display actually changes
the display. Erasing the cache will remove any on-screen notification.
With the vertical layout, this does nothing on the display.


Layouts
=======

The default layout is the horizontal one.
This will display on a single line, and overwrite it as soon as an update is
received.
When refreshing its display in the horizontal layout, the displayed dates will
be refreshed as well.
However, it does not show all the cached notifications, but only the few last
ones that can fit the current width of the terminal.

The vertical layout simply prints a new line as soon as the CLI bard receive
a notification. The display cannot be cleared nor refreshed.
Most notably, the dates of notifications will all be "now".
However, the terminal does display all the received notifications, if you can
scroll back enough.

