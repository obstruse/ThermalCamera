#!/usr/bin/env python

import  adafruit_mlx90640 as adafruit

import time

import struct
import math
import time
from typing import List, Optional, Tuple, Union

class MLX90640(adafruit.MLX90640):

    def getFrame(self, framebuf: List[int]) -> None:
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

        # clear data ready
        self._I2CWriteWord(0x8000, 0x0010)

        self._I2CReadWords(0x800D, controlRegister)
        frameData[832] = controlRegister[0]
        frameData[833] = statusRegister[0] & 0x0001
        #print(f"read MS: {int((time.time() - timeStart)* 1000)} bps: {int((832*2*9)/(time.time() - timeStart))}")

        # For a MLX90640 in the open air the shift is -8 degC.
        tr = self._GetTa(frameData) - OPENAIR_TA_SHIFT
        # for each subpage in frameData
        for i in [0,1] :
            frameData[833] = i
            self._CalculateTo(frameData, emissivity, tr, framebuf)


RefreshRate = adafruit.RefreshRate
OPENAIR_TA_SHIFT = adafruit.OPENAIR_TA_SHIFT
