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
    newControl=$((control & 0xfc7f ))
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
    i2ctransfer -y 1 w2@0x33 0x04 0x00 r16
    # clear status after read
    i2ctransfer -y 1 w4@0x33 0x80 0x00 0x00 0x10
}

#getRR
#setRR
#getRR

status
control

temps
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
status
sleep 1

