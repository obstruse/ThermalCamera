# ThermalCamera
![](/Images/heat20220617-185005.gif)

MLX90640 Thermal Camera with Edge Detect Video Overlay.

### Updates:

- Enhanced MLX90640 driver with no wait states.

- Eliminated the 'Too many retries' error:  Refresh Rate no long dependant on I2C Transfer Speed.

- MLX90640 can either be connected to the I2C pins on a Raspberry Pi, or connected via the HDMI DDC pins on any computer running Linux.

- Bluetooth shutter release used to trigger image/stream capture to file.

The MLX90640 can be set for 64Hz refresh rate (32 fps), but you probably don't want to -- at the higher refresh rates the output is mostly thermal noise:


![](/Images/noiseCompare.png)



## Hardware
- Raspberry Pi
- [Adafruit MLX90640 IR Thermal Camera Breakout](https://www.adafruit.com/product/4407)
- USB Camera (see below)



### Cameras

The cameras need to be mounted flat and as close together as possible:

![](Images/PXL_20250911_021926412a.jpg)

The USB camera pictured is 
["Bare USB Webcam" from Public Lab](https://publiclab.myshopify.com/collections/bits-bobs/products/webcam-dsk-3-0) which unfortunately is no longer available. 

These will probably work, but with a different FOV:

- [Ultra Tiny USB Webcam Camera with GC0307 Sensor](https://www.adafruit.com/product/5733) (it's only $7)
- [Arducam OV5648](https://www.arducam.com/product/arducam-ov5648-auto-focus-usb-camera-ub0238-6/)

- [Newcamermoudle 5MP CMOS Sensor](https://newcameramodule.com/product/small-size-5mp-cmos-sensor-usb-2-0-camera-module/)

By default the camera device is `/dev/video0`.  To change it, edit `videoDev` in `config.ini`:

```
videoDev = /dev/video0
```
---

Camera Resolution|
-|



![](Images/framing.jpg)

 


## Setup

![](Images/heat20220618-112607.gif)
### Installation

The installation script installs:
- pygame
- colour
- MLX90640

```
git clone https://github.com/obstruse/ThermalCamera.git
sudo ThermalCamera/install/installThermalCamera.sh
```
I2C via GPIO|
-|


Connect the SDA/SCL pins to the MLX90640. To increase the speed of data transfers, set the I2C baudrate to 1 MHz by editing `/boot/config.txt`. Modify the **dtparam=i2c_arm=on** line to read:

```
dtparam=i2c_arm=on,i2c_arm_baudrate=1000000
```
...and reboot.

I2C via HDMI|
-|


![https://www.adafruit.com/product/4984](Images/HDMIadapter.jpg)

[Adafruit DVI Breakout Board](https://www.adafruit.com/product/4984)

The '5 - D - C' pins along the bottom are the 5V, SDA, and SCL of the I2C interface.  Connect them to the corresponding pins on the MLX90640.  Use an HDMI cable to connect from the breakout board to the computer.

To find the I2C bus used by the device, run the `findMLX.sh` script in the `install/` directory.  Enter the bus number in the `config.ini` file (see below)

### Configuration

Program settings can be changed by modifying `config.ini` located in the same directory as `heat.py`

&nbsp;|Configuration Settings|&nbsp;
-|-|-
**Key**|**Description**|**Default**
camOffsetX | camera X offset | 0
camOffsetY | camera Y offset | 0
width | display width | 320
height | display height | 240
camWidth | camera width | 320
camHdight | camera height | 240
videoDev | video device | /dev/video0
camFOV | camera FOV | 35
heatFOV | heat FOV | 40
theme | color mapping theme | 1 (0-3 available)
SMB | SMBus to use | -1
---



## Execution

Run the program from the command line:
```
ThermalCamera/python/heat.py
```

You can run the program remotely from an SSH connection, with the heat displayed in an X-window.  Commands are typed in the console window.

![Menu](Images/heat20220622-132440.jpg)

Keyboard Commands|&nbsp;
-|-
up/down/left/right | Change Camera Offset
-/= | Decrement/Increment Camera FOV
PageUP/PageDown | Decrement/Increment Refresh Rate
c | Clear spot temperature tracking
p | Display spot temperatures
v | Track maximum temperature spot
b | Track minimum temperature spot
t | Step through Colormap Themes
e | Change color for edge display
m | Step through Display Modes
s | Stream Capture
i | Image Capture
w | Write settings to `config.ini`
f | Save Spot readings to file
1/3 | Decrement/Increment Low Temperature threshold
2 | Automatic Low Temperature set
7/9 | Decrement/Increment Hight Temperature threshold
8 | Automatic High Temperature set
F1/F2/F3/F4 | Presets

Bluetooth Commands| &nbsp;
-|-
VolumnDown | Start/Stop stream capture
VolumeUp | Capture image

Mouse Commands| &nbsp;
-|-
Buttons 1-3 | Spot temperature at mouse location


Display Modes|
-|
- camera only
- heat + edge detect overlay
- heat + camera overlay
- heat only


File Capture|
-|

Files are stored in the `capture` subdirectory:  temperature readings in `capture/average`, still images in `capture/images`, and image streams in a timestamped directory under `capture`.

The captured images in `capture/[timestamp]` can be combined into an MP4 using ffmpeg, for example:
```
#!/bin/bash

DIR=$1
FPS=$(cat ${DIR}/FPS)
ffmpeg -loglevel error -framerate ${FPS} -pattern_type glob -i ${DIR}/\*.jpg ${DIR}.mp4
echo "created: ${DIR}.mp4"
```
---

## Alignment


### Field Of View (FOV)

The script needs the FOV of both cameras in order to scale the images properly.  The camera data sheet might have a value for FOV, but it's often missing or incorrect.  You can try measuring the FOV, but it will mostly likely still require fine adjustments to get everything lined-up properly.  

Simplest method is to leave the default values in the config.ini file and use the '-' and '=' keys to increment/decrement the camera FOV until the two images are the same size.  The actual values aren't important, just the ratio of the two. Press 'w' to save the FOV in the `config.ini` file.

### Offset

If you carefully mounted the two cameras, the two images should line up fairly well... but then there's the parallax caused by the distance between them.  

To correct for mounting errors and parallax, use the keyboard arrow keys to offset the images until they line up.  Press 'w' to save the offsets in the `config.ini` file

---
---

![Camera](Images/IMG_0791-3.JPG)

Thermal Camera with LCD Touchscreen

![Hot Watermelon](Images/heat20220616-094600.gif)
![PiZero](Images/heat20220613-2059.gif)

![EICO 460](Images/heat20220621-1835302.gif)

EICO 460 Oscilloscope chassis hot spots