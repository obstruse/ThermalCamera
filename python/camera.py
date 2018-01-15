#!/usr/bin/python

import pygame
import pygame.camera
from pygame.locals import *
import os
from PIL import Image

os.putenv('SDL_FBDEV', '/dev/fb1')
os.putenv('SDL_VIDEODRIVER','fbcon')
os.putenv('SDL_MOUSEDRV', 'TSLIB')
os.putenv('SDL_MOUSEDEV', '/dev/input/touchscreen')

import RPi.GPIO as GPIO

GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)

GPIO.setup(18, GPIO.OUT)
GPIO.output(18, True)

pygame.init()
pygame.camera.init()

lcd = pygame.display.set_mode((320, 240))

cam = pygame.camera.Camera("/dev/video0",(320,240))
cam.start()


image = cam.get_image()

going = True
while going:
	events = pygame.event.get()
	for e in events:
		if (e.type is MOUSEBUTTONDOWN):
#			cam.stop()
			going = False

		if e.type == QUIT or (e.type == KEYDOWN and e.key == K_ESCAPE):
#			cam.stop()
			going = False

	if cam.query_image():
		image = cam.get_image()
	#image = image.convert('1', dither=Image.NONE)
	lcd.blit(image, (0,0))
	pygame.display.flip()

#GPIO.output(18, False)

