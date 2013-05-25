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
from enigma import eDVBVolumecontrol, iPlayableService, \
    eServiceReference
from circuits.core.handlers import handler
from cocy.providers import Manifest, MediaPlayer
from Components.ServiceEventTracker import ServiceEventTracker
from circuits_bricks.core.timers import Timer
from circuits.core.events import Event
from circuits_bricks.app.logger import Log
import logging


class DreamBoxPlayer(MediaPlayer):

    manifest = Manifest("DreamBox Media Renderer", "DreamBox Media Renderer")

    def __init__(self, session):
        super(DreamBoxPlayer, self).__init__(self.manifest)
        self._session = session
        self._old_service_set = False
        self._old_service = None
        self._service = None
        self._pausing = False
        self._idle_Timer = None
        self._eom = False
        self._on_async_done = None

        self._volctrl = eDVBVolumecontrol.getInstance()
        vol = self._volctrl.getVolume()
        self.volume = vol / 100
        
        self.onClose = [self._onClose] # Mimic as "screen"
        self.__event_tracker = ServiceEventTracker(screen=self, eventmap={
            iPlayableService.evEOF: self._onEOF,
            iPlayableService.evUpdatedEventInfo: self._onUpdatedEventInfo,
            iPlayableService.evTuneFailed: self._tune_failed
        })

    def _tune_failed(self):
        self.fire(Log(logging.DEBUG, "Tune failed"), "logger")

    @property
    def session(self):
        return getattr(self, "_session", None)

    @handler("close_player")
    def _onClose(self, *args, **kwargs):
        print "[CoCy] Closing"
        if self._old_service_set:
            self._session.nav.playService(self._old_service)
        self._old_service_set = False    
                          
    def _onEOF(self):
        self.fire(Log(logging.DEBUG, "End Of Media from player"), "logger")
        self._session.nav.stopService()
        self._eom = True
        self.fire(MediaPlayer.EndOfMedia())

    def _onUpdatedEventInfo(self):
        self.fire(Log(logging.DEBUG, 
                      "Updated Event Info from player"), "logger")
        if self._on_async_done is not None:
            if self._on_async_done():
                self._on_async_done = None
                                                   
    def _pausable(self):
        service = self._session.nav.getCurrentService()
        if service:
            return service.pause()
        return None
    
    def _seekable(self):
        s = self._session.nav.getCurrentService()
        if s:
            seek = s.seek()
            if seek is None or not seek.isCurrentlySeekable():
                return None
            else:
                return seek

        return None

    @handler("provider_updated")
    def _on_provider_updated_handler(self, provider, changed):
        if "state" in changed and changed["state"] == "IDLE":
            self._session.nav.stopService()
            self._pausing = False
            self._eom = False
            self._idle_Timer = Timer(5, Event.create("ClosePlayer")) \
                .register(self)
            self.fire(Log(logging.DEBUG, "Player stopped"), "logger")
        if "state" in changed and changed["state"] == "PAUSED":
            pausable = self._pausable()
            if pausable:
                pausable.pause()
            self._pausing = True
            self.fire(Log(logging.DEBUG, "Player paused"), "logger")
        if "source" in changed:
            self._service = eServiceReference(4097, 0, changed["source"])
            self.fire(Log(logging.DEBUG, "Player service set to %s"
                          % changed["source"]), "logger")
            if self._eom:
                self._on_play()

    @handler("play", override=True)
    def _on_play(self):
        if self.source is None:
            return
        if not self._old_service_set:
            # First invocation, save currently running service
            self._old_service = self._session.nav \
                .getCurrentlyPlayingServiceReference()
            self._old_service_set = True
            self._session.nav.stopService()
        if self._idle_Timer is not None:
            self._idle_Timer.unregister()
        if self._pausing:
            pausable = self._pausable()
            if pausable:
                pausable.unpause()
            self._pausing = False
            print "[CoCy] Playing..."
            self.state = "PLAYING"
        else:
            def _play_started():
                if not self._seekable():
                    return False
                self.state = "PLAYING"
                self.fire(Log(logging.DEBUG, "Player playing"), "logger")
                if self.current_track_duration is None:
                    self.current_track_duration = self._duration()
            self._on_async_done = _play_started
            self.fire(Log(logging.DEBUG, "Starting player (transitioning)"),
                      "logger")
            self._eom = False
            self._session.nav.playService(self._service)
            self.state = "TRANSITIONING"
        
    def _duration(self):
        print "[CoCy] Getting duration..."
        seek = self._seekable()
        if seek is None:
            return None
        length = seek.getLength()
        if length[0]:
            return 0
        print "[CoCy] Duration raw " + str(length[1])
        print "[CoCy] Duration is " + str(float(length[1]) / 90000)
        return float(length[1]) / 90000

    def current_position(self):
        seek = self._seekable()
        if seek is None:
            return None
        if self.current_track_duration is None:
            self.current_track_duration = self._duration()
        pos = seek.getPlayPosition()
        if pos[0]:
            return 0
        return float(pos[1]) / 90000

    @handler("seek", override=True)
    def _on_seek(self, position):
        if self.state != "PLAYING":
            return
        seekable = self._seekable()
        if seekable is None:
            return
        cur_state = self.state
        def seek_end():
            self.state = cur_state
            print "[CoCy] Resumed " + self.state
            return True
        self._on_async_done = seek_end
        self.state = "TRANSITIONING"
        print "[CoCy] Transitioning..."
        seekable.seekTo(long(int(position) * 90000))

    @handler("set_volume", override=True)
    def _on_set_volume(self, volume):
        print "[CoCy] Volume: " + str(volume)
        self._volctrl.setVolume(int(volume*100), int(volume*100))
        self.volume = volume
    