#!/bin/bash

# control
getControl() {
    hex=($(i2ctransfer -y 1 w2@0x33 0x80 0x0d r2))
    hi=$(($((16#${hex[0]#0x})) << 8 ))
    lo=$((16#${hex[1]#0x}))
    echo $(( hi + lo ))
}
    
control() {
    ctrl=$(getControl)

    ADC=$(( (ctrl >> 10) & 0x03 ))
    RR=$(( (ctrl >> 7) & 0x07 ))
    HLD=$(( (ctrl >> 2) & 0x01 ))

    out=($(echo "obase=2;$ADC; $RR; $HLD" | bc ))
    printf "control: ADC: %s RR: %s HLD: %s\n" ${out[0]} ${out[1]} ${out[2]}
}

setRR() {
    control=$(getControl)
    #newControl=$((control & 0xfc7f ))
    newControl=$((control    & $(( 2#1111110001111111 )) ))
    newControl=$((newControl | $(( 2#0000000100000000 )) ))
    hi=$(( (newControl >> 8 ) & 0xff ))
    lo=$(( (newControl & 0xff ) ))

    i2ctransfer -y 1 w4@0x33 0x80 0x0d $hi $lo
}

# get RR
getRR() {
    RR=$(($(getControl) >> 7 & 0x07 ))
    echo "RR: " $(echo "obase=2;$RR" | bc)
}

# read status
status() {
    hex=($(i2ctransfer -y 1 w2@0x33 0x80 0x00 r2))
    hi=$(( $((16#${hex[0]#0x})) << 8 ))
    lo=$((    16#${hex[1]#0x}        ))
    stat=$(( hi + lo ))

    EO=$(( (stat >> 4) & 0x01 ))
    ND=$(( (stat >> 3) & 0x01 ))
    LM=$(( stat & 0x07 ))

    out=($(echo "obase=2;$EO; $ND; $LM" | bc))
    printf "status: overwrite: %s new data: %s last measured: %s\n"  ${out[0]} ${out[1]} ${out[2]}
}

# read temps
temps() {
    #i2ctransfer -y 1 w2@0x33 0x04 0x00 r16
    i2ctransfer -y 1 w2@0x33 0x07 0x00 r65
    # clear status after read
    i2ctransfer -y 1 w4@0x33 0x80 0x00 0x00 0x10
}

# frame metadata
# metadata is in words (16-bit)
getWord() {     #return word from RAM
    byte=$1
    hi=$(( $((RAM[$byte])) << 8 ))
    lo=$((    RAM[$byte+1]      ))
    #echo $(( hi + lo ))
    printf "%04x\n"  $(( hi + lo ))
}

meta() {
    RAM=($(i2ctransfer -y 1 w2@0x33 0x07 0x00 r64))
    # ram address - read address start (0x700)
    # see 11.2.1.1 example measurement data
    vbe=$( getWord $(( 0x700 - 0x700 )) )
    vdd=$( getWord $(( 0x72a - 0x700 )) )
    gain=$( getWord $(( 0x70a - 0x700 )) )
    ptat=$( getWord $(( 0x720 - 0x700 )) )
    cp0=$( getWord $(( 0x708 - 0x700 )) )
    cp1=$( getWord $(( 0x728 - 0x700 )) )

    # byte address in driver - offset in this read (768)
    #ptatArt=${ram[768-768]} # vbe
    #vdd=${ram[810-768]} # vdd
    #resolutionRAM=${ram[832-768]}
    #gain=${ram[778-768]} # gain
    #mode=${ram[832-768]}
    #irDataCP0=${ram[776-768]} # cp0
    #irDataCP1=${ram[808-768]} # cp1

    hex=($(i2ctransfer -y 1 w2@0x33 0x80 0x00 r2))
    hi=$(( $((16#${hex[0]#0x})) << 8 ))
    lo=$((    16#${hex[1]#0x}        ))
    stat=$(( hi + lo ))

    ND=$(( (stat >> 3) & 0x01 ))
    LM=$(( stat & 0x07 ))


    echo $vbe $vdd $gain $ptat $cp0 $cp1 $LM
}

#getRR
#setRR
#getRR

setRR
control
status
    echo "vbe  vdd  gain ptat cp0  cp1"
meta
sleep .5
meta
sleep .5
meta
sleep .5
meta
sleep .5
meta
sleep .5
meta
sleep .5
sleep .5
meta
sleep .5
meta
sleep .5
meta
sleep .5
meta
sleep .5
meta
sleep .5


exit

temps
status

exit

sleep 1
status
sleep 1
status
sleep 1
status
sleep 1
status
sleep 1
status
sleep 1
status
sleep 1
status
sleep 1

