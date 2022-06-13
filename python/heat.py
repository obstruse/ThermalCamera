#!/usr/bin/python

import adafruit_mlx90640

import pygame
import pygame.camera
from pygame.locals import *
import os
import math
import time

import numpy as np

from colour import Color

import board
import busio

import RPi.GPIO as GPIO

from configparser import ConfigParser

# read config
config = ConfigParser()
config.read('config.ini')
offsetX = config.getint('ThermalCamera','offsetX')
offsetY = config.getint('ThermalCamera','offsetY')
width = config.getint('ThermalCamera','width')
height = config.getint('ThermalCamera','height')
camFOV = config.getint('ThermalCamera','camFOV')
heatFOV = config.getint('ThermalCamera','heatFOV')


# MUST set I2C freq to 1MHz in /boot/config.txt
i2c = busio.I2C(board.SCL, board.SDA)

GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)


# initialize display environment
try:
        os.putenv('SDL_FBDEV', '/dev/fb1')
        os.putenv('SDL_VIDEODRIVER', 'fbcon')
        os.putenv('SDL_MOUSEDRV', 'TSLIB')
        os.putenv('SDL_MOUSEDEV', '/dev/input/touchscreen')
        os.putenv('SDL_AUDIODRIVER', 'dummy')
        pygame.display.init()
        pygame.mouse.set_visible(False)

except:
        pygame.quit()
        os.unsetenv('SDL_FBDEV')
        os.unsetenv('SDL_VIDEODRIVER')
        os.unsetenv('SDL_MOUSEDRV')
        os.unsetenv('SDL_MOUSEDEV')
        pygame.display.init()
        pygame.display.set_caption('ThermalCamera')


pygame.init()

font = pygame.font.Font(None, 30)

WHITE = (255,255,255)
BLACK = (0,0,0)

# initialize the sensor
mlx = adafruit_mlx90640.MLX90640(i2c)
print("MLX addr detected on I2C, Serial #", [hex(i) for i in mlx.serial_number])
mlx.refresh_rate = adafruit_mlx90640.RefreshRate.REFRESH_32_HZ

# initial low range of the sensor (this will be blue on the screen)
MINTEMP = (68 - 32) / 1.8

# initial high range of the sensor (this will be red on the screen)
MAXTEMP = (100 - 32) / 1.8


# initialize camera
pygame.camera.init()
cam = pygame.camera.Camera("/dev/video0",(width, height))
cam.start()


# create surfaces
# display surface
lcd = pygame.display.set_mode((width,height))
lcdRect = lcd.get_rect()

# heat surface
heat = pygame.surface.Surface((width, height))

# edge detect surface
overlay = pygame.surface.Surface((width, height))
overlay.set_colorkey((0,0,0))

# menu surface
menu = pygame.surface.Surface((width, height))
menu.set_colorkey((0,0,0))


#utility functions
def constrain(val, min_val, max_val):
    return min(max_val, max(min_val, val))

def map_pixel(x, in_min, in_max, out_min, out_max):
    cindex = (x - in_min) * (out_max - out_min) / (in_max - in_min) + out_min
    return colormap[constrain(int(cindex), 0, COLORDEPTH - 1) ]

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

# menu buttons and text
menuMaxPlus = menuButton('+',(230,30),(60,60) )
menuMaxMinus = menuButton('-',(230,90),(60,60) )
menuMinPlus = menuButton('+',(230,150),(60,60) )
menuMinMinus = menuButton('-',(230,210),(60,60) )

menuCapture = menuButton('Capture',(60,30),(120,60) )
menuMode = menuButton('Mode',(60,90),(120,60) )

menuBack = menuButton('Back',(60,150),(120,60) )
menuExit = menuButton('Exit',(60,210),(120,60) )

MAXtext = font.render('MAX', True, WHITE)
MAXtextPos = MAXtext.get_rect(center=(290,20))

MINtext = font.render('MIN', True, WHITE)
MINtextPos = MINtext.get_rect(center=(290,140))

#how many color values we can have
COLORDEPTH = 1024
colormap = [0] * COLORDEPTH

# method 1
# ... gradient
# ... how this works??
# the list of colors we can choose from
heatmap = (
    (0.0, (0, 0, 0)),
    (0.20, (0, 0, 0.5)),
    (0.40, (0, 0.5, 0)),
    (0.60, (0.5, 0, 0)),
    (0.80, (0.75, 0.75, 0)),
    (0.90, (1.0, 0.75, 0)),
    (1.00, (1.0, 1.0, 1.0)),
)
colormap = [(gradient(i, COLORDEPTH, heatmap)) for i in range(COLORDEPTH)]

# method 2
# ... range_to (color)
blue = Color("indigo")
#colors = list(blue.range_to(Color("red"), COLORDEPTH))
#colors = list(blue.range_to(Color("yellow"), COLORDEPTH))
#colormap = [(int(c.red * 255), int(c.green * 255), int(c.blue * 255)) for c in colors]



# streamCapture
streamCapture = 5
GPIO.setup(streamCapture, GPIO.OUT)
GPIO.output(streamCapture, False)
fileNum = 0
fileStream = time.strftime("%Y%m%d-%H%M-", time.localtime())

temps = [0] * 768

# flags
menuDisplay = False 
heatDisplay = 1
imageCapture = False

# Field of View and Scale
imageScale = math.tan(math.radians(camFOV/2.))/math.tan(math.radians(heatFOV/2.))

# heat margins after scaling. Only used for wide heat images (imageScale < 1).
# keep scaled heat image within display boundaries after offsets applied; offset cam image if necessary
marginX = 0
marginY = 0
if ( imageScale < 1 ) :
   marginX = (width/imageScale - width) / 2
   marginY = (height/imageScale - height) / 2

heatOffsetX = 0
heatOffsetY = 0
camOffsetX = 0
camOffsetY = 0

#let the sensor initialize
time.sleep(.1)
        
# loop...
running = True
while(running):

        # scan events
        for event in pygame.event.get():
                if (event.type is MOUSEBUTTONUP):
                        if menuDisplay :
                                pos = pygame.mouse.get_pos()
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

                        else :
                                menuDisplay = True

                if (event.type == KEYUP) :
                        if (event.key == K_ESCAPE) :
                                running = False

                        if (event.key == K_RIGHT) :
                                offsetX += 1
                        if (event.key == K_LEFT) :
                                offsetX -= 1

                        if (event.key == K_DOWN) :
                                offsetY += 1
                        if (event.key == K_UP) :
                                offsetY -= 1

                        # keep the scaled heat image within screen
                        heatOffsetX = offsetX
                        camOffsetX  = 0
                        if ( heatOffsetX > marginX ) :
                            heatOffsetX = marginX
                            camOffsetX  = offsetX - marginX
                        if ( heatOffsetX < -marginX ) :
                            heatOffsetX = -marginX
                            camOffsetX  = offsetX + marginX

                        heatOffsetY = offsetY
                        if ( heatOffsetY > marginY ) :
                            heatOffsetY = marginY
                            camOffsetY  = offsetY - marginY
                        if ( heatOffsetY < -marginY ) :
                            heatOffsetY = -marginY
                            camOffsetY  = offsetY + marginY
                        
                        if (event.key == K_w) :
                                # write config
                                config.set('ThermalCamera', 'offsetX',str(offsetX))
                                config.set('ThermalCamera', 'offsetY',str(offsetY))
                                with open('config.ini', 'w') as f:
                                        config.write(f)
                        #print("offsetX: %d, offsetY: %d, heatOffsetX: %d camOffsetX: %d\n" % (offsetX, offsetY, heatOffsetX, camOffsetX) )


                            
                            


        if heatDisplay :
                # heatDisplay == 0      camera only
                # heatDisplay == 1      heat + camera
                # heatDisplay == 2      heat + edge
                # heatDisplay == 3      heat only

                # read temperatures from sensor
                try:
                    mlx.getFrame(temps)
                except ValueError:
                    continue  # these happen, no biggie - retry

                # map temperatures and create pixels
                pixels = np.array([map_pixel(p, MINTEMP, MAXTEMP, 0, COLORDEPTH - 1) for p in temps]).reshape((32,24,3), order='F')

                # create heat surface from pixels
                heat = pygame.surfarray.make_surface(np.flip(pixels,0))
                # scale up if necessary to match camera
                if imageScale < 1.0 and heatDisplay != 3:
                        heatImage = pygame.transform.smoothscale(heat, (int(width/imageScale),int(height/imageScale)))
                        heatRect = heatImage.get_rect(center=lcdRect.center)
                        pygame.Rect.move_ip(heatRect,heatOffsetX,heatOffsetY)
                else:
                        # show heat, full scale
                        heatImage = pygame.transform.smoothscale(heat, (width,height))
                        heatRect = heatImage.get_rect(center=lcdRect.center)

                lcd.blit(heatImage,heatRect)

                # add camera
                if heatDisplay == 2 :
                        # heat display with edge detect camera overlay
                        camImage = pygame.transform.laplacian(cam.get_image())
                        overlay.fill((0,0,0))
                        pygame.transform.threshold(overlay,camImage,(0,0,0),(40,40,40),(1,1,1),1)
                        if imageScale > 1.0 :
                                overlay2 = pygame.transform.scale(overlay,(int(width*imageScale),int(height*imageScale)))
                        else:
                                overlay2 = overlay

                        overlay2Rect = overlay2.get_rect(center=lcdRect.center)
                        pygame.Rect.move_ip(overlay2Rect,-camOffsetX,-camOffsetY)
                        overlay2.set_colorkey((0,0,0))
                        lcd.blit(overlay2,overlay2Rect)

                if heatDisplay == 1 :
                        # heat display with alpha camera overlay
                        if imageScale > 1.0 :
                                camImage = pygame.transform.scale(cam.get_image(), (int(width*imageScale),int(height*imageScale)))
                        else:
                                camImage = cam.get_image()

                        camRect = camImage.get_rect(center=lcdRect.center)
                        pygame.Rect.move_ip(camRect,-camOffsetX,-camOffsetY)
                        camImage.set_alpha(100)
                        lcd.blit(camImage,camRect)

        else:
                # show camera, full scale, no heat
                camImage = cam.get_image()
                lcd.blit(camImage,(0,0))

        # capture single frame to file, without menu overlay
        if imageCapture :
                imageCapture = False
                fileDate = time.strftime("%Y%m%d-%H%M%S", time.localtime())
                fileName = "/home/pi/Pictures/heat%s.jpg" % fileDate
                pygame.image.save(lcd, fileName)

        # remote stream capture
        # similar to imageCapture, but invoked by GPIO
        # capture continues until stopped
        # from a shell window: start capture:  gpio -g write 5 1
        #                       stop capture:  gpio -g write 5 0
        # (Raspberry Pi 4 requires gpio v2.52
        #     wget https://project-downloads.drogon.net/wiringpi-latest.deb
        #     sudo dpkg -i wiringpi-latest.deb )
        if GPIO.input(streamCapture) :
                fileNum = fileNum + 1
                fileName = "/home/pi/Pictures/heat%s%04d.jpg" % (fileStream, fileNum)
                pygame.image.save(lcd, fileName)
        
        # add menu overlay
        if menuDisplay :
                # display max/min
                lcd.blit(MAXtext,MAXtextPos)
                fahrenheit = MAXTEMP*1.8 + 32
                text = font.render('%d'%fahrenheit, True, WHITE)
                textPos = text.get_rect(center=(290,60))
                lcd.blit(text,textPos)

                lcd.blit(MINtext,MINtextPos)
                fahrenheit = MINTEMP*1.8 + 32
                text = font.render('%d'%fahrenheit, True, WHITE)
                textPos = text.get_rect(center=(290,180))
                lcd.blit(text,textPos)

                lcd.blit(menu,(0,0))

        # display
        pygame.display.update()


cam.stop()
pygame.quit()
GPIO.cleanup()
