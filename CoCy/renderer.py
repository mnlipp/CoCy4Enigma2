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
from enigma import eDVBVolumecontrol, iPlayableService, eServiceReference
from circuits.core.handlers import handler
from cocy.providers import Manifest, MediaPlayer, combine_events
from Components.ServiceEventTracker import ServiceEventTracker
from circuits_bricks.core.timers import Timer
from circuits.core.events import Event
from circuits_bricks.app.logger import log
import logging
from socket import gethostname
from xml.etree.ElementTree import QName
from picviewer import PictureScreen
from .ebrigde import blockingCallOnMainThread, callOnMainThread

class player_playing(Event):
    pass

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
        self._seek_offset = 0
        self.onClose = [self._onClose] # Mimic as "screen"
            
        def _init():
            self._picDlg = self._session.instantiateDialog(PictureScreen)
            self._volctrl = eDVBVolumecontrol.getInstance()
            vol = self._volctrl.getVolume()
            self.volume = vol / 100
        
            self.__event_tracker = ServiceEventTracker(screen=self, eventmap={
                iPlayableService.evStart: self._onStart,
                iPlayableService.evEOF: self._onEOF,
                iPlayableService.evUpdatedEventInfo: self._onUpdatedEventInfo,
                iPlayableService.evUpdatedInfo: self._onUpdatedInfo,
                iPlayableService.evBuffering: self._onBuffering,
                iPlayableService.evTuneFailed: self._tune_failed
            })
        callOnMainThread(_init)

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

    @property
    def session(self):
        return getattr(self, "_session", None)

    def _onStart(self):
        # Service event, called by main thread
        self.fire(log(logging.DEBUG, "Enigma player started"), "logger")
        self.fire(player_playing())

    @handler("player_playing")
    @combine_events
    def _on_player_playing(self):
        self.fire(log(logging.DEBUG, "Player playing"), "logger")
        self.state = "PLAYING"
        self.current_track_duration = self._duration()

    def _onEOF(self):
        # Service event, called by main thread
        self.fire(log(logging.DEBUG, "End Of Media from player"), "logger")
        self._session.nav.stopService()
        self._eom = True
        self.fire(MediaPlayer.end_of_media())

    def _onUpdatedEventInfo(self):
        # Service event, called by main thread
        self.fire(log(logging.DEBUG, 
                      "Updated Event Info from player"), "logger")
                                                  
    def _onUpdatedInfo(self):
        # Service event, called by main thread
        self.fire(log(logging.DEBUG, 
                      "Updated Info from player"), "logger")
                                                   
    def _onBuffering(self):
        # Service event, called by main thread
        self.fire(log(logging.DEBUG, 
                      "Buffering from player"), "logger")
                                                   
    def _tune_failed(self):
        # Service event, called by main thread
        self.fire(log(logging.DEBUG, "Tune failed"), "logger")

    @handler("close_player")
    def _onClose(self, *args, **kwargs):
        def _close():
            print "[CoCy] Closing"
            if self._picDlg.execing:
                self._picDlg.close()
            if self._old_service_set:
                self._session.nav.playService(self._old_service)
            self._old_service_set = False
        blockingCallOnMainThread(_close)
                          
    @handler("provider_updated")
    def _on_provider_updated_handler(self, provider, changed):
        if "state" in changed and changed["state"] == "IDLE":
            def _stop():
                self._session.nav.stopService()
                self._pausing = False
                self._eom = False
                self.fire(log(logging.DEBUG, "Player stopped"), "logger")
            blockingCallOnMainThread(_stop)
            self._idle_Timer = Timer(5, Event.create("close_player")) \
                .register(self)
        if "state" in changed and changed["state"] == "PAUSED":
            def _pause():
                pausable = self._pausable()
                if pausable:
                    pausable.pause()
                    self._pausing = True
                    self.fire(log(logging.DEBUG, "Player paused"), "logger")
            blockingCallOnMainThread(_pause)
        if "source" in changed:
            def _source():
                try:
                    self._service = eServiceReference(4097, 0, changed["source"])
                    self._seek_offset = 0
                    self.fire(log(logging.DEBUG, "Player service set to %s"
                                  % changed["source"]), "logger")
                    if self._eom:
                        self._on_play()
                except Exception as e:
                    self.fire(log(logging.ERROR, \
                                  "Failed to set player service to %s: %s"
                                  % (changed["source"], type(e))), "logger")
            blockingCallOnMainThread(_source)

    def _pausable(self):
        # Always called by main thread
        service = self._session.nav.getCurrentService()
        if service:
            return service.pause()
        return None
    
    @handler("play", override=True)
    def _on_play(self):
        if self.source is None:
            return
        if self._idle_Timer is not None:
            self._idle_Timer.unregister()
        def _play():
            if not self._old_service_set:
                # First invocation, save currently running service
                self._old_service = self._session.nav \
                    .getCurrentlyPlayingServiceReference()
                self._old_service_set = True
                self._session.nav.stopService()
            if self._pausing:
                pausable = self._pausable()
                if pausable:
                    pausable.unpause()
                self._pausing = False
                print "[CoCy] Resumed Playing..."
                self.fire(log(logging.DEBUG, "Enigma player unpaused"), "logger")
                self.fire(player_playing())
                return
            # New source
            from cocy.upnp import DIDL_LITE_NS
            protocolInfo = self.source_meta_dom.find(
                str(QName(DIDL_LITE_NS, "item")) + "/" + str(QName(DIDL_LITE_NS, "res"))) \
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
            # Play tune
            if self._picDlg.execing:
                self._picDlg.close()
            self.fire(log(logging.DEBUG, "Starting player (transitioning)"),
                      "logger")
            self._eom = False
            try:
                self._session.nav.playService(self._service)
            except Exception as e:
                self.fire(log(logging.ERROR, "Failed to start playing: %s"
                    % type(e)), "logger")
        self.state = "TRANSITIONING"
        callOnMainThread(_play)

    def _seekable(self):
        # Always called by main thread
        s = self._session.nav.getCurrentService()
        if s:
            seek = s.seek()
            if seek is None or not seek.isCurrentlySeekable():
                return None
            else:
                return seek
        return None

    def _duration(self):
        def _get():
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
        return blockingCallOnMainThread(_get)

    def current_position(self):
        def _get():
            seek = self._seekable()
            if seek is None:
                return None
            if self.current_track_duration is None:
                self.current_track_duration = self._duration()
            pos = seek.getPlayPosition()
            if pos[0]:
                return 0
            return self._seek_offset + float(pos[1]) / 90000
        return blockingCallOnMainThread(_get)

    @handler("seek", override=True)
    def _on_seek(self, position):
        if self.state != "PLAYING":
            return
        def _seek():
            seekable = self._seekable()
            if seekable is None:
                return
            print "[CoCy] Seeking..."
            self._seek_offset = position
            seekable.seekTo(long(int(position) * 90000))
            print "[CoCy] Seeking finished."
        blockingCallOnMainThread(_seek)

    @handler("set_volume", override=True)
    def _on_set_volume(self, volume):
        def _set():
            print "[CoCy] Volume: " + str(volume)
            self._volctrl.setVolume(int(volume*100), int(volume*100))
            self.volume = volume
        blockingCallOnMainThread(_set)
    