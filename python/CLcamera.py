#import pygame.camera
import pygame
import math
import numpy as np
import sys

CV2 = False
class camera:

    readCount = 0
    ready = False
    edge = 0        # index for edge detect color

    def __init__(self, videoDev, camSize, displaySize, offset=(0,0), camFOV=45, heatFOV=45):
        (self.width, self.height) = displaySize
        (self.camOffsetX, self.camOffsetY) = offset
        self.heatFOV = heatFOV
        self.camFOV = camFOV

        # initialize camera
        try:
            if CV2:
                import cv2
                self.cam = cv2.VideoCapture(0,cv2.CAP_V4L2)             # device number...
                self.cam.set(cv2.CAP_PROP_FRAME_WIDTH, camSize[0])
                self.cam.set(cv2.CAP_PROP_FRAME_HEIGHT, camSize[1])
                self.camWidth = self.cam.get(cv2.CAP_PROP_FRAME_WIDTH)
                self.camHeight = self.cam.get(cv2.CAP_PROP_FRAME_HEIGHT)    # are they different? need int?
                print(f"Cam width/height: {self.camWidth},{self.camHeight}")
                self.cam.set(cv2.CAP_PROP_FPS,30)                       # try for 30 FPS
                print(f"Cam FPS: {self.cam.get(cv2.CAP_PROP_FPS)}")     # did it work?

            else:
                import pygame.camera
                pygame.camera.init()
                self.cam = pygame.camera.Camera(videoDev,camSize)  # actual camera resolution may be different
                self.cam.start()
                (self.camWidth,self.camHeight) = self.cam.get_size()

        except Exception as e:
            print(f"Unable to initialize camera: {e}")
            sys.exit()
            
        self.setCameraFOV(camFOV)
        self.setEdgeColor(self.edge)
            
    #----------------------------------
    def setCameraFOV(self,camFOV) :
        self.camFOV = camFOV
        # Field of View and Scale
        self.imageScale = math.tan(math.radians(camFOV/2.))/math.tan(math.radians(self.heatFOV/2.))
        print(f"camFOV: {camFOV}")

        # camera edge detect overlay surface
        # scaled to match display size and preserve aspect ratio
        self.overlay = pygame.surface.Surface((int(self.width*self.imageScale), int(self.width*(self.camHeight/self.camWidth)*self.imageScale)))
        self.overlay.set_colorkey((0,0,0))

    def getCameraScaled(self,scale=None):
        if scale == None:
            scale = self.imageScale
        # block until read
        self.readCount += 1
        self.ready = True

        if CV2:
            if self.cam.grab() :
                ret, array = self.cam.retrieve()
            else:
                print("Not Ready")
            #ret, array = self.cam.read()
            array = cv2.resize( array, (int(self.width*scale), int(self.width*(self.camHeight/self.camWidth)*scale)) )
            array = cv2.cvtColor(array, cv2.COLOR_BGR2RGB)
            return pygame.image.frombuffer(array.tobytes(), array.shape[1::-1], 'RGB')
        else:
            return pygame.transform.scale(self.cam.get_image(),(int(self.width*scale), int(self.width*(self.camHeight/self.camWidth)*scale)))

    def incrOffset(self, incr) :
        self.camOffsetX, self.camOffsetY = np.add( (self.camOffsetX, self.camOffsetY), incr)

    #----------------------------------
    # Mode == 0      normal camera
    # Mode == 1      edge
    # Mode == 2      alpha
    # Mode == 3      transparent
    #----------------------------------

    def getImage(self, lcd, mode=0) :
        lcdRect = lcd.get_rect()
        self.ready = False
        if mode == 0:
            # camera base layer
            camImage = self.getCameraScaled()
            camRect = camImage.get_rect(center=lcdRect.center)
            pygame.Rect.move_ip(camRect,-self.camOffsetX,-self.camOffsetY)
            lcd.blit(camImage, camRect)

        if mode == 1:
            # edge detect camera overlay
            camImage = pygame.transform.laplacian(self.getCameraScaled())
            self.overlay.fill((0,0,0))
            pygame.transform.threshold(self.overlay,camImage,(0,0,0),(40,40,40),self.edgeColor,1)
            # offset camera to match heat image
            overlayRect = self.overlay.get_rect(center=lcdRect.center)
            pygame.Rect.move_ip(overlayRect,-self.camOffsetX,-self.camOffsetY)
            self.overlay.set_colorkey((0,0,0))
            lcd.blit(self.overlay,overlayRect)
        
        if mode == 2 :
            # alpha camera overlay
            camImage = self.getCameraScaled()
            camRect = camImage.get_rect(center=lcdRect.center)
            pygame.Rect.move_ip(camRect,-self.camOffsetX,-self.camOffsetY)
            camImage.set_alpha(100)
            lcd.blit(camImage,camRect)

        if mode == 3:
            pass

    def setEdgeColor(self,edge) :
        E = [(1,1,1),(128,128,128),(255,255,255)]
        self.edge = edge % len(E)
        self.edgeColor = E[self.edge]

    def stop(self) :
        if CV2:
            self.cam.release()
        else:
            self.cam.stop()

