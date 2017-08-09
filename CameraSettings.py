#!/usr/bin/python
# -*- coding: utf-8 -*-

"""
    author: Jacob Kosberg
"""

from SaveState import guisave, guirestore
from PyQt4 import QtGui, QtCore, uic
from camera import AmscopeCamera, WebCamera

import time

class AbstractCameraSettings(QtGui.QWidget):
    def __init__(self, camera, device):
        raise NotImplementedError

    def setDeviceName(self):
        deviceName = str(self.deviceName.text())
        self.deviceNameStr = deviceName if deviceName else self.deviceId

    def wireUiElements(self):
        self.connectObjs((self.brightnessSlider, self.brightnessSpinBox), self.setBrightness)
        self.connectObjs((self.contrastSlider, self.contrastSpinBox), self.setContrast)
        self.connectObjs((self.exposureSlider, self.exposureSpinBox), self.setExposure)
        self.connectObjs((self.rotationSlider, self.rotationSpinBox), self.setRotation)
        self.deviceName.textChanged.connect(self.setDeviceName)
        self.wireSpecialUi()

    def wireSpecialUi(self):
        raise NotImplementedError

    def connectObjs(self, objTuple, setFunction):
        """
        Mutually connect two objects in a tuple so their values stay equal.
        Used to wire up sliders to spin boxes for camera settings.
        """
        first, second = objTuple
        first.valueChanged.connect(
            lambda: self.changeValue(first, second, setFunction))
        second.valueChanged.connect(
            lambda: self.changeValue(second, first, setFunction))

    def changeValue(self, fromObj, toObj, setFunction):
        toObj.setValue(fromObj.value())
        setFunction()

    def setBrightness(self):
        self.camera.set_brightness(self.brightnessSpinBox.value())

    def setContrast(self):
        self.camera.set_contrast(self.contrastSpinBox.value())

    def setExposure(self):
        self.camera.set_exposure(self.exposureSpinBox.value())

    def setRotation(self):
        self.camera.set_rotation(self.rotationSpinBox.value())

    def applySettings(self):
        for func in self.settingsFuncs:
            func()

    def reset(self, waitTime):
        guirestore(self)
        self.applySettings()
        self.wait(waitTime)

    def closeEvent(self, event):
        guisave(self)
        event.accept()

class WebCameraSettings(AbstractCameraSettings):
    def __init__(self, camera, device):
        QtGui.QWidget.__init__(self)
        ui_path = "ui/parameters"
        self.ui = uic.loadUi(ui_path + '.ui', self)
        self.setWindowTitle("Camera Settings")
        self.camera = camera
        self.deviceId = device
        self.settingsFuncs = [self.setBrightness, self.setContrast,
                            self.setExposure, self.setRotation]
        self.setFixedSize(self.size())

        self.settings = QtCore.QSettings(
            ui_path + '_' +str(self.deviceId) + '.ini',
            QtCore.QSettings.IniFormat)
        
        guirestore(self)
        self.setDeviceName()
        self.wireUiElements()

    def wait(self, waitTime):
        #time.sleep(waitTime)
        pass

    def wireSpecialUi(self):
        self.settingsFuncs.extend([self.setGain])
        self.connectObjs((self.gainSlider, self.gainSpinBox), self.setGain)

    def setGain(self):
        self.camera.set_gain(self.gainSpinBox.value())

class AmscopeCameraSettings(AbstractCameraSettings):
    def __init__(self, camera, device):
        QtGui.QWidget.__init__(self)
        ui_path = "ui/amscope_parameters"
        self.ui = uic.loadUi(ui_path + '.ui', self)
        self.setWindowTitle("Camera Settings")
        self.camera = camera
        self.deviceId = device
        self.settingsFuncs = [self.setBrightness, self.setContrast,
                            self.setExposure, self.setRotation]
        self.setFixedSize(self.size())

        self.settings = QtCore.QSettings(
            ui_path + '_' +str(self.deviceId) + '.ini',
            QtCore.QSettings.IniFormat)

        guirestore(self)
        self.setDeviceName()
        self.wireUiElements()

    def wait(self, waitTime):
        time.sleep(waitTime)

    def wireSpecialUi(self):
        self.settingsFuncs.extend([self.setTempTint, self.setHue,
                                self.setGamma, self.setSaturation])
        self.connectObjs((self.gammaSlider, self.gammaSpinBox), self.setGamma)
        self.connectObjs((self.saturationSlider, self.saturationSpinBox), self.setSaturation)
        self.connectObjs((self.tempSlider, self.tempSpinBox), self.setTempTint)
        self.connectObjs((self.tintSlider, self.tintSpinBox), self.setTempTint)
        self.connectObjs((self.hueSlider, self.hueSpinBox), self.setHue)

    def setTempTint(self):
        self.camera.set_temp_tint(self.tempSpinBox.value(), self.tintSpinBox.value())

    def setHue(self):
        self.camera.set_hue(self.hueSpinBox.value())

    def setGamma(self):
        self.camera.set_gamma(self.gammaSpinBox.value())

    def setSaturation(self):
        self.camera.set_saturation(self.saturationSpinBox.value())