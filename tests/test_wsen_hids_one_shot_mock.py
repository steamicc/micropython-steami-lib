"""Mock tests of the wsen-hids measurement path (issue #425).

On the STeaMi V1a/V1b, CTRL_2.ONE_SHOT stays latched at 1 and STATUS
never reports new data, while continuous mode works. A small register
model of the WSEN-HIDS stands for the chip on the I2C bus. It has the
same behavior: a ONE_SHOT request is kept in CTRL_2 but starts no
conversion, and a conversion only happens when CTRL_1 is in continuous
mode (PD set and ODR not 00). The driver must get its data through
continuous mode, as the Arduino driver does
(https://github.com/steamicc/arduino-steami-lib/blob/main/lib/wsen-hids/src/SteamiWsenHids.cpp).
"""

import pytest

from tests.runner.executor import cleanup_driver, load_driver_mock

ADDR = 0x5F

AV_CONF = 0x10
CTRL_1 = 0x20
CTRL_2 = 0x21
STATUS = 0x27
H_OUT_L = 0x28

PD = 0x80
BDU = 0x04
ODR_MASK = 0x03
ODR_1_HZ = 0x01
ODR_12_5_HZ = 0x03
HEATER = 0x08
ONE_SHOT = 0x01
DATA_READY = 0x03  # H_DA | T_DA

# Calibration of tests/scenarios/wsen_hids.yaml: 30 %RH at 3000, 60 %RH
# at 9000, 20 C at 2000 and 35 C at 5000.
CALIBRATION = {
    0x30: 0x3C,
    0x31: 0x78,
    0x32: 0xA0,
    0x33: 0x18,
    0x35: 0x04,
    0x36: 0xB8,
    0x37: 0x0B,
    0x3A: 0x28,
    0x3B: 0x23,
    0x3C: 0xD0,
    0x3D: 0x07,
    0x3E: 0x88,
    0x3F: 0x13,
}

# (h_raw, t_raw) -> (%RH, C)
SAMPLE_50_25 = (7000, 3000)  # 50.0 %RH, 25.0 C
SAMPLE_40_30 = (5000, 4000)  # 40.0 %RH, 30.0 C


class FakeHIDS:
    """Register model of the WSEN-HIDS, seen as an I2C bus.

    Args:
        samples: (h_raw, t_raw) values given by the next conversions; the
            last one is repeated. An empty list models a chip that never
            converts.
        conversion_polls: STATUS reads, in continuous mode, before a
            conversion ends.
        ctrl_1, ctrl_2: register values at start, as left by a previous
            program.
    """

    def __init__(self, samples=(SAMPLE_50_25,), conversion_polls=3, ctrl_1=0x00, ctrl_2=0x00):
        self.regs = bytearray(0x40)
        self.regs[0x0F] = 0xBC
        self.regs[AV_CONF] = 0x1B
        self.regs[CTRL_1] = ctrl_1
        self.regs[CTRL_2] = ctrl_2
        for reg, value in CALIBRATION.items():
            self.regs[reg] = value
        self.samples = list(samples)
        self.conversion_polls = conversion_polls
        self._polls = 0
        self.ctrl_1_writes = []

    def _continuous(self):
        ctrl_1 = self.regs[CTRL_1]
        return bool(ctrl_1 & PD) and (ctrl_1 & ODR_MASK) != 0

    def _convert(self):
        if not self.samples:
            return
        h_raw, t_raw = self.samples[0]
        if len(self.samples) > 1:
            self.samples.pop(0)
        self.regs[H_OUT_L : H_OUT_L + 4] = bytes(
            [
                h_raw & 0xFF,
                h_raw >> 8,
                t_raw & 0xFF,
                t_raw >> 8,
            ]
        )
        self.regs[STATUS] = DATA_READY

    def _read(self, reg, nbytes):
        reg &= 0x7F
        if reg == STATUS and self._continuous():
            self._polls += 1
            if self._polls >= self.conversion_polls:
                self._polls = 0
                self._convert()
        data = bytes(self.regs[reg : reg + nbytes])
        if reg <= H_OUT_L < reg + nbytes:
            # The model drops the data-ready flags once the outputs are read.
            self.regs[STATUS] = 0
        return data

    # ----- I2C side -----

    def readfrom_mem(self, addr, reg, nbytes, *, addrsize=8):
        assert addr == ADDR
        return self._read(reg, nbytes)

    def readfrom_mem_into(self, addr, reg, buf, *, addrsize=8):
        assert addr == ADDR
        data = self._read(reg, len(buf))
        for i, value in enumerate(data):
            buf[i] = value

    def writeto_mem(self, addr, reg, buf, *, addrsize=8):
        assert addr == ADDR
        if reg == CTRL_1:
            self.ctrl_1_writes.append(buf[0])
            self._polls = 0
        # A ONE_SHOT request stays latched in CTRL_2 and converts nothing,
        # as seen on the V1a/V1b (issue #425).
        self.regs[reg] = buf[0]


@pytest.fixture
def drv():
    module, _ = load_driver_mock("wsen-hids", None, "wsen_hids")
    yield module
    cleanup_driver("wsen-hids", "wsen_hids")


@pytest.fixture
def chip():
    return FakeHIDS()


@pytest.fixture
def dev(drv, chip):
    return drv.WSEN_HIDS(chip)


# ----- Measurements with a latched ONE_SHOT -----


def test_mock_read_one_shot_returns_data(dev):
    humidity, temperature = dev.read_one_shot()
    assert humidity == pytest.approx(50.0)
    assert temperature == pytest.approx(25.0)


def test_mock_read_one_shot_does_not_use_one_shot_bit(dev, chip):
    dev.read_one_shot()
    assert chip.regs[CTRL_2] & ONE_SHOT == 0


def test_mock_read_one_shot_uses_continuous_mode(dev, chip):
    dev.read_one_shot()
    assert PD | BDU | ODR_12_5_HZ in chip.ctrl_1_writes


def test_mock_read_in_power_down_returns_data(dev):
    humidity, temperature = dev.read()
    assert humidity == pytest.approx(50.0)
    assert temperature == pytest.approx(25.0)


def test_mock_humidity_and_temperature_in_power_down(dev):
    assert dev.humidity() == pytest.approx(50.0)
    assert dev.temperature() == pytest.approx(25.0)


def test_mock_read_one_shot_twice(drv, chip):
    chip.samples = [SAMPLE_50_25, SAMPLE_40_30]
    dev = drv.WSEN_HIDS(chip)
    assert dev.read_one_shot() == pytest.approx((50.0, 25.0))
    assert dev.read_one_shot() == pytest.approx((40.0, 30.0))


def test_mock_read_after_power_on_takes_new_sample(drv, chip):
    # power_on() leaves the chip active with ODR 00: no conversion runs
    # until the driver asks for one, so read() must not return old data.
    chip.samples = [SAMPLE_50_25, SAMPLE_40_30]
    dev = drv.WSEN_HIDS(chip)
    dev.power_on()
    assert dev.read() == pytest.approx((50.0, 25.0))
    assert dev.read() == pytest.approx((40.0, 30.0))


def test_mock_read_one_shot_with_larger_timeout(dev):
    assert dev.read_one_shot(timeout_ms=500) == pytest.approx((50.0, 25.0))


# ----- Mode kept after a measurement -----


def test_mock_read_one_shot_goes_back_to_power_down(dev, chip):
    dev.read_one_shot()
    assert chip.regs[CTRL_1] == BDU


def test_mock_read_goes_back_to_power_down(dev, chip):
    dev.read()
    assert chip.regs[CTRL_1] == BDU


def test_mock_read_one_shot_keeps_active_one_shot_mode(dev, chip):
    dev.power_on()
    dev.read_one_shot()
    assert chip.regs[CTRL_1] == PD | BDU


def test_mock_read_one_shot_keeps_continuous_mode(dev, chip):
    dev.set_continuous(dev.ODR_1_HZ)
    dev.read_one_shot()
    assert chip.regs[CTRL_1] == PD | BDU | ODR_1_HZ


def test_mock_read_in_continuous_mode_does_not_change_mode(dev, chip):
    dev.set_continuous(dev.ODR_1_HZ)
    writes = len(chip.ctrl_1_writes)
    dev.read()
    assert len(chip.ctrl_1_writes) == writes


def test_mock_read_one_shot_keeps_bdu_disabled(dev, chip):
    dev.enable_bdu(False)
    dev.read_one_shot()
    assert PD | ODR_12_5_HZ in chip.ctrl_1_writes
    assert chip.regs[CTRL_1] == 0x00


def test_mock_read_one_shot_keeps_heater(dev, chip):
    dev.enable_heater(True)
    dev.read_one_shot()
    assert chip.regs[CTRL_2] == HEATER


# ----- Timeout -----


def test_mock_read_one_shot_timeout_when_chip_never_converts(drv):
    chip = FakeHIDS(samples=[])
    dev = drv.WSEN_HIDS(chip)
    with pytest.raises(drv.WSENHIDSTimeoutError):
        dev.read_one_shot(timeout_ms=20)
    # Back to power-down even after the timeout.
    assert chip.regs[CTRL_1] == BDU


def test_mock_default_timeout_covers_a_12_5_hz_period(dev):
    # A conversion at 12.5 Hz takes up to 80 ms.
    assert dev.DEFAULT_ONE_SHOT_TIMEOUT_MS >= 160


# ----- Registers left by a previous program -----


def test_mock_init_clears_latched_ctrl_2(drv):
    chip = FakeHIDS(ctrl_2=ONE_SHOT | HEATER)
    drv.WSEN_HIDS(chip)
    assert chip.regs[CTRL_2] == 0x00


def test_mock_init_stops_continuous_mode(drv):
    chip = FakeHIDS(ctrl_1=PD | ODR_1_HZ)
    drv.WSEN_HIDS(chip)
    assert chip.regs[CTRL_1] == BDU


def test_mock_init_after_latched_one_shot_then_read(drv):
    chip = FakeHIDS(ctrl_1=PD | BDU, ctrl_2=ONE_SHOT)
    dev = drv.WSEN_HIDS(chip)
    assert dev.read_one_shot() == pytest.approx((50.0, 25.0))
