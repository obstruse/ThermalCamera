#!/usr/bin/env python

import  adafruit_mlx90640 as adafruit

import time

import struct
import math
import time
from typing import List, Optional, Tuple, Union

class MLX90640(adafruit.MLX90640):
    version="Fast Driver"
    Constants = False
    Freeze = False
    frameData = [0] * 834

    def setResolution(self, res) :
        controlRegister = [0]
        self._I2CReadWords(0x800D, controlRegister)
        print(f"current resolution: { (controlRegister[0]>>10) & 0x3 }")
        value = (res & 0x3) << 10
        value |= controlRegister[0] & 0xF3FF
        self._I2CWriteWord(0x800D, value)
        print(f"resolution set to: {res}")
        self.version = f"{self.version}(resolution: {res})"

    def setConstants(self, constants) :
        self.Constants = constants
        if constants:
            self.version = f"{self.version}(Constants)"
            print("Using Constants")
        else:
            self.version = self.version.replace("(Constants)","")
            print("Not useing Constants")

        return self.Constants

    def setFreeze(self, freeze) :
        self.Freeze = freeze
        if freeze :
            self.version = f"{self.version}(Frozen)"
            print("frozen")
        else:
            self.version = self.version.replace("(Frozen)","")
            print("unfrozen")

        return self.Freeze

    def setPageMode(self, mode) :
        controlRegister = [0]
        value = mode & 0x1
        self._I2CReadWords(0x800D, controlRegister)
        value |= controlRegister[0] & 0xFFFE
        self._I2CWriteWord(0x800D, value)
        self._I2CReadWords(0x800D, controlRegister)
        print(f"SubPage Mode: {controlRegister[0] & 0x1}")
        self.version = f"{self.version} with PageMode set to {mode}"

    def getFrame(self, framebuf: List[int]) -> int:
        emissivity = 0.95
        #tr = 23.15     # tr is set later, don't need to initialize it

        frameData = self.frameData
        Constants = self.Constants
        Freeze = self.Freeze

        statusRegister = [0]
        controlRegister = [0]


        # wait for dataReady
        self._I2CReadWords(0x8000, statusRegister)
        while not (statusRegister[0] & 0x0008) :
            time.sleep(0.001)
            self._I2CReadWords(0x8000, statusRegister)
            
        # read frame
        timeStart = time.time()
        if Freeze:
            self._I2CReadWords(0x0400, frameData, end=768)
        else:
            self._I2CReadWords(0x0400, frameData, end=832)

        #print(frameData[399], frameData[400])
        if Constants :
            frameData[401] = 65444
            frameData[400] = 65444
            frameData[399] = 65444
            frameData[398] = 65444

        # clear data ready
        self._I2CWriteWord(0x8000, 0x0010)

        self._I2CReadWords(0x800D, controlRegister)
        frameData[832] = controlRegister[0]
        frameData[833] = statusRegister[0] & 0x0001
        subPage = statusRegister[0] & 0x0001
        #print(f"read MS: {int((time.time() - timeStart)* 1000)} bps: {int((832*2*9)/(time.time() - timeStart))}")

        # For a MLX90640 in the open air the shift is -8 degC.
        tr = self._GetTa(frameData) - OPENAIR_TA_SHIFT
        # for each subpage in frameData
        for i in [0,1] :
            frameData[833] = i
            self._CalculateTo(frameData, emissivity, tr, framebuf)

        return subPage


class MLX90640m0(adafruit.MLX90640):
    version="Original Driver"

    pass




RefreshRate = adafruit.RefreshRate
OPENAIR_TA_SHIFT = adafruit.OPENAIR_TA_SHIFT
