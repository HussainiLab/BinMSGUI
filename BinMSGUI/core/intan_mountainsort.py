import os
import datetime
from core.readBin import get_active_tetrode, get_active_eeg
from core.tetrode_conversion import batch_basename_tetrodes
from core.convert_position import convert_position
from core.eeg_conversion import convert_eeg
from core.utils import find_sub
from core.bin2mda import convert_bin2mda
from core.mdaSort import sort_bin
from core.set_conversion import convert_setfile


def validate_session(directory, tint_basename, output_basename, self=None, verbose=True):
    """
    This will return an output of True if you should continue to convert this session,
    otherwise it is convertable.
    """

    output_basename = os.path.basename(output_basename)

    # first check if this session has the necessary files

    bin_filename = '%s.bin' % os.path.join(directory, tint_basename)
    set_filename = '%s.set' % os.path.join(directory, tint_basename)

    # check if there is a position file

    if not os.path.exists(bin_filename):
        # there is no .bin filename.
        if verbose:
            msg = '[%s %s]: There is no .bin file, skipping the following basename: %s!' % \
                  (str(datetime.datetime.now().date()),
                   str(datetime.datetime.now().time())[:8], tint_basename)
            if self:
                self.LogAppend.myGUI_signal_str.emit(msg)
            else:
                print(msg)

        return False

    if not os.path.exists(set_filename):
        # there is no .bin filename.
        if verbose:
            msg = '[%s %s]: There is no .set file, skipping the following basename: %s!' % \
                  (str(datetime.datetime.now().date()),
                   str(datetime.datetime.now().time())[:8], tint_basename)
            if self:
                self.LogAppend.myGUI_signal_str.emit(msg)
            else:
                print(msg)

        return False

        # check that all the files haven't already been converted

    # check that all tetrodes haven't already been created
    converted_files = 0
    n_tetrodes = 0

    tetrodes = get_active_tetrode(set_filename)

    for tetrode in tetrodes:

        # mda_filename = '%s_T%d_filt.mda' % (os.path.join(directory, tint_basename), tetrode)
        mda_filename = '%s_T%d_firings.mda' % (os.path.join(directory, tint_basename), tetrode)

        if os.path.exists(mda_filename):
            converted_files += 1

        n_tetrodes += 1

    if n_tetrodes != converted_files:
        return True

    # check that all the tetrodes have been converted
    # raw_fnames = [os.path.join(directory, file) for file in os.listdir(
    #     directory) if '_filt.mda' in file if tint_basename in file]

    firing_fnames = [os.path.join(directory, file) for file in os.listdir(
        directory) if '_firings.mda' in file if tint_basename in file]

    eeg_filenames = []
    egf_filenames = []

    # for file in raw_fnames:
    for file in firing_fnames:
        mda_basename = os.path.splitext(file)[0]
        mda_basename = mda_basename[:find_sub(mda_basename, '_')[-1]]

        # masked file no longer required
        # masked_out_fname = mda_basename + '_masked.mda'
        # firings_out = mda_basename + '_firings.mda'
        firings_out = file

        # we will skip the pre_out because if the user decided not to whiten, then this wouldn't be there
        # pre_out_fname = mda_basename + '_pre.mda'
        metrics_out_fname = mda_basename + '_metrics.json'

        # check if these outputs have already been created, skip if they have
        existing_files = 0
        output_files = [firings_out,
                        metrics_out_fname,
                        # masked_out_fname,
                        ]
        for outfile in output_files:
            if os.path.exists(outfile):
                existing_files += 1
            else:
                pass

        if existing_files != len(output_files):
            # then the file has not already been sorted, return True
            return True

    eeg_dict = get_active_eeg(set_filename)

    eeg_channels = eeg_dict.keys()

    for eeg_number in eeg_channels:

        if eeg_number == 1:
            eeg_filename = os.path.join(directory, output_basename + '.eeg')
            egf_filename = os.path.join(directory, output_basename + '.egf')
        else:
            eeg_filename = os.path.join(directory, output_basename + '.eeg%d' % (eeg_number))
            egf_filename = os.path.join(directory, output_basename + '.egf%d' % (eeg_number))

        eeg_filenames.append(eeg_filename)
        egf_filenames.append(egf_filename)

    # already checked if position file exists so we don't need to do that

    # check if tetrodes/cut files have been converted already
    filt_fnames = [os.path.join(directory, file) for file in os.listdir(
        directory) if '_filt.mda' in file if os.path.basename(tint_basename) in file]

    for filt_filename in filt_fnames:
        mda_basename = os.path.splitext(filt_filename)[0]
        mda_basename = mda_basename[:find_sub(mda_basename, '_')[-1]]

        tetrode = int(mda_basename[find_sub(mda_basename, '_')[-1] + 2:])
        tetrode_filepath = '%s.%d' % (os.path.join(directory, output_basename), tetrode)

        if not os.path.exists(tetrode_filepath):
            # the tetrode has not been created yet, return True
            return True

        cut_filename = '%s_%d.cut' % (os.path.join(directory, output_basename), tetrode)

        if not os.path.exists(cut_filename):
            # the cut file has not been created yet, return True
            return True

            # check if set file has been converted
    set_filename = '%s.set' % os.path.join(directory, output_basename)
    if not os.path.exists(set_filename):
        return True

    # check if the .eeg/.egf files have been created yet
    for file in eeg_filenames:
        if not os.path.exists(file):
            # the eeg file does not exist
            return True

    for file in egf_filenames:
        if not os.path.exists(file):
            # the egf file does not exist
            return True

    # if you made it this far, then everything has been converted, return False
    return False


def cleanup_files(directory, tint_basename, delete_pre=True, delete_firings=False, delete_masked=True,
                  delete_filt=True, delete_raw=True):
    """
    This function will iterate through files that were created, and delete files that we don't need just to save space.
    :return:
    """
    delete_files = []

    if delete_pre:
        pre_filenames = [os.path.join(directory, file) for file in os.listdir(
            directory) if '_pre.mda' in file if os.path.basename(tint_basename) in file]
        delete_files.extend(pre_filenames)

    if delete_firings:
        firing_filenames = [os.path.join(directory, file) for file in os.listdir(
            directory) if '_firings.mda' in file if os.path.basename(tint_basename) in file]
        delete_files.extend(firing_filenames)

    if delete_masked:
        masked_filenames = [os.path.join(directory, file) for file in os.listdir(
            directory) if '_masked.mda' in file if os.path.basename(tint_basename) in file]
        delete_files.extend(masked_filenames)

    if delete_filt:
        filt_filenames = [os.path.join(directory, file) for file in os.listdir(
            directory) if '_filt.mda' in file if os.path.basename(tint_basename) in file]
        delete_files.extend(filt_filenames)

    if delete_raw:
        filt_filenames = [os.path.join(directory, file) for file in os.listdir(
            directory) if '_raw.mda' in file if os.path.basename(tint_basename) in file]
        delete_files.extend(filt_filenames)

    if len(delete_files) > 0:
        for file in delete_files:
            os.remove(file)


def convert_bin_mountainsort(directory, tint_basename, whiten='true', detect_interval=10, detect_sign=0,
                             detect_threshold=3, freq_min=300, freq_max=6000, mask_threshold=6,
                             masked_chunk_size=None, mask_num_write_chunks=100, clip_size=50, notch_filter=False,
                             pre_spike=15, post_spike=35, mask=True, num_features=10, max_num_clips_for_pca=1000,
                             self=None, verbose=True):

    tint_fullpath = os.path.join(directory, tint_basename)

    output_basename = '%s_ms' % tint_fullpath

    session_valid = validate_session(directory, tint_basename, output_basename, self=self)

    if not session_valid:
        msg = '[%s %s]: The following session has already been analyzed: %s!' % \
              (str(datetime.datetime.now().date()),
               str(datetime.datetime.now().time())[:8], tint_basename)
        if self:
            self.LogAppend.myGUI_signal_str.emit(msg)
        else:
            print(msg)

    pos_filename = output_basename + '.pos'
    set_filename = tint_fullpath + '.set'
    bin_filename = tint_fullpath + '.bin'

    converted_set_filename = output_basename + '.set'

    convert_setfile(set_filename, converted_set_filename, self=self)

    # convert data to mda
    convert_bin2mda(tint_fullpath, notch_filter=notch_filter, self=self)

    # sort the mda data
    sort_bin(directory, tint_fullpath, whiten=whiten, detect_interval=detect_interval,
             detect_sign=detect_sign,
             detect_threshold=detect_threshold,
             freq_min=freq_min,
             freq_max=freq_max,
             mask_threshold=mask_threshold,
             masked_chunk_size=masked_chunk_size,
             mask_num_write_chunks=mask_num_write_chunks,
             clip_size=clip_size,
             mask=mask,
             num_features=num_features,
             max_num_clips_for_pca=max_num_clips_for_pca,
             self=self,
             verbose=verbose)

    # create positions
    convert_position(bin_filename, pos_filename, converted_set_filename, self=self)

    # create tetrodes / cut
    batch_basename_tetrodes(directory, tint_basename, output_basename,  pre_spike=pre_spike, post_spike=post_spike,
                            mask=mask, self=self)

    # create eeg / egf
    convert_eeg(set_filename, output_basename, self=self)

    msg = '[%s %s]: Finished converting the following session: %s!' % \
          (str(datetime.datetime.now().date()),
           str(datetime.datetime.now().time())[:8], tint_basename)
    if self:
        self.LogAppend.myGUI_signal_str.emit(msg)
    else:
        print(msg)

    # clean up any files to save space
    if mask:
        delete_masked = False
        delete_filt = True
    else:
        delete_filt = False
        delete_masked = True

    # we will always delete the preprocessed data, we have the output from the sorting so we won't really need it
    # we will save the firings in case we want to view the data in MountainView, and if the user decides to mask
    # the data we will delete the filt and keep the mask. If the user decides not to mask, we will keep the filtered
    # and delete the masked which won't exist anyways.

    msg = '[%s %s]: Deleting unnecessary intermediate files from MountainSort.' % \
          (str(datetime.datetime.now().date()),
           str(datetime.datetime.now().time())[:8])
    if self:
        self.LogAppend.myGUI_signal_str.emit(msg)
    else:
        print(msg)

    cleanup_files(directory, tint_basename, delete_pre=True, delete_firings=False, delete_masked=delete_masked,
                  delete_filt=delete_filt, delete_raw=True)
