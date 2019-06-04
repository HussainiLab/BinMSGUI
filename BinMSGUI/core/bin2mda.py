import os
import numpy as np
from core.readBin import get_bin_data, get_active_tetrode
import datetime
from core.mountainsort_functions import _writemda
from core.filtering import notch_filt


def bin2mda(bin_filename, set_filename, Fs=48e3, notch_filter=True, notch_freq=60, self=None):
    """
        This function convert the intan ata into the .mda format that MountainSort requires.

        Example:
            bin_filename = 'C:\\example\\bin_example.bin'
            set_filename = 'C:\\example\\bin_example.set'
            bin2mda(bin_filename, set_filename)

        Args:
            bin_filename (str): full filename for the .bin file that you want to convert to .mda
            desired_Fs (int): the sampling rate that you want the data to be at. I've added this because we generally record at 24k but
                we will convert to a 48k signal (the system we analyze w/ needs 48k).
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

    tint_basename = os.path.basename(os.path.splitext(bin_filename)[0])

    directory = os.path.dirname(bin_filename)

    mda_filenames = []

    # find the common mode

    active_tetrodes = get_active_tetrode(set_filename)

    for tetrode in active_tetrodes:

        msg = '[%s %s]: Converting the following tetrode: %d!' % \
              (str(datetime.datetime.now().date()),
               str(datetime.datetime.now().time())[:8], tetrode)
        if self:
            self.LogAppend.myGUI_signal_str.emit(msg)
        else:
            print(msg)

        # get_tetrode_data
        data = get_bin_data(bin_filename, tetrode=tetrode)

        # check if the data has been filtered already

        # TODO: add some methods to find out if the data has been filtered or not
        data_filtered = True

        if data_filtered:
            mda_filename = '%s_T%d_filt.mda' % (os.path.join(directory, tint_basename), tetrode)
        else:
            # the data has not been filtered
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

        if notch_filter:
            data = notch_filt(data, Fs, freq=notch_freq)

        # append any values if we want to make the duration even
        data = np.int16(data)

        _writemda(data, mda_filename, 'int16')

    return mda_filenames


def convert_bin2mda(tint_fullpath, notch_filter=False, self=None):

    bin_filename = '%s.bin' % tint_fullpath
    set_filename = '%s.set' % tint_fullpath

    if not os.path.exists(bin_filename) and not os.path.exists(set_filename):

        msg = '[%s %s]: either of the two following files does not exist, skipping conversion: %s\n%s\n' % \
              (str(datetime.datetime.now().date()),
               str(datetime.datetime.now().time())[:8], bin_filename, set_filename)

        if self:
            self.LogAppend.myGUI_signal_str.emit(msg)
        else:
            print(msg)

        raise FileNotFoundError('missing conversion files (.set or .bin)')

    mda_filenames = bin2mda(bin_filename, set_filename, notch_filter=notch_filter)
