#!/usr/bin/env python

import sys
import os
os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = "hide"
import MLX90640

import pygame
import pygame.camera
from pygame.locals import *

import math
import time
from pathlib import Path

import numpy as np
from colour import Color

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
    refresh = MLX90640.RefreshRate.REFRESH_4_HZ
    if SMB >= 0 :
        import i2cSMB as i2cSMB
        i2c = i2cSMB.i2cSMB(SMB)
    else:
        try:
            import RPi.GPIO as GPIO
            import board
            import busio
            i2c = busio.I2C(board.SCL, board.SDA)
        except Exception as e:
            print(f"No I2C bus found: {e}")
            sys.exit()

    mlx = MLX90640.MLX90640(i2c)
    #mlx = MLX90640.MLX90640m0(i2c)     # original driver

    mlx.refresh_rate = refresh
    print(f"{mlx.version}, refresh {2**(mlx.refresh_rate-1)} Hz")

    temps = [0] * 768
    AVGspots = 4
    AVGdepth = 8
    AVGindex = 0
    AVGfile = ""
    AVGfd = 0
    AVG = [{'spot': 0, 'xy': (0,0), 'print': 0, 'raw': [0]*AVGdepth} for _ in range(AVGspots)]

    # pre-define two spots
    #AVG[1]['spot'] = 399
    #AVG[0]['spot'] = 400

    
    #----------------------------------
    # initialize camera
    pygame.camera.init()
    cam = pygame.camera.Camera(videoDev,(camWidth, camHeight))  # actual camera resolution may be different
    cam.start()
    (camWidth,camHeight) = cam.get_size()
    #print(cam.get_size())

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
    # heat surface and sensor temperature index
    heat = pygame.surface.Surface((32,24))
    tIndex = np.array(list(range(0,(32*24)))).reshape((32,24),order='F')
    tIndex = np.flip(tIndex,0)

    tCenter = lcdRect.center
    tMag = width/32
    #heatRect = heatImage.get_rect(center=lcdRect.center)

    # camera edge detect overlay surface determined by setCamerFOV()

    #----------------------------------
    # menu surface
    menu = pygame.surface.Surface((width, height))
    menu.set_colorkey((0,0,0))

    #----------------------------------
    #utility functions
    def setCameraFOV(FOV) :
        global imageScale
        global overlay

        # Field of View and Scale
        imageScale = math.tan(math.radians(camFOV/2.))/math.tan(math.radians(heatFOV/2.))
        print(f"camFOV: {camFOV}")

        # camera edge detect overlay surface
        # scaled to match display size and preserve aspect ratio
        overlay = pygame.surface.Surface((int(width*imageScale), int(width*(camHeight/camWidth)*imageScale)))
        overlay.set_colorkey((0,0,0))

    def getCameraScaled(scale=None):
        if scale == None:
            scale = imageScale
        return pygame.transform.scale(cam.get_image(),(int(width*scale), int(width*(camHeight/camWidth)*scale)))

    def xyTsensor(xy):
        # temps[] index for (x,y) screen position
        #offset = np.subtract(xy, lcdRect.center)
        #xyA = np.add(offset,tCenter)
        xyT = np.divide(xy,(tMag,tMag))
        xT = int(xyT[0])
        yT = int(xyT[1])

        #print(f"xT,yT: {(xT,yT)}   x,y: {xy}")
        #print(f"    tSensor: {tIndex[xT][yT]}") 
        return tIndex[xT][yT]

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
    heatDisplay = 1
    imageCapture = False
    streamCapture = False
    AVGprint = False

    setCameraFOV(camFOV)
    map.setTheme(theme)

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
                            AVG[1]['spot'] = xyTsensor(pos)
                            AVG[1]['xy'] = pos
                            AVGprint = True
                        if event.button == 3:
                            AVG[0]['spot'] = xyTsensor(pos)
                            AVG[0]['xy'] = pos
                            AVGprint = True

                        if menuDisplay and event.button == 1 :
                                if menuMaxPlus.collidepoint(pos):
                                    incrMINMAX((0,1))
                                if menuMaxMinus.collidepoint(pos):
                                    incrMINMAX((0,-1))
                                if menuMinPlus.collidepoint(pos):
                                    incrMINMAX((1,0))
                                if menuMinMinus.collidepoint(pos):
                                    incrMINMAX((-1,0))
                                    
                                if menuBack.collidepoint(pos):
                                        lcd.fill((0,0,0))
                                        menuDisplay = False
                                if menuExit.collidepoint(pos):
                                        running = False

                                if menuMode.collidepoint(pos):
                                        lcd.fill((0,0,0))
                                        heatDisplay+=1
                                        if heatDisplay > 3 :
                                                heatDisplay = 0
                                if menuCapture.collidepoint(pos):
                                        imageCapture = not imageCapture

                                if menuAvg.collidepoint(pos):
                                    map.MAXTEMP = AVGtemp + (2 / 1.8)
                                    map.MINTEMP = AVGtemp - (2 / 1.8)

                        elif not menuDisplay and event.button == 1 :
                                menuDisplay = True

                    if (event.type == KEYDOWN) :
                            if (event.key == K_ESCAPE) :
                                    running = False

                            if (event.key == K_RIGHT) :
                                    camOffsetX += 1
                            if (event.key == K_LEFT) :
                                    camOffsetX -= 1

                            if (event.key == K_DOWN) :
                                    camOffsetY += 1
                            if (event.key == K_UP) :
                                    camOffsetY -= 1

                            if event.key == K_KP_PLUS :
                                camFOV += 1
                                setCameraFOV(camFOV)
                            if event.key == K_KP_MINUS :
                                camFOV -= 1
                                setCameraFOV(camFOV)

                            if event.key == K_PAGEUP :
                                mlx.refresh_rate = mlx.refresh_rate + 1
                                print(f"Refresh Rate: { 2 ** (mlx.refresh_rate-1) }")
                            if event.key == K_PAGEDOWN :
                                mlx.refresh_rate = mlx.refresh_rate - 1
                                print(f"Refresh Rate: { 2 ** (mlx.refresh_rate-1) }")

                            if event.key == K_p :
                                AVGprint = not AVGprint

                            if event.key == K_t :
                                map.setTheme(map.theme + 1)
                                
                            if event.key == K_s :
                                streamCapture = not streamCapture

                            if event.key == K_i :
                                imageCapture = not imageCapture
                                                                
                            if (event.key == K_w) :
                                    # write config
                                    config.set('ThermalCamera', 'offsetX',str(camOffsetX))
                                    config.set('ThermalCamera', 'offsetY',str(camOffsetY))
                                    config.set('ThermalCamera', 'camFOV',str(camFOV))
                                    with open('config.ini', 'w') as f:
                                            config.write(f)

            #----------------------------------
            # get heat data
        
            # pygame camera buffering causes camera image to lag beind heat image
            # this extra get_image helps.  
            # There will be another camera image available when heat has processed
            if (cam.query_image() ) :
                cam.get_image()

            try:
                subPage = mlx.getFrame(temps)
            except RuntimeError as err:
                print(f"\n\n{err}\n\nMake sure that I2C baudrate is set to 1MHz in /boot/config.txt:\ndtparam=i2c_arm=on,i2c_arm_baudrate=1000000\n\n")
                sys.exit(1)
            except ValueError:
                continue
            except OSError as err:
                print(f"{err}")
                continue

            #----------------------------------
            # heatDisplay == 0      camera only
            # heatDisplay == 1      heat + edge
            # heatDisplay == 2      heat + camera
            # heatDisplay == 3      heat only
            #----------------------------------

            #----------------------------------
            # base layer
            if heatDisplay :
                # heat base layer
                # map temperatures and create pixels
                pixels = np.array([map.map_pixel(p, MINTEMP, MAXTEMP, 0, map.COLORDEPTH - 1) for p in temps]).reshape((32,24,3), order='F')
                AVGtemp = sum(temps) / len(temps)
                map.MAXTEMP = max(temps)
                #MINTEMP = min(temps)

                # create heat surface from pixels
                heat = pygame.surfarray.make_surface(np.flip(pixels,0))
                # scaled to display, no offset
                heatImage = pygame.transform.smoothscale(heat, (width,int(width*24/32)))
                lcd.blit(heatImage,(0,0))
            else:
                # camera base layer
                camImage = getCameraScaled()
                camRect = camImage.get_rect(center=lcdRect.center)
                pygame.Rect.move_ip(camRect,-camOffsetX,-camOffsetY)
                lcd.blit(camImage,camRect)

            #----------------------------------
            # edge detect camera overlay
            if heatDisplay == 1 :
                camImage = pygame.transform.laplacian(getCameraScaled())
                overlay.fill((0,0,0))
                #pygame.transform.threshold(overlay,camImage,(0,0,0),(40,40,40),(1,1,1),1)
                pygame.transform.threshold(overlay,camImage,(0,0,0),(40,40,40),(255,255,255),1)
                # offset camera to match heat image
                overlayRect = overlay.get_rect(center=lcdRect.center)
                pygame.Rect.move_ip(overlayRect,-camOffsetX,-camOffsetY)
                overlay.set_colorkey((0,0,0))
                lcd.blit(overlay,overlayRect)

            #----------------------------------
            # alpha camera overlay
            if heatDisplay == 2 :
                camImage = getCameraScaled()
                camRect = camImage.get_rect(center=lcdRect.center)
                pygame.Rect.move_ip(camRect,-camOffsetX,-camOffsetY)
                camImage.set_alpha(100)
                lcd.blit(camImage,camRect)

            #----------------------------------
            # spot temps overlay
            if AVGprint:
                AVGindex = (AVGindex + 1) % AVGdepth
                for A in AVG:
                    if A['spot']:
                        A['raw'][AVGindex] = temps[A['spot']]
                        #A['print'] = C2F(sum(A['raw'])/AVGdepth)
                        A['print'] = C2F(A['raw'][AVGindex])
                        if A['xy'] != (0,0) :
                            shadow = np.subtract(A['xy'],1)
                            pygame.draw.circle(lcd, (0,0,0)      , shadow, 1*tMag, 1)
                            pygame.draw.circle(lcd, (255,255,255), A['xy'], 1*tMag, 1)
                            Asurf = font.render(f"  {C2F(temps[A['spot']]):.2f}",True,BLACK)
                            lcd.blit(Asurf,shadow)
                            Asurf = font.render(f"  {C2F(temps[A['spot']]):.2f}",True,WHITE)
                            lcd.blit(Asurf,A['xy'])

            # at some point there will be file output as well
            #if AVGprint :
            #    if AVGfile == "" :
            #        AVGfile = time.strftime("AVG-%Y%m%d-%H%M%S.dat", time.localtime())
            #        AVGfd = open(AVGfile, "a")
            #        refresh = 2 ** (mlx.refresh_rate-1)
            #        print(f"{mlx.version}, Refresh Rate: {2**(mlx.refresh_rate-1)}Hz", file=AVGfd)

            #    print(*[A['print'] for A in AVG],subPage)
            #    print(*[A['print'] for A in AVG],subPage, file=AVGfd)
            #elif AVGfile != "" :
            #    AVGfd.close()
            #    AVGfile = ""

            #----------------------------------
            # capture single frame to file, without menu overlay
            if imageCapture :
                    imageCapture = False
                    fileName = "%s/heat%s.jpg" % (os.path.expanduser('~/Pictures'), time.strftime("%Y%m%d-%H%M%S",time.localtime()) )
                    pygame.image.save(lcd, fileName)
                    print(f"Image saved to: {fileName}")

            #----------------------------------
            # remote stream capture
            # similar to imageCapture, but invoked by GPIO
            # capture continues until stopped
            #print(f"TCmap {TCmap[0]} - {TCmap[0]:x}")
            #if TCmap[0] == ord('1') :
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


            # from a shell window: start capture:  gpio -g write 5 1
            #                       stop capture:  gpio -g write 5 0
            # (Raspberry Pi 4 requires gpio v2.52
            #     wget https://project-downloads.drogon.net/wiringpi-latest.deb
            #     sudo dpkg -i wiringpi-latest.deb )
            #if GPIO.input(streamCapture) :
            #        if fileDate == "" :
            #                fileDate = time.strftime("%Y%m%d-%H%M%S", time.localtime())
            #                fileNum = 0

            #        fileName = "%s/heat%s-%04d.jpg" % (os.path.expanduser('~/Pictures'), fileDate, fileNum)
            #        fileNum = fileNum + 1
            #        pygame.image.save(lcd, fileName)

            #if not GPIO.input(streamCapture) and fileDate != "" :
            #        fileDate = ""
            #        print("frames captured:",fileNum)

            #----------------------------------
            # add menu overlay
            if menuDisplay :
                    # display max/min
                    lcd.blit(MAXtext,MAXtextPos)
                    fahrenheit = MAXTEMP*1.8 + 32
                    MAXnum = font.render('%d'%fahrenheit, True, WHITE)
                    textPos = MAXnum.get_rect(center=MAXnumPos.center)
                    lcd.blit(MAXnum,textPos)

                    lcd.blit(MINtext,MINtextPos)
                    fahrenheit = MINTEMP*1.8 + 32
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
    #GPIO.cleanup()

#------------------------------------------------
#------------------------------------------------
# things only used for color mapping (class candidates)
#------------------------------------------------
class map :
    MINTEMP = (68 - 32) / 1.8
    MAXTEMP = (100 - 32) / 1.8
    theme = 0

    COLORDEPTH = 1024
    colormap = []
    
    #----------------------------------
    def setTheme( value ) :
        cmaps = [map.map1, map.map2, map.map3, map.map4]
        map.theme = value % len(cmaps)
        cmaps[map.theme]()

         
    def incrMINMAX( incr ) :
        map.MINTEMP,map.MAXTEMP = np.add( (MINTEMP,MAXTEMP), incr )
        map.MINTEMP,map.MAXTEMP = np.clip( (MINTEMP,MAXTEMP), 0, 80)
        if MINTEMP > MAXTEMP:
            map.MINTEMP = MAXTEMP
        if MAXTEMP < MINTEMP:
            map.MAXTEMP = MINTEMP

    #----------------------------------
    # utility
    def constrain(val, min_val, max_val):
            return min(max_val, max(min_val, val))

    def map_pixel(x, in_min, in_max, out_min, out_max):
        cindex = (x - in_min) * (out_max - out_min) / (in_max - in_min) + out_min
        return map.colormap[map.constrain(int(cindex), 0, map.COLORDEPTH - 1) ]

    def gaussian(x, a, b, c, d=0):
        return a * math.exp(-((x - b) ** 2) / (2 * c**2)) + d

    def gradient(x, width, cmap, spread=1):
        width = float(width)
        r = sum(
            [map.gaussian(x, p[1][0], p[0] * width, width / (spread * len(cmap))) for p in cmap]
        )
        g = sum(
            [map.gaussian(x, p[1][1], p[0] * width, width / (spread * len(cmap))) for p in cmap]
        )
        b = sum(
            [map.gaussian(x, p[1][2], p[0] * width, width / (spread * len(cmap))) for p in cmap]
        )
        r = int(map.constrain(r * 255, 0, 255))
        g = int(map.constrain(g * 255, 0, 255))
        b = int(map.constrain(b * 255, 0, 255))
        return r, g, b
    
    def gradient2(value) :
        numColors = 5
        cl = (
            (0,0,1),
            (0,1,1),
            (0,1,0),
            (1,1,0),
            (1,0,0))

        x = value * (numColors - 1)
        lo = int(x//1)
        hi = int(lo + 1)
        dif = x - lo

        r = int( (cl[lo][0] + dif*(cl[hi][0] - cl[lo][0])) * 255)
        g = int( (cl[lo][1] + dif*(cl[hi][1] - cl[lo][1])) * 255)
        b = int( (cl[lo][2] + dif*(cl[hi][2] - cl[lo][2])) * 255)

        return r,g,b


    #----------------------------------
    # create different colormaps
    def map1() :
        # method 1
        # ... gradient
        heatmap = (
            (0.0, (0, 0, 0)),
            (0.20, (0, 0, 0.5)),
            (0.40, (0, 0.5, 0)),
            (0.60, (0.5, 0, 0)),
            (0.80, (0.75, 0.75, 0)),
            (0.90, (1.0, 0.75, 0)),
            (1.00, (1.0, 1.0, 1.0)),
        )
        map.colormap = [(map.gradient(i, map.COLORDEPTH, heatmap)) for i in range(map.COLORDEPTH)]

    def map2() :
        # method 2
        # ... range_to (color)
        blue = Color("indigo")
        red  = Color("red")
        #colors = list(blue.range_to(Color("yellow"), COLORDEPTH))
        colors = list(blue.range_to(Color("red"), map.COLORDEPTH))
        map.colormap = [(int(c.red * 255), int(c.green * 255), int(c.blue * 255)) for c in colors]

    def map3() :
        # method 3
        blue = Color("indigo")
        red  = Color("red")
        colors = list(blue.range_to(Color("orange"), map.COLORDEPTH))
        map.colormap = [(int(c.red * 255), int(c.green * 255), int(c.blue * 255)) for c in colors]

    def map4(value):
        # method 4
        # ... gradient2
        map.colormap = [(map.gradient2(c/map.COLORDEPTH)) for c in range(map.COLORDEPTH)]
     
#------------------------------------------------
#------------------------------------------------
if __name__ == '__main__':
    main()
