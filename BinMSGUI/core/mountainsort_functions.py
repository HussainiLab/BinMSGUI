import numpy as np
# import time
import os
import struct
import json
from core.wsl_terminal import BashConfigure
# from core.readMDA import readMDA
# import datetime


class Error(Exception):
    """Base class for exceptions in this module."""
    pass


class MSError(Error):
    """Exception raised for errors in the input.

    Attributes:
        expression -- input expression in which the error occurred
        message -- explanation of the error
    """

    # def __init__(self, expression, message):
    def __init__(self, message):
        # self.expression = expression
        self.message = message


def _writemda(X, fname, dt):
    dt_code = 0
    num_bytes_per_entry = get_num_bytes_per_entry_from_dt(dt)
    dt_code = _dt_code_from_dt(dt)
    if dt_code is None:
        print("Unexpected data type: {}".format(dt))
        return False

    f = open(fname, 'wb')
    try:
        _write_int32(f, dt_code)
        _write_int32(f, num_bytes_per_entry)
        _write_int32(f, X.ndim)
        for j in range(0, X.ndim):
            _write_int32(f, X.shape[j])
        # This is how I do column-major order
        A = np.reshape(X, X.size, order='F').astype(dt)
        A.tofile(f)
    except Exception as e:  # catch *all* exceptions
        print(e)
    finally:
        f.close()
        return True


def _write_int32(f, val):
    f.write(struct.pack('<i', val))


def get_num_bytes_per_entry_from_dt(dt):
    if dt == 'uint8':
        return 1
    if dt == 'float32':
        return 4
    if dt == 'int16':
        return 2
    if dt == 'int32':
        return 4
    if dt == 'uint16':
        return 2
    if dt == 'float64':
        return 8
    if dt == 'uint32':
        return 4
    return None


def get_np_dt_from_code(code):
    if code == -2:
        return np.uint8
    if code == -3:
        return np.float32
    if code == -4:
        return np.int16
    if code == -5:
        return np.int32
    if code == -6:
        return np.uint16
    if code == -7:
        return np.float64
    if code == -8:
        return np.uint32


def get_dt_from_code(code):
    if code == -2:
        return 'uint8'
    if code == -3:
        return 'float32'
    if code == -4:
        return 'int16'
    if code == -5:
        return 'int32'
    if code == -6:
        return 'uint16'
    if code == -7:
        return 'float64'
    if code == -8:
        return 'uint32'


def _dt_code_from_dt(dt):
    if dt == 'uint8':
        return -2
    if dt == 'float32':
        return -3
    if dt == 'int16':
        return -4
    if dt == 'int32':
        return -5
    if dt == 'uint16':
        return -6
    if dt == 'float64':
        return -7
    if dt == 'uint32':
        return -8
    return None


def get_threshold_index(data, data_indices, threshold):
    event_index = int(len(data_indices) / 2)

    if threshold >= 0:
        threshold_i = find_consec(np.where((data >= threshold) * (data_indices <= event_index))[0])[-1][0]
    else:
        threshold_i = find_consec(np.where((data <= threshold) * (data_indices <= event_index))[0])[-1][0]

    return threshold_i


def get_indices(data, spike_times, spike_channels, thresholds, delta=50, pre_threshold=10, post_threshold=40):
    # data contains all the preprocessed data
    # spike_times is a list of index values
    # spike_channels is a list of channel values for the
    # thresholds will be a list of thresholds [positive threhsolds, negative thresholds]

    half_delta = int(delta / 2)

    data_i = np.arange(delta)

    indices = np.zeros((len(spike_times), pre_threshold + post_threshold))

    for i, event in enumerate(spike_times):

        channel = spike_channels[i] - 1

        start = event - half_delta

        if start < 0:
            # cannot get the full range of indices
            continue

        stop = event + half_delta

        if stop > data.shape[1] - 1:
            # cannot get the full range of indices
            continue

        current_data = data[channel, start:stop]

        value = data[channel, event]

        if value > 0:
            # positive spike
            threshold = thresholds[0][channel]
        else:
            # negative spike
            threshold = thresholds[1][channel]

        try:
            index = get_threshold_index(current_data, data_i, threshold)
        except IndexError:
            index = np.where(current_data == value)[0]
            # print(channel, i, event, value, threshold)

        index += start

        # ensure that the threshold crossing is the 10th value (index 9) for Tint
        indices[i, :] = np.arange(index - pre_threshold + 1, index + post_threshold + 1)

    return indices.astype(int)


def find_consec(data):
    '''finds the consecutive numbers and outputs as a list'''
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


def create_tetrode_geom(filename, channel_width=25):
    """
    This will create the geom.csv file for the tetrodes
    where each channel within the tetrode are separated by
    the channel width (this should be in microns). We default
    to 25 microns.
    """
    x = np.array([0, 0, channel_width, channel_width])
    y = np.array([0, channel_width, 0, channel_width])

    coordinates = np.vstack((x, y)).T

    np.savetxt(filename, coordinates, fmt='%d', delimiter=',')


def get_ubuntu_path(filepath):
    # get the drive letter

    drive_letter_i = filepath.find(':/')

    if drive_letter_i == -1:
        drive_letter_i = filepath.find(':\\')

    drive_letter = filepath[:drive_letter_i].lower()

    i = 1
    while drive_letter_i + i == '/':
        i += 1

    remaining_path = filepath[drive_letter_i + i + 1:]
    linux_path = '/mnt/%s/%s' % (drive_letter, remaining_path)
    
    # add single quotes so linux can understand the special characters
    if '(' in linux_path or ')' in linux_path:
        linux_path = "'%s'" % linux_path

    return os.path.normpath((linux_path)).replace('\\', '/')


def get_windows_filename(filename):
    # remove the single quotes if added
    if filename[0] == "'" and filename[-1] == "'":
        filename = filename[1:-1]

    filename_split = filename.split('/')
    mnt_i = np.where(np.array(filename_split) == 'mnt')[0][0]

    drive_letter = filename_split[mnt_i + 1].upper()

    remaining = '\\'.join(list(filename_split[mnt_i + 2:]))

    return '%s:\\%s' % (drive_letter, remaining)


def create_sorting_parameters(filename, Fs=24e3, detect_sign='pos', adjacency_radius=-1, freq_width=1000, freq_min=300,
                              freq_max=7000, detect_threshold=3, detect_interval=50):
    """This method will create the sorting parameters

    Fs - the sampleing frequency that the data was recorded at.
    detect_sign = 'pos', 'neg', 'both'

    adjacency_radius=-1, "then there is only one electrode neighborhood containing all the channels."
    adjacency_radius=0, "then each channel is sorted independently."

    For tetrodes it is recommended that the adjacency_radius is equal to -1

    """

    detect_sign_options = ['pos', 'neg', 'both']

    parameters = {}

    parameters['samplerate'] = int(Fs)

    # ----- decide weather to detect positive/negative/both peaks ----- #
    if detect_sign not in detect_sign_options:
        raise ValueError('detect_sign is an invalid value.')

    else:
        # Tint requires
        if 'pos' in detect_sign:
            parameters['detect_sign'] = 1
        elif 'neg' in detect_sign:
            parameters['detect_sign'] = -1
        elif 'both' in detect_sign:
            parameters['detect_sign'] = 0

    parameters['freq_wid'] = freq_width
    parameters['freq_min'] = freq_min
    parameters['freq_max'] = freq_max

    parameters['detect_interval'] = detect_interval
    parameters['detect_threshold'] = detect_threshold

    # ----- adjacency radius ----- #
    parameters['adjacency_radius'] = adjacency_radius

    with open(filename, 'w') as f:
        json.dump(parameters, f)


def check_file_complete(filepath, delta_time=5):
    import time

    mtime = 0
    new_mtime = os.path.getmtime(filepath)

    while mtime != new_mtime:
        mtime = new_mtime
        time.sleep(delta_time)
        new_mtime = os.path.getmtime(filepath)

    return


def get_tetrode_metric(filename):
    under_index = find_sub(filename, '_')

    return int(filename[under_index[-2] + 1:under_index[-1]])


def run_pipeline_js(pipeline, inputs, outputs, parameters=None, verbose=False):

    command = 'ml-run-process %s ' % (pipeline)

    command += '--inputs '

    for key, value in inputs.items():
        if type(value) != list:
            command += '%s:%s ' % (str(key), str(value))
        else:
            for x in value:
                command += '%s:%s ' % (str(key), str(x))

    command += '--outputs '

    for key, value in outputs.items():
        command += '%s:%s ' % (str(key), str(value))

    if parameters is not None:
        command += '--parameters '

        for key, value in parameters.items():
            command += '%s:%s ' % (str(key), str(value))

    if verbose:
        print(command)

    profile = None
    cfg = BashConfigure()

    cfg.win32_wsl_open_bash('', [  # 'cd %s' % filepath, # needed for x-server to display visually
        # 'ls',
        command,
        'sleep 2'], profile)


def get_metric_files(session_filename, metrics_string='_metrics_'):
    directory = os.path.dirname(session_filename)

    basename = os.path.basename(os.path.splitext(session_filename)[0])

    file_list = os.listdir(directory)

    string_match = basename + metrics_string

    metric_list = [os.path.join(directory, file) for file in file_list
                   if string_match in file and is_json(file)]

    return metric_list


def is_json(file):
    if os.path.splitext(file)[-1] == '.json':
        return True
    return False


def run_sort(raw_fname=None, pre_fname=None, geom_fname=None, params_fname=None,
                 firings_out=None, pre_out_fname=None, metrics_out_fname=None, filt_out_fname=None,
                 freq_min=300, freq_max=7000, samplerate=30000, detect_sign=1,
                 adjacency_radius=-1, detect_threshold=3, detect_interval=50, clip_size=50,
                 firing_rate_thresh=0.05, isolation_thresh=0.95, noise_overlap_thresh=0.03,
                 peak_snr_thresh=1.5, verbose=True):
    """

    Parameters
    ----------
    raw_fname : INPUT
        MxN raw timeseries array (M = #channels, N = #timepoints). If you input this it will pre-process the data.
    pre_fname : INPUT
        MxN pre-processed array timeseries array (M = #channels, N = #timepoints). This is if you want to analyze already pre-processed data.
    geom_fname : INPUT
        (Optional) geometry file (.csv format).
    params_fname : INPUT
        (Optional) parameter file (.json format), where the key is the any of the parameters for this pipeline. Any values in this .json file will overwrite any defaults.

    firings_out : OUTPUT
        The filename that will contain the spike data (.mda file), default to '/firings.mda'
    filt_out_fname : OUTPUT
        The filename that will contain the filtered data (bandpassed).
    pre_out_fname : OUTPUT
        Optional filename for the pre-processed data.
    metrics_out_fname : OUTPUT
        The output filename (.json) for the metrics that will be computed for each unit.

    samplerate : float
        (Optional) The sampling rate in Hz
    freq_min : float
        (Optional) The lower endpoint of the frequency band (Hz)
    freq_max : float
        (Optional) The upper endpoint of the frequency band (Hz)
    adjacency_radius : float
        (Optional) Radius of local sorting neighborhood, corresponding to the geometry file (same units). 0 means each channel is sorted independently. -1 means all channels are included in every neighborhood.
    detect_sign : int
        (Optional) Use 1, -1, or 0 to detect positive peaks, negative peaks, or both, respectively
    detect_threshold : float
        (Optional) Threshold for event detection, corresponding to the input file. So if the input file is normalized to have noise standard deviation 1 (e.g., whitened), then this is in units of std. deviations away from the mean.
    detect_interval : int
        (Optional) The minimum number of timepoints between adjacent spikes detected in the same channel neighborhood.
    clip_size : int
        (Optional) Size of extracted clips or snippets, used throughout
    firing_rate_thresh : float64
        (Optional) firing rate must be above this
    isolation_thresh : float64
        (Optional) isolation must be above this
    noise_overlap_thresh : float64
        (Optional) noise_overlap_thresh must be below this
    peak_snr_thresh : float64
        (Optional) peak snr must be above this

    """

    # the name of the pipeline we will be using
    pipeline = 'ms4_geoff.sort'

    inputs = {}

    if raw_fname:
        inputs['raw_fname'] = raw_fname
    elif pre_fname:
        inputs['pre_fname'] = pre_fname

    if geom_fname:
        inputs['geom_fname'] = geom_fname

    if params_fname:
        inputs['params_fname'] = params_fname

    outputs = {'firings_out': firings_out,
               'pre_out_fname': pre_out_fname,
               'metrics_out_fname': metrics_out_fname,
               'filt_out_fname': filt_out_fname,
               }

    parameters = {'freq_min': freq_min, 'freq_max': freq_max, 'samplerate': samplerate,
                  'detect_sign': detect_sign, 'adjacency_radius': adjacency_radius,
                  'detect_threshold': detect_threshold, 'detect_interval': detect_interval,
                  'clip_size': clip_size, 'firing_rate_thresh': firing_rate_thresh, 'isolation_thresh': isolation_thresh,
                  'noise_overlap_thresh': noise_overlap_thresh, 'peak_snr_thresh': peak_snr_thresh}

    run_pipeline_js(pipeline, inputs, outputs, parameters, verbose=verbose)


def get_pre_params(preproc_filename, whiten=True):
    json_filename = os.path.splitext(preproc_filename)[0] + '.json'

    if not whiten:
        json_filename = json_filename[:-8] + 'pre.json'
    # print(json_filename)

    if os.path.exists(json_filename):
        with open(json_filename, 'r') as f:
            parameters = json.load(f)
    else:
        raise (MSError('No pre processing parameter filename, have you pre processed?'))

    return parameters


def get_snip_indices(snippets, ts_indices, snippet_size=50):
    # create an array that will hold on index value for snippet value
    data_snip_indices = np.zeros((1, snippets.shape[1])).flatten().astype(int)
    for i, spike_i in enumerate(ts_indices):
        start = i * snippet_size
        stop = start + snippet_size
        data_snip_indices[start:stop] = np.arange(spike_i, spike_i + snippet_size)

    return data_snip_indices


def snippets2continuous(snippets, ts_indices, Fs, threshold, n_samples, method='zero',
                        sin_f=500, sin_a=100, sigmas=3):
    """
    This function will return a pseudo continuous waveform for a given snippets matrix. It will interpolate a
    line between each of the snippets.

    Example:

        duration = get_setfile_parameter(snippets, set_fullpath)

    Args:
        snippets (ndarray): A concatenated array of all the snippets. It will be an NxM array
            where N is the number of channels, and M is the snippet length * the number of snippets.
            (i.e. if you have 50 samples per snippets, and 100 snippets, M = 5000)
        ts_indices (ndarray): A 1xN array of index values where each index value corresponds to where the
            snippet began. (i.e. with data sampled at 1 kHz, if there were two snippets beginning at 1 second,
            and 2 seconds, the ts_indices would have values of [1000, 2000])
        n_samples (int): the number of samples for the output continuous data
        method (str): options ('zero', 'ramp', 'sin'), this will determine the method you use to fill in values between
        chunks 'zero' will just zero bad between chunks, 'ramp' will interpolate a straight line between the previous
        and current chunk. Recommended using 'zero', it should ensure that no events are picked up between chunks.

    Returns:
        continuous_data (ndarray): the continuous version of the snippet data
        data_snip_indices (ndarray): the pre interpolated index values that were calcualted
    """

    # create an array that will hold on index value for snippet value

    data_snip_indices = get_snip_indices(snippets, ts_indices)

    data_snip_indices_new = np.arange(n_samples)

    n_channels = snippets.shape[0]

    snippets_new = np.zeros((n_channels, len(data_snip_indices_new)))

    if 'ramp' in method:
        # this if statement will interpolate the lines between chunks for us.

        # calculate slopes
        diff_data_snip_indices = np.diff(data_snip_indices)  # used for slope calc, dx
        diff_snippets = np.diff(snippets)  # used for slope calculation, dy

        slopes = np.zeros_like(diff_snippets)
        non_zero_bool = np.where(diff_data_snip_indices != 0)[0]

        # only calculate where difference in snip indices is not zero so we avoid dividing by zero
        # works without this, but was tired of seeing that error
        slopes[:, non_zero_bool] = np.divide(diff_snippets[:, non_zero_bool],
                                             diff_data_snip_indices[non_zero_bool])  # dy/dx

        # if two snippest connect there will be a diff_data_snip == 0, if it's within a snippet diff = 1
        bool_value = np.where((diff_data_snip_indices != 0) * (diff_data_snip_indices != 1))[0]

        for i, bool_i in enumerate(bool_value):
            start_index = data_snip_indices[bool_i]
            stop_index = data_snip_indices[bool_i + 1]

            snippets_new[:, start_index:stop_index] = np.multiply(
                slopes[:, bool_i].reshape((-1, 1)),
                np.tile(np.arange(stop_index - start_index),
                        (n_channels, 1))) + snippets[:, bool_i].reshape((-1, 1))

    elif 'zero' in method:
        # do nothing as we already set the zeros
        pass

    elif 'sin' in method:

        t = np.arange(snippets_new.shape[1]) / Fs

        '''
        diff_data_snip_indices = np.diff(data_snip_indices)  # used for slope calc, dx

        bool_value = np.where((diff_data_snip_indices != 0) * (diff_data_snip_indices != 1))[0]

        for i, bool_i in enumerate(bool_value):
            start_index = data_snip_indices[bool_i]
            stop_index = data_snip_indices[bool_i+1]

            t = np.arange(stop_index-start_index)/Fs
            snippets_new[:, start_index:stop_index] = sin_a*np.sin(2*np.pi*sin_f*t)
        '''

        snippets_new[:, :] = sin_a * np.sin(2 * np.pi * sin_f * t)

        snippets_new[:, data_snip_indices] = snippets

        means = np.mean(snippets_new, axis=1)
        stdevs = np.std(snippets_new, axis=1)

        thresholds = means + sigmas * stdevs

        for i, threshold_value in enumerate(thresholds):
            if threshold_value > threshold:
                offset = threshold_value - threshold
                snippets_new[i, :] = snippets_new[i, :] - 1.5 * offset

    # fill in the appropriate chunk values
    snippets_new[:, data_snip_indices] = snippets

    return snippets_new, data_snip_indices


def is_mda(file):
    if os.path.splitext(file)[-1] == '.mda':
        return True
    return False


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


def get_mda_files(session_filename, files='raw'):
    directory = os.path.dirname(session_filename)

    basename = os.path.basename(os.path.splitext(session_filename)[0])

    basename += '_T'

    file_list = os.listdir(directory)

    if files == 'raw':
        file_string = '_raw.'
    elif files == 'pre':
        file_string = '_pre.'
    else:
        file_string = '_%s.' % files

    mda_list = [os.path.join(directory, file) for file in file_list
                if basename in file and is_mda(file) and file_string in file]

    return mda_list


def get_rawmda_tetrode(raw_mda, unders=2):
    basename = os.path.basename(os.path.splitext(raw_mda)[0])
    under_i = find_sub(basename, '_')

    # +2 because +1 for _ and +1 for T
    try:
        return int(basename[under_i[-unders] + 2:under_i[-unders+1]])
    except:
        return None


def get_mua_cells(metrics_filename):
    with open(metrics_filename, 'r') as f:
        data = json.load(f)
    data = data['clusters']
    mua_list = []
    for unit in data:
        label = unit['label']
        tag = unit['tags']

        if 'mua' in tag:
            mua_list.append(label)
    return mua_list


def get_tint_cut(cut, mua_cells):
    """This will make it so that the good cells are consecutive and in the beginning of the cut file, and the
    MUA (noise + cells that just didn't meet our criteria), will be in the back, separated by an emtpy cell.
    It will also sort the mua cells from most least to most spikes."""
    from operator import itemgetter

    mua_cells = np.asarray(mua_cells)

    cut_dict = {0: 0}  # cut_value, new_consecutive_cut_value

    # for the curated the cut values might not be consecutive numbers, lets turn these values
    # into consecutive numbers

    if 0 in cut:
        add_one = 0
    else:
        add_one = 1

    cells = np.setdiff1d(np.unique(cut), mua_cells)

    i = 0  # initialize i, if all the cells are mua, it will skip the next for loop and i will not be initialized
    for i, cut_value in enumerate(np.unique(cells)):
        if cut_value == 0:
            continue

        cut_dict[cut_value] = i + add_one  # +1 because we already have zero

    i_offset = i + 1 + 1  # +1 for the gap as well as incrementing +1 from what we have already done above

    count_dict = {}
    for cut_value in mua_cells:
        count_dict[cut_value] = sum(cut.flatten() == cut_value)

    for i, cut_value in enumerate(sorted(count_dict.items(), key=lambda x: x[1])):
        cut_value = cut_value[0]
        if cut_value == 0:
            continue

        cut_dict[cut_value] = i + i_offset + add_one  # +1 because we already have zero

    return itemgetter(*list(cut))(cut_dict), cut_dict


def write_cut(cut_filename, cut, basename=None):
    if basename is None:
        basename = os.path.basename(os.path.splitext(cut_filename)[0])

    unique_cells = np.unique(cut)

    if 0 not in unique_cells:
        # if it happens that there is no zero cell, add it anyways
        unique_cells = np.insert(unique_cells, 0, 0)  # object, index, value to insert

    n_clusters = len(np.unique(cut))
    n_spikes = len(cut)

    write_list = []  # the list of values to write

    tab = '    '  # the spaces didn't line up with my tab so I just created a string with enough spaces
    empty_space = '               '  # some of the empty spaces don't line up to x tabs

    # we add 1 to n_clusters because zero is the garbage cell that no one uses
    write_list.append('n_clusters: %d\n' % (n_clusters))
    write_list.append('n_channels: 4\n')
    write_list.append('n_params: 2\n')
    write_list.append('times_used_in_Vt:%s' % ((tab + '0') * 4 + '\n'))

    zero_string = (tab + '0') * 8 + '\n'

    for cell_i in np.arange(n_clusters):
        write_list.append(' cluster: %d center:%s' % (cell_i, zero_string))
        write_list.append('%smin:%s' % (empty_space, zero_string))
        write_list.append('%smax:%s' % (empty_space, zero_string))
    write_list.append('\nExact_cut_for: %s spikes: %d\n' % (basename, n_spikes))

    # now the cut file lists 25 values per row
    n_rows = int(np.floor(n_spikes / 25))  # number of full rows

    remaining = int(n_spikes - n_rows * 25)
    cut_string = ('%3u' * 25 + '\n') * n_rows + '%3u' * remaining

    write_list.append(cut_string % (tuple(cut)))

    with open(cut_filename, 'w') as f:
        f.writelines(write_list)
