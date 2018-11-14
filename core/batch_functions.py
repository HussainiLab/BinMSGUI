import os, datetime, time
from PyQt4 import QtGui
from core.intan_mountainsort import intan_mountainsort, find_sub
import json
from core.Tint_Matlab import get_active_tetrode


def find_tetrodes(session, directory):
    """returns a list of tetrode files given a session and directory name"""
    session_basename = os.path.splitext(session)[0]

    invalid_types = ['.clu', '.eeg', '.egf', '.set', '.cut', '.fmask', '.fet', '.klg', '.pos', '.SET', '.ini', '.txt']
    tetrodes = [file for file in os.listdir(directory)
                if not any(x in file for x in invalid_types) and not os.path.isdir(os.path.join(directory, file))
                and is_tetrode(file, session_basename)]

    # valid_tetrodes = [file for file in tetrodes if has_cut(directory, session_basename, file)]
    valid_tetrodes = [file for file in tetrodes if is_valid_tetrode(directory, session_basename, file)]

    return valid_tetrodes


def is_valid_tetrode(directory, session_basename, tetrode_filename):
    tetrode = int(os.path.splitext(tetrode_filename)[1][1:])
    set_filename = os.path.join(directory, '%s.set' % session_basename)

    active_tetrodes = get_active_tetrode(set_filename)

    if tetrode in active_tetrodes:
        return True
    return False


def has_cut(directory, session_basename, tetrode_filename):
    # this is deprecated
    tetrode = int(os.path.splitext(tetrode_filename)[1][1:])
    cut_filename = os.path.join(directory, '%s_%d.cut' % (session_basename, tetrode))
    if os.path.exists(cut_filename):
        return True
    return False


def is_tetrode(file, session):

    if os.path.splitext(file)[0] == session:
        try:
            _ = int(os.path.splitext(file)[1][1:])
            return True
        except ValueError:
            return False
    else:
        return False


def session_analyzable(directory, session, tetrodes, version, whiten=True):

    cut_created = 0

    if '.set' in session:
        session = os.path.splitext(session)[0]

    name_valid = validate_sesssion_name(session)

    if not name_valid:
        return False

    for tetrode_file in tetrodes:
        tetrode = int(os.path.splitext(tetrode_file)[1][1:])

        if whiten:
            cut_filename = os.path.join(directory, '%s_%d_%s.cut' % (session, tetrode, version))
        else:
            cut_filename = os.path.join(directory, '%s_nowhiten_%d_%s.cut' % (session, tetrode, version))

        if os.path.exists(cut_filename):
            cut_created += 1
    if len(tetrodes) != cut_created:
        return True
    return False


def validate_sesssion_name(session):

    invalid_characters = [' ', '(', ')']

    if any(x in session for x in invalid_characters):
        return False
    return True


def BatchAnalyze(main_window, directory):
    # ------- making a function that runs the entire GUI ----------
    '''
    def __init__(self, main_window, directory):
        QtCore.QThread.__init__(self)
        self.main_window = main_window
        self.directory = directory

    def __del__(self):
        self.wait()

    def run(self):
    '''

    # checks if the settings are appropriate to run analysis
    # klusta_ready = check_klusta_ready(main_window, directory)

    # get settings

    batch_analysis_ready = True

    if batch_analysis_ready:

        main_window.LogAppend.myGUI_signal_str.emit(
            '[%s %s]: Analyzing the following directory: %s!' % (str(datetime.datetime.now().date()),
                                                                 str(datetime.datetime.now().time())[
                                                                 :8], directory))

        if not main_window.nonbatch.isChecked():
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
            if main_window.nonbatch.isChecked():
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

                if main_window.choice == QtGui.QMessageBox.Abort:
                    main_window.stopBatch()
                    return

        # save directory settings
        with open(main_window.directory_settings, 'w') as filename:
            if not main_window.nonbatch.isChecked():
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
        # for sub_directory in sub_directories:  # finding all the folders within the directory

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
                    # main_window.directory_queue.takeTopLevelItem(0)
                    continue

            while main_window.directory_item.childCount() != 0:

                # set_file = []
                # for child_count in range(main_window.directory_item.childCount()):
                #     set_file.append(main_window.directory_item.child(child_count).data(0, 0))
                main_window.current_session = main_window.directory_item.child(0).data(0, 0)
                main_window.child_data_taken = False
                main_window.RemoveSessionData.myGUI_signal_str.emit(str(0))
                while not main_window.child_data_taken:
                    time.sleep(0.1)
                # main_window.directory_item.takeChild(0).data(0, 0)

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
                    # main_window.directory_queue.takeTopLevelItem(0)

                try:

                    if not os.path.exists(os.path.join(directory, sub_directory)):
                        main_window.top_level_taken = False
                        main_window.RemoveQueueItem.myGUI_signal_str.emit(str(0))
                        while not main_window.top_level_taken:
                            time.sleep(0.1)
                        # main_window.directory_queue.takeTopLevelItem(0)
                        continue
                    else:
                        analysis_directory = os.path.join(directory, main_window.current_subdirectory)

                        rhd_session_file = main_window.current_session

                        pre_threshold = main_window.pre_threshold_widget.value()
                        post_threshold = main_window.post_threshold_widget.value()
                        curated = main_window.curated_cb.isChecked()
                        whiten = main_window.whiten_cb.isChecked()
                        detect_sign = main_window.detect_sign
                        detect_threshold = main_window.detect_threshold_widget.value()
                        version = main_window.version
                        detect_interval = main_window.detect_interval_widget.value()

                        main_window.LogAppend.myGUI_signal_str.emit(
                            '[%s %s]: Analyzing the following basename: %s!' % (
                                str(datetime.datetime.now().date()),
                                str(datetime.datetime.now().time())[
                                :8], rhd_session_file))

                        intan_mountainsort(analysis_directory, rhd_session_file, pre_threshold=pre_threshold,
                                           post_threshold=post_threshold, detect_sign=detect_sign,
                                           adjacency_radius=-1, whiten=whiten, detect_threshold=detect_threshold,
                                           self=main_window, detect_interval=detect_interval)

                        main_window.LogAppend.myGUI_signal_str.emit(
                            '[%s %s]: Finished analyzing the following basename: %s!' % (
                                str(datetime.datetime.now().date()),
                                str(datetime.datetime.now().time())[
                                :8], rhd_session_file))

                except NotADirectoryError:
                    # if the file is not a directory it prints this message
                    main_window.LogAppend.myGUI_signal_str.emit(
                        '[%s %s]: %s is not a directory!' % (
                            str(datetime.datetime.now().date()),
                            str(datetime.datetime.now().time())[
                            :8], str(sub_directory)))
                    continue