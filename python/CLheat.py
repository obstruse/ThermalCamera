import MLX90640
import numpy as np
from colour import Color
import pygame
import sys
import time
import math

class heat:
    def __init__(self, displaySize=(320,240), SMB=-1 ):
        width, height = displaySize
        # Must set I2C freq to 1MHz in /boot/config.txt to support 32Hz refresh
        refresh = MLX90640.RefreshRate.REFRESH_2_HZ
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

        self.temps = [0] * 768
        self.AVGspots = 4
        self.AVGdepth = 8
        self.AVGindex = 0
        self.AVGfile = ""
        self.AVGfd = 0
        self.AVG = [{'spot': 0, 'xy': (0,0), 'print': 0, 'raw': [0]*self.AVGdepth} for _ in range(self.AVGspots)]

        # pre-define two spots
        #AVG[1]['spot'] = 399
        #AVG[0]['spot'] = 400  
        CM.setTheme(2)

        #----------------------------------
        # temperature index
        tIndex = np.array(list(range(0,(32*24)))).reshape((32,24),order='F')
        self.tIndex = np.flip(tIndex,0)
        self.tMag = width/32
        #tCenter = lcdRect.center
        
    def xyTsensor(self, xy):
        # return sensor number for a given display x,y
        tMag = self.tMag
        tIndex = self.tIndex
        xyT = np.divide(xy,(tMag,tMag))
        xT = int(xyT[0])
        yT = int(xyT[1])
        return tIndex[xT][yT]

    def getImage(self, lcd, mode=1):
        # get heat data
        mlx = self.mlx
        temps = self.temps
    
        # pygame camera buffering causes camera image to lag beind heat image
        # this extra get_image helps.  
        # There will be another camera image available when heat has processed
        #if (cam.query_image() ) :
        #    cam.get_image()

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
            CM.MAXTEMP = max(temps)
            CM.MINTEMP = min(temps)

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
                #pixels = np.array(list(map(CM.map2pixel, temps))).reshape((32,24,3), order='F')
                pixels = np.array([CM.map2pixel(p) for p in temps]).reshape((32,24,3), order='F')
                heat = pygame.surfarray.make_surface(np.flip(pixels,0))
                self.heatImage = pygame.transform.smoothscale(heat, lcd.get_size())

            lcd.blit(self.heatImage,(0,0))
        else:
            lcd.fill((0,0,0))

            



    def getSpots(self, lcd):
        #----------------------------------
        # spot temps overlay
        if AVGprint:
            AVGindex = (AVGindex + 1) % AVGdepth
            for A in AVG:
                if A['spot']:
                    A['raw'][AVGindex] = temps[A['spot']]
                    #A['print'] = C2F(sum(A['raw'])/AVGdepth)
                    A['print'] = C2F(A['raw'][AVGindex])
                    if A['xy'] != (0,0) :
                        shadow = np.subtract(A['xy'],1)
                        pygame.draw.circle(lcd, (0,0,0)      , shadow, 1*tMag, 1)
                        pygame.draw.circle(lcd, (255,255,255), A['xy'], 1*tMag, 1)
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


#------------------------------------------------
class CM :
    MINTEMP = (68 - 32) / 1.8
    MAXTEMP = (100 - 32) / 1.8
    theme = 0

    COLORDEPTH = 1024
    colormap = [0,0,0] * COLORDEPTH
    
    #----------------------------------
    def setTheme( value ) :
        cmaps = [CM.map1, CM.map2, CM.map3, CM.map4]
        CM.theme = value % len(cmaps)
        cmaps[CM.theme]()

         
    def incrMINMAX( incr ) :
        CM.MINTEMP,CM.MAXTEMP = np.add( (CM.MINTEMP,CM.MAXTEMP), incr )
        CM.MINTEMP,CM.MAXTEMP = np.clip( (CM.MINTEMP,CM.MAXTEMP), 0, 80)
        if CM.MINTEMP > CM.MAXTEMP:
            CM.MINTEMP = CM.MAXTEMP
        if CM.MAXTEMP < CM.MINTEMP:
            CM.MAXTEMP = CM.MINTEMP

    #----------------------------------
    # utility
    def constrain(val, min_val, max_val):
            return min(max_val, max(min_val, val))

    def map2pixel(x):
        cindex = (x - CM.MINTEMP) * (CM.COLORDEPTH - 0) / (CM.MAXTEMP - CM.MINTEMP) + 0
        return CM.colormap[CM.constrain(int(cindex), 0, CM.COLORDEPTH - 1) ]

    def gaussian(x, a, b, c, d=0):
        return a * math.exp(-((x - b) ** 2) / (2 * c**2)) + d

    def gradient(x, width, cmap, spread=1):
        width = float(width)
        r = sum(
            [CM.gaussian(x, p[1][0], p[0] * width, width / (spread * len(cmap))) for p in cmap]
        )
        g = sum(
            [CM.gaussian(x, p[1][1], p[0] * width, width / (spread * len(cmap))) for p in cmap]
        )
        b = sum(
            [CM.gaussian(x, p[1][2], p[0] * width, width / (spread * len(cmap))) for p in cmap]
        )
        r = int(CM.constrain(r * 255, 0, 255))
        g = int(CM.constrain(g * 255, 0, 255))
        b = int(CM.constrain(b * 255, 0, 255))
        return r, g, b
    
    def gradient2(value) :
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


    #----------------------------------
    # create different colormaps
    def map1() :
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
        CM.colormap = [(CM.gradient(i, CM.COLORDEPTH, heatmap)) for i in range(CM.COLORDEPTH)]

    def map2() :
        # method 2
        # ... range_to (color)
        blue = Color("indigo")
        red  = Color("red")
        #colors = list(blue.range_to(Color("yellow"), COLORDEPTH))
        colors = list(blue.range_to(Color("red"), CM.COLORDEPTH))
        CM.colormap = [(int(c.red * 255), int(c.green * 255), int(c.blue * 255)) for c in colors]

    def map3() :
        # method 3
        blue = Color("indigo")
        red  = Color("red")
        colors = list(blue.range_to(Color("orange"), CM.COLORDEPTH))
        CM.colormap = [(int(c.red * 255), int(c.green * 255), int(c.blue * 255)) for c in colors]

    def map4() :
        # method 4
        # ... gradient2
        CM.colormap = [(CM.gradient2(c/CM.COLORDEPTH)) for c in range(CM.COLORDEPTH)]
     
