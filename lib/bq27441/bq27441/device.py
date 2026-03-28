import struct
from time import sleep_ms, ticks_ms

from machine import Pin

from bq27441.const import *
from bq27441.exceptions import *


# Parameters for the current() function, to specify which current to read
# current_measure types
class CurrentMeasureType(object):
    AVG = 0  # Average Current (DEFAULT)
    STBY = 1  # Standby Current
    MAX = 2  # Max Current

    def __init__(self, value):
        self.value = value


# Parameters for the capacity() function, to specify which capacity to read
class CapacityMeasureType(object):
    REMAIN = 0  # Remaining Capacity (DEFAULT)
    FULL = 1  # Full Capacity
    AVAIL = 2  # Available Capacity
    AVAIL_FULL = 3  # Full Available Capacity
    REMAIN_F = 4  # Remaining Capacity Filtered
    REMAIN_UF = 5  # Remaining Capacity Unfiltered
    FULL_F = 6  # Full Capacity Filtered
    FULL_UF = 7  # Full Capacity Unfiltered
    DESIGN = 8  # Design Capacity

    def __init__(self, value):
        self.value = value


# Parameters for the soc() function
class SocMeasureType(object):
    FILTERED = 0  # State of Charge Filtered (DEFAULT)
    UNFILTERED = 1  # State of Charge Unfiltered

    def __init__(self, value):
        self.value = value


# Parameters for the soh() function
class SohMeasureType(object):
    PERCENT = 0  # State of Health Percentage (DEFAULT)
    SOH_STAT = 1  # State of Health Status Bits

    def __init__(self, value):
        self.value = value


# Parameters for the temperature() function
class TempMeasureType(object):
    BATTERY = 0  # Battery Temperature (DEFAULT)
    INTERNAL_TEMP = 1  # Internal IC Temperature

    def __init__(self, value):
        self.value = value


# Parameters for the set_gpout_function() function
class GpoutFunctionType(object):
    SOC_INT = 0  # Set GPOUT to SOC_INT functionality
    BAT_LOW = 1  # Set GPOUT to BAT_LOW functionality

    def __init__(self, value):
        self.value = value


class BQ27441(object):
    """BQ27441 class contains all major and minor functions use to read and control
    the fuel gauge ic"""

    def __init__(
        self,
        i2c,
        capacity_mAh=LIPO_BATTERY_CAPACITY,  # noqa: N803
        address=BQ27441_I2C_ADDRESS,
        gpout_pin=None,
    ):
        self.address = address
        self.i2c = i2c
        self.gpout = None
        self._shutdown_en = False
        self._user_config_control = False
        self._seal_flag = False
        self.gpout_pin = gpout_pin
        self.capacity_mAh = capacity_mAh
        self.configure_gpout_input()
        self.power_on()

    def configure_gpout_input(self):
        if self.gpout_pin:
            self.gpout = Pin(self.gpout_pin, mode=Pin.IN, pull=Pin.PULL_UP)

    def configure_gpout_output(self):
        if self.gpout_pin:
            self.gpout = Pin(self.gpout_pin, mode=Pin.OUT)

    def power_on(self):
        """Wake up fuel gauge ic if in shutdown mode"""
        self.disable_shutdown_mode()
        sleep_ms(10)
        try:
            self.set_capacity(self.capacity_mAh)
        except Exception:
            raise

    def power_off(self):
        """Put fuel gauge ic in shutdown mode by sending shutdown i2c cmd"""
        self.enter_shutdown_mode()

    def enable_shutdown_mode(self):
        """send i2c shutdown mode enable cmd"""
        self.execute_control_word(BQ27441_CONTROL_SHUTDOWN_ENABLE)
        self._shutdown_en = True

    def enter_shutdown_mode(self):
        """Enter shutdown mode"""
        self.configure_gpout_input()
        self.enable_shutdown_mode()
        self.execute_control_word(BQ27441_CONTROL_SHUTDOWN)

    def disable_shutdown_mode(self):
        if self.gpout_pin:
            self.configure_gpout_output()
            # toggle gpout to exit shutdown mode
            self.gpout.value(0)
            sleep_ms(10)
            self.gpout.value(1)
            sleep_ms(10)
        self._shutdown_en = False

    def is_valid_device(self):
        """Checks if device id returned matches bq27441"""
        return self.device_id() == BQ27441_DEVICE_ID

    # Configures the design capacity of the connected battery.
    def set_capacity(self, capacity):
        # Write to STATE subclass(82) of BQ27441 extended memory.
        # Offset 0x0A(10) Design capacity is a 2 - byte piece of data - MSB first
        cap_msb = capacity >> 8
        cap_lsb = capacity & 0x00FF
        capacity_data = [cap_msb, cap_lsb]
        return self.write_extended_data(BQ27441_ID_STATE, 10, capacity_data, 2)

    # Battery Characteristic Functions

    def current_average(self):
        """Return average current"""
        try:
            result = self.current(CurrentMeasureType.AVG)
            return result
        except Exception:
            raise

    def capacity_full(self):
        """Return full capacity (mAh)"""
        return self.capacity(CapacityMeasureType.FULL)

    def capacity_remaining(self):
        """Return remaining capacity (mAh)"""
        return self.capacity(CapacityMeasureType.REMAIN)

    def state_of_charge(self):
        """Return remaining charge %"""
        return self.soc(SocMeasureType.FILTERED)

    def state_of_health(self):
        """Return state of health %"""
        return self.soh(SohMeasureType.PERCENT)

    # Reads and returns the battery voltage
    def voltage_mv(self):
        """Return current voltage"""
        return self.read_word(BQ27441_COMMAND_VOLTAGE)

    # Reads and returns the specified current measurement
    def current(self, current_measure_type):
        current = 0
        if current_measure_type == CurrentMeasureType.AVG:
            current = self.read_word(BQ27441_COMMAND_AVG_CURRENT)

        elif current_measure_type == CurrentMeasureType.STBY:
            current = self.read_word(BQ27441_COMMAND_STDBY_CURRENT)

        elif current_measure_type == CurrentMeasureType.MAX:
            current = self.read_word(BQ27441_COMMAND_MAX_CURRENT)

        return current

    # Reads and returns the specified capacity measurement
    def capacity(self, capacity_measure_type):
        capacity = 0
        if capacity_measure_type == CapacityMeasureType.REMAIN:
            return self.read_word(BQ27441_COMMAND_REM_CAPACITY)
        elif capacity_measure_type == CapacityMeasureType.FULL:
            return self.read_word(BQ27441_COMMAND_FULL_CAPACITY)
        elif capacity_measure_type == CapacityMeasureType.AVAIL:
            capacity = self.read_word(BQ27441_COMMAND_NOM_CAPACITY)
        elif capacity_measure_type == CapacityMeasureType.AVAIL_FULL:
            capacity = self.read_word(BQ27441_COMMAND_AVAIL_CAPACITY)
        elif capacity_measure_type == CapacityMeasureType.REMAIN_F:
            capacity = self.read_word(BQ27441_COMMAND_REM_CAP_FIL)
        elif capacity_measure_type == CapacityMeasureType.REMAIN_UF:
            capacity = self.read_word(BQ27441_COMMAND_REM_CAP_UNFL)
        elif capacity_measure_type == CapacityMeasureType.FULL_F:
            capacity = self.read_word(BQ27441_COMMAND_FULL_CAP_FIL)
        elif capacity_measure_type == CapacityMeasureType.FULL_UF:
            capacity = self.read_word(BQ27441_COMMAND_FULL_CAP_UNFL)
        elif capacity_measure_type == CapacityMeasureType.DESIGN:
            capacity = self.read_word(BQ27441_EXTENDED_CAPACITY)

        return capacity

    # Reads and returns measured average power

    def power(self):
        return self.read_word(BQ27441_COMMAND_AVG_POWER)

    # Reads and returns specified state of charge measurement
    def soc(self, soc_measure_type=SocMeasureType.FILTERED):
        soc_ret = 0
        if soc_measure_type == SocMeasureType.FILTERED:
            soc_ret = self.read_word(BQ27441_COMMAND_SOC)
        elif soc_measure_type == SocMeasureType.UNFILTERED:
            soc_ret = self.read_word(BQ27441_COMMAND_SOC_UNFL)

        return soc_ret

    # Reads and returns specified state of health measurement
    def soh(self, soh_measure_type=SohMeasureType.PERCENT):
        soh_raw = self.read_word(BQ27441_COMMAND_SOH)
        soh_status = soh_raw >> 8
        soh_percent = soh_raw & 0x00FF

        if soh_measure_type == SohMeasureType.PERCENT:
            return soh_percent
        else:
            return soh_status

    def _read_temperature_dk(self, temp_measure_type=TempMeasureType.BATTERY):
        if temp_measure_type == TempMeasureType.BATTERY:
            return self.read_word(BQ27441_COMMAND_TEMP)
        elif temp_measure_type == TempMeasureType.INTERNAL_TEMP:
            return self.read_word(BQ27441_COMMAND_INT_TEMP)
        else:
            raise ValueError("Unsupported TempMeasureType: {!r}".format(temp_measure_type))

    def temperature(self, temp_measure_type=TempMeasureType.BATTERY):
        return self._read_temperature_dk(temp_measure_type) / 10.0 - 273.15

    def temperature_k(self, temp_measure_type=TempMeasureType.BATTERY):
        return self._read_temperature_dk(temp_measure_type) / 10.0

    def temperature_dk(self, temp_measure_type=TempMeasureType.BATTERY):
        return self._read_temperature_dk(temp_measure_type)

    # GPOUT Control Functions

    # Get GPOUT polarity setting(active - high or active - low)
    def gpout_polarity(self):
        op_config_register = self.op_config()
        return op_config_register & BQ27441_OPCONFIG_GPIOPOL

    # Set GPOUT polarity to active - high or active - low
    def set_gpout_polarity(self, active_high):
        old_op_config = self.op_config()

        # Check to see if we need to update op_config:
        if (active_high and (old_op_config & BQ27441_OPCONFIG_GPIOPOL)) or (
            not active_high and not (old_op_config & BQ27441_OPCONFIG_GPIOPOL)
        ):
            return True
        new_op_config = old_op_config
        if active_high:
            new_op_config |= BQ27441_OPCONFIG_GPIOPOL
        else:
            new_op_config &= ~(BQ27441_OPCONFIG_GPIOPOL)

        return self.write_op_config(new_op_config)

    # Get GPOUT function (BAT_LOW or SOC_INT)
    def gpout_function(self):
        op_config_register = self.op_config()
        return op_config_register & BQ27441_OPCONFIG_BATLOWEN

    # Set GPOUT function to BAT_LOW or SOC_INT
    def set_gpout_function(self, gpout_function):
        old_op_config = self.op_config()
        # Check to see if we need to update op_config:
        if (gpout_function and (old_op_config & BQ27441_OPCONFIG_BATLOWEN)) or (
            not gpout_function and not (old_op_config & BQ27441_OPCONFIG_BATLOWEN)
        ):
            return True

        # Modify BATLOWN_EN bit of op_config:
        new_op_config = old_op_config
        if gpout_function:
            new_op_config |= BQ27441_OPCONFIG_BATLOWEN
        else:
            new_op_config &= ~(BQ27441_OPCONFIG_BATLOWEN)
        # Write new op_config
        return self.write_op_config(new_op_config)

    # Get SOC1_Set Threshold - threshold to set the alert flag
    def soc1_set_threshold(self):
        return self.read_extended_data(BQ27441_ID_DISCHARGE, 0)

    # Get SOC1_Clear Threshold - threshold to clear the alert flag
    def soc1_clear_threshold(self):
        return self.read_extended_data(BQ27441_ID_DISCHARGE, 1)

    # Set the SOC1 set and clear thresholds to a percentage
    def set_soc1_thresholds(self, set_soc, clear_soc):
        thresholds = [0, 0]
        thresholds[0] = constrain(set_soc, 0, 100)
        thresholds[1] = constrain(clear_soc, 0, 100)
        return self.write_extended_data(BQ27441_ID_DISCHARGE, 0, thresholds, 2)

    # Get SOCF_Set Threshold - threshold to set the alert flag
    def socf_set_threshold(self):
        return self.read_extended_data(BQ27441_ID_DISCHARGE, 2)

    # Get SOCF_Clear Threshold - threshold to clear the alert flag
    def socf_clear_threshold(self):
        return self.read_extended_data(BQ27441_ID_DISCHARGE, 3)

    # Set the SOCF set and clear thresholds to a percentage
    def set_socf_thresholds(self, set_socf, clear_socf):
        thresholds = [0, 0]
        thresholds[0] = constrain(set_socf, 0, 100)
        thresholds[1] = constrain(clear_socf, 0, 100)
        return self.write_extended_data(BQ27441_ID_DISCHARGE, 2, thresholds, 2)

    # Check if the SOC1 flag is set
    def soc_flag(self):
        flag_state = self.flags()
        return flag_state & BQ27441_FLAG_SOC1

    # Check if the SOCF flag is set
    def socf_flag(self):
        flag_state = self.flags()
        return flag_state & BQ27441_FLAG_SOCF

    # Get the SOC_INT interval delta
    def soci_delta(self):
        return self.read_extended_data(BQ27441_ID_STATE, 26)

    # Set the SOC_INT interval delta to a value between 1 and 100
    def set_soci_delta(self, delta):
        soci = constrain(delta, 0, 100)
        return self.write_extended_data(BQ27441_ID_STATE, 26, soci, 1)

    # Pulse the GPOUT pin - must be in SOC_INT mode
    def pulse_gpout(self):
        return self.execute_control_word(BQ27441_CONTROL_PULSE_SOC_INT)

    # Read the device ID - should be 0x0421
    def device_id(self):
        return self.read_control_word(BQ27441_CONTROL_DEVICE_TYPE)

    def get_time_ms(self):
        return ticks_ms()

    # Enter configuration mode - set user_control if calling from user code
    # and you want control over when to exit_config
    def enter_config(self, user_control):
        if user_control:
            self._user_config_control = True

        if self.sealed():
            self._seal_flag = True
            self.unseal()  # be unsealed before making changes

        if self.execute_control_word(BQ27441_CONTROL_SET_CFGUPDATE):
            start_ms = self.get_time_ms()
            timeout = False
            while not (self.flags() & BQ27441_FLAG_CFGUPMODE):
                sleep_ms(1)
                elapsed_ms = self.get_time_ms() - start_ms
                if elapsed_ms > BQ27441_I2C_TIMEOUT:
                    timeout = True
                    break

            if not timeout:
                return True
        return False

    # Exit configuration mode with the option to perform a resimulation
    def exit_config(self, resim=True):
        # There are two methods for exiting config mode:
        # 1. Execute the EXIT_CFGUPDATE command
        # 2. Execute the SOFT_RESET command
        # EXIT_CFGUPDATE exits config mode _without_ an OCV(open - circuit voltage)
        # measurement, and without resimulating to update unfiltered - SoC and SoC.
        #  If a new OCV measurement or resimulation is desired, SOFT_RESET or
        # EXIT_RESIM should be used to exit config mode.
        if resim:
            if self.soft_reset():
                start_ms = self.get_time_ms()
                timeout = False

                while not (self.flags() & BQ27441_FLAG_CFGUPMODE):
                    sleep_ms(1)
                    elapsed_ms = self.get_time_ms() - start_ms
                    if elapsed_ms > BQ27441_I2C_TIMEOUT:
                        timeout = True
                        break

                if not timeout:
                    if self._seal_flag:
                        self.seal()  # Seal back up if we IC was sealed coming in
                    return True

            return False

        else:
            return self.execute_control_word(BQ27441_CONTROL_EXIT_CFGUPDATE)

    # Read the flags() command
    def flags(self):
        return self.read_word(BQ27441_COMMAND_FLAGS)

    # Read the CONTROL_STATUS subcommand of control()
    def _control_status(self):
        return self.read_control_word(BQ27441_CONTROL_STATUS)

    # Private Functions
    # Check if the BQ27441 - G1A is sealed or not.
    def sealed(self):
        stat = self._control_status()
        return stat & BQ27441_STATUS_SS

    # Seal the BQ27441 - G1A
    def seal(self):
        return self.read_control_word(BQ27441_CONTROL_SEALED)

    # UNseal the BQ27441 - G1A
    def unseal(self):
        # To unseal the BQ27441, write the key to
        # the control command.Then immediately write the same key to control again.
        if self.read_control_word(BQ27441_UNSEAL_KEY):
            return self.read_control_word(BQ27441_UNSEAL_KEY)

        return False

    # Read the 16-bit op_config register from extended data
    def op_config(self):
        return self.read_word(BQ27441_EXTENDED_OPCONFIG)

    # Write the 16-bit op_config register in extended data
    def write_op_config(self, value):
        op_config_msb = value >> 8
        op_config_lsb = value & 0x00FF
        op_config_data = [op_config_msb, op_config_lsb]

        # OpConfig register location: BQ27441_ID_REGISTERS id, offset 0
        return self.write_extended_data(BQ27441_ID_REGISTERS, 0, op_config_data, 2)

    # Full reset of the BQ27441-G1A
    def reset(self):
        return self.execute_control_word(BQ27441_CONTROL_RESET)

    # Soft reset (resimulation) of the BQ27441-G1A
    def soft_reset(self):
        return self.execute_control_word(BQ27441_CONTROL_SOFT_RESET)

    # Read a 16-bit command word from the BQ27441-G1A, default fmt = little-endian int16
    def read_word(self, sub_address, fmt="<h"):
        data = bytes(self._read_reg(sub_address, 2))
        return struct.unpack(fmt, data)[0]

    # Read a 16 - bit subcommand() from the BQ27441-G1A's control()
    def read_control_word(self, function):
        sub_command_msb = function >> 8
        sub_command_lsb = function & 0x00FF
        command = [sub_command_lsb, sub_command_msb]
        self._write_reg(0, command, 2)
        data = self._read_reg(0, 2)
        if data:
            return (data[1] << 8) | data[0]

        return False

    # Execute a subcommand() from the BQ27441-G1A's control()
    def execute_control_word(self, function):
        sub_command_msb = function >> 8
        sub_command_lsb = function & 0x00FF
        command = [sub_command_lsb, sub_command_msb]
        if self._write_reg(0, command, 2):
            return True

        return False

    # Extended Data Cmds
    # Issue a block_data_control() command to enable block data access
    def block_data_control(self):
        enable_byte = [0x00]
        return self._write_reg(BQ27441_EXTENDED_CONTROL, enable_byte, 1)

    # Issue a block_data_class() command to set the data class to be accessed
    def block_data_class(self, _id):
        _id = [_id]
        return self._write_reg(BQ27441_EXTENDED_DATACLASS, _id, 1)

    # Issue a block_data_offset() command to set the data block to be accessed
    def block_data_offset(self, offset):
        offset = [offset]
        return self._write_reg(BQ27441_EXTENDED_DATABLOCK, offset, 1)

    # Read the current checksum using block_data_checksum()
    def block_data_checksum(self):
        csum = self._read_reg(BQ27441_EXTENDED_CHECKSUM, 1)
        return csum

    # Use BlockData() to read a byte from the loaded extended data
    def read_block_data(self, offset):
        address = offset + BQ27441_EXTENDED_BLOCKDATA
        ret = self._read_reg(address, 1)
        return ret

    # Use BlockData() to write a byte to an offset of the loaded data
    def write_block_data(self, offset, data):
        address = offset + BQ27441_EXTENDED_BLOCKDATA
        data = [data]
        return self._write_reg(address, data, 1)

    # Read all 32 bytes of the loaded extended data and compute a
    # checksum based on the values.
    def compute_block_checksum(self):
        data = self._read_reg(BQ27441_EXTENDED_BLOCKDATA, 32)
        csum = 0
        for i in range(32):
            csum += data[i]

        csum = (255 - (csum & 0xFF)) & 0xFF
        return csum

    # Use the block_data_checksum command to write a checksum value
    def write_block_checksum(self, csum):
        csum = [csum]
        return self._write_reg(BQ27441_EXTENDED_CHECKSUM, csum, 1)

    # Read a byte from extended data specifying a class ID and position offset
    def read_extended_data(self, class_id, offset):
        if not self._user_config_control:
            self.enter_config(False)

        if not self.block_data_control():  # enable block data memory control
            return False  # Return false if enable fails
        if not self.block_data_class(class_id):
            return False

        self.block_data_offset(offset / 32)  # Write 32 - bit block offset(usually 0)

        self.compute_block_checksum()  # Compute checksum going in
        self.block_data_checksum()

        ret_data = self.read_block_data(offset % 32)  # Read from offset (limit to 0 - 31)

        if not self._user_config_control:
            self.exit_config()

        return ret_data

    # Write a specified number of bytes to extended data specifying a
    # class ID, position offset.

    def write_extended_data(self, class_id, offset, data, length):
        if length > 32:
            return False

        if not self._user_config_control:
            self.enter_config(False)

        if not self.block_data_control():  # enable block data memory control
            return False  # Return false if enable fails

        if not self.block_data_class(class_id):
            return False

        self.block_data_offset(int(offset / 32))  # Write 32-bit block offset (usually 0)
        self.compute_block_checksum()  # Compute checksum going in
        self.block_data_checksum()

        # Write data bytes:
        for i in range(length):
            # Write to offset, mod 32 if offset is greater than 32
            # block_data_offset above sets the 32-bit block
            self.write_block_data((offset % 32) + i, data[i])

        # Write new checksum using block_data_checksum (0x60)
        new_csum = self.compute_block_checksum()  # Compute the new checksum
        self.write_block_checksum(new_csum)

        if not self._user_config_control:
            self.exit_config()

        return True

    # I2C Read / Write Functions
    def _read_reg(self, sub_address, count):
        result = self.i2c.readfrom_mem(self.address, sub_address, count)
        return list(result)

    # Write a specified number of bytes over I2C to a given address
    def _write_reg(self, mem_address, buf, count):
        self.i2c.writeto_mem(self.address, mem_address, bytes(buf))
        return True


def constrain(x, a, b):
    if x < a:
        return a
    elif b < x:
        return b
    else:
        return x
