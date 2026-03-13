from micropython import const

# Lipo Battery Capacity
LIPO_BATTERY_CAPACITY = const(650)  # 650 mAh


BQ27441_I2C_ADDRESS = const(0x55)  # Default I2C address of the BQ27441-G1A

# General Constants #
BQ27441_UNSEAL_KEY = const(0x8000)  # Secret code to unseal the BQ27441-G1A
BQ27441_DEVICE_ID = const(0x0421)  # Default device ID

# Standard Commands #

# The fuel gauge uses a series of 2-byte standard commands to enable system
# reading and writing of battery information. Each command has an associated
# sequential command-code pair.

BQ27441_COMMAND_CONTROL = const(0x00)  # Control()
BQ27441_COMMAND_TEMP = const(0x02)  # Temperature()
BQ27441_COMMAND_VOLTAGE = const(0x04)  # Voltage()
BQ27441_COMMAND_FLAGS = const(0x06)  # Flags()
BQ27441_COMMAND_NOM_CAPACITY = const(0x08)  # NominalAvailableCapacity()
BQ27441_COMMAND_AVAIL_CAPACITY = const(0x0A)  # FullAvailableCapacity()
BQ27441_COMMAND_REM_CAPACITY = const(0x0C)  # RemainingCapacity()
BQ27441_COMMAND_FULL_CAPACITY = const(0x0E)  # FullChargeCapacity()
BQ27441_COMMAND_AVG_CURRENT = const(0x10)  # AverageCurrent()
BQ27441_COMMAND_STDBY_CURRENT = const(0x12)  # StandbyCurrent()
BQ27441_COMMAND_MAX_CURRENT = const(0x14)  # MaxLoadCurrent()
BQ27441_COMMAND_AVG_POWER = const(0x18)  # AveragePower()
BQ27441_COMMAND_SOC = const(0x1C)  # StateOfCharge()
BQ27441_COMMAND_INT_TEMP = const(0x1E)  # InternalTemperature()
BQ27441_COMMAND_SOH = const(0x20)  # StateOfHealth()
BQ27441_COMMAND_REM_CAP_UNFL = const(0x28)  # RemainingCapacityUnfiltered()
BQ27441_COMMAND_REM_CAP_FIL = const(0x2A)  # RemainingCapacityFiltered()
BQ27441_COMMAND_FULL_CAP_UNFL = const(0x2C)  # FullChargeCapacityUnfiltered()
BQ27441_COMMAND_FULL_CAP_FIL = const(0x2E)  # FullChargeCapacityFiltered()
BQ27441_COMMAND_SOC_UNFL = const(0x30)  # StateOfChargeUnfiltered()

# Control Sub-commands #

# Issuing a Control() command requires a subsequent 2-byte subcommand. These
# additional bytes specify the particular control function desired. The
# Control() command allows the system to control specific features of the fuel
# gauge during normal operation and additional features when the device is in
# different access modes.

BQ27441_CONTROL_STATUS = const(0x00)
BQ27441_CONTROL_DEVICE_TYPE = const(0x01)
BQ27441_CONTROL_FW_VERSION = const(0x02)
BQ27441_CONTROL_DM_CODE = const(0x04)
BQ27441_CONTROL_PREV_MACWRITE = const(0x07)
BQ27441_CONTROL_CHEM_ID = const(0x08)
BQ27441_CONTROL_BAT_INSERT = const(0x0C)
BQ27441_CONTROL_BAT_REMOVE = const(0x0D)
BQ27441_CONTROL_SET_HIBERNATE = const(0x11)
BQ27441_CONTROL_CLEAR_HIBERNATE = const(0x12)
BQ27441_CONTROL_SET_CFGUPDATE = const(0x13)
BQ27441_CONTROL_SHUTDOWN_ENABLE = const(0x1B)
BQ27441_CONTROL_SHUTDOWN = const(0x1C)
BQ27441_CONTROL_SEALED = const(0x20)
BQ27441_CONTROL_PULSE_SOC_INT = const(0x23)
BQ27441_CONTROL_RESET = const(0x41)
BQ27441_CONTROL_SOFT_RESET = const(0x42)
BQ27441_CONTROL_EXIT_CFGUPDATE = const(0x43)
BQ27441_CONTROL_EXIT_RESIM = const(0x44)

# Control Status Word - Bit Definitions #

# Bit positions for the 16-bit data of CONTROL_STATUS.
# CONTROL_STATUS instructs the fuel gauge to return status information to
# Control() addresses 0x00 and 0x01. The read-only status word contains status
# bits that are set or cleared either automatically as conditions warrant or
# through using specified subcommands.
BQ27441_STATUS_SHUTDOWNEN = const(1 << 15)
BQ27441_STATUS_WDRESET = const(1 << 14)
BQ27441_STATUS_SS = const(1 << 13)
BQ27441_STATUS_CALMODE = const(1 << 12)
BQ27441_STATUS_CCA = const(1 << 11)
BQ27441_STATUS_BCA = const(1 << 10)
BQ27441_STATUS_QMAX_UP = const(1 << 9)
BQ27441_STATUS_RES_UP = const(1 << 8)
BQ27441_STATUS_INITCOMP = const(1 << 7)
BQ27441_STATUS_HIBERNATE = const(1 << 6)
BQ27441_STATUS_SLEEP = const(1 << 4)
BQ27441_STATUS_LDMD = const(1 << 3)
BQ27441_STATUS_RUP_DIS = const(1 << 2)
BQ27441_STATUS_VOK = const(1 << 1)


# Flag Command - Bit Definitions #

# Bit positions for the 16-bit data of Flags()
# This read-word function returns the contents of the fuel gauging status
# register, depicting the current operating status.
BQ27441_FLAG_OT = const(1 << 15)
BQ27441_FLAG_UT = const(1 << 14)
BQ27441_FLAG_FC = const(1 << 9)
BQ27441_FLAG_CHG = const(1 << 8)
BQ27441_FLAG_OCVTAKEN = const(1 << 7)
BQ27441_FLAG_ITPOR = const(1 << 5)
BQ27441_FLAG_CFGUPMODE = const(1 << 4)
BQ27441_FLAG_BAT_DET = const(1 << 3)
BQ27441_FLAG_SOC1 = const(1 << 2)
BQ27441_FLAG_SOCF = const(1 << 1)
BQ27441_FLAG_DSG = const(1 << 0)


# Extended Data Commands #

# Extended data commands offer additional functionality beyond the standard
# set of commands. They are used in the same manner; however, unlike standard
# commands, extended commands are not limited to 2-byte words.
BQ27441_EXTENDED_OPCONFIG = const(0x3A)  # OpConfig()
BQ27441_EXTENDED_CAPACITY = const(0x3C)  # DesignCapacity()
BQ27441_EXTENDED_DATACLASS = const(0x3E)  # DataClass()
BQ27441_EXTENDED_DATABLOCK = const(0x3F)  # DataBlock()
BQ27441_EXTENDED_BLOCKDATA = const(0x40)  # BlockData()
BQ27441_EXTENDED_CHECKSUM = const(0x60)  # BlockDataCheckSum()
BQ27441_EXTENDED_CONTROL = const(0x61)  # BlockDataControl()


# Configuration Class, Subclass ID's #

# To access a subclass of the extended data, set the DataClass() function
# with one of these values.
# Configuration Classes
BQ27441_ID_SAFETY = const(2)  # Safety
BQ27441_ID_CHG_TERMINATION = const(36)  # Charge Termination
BQ27441_ID_CONFIG_DATA = const(48)  # Data
BQ27441_ID_DISCHARGE = const(49)  # Discharge
BQ27441_ID_REGISTERS = const(64)  # Registers
BQ27441_ID_POWER = const(68)  # Power
# Gas Gauging Classes
BQ27441_ID_IT_CFG = const(80)  # IT Cfg
BQ27441_ID_CURRENT_THRESH = const(81)  # Current Thresholds
BQ27441_ID_STATE = const(82)  # State
# Ra Tables Classes
BQ27441_ID_R_A_RAM = const(89)  # R_a RAM
# Calibration Classes
BQ27441_ID_CALIB_DATA = const(104)  # Data
BQ27441_ID_CC_CAL = const(105)  # CC Cal
BQ27441_ID_CURRENT = const(107)  # Current
# Security Classes
BQ27441_ID_CODES = const(112)  # Codes


# OpConfig Register - Bit Definitions #

# Bit positions of the OpConfig Register
BQ27441_OPCONFIG_BIE = const(1 << 13)
BQ27441_OPCONFIG_BI_PU_EN = const(1 << 12)
BQ27441_OPCONFIG_GPIOPOL = const(1 << 11)
BQ27441_OPCONFIG_SLEEP = const(1 << 5)
BQ27441_OPCONFIG_RMFCC = const(1 << 4)
BQ27441_OPCONFIG_BATLOWEN = const(1 << 2)
BQ27441_OPCONFIG_TEMPS = const(1 << 0)

BQ27441_I2C_TIMEOUT = const(2000)  # ms
