#!/usr/bin/env python

import sys
import os
os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = "hide"
import MLX90640

import pygame
import pygame.camera
from pygame.locals import *

import math
import time

import numpy as np

from colour import Color

#import RPi.GPIO as GPIO

from configparser import ConfigParser

# change to the python directory
os.chdir(os.path.dirname(os.path.abspath(__file__)))

# read config
config = ConfigParser()
config.read('config.ini')
offsetX = config.getint('ThermalCamera','offsetX',fallback=0)
offsetY = config.getint('ThermalCamera','offsetY',fallback=0)
width = config.getint('ThermalCamera','width',fallback=320)
height = config.getint('ThermalCamera','height',fallback=240)
camWidth = config.getint('ThermalCamera','camWidth',fallback=320)
camHeight = config.getint('ThermalCamera','camHeight',fallback=240)
camFOV = config.getint('ThermalCamera','camFOV',fallback=45)
heatFOV = config.getint('ThermalCamera','heatFOV',fallback=45)
theme = config.getint('ThermalCamera','theme',fallback=1)
videoDev = config.get('ThermalCamera','videoDev',fallback='/dev/video0')
SMB = config.getint('ThermalCamera','SMB',fallback=-1)

# initialize display environment
pygame.display.init()
pygame.display.set_caption('ThermalCamera')

pygame.init()

font = pygame.font.Font(None, 30)

WHITE = (255,255,255)
BLACK = (0,0,0)

#----------------------------------
# initialize the sensor
if SMB >= 0 :
    import i2cSMB as i2cSMB
    i2c = i2cSMB.i2cSMB(SMB)
    refresh = MLX90640.RefreshRate.REFRESH_4_HZ
else:
    try:
        import RPi.GPIO as GPIO
        import board
        import busio
        # Must set I2C freq to 1MHz in /boot/config.txt to support 32Hz refresh
        i2c = busio.I2C(board.SCL, board.SDA)
        refresh = MLX90640.RefreshRate.REFRESH_1_HZ
    except Exception as e:
        print(f"No I2C bus found: {e}")
        sys.exit()

mlx = MLX90640.MLX90640(i2c)
#print("MLX addr detected on I2C, Serial #", [hex(i) for i in mlx.serial_number])
print(mlx.version,refresh)

# refresh rate for a 'subpage', half the pixels in the heat image changing
# The highest refresh rate for 100kHz I2C is 4Hz
# At 1mHz I2C you can use 32Hz refresh rate
mlx.refresh_rate = refresh

temps = [0] * 768
AVGspots = 4
AVGdepth = 6    # the heat noise looks like a 3  cycle, skips highest/lowest, so 6 for smoothing
AVGindex = 0
AVGprint = False
AVGfile = ""
AVGfd = 0
AVG = [{'spot': 0, 'print': 0, 'mark': 99, 'raw': [0]*AVGdepth} for _ in range(AVGspots)]

# pre-define2 two spots ... I think I also want to turn off the averaging
AVG[3]['spot'] = 398
AVG[3]['mark'] = 99
AVG[2]['spot'] = 401
AVG[2]['mark'] = 99

AVG[1]['spot'] = 399
AVG[1]['mark'] = 99
AVG[0]['spot'] = 400
AVG[0]['mark'] = 99

# initial low range of the sensor (this will be blue on the screen)
MINTEMP = (68 - 32) / 1.8

# initial high range of the sensor (this will be red on the screen)
MAXTEMP = (100 - 32) / 1.8


#----------------------------------
# initialize camera
pygame.camera.init()
cam = pygame.camera.Camera(videoDev,(camWidth, camHeight))  # actual camera resolution may be different
cam.start()
(camWidth,camHeight) = cam.get_size()
#print(cam.get_size())

#----------------------------------
# initialize streamCapture
import mmap
fd = os.open('/dev/shm/ThermalCamera', os.O_CREAT | os.O_TRUNC | os.O_RDWR)
assert os.write(fd, b'\x00' * mmap.PAGESIZE) == mmap.PAGESIZE
TCmap = mmap.mmap(fd, mmap.PAGESIZE, mmap.MAP_SHARED, mmap.PROT_WRITE)
fileNum = 0
fileDate = ""
streamDir = ""

#----------------------------------
# create surfaces
# display surface
lcd = pygame.display.set_mode((width,height))
#lcd = pygame.display.set_mode((width,height), pygame.FULLSCREEN)
lcdRect = lcd.get_rect()

# heat surface and sensor temperature index
heat = pygame.surface.Surface((32,24))
tIndex = np.array(list(range(0,(32*24)))).reshape((32,24),order='F')
tIndex = np.flip(tIndex,0)
tCenter = (0,0)  # center of the heat image
tMag = 1

# camera edge detect overlay surface determined by setCamerFOV()

# menu surface
menu = pygame.surface.Surface((width, height))
menu.set_colorkey((0,0,0))

#----------------------------------
#utility functions
def setCameraFOV(FOV) :
    global imageScale
    global overlay

    # Field of View and Scale
    imageScale = math.tan(math.radians(camFOV/2.))/math.tan(math.radians(heatFOV/2.))
    #print(f"imageScale: {imageScale}")

    # camera edge detect overlay surface
    # scaled to match display size and preserve aspect ratio
    overlay = pygame.surface.Surface((int(width*imageScale), int(width*(camHeight/camWidth)*imageScale)))
    overlay.set_colorkey((0,0,0))

def getCameraScaled(scale=None):
    if scale == None:
        scale = imageScale
    return pygame.transform.scale(cam.get_image(),(int(width*scale), int(width*(camHeight/camWidth)*scale)))

def xyTsensor(xy):
    offset = np.subtract(xy, lcdRect.center)
    xyA = np.add(offset,tCenter)
    xyT = np.divide(xyA,(tMag,tMag))
    xT = int(xyT[0])
    yT = int(xyT[1])

    #print(f"xT,yT: {(xT,yT)}   x,y: {xy}")
    #print(f"    tSensor: {tIndex[xT][yT]}") 
    return tIndex[xT][yT]

def C2F(c):
    return (c * 9.0/5.0) + 32.0
       
def constrain(val, min_val, max_val):
    return min(max_val, max(min_val, val))

def map_pixel(x, in_min, in_max, out_min, out_max):
    cindex = (x - in_min) * (out_max - out_min) / (in_max - in_min) + out_min
    return colormap[theme][constrain(int(cindex), 0, COLORDEPTH - 1) ]

def gaussian(x, a, b, c, d=0):
    return a * math.exp(-((x - b) ** 2) / (2 * c**2)) + d

def gradient(x, width, cmap, spread=1):
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

def menuButton( menuText, menuCenter, menuSize ) :
        mbSurf = font.render(menuText,True,WHITE)
        mbRect = mbSurf.get_rect(center=menuCenter)
        menu.blit(mbSurf,mbRect)

        mbRect.size = menuSize
        mbRect.center = menuCenter
        pygame.draw.rect(menu,WHITE,mbRect,3)

        return mbRect

#----------------------------------
# menu buttons and text
menuCapture = menuButton('Capture',(60,30),(120,60) )
menuMode = menuButton('Mode',(60,90),(120,60) )

menuBack = menuButton('Back',(60,150),(120,60) )
menuExit = menuButton('Exit',(60,210),(120,60) )

menuMaxPlus = menuButton('+',(width-90,30),(60,60) )
menuMaxMinus = menuButton('-',(width-90,90),(60,60) )
menuMinPlus = menuButton('+',(width-90,150),(60,60) )
menuMinMinus = menuButton('-',(width-90,210),(60,60) )

menuAvg = menuButton('AVG',(width-90,270),(60,60) )

MAXtext = font.render('MAX', True, WHITE)
MAXtextPos = MAXtext.get_rect(center=(width-30,20))
MAXnum  = font.render('999', True, WHITE)
MAXnumPos  = MAXnum.get_rect(center=(width-30,60))

MINtext = font.render('MIN', True, WHITE)
MINtextPos = MINtext.get_rect(center=(width-30,140))
MINnum  = font.render('999', True, WHITE)
MINnumPos  = MINnum.get_rect(center=(width-30,180))

AVGtemp = 0
AVGnum = font.render('999', True, WHITE)
AVGnumPos = AVGnum.get_rect(center=(width-30,270))

#----------------------------------
# colors
COLORDEPTH = 2048
colormap = [None] * 4

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
colormap[0] = [(gradient(i, COLORDEPTH, heatmap)) for i in range(COLORDEPTH)]

# method 2
# ... range_to (color)
blue = Color("indigo")
red  = Color("red")
#colors = list(blue.range_to(Color("yellow"), COLORDEPTH))
colors = list(blue.range_to(Color("red"), COLORDEPTH))
colormap[1] = [(int(c.red * 255), int(c.green * 255), int(c.blue * 255)) for c in colors]
colors = list(blue.range_to(Color("orange"), COLORDEPTH))
colormap[2] = [(int(c.red * 255), int(c.green * 255), int(c.blue * 255)) for c in colors]
colors = list(red.range_to(Color("yellow"), COLORDEPTH))
colormap[3] = [(int(c.red * 255), int(c.green * 255), int(c.blue * 255)) for c in colors]

#----------------------------------
# flags
menuDisplay = False 
heatDisplay = 1
imageCapture = False

imageScale = 1.0
setCameraFOV(camFOV)

# heat margins after scaling. Only used for wide heat images (imageScale < 1).
# keep edges of scaled heat image outside display boundaries after offsets applied; offset cam image if necessary
marginX = 0
marginY = 0
if imageScale < 1 :
   marginX = (width/imageScale - width) / 2
   marginY = (height/imageScale - height) / 2

heatOffsetX = 0
heatOffsetY = 0
camOffsetX = 0
camOffsetY = 0

# event to calculate offsets (playing with events...)
OFFSETS = pygame.event.Event(pygame.USEREVENT)

# trigger offset calculation
pygame.event.post(OFFSETS)

timeStart = time.time()
frameStart = time.time()

#----------------------------------
# loop...
running = True
while(running):

        #print(f"frame ms: {int((time.time() - frameStart) * 1000)} FPS: {int(1/(time.time() - frameStart))}")
        frameStart = time.time()

        # scan events
        for event in pygame.event.get():
                if (event.type == MOUSEBUTTONUP):
                        pos = event.pos
                        if event.button == 2:
                            AVG[1]['spot'] = xyTsensor(pos)
                            AVG[1]['mark'] = 0
                        if event.button == 3:
                            AVG[0]['spot'] = xyTsensor(pos)
                            AVG[0]['mark'] = 99
                        if menuDisplay and event.button == 1 :
                                if menuMaxPlus.collidepoint(pos):
                                        MAXTEMP+=1
                                        if MAXTEMP > 80 :
                                                MAXTEMP = 80
                                if menuMaxMinus.collidepoint(pos):
                                        MAXTEMP-=1
                                        if MAXTEMP < 1 :
                                                MAXTEMP = 1
                                        if MAXTEMP <= MINTEMP :
                                                MINTEMP = MAXTEMP - 1
                                if menuMinPlus.collidepoint(pos):
                                        MINTEMP+=1
                                        if MINTEMP > 79 :
                                                MINTEMP = 79
                                        if MINTEMP >= MAXTEMP :
                                                MAXTEMP = MINTEMP + 1
                                if menuMinMinus.collidepoint(pos):
                                        MINTEMP-=1
                                        if MINTEMP < 0 :
                                                MINTEMP = 0

                                if menuBack.collidepoint(pos):
                                        lcd.fill((0,0,0))
                                        menuDisplay = False
                                if menuExit.collidepoint(pos):
                                        running = False

                                if menuMode.collidepoint(pos):
                                        heatDisplay+=1
                                        if heatDisplay > 3 :
                                                heatDisplay = 0
                                if menuCapture.collidepoint(pos):
                                        imageCapture = not imageCapture

                                if menuAvg.collidepoint(pos):
                                       MAXTEMP = AVGtemp + (2 / 1.8)
                                       MINTEMP = AVGtemp - (2 / 1.8)

                        elif not menuDisplay and event.button == 1 :
                                menuDisplay = True

                if (event.type == KEYUP) :
                        if (event.key == K_ESCAPE) :
                                running = False

                        if (event.key == K_RIGHT) :
                                offsetX += 1
                                pygame.event.post(OFFSETS)
                        if (event.key == K_LEFT) :
                                offsetX -= 1
                                pygame.event.post(OFFSETS)

                        if (event.key == K_DOWN) :
                                offsetY += 1
                                pygame.event.post(OFFSETS)
                        if (event.key == K_UP) :
                                offsetY -= 1
                                pygame.event.post(OFFSETS)

                        if event.key == K_KP_PLUS :
                               camFOV += 1
                               setCameraFOV(camFOV)
                               print(f"camFOV: {camFOV}")
                        if event.key == K_KP_MINUS :
                               camFOV -= 1
                               setCameraFOV(camFOV)
                               print(f"camFOV: {camFOV}")

                        if event.key == K_PAGEUP :
                            mlx.refresh_rate = mlx.refresh_rate + 1
                            print(f"Refresh Rate: { 2 ** (mlx.refresh_rate-1) }")
                        if event.key == K_PAGEDOWN :
                            mlx.refresh_rate = mlx.refresh_rate - 1
                            print(f"Refresh Rate: { 2 ** (mlx.refresh_rate-1) }")

                        if event.key == K_p :
                            AVGprint = not AVGprint

                        if event.key == K_t :
                            theme = (theme +1) % len(colormap)
                                                              
                        if (event.key == K_w) :
                                # write config
                                config.set('ThermalCamera', 'offsetX',str(offsetX))
                                config.set('ThermalCamera', 'offsetY',str(offsetY))
                                config.set('ThermalCamera', 'camFOV',str(camFOV))
                                with open('config.ini', 'w') as f:
                                        config.write(f)

                if (event == OFFSETS) :
                        # keep the offset scaled heat image within screen, move camera if necessary
                        # changed my mind:  move the camera image, don't move the heat image
                        #heatOffsetX = offsetX
                        #camOffsetX  = 0
                        #if ( heatOffsetX > marginX ) :
                        #    heatOffsetX = marginX
                        #    camOffsetX  = offsetX - marginX
                        #if ( heatOffsetX < -marginX ) :
                        #    heatOffsetX = -marginX
                        #    camOffsetX  = offsetX + marginX
                        #
                        #
                        #heatOffsetY = offsetY
                        #camOffsetY = 0
                        #if ( heatOffsetY > marginY ) :
                        #    heatOffsetY = marginY
                        #    camOffsetY  = offsetY - marginY
                        #if ( heatOffsetY < -marginY ) :
                        #    heatOffsetY = -marginY
                        #    camOffsetY  = offsetY + marginY
                        heatOffsetX = 0
                        heatOffsetY = 0
                        camOffsetX = offsetX
                        camOffsetY = offsetY
                        # need to clean this up later (if it works OK)

                            
                            


        if heatDisplay :
                # the pygame camera buffering causes the camera image to lag beind the heat image
                # this extra get_image helps.  
                # There will be another camera image available when heat has processed
                if (cam.query_image() ) :
                    cam.get_image()

                # heatDisplay == 0      camera only
                # heatDisplay == 1      heat + edge
                # heatDisplay == 2      heat + camera
                # heatDisplay == 3      heat only

                # read temperatures from sensor
                try:
                    subPage = mlx.getFrame(temps)
                except RuntimeError as err:
                    print(f"\n\n{err}\n\nMake sure that I2C baudrate is set to 1MHz in /boot/config.txt:\ndtparam=i2c_arm=on,i2c_arm_baudrate=1000000\n\n")
                    sys.exit(1)
                except ValueError:
                    continue
                except OSError as err:
                    print(f"{err}")
                    continue

                
                timeStart = time.time()

                # print averages
                AVGindex = (AVGindex + 1) % AVGdepth
                for A in AVG:
                    if A['spot']:
                        #AVGprint = True
                        A['raw'][AVGindex] = temps[A['spot']]
                        temps[A['spot']] = A['mark']
                        #A['print'] = C2F(sum(A['raw'])/AVGdepth)
                        A['print'] = C2F(A['raw'][AVGindex])
                if AVGprint :
                    if AVGfile == "" :
                        AVGfile = time.strftime("AVG-%Y%m%d-%H%M%S.dat", time.localtime())
                        AVGfd = open(AVGfile, "a")
                        refresh = 2 ** (mlx.refresh_rate-1)
                        print(f"{mlx.version}, Refresh Rate: {2**(mlx.refresh_rate-1)}Hz", file=AVGfd)

                    print(*[A['print'] for A in AVG],subPage)
                    print(*[A['print'] for A in AVG],subPage, file=AVGfd)
                elif AVGfile != "" :
                    AVGfd.close()
                    AVGfile = ""

                # map temperatures and create pixels
                pixels = np.array([map_pixel(p, MINTEMP, MAXTEMP, 0, COLORDEPTH - 1) for p in temps]).reshape((32,24,3), order='F')
                AVGtemp = sum(temps) / len(temps)

                # create heat surface from pixels
                heat = pygame.surfarray.make_surface(np.flip(pixels,0))
                # scale up if necessary to match camera
                # ...changed my mind.  There's so little resolution to the heat image, scale up looks worse.
                # So, is it a video camera with heat overlay, or heat camera with video overlay?
                # I say it's a heat camera, so primarily is should show as much of the heat image as possible.
                # ... if that's so, shouldn't the display aspect match the heat image and not the video image?
                # TODO: match display aspect ratio to heat image?

                # Scale heat image to fit screen.  Pad/truncate verticle is needed
                #if imageScale < 1.0 and heatDisplay != 3:
                #        # TODO:  this isn't right, but I don't need it yet, so...
                #        heatImage = pygame.transform.smoothscale(heat, (int(width/imageScale),int(height/imageScale)))
                #        tCenter = heatImage.get_rect().center
                #        tMag = (width/imageScale)/32
                #        heatRect = heatImage.get_rect(center=lcdRect.center)
                #        pygame.Rect.move_ip(heatRect,heatOffsetX,heatOffsetY)
                #else:
                #        # show heat, full width
                #        # since the aspect ratio is probably not the same as the display,
                #        # the height will be truncated or padded 
                #        heatImage = pygame.transform.smoothscale(heat, (width,int(width*24/32)))
                #        tCenter = heatImage.get_rect().center
                #        tMag = width/32
                #        heatRect = heatImage.get_rect(center=lcdRect.center)

                heatImage = pygame.transform.smoothscale(heat, (width,int(width*24/32)))
                tCenter = heatImage.get_rect().center
                tMag = width/32
                heatRect = heatImage.get_rect(center=lcdRect.center)

                lcd.blit(heatImage,heatRect)

                # add camera
                if heatDisplay == 1 :
                        # heat display with edge detect camera overlay
                        #camImage = pygame.transform.laplacian(cam.get_image())
                        camImage = pygame.transform.laplacian(getCameraScaled())
                        overlay.fill((0,0,0))
                        pygame.transform.threshold(overlay,camImage,(0,0,0),(40,40,40),(1,1,1),1)
                        # ...changed my mind.
                        # Scale camera to fit heat image
                        #if imageScale > 1.0 :
                        #        overlay2 = pygame.transform.scale(overlay,(int(width*imageScale),int(height*imageScale)))
                        #else:
                        #        # show camera, full width
                        #        # the aspect ratio is the same as display,
                        #        # so it shows the full frame
                        #        overlay2 = pygame.transform.scale(overlay,(width,height))

                        #overlay2 = pygame.transform.scale(overlay,(int(width*imageScale),int(height*imageScale)))
                        overlayRect = overlay.get_rect(center=lcdRect.center)
                        pygame.Rect.move_ip(overlayRect,-camOffsetX,-camOffsetY)
                        overlay.set_colorkey((0,0,0))
                        lcd.blit(overlay,overlayRect)

                if heatDisplay == 2 :
                        # heat display with alpha camera overlay
                        #if imageScale > 1.0 :
                        #        camImage = pygame.transform.scale(cam.get_image(), (int(width*imageScale),int(height*imageScale)))
                        #else:
                        #        camImage = pygame.transform.scale(cam.get_image(), (width,height))
                        #camImage = pygame.transform.scale(cam.get_image(), (int(width*imageScale),int(height*imageScale)))
                        camImage = getCameraScaled()
                        camRect = camImage.get_rect(center=lcdRect.center)
                        pygame.Rect.move_ip(camRect,-camOffsetX,-camOffsetY)
                        camImage.set_alpha(100)
                        lcd.blit(camImage,camRect)

        else:
                # show camera, full scale, no heat
                #camImage = pygame.transform.scale(cam.get_image(), (width,height))
                #lcd.blit(camImage,(0,0))
                lcd.blit(getCameraScaled(1.0),(0,0))

        # capture single frame to file, without menu overlay
        if imageCapture :
                imageCapture = False
                fileName = "%s/heat%s.jpg" % (os.path.expanduser('~/Pictures'), time.strftime("%Y%m%d-%H%M%S",time.localtime()) )
                pygame.image.save(lcd, fileName)

        # remote stream capture
        # similar to imageCapture, but invoked by GPIO
        # capture continues until stopped
        #print(f"TCmap {TCmap[0]} - {TCmap[0]:x}")
        if TCmap[0] == ord('1') :
                if fileNum == 0 :
                        # store in subdirectory of working directory
                        streamDir = time.strftime("%Y%m%d-%H%M%S", time.localtime())
                        os.mkdir(streamDir)

                #fileName = "%s/heat%s-%04d.jpg" % (os.path.expanduser('~/Pictures'), fileDate, fileNum)
                fileName = f"{streamDir}/{fileNum:04d}.jpg"
                fileNum = fileNum + 1
                pygame.image.save(lcd, fileName)

        elif fileNum != 0 :
                fileNum = 0
                print("frames captured:",fileNum)


        # from a shell window: start capture:  gpio -g write 5 1
        #                       stop capture:  gpio -g write 5 0
        # (Raspberry Pi 4 requires gpio v2.52
        #     wget https://project-downloads.drogon.net/wiringpi-latest.deb
        #     sudo dpkg -i wiringpi-latest.deb )
        #if GPIO.input(streamCapture) :
        #        if fileDate == "" :
        #                fileDate = time.strftime("%Y%m%d-%H%M%S", time.localtime())
        #                fileNum = 0

        #        fileName = "%s/heat%s-%04d.jpg" % (os.path.expanduser('~/Pictures'), fileDate, fileNum)
        #        fileNum = fileNum + 1
        #        pygame.image.save(lcd, fileName)

        #if not GPIO.input(streamCapture) and fileDate != "" :
        #        fileDate = ""
        #        print("frames captured:",fileNum)

        # add menu overlay
        if menuDisplay :
                # display max/min
                lcd.blit(MAXtext,MAXtextPos)
                fahrenheit = MAXTEMP*1.8 + 32
                MAXnum = font.render('%d'%fahrenheit, True, WHITE)
                textPos = MAXnum.get_rect(center=MAXnumPos.center)
                lcd.blit(MAXnum,textPos)

                lcd.blit(MINtext,MINtextPos)
                fahrenheit = MINTEMP*1.8 + 32
                MINnum = font.render('%d'%fahrenheit, True, WHITE)
                textPos = MINnum.get_rect(center=MINnumPos.center)
                lcd.blit(MINnum,textPos)

                AVGf = AVGtemp*1.8 + 32
                AVGnum = font.render('%d'%AVGf, True, WHITE)
                textPos = AVGnum.get_rect(center=AVGnumPos.center)
                lcd.blit(AVGnum, textPos)

                lcd.blit(menu,(0,0))

        # display
        pygame.display.update()


cam.stop()
pygame.quit()
#GPIO.cleanup()
