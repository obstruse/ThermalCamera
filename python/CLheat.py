import MLX90640
import numpy as np
from colour import Color
import pygame
import sys
import time
import math
import os

class heat:

    loTemp = (68 - 32) / 1.8
    hiTemp = (100 - 32) / 1.8
    theme = 0

    COLORDEPTH = 1024
    colormap = [0,0,0] * COLORDEPTH

    temps = [0] * 768

    MINspots = False
    MAXspots = False

    AVGspots = 5
    AVGdepth = 4
    AVGindex = 0
    AVGfd = 0
    AVGprint = False
    fileCapture = False

    pygame.font.init()
    font = pygame.font.Font(None, 30)

    readCount = 0
    ready = False
       
    #----------------------------------
    #----------------------------------
    def __init__(self, displaySize=(320,240), SMB=-1 ):
        width, height = displaySize
        # Must set I2C freq to 1MHz in /boot/config.txt to support 32Hz refresh
        refresh = MLX90640.RefreshRate.REFRESH_8_HZ
        if SMB >= 0 :
            import i2cSMB as i2cSMB
            i2c = i2cSMB.i2cSMB(SMB)
        else:
            try:
                import RPi.GPIO as GPIO
                import board
                import busio
                i2c = busio.I2C(board.SCL, board.SDA)
            except Exception as e:
                print(f"No I2C bus found: {e}")
                sys.exit()

        self.mlx = MLX90640.MLX90640(i2c)
        #mlx = MLX90640.MLX90640m0(i2c)     # original driver

        self.mlx.refresh_rate = refresh
        print(f"{self.mlx.version}, refresh {2**(self.mlx.refresh_rate-1)} Hz")

        self.setTheme(2)

        self.heatImage = pygame.surface.Surface((0,0))

        # temperature index
        tIndex = np.array(list(range(0,(32*24)))).reshape((32,24),order='F')
        self.tIndex = np.flip(tIndex,0)
        self.tMag = width/32

        # init spot dictionary
        self.AVG = [{'spot': 0, 'xy': (0,0), 'print': 0, 'raw': [0] * self.AVGdepth} for _ in range(self.AVGspots)]

    #----------------------------------
    def getImage(self, lcd, mode=1):
        # get heat data
        mlx = self.mlx
        temps = self.temps
    
        # current plan:
        #   if mode == 0, read temps, but create black image on output
        #   if MLX doesnot have data ready, use last read

        try:
            self.ready = False
            #dataReady = mlx.dataReady()
            if mlx.dataReady():
                mlx.getFrame(temps)
                self.readCount += 1
                self.ready = True
        except RuntimeError as err:
            print(f"\n\n{err}\n\nMake sure that I2C baudrate is set to 1MHz in /boot/config.txt:\ndtparam=i2c_arm=on,i2c_arm_baudrate=1000000\n\n")
            sys.exit(1)
        except ValueError:
            pass
        except OSError as err:
            print(f"{err}")
            pass

        if self.ready:   # there was a valid read
            if self.MINspots :
                sensor = temps.index(min(temps))
                x, y = np.multiply(np.add(np.argwhere(self.tIndex == sensor),(0.5,0.5)),(self.tMag,self.tMag))[0]
                self.setSpots(0,(x,y))
            if self.MAXspots :
                sensor = temps.index(max(temps))
                x, y = np.multiply(np.add(np.argwhere(self.tIndex == sensor),(0.5,0.5)),(self.tMag,self.tMag))[0]
                self.setSpots(4,(x,y))


        #----------------------------------
        # mode == 0      camera only
        # mode == 1      heat + edge
        # mode == 2      heat + camera
        # mode == 3      heat only
        #----------------------------------

        if mode :
            # heat base layer
            if self.ready :  # there was a valid read
                # map temperatures and create pixels
                #pixels = np.array(list(map(self.map2pixel, temps))).reshape((32,24,3), order='F')
                pixels = np.array([self.map2pixel(p) for p in temps]).reshape((32,24,3), order='F')
                heat = pygame.surfarray.make_surface(np.flip(pixels,0))
                self.heatImage = pygame.transform.smoothscale(heat, lcd.get_size())

            lcd.blit(self.heatImage,(0,0))
        else:
            lcd.fill((0,0,0))

    #----------------------------------
    # spots: display, file, select, accumulate            
    #----------------------------------
    def getSpots(self, lcd):
        # spot temps overlay
        temps = self.temps
        C2F = lambda x : ( x * 9.0/5.0) + 32
        BLACK = (0,0,0)
        WHITE = (255,255,255)
        AVGdepth = self.AVGdepth
        tMag = self.tMag
        font = self.font

        if self.AVGprint:
            self.AVGindex = (self.AVGindex + 1) % AVGdepth
            for A in self.AVG:
                if A['spot']:
                    A['raw'][self.AVGindex] = temps[A['spot']]
                    A['print'] = C2F(sum(A['raw'])/AVGdepth)
                    #A['print'] = C2F(A['raw'][self.AVGindex])
                    if A['xy'] != (0,0) :
                        (x,y) = A['xy']
                        pygame.draw.circle(lcd, (0,0,0)      , A['xy'],  (tMag/2.0)+1, 3)
                        pygame.draw.circle(lcd, (255,255,255), A['xy'], tMag/2.0, 1)

                        Asurf = font.render(f"  {C2F(temps[A['spot']]):.1f}",True,BLACK)
                        lcd.blit(Asurf,(x+1,y+1))
                        lcd.blit(Asurf,(x-1,y-1))
                        lcd.blit(Asurf,(x-1,y+1))
                        lcd.blit(Asurf,(x+1,y-1))
                        Asurf = font.render(f"  {C2F(temps[A['spot']]):.1f}",True,WHITE)
                        lcd.blit(Asurf,A['xy'])

    #----------------------------------
    def fileSpots(self):
        AVG = self.AVG
        if self.fileCapture:
            # output to file requested
            if self.AVGfd == 0 :
                # don't have an opened file to write to yet
                fileDir = "capture/average"
                os.makedirs(fileDir, exist_ok=True)
                fileName = f"{fileDir}/{time.strftime("AVG-%Y%m%d-%H%M%S.dat", time.localtime())}"
                print(f"Saving averages to: {fileName}")
                self.AVGfd = open(fileName, "a")
                refresh = 2 ** (self.refresh_rate-1)
                print(f"{self.mlx.version}, Refresh Rate: {refresh}Hz", file=self.AVGfd)

            if self.AVGprint and self.ready:
                # data ready, and there's an AVG spot printed on screen
                print(*[A['print'] for A in AVG], file=self.AVGfd)      # timestamp?

        elif self.AVGfd != 0 :
            # file output not requested, but there's an output file open
            self.AVGfd.close()
            self.AVGfd = 0
            print("Average file closed")

    #----------------------------------
    def setSpots(self,spot,xy):
        AVG = self.AVG
        AVG[spot]['spot'] = self.xyTsensor(xy)
        AVG[spot]['xy'] = xy
        self.AVGprint = True

    def setMINMAXspots(self, MINspots=False, MAXspots=False) :
        self.AVGprint = True
        self.MINspots = self.MINspots or MINspots
        self.MAXspots = self.MAXspots or MAXspots
        
    def clearSpots(self):
        # the only way to unset a spot is to clear all spots
        for A in self.AVG:
            A['spot'] = 0
            A['xy'] = (0,0)
            A['print'] = 0
        self.AVGprint = False
        self.MINspots = False
        self.MAXspots = False

    def xyTsensor(self, xy):
        # return sensor number for a given display x,y
        tMag = self.tMag
        tIndex = self.tIndex
        xyT = np.divide(xy,(tMag,tMag))
        xT = int(xyT[0])
        yT = int(xyT[1])
        return tIndex[xT][yT]

    #----------------------------------
    # color mapping
    #----------------------------------
    def map2pixel(self,x):
        loTemp = self.loTemp
        hiTemp = self.hiTemp
        COLORDEPTH = self.COLORDEPTH
        constrain = self.constrain

        cindex = (x - loTemp) * (COLORDEPTH - 0) / (hiTemp - loTemp) + 0
        return self.colormap[constrain(int(cindex), 0, COLORDEPTH - 1) ]

    def incrLoTemp( self, incr) :
        if incr:
            self.loTemp += incr
            self.loTemp = min(self.hiTemp-1,max(0,self.loTemp))
        else:
            self.loTemp = min(self.temps)
        
    def incrHiTemp( self, incr) :
        if incr:
            self.hiTemp += incr
            self.hiTemp = min(80,max(self.hiTemp,self.loTemp+1))
        else:
            self.hiTemp = max(self.temps)
        
    #----------------------------------
    # Themes
    #----------------------------------
    def setTheme( self,value ) :
        # generate the colormap for the selected theme
        cmaps = [self.map1, self.map2, self.map3, self.map4]
        self.theme = value % len(cmaps)
        cmaps[self.theme]()
        print(f"Theme: {self.theme}")

    #----------------------------------
    # create different colormaps
    def map1(self) :
        # method 1
        # ... gradient
        heatmap = (
            (0.0, (0, 0, 0)),
            (0.20, (0, 0, 0.5)),
            (0.40, (0, 0.5, 0)),
            (0.60, (0.5, 0, 0)),
            (0.80, (0.75, 0.75, 0)),
            (0.90, (1.0, 0.75, 0)),
            (1.00, (1.0, 1.0, 1.0)),
        )
        self.colormap = [(self.gradient(i, self.COLORDEPTH, heatmap)) for i in range(self.COLORDEPTH)]

    def map2(self) :
        # method 2
        # ... range_to (color)
        blue = Color("indigo")
        red  = Color("red")
        #colors = list(blue.range_to(Color("yellow"), COLORDEPTH))
        colors = list(blue.range_to(Color("red"), self.COLORDEPTH))
        self.colormap = [(int(c.red * 255), int(c.green * 255), int(c.blue * 255)) for c in colors]

    def map3(self) :
        # method 3
        blue = Color("indigo")
        red  = Color("red")
        colors = list(blue.range_to(Color("orange"), self.COLORDEPTH))
        self.colormap = [(int(c.red * 255), int(c.green * 255), int(c.blue * 255)) for c in colors]

    def map4(self) :
        # method 4
        # ... gradient2
        cl = (
        (0,0,0),
        (0,0,0),
        (0,1,0),
        (1,1,0),
        (1,0,0))

        self.colormap = [(self.gradient2(c/self.COLORDEPTH, cl)) for c in range(self.COLORDEPTH)]
     
    #----------------------------------
    # colormaps utility
    def constrain(self, val, min_val, max_val):
            return min(max_val, max(min_val, val))

    def gaussian(self, x, a, b, c, d=0):
        return a * math.exp(-((x - b) ** 2) / (2 * c**2)) + d

    def gradient(self, x, width, cmap, spread=1):
        gaussian = self.gaussian
        constrain = self.constrain
        width = float(width)
        r = sum(
            [gaussian(x, p[1][0], p[0] * width, width / (spread * len(cmap))) for p in cmap]
        )
        g = sum(
            [gaussian(x, p[1][1], p[0] * width, width / (spread * len(cmap))) for p in cmap]
        )
        b = sum(
            [gaussian(x, p[1][2], p[0] * width, width / (spread * len(cmap))) for p in cmap]
        )
        r = int(constrain(r * 255, 0, 255))
        g = int(constrain(g * 255, 0, 255))
        b = int(constrain(b * 255, 0, 255))
        return r, g, b
    
    def gradient2(self, value, cl) :
        numColors = len(cl)
        x = value * (numColors - 1)
        lo = int(x//1)
        hi = int(lo + 1)
        dif = x - lo

        r = int( (cl[lo][0] + dif*(cl[hi][0] - cl[lo][0])) * 255)
        g = int( (cl[lo][1] + dif*(cl[hi][1] - cl[lo][1])) * 255)
        b = int( (cl[lo][2] + dif*(cl[hi][2] - cl[lo][2])) * 255)

        return r,g,b

    #----------------------------------
    # pass-through to MLX90640
    #----------------------------------
    @property
    def refresh_rate(self):
        return self.mlx.refresh_rate

    @refresh_rate.setter
    def refresh_rate(self, rate):
        self.mlx.refresh_rate = rate
        print(f"Refresh Rate: { 2 ** (self.mlx.refresh_rate-1) }")

    #def incrRefreshRate(self,incr) :
    #    self.refresh_rate = self.refresh_rate + incr

    def incr(self, fileCapture=False, AVGprint=False, refresh_rate=0) :
        #print(f"fileCapture: {fileCapture}, self.fileCapture: {self.fileCapture}, refresh_rate: {refresh_rate}")
        self.fileCapture = self.fileCapture != fileCapture
        self.AVGprint = self.AVGprint != AVGprint
        if refresh_rate != 0 :
            self.refresh_rate = self.refresh_rate + refresh_rate

RefreshRate = MLX90640.RefreshRate
