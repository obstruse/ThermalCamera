#!

# exit on error
set -e

echo ' '
echo Install packages...

echo ...update package lists
apt -qq update

echo ...pygame
apt -qq install -y python3-pygame

echo ...MLX90640 python module
pip install -q adafruit-circuitpython-mlx90640

echo ...colour python module
pip install -q colour

echo ...numpy python module
pip install -q numpy

echo ' '
echo Install complete
