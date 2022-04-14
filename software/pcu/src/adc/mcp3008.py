from datetime import datetime
import Adafruit_GPIO.GPIO as GPIO
import Adafruit_GPIO.SPI as SPI
import time
import math


# Classe MCP3008 permettant d'instancier un objet ADC

class MCP3008(object):
    """Class to represent an Adafruit MCP3008 analog to digital converter.
    """
    def __init__(self, clk=None, cs=None, miso=None, mosi=None, spi=None, gpio=None):
        self._spi = None
        # Handle hardware SPI
        if spi is not None:
            self._spi = spi
        elif clk is not None and cs is not None and miso is not None and mosi is not None:
            # Default to platform GPIO if not provided.
            if gpio is None:
                gpio = GPIO.get_platform_gpio()
            self._spi = SPI.BitBang(gpio, clk, mosi, miso, cs)
        else:
            raise ValueError('Must specify either spi for for hardware SPI or clk, cs, miso, and mosi for software SPI!')
        self._spi.set_clock_hz(3600000)
        self._spi.set_mode(0)
        self._spi.set_bit_order(SPI.MSBFIRST)

    def read_adc(self, adc_number):
        """Read the current value of the specified ADC channel (0-7).  The values
        can range from 0 to 1023 (10-bits).
        """
        assert 0 <= adc_number <= 7, 'ADC number must be a value of 0-7!'
        # Build a single channel read command.
        # For example channel zero = 0b11000000
        command = 0b11 << 6                  # Start bit, single channel read
        command |= (adc_number & 0x07) << 3  # Channel number (in 3 bits)
        # Note the bottom 3 bits of command are 0, this is to account for the
        # extra clock to do the conversion, and the low null bit returned at
        # the start of the response.
        resp = self._spi.transfer([command, 0x0, 0x0])
        # Parse out the 10 bits of response data and return it.
        result = (resp[0] & 0x01) << 9
        result |= (resp[1] & 0xFF) << 1
        result |= (resp[2] & 0x80) >> 7
        return result & 0x3FF


# Fonction permettant d'initialiser le port SPI et les ADC
def ADC_setup():
    SPI_PORT   = 0
    SPI_DEVICE_0 = 0
    SPI_DEVICE_1 = 1
    mcp0 = MCP3008(spi=SPI.SpiDev(SPI_PORT, SPI_DEVICE_0))
    mcp1 = MCP3008(spi=SPI.SpiDev(SPI_PORT, SPI_DEVICE_1))
    adc_port = [mcp0, mcp1]
    return adc_port


# Fonction permettant de faire différent debug selon le niveau d'abstraction (branchement, lecture, encodage, etc..)
def calculate_read(adc_port, adc_repo, voltage_ref):
    voltage_list = []
    current_list0 = []
    current_list1 = []
    current_list2 = []
    current_list3 = []
    current_list4 = []
    current_list5 = []
    current_list6 = []
    current_list7 = []

    squareroot2 = math.sqrt(2)                      # Squareroot of 2 to get peak value
    raspberrypi_vdd = voltage_ref                   # Vdd output from the RPi (Has to be confirm if values are not precise)
    voltage_conv_factor = 66.9  # Conversion factor to get V(peak)
    current_conv_factor_port0 = 0.02674548 * 1.018053133654734 * 1.059553084571795 * squareroot2  # Conversion factor to get I(peak) (Due tu resistance precision, every port has to be configure differently)
    current_conv_factor_port1 = 0.02674548 * 1.018053133654734 * 1.059553084571795 * squareroot2
    current_conv_factor_port2 = 0.02640527 * 1.018053133654734 * 1.059553084571795 * squareroot2
    current_conv_factor_port3 = 0.02651524 * 1.018053133654734 * 1.059553084571795 * squareroot2
    current_conv_factor_port4 = 0.02637314 * 1.018053133654734 * 1.059553084571795 * squareroot2
    current_conv_factor_port5 = 0.02669338 * 1.018053133654734 * 1.059553084571795 * squareroot2
    current_conv_factor_port6 = 0.02645705 * 1.018053133654734 * 1.059553084571795 * squareroot2
    current_conv_factor_port7 = 0.01645705 * squareroot2  # Pince de 20A qui sera changé dans le futur

    current_PowerCal_factor_port0 = 0.0284099 * 1.421461196567192 # Conversion factor to get I(peak) (Due tu resistance precision, every port has to be configure differently)
    current_PowerCal_factor_port1 = 0.0284099 * 1.421461196567192 * 1.012820512820513 / 1.018801479257642
    current_PowerCal_factor_port2 = 0.0298088 * 1.421461196567192
    current_PowerCal_factor_port3 = 0.0301245 * 1.421461196567192
    current_PowerCal_factor_port4 = 0.0303976 * 1.421461196567192
    current_PowerCal_factor_port5 = 0.0308991 * 1.421461196567192
    current_PowerCal_factor_port6 = 0.0309091 * 1.421461196567192
    current_PowerCal_factor_port7 = 0.0284099 * 1.421461196567192

    sampling_period = 1.0                           # Sampling period in secondes

    def conv_factor_current(adc_data, v_ref):
        if adc_data < 4:                            # Eliminate noise at start of ADC_READ
            retVal = 0
        else:
            retVal = (adc_data - v_ref)
        return retVal

    def calculate_current(current_list, currentConv):
        size_list = len(current_list)
        temp_data = [None]*size_list
        for i in range(size_list):
            temp_data[i] = math.pow((current_list[i]*currentConv), 2)
        ret_val = math.sqrt(sum(temp_data)/size_list)
        return ret_val

    def calculate_powerdraw(v_list, current_list, powerConv):
        temp_data = []
        for i in range(len(v_list)):
            temp_data.append((current_list[i] * powerConv) * v_list[i])

        ret_val = sum(temp_data) / len(temp_data)
        if ret_val < 0:
            ret_val = 0

        return ret_val

    start_time = time.time()
    while (time.time() - start_time) <= sampling_period:

        voltage_ref = (adc_port[1].read_adc(1))

        current_list0.append(conv_factor_current(adc_port[0].read_adc(0), voltage_ref))
        current_list1.append(conv_factor_current(adc_port[0].read_adc(1), voltage_ref))
        current_list2.append(conv_factor_current(adc_port[0].read_adc(2), voltage_ref))
        current_list3.append(conv_factor_current(adc_port[0].read_adc(3), voltage_ref))

        voltage_list.append((((adc_port[1].read_adc(0)-510) / 1023) * raspberrypi_vdd) * voltage_conv_factor * squareroot2)

        current_list4.append(conv_factor_current(adc_port[0].read_adc(4), voltage_ref))
        current_list5.append(conv_factor_current(adc_port[0].read_adc(5), voltage_ref))
        current_list6.append(conv_factor_current(adc_port[0].read_adc(6), voltage_ref))
        current_list7.append(conv_factor_current(adc_port[0].read_adc(7), voltage_ref))

    powerdraw0 = abs(calculate_powerdraw(voltage_list, current_list0, current_PowerCal_factor_port0))
    powerdraw1 = abs(calculate_powerdraw(voltage_list, current_list1, current_PowerCal_factor_port1))
    powerdraw2 = abs(calculate_powerdraw(voltage_list, current_list2, current_PowerCal_factor_port2))
    powerdraw3 = abs(calculate_powerdraw(voltage_list, current_list3, current_PowerCal_factor_port3))
    powerdraw4 = abs(calculate_powerdraw(voltage_list, current_list4, current_PowerCal_factor_port4))
    powerdraw5 = abs(calculate_powerdraw(voltage_list, current_list5, current_PowerCal_factor_port5))
    powerdraw6 = abs(calculate_powerdraw(voltage_list, current_list6, current_PowerCal_factor_port6))
    powerdraw7 = abs(calculate_powerdraw(voltage_list, current_list7, current_PowerCal_factor_port7))

    voltage_rms = max(voltage_list) / squareroot2

    current0 = calculate_current(current_list0, current_conv_factor_port0)
    current1 = calculate_current(current_list1, current_conv_factor_port1)
    current2 = calculate_current(current_list2, current_conv_factor_port2)
    current3 = calculate_current(current_list3, current_conv_factor_port3)
    current4 = calculate_current(current_list4, current_conv_factor_port4)
    current5 = calculate_current(current_list5, current_conv_factor_port5)
    current6 = calculate_current(current_list6, current_conv_factor_port6)
    current7 = calculate_current(current_list7, current_conv_factor_port7)

    currents_list = [current0, current1, current2, current3, current4, current5,current6, current7]

    powerdraw_list = [powerdraw0, powerdraw1, powerdraw2, powerdraw3, powerdraw4, powerdraw5, powerdraw6, powerdraw7]

    adc_repo.insert_port_measures(datetime.now(), currents_list, voltage_rms, powerdraw_list)





