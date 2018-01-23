#!/usr/bin/python

import pygame
import pygame.camera
from pygame.locals import *
import os
from PIL import Image

# initialize display
try:
	os.putenv('SDL_FBDEV', '/dev/fb1')
	os.putenv('SDL_VIDEODRIVER','fbcon')
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
	pygame.display.set_caption('Camera')

pygame.init()

pygame.camera.init()

height = 240
width = 320

lcd = pygame.display.set_mode((width,height))

cam = pygame.camera.Camera("/dev/video0",(width,height))
cam.start()

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

