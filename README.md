# ThermalCamera
Thermal Camera with Video Overlay for Raspberry Pi

## Hardware
- Raspberry Pi 3 (https://www.adafruit.com/product/3055)
- Adafruit AMG8833 IR Thermal Camera Breakout (https://www.adafruit.com/product/3538)
- USB Camera
- Power supply, 5V 2.4A (https://www.adafruit.com/product/1995)

Optional:
- Adafruit PiTFT Plus 320x240 2.8" TFT + Capacitive Touchscreen (https://www.adafruit.com/product/2423)

### Wiring
The Thermal Camera connects using I2C:

![Wiring](/Images/wiring.png)

### Mounting
Mount the Thermal Camera next to the USB Camera:

![Mounting](Images/IMG_0788-3.JPG)
![Bare USB Camera](Images/IMG_0789-3.JPG)
![Camera](Images/IMG_0791-3.JPG)

https://publiclab.myshopify.com/collections/bits-bobs/products/webcam-dsk-3-0

## Software

```
git clone https://github.com/obstruse/ThermalCamera.git
sudo ThermalCamera/install/installThermalCamera.sh
```
## Touchscreen
