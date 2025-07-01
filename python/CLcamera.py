import pygame.camera
import math
import numpy as np

class camera:
    def __init__(self, videoDev, camSize, displaySize, offset=(0,0), camFOV=45, heatFOV=45):
        (self.width, self.height) = displaySize
        (self.camOffsetX, self.camOffsetY) = offset
        self.heatFOV = heatFOV
        self.camFOV = camFOV

        # initialize camera
        pygame.camera.init()
        self.cam = pygame.camera.Camera(videoDev,camSize)  # actual camera resolution may be different
        self.cam.start()
        (self.camWidth,self.camHeight) = self.cam.get_size()
        self.setCameraFOV(camFOV)
        
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
            #pygame.transform.threshold(self.overlay,camImage,(0,0,0),(40,40,40),(1,1,1),1)
            pygame.transform.threshold(self.overlay,camImage,(0,0,0),(64,64,64),(255,255,255),1)
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
