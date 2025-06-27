#!/usr/bin/env python

import os
os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = "hide"
import pygame

import CLcamera as camera
cam = camera.camera('/dev/video1',(640,480),(320,240))
#cam.setCameraFOV(45)

pygame.display.init()
pygame.display.set_caption('CLtest')

pygame.init()
lcd = pygame.display.set_mode((320,240))

while True:
    lcd.fill((0,0,0))
    cam.getImage(lcd, 1)
    pygame.display.update()
