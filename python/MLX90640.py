#!/usr/bin/env python

import  adafruit_mlx90640 as adafruit

import time

import struct
import math
import time
from typing import List, Optional, Tuple, Union

class MLX90640(adafruit.MLX90640):
    version="Fast Driver[with constants]"

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
        tr = 23.15

        statusRegister = [0]
        controlRegister = [0]

        frameData = [0] * 834

        # wait for dataReady
        self._I2CReadWords(0x8000, statusRegister)
        while not (statusRegister[0] & 0x0008) :
            time.sleep(0.001)
            self._I2CReadWords(0x8000, statusRegister)
            
        # read frame
        timeStart = time.time()
        self._I2CReadWords(0x0400, frameData, end=832)
        #print(frameData[399], frameData[400])
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


class MLX90640m1(adafruit.MLX90640):
    version="No loop after read"

    def _GetFrameData(self, frameData: List[int]) -> int:
        dataReady = 0
        cnt = 0
        statusRegister = [0]
        controlRegister = [0]

        while dataReady == 0:
            self._I2CReadWords(0x8000, statusRegister)
            dataReady = statusRegister[0] & 0x0008
            # print("ready status: 0x%x" % dataReady)

        self._I2CReadWords(0x0400, frameData, end=832)
        self._I2CReadWords(0x8000, statusRegister)
        frameData[833] = statusRegister[0] & 0x0001
        # clear dataready
        self._I2CWriteWord(0x8000, 0x0010)

        if cnt > 4:
            raise RuntimeError("Too many retries")

        self._I2CReadWords(0x800D, controlRegister)
        frameData[832] = controlRegister[0]
        #print(f"subpage: {frameData[833]}")
        return frameData[833]

class MLX90640m2(adafruit.MLX90640):
    version="Subpages reversed"


    def getFrame(self, framebuf: List[int]) -> None:
        """Request both 'halves' of a frame from the sensor, merge them
        and calculate the temperature in C for each of 32x24 pixels. Placed
        into the 768-element array passed in!"""
        emissivity = 0.95
        tr = 23.15
        mlx90640Frame = [0] * 834

        for _ in range(2):
            status = self._GetFrameData(mlx90640Frame)
            mlx90640Frame[833] = (mlx90640Frame[833] + 1) % 2
            if status < 0:
                raise RuntimeError("Frame data error")
            # For a MLX90640 in the open air the shift is -8 degC.
            tr = self._GetTa(mlx90640Frame) - OPENAIR_TA_SHIFT
            self._CalculateTo(mlx90640Frame, emissivity, tr, framebuf)




RefreshRate = adafruit.RefreshRate
OPENAIR_TA_SHIFT = adafruit.OPENAIR_TA_SHIFT
