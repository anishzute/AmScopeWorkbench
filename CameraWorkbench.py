#!/usr/bin/python
# -*- coding: utf-8 -*-

"""
    author: Jacob Kosberg
"""

from SaveState import guisave, guirestore
from PyQt5 import QtWidgets, QtCore, uic

import camera
import CameraSettings
import cv2
import time
import os
import argparse
import sys

# Used for profiling
#from pympler import tracker

# This is the time it takes to switch Amscope cameras. Used for interval
# calculation. For webcams, we set equal to 0 since we don't deactivate
# cameras. (Less risk of hitting USB bandwidth.)
CAMERA_ACTIVATION_TIME_SECONDS = 5

# HOME_FOLDER = "C:\Users\europaexpts\Documents\code\CameraWorkbench"
HOME_FOLDER = os. getcwd()

class MainWindow(QtWidgets.QMainWindow):
    """MainWindow initializes UI objects like buttons, text/check/spin boxes, etc."""
    def __init__(self, worker, change_signal):
        QtWidgets.QMainWindow.__init__(self)
        self.ui = uic.loadUi('ui/main.ui', self)
        self.setWindowTitle("Camera Workbench")
        self.setFixedSize(self.size())
        self.settings = QtCore.QSettings('ui/main.ini', QtCore.QSettings.IniFormat)
        guirestore(self)
        self.change_detected = change_signal
        self.worker = worker
        self.timelapse = TimeLapse(self.worker)
        #self.tr = tracker.SummaryTracker()
        #self.tr.print_diff()
        self.wireUiElements()
        self.populateDeviceList()
        self.setInitValues()


    def populateDeviceList(self):
        self.deviceList.clear()
        for camera in self.worker.cameras:
            item = QtWidgets.QListWidgetItem(str(camera.deviceNameStr))
            if camera.camera.disabled:
                item.setForeground(QtWidgets.QColor(255, 0, 0))
            self.deviceList.addItem(item)


            # Select and activate the first camera
            #if i == 0:
            #    self.deviceList.setCurrentItem(item)
            #    self.switchCamera(item)
            #i += 1

    def update_ui(self):
        self.populateDeviceList()

    def setInitValues(self):
        self.worker.scale = self.previewScaleSpinBox.value()
        self.worker.previewEnabled = False #self.previewEnabled.isChecked()
        self.worker.setImagesPath(str(self.capturePath.text()))
        self.timelapse.interval = self.intervalSpinBox.value()
        self.timelapse.intervalEnabled = self.intervalEnabled.isChecked()

    def wireUiElements(self):
        self.change_detected.connect(self.update_ui)
        # Change device to selected device
        self.deviceList.itemClicked.connect(self.switchCamera)

        # Camera Settings/Parameters Button
        self.settingsButton.clicked.connect(lambda: self.worker.camera.show())

        # Preview Window
        self.previewScaleSpinBox.valueChanged.connect(
            lambda: self.worker.setScale(self.previewScaleSpinBox.value()))
        self.previewEnabled.stateChanged.connect(
            lambda: self.worker.setPreviewEnabled(self.previewEnabled.isChecked()))

        # Capture path
        self.capturePath.textChanged.connect(
            lambda: self.worker.setImagesPath(str(self.capturePath.text())))

        # Capture Image, either ALL or Selected Device
        self.snapAllButton.clicked.connect(
            lambda: self.worker.actionQueue.append(self.worker.captureAll))
        self.snapSelectedButton.clicked.connect(
            lambda: self.worker.actionQueue.append(self.worker.captureImage))

        # Interval value and checkbox
        self.intervalSpinBox.valueChanged.connect(
            lambda: self.timelapse.setInterval(self.intervalSpinBox.value()))
        self.intervalEnabled.stateChanged.connect(lambda: self.toggleTimelapse())

        # Reconstruct interval photography
        self.reconstructEnabled.stateChanged.connect(
            lambda: self.worker.setReconstructEnabled(self.reconstructEnabled.isChecked()))

    def toggleTimelapse(self):
        self.timelapse.setIntervalEnabled(self.intervalEnabled.isChecked())
        if self.intervalEnabled.isChecked():
            self.timelapse.running = True
            self.timelapse.start()
        else:
            self.timelapse.running = False

    def switchCamera(self, item):
        i = int(self.deviceList.indexFromItem(item).row())
        self.worker.actionQueue.append(lambda: self.worker.switchCamera(i))
        #self.tr.print_diff()

    def closeEvent(self, event):
        self.worker.running = False
        for settings in self.worker.cameras:
            settings.closeEvent(event)
        guisave(self)
        event.accept()

class TimeLapse(QtCore.QThread):
    def __init__(self, worker):
        QtCore.QThread.__init__(self)
        self.worker = worker
        self.running = False

    def run(self):
        while self.running:
            self.capture()
            interval = self.interval - len(self.worker.cameras)*(CAMERA_ACTIVATION_TIME_SECONDS+1)
            start = time.time()
            while self.running and time.time() < start + self.interval:
                pass

    def capture(self):
        self.worker.actionQueue.append(self.worker.captureAll)

    def setIntervalEnabled(self, enabled):
        self.intervalEnabled = enabled

    def setInterval(self, interval):
        self.interval = interval

class Worker(QtCore.QThread):
    """
    QT thread for activating cameras, capturing and scaling images.
    self.cameras is actually a list of CameraSettings, which act as
    camera managers.
    """
    def __init__(self, cameras):
        QtCore.QThread.__init__(self)
        self.cameras = cameras
        self.camera = None
        self.running = True
        self.scale = 60
        self.previewEnabled = False
        self.reconstructEnabled = False
        self.actionQueue = []

    def run(self):
        while self.running:
            self.idle()
        self.kill()

    def idle(self):
        while self.actionQueue:
            self.actionQueue.pop(0)()
        self.show_frame()

    def createPathIfNotExists(self, path):
        if not os.path.exists(path):
            os.makedirs(path)

    def assertPathNotNull(self, path):
        if path in [None, ""]:
            raise ValueError("Path cannot be empty!")

    def show_frame(self):
        title = "Preview"
        try:
            if self.previewEnabled and self.camera.camera.capture:
                self.camera.camera.show_frame(title, scale=self.scale)
            else:
                cv2.destroyWindow(title)
        except AttributeError as e:
            print(e)
            print("A camera was detached!")
            self.kill()

    def captureAll(self):
        images = []
        for i in range(len(self.cameras)):
            self.switchCamera(i)
            images.append(self.captureImage())

        if self.reconstructEnabled:
            import reconstructor
            outputDir = os.path.join(self.imagesPath, "reconstruction", self.getDateString())
            self.createPathIfNotExists(outputDir)
            reconstructor.convertPngsToJpgs(images, outputDir)
            reconstructor.runCMPMVS(outputDir)
        self.camera.camera.deactivate()

    def captureImage(self):
        cameraSettings = self.camera
        print("1")
        #cameraSettings.reset(CAMERA_ACTIVATION_TIME_SECONDS)
        print("2")
        frame = cameraSettings.camera.get_frame()
        print("3")
        filename = self.getImageFilepath(self.imagesPath, cameraSettings.deviceNameStr)
        print("4")
        cv2.imwrite(filename, frame)
        print("5")
        return filename

    def getImageFilepath(self, path, deviceName):
        """
        Creates file path under 'deviceName' folder in parent images path.
        Uses date and time as filename. Ex: '2017-08-08_10-29-57.png'
        """
        self.assertPathNotNull(path)
        newPath = os.path.join(path, str(deviceName))
        self.createPathIfNotExists(newPath)
        return os.path.join(newPath, self.getDateString() + ".png")

    def getDateString(self):
        return time.strftime("%Y-%m-%d_%H-%M-%S")

    def setPreviewEnabled(self, enabled):
        self.previewEnabled = enabled

    def setReconstructEnabled(self, enabled):
        self.reconstructEnabled = enabled

    def setImagesPath(self, path):
        self.imagesPath = path

    def setScale(self, scale):
        self.scale = scale

    def switchCamera(self, index):
        if self.camera:
            self.camera.camera.deactivate()
        self.camera = self.cameras[index]
        self.camera.camera.activate()
        self.camera.reset(CAMERA_ACTIVATION_TIME_SECONDS)
        self.camera.setDeviceSerial()
        self.camera.setDeviceId()

    def kill(self):
        self.running = False
        for cam in self.cameras:
            cam.camera.close()

class Application(QtWidgets.QApplication):
    change_detected = QtCore.pyqtSignal()
    def __init__(self, args):
        super(Application, self).__init__(["Camera Workbench"])
        
        if args.use_amscope:
            Camera = camera.AmscopeCamera
            CameraManager = CameraSettings.AmscopeCameraSettings
        else:
            Camera = camera.WebCamera
            CameraManager = CameraSettings.WebCameraSettings

        cams = [CameraManager(Camera(device, fullRes=True), device, change_signal=self.change_detected) 
                    for device in args.devices]
        worker = Worker(cams)
        worker.start()
        mainWindow = MainWindow(worker, self.change_detected)
        mainWindow.show()

def main():
    parser = argparse.ArgumentParser(description="UI utility for time lapse and HDR imagery.")
    parser.add_argument("devices", type=int, nargs="+", help="Device index. (0, 1, 2, ...)")
    parser.add_argument('--amscope', dest='use_amscope', action='store_true')
    parser.add_argument('--webcam', dest='use_amscope', action='store_false')
    args = parser.parse_args()

    os.chdir(HOME_FOLDER)
    app = Application(args)

    app.exec_()
    time.sleep(2)
    app.quit()

if __name__ == '__main__':
    main()