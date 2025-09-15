#!

status="MLX90640 not found on any bus"
while read -r adapter type; do
    bus="${adapter##*-}"  
    if [[ -n $(i2cdetect -y "$bus" 0x33 0x33 2>/dev/null | grep -o '33') ]]; then
        status="MLX90640 found on bus $bus"
    fi

done < <(i2cdetect -l)
echo $status

