import MLX90640
import numpy as np
from colour import Color
import pygame
import sys
import time
import math

class heat:

    MINTEMP = (68 - 32) / 1.8
    MAXTEMP = (100 - 32) / 1.8
    theme = 0

    COLORDEPTH = 1024
    colormap = [0,0,0] * COLORDEPTH

    temps = [0] * 768

    AVGspots = 4
    AVGdepth = 8
    AVGindex = 0
    AVGfile = ""
    AVGfd = 0
    AVGprint = False

    pygame.font.init()
    font = pygame.font.Font(None, 30)
       
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
            dataReady = mlx.dataReady()
            if dataReady:
                mlx.getFrame(temps)
        except RuntimeError as err:
            print(f"\n\n{err}\n\nMake sure that I2C baudrate is set to 1MHz in /boot/config.txt:\ndtparam=i2c_arm=on,i2c_arm_baudrate=1000000\n\n")
            sys.exit(1)
        except ValueError:
            dataReady = False
            pass
        except OSError as err:
            dataReady = False
            print(f"{err}")
            pass

        if dataReady:   # if it's still ready: no errors during read.
            AVGtemp = sum(temps) / len(temps)
            self.MAXTEMP = max(temps)
            self.MINTEMP = min(temps)

        #----------------------------------
        # mode == 0      camera only
        # mode == 1      heat + edge
        # mode == 2      heat + camera
        # mode == 3      heat only
        #----------------------------------

        if mode :
            # heat base layer
            if dataReady :  # there was a valid read
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
                    #A['print'] = C2F(sum(A['raw'])/AVGdepth)
                    A['print'] = C2F(A['raw'][self.AVGindex])
                    if A['xy'] != (0,0) :
                        shadow = np.subtract(A['xy'],1)
                        pygame.draw.circle(lcd, (0,0,0)      , shadow,  tMag, 1)
                        pygame.draw.circle(lcd, (255,255,255), A['xy'], tMag, 1)
                        Asurf = font.render(f"  {C2F(temps[A['spot']]):.2f}",True,BLACK)
                        lcd.blit(Asurf,shadow)
                        Asurf = font.render(f"  {C2F(temps[A['spot']]):.2f}",True,WHITE)
                        lcd.blit(Asurf,A['xy'])

    def fileSpots(self, file):
        pass
        # at some point there will be file output as well
        #if AVGprint :
        #    if AVGfile == "" :
        #        AVGfile = time.strftime("AVG-%Y%m%d-%H%M%S.dat", time.localtime())
        #        AVGfd = open(AVGfile, "a")
        #        refresh = 2 ** (mlx.refresh_rate-1)
        #        print(f"{mlx.version}, Refresh Rate: {2**(mlx.refresh_rate-1)}Hz", file=AVGfd)

        #    print(*[A['print'] for A in AVG],subPage)
        #    print(*[A['print'] for A in AVG],subPage, file=AVGfd)
        #elif AVGfile != "" :
        #    AVGfd.close()
        #    AVGfile = ""

    def setSpots(self,spot,xy):
        AVG = self.AVG
        AVG[spot]['spot'] = self.xyTsensor(xy)
        AVG[spot]['xy'] = xy
        self.AVGprint = True

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
        MINTEMP = self.MINTEMP
        MAXTEMP = self.MAXTEMP
        COLORDEPTH = self.COLORDEPTH
        constrain = self.constrain

        cindex = (x - MINTEMP) * (COLORDEPTH - 0) / (MAXTEMP - MINTEMP) + 0
        return self.colormap[constrain(int(cindex), 0, COLORDEPTH - 1) ]

    def incrMINMAX( self, incr ) :
        self.MINTEMP,self.MAXTEMP = np.add( (self.MINTEMP,self.MAXTEMP), incr )
        self.MINTEMP,self.MAXTEMP = np.clip( (self.MINTEMP,self.MAXTEMP), 0, 80)
        if self.MINTEMP > self.MAXTEMP:
            self.MINTEMP = self.MAXTEMP
        if self.MAXTEMP < self.MINTEMP:
            self.MAXTEMP = self.MINTEMP

    #----------------------------------
    # Themes
    #----------------------------------
    def setTheme( self,value ) :
        # generate the colormap for the selected theme
        cmaps = [self.map1, self.map2, self.map3, self.map4]
        self.theme = value % len(cmaps)
        cmaps[self.theme]()

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
        self.colormap = [(self.gradient2(c/self.COLORDEPTH)) for c in range(self.COLORDEPTH)]
     
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
    
    def gradient2(self, value) :
        numColors = 5
        cl = (
            (0,0,1),
            (0,1,1),
            (0,1,0),
            (1,1,0),
            (1,0,0))

        x = value * (numColors - 1)
        lo = int(x//1)
        hi = int(lo + 1)
        dif = x - lo

        r = int( (cl[lo][0] + dif*(cl[hi][0] - cl[lo][0])) * 255)
        g = int( (cl[lo][1] + dif*(cl[hi][1] - cl[lo][1])) * 255)
        b = int( (cl[lo][2] + dif*(cl[hi][2] - cl[lo][2])) * 255)

        return r,g,b


