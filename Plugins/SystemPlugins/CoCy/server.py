"""
..
   This file is part of the CoCy program.
   Copyright (C) 2011 Michael N. Lipp
   
   This program is free software: you can redistribute it and/or modify
   it under the terms of the GNU General Public License as published by
   the Free Software Foundation, either version 3 of the License, or
   (at your option) any later version.
   
   This program is distributed in the hope that it will be useful,
   but WITHOUT ANY WARRANTY; without even the implied warranty of
   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
   GNU General Public License for more details.

   You should have received a copy of the GNU General Public License
   along with this program.  If not, see <http://www.gnu.org/licenses/>.

.. codeauthor:: mnl
"""
from circuits_bricks.app import Application
from cocy.upnp.device_server import UPnPDeviceServer
from renderer import DreamBoxPlayer

CONFIG = {
    "logging": {
        "type": "TimedRotatingFile",
        "file": "/var/log/cocy.log",
        "when": "midnight",
        "backupCount": 7,
        "level": "DEBUG",
    },
    "ui": {
        "port": "8123",
    },
}


def start(session):
    application = Application("CoCy", CONFIG, 
                              { "config_dir": "/etc/cocy",
                                "app_dir": "/var/lib/cocy" })
    # Debugger().register(application)
#    # Build a web (HTTP) server for handling user interface requests.
#    port = int(application.config.get("ui", "port", 0))
#    portal_server = BaseServer(("", port), channel="ui").register(application)
#    Portal(portal_server, title="Test Portal").register(application)
#    HelloWorldPortlet().register(application)
    
    # The server    
    UPnPDeviceServer(application.app_dir).register(application)
    player = DreamBoxPlayer(session)
    print "[CoCy] Player: " + str(player)
    player.register(application)
    
    from circuits.tools import graph
    print graph(application)
    application.start()
