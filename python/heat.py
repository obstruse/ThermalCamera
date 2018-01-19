#!/usr/bin/python

from Adafruit_AMG88xx import Adafruit_AMG88xx
import pygame
import pygame.camera
from pygame.locals import *
import os
import math
import time

import numpy as np
from scipy.interpolate import griddata

from colour import Color

import RPi.GPIO as GPIO

GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)

# streamCapture
streamCapture = 5
GPIO.setup(streamCapture, GPIO.OUT)
GPIO.output(streamCapture, False)
fileNum = 0
fileStream = time.strftime("%Y%m%d-%H%M-", time.localtime())


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
height = 240
width = 320


#initialize the sensor and environment
sensor = Adafruit_AMG88xx()

#how many color values we can have
COLORDEPTH = 1024

WHITE = (255,255,255)
BLACK = (0,0,0)

points = [(math.floor(ix / 8), (ix % 8)) for ix in range(0, 64)]
grid_x, grid_y = np.mgrid[0:7:32j, 0:7:32j]

#the list of colors we can choose from
blue = Color("indigo")
colors = list(blue.range_to(Color("red"), COLORDEPTH))

#create the array of colors
colors = [(int(c.red * 255), int(c.green * 255), int(c.blue * 255)) for c in colors]

#displayPixelWidth = width / 30
displayPixelWidth = 11
displayPixelHeight = height / 30
displayPixelHeight = height / 30

# initial low range of the sensor (this will be blue on the screen)
#MINTEMP = 26
MINTEMP = (73 - 32) / 1.8

# initial high range of the sensor (this will be red on the screen)
#MAXTEMP = 32
MAXTEMP = (79 - 32) / 1.8


# initialize camera
pygame.camera.init()
cam = pygame.camera.Camera("/dev/video0",(width, height))
cam.start()


# create surfaces
# display surface
lcd = pygame.display.set_mode((width,height))

# edge detect surface
overlay = pygame.surface.Surface((width, height))
overlay.set_colorkey((0,0,0))

# menu surface
menu = pygame.surface.Surface((width, height))
menu.set_colorkey((0,0,0))


#utility functions
def constrain(val, min_val, max_val):
    return min(max_val, max(min_val, val))

def map(x, in_min, in_max, out_min, out_max):
  return (x - in_min) * (out_max - out_min) / (in_max - in_min) + out_min

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
menuHeat = menuButton('Heat',(60,90),(120,60) )

menuBack = menuButton('Back',(60,150),(120,60) )
menuExit = menuButton('Exit',(60,210),(120,60) )

MAXtext = font.render('MAX', True, WHITE)
MAXtextPos = MAXtext.get_rect(center=(290,20))

MINtext = font.render('MIN', True, WHITE)
MINtextPos = MINtext.get_rect(center=(290,140))


# flags
menuDisplay = False 
heatDisplay = 1
imageCapture = False

#let the sensor initialize
time.sleep(.1)
	

running = True
while(running):

	# scan events
	for event in pygame.event.get():
		if (event.type is MOUSEBUTTONUP):
			if menuDisplay :
				pos = pygame.mouse.get_pos()
				if menuMaxPlus.collidepoint(pos):
					MAXTEMP+=1
				if menuMaxMinus.collidepoint(pos):
					MAXTEMP-=1
				if menuMinPlus.collidepoint(pos):
					MINTEMP+=1
				if menuMinMinus.collidepoint(pos):
					MINTEMP-=1

				if menuBack.collidepoint(pos):
					menuDisplay = False
				if menuExit.collidepoint(pos):
					running = False

				if menuHeat.collidepoint(pos):
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

	if heatDisplay :
		#read the pixels
		pixels = sensor.readPixels()
		pixels = [map(p, MINTEMP, MAXTEMP, 0, COLORDEPTH - 1) for p in pixels]
		
		#perform interpolation
		bicubic = griddata(points, pixels, (grid_x, grid_y), method='cubic')
		
		#draw everything
		for ix, row in enumerate(bicubic):
			for jx, pixel in enumerate(row):
				rect = (displayPixelWidth * (30 - ix), displayPixelHeight * jx, displayPixelWidth, displayPixelHeight)
				color = colors[constrain(int(pixel), 0, COLORDEPTH- 1)]
				lcd.fill(color, rect)
		# add camera
		if heatDisplay == 2 :
			camImage = pygame.transform.laplacian(cam.get_image())
			pygame.transform.threshold(overlay,camImage,(0,0,0),(40,40,40),(1,1,1),1)
			overlay.set_colorkey((0,0,0))
			lcd.blit(overlay,(0,0))

		if heatDisplay == 1 :
			camImage = cam.get_image()
			camImage.set_alpha(100)
			lcd.blit(camImage,(0,0))

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

	else:
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
	# for example,from a shell window: start capture:  gpio -g 5 1
	#                                  stop capture:   gpio -g 5 0
	if GPIO.input(streamCapture) :
		fileNum = fileNum + 1
		fileName = "/home/pi/Pictures/heat%s%04d.jpg" % (fileStream, fileNum)
		pygame.image.save(lcd, fileName)
	
        # add menu overlay
        if menuDisplay :
                lcd.blit(menu,(0,0))

	# display
	pygame.display.update()


cam.stop()
pygame.quit()
GPIO.cleanup()
