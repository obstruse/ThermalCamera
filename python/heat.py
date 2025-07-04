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

    # --------------- menu buttons and text ---------------

    # keyboard stuff
    K = {
        K_q:    {"handler":lambda: flags.incr(running=1), "desc":"Quit program"},
        27:     {"handler":lambda: flags.incr(running=1), "desc":"Quit program"},
        
        K_RIGHT:{"handler":lambda: cam.incrOffset((1,0)), "desc":"Offset Heat: Right"},
        K_LEFT: {"handler":lambda: cam.incrOffset((-1,0)), "desc":"Offset Heat: Left"},
        K_UP:   {"handler":lambda: cam.incrOffset((0,-1)), "desc":"Offset Heat: Up"},
        K_DOWN: {"handler":lambda: cam.incrOffset((0,1)), "desc":"Offset Heat: Down"},

        K_EQUALS: {"handler":lambda: cam.setCameraFOV(cam.camFOV+1), "desc":"Camera FOV: Increment"},
        K_MINUS: {"handler":lambda: cam.setCameraFOV(cam.camFOV-1), "desc":"Camera FOV: Decrement"},

        K_PAGEUP: {"handler":lambda: mlx.incrRefreshRate(1), "desc":"Refresh Rate: Increment"},
        K_PAGEDOWN: {"handler":lambda: mlx.incrRefreshRate(-1), "desc":"Refresh Rate: Decrement"},

        K_v:    {"handler":lambda: mlx.setMINMAXspots(), "desc":"Display MIN/MAX values"},
        K_c:    {"handler":lambda: mlx.clearSpots(), "desc":"Spot Clear"},
        K_t:    {"handler":lambda: mlx.setTheme(mlx.theme + 1), "desc":"Step through Colormap Themes"},
        K_e:    {"handler":lambda: print(0),"desc":"Change Edge Color"},
        K_m:    {"handler":lambda: flags.incr(mode=1), "desc":"Step through Display Modes"},
        
        K_s:    {"handler":lambda: flags.incr(streamCapture=True),"desc":"Stream Capture"},
        K_i:    {"handler":lambda: flags.incr(imageCapture=True),"desc":"Image Capture"},
        K_w:    {"handler":lambda: print(0),"desc":"Write config.ini"},
        K_f:    {"handler":lambda: print(0),"desc":"Save Spot readings to file"},

        K_1:    {"handler":lambda: mlx.incrLoTemp(-1), "desc":"Lo temp Decrement"},
        K_KP1:  {"handler":lambda: mlx.incrLoTemp(-1), "desc":"Lo temp Decrement"},
        K_2:    {"handler":lambda: mlx.incrLoTemp(0), "desc":"Lo Temp Automatic"},
        K_KP2:  {"handler":lambda: mlx.incrLoTemp(0), "desc":"Lo Temp Automatic"},
        K_3:    {"handler":lambda: mlx.incrLoTemp(1), "desc":"Lo Temp Increment"},
        K_KP3:  {"handler":lambda: mlx.incrLoTemp(1), "desc":"Lo Temp Increment"},

        K_7:    {"handler":lambda: mlx.incrHiTemp(-1), "desc":"Hi Temp Decrement"},
        K_KP7:  {"handler":lambda: mlx.incrHiTemp(-1), "desc":"Hi Temp Decrement"},
        K_8:    {"handler":lambda: mlx.incrHiTemp(0), "desc":"Hi Temp Automatic"},
        K_KP8:  {"handler":lambda: mlx.incrHiTemp(0), "desc":"Hi Temp Automatic"},
        K_9:    {"handler":lambda: mlx.incrHiTemp(1), "desc":"Hi Temp Increment"},
        K_KP9:  {"handler":lambda: mlx.incrHiTemp(1), "desc":"Hi Temp Increment"},

        0:      {"handler":lambda: noKey()}
#        K_ :    {"handler":lambda: , "desc":""},
    }

    # Might be nice to display a help screen, grouped by function?

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

    mlx.setTheme(theme)

    frameStart = time.time()
    #----------------------------------
    # loop...
    while(flags.running):

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
                if (event.type == MOUSEBUTTONDOWN):
                    if event.button <= 3 :
                        pos = event.pos
                        mlx.setSpots(event.button,pos)

                if event.type == KEYDOWN:
                    key = K.get(event.key,K[0])
                    key['handler']()

                '''    

                    if (event.type == KEYDOWN) :
                        if (event.key == K_ESCAPE) :
                            K[event.key]['handler']()

                        if (event.key == K_RIGHT) :
                            cam.incrOffset((1,0))
                        if (event.key == K_LEFT) :
                            cam.incrOffset((-1,0))

                        if (event.key == K_DOWN) :
                            cam.incrOffset((0,1))
                        if (event.key == K_UP) :
                            cam.incrOffset((0,-1))

                        if event.key == K_KP_PLUS :
                            cam.setCameraFOV(cam.camFOV+1)
                        if event.key == K_KP_MINUS :
                            cam.setCameraFOV(cam.camFOV-1)

                        if event.key == K_PAGEUP :
                            mlx.incrRefreshRate(1)
                        if event.key == K_PAGEDOWN :
                            mlx.incrRefreshRate(-1)

                        if event.key == K_p :
                            mlx.toggleAVGprint()

                        if event.key == K_t :
                            mlx.setTheme(mlx.theme + 1)
                            
                        if event.key == K_s :
                            K[event.key]['handler']()

                        if event.key == K_i :
                            K[event.key]['handler']()
                        
                        if event.key == K_m:
                            K[event.key]['handler']()
                                                            
                        if (event.key == K_w) :
                            # write config
                            config.set('ThermalCamera', 'offsetX',str(cam.camOffsetX))
                            config.set('ThermalCamera', 'offsetY',str(cam.camOffsetY))
                            config.set('ThermalCamera', 'camFOV',str(cam.camFOV))
                            with open('config.ini', 'w') as f:
                                config.write(f)
                '''
                
            #----------------------------------
            # get heat layer
            mlx.getImage(lcd, flags.mode)

            #----------------------------------
            # add image layer
            cam.getImage(lcd, flags.mode)

            #----------------------------------
            # add spots overlay
            mlx.getSpots(lcd)

            #----------------------------------
            # capture single frame to file, without menu overlay
            if flags.imageCapture :
                flags.imageCapture = False
                flags.streamCapture = False
                fileName = "%s/heat%s.jpg" % (os.path.expanduser('~/Pictures'), time.strftime("%Y%m%d-%H%M%S",time.localtime()) )
                pygame.image.save(lcd, fileName)
                print(f"Image saved to: {fileName}")

            #----------------------------------
            # remote stream capture
            # capture continues until stopped
            if flags.streamCapture :
                if fileNum == 0 :
                    streamStart = time.time()
                    # store in subdirectory of working directory
                    streamDir = time.strftime("%Y%m%d-%H%M%S", time.localtime())
                    os.mkdir(streamDir)
                    print("Capturing stream...")

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
            # display
            pygame.display.update()


    cam.stop()
    pygame.quit()

#------------------------------------------------
class flags:  
    mode = 1
    imageCapture = False
    streamCapture = False
    running = True

    def incr(mode=0, imageCapture=False, streamCapture=False, running=False):
        flags.mode = (flags.mode + mode) % 4
        flags.imageCapture = flags.imageCapture != imageCapture
        flags.streamCapture = flags.streamCapture != streamCapture
        flags.running = flags.running != running
        
def noKey():
    print("Undefined key")

#------------------------------------------------
#------------------------------------------------
if __name__ == '__main__':
    main()
