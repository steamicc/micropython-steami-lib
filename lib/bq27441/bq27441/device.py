from bq27441.const import *
from bq27441.exceptions import *

from utime import sleep_ms, ticks_ms
from machine import Pin, I2C

import sys
import struct


# Parameters for the current() function, to specify which current to read
# current_measure types
class CurrentMeasureType:
    AVG = 0  # Average Current (DEFAULT)
    STBY = 1  # Standby Current
    MAX = 2  # Max Current

    def __init__(self, value):
        self.value = value


# Parameters for the capacity() function, to specify which capacity to read
class CapacityMeasureType:
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
class SocMeasureType:
    FILTERED = 0  # State of Charge Filtered (DEFAULT)
    UNFILTERED = 1  # State of Charge Unfiltered

    def __init__(self, value):
        self.value = value


# Parameters for the soh() function
class SohMeasureType:
    PERCENT = 0  # State of Health Percentage (DEFAULT)
    SOH_STAT = 1  # State of Health Status Bits

    def __init__(self, value):
        self.value = value


# Parameters for the temperature() function
class TempMeasureType:
    BATTERY = 0  # Battery Temperature (DEFAULT)
    INTERNAL_TEMP = 1  # Internal IC Temperature

    def __init__(self, value):
        self.value = value


# Parameters for the setGPOUTFunction() funciton
class GpoutFunctionType:
    SOC_INT = 0  # Set GPOUT to SOC_INT functionality
    BAT_LOW = 1  # Set GPOUT to BAT_LOW functionality

    def __init__(self, value):
        self.value = value


DEFAULT_I2C_BUS = I2C(1)


class BQ27441:
    """BQ27441 class contains all major and minor functions use to read and control
    the fuel gauge ic"""

    def __init__(
        self,
        bus=DEFAULT_I2C_BUS,
        capacity_mAh=LIPO_BATTERY_CAPACITY,
        address=BQ27441_I2C_ADDRESS,
        gpout_pin=None,
    ):
        self.address = address
        self.bus = bus
        self.gpout = None
        self._shutdown_en = False
        self._userConfigControl = False
        self._sealFlag = False
        self.gpout_pin = gpout_pin
        self.capacity_mAh = capacity_mAh
        self.configure_gpout_input()
        print("call power_up after init to use")
        self.power_up()

    def configure_gpout_input(self):
        if self.gpout_pin:
            self.gpout = Pin(self.gpout_pin, mode=Pin.IN, pull=Pin.PULL_UP)

    def configure_gpout_output(self):
        if self.gpout_pin:
            self.gpout = Pin(self.gpout_pin, mode=Pin.OUT)

    def power_up(self):
        """Wake up fuel gauge ic if in shutdown mode"""
        self.disable_shutdown_mode()
        sleep_ms(10)
        try:
            self.set_capacity(self.capacity_mAh)
        except Exception as e:
            print("Failed to wake up fuel gauge: %s" % e)
            sys.print_exception(e)

    def power_down(self):
        """Put fuel gauge ic in shutdown mode by sending shutdown i2c cmd"""
        self.enter_shutdown_mode()

    def enable_shutdown_mode(self):
        """send i2c shutdown mode enable cmd"""
        self.executeControlWord(BQ27441_CONTROL_SHUTDOWN_ENABLE)
        self._shutdown_en = True

    def enter_shutdown_mode(self):
        """Enter shutdown mode"""
        self.configure_gpout_input()
        self.enable_shutdown_mode()
        self.executeControlWord(BQ27441_CONTROL_SHUTDOWN)
        print("WARNING: will need to power cycle board in order to use FuelGauge again")

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
        """Checks if device id returned matches bq27442"""
        deviceID = self.deviceType()  # Read deviceType from BQ27441
        return deviceID == BQ27441_DEVICE_ID

    # Configures the design capacity of the connected battery.
    def set_capacity(self, capacity):
        # Write to STATE subclass(82) of BQ27441 extended memory.
        # Offset 0x0A(10) Design capacity is a 2 - byte piece of data - MSB first
        capMSB = capacity >> 8
        capLSB = capacity & 0x00FF
        capacityData = [capMSB, capLSB]
        return self.writeExtendedData(BQ27441_ID_STATE, 10, capacityData, 2)

    # Battery Characteristic Functions

    def current_average(self):
        """Return average current"""
        try:
            result = self.current(CurrentMeasureType.AVG)
            return result
        except Exception as e:
            print("Failed to get average current (mA): %s" % e)
            sys.print_exception(e)

    def capacity_full(self):
        """Return full capacity (mAh)"""
        try:
            result = self.capacity(CapacityMeasureType.FULL)
            return result
        except Exception as e:
            print("Failed to get max capacity (mAh): %s" % e)
            sys.print_exception(e)

    def capacity_remaining(self):
        """Return remaining capacity (mAh)"""
        try:
            result = self.capacity(CapacityMeasureType.REMAIN)
            return result
        except Exception as e:
            print("Failed to get average current (mA): %s" % e)
            sys.print_exception(e)

    def state_of_charge(self):
        """Return remaining charge %"""
        try:
            result = self.soh(SohMeasureType.PERCENT)
            return result
        except Exception as e:
            print("Failed to get state of health (soh): %s" % e)
            sys.print_exception(e)

    # Reads and returns the battery voltage
    def voltage(self):
        """Return current voltage"""
        try:
            result = self.readWord(BQ27441_COMMAND_VOLTAGE)
            return result
        except Exception as e:
            print("Failed to get voltage: %s" % e)
            sys.print_exception(e)

    # Reads and returns the specified current measurement
    def current(self, current_measure_type):
        current = 0
        if current_measure_type == CurrentMeasureType.AVG:
            current = self.readWord(BQ27441_COMMAND_AVG_CURRENT)

        elif current_measure_type == CurrentMeasureType.STBY:
            current = self.readWord(BQ27441_COMMAND_STDBY_CURRENT)

        elif current_measure_type == CurrentMeasureType.MAX:
            current = self.readWord(BQ27441_COMMAND_MAX_CURRENT)

        return current

    # Reads and returns the specified capacity measurement
    def capacity(self, capacity_measure_type):
        capacity = 0
        if capacity_measure_type == CapacityMeasureType.REMAIN:
            return self.readWord(BQ27441_COMMAND_REM_CAPACITY)
        elif capacity_measure_type == CapacityMeasureType.FULL:
            return self.readWord(BQ27441_COMMAND_FULL_CAPACITY)
        elif capacity_measure_type == CapacityMeasureType.AVAIL:
            capacity = self.readWord(BQ27441_COMMAND_NOM_CAPACITY)
        elif capacity_measure_type == CapacityMeasureType.AVAIL_FULL:
            capacity = self.readWord(BQ27441_COMMAND_AVAIL_CAPACITY)
        elif capacity_measure_type == CapacityMeasureType.REMAIN_F:
            capacity = self.readWord(BQ27441_COMMAND_REM_CAP_FIL)
        elif capacity_measure_type == CapacityMeasureType.REMAIN_UF:
            capacity = self.readWord(BQ27441_COMMAND_REM_CAP_UNFL)
        elif capacity_measure_type == CapacityMeasureType.FULL_F:
            capacity = self.readWord(BQ27441_COMMAND_FULL_CAP_FIL)
        elif capacity_measure_type == CapacityMeasureType.FULL_UF:
            capacity = self.readWord(BQ27441_COMMAND_FULL_CAP_UNFL)
        elif capacity_measure_type == CapacityMeasureType.DESIGN:
            capacity = self.readWord(BQ27441_EXTENDED_CAPACITY)

        return capacity

    # Reads and returns measured average power

    def power(self):
        return self.readWord(BQ27441_COMMAND_AVG_POWER)

    # Reads and returns specified state of charge measurement
    def soc(self, soc_measure_type=SocMeasureType.FILTERED):
        socRet = 0
        if soc_measure_type == SocMeasureType.FILTERED:
            socRet = self.readWord(BQ27441_COMMAND_SOC)
        elif soc_measure_type == SocMeasureType.UNFILTERED:
            socRet = self.readWord(BQ27441_COMMAND_SOC_UNFL)

        return socRet

    # Reads and returns specified state of health measurement
    def soh(self, soh_measure_type=SohMeasureType.PERCENT):
        sohRaw = self.readWord(BQ27441_COMMAND_SOH)
        sohStatus = sohRaw >> 8
        sohPercent = sohRaw & 0x00FF

        if soh_measure_type == SohMeasureType.PERCENT:
            return sohPercent
        else:
            return sohStatus

    # Reads and returns specified temperature measurement
    def temperature(self, temp_measure_type):
        temp = 0
        if temp_measure_type == TempMeasureType.BATTERY:
            temp = self.readWord(BQ27441_COMMAND_TEMP)
        elif temp_measure_type == TempMeasureType.INTERNAL_TEMP:
            temp = self.readWord(BQ27441_COMMAND_INT_TEMP)

        return temp

    # GPOUT Control Functions

    # Get GPOUT polarity setting(active - high or active - low)
    def GPOUTPolarity(self):
        opConfigRegister = self.opConfig()
        return opConfigRegister & BQ27441_OPCONFIG_GPIOPOL

    # Set GPOUT polarity to active - high or active - low
    def setGPOUTPolarity(self, activeHigh):
        oldOpConfig = self.opConfig()

        # Check to see if we need to update opConfig:
        if (activeHigh and (oldOpConfig & BQ27441_OPCONFIG_GPIOPOL)) or (
            not activeHigh and not (oldOpConfig & BQ27441_OPCONFIG_GPIOPOL)
        ):
            return True
        newOpConfig = oldOpConfig
        if activeHigh:
            newOpConfig |= BQ27441_OPCONFIG_GPIOPOL
        else:
            newOpConfig &= ~(BQ27441_OPCONFIG_GPIOPOL)

        return self.writeOpConfig(newOpConfig)

    # Get GPOUT function(BAT_LOW or SOC_INT)
    def GPOUTFunction(self):
        opConfigRegister = self.opConfig()
        return opConfigRegister & BQ27441_OPCONFIG_BATLOWEN

    # Set GPOUT function to BAT_LOW or SOC_INT
    def setGPOUTFunction(self, gpout_function):
        oldOpConfig = self.opConfig()
        # Check to see if we need to update opConfig:
        if (gpout_function and (oldOpConfig & BQ27441_OPCONFIG_BATLOWEN)) or (
            not gpout_function and not (oldOpConfig & BQ27441_OPCONFIG_BATLOWEN)
        ):
            return True

        # Modify BATLOWN_EN bit of opConfig:
        newOpConfig = oldOpConfig
        if gpout_function:
            newOpConfig |= BQ27441_OPCONFIG_BATLOWEN
        else:
            newOpConfig &= ~(BQ27441_OPCONFIG_BATLOWEN)
        # Write new opConfig
        return self.writeOpConfig(newOpConfig)

    # Get SOC1_Set Threshold - threshold to set the alert flag
    def SOC1SetThreshold(self):
        return self.readExtendedData(BQ27441_ID_DISCHARGE, 0)

    # Get SOC1_Clear Threshold - threshold to clear the alert flag
    def SOC1ClearThreshold(self):
        return self.readExtendedData(BQ27441_ID_DISCHARGE, 1)

    # Set the SOC1 set and clear thresholds to a percentage
    def setSOC1Thresholds(self, set_soc, clear_soc):
        thresholds = [0, 0]
        thresholds[0] = constrain(set_soc, 0, 100)
        thresholds[1] = constrain(clear_soc, 0, 100)
        return self.writeExtendedData(BQ27441_ID_DISCHARGE, 0, thresholds, 2)

    # Get SOCF_Set Threshold - threshold to set the alert flag
    def SOCFSetThreshold(self):
        return self.readExtendedData(BQ27441_ID_DISCHARGE, 2)

    # Get SOCF_Clear Threshold - threshold to clear the alert flag
    def SOCFClearThreshold(self):
        return self.readExtendedData(BQ27441_ID_DISCHARGE, 3)

    # Set the SOCF set and clear thresholds to a percentage
    def setSOCFThresholds(self, set_socf, clear_socf):
        thresholds = [0, 0]
        thresholds[0] = constrain(set_socf, 0, 100)
        thresholds[1] = constrain(clear_socf, 0, 100)
        return self.writeExtendedData(BQ27441_ID_DISCHARGE, 2, thresholds, 2)

    # Check if the SOC1 flag is set
    def socFlag(self):
        flagState = self.flags()
        return flagState & BQ27441_FLAG_SOC1

    # Check if the SOCF flag is set
    def socfFlag(self):
        flagState = self.flags()
        return flagState & BQ27441_FLAG_SOCF

    # Get the SOC_INT interval delta
    def sociDelta(self):
        return self.readExtendedData(BQ27441_ID_STATE, 26)

    # Set the SOC_INT interval delta to a value between 1 and 100
    def setSOCIDelta(self, delta):
        soci = constrain(delta, 0, 100)
        return self.writeExtendedData(BQ27441_ID_STATE, 26, soci, 1)

    # Pulse the GPOUT pin - must be in SOC_INT mode
    def pulseGPOUT(self):
        return self.executeControlWord(BQ27441_CONTROL_PULSE_SOC_INT)

    # Read the device type - should be 0x0421
    def deviceType(self):
        return self.readControlWord(BQ27441_CONTROL_DEVICE_TYPE)

    def get_time_ms(self):
        return ticks_ms()

    # Enter configuration mode - set userControl if calling from an Arduino sketch
    # and you want control over when to exitConfig
    def enterConfig(self, userControl):
        print("enterConfig")
        if userControl:
            self._userConfigControl = True

        if self.sealed():
            self._sealFlag = True
            self.unseal()  # be unsealed before making changes

        if self.executeControlWord(BQ27441_CONTROL_SET_CFGUPDATE):
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
    def exitConfig(self, resim=True):
        # There are two methods for exiting config mode:
        # 1. Execute the EXIT_CFGUPDATE command
        # 2. Execute the SOFT_RESET command
        # EXIT_CFGUPDATE exits config mode _without_ an OCV(open - circuit voltage)
        # measurement, and without resimulating to update unfiltered - SoC and SoC.
        #  If a new OCV measurement or resimulation is desired, SOFT_RESET or
        # EXIT_RESIM should be used to exit config mode.
        print("exitConfig")
        if resim:
            if self.softReset():
                start_ms = self.get_time_ms()
                timeout = False

                while not (self.flags() & BQ27441_FLAG_CFGUPMODE):
                    sleep_ms(1)
                    elapsed_ms = self.get_time_ms() - start_ms
                    if elapsed_ms > BQ27441_I2C_TIMEOUT:
                        timeout = True
                        break

                if not timeout:
                    if self._sealFlag:
                        self.seal()  # Seal back up if we IC was sealed coming in
                    return True

            return False

        else:
            return self.executeControlWord(BQ27441_CONTROL_EXIT_CFGUPDATE)

    # Read the flags() command
    def flags(self):
        return self.readWord(BQ27441_COMMAND_FLAGS)

    # Read the CONTROL_STATUS subcommand of control()
    def status(self):
        return self.readControlWord(BQ27441_CONTROL_STATUS)

    # Private Functions
    # Check if the BQ27441 - G1A is sealed or not.
    def sealed(self):
        stat = self.status()
        return stat & BQ27441_STATUS_SS

    # Seal the BQ27441 - G1A
    def seal(self):
        return self.readControlWord(BQ27441_CONTROL_SEALED)

    # UNseal the BQ27441 - G1A
    def unseal(self):
        # To unseal the BQ27441, write the key to
        # the control command.Then immediately write the same key to control again.
        if self.readControlWord(BQ27441_UNSEAL_KEY):
            return self.readControlWord(BQ27441_UNSEAL_KEY)

        return False

    # Readthe 16 - bit opConfig register from extended data
    def opConfig(self):
        return self.readWord(BQ27441_EXTENDED_OPCONFIG)

    # Write the 16 - bit opConfig register in extended data
    def writeOpConfig(self, value):
        opConfigMSB = value >> 8
        opConfigLSB = value & 0x00FF
        opConfigData = [opConfigMSB, opConfigLSB]

        # OpConfig register location: BQ27441_ID_REGISTERS id, offset 0
        return self.writeExtendedData(BQ27441_ID_REGISTERS, 0, opConfigData, 2)

    # Issue a soft - reset to the BQ27441 - G1A
    def softReset(self):
        return self.executeControlWord(BQ27441_CONTROL_SOFT_RESET)

    # Read a 16 - bit command word from the BQ27441-G1A, def format = little endian int16
    def readWord(self, subAddress, format="<h"):
        data = bytes(self.i2cReadBytes(subAddress, 2))
        return struct.unpack(format, data)[0]

    # Read a 16 - bit subcommand() from the BQ27441-G1A's control()
    def readControlWord(self, function):
        subCommandMSB = function >> 8
        subCommandLSB = function & 0x00FF
        command = [subCommandLSB, subCommandMSB]
        self.i2cWriteBytes(0, command, 2)
        data = self.i2cReadBytes(0, 2)
        if data:
            return (data[1] << 8) | data[0]

        return False

    # Execute a subcommand() from the BQ27441-G1A's control()
    def executeControlWord(self, function):
        subCommandMSB = function >> 8
        subCommandLSB = function & 0x00FF
        command = [subCommandLSB, subCommandMSB]
        if self.i2cWriteBytes(0, command, 2):
            return True

        return False

    # Extended Data Cmds
    # Issue a BlockDataControl() command to enable BlockData access
    def blockDataControl(self):
        print("blockDataControl")
        enableByte = [0x00]
        return self.i2cWriteBytes(BQ27441_EXTENDED_CONTROL, enableByte, 1)

    # Issue a DataClass() command to set the data class to be accessed

    def blockDataClass(self, _id):
        print("blockDataClass")
        return self.i2cWriteBytes(BQ27441_EXTENDED_DATACLASS, _id, 1)

    # Issue a DataBlock() command to set the data block to be accessed
    def blockDataOffset(self, offset):
        print("blockDataOffset %s" % offset)
        offset = [offset]
        return self.i2cWriteBytes(BQ27441_EXTENDED_DATABLOCK, offset, 1)

    # Read the current checksum using BlockDataCheckSum()
    def blockDataChecksum(self):
        csum = self.i2cReadBytes(BQ27441_EXTENDED_CHECKSUM, 1)
        return csum

    # Use BlockData() to read a byte from the loaded extended data
    def readBlockData(self, offset):
        address = offset + BQ27441_EXTENDED_BLOCKDATA
        ret = self.i2cReadBytes(address, 1)
        return ret

    # Use BlockData() to write a byte to an offset of the loaded data
    def writeBlockData(self, offset, data):
        address = offset + BQ27441_EXTENDED_BLOCKDATA
        data = [data]
        return self.i2cWriteBytes(address, data, 1)

    # Read all 32 bytes of the loaded extended data and compute a
    # checksum based on the values.
    def computeBlockChecksum(self):
        print("computeBlockChecksum")
        data = self.i2cReadBytes(BQ27441_EXTENDED_BLOCKDATA, 32)
        csum = 0
        for i in range(32):
            csum += data[i]

        csum = 255 - csum
        return csum

    # Use the BlockDataCheckSum() command to write a checksum value
    def writeBlockChecksum(self, csum):
        csum = [csum]
        return self.i2cWriteBytes(BQ27441_EXTENDED_CHECKSUM, csum, 1)

    # Read a byte from extended data specifying a class ID and position offset
    def readExtendedData(self, classID, offset):
        if not self._userConfigControl:
            self.enterConfig(False)

        if not self.blockDataControl():  # enable block data memory control
            return False  # Return false if enable fails
        if not self.blockDataClass(classID):  # Write class ID using DataBlockClass()
            return False

        self.blockDataOffset(offset / 32)  # Write 32 - bit block offset(usually 0)

        self.computeBlockChecksum()  # Compute checksum going in
        self.blockDataChecksum()

        retData = self.readBlockData(offset % 32)  # Read from offset (limit to 0 - 31)

        if not self._userConfigControl:
            self.exitConfig()

        return retData

    # Write a specified number of bytes to extended data specifying a
    # class ID, position offset.

    def writeExtendedData(self, class_id, offset, data, length):
        print("writeExtendedData")
        if length > 32:
            return False

        if not self._userConfigControl:
            self.enterConfig(False)

        if not self.blockDataControl():  # enable block data memory control
            return False  # Return false if enable fails

        if not self.blockDataClass(class_id):  # Write class ID using DataBlockClass()
            return False

        self.blockDataOffset(int(offset / 32))  # Write 32 - bit block offset(usually 0)
        self.computeBlockChecksum()  # Compute checksum going in
        self.blockDataChecksum()

        # Write data bytes:
        print("write data bytes for length %d" % length)
        for i in range(length):
            # Write to offset, mod 32 if offset is greater than 32 The blockDataOffset above sets
            # the 32 - bit block
            self.writeBlockData((offset % 32) + i, data[i])

        # Write new checksum using BlockDataChecksum(0x60)
        newCsum = self.computeBlockChecksum()  # Compute the new checksum
        self.writeBlockChecksum(newCsum)

        if not self._userConfigControl:
            self.exitConfig()

        return True

    # I2C Read / Write Functions
    def i2cReadBytes(self, subAddress, count):
        result = self.bus.readfrom_mem(self.address, subAddress, count)
        return list(result)

    # Write a specified number of bytes over I2C to a given subAddress
    def i2cWriteBytes(self, memAddress, buf, count):
        self.bus.writeto_mem(self.address, memAddress, bytes(buf))


def constrain(x, a, b):
    if x < a:
        return a
    elif b < x:
        return b
    else:
        return x
