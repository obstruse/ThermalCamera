#!/usr/bin/env python

import adafruit_mlx90640 as adafruit
import time

class MLX90640(adafruit.MLX90604):
    def getFrame(self, framebuf: List[int]) -> None:
        emissivity = 0.95
        tr = 23.15
        mlx90640Frame = [0] * 834

        dataReady = 0
        cnt = 0
        statusRegister = [0]
        controlRegister = [0]

        # wait for dataReady
        while not (self._I2CReadWords(0x8000, statusRegister) & 0x0008) :
            time.sleep(0.001)
            
        # read frame
        timeStart = time.time()
        self._I2CReadWords(0x0400, frameData, end=832)

        # clear data ready
        self._I2CWriteWord(0x8000, 0x0010)

        self._I2CReadWords(0x800D, controlRegister)
        frameData[832] = controlRegister[0]
        # hmmmmm....is this an issue?
        frameData[833] = statusRegister[0] & 0x0001
        print(f"read MS: {int((time.time() - timeStart)* 1000)} bps: {int((832*2*9)/(time.time() - timeStart))}")

        # For a MLX90640 in the open air the shift is -8 degC.
        tr = self._GetTa(self.mlx90640Frame) - OPENAIR_TA_SHIFT
        self._CalculateTo(self.mlx90640Frame, emissivity, tr, framebuf)


