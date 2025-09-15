#!/usr/bin/python

import pygame
import pygame.camera
from pygame.locals import *
import os
from PIL import Image

from configparser import ConfigParser

# read config
config = ConfigParser()
config.read('config.ini')
width = config.getint('ThermalCamera','camwidth', fallback=320)
height = config.getint('ThermalCamera','camheight', fallback=240)
videoDev = config.get('ThermalCamera','videoDev',fallback='/dev/video0')

# initialize display
pygame.display.init()
pygame.display.set_caption('Camera')

pygame.init()

pygame.camera.init()

lcd = pygame.display.set_mode((width,height))

cam = pygame.camera.Camera(videoDev,(width,height)) # actual camera resolution may be different
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
		image = pygame.transform.scale(cam.get_image(), (width,height))
		lcd.blit(image, (0,0))
		pygame.display.flip()

cam.stop()
pygame.quit()

