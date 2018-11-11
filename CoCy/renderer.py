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
from circuits_bricks.app.logger import log
import logging
from socket import gethostname
from xml import etree
from xml.etree.ElementTree import QName
from picviewer import PictureScreen


class Enigma2Player(MediaPlayer):

    manifest = Manifest("Media Renderer on " + gethostname(),
                        "Media Renderer on " + gethostname())

    def __init__(self, session):
        super(Enigma2Player, self).__init__(self.manifest)
        self._session = session
        self._old_service_set = False
        self._old_service = None
        self._service = None
        self._pausing = False
        self._idle_Timer = None
        self._eom = False
        self._on_async_done = None

        self._picDlg = self._session.instantiateDialog(PictureScreen)
        
        self._volctrl = eDVBVolumecontrol.getInstance()
        vol = self._volctrl.getVolume()
        self.volume = vol / 100
        
        self.onClose = [self._onClose] # Mimic as "screen"
        self.__event_tracker = ServiceEventTracker(screen=self, eventmap={
            iPlayableService.evEOF: self._onEOF,
            iPlayableService.evUpdatedEventInfo: self._onUpdatedEventInfo,
            iPlayableService.evUpdatedInfo: self._onUpdatedInfo,
            iPlayableService.evBuffering: self._onBuffering,
            iPlayableService.evTuneFailed: self._tune_failed
        })

    def supportedMediaTypes(self):
        return ["http-get:*:audio/mpeg:*", "http-get:*:audio/ogg:*",
                "http-get:*:video/MP2T:*", "http-get:*:audio/mp4:*",
                "http-get:*:application/mp4:*", "http-get:*:video/mp4:*",
                "http-get:*:audio/3gpp:*", "http-get:*:video/3gpp:*",
                "http-get:*:audio/3gpp2:*", "http-get:*:video/3gpp2:*",
                "http-get:*:application/vnd.ms-asf:*", 
                "http-get:*:image/jpeg:*", "http-get:*:image/gif:*",
                "http-get:*:image/png:*",
                # those are not officially asigned!
                "http-get:*:video/mpeg:*", "http-get:*:video/avi:*",
                "http-get:*:image/bmp:*"]

    def _tune_failed(self):
        self.fire(log(logging.DEBUG, "Tune failed"), "logger")

    @property
    def session(self):
        return getattr(self, "_session", None)

    @handler("close_player")
    def _onClose(self, *args, **kwargs):
        print "[CoCy] Closing"
        if self._picDlg.execing:
            self._picDlg.close()
        if self._old_service_set:
            self._session.nav.playService(self._old_service)
        self._old_service_set = False    
                          
    def _onEOF(self):
        self.fire(log(logging.DEBUG, "End Of Media from player"), "logger")
        self._session.nav.stopService()
        self._eom = True
        self.fire(MediaPlayer.end_of_media())

    def _onUpdatedEventInfo(self):
        if self._on_async_done is not None:
            self.fire(log(logging.DEBUG, 
                      "Updated Event Info from player"), "logger")
            if self._on_async_done():
                self._on_async_done = None
                                                   
    def _onUpdatedInfo(self):
        if self._on_async_done is not None:
            self.fire(log(logging.DEBUG, 
                      "Updated Info from player"), "logger")
            if self._on_async_done():
                self._on_async_done = None
                                                   
    def _onBuffering(self):
        if self._on_async_done is not None:
            self.fire(log(logging.DEBUG, 
                      "Buffering from player"), "logger")
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
            self._idle_Timer = Timer(5, Event.create("close_player")) \
                .register(self)
            self.fire(log(logging.DEBUG, "Player stopped"), "logger")
        if "state" in changed and changed["state"] == "PAUSED":
            pausable = self._pausable()
            if pausable:
                pausable.pause()
            self._pausing = True
            self.fire(log(logging.DEBUG, "Player paused"), "logger")
        if "source" in changed:
            try:
                self._service = eServiceReference(4097, 0, changed["source"])
                self.fire(log(logging.DEBUG, "Player service set to %s"
                          % changed["source"]), "logger")
                if self._eom:
                    self._on_play()
            except Exception as e:
                self.fire(log(logging.ERROR, \
                    "Failed to set player service to %s: %s"
                    % (changed["source"], type(e))), "logger")

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
            desc = etree.ElementTree.fromstring(self.source_meta_data)
            from cocy.upnp import DIDL_LITE_NS
            protocolInfo = desc.find(str(QName(DIDL_LITE_NS, "item")) + "/"
                                     + str(QName(DIDL_LITE_NS, "res"))) \
                                     .get("protocolInfo")
            mimetype = protocolInfo.split(":")[2]
            if mimetype.startswith("image"):
                self.fire(log(logging.DEBUG, "Playing picture"), "logger")
                self.state = "TRANSITIONING"
                if not self._picDlg.execing:
                    self._session.execDialog(self._picDlg)
                def _pic_showing():
                    self.state = "PLAYING"
                self._picDlg.loadPicture(self._source, mimetype, _pic_showing)
                return
            if self._picDlg.execing:
                self._picDlg.close()
            
            def _play_started():
                if not self._seekable():
                    return False
                self.state = "PLAYING"
                self.fire(log(logging.DEBUG, "Player playing"), "logger")
                if self.current_track_duration is None:
                    self.current_track_duration = self._duration()
                return True
            self._on_async_done = _play_started
            self.state = "TRANSITIONING"
            self.fire(log(logging.DEBUG, "Starting player (transitioning)"),
                      "logger")
            self._eom = False
            try:
                self._session.nav.playService(self._service)
            except Exception as e:
                self.fire(log(logging.ERROR, "Failed to start playing: %s"
                    % type(e)), "logger")

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
    