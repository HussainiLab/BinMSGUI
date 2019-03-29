import numpy as np
import mmap
import contextlib
import os
import json
import datetime
import math


__author__ = "Geoffrey Barrett"
"""I converted Intan's functions for Python to include memory mapping which should result in faster reads of the data"""


def find_sub(string, sub):
    '''finds all instances of a substring within a string and outputs a list of indices'''
    result = []
    k = 0
    while k < len(string):
        k = string.find(sub, k)
        if k == -1:
            return result
        else:
            result.append(k)
            k += 1  # change to k += len(sub) to not search overlapping results
    return result


def get_ref_index(channel_info, ref):
    """
    This function will find the index (1-based) for a given channel name
    using Intan's native_channel_name structure (i.e. A-000, A-001, A-002, etc.)
    """
    for i, channel in enumerate(channel_info):
        if channel['native_channel_name'] == ref:
            return i + 1
    raise ValueError("The following channel name does not exist: %s" % ref)


def get_intan_data(session_files, data_channels=None, tetrode=None, self=None, verbose=True, ephys_data=True,
                   digital_data=True, analog_data=True):

    file_header = read_header(session_files[0])

    data = np.array([])
    t_intan = np.array([])
    data_digital_in = np.array([])
    data_analog_in = np.array([])
    # concatenates the data from all the .rhd files

    if data_channels is not None:
        data_channels = np.asarray(data_channels)

    # analyze the one tetrode's data at a time to attempt to not load too much data into memory at once
    for session_file in sorted(session_files, reverse=False):
        # Loads each session and appends them to create one matrix of data for the current tetrode

        if verbose:
            msg = '[%s %s]: Currently loading data from the following file: %s' % \
                  (str(datetime.datetime.now().date()),
                   str(datetime.datetime.now().time())[:8], session_file)

            if self:
                self.LogAppend.myGUI_signal_str.emit(msg)
            else:
                print(msg)

        file_data = read_data(session_file, include_analog=analog_data, include_digital=digital_data,
                              include_ephys=ephys_data)

        # Acquiring session information

        # read the digital values if given
        if digital_data:
            if file_header['num_board_dig_in_channels'] > 0:
                if data_digital_in.shape[0] == 0:
                    data_digital_in = file_data['board_dig_in_data']
                else:
                    data_digital_in = np.concatenate((data_digital_in, file_data['board_dig_in_data']), axis=1)

        if analog_data:
            # read the analog data
            if file_header['num_board_adc_channels'] > 0:
                if data_analog_in.shape[0] == 0:
                    data_analog_in = file_data['board_adc_data']
                else:
                    data_analog_in = np.concatenate((data_analog_in, file_data['board_adc_data']), axis=1)

        if ephys_data:
            # read the ephys data
            if data_channels is None:
                data_channels = np.arange(file_data['amplifier_data'].shape[0])+1

            if data.shape[0] == 0:
                data = file_data['amplifier_data']
                # bits, data is arranged into (number of channels, number of samples)
                data = data[data_channels - 1, :]
            else:
                data = np.concatenate((data, file_data['amplifier_data'][data_channels - 1, :]), axis=1)

        # read the time data
        if t_intan.shape[0] == 0:
            t_intan = file_data[
                't_amplifier']  # the times recorded by the intan system, starts at the value of 0 seconds
        else:
            # the time's always start at 0, per .rhd file, so when putting them together you need add
            # to each time value
            t_intan = np.concatenate((t_intan, file_data['t_amplifier']), axis=0)

    return data, t_intan, data_digital_in, data_analog_in


def get_bytes_per_data_block(header):
    """Calculates the number of bytes in each 60 or 128 sample datablock."""

    # Each data block contains 60 or 128 amplifier samples.
    bytes_per_block = header['num_samples_per_data_block'] * 4  # timestamp data
    bytes_per_block = bytes_per_block + header['num_samples_per_data_block'] * 2 * header['num_amplifier_channels']

    # Auxiliary inputs are sampled 4x slower than amplifiers
    bytes_per_block = bytes_per_block + (
            header['num_samples_per_data_block'] / 4) * 2 * header['num_aux_input_channels']

    # Supply voltage is sampled 60 or 128x slower than amplifiers
    bytes_per_block = bytes_per_block + 1 * 2 * header['num_supply_voltage_channels']

    # Board analog inputs are sampled at same rate as amplifiers
    bytes_per_block = bytes_per_block + header['num_samples_per_data_block'] * 2 * header['num_board_adc_channels']

    # Board digital inputs are sampled at same rate as amplifiers
    if header['num_board_dig_in_channels'] > 0:
        bytes_per_block = bytes_per_block + header['num_samples_per_data_block'] * 2

    # Board digital outputs are sampled at same rate as amplifiers
    if header['num_board_dig_out_channels'] > 0:
        bytes_per_block = bytes_per_block + header['num_samples_per_data_block'] * 2

    # Temp sensor is sampled 60 or 128x slower than amplifiers
    if header['num_temp_sensor_channels'] > 0:
        bytes_per_block = bytes_per_block + 1 * 2 * header['num_temp_sensor_channels']

    return bytes_per_block


def get_qstring_length(data, qstring_start):
    """returns the length of the qstring"""

    qstring_length = 4  # from the first 4 bytes which will be used to computer the string length
    length = np.fromstring(data[qstring_start:qstring_start + qstring_length], dtype='<I')

    if length == int('ffffffff', 16):
        pass
    else:
        qstring_length += length[0]

    return qstring_length


def get_qstring(data, qstring_start):
    """returns the length of the qstring"""

    qstring_length = 4  # from the first 4 bytes which will be used to computer the string length
    length = np.fromstring(data[qstring_start:qstring_start + qstring_length], dtype='<I')
    if length == int('ffffffff', 16):
        return '', 4  # for the 4 bytes used for the length
    else:
        length = length[0]
        if length != 0:
            qstring = np.fromstring(data[
                                    qstring_start + qstring_length:qstring_start + qstring_length + length],
                                    dtype='<H')
            qstring = ''.join([chr(c) for c in qstring])
        else:
            qstring = ''

    return qstring, qstring_length + length


def get_intan_Fs(filename):
    with open(filename, 'rb') as f:
        with contextlib.closing(mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ)) as m:
            pass


def get_header_length(data):
    """This will let us know how many bytes the header requires so we can skip reading
    this information into memory"""

    header_length = 48  # skip the first 48 bytes, they will always have a determined byte length

    version = np.fromstring(data[4:8], dtype='<h')  # (version major, version minor)

    for i in range(3):
        # get the qstrings for the 3 notes
        # qstring_start = header_length
        header_length += get_qstring_length(data, header_length)

    # need to get the string length for the settings filename
    if (version[0] == 1 and version[1] >= 6) or (version[0] > 1):
        header_length += get_qstring_length(data, header_length)

    # if data file is from GUI v1.1 or later, see if temp sensor was saved
    if version[0] == 1 and version[1] >= 1 or version[0] > 1:
        header_length += 2

    # if data file is from GUI v1.3 or later, load eval board mode
    if version[0] == 1 and version[1] >= 3 or version[0] > 1:
        header_length += 2

    # get the reference channel data length
    if version[0] > 1:
        header_length += get_qstring_length(data, header_length)

    # get the qstrings for signal group
    number_of_signal_groups = np.fromstring(data[header_length:header_length + 2], dtype='<h')
    header_length += 2

    for signal_group in np.arange(number_of_signal_groups):
        # qstring_start = header_length
        for i in range(2):
            # once for signal group name, once for group prefix
            header_length += get_qstring_length(data, header_length)

        signal_values = np.fromstring(data[header_length:header_length + 6], dtype='<h')

        header_length += 6

        if signal_values[1] > 0 and signal_values[0] > 0:
            for signal_channel in np.arange(signal_values[1]):
                for i in range(2):
                    # once for native_channel_name, once for custom_channel_name
                    header_length += get_qstring_length(data, header_length)
                header_length += 12 + 8 + 8
    return header_length


def read_header(filename):
    with open(filename, 'rb') as f:

        with contextlib.closing(mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ)) as data:

            header = {}
            freq = {}

            version = np.fromstring(data[4:8], dtype='<h')  # (version major, version minor)

            header['version'] = version

            header['sample_rate'] = np.fromstring(data[8:12], dtype='<f')[0]

            notch_filter_mode, = np.fromstring(data[38:40], dtype='<h')

            if notch_filter_mode == 1:
                header['notch_filter_frequency'] = 50
            elif notch_filter_mode == 2:
                header['notch_filter_frequency'] = 60
            elif notch_filter_mode == 0:
                header['notch_filter_frequency'] = 0

            freq['notch_filter_frequency'] = header['notch_filter_frequency']
            freq['amplifier_sample_rate'] = header['sample_rate']
            header['frequency_parameters'] = freq

            notes = {}
            note_start = 48
            for i in range(1, 4):
                notes['note%d' % i], qstring_length = get_qstring(data, note_start)
                note_start += qstring_length

            header['notes'] = notes

            if (version[0] == 1 and version[1] >= 6) or (version[0] > 1):
                settings_filename, qstring_length = get_qstring(data, note_start)
                note_start += qstring_length
            else:
                settings_filename = ''

            header['settings_filename'] = settings_filename

            header_offset = note_start

            # if data file is from GUI v1.1 or later, see if temp sensor was saved
            if version[0] == 1 and version[1] >= 1 or version[0] > 1:
                header['num_temp_sensor_channels'] = np.fromstring(data[header_offset:header_offset + 2], dtype='<h')[0]
                header_offset += 2

            # if data file is from GUI v1.3 or later, load eval board mode
            header['eval_board_mode'] = 0
            if version[0] == 1 and version[1] >= 3 or version[0] > 1:
                header['eval_board_mode'] = np.fromstring(data[header_offset:header_offset + 2], dtype='<h')[0]
                header_offset += 2

            header['num_samples_per_data_block'] = 60
            # If data file is from v2.0 or later (Intan Recording Controller), load name of digital reference channel
            if version[0] > 1:
                reference_channel, qstring_length = get_qstring(data, header_offset)
                header['reference_channel'] = reference_channel
                header['num_samples_per_data_block'] = 128
                header_offset += qstring_length

            # get the qstrings for
            number_of_signal_groups = np.fromstring(data[header_offset:header_offset + 2], dtype='<h')[0]

            header_offset += 2

            header['spike_triggers'] = []
            header['num_amplifier_channels'] = 0
            header['num_aux_input_channels'] = 0
            header['num_supply_voltage_channels'] = 0
            header['num_board_adc_channels'] = 0
            header['num_board_dig_in_channels'] = 0
            header['num_board_dig_out_channels'] = 0
            header['amplifier_channels'] = []
            header['aux_input_channels'] = []
            header['supply_voltage_channels'] = []
            header['board_adc_channels'] = []
            header['board_dig_in_channels'] = []
            header['board_dig_out_channels'] = []

            for signal_group in np.arange(number_of_signal_groups):
                # qstring_start = header_length
                for i in range(2):
                    # once for signal group name, once for group prefix
                    header_offset += get_qstring_length(data, header_offset)

                signal_values = np.fromstring(data[header_offset:header_offset + 6], dtype='<h')

                header_offset += 6

                if signal_values[1] > 0 and signal_values[0] > 0:
                    for signal_channel in np.arange(signal_values[1]):
                        new_channel = {}

                        # once for native_channel_name, once for custom_channel_name
                        new_channel['native_channel_name'], qstring_length = get_qstring(data, header_offset)
                        header_offset += qstring_length

                        new_channel['custom_channel_name'], qstring_length = get_qstring(data, header_offset)
                        header_offset += qstring_length

                        values = np.fromstring(data[header_offset:header_offset + 12], dtype='<h')
                        header_offset += 12
                        trigger_values = np.fromstring(data[header_offset:header_offset + 8], dtype='<h')

                        new_trigger_channel = {'voltage_trigger_mode': trigger_values[0],
                                               'voltage_threshold': trigger_values[1],
                                               'digital_trigger_channel': trigger_values[2],
                                               'digital_edge_polarity': trigger_values[3]}

                        new_channel['native_order'] = values[0]
                        new_channel['custom_order'] = values[1]

                        signal_type = values[2]
                        channel_enabled = values[3]

                        if channel_enabled:
                            if signal_type == 0:
                                header['amplifier_channels'].append(new_channel)
                                header['num_amplifier_channels'] += 1
                                header['spike_triggers'].append(new_trigger_channel)
                            elif signal_type == 1:
                                header['aux_input_channels'].append(new_channel)
                                header['num_aux_input_channels'] += 1
                            elif signal_type == 2:
                                header['supply_voltage_channels'].append(new_channel)
                                header['num_supply_voltage_channels'] += 1
                            elif signal_type == 3:
                                header['board_adc_channels'].append(new_channel)
                                header['num_board_adc_channels'] += 1
                            elif signal_type == 4:
                                header['board_dig_in_channels'].append(new_channel)
                                header['num_board_dig_in_channels'] += 1
                            elif signal_type == 5:
                                header['board_dig_out_channels'].append(new_channel)
                                header['num_board_dig_out_channels'] += 1
                            else:
                                raise Exception('Unknown channel type.')

                        header_offset += 8 + 8

    return header


def rhd_duration(filename):
    header = read_header(filename)

    # Determine how many samples the data file contains.
    bytes_per_block = get_bytes_per_data_block(header)

    # How many data blocks remain in this file?

    with open(filename, 'rb') as f:
        with contextlib.closing(mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ)) as m:
            header_length = get_header_length(m)
            bytes_remaining = len(m) - header_length
            m = None

    if bytes_remaining % bytes_per_block != 0:
        raise Exception('Something is wrong with file size : should have a whole number of data blocks')

    num_data_blocks = int(bytes_remaining / bytes_per_block)

    num_amplifier_samples = header['num_samples_per_data_block'] * num_data_blocks

    return num_amplifier_samples / header['sample_rate']


def get_probe_name(filename, default_probe='axona16_new'):
    """We save the probe name as the settings filename so we know how to map each probe"""

    probe = read_header(filename)['settings_filename']
    if probe == '':
        # there was a time before we had this ability and we just used the axona16_new probe
        return default_probe
    else:
        return probe


def get_total_num_data_blocks(session_files):
    total_num_data_blocks = 0
    for filename in session_files:
        with open(filename, 'rb') as f:
            with contextlib.closing(mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ)) as m:
                header_length = get_header_length(m)

                header = read_header(filename)  # could probably combine these two functions

                bytes_per_block = get_bytes_per_data_block(header)

                bytes_remaining = len(m) - header_length

                if bytes_remaining % bytes_per_block != 0:
                    raise Exception('Something is wrong with file size : should have a whole number of data blocks')

                num_data_blocks = int(bytes_remaining / bytes_per_block)
        total_num_data_blocks += num_data_blocks

    return total_num_data_blocks


def get_num_data_blocks(filename):
    with open(filename, 'rb') as f:
        with contextlib.closing(mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ)) as m:
            header_length = get_header_length(m)

            header = read_header(filename)  # could probably combine these two functions

            bytes_per_block = get_bytes_per_data_block(header)

            bytes_remaining = len(m) - header_length

            if bytes_remaining % bytes_per_block != 0:
                raise Exception('Something is wrong with file size : should have a whole number of data blocks')

            num_data_blocks = int(bytes_remaining / bytes_per_block)

    return num_data_blocks


def read_data(filename, include_ephys=True, include_analog=True, include_digital=True):
    with open(filename, 'rb') as f:

        with contextlib.closing(mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ)) as m:

            header_length = get_header_length(m)

            header = read_header(filename)  # could probably combine these two functions

            bytes_per_block = get_bytes_per_data_block(header)

            bytes_remaining = len(m) - header_length

            data_present = False

            if bytes_remaining > 0:
                data_present = True

            if bytes_remaining % bytes_per_block != 0:
                raise Exception('Something is wrong with file size : should have a whole number of data blocks')

            num_data_blocks = int(bytes_remaining / bytes_per_block)

            num_amplifier_samples = header['num_samples_per_data_block'] * num_data_blocks
            num_board_adc_samples = header['num_samples_per_data_block'] * num_data_blocks
            num_board_dig_in_samples = header['num_samples_per_data_block'] * num_data_blocks

            # calculate how many bytes per block so we can skip unnecessary data
            data_stride = 4 * header['num_samples_per_data_block']  # offset from the t_amplifier
            if header['num_amplifier_channels'] > 0:
                # num_samples_per_data_block values x X channels x 2 bytes, offset from amplifier_data
                data_stride += 2 * header['num_samples_per_data_block'] * header['num_amplifier_channels']

            if header['num_aux_input_channels'] > 0:
                # offset from aux_input_data
                data_stride += 2 * int(header['num_samples_per_data_block'] / 4) * header['num_aux_input_channels']

            if header['num_supply_voltage_channels'] > 0:
                # offset from supply_voltage_data
                data_stride += 2 * header['num_supply_voltage_channels']

            if header['num_temp_sensor_channels'] > 0:
                # offset from temp_sensor_data
                data_stride += 2 * header['num_temp_sensor_channels']

            if header['num_board_adc_channels'] > 0:
                # offset from board_adc_data
                data_stride += 2 * header['num_samples_per_data_block'] * header['num_board_adc_channels']

            if header['num_board_dig_in_channels'] > 0:
                # offset from board_dig_in_raw
                data_stride += 2 * header['num_samples_per_data_block']

            if header['num_board_dig_out_channels'] > 0:
                # offset from board_dig_out_raw
                data_stride += 2 * header['num_samples_per_data_block']

            if data_present:
                data = {}

                data['frequency_parameters'] = header['frequency_parameters']

                data['amplifier_data'] = np.zeros([header['num_amplifier_channels'], num_amplifier_samples],
                                                  dtype=np.uint)
                if include_digital and header['num_board_dig_in_channels'] > 0 and num_board_dig_in_samples > 0:
                    data['board_dig_in_data'] = np.zeros([header['num_board_dig_in_channels'],
                                                          num_board_dig_in_samples],
                                                         dtype=np.uint)

                    data['board_dig_in_raw'] = np.zeros(num_board_dig_in_samples,
                                                        dtype=np.uint)

                if include_analog and header['num_board_adc_channels'] > 0 and num_board_adc_samples > 0:
                    data['board_adc_data'] = np.zeros([header['num_board_adc_channels'], num_board_adc_samples],
                                                        dtype=np.uint16)

                if (header['version'][0] == 1 and header['version'][1] >= 2) or (header['version'][0] > 1):
                    data['t_amplifier'] = np.ndarray((num_data_blocks,),
                                                     ('<i', (1, header['num_samples_per_data_block'])),
                                                     m, header_length,
                                                     (data_stride,)).flatten()

                else:
                    data['t_amplifier'] = np.ndarray((num_data_blocks,),
                                                     ('<I', (1, header['num_samples_per_data_block'])), m,
                                                     header_length,
                                                     (data_stride,)).flatten()

                # we will read the amplifier data by reading the 60 values per block per channel, starting at
                # a given offset , and then repeating every data_stride

                data_values = np.ndarray((num_data_blocks,),
                                         (np.uint16, (header['num_amplifier_channels'],
                                                      header['num_samples_per_data_block'])),
                                         m, get_offset(header, header_length, 'amplifier_data'),
                                         (data_stride,))
                if include_ephys:
                    for i in range(header['num_amplifier_channels']):
                        data['amplifier_data'][i, :] = data_values[:, i, :].reshape((1, -1))
                    data_values = None

                if include_digital and header['num_board_dig_in_channels'] > 0:
                    if num_board_dig_in_samples > 0:
                        data['board_dig_in_raw'] = np.ndarray((num_data_blocks,),
                                                              ('<H', (1, header['num_samples_per_data_block'])),
                                                              m, get_offset(header, header_length,
                                                                            'board_dig_in_raw'),
                                                              (data_stride,)).flatten()

                    for i in range(header['num_board_dig_in_channels']):
                        data['board_dig_in_data'][i, :] = np.not_equal(
                            np.bitwise_and(data['board_dig_in_raw'],
                                           (1 << header['board_dig_in_channels'][i]['native_order'])), 0)

                        # remove the board_dig_in_raw since we no longer need it
                    data.pop('board_dig_in_raw', None)

                if include_analog and header['num_board_adc_channels'] > 0 and num_board_adc_samples > 0:
                    data_values = np.ndarray((num_data_blocks,), (np.uint16, (header['num_board_adc_channels'],
                                                                              header['num_samples_per_data_block'])),
                                             m, get_offset(header, header_length, 'board_adc_data'), (data_stride,))

                    for i in range(header['num_board_adc_channels']):
                        data['board_adc_data'][i, :] = data_values[:, i, :].reshape((1, -1))

                    data_values = None

                m = None

                # convert from unsigned to signed
                data['amplifier_data'] = data['amplifier_data'].astype(np.int32) - 32768  # bits

                if include_analog and header['num_board_adc_channels'] > 0 and num_board_adc_samples > 0:
                    data['board_adc_data'] = data['board_adc_data'].astype(np.int32) - 32768  # bits

                # convert from sample number to time (in seconds)
                data['t_amplifier'] = data['t_amplifier'] / header['sample_rate']

    return data


def get_analog_scalar(session_files):
    file_header = read_header(session_files[0])
    if file_header['eval_board_mode'] == 1:
        scalar = 152.59e-6
    elif file_header['eval_board_mode'] == 13:
        scalar = 312.5e-6
    return scalar


def get_offset(header, header_length, output):
    offset = header_length

    if output == 'amplifier_data':
        offset = header_length + 4 * header['num_samples_per_data_block']

    elif output == 'board_dig_in_raw':
        offset = header_length + 4 * header['num_samples_per_data_block'] + \
                 2 * header['num_samples_per_data_block'] * header['num_amplifier_channels'] + \
                 2 * int(header['num_samples_per_data_block'] / 4) * header['num_aux_input_channels'] + \
                 2 * header['num_supply_voltage_channels'] + \
                 2 * header['num_temp_sensor_channels'] + \
                 2 * header['num_samples_per_data_block'] * header['num_board_adc_channels']

    elif output == 'board_adc_data':
        offset = header_length + 4 * header['num_samples_per_data_block'] + \
                 2 * header['num_samples_per_data_block'] * header['num_amplifier_channels'] + \
                 2 * int(header['num_samples_per_data_block'] / 4) * header['num_aux_input_channels'] + \
                 2 * header['num_supply_voltage_channels'] + \
                 2 * header['num_temp_sensor_channels']

    return offset


def get_cue_json_parameter(directory, tint_basename, parameter):
    cues_filename = os.path.join(directory, '%s_cues.json' % tint_basename)

    if os.path.exists(cues_filename):
        with open(cues_filename, 'r') as f:
            values = json.load(f)
        if parameter in list(values.keys()):
            try:
                # this is a legacy, should be a string instead of an integer, but this is just to keep it c
                # compatible with old code
                parameter_value = int(values[parameter])
            except ValueError:
                parameter_value = values[parameter]
        else:
            return None

    else:
        return None

    return parameter_value


def get_data_limits(directory, tint_basename, data_digital_in, data_analog_in, self=None, default_start_stop_pin='0D',
                    minimum_analog_value=3):
    """
    This will get the beginning and end indices of the data defined by when digital channel used to deliver the start
    and stop signal is set to high.

    :param directory: the directory name of the file you want to get the limits of 'C:\\example\\'
    :param tint_basename: the tint basename of file that was used to produced the '*_cues.json' file.
    :param data_digital_in: the digital input data
    :param self: the self variable for the GUI (if used by a GUI)
    :param default_start_stop_pin:
    :return:
    """
    # default_start_stop_pin = 0

    Analog = False
    Digital = False

    start_stop_pin = get_cue_json_parameter(directory, tint_basename, 'Start/Stop Input:')
    if start_stop_pin is None:
        start_stop_pin = get_cue_json_parameter(directory, tint_basename, 'Start/Stop Digital Input:')

    if start_stop_pin is None:
        start_stop_pin = default_start_stop_pin

    if type(start_stop_pin) == str:
        if 'A' in start_stop_pin:
            Analog = True
        elif 'D' in start_stop_pin:
            Digital = True
        start_stop_pin = int(start_stop_pin[:-1])
    elif type(start_stop_pin) == int:
        # then it is the old version where everything was on digital, set digital to true
        Digital = True

    start_stop_index = None
    if Digital:
        start_stop_index = detect_peaks(data_digital_in[start_stop_pin, :], mpd=1, mph=0, threshold=0)
    elif Analog:
        # we will convert the data to volts in this case, and use the output voltage from the raspberry pi
        # (minimum analog_value) as the minimum height (we went slightly below the 3.3 value and just did 3 to keep
        # it safe.
        # we will convert the data to volts in this case, and use the output voltage from the raspberry pi
        # (minimum analog_value) as the minimum height (we went slightly below the 3.3 value and just did 3 to keep
        # it safe. In this I have also clipped the data at 3 because it is analog which means it can take on more
        # numbers than just 0 and 1, and thus you would get many values being considered "peaks" when it should really
        # just be the 1 index that it reaches the theoretical 3.3V.
        session_files = [os.path.join(directory, tint_basename + '.rhd')]
        analog_scalar = get_analog_scalar(session_files)
        data_analog_in = np.multiply(analog_scalar, data_analog_in[start_stop_pin, :])
        data_analog_in[np.where(data_analog_in >= minimum_analog_value)[0]] = minimum_analog_value
        start_stop_index = detect_peaks(data_analog_in, mpd=1, mph=minimum_analog_value, threshold=0)

    if len(start_stop_index) > 2:
        # This is odd but I have seen a few indices where the start/stop had the correct start/stop signal, but
        # also received a few of the other signals as well across its channel. Not entirely sure why. We will just
        # return the first and last of the peaks

        msg = '[%s %s]: Start/Stop indices have larger length than expected!#red' % (str(datetime.datetime.now().date()),
                                                                            str(datetime.datetime.now().time())[
                                                                            :8])
        if self is None:
            print(msg)
        else:
            self.Log.append(msg)
        return start_stop_index[0], start_stop_index[-1]

    elif len(start_stop_index) < 2:
        # For some reason it is missing one or both the signals.

        msg = '[%s %s]: No Start/Stop indices found! Will use latest digital signal as end.#red' % (
            str(datetime.datetime.now().date()), str(datetime.datetime.now().time())[:8])
        if self is None:
            print(msg)
        else:
            self.Log.append(msg)

        # find the latest digital signal from any of the other channels to use as the end.
        peak_indices = []
        for channel in data_digital_in:
            peak_indices += detect_peaks(channel, mpd=1, mph=0, threshold=0).tolist()
        peak_indices = np.asarray(peak_indices)

        if len(peak_indices) < 2:
            return None, None
        else:
            return np.amin(peak_indices), np.amax(peak_indices)

    return start_stop_index[0], start_stop_index[1]


def get_reward_indices(directory, tint_basename, data_digital_in, data_analog_in, start_index, default_reward_pin='0A',
                       minimum_analog_value=3):

    # default_reward_pin = 2
    Analog = False
    Digital = False

    reward_pin = get_cue_json_parameter(directory, tint_basename, 'Reward Input:')
    if reward_pin is None:
        # Reward Digital Input: was the legacy value, was changed
        reward_pin = get_cue_json_parameter(directory, tint_basename, 'Reward Digital Input:')
    if reward_pin is None:
        # then just use the default
        reward_pin = default_reward_pin

    if type(reward_pin) == str:
        if 'A' in reward_pin:
            Analog = True
        elif 'D' in reward_pin:
            Digital = True
        reward_pin = int(reward_pin[:-1])
    elif type(reward_pin) == int:
        # then it is the old version where everything was on digital, set digital to true
        Digital = True

    reward_indices = None
    if Digital:
        # we will offset by the start_index
        reward_indices = detect_peaks(data_digital_in[reward_pin, :], mpd=1, mph=0, threshold=0) - start_index
    elif Analog:
        # we will convert the data to volts in this case, and use the output voltage from the raspberry pi
        # (minimum analog_value) as the minimum height (we went slightly below the 3.3 value and just did 3 to keep
        # it safe.
        # we will convert the data to volts in this case, and use the output voltage from the raspberry pi
        # (minimum analog_value) as the minimum height (we went slightly below the 3.3 value and just did 3 to keep
        # it safe. In this I have also clipped the data at 3 because it is analog which means it can take on more
        # numbers than just 0 and 1, and thus you would get many values being considered "peaks" when it should really
        # just be the 1 index that it reaches the theoretical 3.3V.
        session_files = [os.path.join(directory, tint_basename + '.rhd')]
        analog_scalar = get_analog_scalar(session_files)
        data_analog_in = np.multiply(analog_scalar, data_analog_in[reward_pin, :])
        data_analog_in[np.where(data_analog_in >= minimum_analog_value)[0]] = minimum_analog_value
        reward_indices = detect_peaks(data_analog_in, mpd=1, mph=minimum_analog_value, threshold=0) - start_index

    return reward_indices


def get_lap_indices(directory, tint_basename, data_digital_in, data_analog_in, start_index, default_lap_pin='1D',
                    minimum_analog_value=3):

    # default_lap_pin = 1

    Analog = False
    Digital = False

    lap_pin = get_cue_json_parameter(directory, tint_basename, 'Lap Input:')
    if lap_pin is None:
        # Lap Digital Input: was the legacy value, was changed
        lap_pin = get_cue_json_parameter(directory, tint_basename, 'Lap Digital Input:')
    if lap_pin is None:
        lap_pin = default_lap_pin

    if type(lap_pin) == str:
        if 'A' in lap_pin:
            Analog = True
        elif 'D' in lap_pin:
            Digital = True
        lap_pin = int(lap_pin[:-1])
    elif type(lap_pin) == int:
        # then it is the old version where everything was on digital, set digital to true
        Digital = True

    lap_indices = None
    if Digital:
        # we will offset by the start_index
        lap_indices = detect_peaks(data_digital_in[lap_pin, :], mpd=1, mph=0, threshold=0) - start_index
    elif Analog:
        # we will convert the data to volts in this case, and use the output voltage from the raspberry pi
        # (minimum analog_value) as the minimum height (we went slightly below the 3.3 value and just did 3 to keep
        # it safe.
        # we will convert the data to volts in this case, and use the output voltage from the raspberry pi
        # (minimum analog_value) as the minimum height (we went slightly below the 3.3 value and just did 3 to keep
        # it safe. In this I have also clipped the data at 3 because it is analog which means it can take on more
        # numbers than just 0 and 1, and thus you would get many values being considered "peaks" when it should really
        # just be the 1 index that it reaches the theoretical 3.3V.
        session_files = [os.path.join(directory, tint_basename + '.rhd')]
        analog_scalar = get_analog_scalar(session_files)
        data_analog_in = np.multiply(analog_scalar, data_analog_in[lap_pin, :])
        data_analog_in[np.where(data_analog_in >= minimum_analog_value)[0]] = minimum_analog_value
        lap_indices = detect_peaks(data_analog_in, mpd=1, mph=minimum_analog_value, threshold=0) - start_index

    return lap_indices


def get_signal_events(directory, tint_basename, parameter_name, data_digital_in, data_analog_in, start_index,
                      default_pin='0D', minimum_analog_value=3):
    """
    from now one we will gather custom signal event times using this function, the rest of the functions are legacy
    and I'll leave them
    """

    Analog = False
    Digital = False

    pin = get_cue_json_parameter(directory, tint_basename, parameter_name)
    if pin is None:
        pin = default_pin

    if type(pin) == str:
        if 'A' in pin:
            Analog = True
        elif 'D' in pin:
            Digital = True
        pin = int(pin[:-1])
    elif type(pin) == int:
        # then it is the old version where everything was on digital, set digital to true
        Digital = True

    event_indices = None
    if Digital:
        # we will offset by the start_index
        event_indices = detect_peaks(data_digital_in[pin, :], mpd=1, mph=0, threshold=0) - start_index
    elif Analog:
        # we will convert the data to volts in this case, and use the output voltage from the raspberry pi
        # (minimum analog_value) as the minimum height (we went slightly below the 3.3 value and just did 3 to keep
        # it safe. In this I have also clipped the data at 3 because it is analog which means it can take on more
        # numbers than just 0 and 1, and thus you would get many values being considered "peaks" when it should really
        # just be the 1 index that it reaches the theoretical 3.3V.
        session_files = [os.path.join(directory, tint_basename + '.rhd')]
        analog_scalar = get_analog_scalar(session_files)
        data_analog_in = np.multiply(analog_scalar, data_analog_in[pin, :])
        data_analog_in[np.where(data_analog_in >= minimum_analog_value)[0]] = minimum_analog_value
        event_indices = detect_peaks(data_analog_in, mpd=1, mph=minimum_analog_value, threshold=0) - start_index

    return event_indices


def detect_peaks(x, mph=None, mpd=1, threshold=0, edge='rising',
                 kpsh=False, valley=False, show=False, ax=None):
    __author__ = "Marcos Duarte, https://github.com/demotu/BMC"
    __version__ = "1.0.4"
    __license__ = "MIT"

    """Detect peaks in data based on their amplitude and other features.

    Parameters
    ----------
    x : 1D array_like
        data.
    mph : {None, number}, optional (default = None)
        detect peaks that are greater than minimum peak height.
    mpd : positive integer, optional (default = 1)
        detect peaks that are at least separated by minimum peak distance (in
        number of data).
    threshold : positive number, optional (default = 0)
        detect peaks (valleys) that are greater (smaller) than `threshold`
        in relation to their immediate neighbors.
    edge : {None, 'rising', 'falling', 'both'}, optional (default = 'rising')
        for a flat peak, keep only the rising edge ('rising'), only the
        falling edge ('falling'), both edges ('both'), or don't detect a
        flat peak (None).
    kpsh : bool, optional (default = False)
        keep peaks with same height even if they are closer than `mpd`.
    valley : bool, optional (default = False)
        if True (1), detect valleys (local minima) instead of peaks.
    show : bool, optional (default = False)
        if True (1), plot data in matplotlib figure.
    ax : a matplotlib.axes.Axes instance, optional (default = None).

    Returns
    -------
    ind : 1D array_like
        indeces of the peaks in `x`.

    Notes
    -----
    The detection of valleys instead of peaks is performed internally by simply
    negating the data: `ind_valleys = detect_peaks(-x)`

    The function can handle NaN's

    See this IPython Notebook [1]_.

    References
    ----------
    .. [1] http://nbviewer.ipython.org/github/demotu/BMC/blob/master/notebooks/DetectPeaks.ipynb

    Examples
    --------
    >>> from detect_peaks import detect_peaks
    >>> x = np.random.randn(100)
    >>> x[60:81] = np.nan
    >>> # detect all peaks and plot data
    >>> ind = detect_peaks(x, show=True)
    >>> print(ind)

    >>> x = np.sin(2*np.pi*5*np.linspace(0, 1, 200)) + np.random.randn(200)/5
    >>> # set minimum peak height = 0 and minimum peak distance = 20
    >>> detect_peaks(x, mph=0, mpd=20, show=True)

    >>> x = [0, 1, 0, 2, 0, 3, 0, 2, 0, 1, 0]
    >>> # set minimum peak distance = 2
    >>> detect_peaks(x, mpd=2, show=True)

    >>> x = np.sin(2*np.pi*5*np.linspace(0, 1, 200)) + np.random.randn(200)/5
    >>> # detection of valleys instead of peaks
    >>> detect_peaks(x, mph=0, mpd=20, valley=True, show=True)

    >>> x = [0, 1, 1, 0, 1, 1, 0]
    >>> # detect both edges
    >>> detect_peaks(x, edge='both', show=True)

    >>> x = [-2, 1, -2, 2, 1, 1, 3, 0]
    >>> # set threshold = 2
    >>> detect_peaks(x, threshold = 2, show=True)
    """

    x = np.atleast_1d(x).astype('float64')
    if x.size < 3:
        return np.array([], dtype=int)
    if valley:
        x = -x
    # find indices of all peaks
    dx = x[1:] - x[:-1]
    # handle NaN's
    indnan = np.where(np.isnan(x))[0]
    if indnan.size:
        x[indnan] = np.inf
        dx[np.where(np.isnan(dx))[0]] = np.inf
    ine, ire, ife = np.array([[], [], []], dtype=int)
    if not edge:
        ine = np.where((np.hstack((dx, 0)) < 0) & (np.hstack((0, dx)) > 0))[0]
    else:
        if edge.lower() in ['rising', 'both']:
            ire = np.where((np.hstack((dx, 0)) <= 0) & (np.hstack((0, dx)) > 0))[0]
        if edge.lower() in ['falling', 'both']:
            ife = np.where((np.hstack((dx, 0)) < 0) & (np.hstack((0, dx)) >= 0))[0]
    ind = np.unique(np.hstack((ine, ire, ife)))
    # handle NaN's
    if ind.size and indnan.size:
        # NaN's and values close to NaN's cannot be peaks
        ind = ind[np.in1d(ind, np.unique(np.hstack((indnan, indnan - 1, indnan + 1))), invert=True)]
    # first and last values of x cannot be peaks
    if ind.size and ind[0] == 0:
        ind = ind[1:]
    if ind.size and ind[-1] == x.size - 1:
        ind = ind[:-1]
    # remove peaks < minimum peak height
    if ind.size and mph is not None:
        ind = ind[x[ind] >= mph]
    # remove peaks - neighbors < threshold
    if ind.size and threshold > 0:
        dx = np.min(np.vstack([x[ind] - x[ind - 1], x[ind] - x[ind + 1]]), axis=0)
        ind = np.delete(ind, np.where(dx < threshold)[0])
    # detect small peaks closer than minimum peak distance
    if ind.size and mpd > 1:
        ind = ind[np.argsort(x[ind])][::-1]  # sort ind by peak height
        idel = np.zeros(ind.size, dtype=bool)
        for i in range(ind.size):
            if not idel[i]:
                # keep peaks with the same height if kpsh is True
                idel = idel | (ind >= ind[i] - mpd) & (ind <= ind[i] + mpd) \
                              & (x[ind[i]] > x[ind] if kpsh else True)
                idel[i] = 0  # Keep current peak
        # remove the small peaks and sort back the indices by their occurrence
        ind = np.sort(ind[~idel])

    if show:
        if indnan.size:
            x[indnan] = np.nan
        if valley:
            x = -x
        _plot(x, mph, mpd, threshold, edge, valley, ax, ind)

    return ind


def _plot(x, mph, mpd, threshold, edge, valley, ax, ind):
    """Plot results of the detect_peaks function, see its help."""
    try:
        import matplotlib.pyplot as plt
    except ImportError:
        print('matplotlib is not available.')
    else:
        if ax is None:
            _, ax = plt.subplots(1, 1, figsize=(8, 4))

        ax.plot(x, 'b', lw=1)
        if ind.size:
            label = 'valley' if valley else 'peak'
            label = label + 's' if ind.size > 1 else label
            ax.plot(ind, x[ind], '+', mfc=None, mec='r', mew=2, ms=8,
                    label='%d %s' % (ind.size, label))
            ax.legend(loc='best', framealpha=.5, numpoints=1)
        ax.set_xlim(-.02 * x.size, x.size * 1.02 - 1)
        ymin, ymax = x[np.isfinite(x)].min(), x[np.isfinite(x)].max()
        yrange = ymax - ymin if ymax > ymin else 1
        ax.set_ylim(ymin - 0.1 * yrange, ymax + 0.1 * yrange)
        ax.set_xlabel('Data #', fontsize=14)
        ax.set_ylabel('Amplitude', fontsize=14)
        mode = 'Valley detection' if valley else 'Peak detection'
        ax.set_title("%s (mph=%s, mpd=%d, threshold=%s, edge='%s')"
                     % (mode, str(mph), mpd, str(threshold), edge))
        # plt.grid()
        plt.show()


def find_consec(data):
    """finds the consecutive numbers and outputs as a list"""
    consecutive_values = []  # a list for the output
    current_consecutive = [data[0]]

    if len(data) == 1:
        return [[data[0]]]

    for index in range(1, len(data)):

        if data[index] == data[index - 1] + 1:
            current_consecutive.append(data[index])

            if index == len(data) - 1:
                consecutive_values.append(current_consecutive)

        else:
            consecutive_values.append(current_consecutive)
            current_consecutive = [data[index]]

            if index == len(data) - 1:
                consecutive_values.append(current_consecutive)
    return consecutive_values


def find_basename_files_old(basename, directory):
    """
    This is the old version of the function, it had an issue when one file was missing from the sessions I decided to
    change the method.

    This function will find all the files belonging to a basename within a specified folder. It will do this by
    finding where the t=0 values are (the starting files) to separate the list into the respective sessions if there
    are multiple sessions with the same base name."""
    rhd_sessions = []

    directory_file_list = os.listdir(directory)  # making a list of all files within the specified directory

    basename_files = [os.path.join(directory, file) for file in directory_file_list
                      if (basename in file[:len(basename)] and '.rhd' in file and
                          len(file[len(basename):]) == 18) and
                      file not in (session_file for session in rhd_sessions for session_file in session)]

    if len(basename_files) == 1:
        # there was only one related .rhd file
        if basename_files not in (session_file for session in rhd_sessions for session_file in session):
            rhd_sessions.append([basename_files[0]])
            return rhd_sessions

    else:

        session_beginning = [is_session_beginning(file) for file in sorted(basename_files, reverse=True)]
        session_beginning = np.asarray(session_beginning).astype(int)

        zero_bool = np.where(session_beginning == 0)[0]
        if len(zero_bool) != 0:
            zero_bool_consec = find_consec(zero_bool)

            for current_session in zero_bool_consec:
                # we have all the files in this session besides the start so we have to append that value
                current_session.append(current_session[-1] + 1)

                current_session = (np.asarray(sorted(basename_files, reverse=True))[current_session]).tolist()

                if current_session not in rhd_sessions:
                    rhd_sessions.append(current_session)

        else:
            # this means that all the sessions belong to their own session, and there are not more than 1 file
            # for each of these sessions so we will just leave it because later in the code we add the single file
            # sessions
            pass

        for file in sorted(basename_files, reverse=True):
            # adds the recordings sessions that don't have multiple .rhd files
            if file not in (session_file for session in rhd_sessions for session_file in session):
                # the files are single file recordings that have not been added yet
                rhd_sessions.append([file])

    return rhd_sessions


def find_basename_files(basename, directory):
    """
    This function will find all the files belonging to a basename within a specified folder. It will do this
    by finding all the files with the same intan basename, looking at the start and stop times of the data within
    these files and stringing together the consecutive files.
    """
    rhd_sessions = []

    directory_file_list = os.listdir(directory)  # making a list of all files within the specified directory

    basename_files = [os.path.join(directory, file) for file in directory_file_list
                      if (basename in file[:len(basename)] and '.rhd' in file and
                          len(file[len(basename):]) == 18) and
                      file not in (session_file for session in rhd_sessions for session_file in session)]

    if len(basename_files) == 1:
        # there was only one related .rhd file
        if basename_files not in (session_file for session in rhd_sessions for session_file in session):
            rhd_sessions.append([basename_files[0]])
            return rhd_sessions

    else:
        rhd_sessions = []
        current_session = []
        previous_end = None
        for i, file in enumerate(sorted(basename_files, reverse=False)):
            fstart, fstop = get_time_boundaries(file)
            if i == 0:
                current_session.append(file)
                previous_end = fstop
                continue

            if fstart - previous_end == 1:
                # then it is a continuation of the current session
                current_session.append(file)
            else:
                # this is the beginning of a different session
                rhd_sessions.append(sorted(current_session, reverse=True))
                # rhd_sessions.append(current_session)
                current_session = [file]
            previous_end = fstop

        if current_session not in rhd_sessions:
            rhd_sessions.append(sorted(current_session, reverse=True))
            # rhd_sessions.append(current_session)

    return rhd_sessions


def session_datetime(file, output='datetime'):
    """Getting the Trial Date and Time value for the .set file"""

    file = os.path.splitext(os.path.basename(file))[0]
    date, time = (file[find_sub(file, '_')[-2] + 1:]).split('_')

    date = datetime.datetime.strptime(str(date), '%y%m%d')
    time = datetime.datetime.strptime(str(time), '%H%M%S')
    if output == 'datetime':
        date = date.strftime("%A, %d %b %Y")
        time = time.strftime("%H:%M:%S")

        return date, time

    elif output == 'seconds':
        # returns seconds since epoc
        date = str(date)
        date = date[:date.find(' ')]
        time = str(time)
        time = time[time.find(' ') + 1:]

        seconds = (datetime.datetime.strptime('%s %s' % (str(date), str(time)),
                                              '%Y-%m-%d %H:%M:%S') - datetime.datetime(1970, 1, 1)).total_seconds()
        return seconds


def is_session_beginning(filename):
    """This function will return true if the file is the beginning of the experiment (starts with a timepoint of 0)
    otherwise it will return false."""
    with open(filename, 'rb') as f:
        with contextlib.closing(mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ)) as m:
            header_length = get_header_length(m)

            header = read_header(filename)  # could probably combine these two functions

            bytes_per_block = get_bytes_per_data_block(header)

            bytes_remaining = len(m) - header_length

            if bytes_remaining % bytes_per_block != 0:
                raise Exception('Something is wrong with file size : should have a whole number of data blocks')

            # calculate how many bytes per block so we can skip unnecessary data
            data_stride = 4 * header['num_samples_per_data_block']  # offset from the t_amplifier
            if header['num_amplifier_channels'] > 0:
                # 60 values x X channels x 2 bytes
                data_stride += 2 * header['num_samples_per_data_block'] * header['num_amplifier_channels']

            if header['num_aux_input_channels'] > 0:
                data_stride += 2 * int(header['num_samples_per_data_block'] / 4) * header['num_aux_input_channels']

            if header['num_supply_voltage_channels'] > 0:
                data_stride += 2 * header['num_supply_voltage_channels']

            if header['num_temp_sensor_channels'] > 0:
                data_stride += 2 * header['num_temp_sensor_channels']

            if header['num_board_adc_channels'] > 0:
                data_stride += 2 * header['num_samples_per_data_block'] * header['num_board_adc_channels']

            if header['num_board_dig_in_channels'] > 0:
                data_stride += 2 * header['num_samples_per_data_block']

            if header['num_board_dig_out_channels'] > 0:
                data_stride += 2 * header['num_samples_per_data_block']

            if (header['version'][0] == 1 and header['version'][1] >= 2) or (header['version'][0] > 1):
                data = np.ndarray((1,), ('<i', (1, 1)), m, header_length, (data_stride,)).flatten()
            else:
                data = np.ndarray((1,), ('<I', (1, 1)), m, header_length, (data_stride,)).flatten()

            if data[0] == 0:
                return True
            return False


def get_time_boundaries(filename):
    """
    This function will return the beginning and end time point of the session.
    :param filename:
    :return:
    """
    with open(filename, 'rb') as f:
        with contextlib.closing(mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ)) as m:
            header_length = get_header_length(m)

            header = read_header(filename)  # could probably combine these two functions

            bytes_per_block = get_bytes_per_data_block(header)

            bytes_remaining = len(m) - header_length

            if bytes_remaining % bytes_per_block != 0:
                raise Exception('Something is wrong with file size : should have a whole number of data blocks')

            num_data_blocks = int(bytes_remaining / bytes_per_block)

            # calculate how many bytes per block so we can skip unnecessary data
            data_stride = 4 * header['num_samples_per_data_block']  # offset from the t_amplifier
            if header['num_amplifier_channels'] > 0:
                # 60 values x X channels x 2 bytes, offset from amplifier_data
                data_stride += 2 * header['num_samples_per_data_block'] * header['num_amplifier_channels']

            if header['num_aux_input_channels'] > 0:
                # offset from aux_input_data
                data_stride += 2 * int(header['num_samples_per_data_block'] / 4) * header['num_aux_input_channels']

            if header['num_supply_voltage_channels'] > 0:
                # offset from supply_voltage_data
                data_stride += 2 * header['num_supply_voltage_channels']

            if header['num_temp_sensor_channels'] > 0:
                # offset from temp_sensor_data
                data_stride += 2 * header['num_temp_sensor_channels']

            if header['num_board_adc_channels'] > 0:
                # offset from board_adc_data
                data_stride += 2 * header['num_samples_per_data_block'] * header['num_board_adc_channels']

            if header['num_board_dig_in_channels'] > 0:
                # offset from board_dig_in_raw
                data_stride += 2 * header['num_samples_per_data_block']

            if header['num_board_dig_out_channels'] > 0:
                # offset from board_dig_out_raw
                data_stride += 2 * header['num_samples_per_data_block']

            if (header['version'][0] == 1 and header['version'][1] >= 2) or (header['version'][0] > 1):
                start = np.ndarray((1,), ('<i', (1, 1)), m, header_length,
                                   (data_stride,)).flatten()

                # it takes the last time sample, of the last data block
                header_length += int((num_data_blocks - 1) * data_stride) + \
                                 4 * (header['num_samples_per_data_block'] - 1)

                stop = np.ndarray((1,), ('<i', (1, 1)), m, header_length,
                                  (data_stride,)).flatten()
            else:
                start = np.ndarray((1,), ('<I', (1, 1)), m, header_length,
                                   (data_stride,)).flatten()
                # it takes the last time sample, of the last data block
                header_length += int((num_data_blocks - 1) * data_stride) + \
                                 4 * (header['num_samples_per_data_block'] - 1)

                stop = np.ndarray((1,), ('<I', (1, 1)), m, header_length,
                                  (data_stride,)).flatten()

            return start[0], stop[0]
