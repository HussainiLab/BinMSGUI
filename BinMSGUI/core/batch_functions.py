import os, datetime, time
import json
from PyQt5 import QtWidgets

from core.intan_mountainsort import convert_bin_mountainsort, validate_session
from core.default_parameters import self


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
                        session_valid = validate_session(analysis_directory, tint_basename, output_basename,
                                                         self=main_window,
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
                                                 notch_filter=notch_filter, pre_spike=pre_spike, post_spike=post_spike,
                                                 mask=mask,
                                                 num_features=num_features,
                                                 max_num_clips_for_pca=max_num_clips_for_pca,
                                                 self=main_window)

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
