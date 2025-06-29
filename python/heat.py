#!/usr/bin/env python

import sys
import os
os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = "hide"

import pygame
#import pygame.camera
from pygame.locals import *

import math
import time
from pathlib import Path

import numpy as np
from colour import Color

import CLcamera as camera
import CLheat

def main() :

    # change to the python directory
    os.chdir(os.path.dirname(os.path.abspath(__file__)))

    #----------------------------------
    # read config
    from configparser import ConfigParser
    config = ConfigParser()
    config.read('config.ini')
    camOffsetX = config.getint('ThermalCamera','offsetX',fallback=0)
    camOffsetY = config.getint('ThermalCamera','offsetY',fallback=0)
    width = config.getint('ThermalCamera','width',fallback=320)
    height = config.getint('ThermalCamera','height',fallback=240)
    camWidth = config.getint('ThermalCamera','camWidth',fallback=320)
    camHeight = config.getint('ThermalCamera','camHeight',fallback=240)
    camFOV = config.getint('ThermalCamera','camFOV',fallback=45)
    heatFOV = config.getint('ThermalCamera','heatFOV',fallback=45)
    theme = config.getint('ThermalCamera','theme',fallback=1)
    videoDev = config.get('ThermalCamera','videoDev',fallback='/dev/video0')
    SMB = config.getint('ThermalCamera','SMB',fallback=-1)

    #----------------------------------
    # initialize display environment
    pygame.display.init()
    pygame.display.set_caption('ThermalCamera')

    pygame.init()

    font = pygame.font.Font(None, 30)

    WHITE = (255,255,255)
    BLACK = (0,0,0)

    #----------------------------------
    # initialize the sensor
    # Must set I2C freq to 1MHz in /boot/config.txt to support 32Hz refresh
    try:
        mlx = CLheat.heat((width,height),SMB)
    except Exception as e:
         print(e)
         sys.exit()

    #----------------------------------
    # initialize camera
    cam = camera.camera(videoDev,(camWidth, camHeight),(width,height),(camOffsetX,camOffsetY),camFOV=camFOV, heatFOV=heatFOV)

    #----------------------------------
    # initialize streamCapture
    ##import mmap
    ##fd = os.open('/dev/shm/ThermalCamera', os.O_CREAT | os.O_TRUNC | os.O_RDWR)
    ##assert os.write(fd, b'\x00' * mmap.PAGESIZE) == mmap.PAGESIZE
    ##TCmap = mmap.mmap(fd, mmap.PAGESIZE, mmap.MAP_SHARED, mmap.PROT_WRITE)
    fileNum = 0
    fileDate = ""
    streamDir = ""

    #----------------------------------
    # create surfaces
    # display surface
    lcd = pygame.display.set_mode((width,height))
    #lcd = pygame.display.set_mode((width,height), pygame.FULLSCREEN)
    lcdRect = lcd.get_rect()

    #----------------------------------
    # menu surface
    menu = pygame.surface.Surface((width, height))
    menu.set_colorkey((0,0,0))

    #----------------------------------
    #utility functions
    def C2F(c):
        return (c * 9.0/5.0) + 32.0
        
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
    # bluetooth shutter button
    SHUTTER = True
    try:
        import evdev
        from evdev import ecodes
        import select

        # to view events:  python -m evdev.evtest
        # <Event(1026-MouseButtonUp {'pos': (133, 29), 'button': 1, 'touch': False, 'window': None})>
        # <Event(768-KeyDown {'unicode': 't', 'key': 116, 'mod': 4096, 'scancode': 23, 'window': None})>
        
        themeEvent = pygame.event.Event(KEYDOWN, key=K_t)
        streamEvent = pygame.event.Event(KEYDOWN, key=K_s)
        captureEvent = pygame.event.Event(KEYDOWN, key=K_i)
        #captureEvent = pygame.event.Event(MOUSEBUTTONUP, button=1, pos=menuCapture.center)

        shutter = evdev.InputDevice('/dev/input/shutter')
        shutter.grab

    except Exception as err:
        print(f"Shutter Button not available: {err}")
        SHUTTER = False

    #----------------------------------
    # flags
    menuDisplay = False 
    mode = 1
    imageCapture = False
    streamCapture = False

    mlx.setTheme(theme)

    frameStart = time.time()
    #----------------------------------
    # loop...
    running = True
    while(running):

            #print(f"frame ms: {int((time.time() - frameStart) * 1000)} FPS: {int(1/(time.time() - frameStart))}")
            frameStart = time.time()

            #----------------------------------
            # scan shutter button
            if SHUTTER :
                try :
                    Event, nonEvent, nonEvent = select.select([shutter],[], [], 0 )
                    if Event :
                        for e in shutter.read():
                            if e.type == ecodes.EV_KEY and e.value == 1:
                                if e.code == ecodes.ecodes['KEY_VOLUMEDOWN'] :
                                    pygame.event.post(streamEvent)
                                if e.code == ecodes.ecodes['KEY_VOLUMEUP'] :
                                    pygame.event.post(captureEvent)

                except OSError as err:
                    print(f"Shutter Button Unavailable:{err}")
                    SHUTTER = False

            #----------------------------------
            # scan events
            for event in pygame.event.get():
                    if (event.type == MOUSEBUTTONUP):
                        pos = event.pos
                        if event.button == 2:
                            mlx.setSpots(1,pos)
                        if event.button == 3:
                            mlx.setSpots(0,pos)
                            
                        if menuDisplay and event.button == 1 :
                                if menuMaxPlus.collidepoint(pos):
                                    mlx.incrMINMAX((0,1))
                                if menuMaxMinus.collidepoint(pos):
                                    mlx.incrMINMAX((0,-1))
                                if menuMinPlus.collidepoint(pos):
                                    mlx.incrMINMAX((1,0))
                                if menuMinMinus.collidepoint(pos):
                                    mlx.incrMINMAX((-1,0))
                                    
                                if menuBack.collidepoint(pos):
                                        lcd.fill((0,0,0))
                                        menuDisplay = False
                                if menuExit.collidepoint(pos):
                                        running = False

                                if menuMode.collidepoint(pos):
                                        lcd.fill((0,0,0))
                                        mode = (mode + 1) % 4
                                        
                                if menuCapture.collidepoint(pos):
                                        imageCapture = not imageCapture

                                if menuAvg.collidepoint(pos):
                                    mlx.MAXTEMP = mlx.AVGtemp + (2 / 1.8)
                                    mlx.MINTEMP = mlx.AVGtemp - (2 / 1.8)

                        elif not menuDisplay and event.button == 1 :
                                menuDisplay = True

                    if (event.type == KEYDOWN) :
                            if (event.key == K_ESCAPE) :
                                    running = False

                            if (event.key == K_RIGHT) :
                                    cam.camOffsetX += 1
                            if (event.key == K_LEFT) :
                                    cam.camOffsetX -= 1

                            if (event.key == K_DOWN) :
                                    cam.camOffsetY += 1
                            if (event.key == K_UP) :
                                    cam.camOffsetY -= 1

                            if event.key == K_KP_PLUS :
                                cam.setCameraFOV(cam.camFOV+1)
                            if event.key == K_KP_MINUS :
                                camFOV -= 1
                                cam.setCameraFOV(cam.camFOV-1)

                            if event.key == K_PAGEUP :
                                mlx.refresh_rate = mlx.refresh_rate + 1
                                print(f"Refresh Rate: { 2 ** (mlx.refresh_rate-1) }")
                            if event.key == K_PAGEDOWN :
                                mlx.refresh_rate = mlx.refresh_rate - 1
                                print(f"Refresh Rate: { 2 ** (mlx.refresh_rate-1) }")

                            if event.key == K_p :
                                mlx.AVGprint = not mlx.AVGprint

                            if event.key == K_t :
                                mlx.setTheme(mlx.theme + 1)
                                
                            if event.key == K_s :
                                streamCapture = not streamCapture

                            if event.key == K_i :
                                imageCapture = not imageCapture
                                                                
                            if (event.key == K_w) :
                                    # write config
                                    config.set('ThermalCamera', 'offsetX',str(cam.camOffsetX))
                                    config.set('ThermalCamera', 'offsetY',str(cam.camOffsetY))
                                    config.set('ThermalCamera', 'camFOV',str(cam.camFOV))
                                    with open('config.ini', 'w') as f:
                                            config.write(f)

            #----------------------------------
            # get heat layer
            mlx.getImage(lcd, mode)

            #----------------------------------
            # add image layer
            cam.getImage(lcd, mode)

            #----------------------------------
            # add spots overlay
            mlx.getSpots(lcd)

            #----------------------------------
            # capture single frame to file, without menu overlay
            if imageCapture :
                    imageCapture = False
                    fileName = "%s/heat%s.jpg" % (os.path.expanduser('~/Pictures'), time.strftime("%Y%m%d-%H%M%S",time.localtime()) )
                    pygame.image.save(lcd, fileName)
                    print(f"Image saved to: {fileName}")

            #----------------------------------
            # remote stream capture
            # capture continues until stopped
            if streamCapture :
                if fileNum == 0 :
                    streamStart = time.time()
                    # store in subdirectory of working directory
                    streamDir = time.strftime("%Y%m%d-%H%M%S", time.localtime())
                    os.mkdir(streamDir)

                #fileName = "%s/heat%s-%04d.jpg" % (os.path.expanduser('~/Pictures'), fileDate, fileNum)
                fileName = f"{streamDir}/{fileNum:04d}.jpg"
                fileNum = fileNum + 1
                pygame.image.save(lcd, fileName)

            elif fileNum != 0 :
                fps = fileNum / (time.time() - streamStart)
                print(f"frames captured: {fileNum}, FPS: {fps:.1f}")
                Path(f"{streamDir}/FPS").write_text(f"{fps:.1f}")
                fileNum = 0

            #----------------------------------
            # add menu overlay
            if menuDisplay :
                    # display max/min
                    lcd.blit(MAXtext,MAXtextPos)
                    fahrenheit = mlx.MAXTEMP*1.8 + 32
                    MAXnum = font.render('%d'%fahrenheit, True, WHITE)
                    textPos = MAXnum.get_rect(center=MAXnumPos.center)
                    lcd.blit(MAXnum,textPos)

                    lcd.blit(MINtext,MINtextPos)
                    fahrenheit = mlx.MINTEMP*1.8 + 32
                    MINnum = font.render('%d'%fahrenheit, True, WHITE)
                    textPos = MINnum.get_rect(center=MINnumPos.center)
                    lcd.blit(MINnum,textPos)

                    AVGf = AVGtemp*1.8 + 32
                    AVGnum = font.render('%d'%AVGf, True, WHITE)
                    textPos = AVGnum.get_rect(center=AVGnumPos.center)
                    lcd.blit(AVGnum, textPos)

                    lcd.blit(menu,(0,0))

            #----------------------------------
            # display
            pygame.display.update()


    cam.stop()
    pygame.quit()
     
#------------------------------------------------
#------------------------------------------------
if __name__ == '__main__':
    main()
