#!

# exit on error
set -e

echo ' '
echo Install packages...

echo ...update package lists
apt -qq update

echo ...pygame
apt -qq install -y python-pygame

echo ...MLX90640 python module
pip install -q adafruit-circuitpython-mlx90640

echo ...colour python module
pip install -q colour

echo ...numpy python module
pip install -q numpy

echo ...GPIO python module
# (Raspberry Pi 4 requires gpio v2.52
wget -q https://project-downloads.drogon.net/wiringpi-latest.deb
dpkg -i wiringpi-latest.deb 
rm -rf wiringpi-latest.deb

echo ' '
echo Install complete
