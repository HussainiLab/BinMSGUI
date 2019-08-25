import os, datetime, time
import json
from PyQt5 import QtWidgets

from core.intan_mountainsort import convert_bin_mountainsort, validate_session
from core.default_parameters import mask_num_write_chunks, clip_size, freq_min, freq_max, notch_filter


def raise_error(main_window, error_action):
    main_window.choice = None
    main_window.LogError.myGUI_signal_str.emit(error_action)
    while main_window.choice is None:
        time.sleep(0.2)
    return main_window.choice


def BatchAnalyze(main_window, directory):
    # ------- making a function that runs the entire GUI ----------

    # checks if the settings are appropriate to run analysis

    # get settings

    directory = os.path.realpath(directory)

    batch_analysis_ready = True

    if batch_analysis_ready:

        main_window.LogAppend.myGUI_signal_str.emit(
            '[%s %s]: Analyzing the following directory: %s!' % (str(datetime.datetime.now().date()),
                                                                 str(datetime.datetime.now().time())[
                                                                 :8], directory))

        if not main_window.nonbatch_check.isChecked():
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
            if main_window.nonbatch_check.isChecked():
                choice = raise_error(main_window, 'InvDirNonBatch')
                main_window.terminate_signal.myGUI_signal_str.emit("emit")
                return
            else:
                choice = raise_error(main_window, 'InvDirBatch')
                if choice == QtWidgets.QMessageBox.Abort:
                    main_window.terminate_signal.myGUI_signal_str.emit("emit")
                    return

        # save directory settings
        with open(main_window.directory_settings, 'w') as filename:
            if not main_window.nonbatch_check.isChecked():
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
                    main_window.modifying_list = True
                    main_window.RemoveQueueItem.myGUI_signal_str.emit(str(0))
                    while not main_window.top_level_taken:
                        time.sleep(0.1)
                    main_window.modifying_list = False
                    continue

            while main_window.directory_item.childCount() != 0:

                sub_directory = main_window.directory_item.data(0, 0)

                main_window.LogAppend.myGUI_signal_str.emit(
                    '[%s %s]: Checking if the following directory is ready to analyze: %s!' % (
                        str(datetime.datetime.now().date()),
                        str(datetime.datetime.now().time())[
                        :8], str(sub_directory)))

                main_window.current_session = main_window.directory_item.child(0).data(0, 0)

                try:
                    if not os.path.exists(os.path.join(directory, sub_directory)):
                        main_window.top_level_taken = False
                        main_window.modifying_list = True
                        main_window.RemoveQueueItem.myGUI_signal_str.emit(str(0))
                        while not main_window.top_level_taken:
                            time.sleep(0.1)
                        main_window.modifying_list = False
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

                            main_window.child_data_taken = False
                            main_window.modifying_list = True
                            main_window.RemoveSessionData.myGUI_signal_str.emit(str(0))
                            while not main_window.child_data_taken:
                                time.sleep(0.1)
                            main_window.modifying_list = False
                            continue

                        whiten = main_window.whiten_cb.isChecked()
                        if whiten:
                            whiten = 'true'
                        else:
                            whiten = 'false'

                        detect_sign = main_window.detect_sign_combo.currentText()
                        if 'Pos' in detect_sign and "Neg" in detect_sign:
                            detect_sign = 0
                        elif 'Pos' in detect_sign:
                            detect_sign = 1
                        elif 'Neg' in detect_sign:
                            detect_sign = -1

                        detect_threshold = main_window.detect_threshold_widget.text()
                        detect_interval = main_window.detect_interval_widget.text()

                        main_window.LogAppend.myGUI_signal_str.emit(
                            '[%s %s]: Analyzing the following basename: %s!' % (
                                str(datetime.datetime.now().date()),
                                str(datetime.datetime.now().time())[
                                :8], tint_basename))

                        mask = main_window.masked_cb.isChecked()
                        mask_threshold = int(main_window.mask_threshold.text())
                        masked_chunk_size = int(main_window.mask_chunk_size.text())

                        pre_spike = main_window.pre_threshold_widget.value()
                        post_spike = main_window.post_threshold_widget.value()

                        if clip_size != 50:
                            choice = raise_error(main_window, 'invalid_clip_size')
                            main_window.terminate_signal.myGUI_signal_str.emit("emit")
                            return

                        if post_spike + pre_spike != clip_size:
                            choice = raise_error(main_window, 'pre/post_spike')
                            main_window.terminate_signal.myGUI_signal_str.emit("emit")
                            return

                        num_features = int(main_window.num_features.text())
                        max_num_clips_for_pca = int(main_window.max_num_pca_clips.text())

                        convert_bin_mountainsort(analysis_directory, tint_basename, whiten=whiten,
                                                 detect_interval=detect_interval,
                                                 detect_sign=detect_sign,
                                                 detect_threshold=detect_threshold,
                                                 freq_min=freq_min,
                                                 freq_max=freq_max,
                                                 mask=mask,
                                                 mask_threshold=mask_threshold,
                                                 masked_chunk_size=masked_chunk_size,
                                                 mask_num_write_chunks=mask_num_write_chunks,
                                                 clip_size=clip_size,
                                                 notch_filter=notch_filter,
                                                 pre_spike=pre_spike,
                                                 post_spike=post_spike,
                                                 num_features=num_features,
                                                 max_num_clips_for_pca=max_num_clips_for_pca,
                                                 self=main_window,
                                                 verbose=False)

                        main_window.analyzed_sessions.append(main_window.current_session)

                        main_window.child_data_taken = False
                        main_window.modifying_list = True
                        main_window.RemoveSessionData.myGUI_signal_str.emit(str(0))
                        while not main_window.child_data_taken:
                            time.sleep(0.1)
                        main_window.modifying_list = False

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

            # remove the directory as there are no more children
            if main_window.directory_item.childCount() == 0:
                main_window.top_level_taken = False
                main_window.modifying_list = True
                main_window.RemoveQueueItem.myGUI_signal_str.emit(str(0))
                while not main_window.top_level_taken:
                    time.sleep(0.1)
                main_window.modifying_list = False
