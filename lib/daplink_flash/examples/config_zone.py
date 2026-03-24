"""Test suite for DAPLink internal flash config zone.

The config zone is a 1 KB area in the STM32F103 internal flash (gap
between bootloader and interface firmware at 0x0800BC00).  It survives
interface firmware updates and clear_flash operations, making it
suitable for factory data like board revision and sensor calibration.

Commands:
  - WRITE_CONFIG (0x30): offset(2) + len(1) + data(N)
  - READ_CONFIG  (0x31): offset(2) -> 256 bytes
  - CLEAR_CONFIG (0x32): erase the entire 1 KB zone
"""

from time import sleep_ms

from machine import I2C

i2c = I2C(1)
addr = 0x3B
passed = 0
failed = 0


def read_status():
    return i2c.readfrom_mem(addr, 0x80, 1)[0]


def read_error():
    return i2c.readfrom_mem(addr, 0x81, 1)[0]


def wait_busy():
    for _ in range(200):
        if not (read_status() & 0x80):
            return
        sleep_ms(10)
    raise OSError("busy timeout")


def check(name, condition):
    global passed, failed
    if condition:
        passed += 1
        print("  PASS:", name)
    else:
        failed += 1
        print("  FAIL:", name)


def read_config(offset=0):
    wait_busy()
    i2c.writeto_mem(addr, 0x31, bytes([offset >> 8, offset & 0xFF]))
    sleep_ms(100)
    return i2c.readfrom(addr, 256)


def write_config(offset, data):
    if len(data) > 28:
        raise ValueError("data too long (max 28 bytes per frame)")
    wait_busy()
    payload = bytearray([0x30, offset >> 8, offset & 0xFF, len(data)]) + data
    while len(payload) < 32:
        payload.append(0x00)
    i2c.writeto(addr, payload)
    sleep_ms(100)
    wait_busy()


def clear_config():
    wait_busy()
    i2c.writeto(addr, bytearray([0x32]))
    sleep_ms(100)
    wait_busy()


def clear_flash():
    wait_busy()
    i2c.writeto(addr, bytearray([0x10]))
    sleep_ms(1000)
    wait_busy()


print("WHO_AM_I:", hex(i2c.readfrom_mem(addr, 0x01, 1)[0]))

# --- Test 1: Clear config ---
print("\n--- Test 1: Clear config ---")
clear_config()
check("no error", read_error() == 0)
data = read_config()
check("all 0xFF", all(b == 0xFF for b in data))

# --- Test 2: Write and read back ---
print("\n--- Test 2: Write and read back ---")
config = b'{"rev":3,"name":"STeaMi-01"}'
write_config(0, config)
check("no error", read_error() == 0)
data = read_config()
end = 256
for i in range(256):
    if data[i] == 0xFF:
        end = i
        break
check("content matches", bytes(data[:end]) == config)

# --- Test 3: Write at offset ---
print("\n--- Test 3: Write at offset ---")
clear_config()
write_config(100, b"HELLO")
data = read_config()
check("offset 0-99 is 0xFF", all(b == 0xFF for b in data[:100]))
check("offset 100-104 is HELLO", bytes(data[100:105]) == b"HELLO")
check("offset 105 is 0xFF", data[105] == 0xFF)

# --- Test 4: Write preserves existing data ---
print("\n--- Test 4: Write preserves existing data ---")
clear_config()
write_config(0, b"FIRST")
write_config(10, b"SECOND")
data = read_config()
check("FIRST preserved", bytes(data[0:5]) == b"FIRST")
check("SECOND written", bytes(data[10:16]) == b"SECOND")
check("gap is 0xFF", all(b == 0xFF for b in data[5:10]))

# --- Test 5: Clear flash does NOT erase config ---
print("\n--- Test 5: Clear flash preserves config ---")
clear_config()
write_config(0, b"PERSIST")
clear_flash()
data = read_config()
check("config survived clear_flash", bytes(data[:7]) == b"PERSIST")

# --- Test 6: Write at second 256-byte page ---
print("\n--- Test 6: Read second page ---")
clear_config()
write_config(256, b"PAGE2")
data_p1 = read_config(0)
check("page 1 empty", all(b == 0xFF for b in data_p1))
data_p2 = read_config(256)
check("page 2 has data", bytes(data_p2[:5]) == b"PAGE2")

# --- Test 7: Large write (max single chunk) ---
print("\n--- Test 7: Large write ---")
clear_config()
big = b"A" * 28
write_config(0, big)
data = read_config()
check("28 bytes written", bytes(data[:28]) == big)
check("byte 29 is 0xFF", data[28] == 0xFF)

# --- Test 8: Multiple sequential writes ---
print("\n--- Test 8: Multiple sequential writes ---")
clear_config()
for i in range(5):
    write_config(i * 20, bytes([0x41 + i]) * 10)
data = read_config()
check("chunk 0 = AAAAAAAAAA", bytes(data[0:10]) == b"A" * 10)
check("chunk 2 = CCCCCCCCCC", bytes(data[40:50]) == b"C" * 10)
check("chunk 4 = EEEEEEEEEE", bytes(data[80:90]) == b"E" * 10)

# --- Test 9: Existing flash operations still work ---
print("\n--- Test 9: Flash operations still work ---")
wait_busy()
i2c.writeto_mem(addr, 0x20, bytes([0x00, 0x00]))
sleep_ms(200)
sector = i2c.readfrom(addr, 256)
check("read_sector OK", len(sector) == 256)
check("who_am_i OK", i2c.readfrom_mem(addr, 0x01, 1)[0] == 0x4C)

# --- Test 10: USB stability after all operations ---
print("\n--- Test 10: USB stability ---")
for i in range(10):
    write_config(0, b"STRESS" + bytes([0x30 + i]))
    data = read_config()
    if bytes(data[:7]) != b"STRESS" + bytes([0x30 + i]):
        check("stress iteration %d" % i, False)
        break
else:
    check("10 write/read cycles OK", True)

# --- Summary ---
print("\n" + "=" * 40)
print("Results: %d passed, %d failed" % (passed, failed))
if failed == 0:
    print("ALL TESTS PASSED")
else:
    print("SOME TESTS FAILED")
