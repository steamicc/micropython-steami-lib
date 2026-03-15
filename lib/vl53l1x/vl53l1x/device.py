import machine

VL53L1X_DEFAULT_CONFIGURATION = bytes(
    [
        0x00,  # 0x2d : fast plus mode disabled (set bit 2 and 5 to 1 for 1MHz I2C) */
        0x00,  # 0x2e : bit 0 if I2C pulled up at 1.8V, else set bit 0 to 1 (pull up at AVDD) */
        0x00,  # 0x2f : bit 0 if GPIO pulled up at 1.8V, else set bit 0 to 1 (pull up at AVDD) */
        0x01,  # 0x30 : set bit 4 to 0 for active high interrupt and 1 for active low (bits 3:0 must be 0x1) */
        0x02,  # 0x31 : bit 1 = interrupt depending on the polarity */
        0x00,  # 0x32 : not user-modifiable */
        0x02,  # 0x33 : not user-modifiable */
        0x08,  # 0x34 : not user-modifiable */
        0x00,  # 0x35 : not user-modifiable */
        0x08,  # 0x36 : not user-modifiable */
        0x10,  # 0x37 : not user-modifiable */
        0x01,  # 0x38 : not user-modifiable */
        0x01,  # 0x39 : not user-modifiable */
        0x00,  # 0x3a : not user-modifiable */
        0x00,  # 0x3b : not user-modifiable */
        0x00,  # 0x3c : not user-modifiable */
        0x00,  # 0x3d : not user-modifiable */
        0xFF,  # 0x3e : not user-modifiable */
        0x00,  # 0x3f : not user-modifiable */
        0x0F,  # 0x40 : not user-modifiable */
        0x00,  # 0x41 : not user-modifiable */
        0x00,  # 0x42 : not user-modifiable */
        0x00,  # 0x43 : not user-modifiable */
        0x00,  # 0x44 : not user-modifiable */
        0x00,  # 0x45 : not user-modifiable */
        0x20,  # 0x46 : interrupt configuration 0x20 = new sample ready */
        0x0B,  # 0x47 : not user-modifiable */
        0x00,  # 0x48 : not user-modifiable */
        0x00,  # 0x49 : not user-modifiable */
        0x02,  # 0x4a : not user-modifiable */
        0x0A,  # 0x4b : not user-modifiable */
        0x21,  # 0x4c : not user-modifiable */
        0x00,  # 0x4d : not user-modifiable */
        0x00,  # 0x4e : not user-modifiable */
        0x05,  # 0x4f : not user-modifiable */
        0x00,  # 0x50 : not user-modifiable */
        0x00,  # 0x51 : not user-modifiable */
        0x00,  # 0x52 : not user-modifiable */
        0x00,  # 0x53 : not user-modifiable */
        0xC8,  # 0x54 : not user-modifiable */
        0x00,  # 0x55 : not user-modifiable */
        0x00,  # 0x56 : not user-modifiable */
        0x38,  # 0x57 : not user-modifiable */
        0xFF,  # 0x58 : not user-modifiable */
        0x01,  # 0x59 : not user-modifiable */
        0x00,  # 0x5a : not user-modifiable */
        0x08,  # 0x5b : not user-modifiable */
        0x00,  # 0x5c : not user-modifiable */
        0x00,  # 0x5d : not user-modifiable */
        0x01,  # 0x5e : not user-modifiable */
        0xDB,  # 0x5f : not user-modifiable */
        0x0F,  # 0x60 : not user-modifiable */
        0x01,  # 0x61 : not user-modifiable */
        0xF1,  # 0x62 : not user-modifiable */
        0x0D,  # 0x63 : not user-modifiable */
        0x01,  # 0x64 : Sigma threshold MSB (mm in 14.2 format for MSB+LSB), default value 90 mm */
        0x68,  # 0x65 : Sigma threshold LSB */
        0x00,  # 0x66 : Min count Rate MSB (MCPS in 9.7 format for MSB+LSB) */
        0x80,  # 0x67 : Min count Rate LSB */
        0x08,  # 0x68 : not user-modifiable */
        0xB8,  # 0x69 : not user-modifiable */
        0x00,  # 0x6a : not user-modifiable */
        0x00,  # 0x6b : not user-modifiable */
        0x00,  # 0x6c : Intermeasurement period MSB, 32 bits register */
        0x00,  # 0x6d : Intermeasurement period */
        0x0F,  # 0x6e : Intermeasurement period */
        0x89,  # 0x6f : Intermeasurement period LSB */
        0x00,  # 0x70 : not user-modifiable */
        0x00,  # 0x71 : not user-modifiable */
        0x00,  # 0x72 : distance threshold high MSB (in mm, MSB+LSB) */
        0x00,  # 0x73 : distance threshold high LSB */
        0x00,  # 0x74 : distance threshold low MSB (in mm, MSB+LSB) */
        0x00,  # 0x75 : distance threshold low LSB */
        0x00,  # 0x76 : not user-modifiable */
        0x01,  # 0x77 : not user-modifiable */
        0x0F,  # 0x78 : not user-modifiable */
        0x0D,  # 0x79 : not user-modifiable */
        0x0E,  # 0x7a : not user-modifiable */
        0x0E,  # 0x7b : not user-modifiable */
        0x00,  # 0x7c : not user-modifiable */
        0x00,  # 0x7d : not user-modifiable */
        0x02,  # 0x7e : not user-modifiable */
        0xC7,  # 0x7f : ROI center */
        0xFF,  # 0x80 : XY ROI (X=Width, Y=Height) */
        0x9B,  # 0x81 : not user-modifiable */
        0x00,  # 0x82 : not user-modifiable */
        0x00,  # 0x83 : not user-modifiable */
        0x00,  # 0x84 : not user-modifiable */
        0x01,  # 0x85 : not user-modifiable */
        0x01,  # 0x86 : clear interrupt */
        0x40,  # 0x87 : start ranging, put 0x40 for automatic start after init */
    ]
)


class VL53L1X(object):
    def __init__(self, i2c, address=0x29):
        self.i2c = i2c
        self.address = address
        self.reset()
        machine.lightsleep(1)
        if self.device_id() != 0xEACC:
            raise RuntimeError("Failed to find expected ID register values. Check wiring!")
        # write default configuration
        self.i2c.writeto_mem(self.address, 0x2D, VL53L1X_DEFAULT_CONFIGURATION, addrsize=16)
        # adjust timing; assumes MM1 and MM2 are disabled
        self._write_reg16(0x001E, self._read_reg16(0x0022) * 4)
        machine.lightsleep(200)

    def _write_reg(self, reg, value):
        return self.i2c.writeto_mem(self.address, reg, bytes([value]), addrsize=16)

    def _write_reg16(self, reg, value):
        return self.i2c.writeto_mem(
            self.address, reg, bytes([(value >> 8) & 0xFF, value & 0xFF]), addrsize=16
        )

    def _read_reg(self, reg):
        return self.i2c.readfrom_mem(self.address, reg, 1, addrsize=16)[0]

    def _read_reg16(self, reg):
        data = self.i2c.readfrom_mem(self.address, reg, 2, addrsize=16)
        return (data[0] << 8) + data[1]

    def device_id(self):
        return self._read_reg16(0x010F)

    def reset(self):
        self._write_reg(0x0000, 0x00)
        machine.lightsleep(100)
        self._write_reg(0x0000, 0x01)

    def start_ranging(self):
        self._write_reg(0x0087, 0x40)

    def stop_ranging(self):
        self._write_reg(0x0087, 0x00)

    def _is_data_ready(self):
        polarity = self._read_reg(0x0030) & 0x10
        ready_val = 1 if polarity == 0 else 0
        return (self._read_reg(0x0031) & 0x01) == ready_val

    def _clear_interrupt(self):
        self._write_reg(0x0086, 0x01)

    def _ensure_data(self):
        if not self._is_data_ready():
            self.start_ranging()
            for _ in range(100):
                if self._is_data_ready():
                    return
                machine.lightsleep(10)
            raise OSError("VL53L1X data ready timeout")

    def read(self):
        self._ensure_data()
        data = self.i2c.readfrom_mem(self.address, 0x0089, 17, addrsize=16)
        final_crosstalk_corrected_range_mm_sd0 = (data[13] << 8) + data[14]
        self._clear_interrupt()
        return final_crosstalk_corrected_range_mm_sd0
