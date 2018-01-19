#!

# exit on error
set -e

echo ' '
echo Install Desktop Icons...
projDir=$(dirname $(dirname $(readlink -f $0)))
userDir=$(eval echo ~$SUDO_USER)
cp $projDir/Desktop/*.desktop $userDir/Desktop

echo ' '
echo Install packages...

echo ...update package lists
apt-get -qq update

echo ...build-essential, git
apt-get -qq install -y build-essential git

echo ...python packages
apt-get -qq install -y python-pip python-dev python-smbus python-scipy python-pygame

echo ' '
echo Install AMG88xx...
echo ...AMG88xx python module
pip install -q colour Adafruit_AMG88xx

echo ' '
echo Install GPIO...
echo ...GPIO python module
git clone -q https://github.com/adafruit/Adafruit_Python_GPIO.git
cd Adafruit_Python_GPIO
cat <<! >setup.cfg
[global]
verbose=0
!
python setup.py install
cd ..
rm -rf Adafruit_Python_GPIO

echo ' '
echo Install SDL1.2...

echo ...force version
#enable wheezy package sources

echo "deb http://archive.raspbian.org/raspbian wheezy main
" > /etc/apt/sources.list.d/wheezy.list

release=$(lsb_release -cs)
#set stable as default package source (currently jessie)
echo "APT::Default-release \"$release\";
" > /etc/apt/apt.conf.d/10defaultRelease

#set the priority for libsdl from wheezy higher then the jessie package
echo "Package: libsdl1.2debian
Pin: release n=$release
Pin-Priority: -10
Package: libsdl1.2debian
Pin: release n=wheezy
Pin-Priority: 900
" > /etc/apt/preferences.d/libsdl

#install
echo ...update package lists
apt-get -qq update

echo ...install libSDL
apt-get -qq -y --force-yes install libsdl1.2debian/wheezy

echo ' '
echo Install complete
