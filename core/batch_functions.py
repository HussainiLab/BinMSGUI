import os, datetime, time
from PyQt5 import QtWidgets
from core.intan_mountainsort import convert_bin_mountainsort, validate_session
import json
from core.Tint_Matlab import get_active_tetrode

whiten = 'true'  # do you want to whiten the data?
# whiten = 'false'

detect_interval = 50  # roughly the number of samples to check for a spike
# the algorithm will take the detect_interval value and bin the data in bin sizes of that many
# samples. Then it will find the peak (or trough, or both) of each bin and evaluate that event
# if it exceeds the threshold value.

# recommend only doing positive peaks so we don't get any weird issues with a cell that is
# aligned with the peak, and seemingly the same cell aligned with the trough (in this case
# both peak and trough would have to exceed the threshold).

# detect_sign = 0  # positive or negative peaks
detect_sign = 1  # only positive peaks
# detect_sign = -1  # only negative peaks

# threshold values, I changed it into a whitened and non whitened threshold
# this is because if you whiten the data you normalize it by the variance, thus
# a threshold of 3 is essentially saying 3 standard deviations. However if you do not whiten
# the data is not normalized and thus, you would be using a bit value, maybe should take whatever
# value is in the threshold from the set file.

if whiten == 'true':
    detect_threshold = 3  # units: ~sd's
    # ---------------
    automate_threshold = False  # Don't Change this

else:
    # this mean's the data was not whitened

    detect_threshold = 1000  # units: bits

    # if you want to find the threshold from the .set file and use that
    # set automate_threshold to True, otherwise False. This threshold would override any
    # value set above. I'd recommend setting this to true as this is variable from .set file
    # to .set file it seems.
    automate_threshold = True
    # automate_threshold = False

# bandpass filtering parameters, don't really know this
freq_min = 300  # this doesn't really matter because data is already filtered so it won't do the filtering
freq_max = 7000  # this doesn't really matter because data is already filtered so it won't do the filtering

# artifact masking parameters
# here we bin the data into masked_chunk_size bins, and it will take the sqrt of the sum of
# the squares (RSS) for each bin. It will then find the SD for all the bins, and if the bin is
# above mask_threshold SD's from the average bin RSS, it will consider it as high amplitude noise
# and remove this chunk (and neighboring chunks).

mask_threshold = 6  # units: SD's
masked_chunk_size = None  # if none it will default to Fs/10
mask_num_write_chunks = 100  #

# random parameters, probably don't need to change

clip_size = 50  # this needs to be left at 50 for Tint, Tint only likes 50 samples
notch_filter = False  # the data is already notch filtered likely
self = None  # don't worry about this, this is for objective oriented programming (my GUIs)


def BatchAnalyze(main_window, directory):
    # ------- making a function that runs the entire GUI ----------

    # checks if the settings are appropriate to run analysis
    # klusta_ready = check_klusta_ready(main_window, directory)

    # get settings

    directory = os.path.realpath(directory)

    batch_analysis_ready = True

    if batch_analysis_ready:

        main_window.LogAppend.myGUI_signal_str.emit(
            '[%s %s]: Analyzing the following directory: %s!' % (str(datetime.datetime.now().date()),
                                                                 str(datetime.datetime.now().time())[
                                                                 :8], directory))

        if not main_window.nonbatch:
            # message that shows how many files were found
            main_window.LogAppend.myGUI_signal_str.emit(
                '[%s %s]: Found %d sub-directories in the directory!#Red' % (str(datetime.datetime.now().date()),
                                                               str(datetime.datetime.now().time())[
                                                               :8], main_window.directory_queue.topLevelItemCount()))

        else:
            directory = os.path.dirname(directory)

        if main_window.directory_queue.topLevelItemCount() == 0:
            # main_window.AnalyzeThread.quit()
            # main_window.AddSessionsThread.quit()
            if main_window.nonbatch:
                main_window.choice = ''
                main_window.LogError.myGUI_signal_str.emit('InvDirNonBatch')
                while main_window.choice == '':
                    time.sleep(0.2)
                main_window.stopBatch()
                return
            else:
                main_window.choice = ''
                main_window.LogError.myGUI_signal_str.emit('InvDirBatch')
                while main_window.choice == '':
                    time.sleep(0.2)

                if main_window.choice == QtWidgets.QMessageBox.Abort:
                    main_window.stopBatch()
                    return

        # save directory settings
        with open(main_window.directory_settings, 'w') as filename:
            if not main_window.nonbatch:
                save_directory = directory
            else:
                if main_window.directory_queue.topLevelItemCount() > 0:
                    sub_dir = main_window.directory_queue.topLevelItem(0).data(0, 0)
                    save_directory = os.path.join(directory, sub_dir)
                else:
                    save_directory = directory

            settings = {"directory": save_directory}
            json.dump(settings, filename)

        # ----------- cycle through each file  ------------------------------------------

        while main_window.directory_queue.topLevelItemCount() > 0:

            main_window.directory_item = main_window.directory_queue.topLevelItem(0)

            if not main_window.directory_item:
                continue
            else:
                main_window.current_subdirectory = main_window.directory_item.data(0, 0)

                # check if the directory exists, if not, remove it

                if not os.path.exists(os.path.join(directory, main_window.current_subdirectory)):
                    main_window.top_level_taken = False
                    main_window.RemoveQueueItem.myGUI_signal_str.emit(str(0))
                    while not main_window.top_level_taken:
                        time.sleep(0.1)
                    continue

            while main_window.directory_item.childCount() != 0:

                main_window.current_session = main_window.directory_item.child(0).data(0, 0)
                main_window.child_data_taken = False
                main_window.RemoveSessionData.myGUI_signal_str.emit(str(0))
                while not main_window.child_data_taken:
                    time.sleep(0.1)

                sub_directory = main_window.directory_item.data(0, 0)

                directory_ready = False

                main_window.LogAppend.myGUI_signal_str.emit(
                    '[%s %s]: Checking if the following directory is ready to analyze: %s!' % (
                        str(datetime.datetime.now().date()),
                        str(datetime.datetime.now().time())[
                        :8], str(sub_directory)))

                if main_window.directory_item.childCount() == 0:
                    main_window.top_level_taken = False
                    main_window.RemoveQueueItem.myGUI_signal_str.emit(str(0))
                    while not main_window.top_level_taken:
                        time.sleep(0.1)
                try:

                    if not os.path.exists(os.path.join(directory, sub_directory)):
                        main_window.top_level_taken = False
                        main_window.RemoveQueueItem.myGUI_signal_str.emit(str(0))
                        while not main_window.top_level_taken:
                            time.sleep(0.1)
                        continue
                    else:

                        analysis_directory = os.path.join(directory, main_window.current_subdirectory)

                        bin_file = main_window.current_session
                        bin_fullfile = os.path.join(directory, sub_directory, bin_file + '.bin')

                        tint_basename = os.path.basename(os.path.splitext(bin_fullfile)[0])
                        tint_fullpath = os.path.join(analysis_directory, tint_basename)
                        output_basename = '%s_ms' % tint_fullpath
                        session_valid = validate_session(analysis_directory, tint_basename, output_basename, self=main_window,
                                                         verbose=False)

                        if not session_valid:
                            message = '[%s %s]: The following session has already been analyzed: %s' % (
                                str(datetime.datetime.now().date()),
                                str(datetime.datetime.now().time())[
                                :8], os.path.basename(
                                    tint_fullpath))

                            main_window.LogAppend.myGUI_signal_str.emit(message)
                            continue

                        whiten = main_window.whiten_cb.isChecked()
                        if whiten:
                            whiten = 'true'
                        else:
                            whiten = 'false'

                        detect_sign = main_window.detect_sign

                        detect_threshold = main_window.detect_threshold_widget.value()
                        # version = main_window.version
                        detect_interval = main_window.detect_interval_widget.value()

                        main_window.LogAppend.myGUI_signal_str.emit(
                            '[%s %s]: Analyzing the following basename: %s!' % (
                                str(datetime.datetime.now().date()),
                                str(datetime.datetime.now().time())[
                                :8], tint_basename))

                        convert_bin_mountainsort(analysis_directory, tint_basename, whiten=whiten,
                                                 detect_interval=detect_interval,
                                                 detect_sign=detect_sign,
                                                 detect_threshold=detect_threshold,
                                                 freq_min=freq_min,
                                                 freq_max=freq_max, mask_threshold=mask_threshold,
                                                 masked_chunk_size=masked_chunk_size,
                                                 mask_num_write_chunks=mask_num_write_chunks,
                                                 clip_size=clip_size,
                                                 notch_filter=notch_filter, self=main_window)

                        main_window.analyzed_sessions.append(main_window.current_session)

                        main_window.LogAppend.myGUI_signal_str.emit(
                            '[%s %s]: Finished analyzing the following basename: %s!' % (
                                str(datetime.datetime.now().date()),
                                str(datetime.datetime.now().time())[
                                :8], tint_basename))

                except NotADirectoryError:
                    # if the file is not a directory it prints this message
                    main_window.LogAppend.myGUI_signal_str.emit(
                        '[%s %s]: %s is not a directory!' % (
                            str(datetime.datetime.now().date()),
                            str(datetime.datetime.now().time())[
                            :8], str(sub_directory)))
                    continue
