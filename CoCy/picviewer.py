"""
.. codeauthor: mnl
"""
# Based on
# Ihad.tv enigma2-plugin tutorial 2010
# lesson 7
# by emanuel
from Screens.Screen import Screen
from Components.Pixmap import Pixmap
from Components.AVSwitch import AVSwitch
from enigma import ePicLoad, getDesktop
from Components.ActionMap import ActionMap
import mimetypes
from twisted.web.client import downloadPage

class PictureScreen(Screen):

    def __init__(self, session):
        print "[PictureScreen] __init__\n"
        self.closed = False
        self.size_w = size_w = getDesktop(0).size().width()
        self.size_h = size_h = getDesktop(0).size().height()
        space = 0
        self.bgcolor = "#00000000" # "#002C2C39"
        self.skin = "<screen position=\"0,0\" \
            size=\"" + str(size_w) + "," + str(size_h) \
            + "\" flags=\"wfNoBorder\" > \
            <eLabel position=\"0,0\" zPosition=\"0\" \
            size=\""+ str(size_w) + "," + str(size_h) \
            + "\" backgroundColor=\""+ self.bgcolor \
            +"\" /><widget name=\"pic\" position=\"" \
            + str(space) + "," + str(space) + "\" size=\"" \
            + str(size_w-(space*2)) + "," + str(size_h-(space*2)) \
            + "\" zPosition=\"1\" alphatest=\"on\" /> \
            </screen>"
        
        Screen.__init__(self, session)
        self["myActionMap"] = ActionMap(["SetupActions"],
            {
                 "cancel": self.close # add the RC Command "cancel"
            }, -1)
        self.Scale = AVSwitch().getFramebufferScale()
        self.PicLoad = ePicLoad()
        self["pic"] = Pixmap()
        self.PicLoad.PictureData.get().append(self.DecodePicture)
        # self.onLayoutFinish.append(self.ShowPicture)
        
    def loadPicture(self, picUrl, mimetype, on_showing = None):
        self._on_showing = on_showing
        extension = mimetypes.guess_extension(mimetype, strict=False)
        self._imageFile = "%s%s" % ("/tmp/picviewer", extension)
        print "Start downloading", picUrl, "to", self._imageFile
        d = downloadPage(picUrl, self._imageFile)
        d.addCallbacks(self._onPictureReady, self._onPictureLoadFailed)

    def _onPictureReady(self, nothing):
        self.showPicture(self._imageFile)

    def _onPictureLoadFailed(self):
        print "Loading picture failed!"

    def showPicture(self, picPath):
        self.PicLoad.setPara([
                              self["pic"].instance.size().width(),
                              self["pic"].instance.size().height(),
                              self.Scale[0],
                              self.Scale[1],
                              0,
                              1,
                              "#002C2C39"])
        self.PicLoad.startDecode(picPath)

    def DecodePicture(self, PicInfo = ""):
        ptr = self.PicLoad.getData()
        self["pic"].instance.setPixmap(ptr)
        if self._on_showing is not None:
            self._on_showing()
