#!/usr/bin/python

import pygame
import pygame.camera
from pygame.locals import *
import os
from PIL import Image


# if user is root, then output to fb1
if os.geteuid() == 0:
	os.putenv('SDL_FBDEV', '/dev/fb1')
	os.putenv('SDL_VIDEODRIVER','fbcon')
	os.putenv('SDL_MOUSEDRV', 'TSLIB')
	os.putenv('SDL_MOUSEDEV', '/dev/input/touchscreen')

pygame.init()
pygame.camera.init()

if os.geteuid() == 0:
	pygame.mouse.set_visible(False)

lcd = pygame.display.set_mode((320, 240))

cam = pygame.camera.Camera("/dev/video0",(320,240))
cam.start()


image = cam.get_image()

running = True
while running:
	events = pygame.event.get()
	for e in events:
		if (e.type is MOUSEBUTTONDOWN):
			running = False

		if e.type == QUIT or (e.type == KEYDOWN and e.key == K_ESCAPE):
			running = False

	if cam.query_image():
		image = cam.get_image()

	lcd.blit(image, (0,0))
	pygame.display.flip()

cam.stop()
pygame.quit()
GPIO.cleanup()

