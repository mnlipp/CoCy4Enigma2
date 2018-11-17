"""
..
   This file is part of the CoCy program.
   Copyright (C) 2018 Michael N. Lipp
   
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

"""

# Taken from https://pastebin.com/dqHGnJ8B
from threading import currentThread
from twisted.internet import reactor, defer
from twisted.python import failure
import Queue

def blockingCallOnMainThread(func, *args, **kwargs):
    """
      Modified version of twisted.internet.threads.blockingCallFromThread
      which waits 30s for results and otherwise assumes the system to be shut down.
      This is an ugly workaround for a twisted-internal deadlock.
      Please keep the look intact in case someone comes up with a way
      to reliably detect from the outside if twisted is currently shutting
      down.
    """
    def blockingCallFromThread(f, *a, **kw):
        queue = Queue.Queue()
        def _callFromThread():
            result = defer.maybeDeferred(f, *a, **kw)
            result.addBoth(queue.put)
        reactor.callFromThread(_callFromThread)

        result = None
        while True:
            try:
                result = queue.get(True, 30)
            except Queue.Empty as qe:
                if True: #not reactor.running: # reactor.running is only False AFTER shutdown, we are during.
                    raise ValueError("Reactor no longer active, aborting.")
            else:
                break

        if isinstance(result, failure.Failure):
            result.raiseException()
        return result

    if currentThread().getName() == 'MainThread':
        return func(*args, **kwargs)
    else:
        return blockingCallFromThread(func, *args, **kwargs)

def callOnMainThread(func, *args, **kwargs):
    """
      Ensures that a method is being called on the main-thread.
      No return value here!
    """
    if currentThread().getName() == 'MainThread':
        #call on next mainloop interation
        reactor.callLater(0, func, *args, **kwargs)
    else:
        #call on mainthread
        reactor.callFromThread(func, *args, **kwargs)

