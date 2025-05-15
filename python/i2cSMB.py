#!/usr/bin/env python

from smbus2 import SMBus, i2c_msg
#import board
#import busio

class i2cSMB(SMBus):
    def try_lock(self):
        return True

    def unlock(self):
        pass

    def writeto(self, addr, buf, *, start=0, end=None, stop=True):
        if end is None:
            end = len(buf)
        # buf must be bytes
        #print("writeto")
        write = i2c_msg.write(addr, bytes(buf[start:end]))
        self.i2c_rdwr(write)

    def readfrom(self, addr, nbytes, stop=True):
        #print("readfrom")
        read = i2c_msg.read(addr, nbytes)
        self.i2c_rdwr(read)
        return bytes(read)

    def readfrom_into(self, addr, buf, stop=True):
        #print("readfrom_into")
        nbytes = len(buf)
        read = i2c_msg.read(addr, nbytes)
        self.i2c_rdwr(read)
        # Copy bytes into the provided buffer
        for i in range(nbytes):
            buf[i] = read.buf[i][0]


    def writeto_then_readfrom(self, addr, out_buffer, in_buffer, *, out_start=0, out_end=None, in_start=0, in_end=None):
        MAX_CHUNK = 500  # adjust as needed

        if out_end is None:
            out_end = len(out_buffer)
        if in_end is None:
            in_end = len(in_buffer)

        if out_end - out_start < 2:
            raise ValueError("Need at least 2 bytes in out_buffer for starting address")

        reg_addr = (out_buffer[out_start] << 8) | out_buffer[out_start + 1]
        total_bytes = in_end - in_start

        offset = in_start
        remaining = total_bytes

        while remaining > 0:
            chunk_size = min(MAX_CHUNK, remaining)

            curr_addr = reg_addr + (offset // 2)
            reg_high = (curr_addr >> 8) & 0xFF
            reg_low = curr_addr & 0xFF

            # Create combined write+read message for repeated start
            write = i2c_msg.write(addr, [reg_high, reg_low])
            read = i2c_msg.read(addr, chunk_size)
            self.i2c_rdwr(write, read)

            for i in range(chunk_size):
                in_buffer[offset + i] = read.buf[i][0]

            offset += chunk_size
            remaining -= chunk_size




#i2c = SMBus(4)
#BUS=busio.I2C(1,1)
#i2c = i2cHDMI(4)
#mlx = adafruit_mlx90640.MLX90640(i2c)
#print(f"refresh_rate: {mlx.refresh_rate}")
#mlx.refresh_rate = adafruit_mlx90640.RefreshRate.REFRESH_8_HZ
#print(f"refresh_rate: {mlx.refresh_rate}")
#print("ready")
