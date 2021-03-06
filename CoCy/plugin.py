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
from Plugins.Plugin import PluginDescriptor
from Components.ServiceEventTracker import ServiceEventTracker
from Plugins.SystemPlugins.CoCy.server import start

def plugin_start(reason, **kwargs):
	print "[CoCy] reason = " + str(reason)
	session = kwargs.get('session', None)
	print "[CoCy] session = " + str(session)
	
	# Fix an enigma bug
	if not hasattr(ServiceEventTracker, "oldRef"):
		ServiceEventTracker.oldRef = None
		print "[CoCy] Added missing attribute oldRef to ServiceEventTracker"

	start(session)

def Plugins(**kwargs):
	return PluginDescriptor(name="CoCy", 
						where=PluginDescriptor.WHERE_SESSIONSTART, 
						fnc=plugin_start) 
