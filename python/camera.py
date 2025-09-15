#!/usr/bin/python

import pygame
import pygame.camera
from pygame.locals import *
import os
from PIL import Image

import numpy as np
import cv2

from configparser import ConfigParser

# read config
config = ConfigParser()
config.read('config.ini')
width = config.getint('ThermalCamera','camWidth', fallback=320)
height = config.getint('ThermalCamera','camHeight', fallback=240)
videoDev = config.get('ThermalCamera','videoDev',fallback='/dev/video0')

# initialize display
pygame.display.init()
pygame.display.set_caption('Camera')

pygame.init()

pygame.camera.init()

lcd = pygame.display.set_mode((width,height))

cam = pygame.camera.Camera(videoDev,(width,height)) # actual camera resolution may be different
cam.start()

# center marker
size = 40
markerCV = np.zeros((size, size, 3), dtype=np.uint8)
cv2.drawMarker( markerCV, (size // 2, size // 2), (0, 0, 255), markerType=cv2.MARKER_CROSS, markerSize=size // 2, thickness=2)
marker = pygame.image.frombuffer(markerCV.tobytes(), (size, size), "RGB")
marker.set_colorkey((0, 0, 0))  # make black transparent
markerRect = marker.get_rect(center=(width//2, height // 2))

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
        #print(image)
        lcd.blit(image, (0,0))
        lcd.blit(marker,markerRect)
        pygame.display.flip()
        #running = False

cam.stop()
pygame.quit()

