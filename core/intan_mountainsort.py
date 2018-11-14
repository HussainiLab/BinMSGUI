import numpy as np
from core.Tint_Matlab import getspikes, get_setfile_parameter, get_active_tetrode
import os
from core.mountainsort_functions import _writemda, get_mda_files, get_rawmda_tetrode, \
    get_ubuntu_path, get_pre_params, get_windows_filename, run_sort, check_file_complete, \
    get_snip_indices, get_tint_cut, write_cut, get_dt_from_code, find_sub, \
    get_metric_files, get_tetrode_metric, get_mua_cells
from core.intan_rhd_functions import find_basename_files, read_data, read_header
from core.rhd_utils import read_notes, tetrode_map
import time
from core.readMDA import readMDA
import datetime
import json


def intan_scalar():
    """returns the scalar value that can be element-wise multiplied to the data
    to convert from bits to micro-volts"""
    Vswing = 2.45
    bit_range = 2 ** 16  # it's 16 bit system
    gain = 192  # V/V, listed in the intan chip's datasheet
    return (1e6) * (Vswing) / (bit_range * gain)


def intan2mda(session_files, directory, self=None):
    """
        This function convert the intan ata into the .mda format that MountainSort requires.

        Example:
            session_files = ['C:\\example\\example_session_1.rhd' , 'C:\\example\\example_session_2.rhd']
            directory = 'C:\\example'
            intan2mda(session_files, directory, basename)

        Args:
            tetrode_files (list): list of the fullpaths to the tetrode files belonging to the session you want to
                convert.
            directory (string): the path of the directory the session and tetrode files are in.
            basename (string): the basename of the session you are converting.
            pre_threshold (int): the number of samples before the threshold that you want to save in the waveform
            post_threshold (int): the number of samples after the threshold that you want to save in the waveform
            self (object): self is the main window of a GUI that has a LogAppend method that will append this message to
                a log (QTextEdit), and a custom signal named myGUI_signal_str that would was hooked up to LogAppend to
                append messages to the log.
        Returns:
            mdas_written (list): a list of mda files that were created
    """

    file_header = read_header(session_files[0])

    # get the probe value from the notes
    notes = file_header['notes']  # finds the notes of the file headers where we might keep probe info

    probe, experimenter = read_notes(notes, tetrode_map)

    probe_map = tetrode_map[probe]

    tint_basename = os.path.basename(os.path.splitext(sorted(session_files, reverse=False)[0])[0])

    mda_filenames = []

    for tetrode, tetrode_channels in sorted(probe_map.items()):

        msg = '[%s %s]: Converting the following tetrode: %d!' % \
              (str(datetime.datetime.now().date()),
               str(datetime.datetime.now().time())[:8], tetrode)
        if self:
            self.LogAppend.myGUI_signal_str.emit(msg)
        else:
            print(msg)
        # self.LogAppend.myGUI_signal.emit(msg)

        mda_filename = '%s_T%d_raw.mda' % (os.path.join(directory, tint_basename), tetrode)

        mda_filenames.append(mda_filename)

        if os.path.exists(mda_filename):
            msg = '[%s %s]: The following filename already exists: %s, skipping conversion!#Red' % \
                  (str(datetime.datetime.now().date()),
                   str(datetime.datetime.now().time())[:8], mda_filename)

            if self:
                self.LogAppend.myGUI_signal_str.emit(msg)
            else:
                print(msg)

            continue

        data = np.array([])
        t_intan = np.array([])
        # concatenates the data from all the .rhd files

        tetrode_channels = np.asarray(tetrode_channels)

        msg = '[%s %s]: Currently Converting Data Related to Tetrode: %d!' % \
              (str(datetime.datetime.now().date()),
               str(datetime.datetime.now().time())[:8], tetrode)
        # self.LogAppend.myGUI_signal.emit(msg)
        if self:
            self.LogAppend.myGUI_signal_str.emit(msg)
        else:
            print(msg)

        # analyze the one tetrode's data at a time to attempt to not load too much data into memory at once
        for session_file in sorted(session_files, reverse=False):
            # Loads each session and appends them to create one matrix of data for the current tetrode

            msg = '[%s %s]: Currently loading T%d data from the following file: %s' % \
                  (str(datetime.datetime.now().date()),
                   str(datetime.datetime.now().time())[:8], tetrode, session_file)
            # self.LogAppend.myGUI_signal.emit(msg)
            if self:
                self.LogAppend.myGUI_signal_str.emit(msg)
            else:
                print(msg)

            file_data = read_data(session_file)

            # Acquiring session information

            if data.shape[0] == 0:
                data = file_data['amplifier_data']
                # bits, data is arranged into (number of channels, number of samples)

                data = data[tetrode_channels - 1, :]

            else:

                data = np.concatenate((data, file_data['amplifier_data'][tetrode_channels - 1, :]), axis=1)

            if t_intan.shape[0] == 0:
                t_intan = file_data[
                    't_amplifier']  # the times recorded by the intan system, starts at the value of 0 seconds
            else:
                # the time's always start at 0, per .rhd file, so when putting them together you need add
                # to each time value
                t_intan = np.concatenate((t_intan, file_data['t_amplifier']), axis=0)

        data = np.multiply(-1, data)

        # because we flipped the signs we need to make sure that it is still int16
        data[np.where(data >= 32767)] = 32767

        data = np.int16(data)

        _writemda(data, mda_filename, 'int16')

    return mda_filenames


def matching_ind(haystack, needle):
    """This function will find the index values of the haystack that are within the needle"""
    idx = np.searchsorted(haystack, needle)
    mask = idx < haystack.size
    mask[mask] = haystack[idx[mask]] == needle[mask]
    idx = idx[mask]
    return idx


class EventDict(dict):
    """This dictionary will hold all the events belonging to a chunk"""
    def __getitem__(self, key, mode='list'):
        """This method will return the values for a given key"""
        if isinstance(key, tuple):
            # return [super().__getitem__(k) for k in key]
            # return [self.__getitem__(k) for k in key]
            if mode == 'list':
                return [self.__getitem__(k, mode=mode) for k in key]
            return np.asarray([self.__getitem__(k, mode=mode) for k in key])

        else:
            if mode == 'list':
                return super().__getitem__(key)
            else:
                values = super().__getitem__(key)
                return np.asarray(values)

    def __setitem__(self, key, value):
        """This method will add the key values, also if a key exists it will append
        the new values to the existing values"""
        if not isinstance(key, tuple):
            key = tuple([key])

        if not isinstance(value, tuple):
            value = tuple([value])

        if isinstance(key, tuple):
            #
            key_array = np.asarray(key)
            current_keys = np.asarray(list(self.keys()))
            if len(current_keys) > 0:
                """If there are existing keys, append these values to the existing ones"""
                existing_bool = np.in1d(np.asarray(key), current_keys)

                existing_keys = tuple(key_array[existing_bool])

                existing_values = self.__getitem__(existing_keys, mode='list')

                add_values = np.asarray(value)[existing_bool].tolist()

                # append the list for existing values
                for i in np.arange(len(existing_values)):
                    existing_values[i] += add_values[i]
                self.update(zip(existing_keys, tuple(existing_values)))

                new_keys = tuple(key_array[~existing_bool])
                new_values = np.asarray(value)[~existing_bool].tolist()

                self.update(zip(new_keys, new_values))

            else:
                """There are no existing keys, just add normaly"""
                self.update(zip(key, value))
                # else:
                #    super().__setitem__(key, value)

    def __delitem__(self, key, value):
        if isinstance(key, tuple):
            for k in key: super().__delitem__(k)
        else:
            super().__setitem__(key, value)


class Error(Exception):
    """Base class for exceptions in this module."""
    pass


class CutError(Error):
    """Exception raised for errors in the input.

    Attributes:
        expression -- input expression in which the error occurred
        message -- explanation of the error
    """

    # def __init__(self, expression, message):
    def __init__(self, message):
        # self.expression = expression
        self.message = message


def pad_array(arr):
    """This function will turn a list of lists into a numpy matrix with padded nan values"""
    M = max(len(a) for a in arr)
    return np.array([a + [np.nan] * (M - len(a)) for a in arr])


def get_chunk_events(spike_times, indices_start, start=0, stop=50):
    """This function will find the events that belong to each chunk"""

    chunk_events = EventDict()

    for i in np.arange(start, stop):
        # the index values for the i'th value in each waveform
        start_values = indices_start + i

        # check if any of these index values match the spike_time indices
        idx = matching_ind(start_values, spike_times)  # index values within start_values that match spike_times

        chunk_events[tuple(idx)] = tuple(start_values[idx].reshape((-1, 1)).tolist())

    return chunk_events


def process_sort(set_filename, pre_threshold=10, whiten=True, version='js', self=None):
    """
        This function will ensure that there is only one spike per chunk.

        Example:


        Args:
            set_filename (str):

        Returns:
            Bool: It will return True if all these files have already been processed, otherwise it will return False
    """
    basename = os.path.basename(os.path.splitext(set_filename)[0])
    directory, _ = os.path.split(set_filename)
    tetrodes = get_active_tetrode(set_filename)
    tetrode_files = [os.path.join(directory, '%s.%d' % (basename, tetrode)) for tetrode in tetrodes]
    # directory, tetrode_files = find_tet(set_filename)  # find the tetrode files

    # just in case the curated version doesn't work and it runs a non-curated sort, we want to convert both to .cut
    if whiten:
        firings_mda = get_mda_files(set_filename, 'firings_%s' % version)
    else:
        firings_mda = get_mda_files(set_filename, 'firings_nowhiten_%s' % version)

    already_processed = 0

    for spike_filename in firings_mda:

        msg = '[%s %s]: Processing the following spike files to remove duplicate spikes: %s!' % (
            str(datetime.datetime.now().date()),
            str(datetime.datetime.now().time())[
            :8], spike_filename)

        if self:
            self.LogAppend.myGUI_signal_str.emit(msg)
        else:
            print(msg)

        if whiten:
            tetrode = get_rawmda_tetrode(spike_filename, unders=3)
        else:
            tetrode = get_rawmda_tetrode(spike_filename, unders=4)

        tetrode_fname = [file for file in tetrode_files if os.path.splitext(file)[1] == ('.%d' % tetrode)][0]

        A, code = readMDA(spike_filename)

        dt = get_dt_from_code(code)

        spike_times = (A[1, :]).astype(int)  # at this stage it is in index values (0-based)

        # remove any repeat spike times
        repeat_spikes = np.where(np.diff(spike_times) == 0)[0]

        A = np.delete(A, repeat_spikes + 1, axis=1)

        # spike_channel = A[0, :].astype(int)  # the channel which the spike belongs to
        spike_times = (A[1, :]).astype(int)  # at this stage it is in index values (0-based)
        # cell_number = A[2, :].astype(int)

        ts, ch1, ch2, ch3, ch4, spikeparam = getspikes(tetrode_fname)  # sec, bits, bits, bits, bits, dict

        snippets_concat = np.vstack((ch1, ch2, ch3, ch4)).reshape((4, -1))

        ch1 = None
        ch2 = None
        ch3 = None
        ch4 = None

        Fs = spikeparam['sample_rate']

        ts_indices = np.rint(np.multiply(ts.flatten(), Fs)).astype(int)  # get the index value of threshold cross

        ts_indices = ts_indices - pre_threshold + 1  # ensures that index value represents the start of the chunk

        data_snip_indices = get_snip_indices(snippets_concat, ts_indices)

        start_i = data_snip_indices[::50].reshape((-1, 1))
        stop_i = data_snip_indices[49::50].reshape((-1, 1)) + 1  # add 1 so it includes the stop value

        indices = np.hstack((np.arange(len(start_i)).reshape((-1, 1)), start_i, stop_i))

        # produce a dictionary where the key is the chunk index, and the value is a list of events within each chunk
        chunk_events_values = get_chunk_events(spike_times, indices[:, 1])

        desired_events_indices = indices[:, 1] + 25

        event_values, chunk_indices = process_event_values(spike_times, chunk_events_values, desired_events_indices,
                                                           indices)

        event_bool = np.in1d(spike_times, event_values)

        if sum(event_bool) != len(event_bool):

            A = A[:, event_bool]

            # new_cut_filename = 'new_spikes.mda'
            os.remove(spike_filename)  # delete the previous firing output

            _writemda(A, spike_filename, dt)  # write the new firing output

        else:

            already_processed += 1

            msg = '[%s %s]: The following spike file has already been processed, or has no duplicates: %s!' % (
                str(datetime.datetime.now().date()),
                str(datetime.datetime.now().time())[
                :8], spike_filename)

            if self:
                self.LogAppend.myGUI_signal_str.emit(msg)
            else:
                print(msg)

    if already_processed == len(firings_mda):
        return True
    return False


def process_event_values(spike_times, chunk_events_values, desired_events_indices, indices):
    """This method will ensure that there's no repeat spikes, and that there's only one spike per chunk"""
    # obtain the chunk indices and values associated with them
    chunk_indices = sorted(chunk_events_values.keys())  # this corresponds to the indices row that contains events
    chunk_values = chunk_events_values[tuple(chunk_indices)]  # these are the events within that row

    chunk_values = pad_array(chunk_values)  # pad the list of lists so we can have a uniform length array

    # some chunks will have no events, remove these so the chunk_values has the same amount of rows
    desired_events_indices = desired_events_indices[chunk_indices]

    if chunk_values.shape[0] != len(desired_events_indices):
        raise CutError("Mismatching dimensions for desired_events_indices and chunk_values")

    # we want to find the closest index to the desired_events_indices, so we will take the absolute value
    # of the difference and find the index of the smallest value
    chunk_values_difference = np.abs(chunk_values - desired_events_indices.reshape((-1, 1)))

    difference_mins = np.nanmin(chunk_values_difference, axis=1)  # find the minimum values

    column_values = np.zeros(chunk_values.shape[0]).astype(int)
    set_values = np.zeros(chunk_values.shape[0]).astype(int)

    # iterate through the columns to find the indices of the minimums, if you subtract the minimums from the column
    # array, then the minimum will be located where that difference array is equal to zero
    for i in np.arange(chunk_values.shape[1]):
        # the index values for the i'th value in each waveform
        difference_bool = np.where((chunk_values_difference[:, i] - difference_mins) == 0)[0]

        # make sure we leave values that have already been set (sometimes there are two events that will be the same
        # distance)
        difference_bool = difference_bool[np.where(set_values[difference_bool] == 0)[0]]  # index

        set_values[difference_bool] = 1  # set these index values to 1 to make sure that we only set them once
        column_values[difference_bool] = i

    # get the event_values so there is only one event per chunk
    event_values = chunk_values[np.arange(chunk_values.shape[0]).tolist(), column_values.tolist()].astype(int)

    # return event_values

    # return event_values
    chunk_indices = np.asarray(chunk_indices)

    # iterate through any repeat values (likely due to overlapping chunks)
    index_delete = []  # initialize the list that holds indices to delete
    array_insert = []  # initialize the list that holds array values to insert (and replace repeats)
    index_insert = []  # initialize the list that holds the indices that the array values will belong to

    # check if there are any repeats
    if np.unique(event_values).shape[0] != event_values.shape[0]:
        # then there is a repeat spike_time, most likely due to overlapping chunks
        repeat_indices = np.where(np.diff(event_values) == 0)[0]
        for repeat_index in repeat_indices:
            repeat_value = event_values[repeat_index]
            chunk_i = chunk_indices[repeat_index + 1]  # chunk index value

            desired_event = desired_events_indices[repeat_index + 1]
            start, stop = indices[chunk_i, 1:]

            spikes = spike_times[np.where((spike_times >= start) * (spike_times < stop))[0]]

            # remove already chosen values
            spikes = spikes[np.where((spikes != repeat_value) * (~np.in1d(spikes, event_values)))]

            index_delete.append(repeat_index + 1)

            # event_values = np.delete(event_values, repeat_index+1)  # remove the repeat value

            if len(spikes) > 0:
                # find the next closest value to the desired spike index
                spike_diff_min = np.abs(spikes - desired_event)
                new_spike_t = spikes[np.where(spike_diff_min == np.amin(spike_diff_min))[0]][0]

                if new_spike_t not in event_values:
                    array_insert.append(new_spike_t)
                    index_insert.append(repeat_index + 1)
                else:
                    pass
            else:
                # set_values[chunk_i] = 0
                # set_values[repeat_index+1] = 0
                pass

        index_delete = np.asarray(index_delete)

        event_values = np.delete(event_values, index_delete)  # delete repeat values
        chunk_index_deleted_values = chunk_indices[index_delete]
        chunk_indices = np.delete(chunk_indices, index_delete)
        # set_values = np.delete(set_values, index_delete)

        if len(array_insert) > 0:
            # insert any replacements
            array_insert = np.asarray(array_insert)

            # the chunk value (cut index)
            chunk_array_insert = chunk_index_deleted_values[
                np.in1d(index_delete, index_insert)
            ]

            index_insert = np.zeros(len(array_insert)).astype(int)
            # set_values_insert = np.ones(len(chunk_array_insert))

            # for each value, find where it should be inserted into the arrays
            for i, value in enumerate(array_insert):
                index_insert[i] = np.where(event_values > value)[0][0]

            event_values = np.insert(event_values, index_insert, array_insert)
            chunk_indices = np.insert(chunk_indices, index_insert, chunk_array_insert)
            # set_values = np.insert(set_values, index_insert, set_values_insert)

            if not np.array_equal(chunk_indices, np.sort(chunk_indices)):
                raise CutError("Error, the new chunk_indices should be equal to np.sort(chunk_indices)")

            if not np.array_equal(event_values, np.sort(event_values)):
                raise CutError("Error, the new event_values should be equal to np.sort(event_values)")

    return event_values, chunk_indices


def intan_mountainsort(directory, rhd_session_file, pre_threshold=10, post_threshold=40, detect_sign=0,
                       whiten=True, adjacency_radius=-1, detect_threshold=3, detect_interval=10, clip_size=50,
                       firing_rate_thresh=0.05, isolation_thresh=0.95, noise_overlap_thresh=0.03,
                       peak_snr_thresh=1.5, self=None):
    """
        This will convert an entire session into a format the MountainSort can use, sort the data via MountainSort,
        and then convert the sorted output to a format that Tint can utilize.

        Example:


        Args:
            set_filename (str): the fullpath for the .set file you want to analyze.
            pre_threshold (int): the number of samples before threshold that you want to save for the waveform.
            curated (bool): True means you want to curate the sorted data, False means you do not. Curation will further
                sort the data by combining similar cells, etc. Note that if you curate on data with a lot of noise you
                could end up with no cells.
            detect_sign (int): {-1, 0, 1}, -1, means you want to detect the negative peaks, 1, means you want to detect
                the positive peaks, 0 means you want to detect both positive and negative peaks.
            adjacency_radius (int): use the value of -1 for tetrodes.
            detect_threshold (float): how many standard deviations away from the mean to use as the threshold.
            version (string): {'js', 'ms3'}, 'js' for the new javascript version, 'ms3' for the old MountainSort3.
            self (object): self is the main window of a GUI that has a LogAppend method that will append this message to
                a log (QTextEdit), and a custom signal named myGUI_signal_str that would was hooked up to LogAppend to
                append messages to the log.

        Returns:
            None
    """
    rhd_basename = rhd_session_file[:find_sub(rhd_session_file, '_')[-2]]

    session_files = find_basename_files(rhd_basename, directory)

    rhd_session_fullfile = os.path.join(directory, rhd_session_file + '.rhd')

    # find the session with our rhd file in it
    session_files = [sub_list for sub_list in session_files if rhd_session_fullfile in sub_list][0]

    if type(session_files) != list:
        # if there is only one file in the list, the output will not be a list
        session_files = [session_files]

    # convert tetrodes to .mda format
    mdas = intan2mda(session_files, directory, self=self)

    # get files
    file_header = read_header(session_files[0])

    Fs = int(file_header['sample_rate'][0])  # samplerate

    for mda in mdas:
        mda_basename = os.path.splitext(mda)[0]
        mda_basename = mda_basename[:find_sub(mda_basename, '_')[-1]]

        firings_out = mda_basename + '_firings.mda'
        filt_out_fname = get_ubuntu_path(mda_basename + '_filt.mda')
        pre_out_fname = get_ubuntu_path(mda_basename + '_pre.mda')
        metrics_out_fname = get_ubuntu_path(mda_basename + '_metrics.json')

        if os.path.exists(firings_out):
            self.LogAppend.myGUI_signal_str.emit('[%s %s]: The following file has already been created: %s!' % (
                str(datetime.datetime.now().date()),
                str(datetime.datetime.now().time())[:8], firings_out))
            continue

        run_sort(raw_fname=get_ubuntu_path(mda),
                 firings_out=get_ubuntu_path(firings_out), pre_out_fname=pre_out_fname,
                 metrics_out_fname=metrics_out_fname, filt_out_fname=filt_out_fname,
                 freq_min=300, freq_max=7000, samplerate=Fs, detect_sign=detect_sign,
                 adjacency_radius=adjacency_radius, detect_threshold=detect_threshold, detect_interval=detect_interval,
                 clip_size=clip_size, firing_rate_thresh=firing_rate_thresh, isolation_thresh=isolation_thresh,
                 noise_overlap_thresh=noise_overlap_thresh, peak_snr_thresh=peak_snr_thresh, verbose=True)

        while not os.path.exists(get_windows_filename(metrics_out_fname)):
            time.sleep(0.1)

        check_file_complete(get_windows_filename(metrics_out_fname))

    # create a cut file so that Tint can read the sorted output
    '''create_cut(set_filename, tags_bool, pre_threshold=pre_threshold, post_threshold=post_threshold, whiten=whiten,
               self=self)

    
    merge = True
    if merge:
        # combine parents
        run_merge_parents(set_filename, tags_bool, verbose=False, version=version, whiten=whiten, self=self)

        time.sleep(0.5)

        # re calculate cluster metrics (for the firingsmerged data)
        reclustered_bool = cluster_metrics_tint(set_filename, processed_bool, mda_suffix=mda_suffix,
                                                firings_suffix='firingsmerged', clip_size=50, samplerate=Fs,
                                                refrac_msec=1, version=version, verbose=False, whiten=whiten, self=self)

        metric_string = '_metricsmerged_'
        merge_tags_bool = add_tags_tint(set_filename, reclustered_bool, metrics_string=metric_string,
                                        firing_rate_thresh=0.05, isolation_thresh=0.95, noise_overlap_thresh=0.03,
                                        peak_snr_thresh=1.5, verbose=False, whiten=whiten, self=self)

        # create a cut file so that Tint can read the sorted output
        create_cut(set_filename, merge_tags_bool, merged=True, pre_threshold=pre_threshold,
                   post_threshold=post_threshold, version=version, whiten=whiten, self=self)
    '''