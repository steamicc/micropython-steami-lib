import math
from time import sleep_ms

from lis2mdl.const import *
from lis2mdl.device import LIS2MDL
from machine import I2C

# Définition des constantes pour remplacer les valeurs magiques
MAGNETIC_FIELD_MIN = 5.0
MAGNETIC_FIELD_MAX = 200.0
TEMP_MIN = -100.0
TEMP_MAX = 150.0
CENTER_TOLERANCE = 0.2
ROUND_TOLERANCE = 1.4
CENTER_TOLERANCE_3D = 0.3
ROUND_TOLERANCE_3D = 1.6
ANGLE_DIFF_MIN = 14.0
ANGLE_DIFF_MAX = 20.0
ANGLE_DIFF_WRAP_MIN = 340.0
ANGLE_DIFF_WRAP_MAX = 346.0
SPAN_MIN = 300.0
FILTER_DIFF_MAX = 90.0


def _bits(v, hi, lo):
    m = (1 << (hi - lo + 1)) - 1
    return (v >> lo) & m


def test_sets(dev):
    ok = True

    # --- MODE ---
    dev.set_mode("continuous")
    r = dev._read_reg(LIS2MDL_CFG_REG_A)
    exp = 0b00
    print(
        "set_mode(continuous): MD=",
        _bits(r, 1, 0),
        "expected",
        exp,
        "=>",
        "OK" if _bits(r, 1, 0) == exp else "FAIL",
    )
    ok &= _bits(r, 1, 0) == exp

    dev.set_mode("single")
    r = dev._read_reg(LIS2MDL_CFG_REG_A)
    exp = 0b01
    print(
        "set_mode(single):      MD=",
        _bits(r, 1, 0),
        "expected",
        exp,
        "=>",
        "OK" if _bits(r, 1, 0) == exp else "FAIL",
    )
    ok &= _bits(r, 1, 0) == exp

    dev.set_mode("idle")
    r = dev._read_reg(LIS2MDL_CFG_REG_A)
    exp = 0b11
    print(
        "set_mode(idle):        MD=",
        _bits(r, 1, 0),
        "expected",
        exp,
        "=>",
        "OK" if _bits(r, 1, 0) == exp else "FAIL",
    )
    ok &= _bits(r, 1, 0) == exp

    # --- ODR ---
    dev.set_odr(50)
    r = dev._read_reg(LIS2MDL_CFG_REG_A)
    exp = 0b10
    print(
        "set_odr(50):         ODR=",
        _bits(r, 3, 2),
        "expected",
        exp,
        "=>",
        "OK" if _bits(r, 3, 2) == exp else "FAIL",
    )
    ok &= _bits(r, 3, 2) == exp

    dev.set_odr(100)
    r = dev._read_reg(LIS2MDL_CFG_REG_A)
    exp = 0b11
    print(
        "set_odr(100):        ODR=",
        _bits(r, 3, 2),
        "expected",
        exp,
        "=>",
        "OK" if _bits(r, 3, 2) == exp else "FAIL",
    )
    ok &= _bits(r, 3, 2) == exp

    # --- Low power ---
    dev.set_low_power(True)
    r = dev._read_reg(LIS2MDL_CFG_REG_A)
    print(
        "set_low_power(True):  LP=",
        (r >> 4) & 1,
        "expected 1 =>",
        "OK" if ((r >> 4) & 1) == 1 else "FAIL",
    )
    ok &= ((r >> 4) & 1) == 1
    dev.set_low_power(False)
    r = dev._read_reg(LIS2MDL_CFG_REG_A)
    print(
        "set_low_power(False): LP=",
        (r >> 4) & 1,
        "expected 0 =>",
        "OK" if ((r >> 4) & 1) == 0 else "FAIL",
    )
    ok &= ((r >> 4) & 1) == 0

    # --- LPF ---
    dev.set_low_pass(True)
    r = dev._read_reg(LIS2MDL_CFG_REG_B)
    print(
        "set_low_pass(True):  LPF=",
        r & 1,
        "expected 1 =>",
        "OK" if (r & 1) == 1 else "FAIL",
    )
    ok &= (r & 1) == 1
    dev.set_low_pass(False)
    r = dev._read_reg(LIS2MDL_CFG_REG_B)
    print(
        "set_low_pass(False): LPF=",
        r & 1,
        "expected 0 =>",
        "OK" if (r & 1) == 0 else "FAIL",
    )
    ok &= (r & 1) == 0

    # --- Offset cancellation ---
    dev.set_offset_cancellation(True, oneshot=False)
    r = dev._read_reg(LIS2MDL_CFG_REG_B)
    print(
        "set_offset_cancellation(True,False): OFF_CANC(bit1)=",
        (r >> 1) & 1,
        "ONE_SHOT(bit4)=",
        (r >> 4) & 1,
        "expected 1,0 =>",
        "OK" if ((r >> 1) & 1) == 1 and ((r >> 4) & 1) == 0 else "FAIL",
    )
    ok &= ((r >> 1) & 1) == 1 and ((r >> 4) & 1) == 0

    dev.set_offset_cancellation(True, oneshot=True)
    r = dev._read_reg(LIS2MDL_CFG_REG_B)
    print(
        "set_offset_cancellation(True,True):  OFF_CANC(bit1)=",
        (r >> 1) & 1,
        "ONE_SHOT(bit4)=",
        (r >> 4) & 1,
        "expected 1,1 =>",
        "OK" if ((r >> 1) & 1) == 1 and ((r >> 4) & 1) == 1 else "FAIL",
    )
    ok &= ((r >> 1) & 1) == 1 and ((r >> 4) & 1) == 1

    # --- BDU / Endianness / SPI4 ---
    dev.set_bdu(True)
    r = dev._read_reg(LIS2MDL_CFG_REG_C)
    print(
        "set_bdu(True):     BDU(bit4)=",
        (r >> 4) & 1,
        "expected 1 =>",
        "OK" if ((r >> 4) & 1) == 1 else "FAIL",
    )
    ok &= ((r >> 4) & 1) == 1

    dev.set_endianness(True)
    r = dev._read_reg(LIS2MDL_CFG_REG_C)
    print(
        "set_endianness(True): BLE(bit3)=",
        (r >> 3) & 1,
        "expected 1 =>",
        "OK" if ((r >> 3) & 1) == 1 else "FAIL",
    )
    ok &= ((r >> 3) & 1) == 1

    dev.use_spi_4wire(True)
    r = dev._read_reg(LIS2MDL_CFG_REG_C)
    print(
        "use_spi_4wire(True): 4WSPI(bit2)=",
        (r >> 2) & 1,
        "expected 1 =>",
        "OK" if ((r >> 2) & 1) == 1 else "FAIL",
    )
    ok &= ((r >> 2) & 1) == 1

    # --- Software offsets / declination ---
    dev.set_heading_offset(15.0)
    dev.set_declination(2.0)
    # Instant flat measurement: the angle should increase by ~17° compared to your raw calculation
    ang1 = (
        dev.heading_flat_only()
    )  # (remember to add offset+declination in your method)
    print(
        "heading_flat_only with offset+declination: angle≈raw+17° (check visually) =>",
        f"{ang1:.2f}°",
    )

    # --- set_calibrate_step / set_hw_offsets ---
    # Apply a dummy calibration, then verify the read-back fields
    dev.set_calibrate_step(10, -20, 30, 300, 300, 300)
    xoff, yoff, zoff, xs, ys, zs = dev.read_calibration()
    print(
        "set_calibrate_step(...): applied offsets/scales =>",
        (xoff, yoff, zoff, xs, ys, zs),
    )

    # If you want to push the correction into the sensor:
    dev.set_hw_offsets(0, 0, 0)  # e.g., reset to 0
    # You can read the registers to verify (optional)
    oxL = dev._read_reg(LIS2MDL_OFFSET_X_REG_L)
    oxH = dev._read_reg(LIS2MDL_OFFSET_X_REG_L + 1)
    print(
        "set_hw_offsets(...): OFFSET_X* =", (oxH << 8) | oxL, "expected written value"
    )

    print("\n=== Overall summary:", "OK" if ok else "Some tests FAIL ===")


def _approx_equal(a, b, tol):
    return abs(a - b) <= tol


def test_reads(dev):
    ok = True
    print("\n=== TEST READS ===")

    # WHO_AM_I
    who = dev.device_id()
    print(f"WHO_AM_I=0x{who:02X}  expected 0x40 =>", "OK" if who == 0x40 else "FAIL")
    ok &= who == 0x40

    # DATA READY
    sleep_ms(50)
    ready = dev.data_ready()
    print("data_ready():", ready, "=>", "OK" if isinstance(ready, bool) else "FAIL")
    ok &= isinstance(ready, bool)

    # MAG RAW
    xr, yr, zr = dev.magnetic_field_raw()
    print(
        f"magnetic_field_raw: (X,Y,Z)=({xr},{yr},{zr}) LSB  =>",
        "OK" if all(isinstance(v, int) for v in (xr, yr, zr)) else "FAIL",
    )
    ok &= all(isinstance(v, int) for v in (xr, yr, zr))

    # MAG µT vs RAW
    xu, yu, zu = dev.magnetic_field_ut()
    print(f"magnetic_field_ut: (X,Y,Z)=({xu:.2f},{yu:.2f},{zu:.2f}) µT")
    # check consistency of conversion µT ≈ raw*0.15
    ok_conv = (
        _approx_equal(xu, xr * 0.15, 0.5)
        and _approx_equal(yu, yr * 0.15, 0.5)
        and _approx_equal(zu, zr * 0.15, 0.5)
    )
    print("Conversion µT vs RAW*0.15 =>", "OK" if ok_conv else "FAIL")
    ok &= ok_conv

    # MAGNITUDE
    B = dev.magnitude_ut()
    print(
        f"magnitude_ut: |B|={B:.1f} µT (Earth ~25-65 µT).  =>",
        "OK" if MAGNETIC_FIELD_MIN <= B <= MAGNETIC_FIELD_MAX else "FAIL",
    )
    ok &= MAGNETIC_FIELD_MIN <= B <= MAGNETIC_FIELD_MAX  # wide, since local disturbances are possible

    # CALIBRATION NORM
    xc, yc, zc = dev.calibrated_field()
    print(f"calibrated_field: ({xc:.3f},{yc:.3f},{zc:.3f})")
    # expected: magnitudes ~[-2..+2] after simple calibration
    ok_cal_rng = abs(xc) < 5 and abs(yc) < 5 and abs(zc) < 5
    print("Calibration norm (|val|<5) =>", "OK" if ok_cal_rng else "WARN")
    ok &= ok_cal_rng

    # TEMP
    t1 = dev.temperature()
    sleep_ms(50)
    t2 = dev.temperature()
    print(f"TempC: t1={t1:.2f}°C, t2={t2:.2f}°C (8 LSB/°C, absolute offset unknown)")
    # test: type & broad plausible range
    ok_temp = (
        isinstance(t1, float)
        and isinstance(t2, float)
        and (TEMP_MIN < t1 < TEMP_MAX)
        and (TEMP_MIN < t2 < TEMP_MAX)
    )
    print("Temp check =>", "OK" if ok_temp else "FAIL")
    ok &= ok_temp

    # INT SOURCE (without IT config, should be 0)
    ints = dev.read_int_source()
    print(
        f"INT_SOURCE=0x{ints:02X} (often 0 if no interrupt configured) =>",
        "OK" if isinstance(ints, int) else "FAIL",
    )
    ok &= isinstance(ints, int)

    # REGISTER DUMP (sanity)
    dump = dev.read_registers(LIS2MDL_CFG_REG_A, 8)  # A..H ~ 0x60..0x67
    print(
        f"Dump 0x60..0x67: {dump} =>",
        "OK" if isinstance(dump, (bytes, bytearray)) and len(dump) == 8 else "FAIL",
    )
    ok &= isinstance(dump, (bytes, bytearray)) and len(dump) == 8

    print("\n=== Overall READS result:", "OK ✅" if ok else "Some checks FAIL ❌")
    return ok


def _fmt_tuple(t):
    return "({:.3f},{:.3f})".format(t[0], t[1])


def test_calibrate_2d(dev):
    print("\n=== 2D CALIBRATION (flat, 360° rotation) ===")
    print("Rotate the board FLAT for ~{} samples...".format(300))
    dev.calibrate_minmax_2d(samples=300, delay_ms=20)
    xoff, yoff, _, xs, ys, _ = (
        dev.x_off,
        dev.y_off,
        dev.z_off,
        dev.x_scale,
        dev.y_scale,
        dev.z_scale,
    )
    print("XY Offsets:", xoff, yoff, "  XY Scales:", xs, ys)

    # quality
    print("Quick check (move a bit while flat during capture)...")
    q = dev.calibrate_quality(samples_check=200, delay_ms=10)
    print("mean_xy =", _fmt_tuple(q["mean_xy"]), " (expected close to 0,0)")
    print(
        "anisotropy_xy =",
        "{:.2f}".format(q["anisotropy_xy"]),
        " (≈1.0 if circle is nicely round)",
    )
    print("r_std_xy =", "{:.3f}".format(q["r_std_xy"]), " (smaller = better)")

    ok_center = abs(q["mean_xy"][0]) < CENTER_TOLERANCE and abs(q["mean_xy"][1]) < CENTER_TOLERANCE
    ok_round = q["anisotropy_xy"] < ROUND_TOLERANCE  # realistic tolerances
    print("=> Center close to 0 :", "OK" if ok_center else "WARN")
    print("=> Circle ≈ round    :", "OK" if ok_round else "WARN")
    return ok_center and ok_round


def test_calibrate_3d(dev):
    print("\n=== 3D CALIBRATION (all orientations) ===")
    print("Rotate the board IN ALL DIRECTIONS for ~{} samples...".format(600))
    dev.calibrate_minmax_3d(samples=600, delay_ms=20)
    print("Offsets:", dev.x_off, dev.y_off, dev.z_off)
    print("Scales :", dev.x_scale, dev.y_scale, dev.z_scale)

    q = dev.calibrate_quality(samples_check=200, delay_ms=10)
    print(
        "mean_xy =", _fmt_tuple(q["mean_xy"]), "  mean_z = {:.3f}".format(q["mean_z"])
    )
    print(
        "std_xy  = ({:.3f},{:.3f})  std_z = {:.3f}".format(
            q["std_xy"][0], q["std_xy"][1], q["std_z"]
        )
    )
    print("anisotropy_xy =", "{:.2f}".format(q["anisotropy_xy"]))
    print(
        "r_mean_xy =",
        "{:.3f}".format(q["r_mean_xy"]),
        "  r_std_xy =",
        "{:.3f}".format(q["r_std_xy"]),
    )

    ok_center = abs(q["mean_xy"][0]) < CENTER_TOLERANCE_3D and abs(q["mean_xy"][1]) < CENTER_TOLERANCE_3D
    ok_round = q["anisotropy_xy"] < ROUND_TOLERANCE_3D
    print("=> Center close to 0 :", "OK" if ok_center else "WARN")
    print("=> Circle ≈ round    :", "OK" if ok_round else "WARN")
    return ok_center and ok_round


def test_heading_after_calib(dev, n=200, delay_ms=20):
    """
    Verify that the angle moves from 0..360° when rotating flat.
    (qualitative test: we look at the span of angles)
    """
    print("\n=== HEADING after calibration (qualitative) ===")
    angles = []
    for _ in range(n):
        ang = dev.heading_flat_only()  # make sure you have atan2(y, x) inside
        angles.append(ang)
        sleep_ms(delay_ms)
    minA = min(angles)
    maxA = max(angles)
    span = (maxA - minA) % 360.0
    print("Angle min={:.1f}°, max={:.1f}°, span~{:.1f}°".format(minA, maxA, span))
    print("=> If you rotated ~one complete turn flat, we expect ~300-360° span.")


def run_all_calibration_tests(dev):
    ok2d = test_calibrate_2d(dev)
    test_heading_after_calib(dev)
    ok3d = test_calibrate_3d(dev)
    print(
        "\n=== Calibration summary:",
        "OK ✅" if (ok2d and ok3d) else "Partial ⚠️ (see WARN/notes)",
    )


def test_heading_flat_basic(dev, n=10, delay_ms=50):
    print("\n=== TEST heading_flat_only (basic reading) ===")
    dev.set_heading_filter(0.0)  # no filter
    angles = []
    for _ in range(n):
        a = dev.heading_flat_only()
        print(f"angle={a:.2f}°  dir={dev.direction_label(a)}")
        angles.append(a)
        sleep_ms(delay_ms)
    ok_types = all(isinstance(a, float) for a in angles)
    print("Float types =>", "OK" if ok_types else "FAIL")
    return ok_types


def test_heading_offset_declination(dev):
    print("\n=== TEST offset + declination ===")
    dev.set_heading_filter(0.0)
    # reference angle without corrections
    dev.set_heading_offset(0.0)
    dev.set_declination(0.0)
    a0 = dev.heading_flat_only()
    # apply +15° offset +2° declination
    dev.set_heading_offset(15.0)
    dev.set_declination(2.0)
    a1 = dev.heading_flat_only()
    # difference mod 360
    diff = (a1 - a0) % 360.0
    # accept ~17° ±3° (due to noise/quantization/filtering)
    ok = (ANGLE_DIFF_MIN <= diff <= ANGLE_DIFF_MAX) or (ANGLE_DIFF_WRAP_MIN <= diff <= ANGLE_DIFF_WRAP_MAX)  # wrap
    print(
        f"angle0={a0:.2f}°, angle1={a1:.2f}°, diff≈{diff:.2f}°  =>",
        "OK" if ok else "FAIL",
    )
    return ok


def test_heading_span_turn(dev, duration_ms=6000, step_ms=50):
    """
    Rotate the board FLAT in roughly one turn for ~duration.
    We check that the angle sweeps ~300..360°.
    """
    print("\n=== TEST SPAN (Do one turn on table) ===")
    dev.set_heading_filter(0.2)  # gentle smoothing
    dev.set_heading_offset(0.0)
    dev.set_declination(0.0)
    angles = []
    t = 0
    while t < duration_ms:
        a = dev.heading_flat_only()
        angles.append(a)
        sleep_ms(step_ms)
        t += step_ms
    minA = min(angles)
    maxA = max(angles)
    # span modulo 360 (handles wrap)
    span = maxA - minA
    if span < 0:
        span += 360.0
    print(f"min={minA:.1f}°, max={maxA:.1f}°, span≈{span:.1f}°")
    ok = span > SPAN_MIN  # we expect almost 360° for a full turn
    print("SPAN =>", "OK" if ok else "WARN (do a more complete/slower turn)")
    return ok


def test_heading_filter_wrap(dev):
    """
    Synthetic test of the vector filter around 0/360°.
    We inject angles near 360->0 and verify there's no 'jump'.
    """
    print("\n=== TEST filter & wrap ===")
    dev.set_heading_filter(0.3)
    dev._hf_cos = None
    dev._hf_sin = None  # reset filter
    # sequence near 360° then 0°
    seq = [350, 355, 0, 5, 10]
    outs = []
    # we 'fake' a reading by forcing heading_from_vectors with synthetic vectors

    for ang in seq:
        # unit vectors in the XY plane
        x = math.cos(math.radians(ang))
        y = math.sin(math.radians(ang))
        out = dev.heading_from_vectors(x, y, 0, calibrated=False)
        outs.append(out)
        print(f"in={ang:>3}° -> out_filt={out:>6.2f}°")
    # Check that the output is monotonically increasing (no jump around ~180°)
    ok = all((outs[i] - outs[i - 1]) % 360.0 < FILTER_DIFF_MAX for i in range(1, len(outs)))
    print("Wrap-safe filter =>", "OK" if ok else "FAIL")
    return ok


def run_heading_tests(dev):
    all_ok = True
    all_ok &= test_heading_flat_basic(dev)
    all_ok &= test_heading_offset_declination(dev)
    # Run this if you can rotate the board flat:
    all_ok &= test_heading_span_turn(dev)
    all_ok &= test_heading_filter_wrap(dev)
    print("\n=== HEADING summary:", "OK ✅" if all_ok else "Partial ⚠️ (see details)")

def test_power_modes(dev):
    print("\n=== TEST POWER MODES ===")
    ok = True

    # Wake in continuous
    dev.power_on("continuous")
    r = dev._read_reg(LIS2MDL_CFG_REG_A)
    md = _bits(r, 1, 0)
    print(
        "wake('continuous') => MD=",
        md,
        "expected 0b00 =>",
        "OK" if md == 0b00 else "FAIL",
    )
    ok &= md == 0b00

    # Wake in single
    dev.power_on("single")
    r = dev._read_reg(LIS2MDL_CFG_REG_A)
    md = _bits(r, 1, 0)
    print(
        "wake('single')      => MD=",
        md,
        "expected 0b01 =>",
        "OK" if md == 0b01 else "FAIL",
    )
    ok &= md == 0b01

    # Power down
    dev.power_off()
    r = dev._read_reg(LIS2MDL_CFG_REG_A)
    md = _bits(r, 1, 0)
    print(
        "power_off()        => MD=",
        md,
        "expected 0b11 =>",
        "OK" if md == 0b11 else "FAIL",
    )
    ok &= md == 0b11
    print(
        "is_idle():",
        dev.is_idle(),
        "expected True =>",
        "OK" if dev.is_idle() else "FAIL",
    )
    ok &= dev.is_idle()

    # Back to continuous
    dev.power_on("continuous")
    r = dev._read_reg(LIS2MDL_CFG_REG_A)
    md = _bits(r, 1, 0)
    print(
        "wake('continuous') => MD=",
        md,
        "expected 0b00 =>",
        "OK" if md == 0b00 else "FAIL",
    )
    ok &= md == 0b00

    return ok


def test_soft_reset(dev):
    print("\n=== TEST SOFT RESET ===")
    ok = True

    # Put into a non-default state
    dev.set_odr(100)  # ODR bits = 11
    dev.set_low_power(True)  # LP bit4 = 1
    dev.set_low_pass(True)  # CFG_B bit0 = 1
    dev.set_bdu(True)  # CFG_C bit4 = 1

    ra_before = dev._read_reg(LIS2MDL_CFG_REG_A)
    rb_before = dev._read_reg(LIS2MDL_CFG_REG_B)
    rc_before = dev._read_reg(LIS2MDL_CFG_REG_C)
    print(
        f"Before reset:  CFG_A=0x{ra_before:02X} CFG_B=0x{rb_before:02X} CFG_C=0x{rc_before:02X}"
    )

    # Soft reset
    dev.soft_reset(wait_ms=15)

    # Read after reset
    ra = dev._read_reg(LIS2MDL_CFG_REG_A)
    rb = dev._read_reg(LIS2MDL_CFG_REG_B)
    rc = dev._read_reg(LIS2MDL_CFG_REG_C)
    print(f"After reset:   CFG_A=0x{ra:02X} CFG_B=0x{rb:02X} CFG_C=0x{rc:02X}")

    # Realistic expectations (typical default values):
    # - MD (bits1..0) = 11 (idle)
    # - ODR (bits3..2) = 00
    # - LP (bit4) = 0
    # - CFG_B.LPF (bit0) = 0
    # - CFG_C.BDU (bit4) = 0
    md_ok = _bits(ra, 1, 0) == 0b11
    odr_ok = _bits(ra, 3, 2) == 0b00
    lp_ok = ((ra >> 4) & 1) == 0
    lpf_ok = (rb & 1) == 0
    bdu_ok = ((rc >> 4) & 1) == 0

    print("MD=idle (11) =>", "OK" if md_ok else "FAIL")
    ok &= md_ok
    print("ODR=00       =>", "OK" if odr_ok else "FAIL")
    ok &= odr_ok
    print("LP=0         =>", "OK" if lp_ok else "FAIL")
    ok &= lp_ok
    print("LPF=0        =>", "OK" if lpf_ok else "FAIL")
    ok &= lpf_ok
    print("BDU=0        =>", "OK" if bdu_ok else "FAIL")
    ok &= bdu_ok

    # Verify that the SOFT_RST bit has cleared back to 0 (auto-clear)
    soft_rst_cleared = ((ra >> 5) & 1) == 0
    print("SOFT_RST auto-clear =>", "OK" if soft_rst_cleared else "FAIL")
    ok &= soft_rst_cleared

    return ok


def test_reboot(dev):
    print("\n=== TEST REBOOT ===")
    ok = True

    # Put into a known state
    dev.set_odr(20)  # ODR=01
    ra_before = dev._read_reg(LIS2MDL_CFG_REG_A)
    print(f"Before reboot: CFG_A=0x{ra_before:02X}")

    # Reboot
    dev.reboot(wait_ms=15)
    ra = dev._read_reg(LIS2MDL_CFG_REG_A)
    print(f"After reboot:  CFG_A=0x{ra:02X}")

    # The REBOOT bit (bit6) must have cleared back to 0
    reboot_cleared = ((ra >> 6) & 1) == 0
    print("REBOOT auto-clear =>", "OK" if reboot_cleared else "FAIL")
    ok &= reboot_cleared

    # WHO_AM_I still correct
    who = dev.device_id()
    print(f"WHO_AM_I=0x{who:02X} expected 0x40 =>", "OK" if who == 0x40 else "FAIL")
    ok &= who == 0x40

    return ok


def run_power_reset_tests(dev):
    all_ok = True
    all_ok &= test_power_modes(dev)
    all_ok &= test_soft_reset(dev)
    all_ok &= test_reboot(dev)
    print("\n=== POWER/RESET summary:", "OK ✅" if all_ok else "Partial ⚠️ (see logs)")


# ---- Run the tests ----
i2c = I2C(1)
dev = LIS2MDL(i2c)
test_reads(dev)
test_sets(dev)
run_all_calibration_tests(dev)
run_heading_tests(dev)
run_power_reset_tests(dev)
