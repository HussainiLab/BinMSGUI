import sys, os, json, time
# from PIL import Image
from PyQt5 import QtCore, QtWidgets
from core.batch_functions import BatchAnalyze
from core.gui_utils import background, gui_name, center
from core.ChooseDirectory import Choose_Dir
from core.addSessions import RepeatAddSessions
from BinMSGUI.core.default_parameters import pre_spike, post_spike, detect_sign, detect_threshold, detect_interval


_author_ = "Geoffrey Barrett"  # defines myself as the author

Large_Font = ("Verdana", 12)  # defines two fonts for different purposes (might not be used
Small_Font = ("Verdana", 8)


class Window(QtWidgets.QWidget):  # defines the window class (main window)

    def __init__(self):  # initializes the main window
        super(Window, self).__init__()
        # self.setGeometry(50, 50, 500, 300)
        background(self)  # acquires some features from the background function we defined earlier

        self.setWindowTitle("%s - Main Window" % gui_name)  # sets the title of the window
        self.current_session = ''
        self.current_subdirectory = ''
        self.analyzed_sessions = []

        self.LogAppend = Communicate()
        self.LogAppend.myGUI_signal_str.connect(self.AppendLog)

        self.LogError = Communicate()
        self.LogError.myGUI_signal_str.connect(self.raiseError)

        self.RemoveQueueItem = Communicate()
        self.RemoveQueueItem.myGUI_signal_str.connect(self.takeTopLevel)

        self.RemoveSessionItem = Communicate()
        self.RemoveSessionItem.myGUI_signal_str.connect(self.takeChild)

        self.RemoveSessionData = Communicate()
        self.RemoveSessionData.myGUI_signal_str.connect(self.takeChildData)

        self.RemoveChildItem = Communicate()
        self.RemoveChildItem.myGUI_signal_QTreeWidgetItem.connect(self.removeChild)

        self.adding_session = True
        self.reordering_queue = False

        self.reset_add_thread = False
        self.repeat_thread_active = False

        self.RepeatAddSessionsThread = QtCore.QThread()
        self.AnalyzeThread = QtCore.QThread()

        self.choice = ''
        self.home()  # runs the home function

    def home(self):  # defines the home function (the main window)

        try:  # attempts to open previous directory catches error if file not found
            # No saved directory's need to create file
            with open(self.directory_settings, 'r+') as filename:  # opens the defined file
                directory_data = json.load(filename)  # loads the directory data from file
                if os.path.exists(directory_data['directory']):
                    current_directory_name = directory_data['directory']  # defines the data
                else:
                    current_directory_name = 'No Directory Currently Chosen!'  # states that no directory was chosen

        except FileNotFoundError:  # runs if file not found
            with open(self.directory_settings, 'w') as filename:  # opens a file
                current_directory_name = 'No Directory Currently Chosen!'  # states that no directory was chosen
                directory_data = {'directory': current_directory_name}  # creates a dictionary
                json.dump(directory_data, filename)  # writes the dictionary to the file

        # -------- settings widgets ------------------------
        self.pre_threshold_widget = QtWidgets.QSpinBox()
        pre_threshold_layout = QtWidgets.QHBoxLayout()
        pre_threshold_layout.addWidget(QtWidgets.QLabel("Pre-Spike Samples:"))
        pre_threshold_layout.addWidget(self.pre_threshold_widget)
        self.pre_threshold_widget.setMinimum(0)
        self.pre_threshold_widget.setMaximum(50)
        self.pre_threshold_widget.setValue(pre_spike)

        self.post_threshold_widget = QtWidgets.QSpinBox()
        post_threshold_layout = QtWidgets.QHBoxLayout()
        post_threshold_layout.addWidget(QtWidgets.QLabel("Post-Spike Samples:"))
        post_threshold_layout.addWidget(self.post_threshold_widget)
        self.post_threshold_widget.setMinimum(0)
        self.post_threshold_widget.setMaximum(50)
        self.post_threshold_widget.setValue(post_spike)

        self.curated_cb = QtWidgets.QCheckBox("Curated")
        self.curated_cb.toggle()  # default it to curated

        self.detect_sign_combo = QtWidgets.QComboBox()
        self.detect_sign_combo.addItem("Positive Peaks")
        self.detect_sign_combo.addItem("Negative Peaks")
        self.detect_sign_combo.addItem("Positive and Negative Peaks")
        self.detect_sign_combo.currentIndexChanged.connect(self.detect_sign_changed)
        self.detect_sign = detect_sign  # initializing detect_sign value

        text_value = None
        if detect_sign == 0:
            text_value = 'Positive and Negative Peaks'
        elif detect_sign == 1:
            text_value = 'Positive Peaks'
        elif detect_sign == -1:
            text_value = 'Negative Peaks'

        self.detect_sign_combo.setCurrentIndex(self.detect_sign_combo.findText(text_value))

        detect_sign_layout = QtWidgets.QHBoxLayout()
        detect_sign_layout.addWidget(QtWidgets.QLabel("Detect Sign:"))
        detect_sign_layout.addWidget(self.detect_sign_combo)

        self.detect_threshold_widget = QtWidgets.QLineEdit()
        detect_threshold_layout = QtWidgets.QHBoxLayout()
        detect_threshold_layout.addWidget(QtWidgets.QLabel("Detect Threshold:"))
        detect_threshold_layout.addWidget(self.detect_threshold_widget)
        self.detect_threshold_widget.setText(str(detect_threshold))

        self.whiten_cb = QtWidgets.QCheckBox('Whiten')
        self.whiten_cb.toggle()  # set the default to whiten
        self.whiten_cb.stateChanged.connect(self.changed_whiten)

        self.detect_interval_widget = QtWidgets.QSpinBox()
        detect_interval_layout = QtWidgets.QHBoxLayout()
        detect_interval_layout.addWidget(QtWidgets.QLabel("Detect Interval:"))
        detect_interval_layout.addWidget(self.detect_interval_widget)
        self.detect_interval_widget.setValue(detect_interval)

        self.version_combo = QtWidgets.QComboBox()
        self.version_combo.addItem("MountainSort3")
        self.version_combo.addItem("MountainSort-Js")
        self.version_combo.currentIndexChanged.connect(self.version_changed)
        self.version = 'js'
        self.version_combo.setCurrentIndex(1)  # set default js

        version_layout = QtWidgets.QHBoxLayout()
        version_layout.addWidget(QtWidgets.QLabel("Version:"))
        version_layout.addWidget(self.version_combo)

        ms_settings_layout = QtWidgets.QVBoxLayout()

        settings_layer1 = QtWidgets.QHBoxLayout()
        settings_layer2 = QtWidgets.QHBoxLayout()

        settings_layer1.addStretch(1)
        settings_layer2.addStretch(1)

        layer1_widgets = [pre_threshold_layout, post_threshold_layout, self.curated_cb, self.whiten_cb]
        layer2_widgets = [detect_sign_layout, detect_threshold_layout, detect_interval_layout, version_layout]

        for widget in layer1_widgets:
            if 'Layout' in str(widget):
                settings_layer1.addLayout(widget)
            else:
                settings_layer1.addWidget(widget)
            settings_layer1.addStretch(1)

        for widget in layer2_widgets:
            if 'Layout' in str(widget):
                settings_layer2.addLayout(widget)
            else:
                settings_layer2.addWidget(widget)
            settings_layer2.addStretch(1)

        ms_settings_layout.addLayout(settings_layer1)
        ms_settings_layout.addLayout(settings_layer2)

        # ------buttons ------------------------------------------
        quitbtn = QtWidgets.QPushButton('Quit', self)  # making a quit button
        quitbtn.clicked.connect(self.close_app)  # defining the quit button functionality (once pressed)
        quitbtn.setShortcut("Ctrl+Q")  # creates shortcut for the quit button
        quitbtn.setToolTip('Click to quit!')

        self.run_btn = QtWidgets.QPushButton('Run', self)  # creates the batch-klusta pushbutton
        self.run_btn.setToolTip('Click to perform batch analysis!')

        self.choose_directory = QtWidgets.QPushButton('Choose Directory', self)  # creates the choose directory pushbutton

        self.current_directory = QtWidgets.QLineEdit()  # creates a line edit to display the chosen directory (current)
        self.current_directory.setText(current_directory_name)  # sets the text to the current directory
        self.current_directory.setAlignment(QtCore.Qt.AlignHCenter)  # centers the text
        self.current_directory.setToolTip('The current directory that will undergo batch analysis.')
        self.current_directory.textChanged.connect(self.changed_directory)
        self.current_directory_name = self.current_directory.text()

        self.nonbatch_check = QtWidgets.QCheckBox('Non-Batch?')
        self.nonbatch = 0
        self.nonbatch_check.setToolTip("Check this if you don't want to run batch. This means you will choose\n"
                                 "the folder that directly contains all the session files (.set, .pos, .N, etc.).")

        current_directory_layout = QtWidgets.QHBoxLayout()

        for widget in [self.choose_directory, self.current_directory, self.nonbatch_check]:
            current_directory_layout.addWidget(widget)

        # defines an attribute to exchange info between classes/modules
        self.current_directory_name = current_directory_name

        # defines the button functionality once pressed
        self.run_btn.clicked.connect(lambda: self.run(self.current_directory_name))

        # ---------------- queue widgets --------------------------------------------------
        self.directory_queue = QtWidgets.QTreeWidget()
        self.directory_queue.headerItem().setText(0, "Intan Sessions:")
        self.directory_queue.setSelectionMode(QtWidgets.QAbstractItemView.MultiSelection)
        directory_queue_label = QtWidgets.QLabel('Queue: ')

        self.up_btn = QtWidgets.QPushButton("Move Up", self)
        self.up_btn.setToolTip("Clcik this button to move selected directories up on the queue!")
        self.up_btn.clicked.connect(lambda: self.moveQueue('up'))

        self.down_btn = QtWidgets.QPushButton("Move Down", self)
        self.down_btn.setToolTip("Clcik this button to move selected directories down on the queue!")
        self.down_btn.clicked.connect(lambda: self.moveQueue('down'))

        queue_btn_layout = QtWidgets.QVBoxLayout()
        queue_btn_layout.addWidget(self.up_btn)
        queue_btn_layout.addWidget(self.down_btn)

        queue_layout = QtWidgets.QVBoxLayout()
        queue_layout.addWidget(directory_queue_label)
        queue_layout.addWidget(self.directory_queue)

        queue_and_btn_layout = QtWidgets.QHBoxLayout()
        queue_and_btn_layout.addLayout(queue_layout)
        queue_and_btn_layout.addLayout(queue_btn_layout)

        try:
            with open(self.settings_fname, 'r+') as filename:
                settings = json.load(filename)
                if settings['nonbatch'] == 1:
                    self.nonbatch_check.toggle()

        except FileNotFoundError:
            with open(self.settings_fname, 'w') as filename:
                settings = {'nonbatch': 0}
                json.dump(settings, filename)
        except ValueError:
            # This is a strange problem where the file was overwritten and probably has nothing in it
            with open(self.settings_fname, 'w') as filename:
                settings = {'nonbatch': 0}
                json.dump(settings, filename)

        # ------------- Log Box -------------------------
        self.Log = QtWidgets.QTextEdit()
        log_label = QtWidgets.QLabel('Log: ')

        log_lay = QtWidgets.QVBoxLayout()
        log_lay.addWidget(log_label, 0, QtCore.Qt.AlignTop)
        log_lay.addWidget(self.Log)

        # ------------------------------------ version information -------------------------------------------------
        # finds the modification date of the program

        mod_date = time.ctime(os.path.getmtime(__file__))

        # creates a label with that information
        vers_label = QtWidgets.QLabel(("%s V1.0 - Last Updated: " % gui_name) + mod_date)

        # ------------------- page layout ----------------------------------------

        btn_order = [self.run_btn, quitbtn]  # defining button order (left to right)
        btn_layout = QtWidgets.QHBoxLayout()  # creating a widget to align the buttons
        for butn in btn_order:  # adds the buttons in the proper order
            btn_layout.addWidget(butn)

        layout_order = [current_directory_layout, queue_and_btn_layout, ms_settings_layout, log_lay, btn_layout]

        layout = QtWidgets.QVBoxLayout()
        layout.addStretch(1)  # adds the widgets/layouts according to the order
        for order in layout_order:
            if 'Layout' in order.__str__():
                layout.addLayout(order)
                layout.addStretch(1)
            else:
                layout.addWidget(order, 0, QtCore.Qt.AlignCenter)
                layout.addStretch(1)

        layout.addStretch(1)  # adds stretch to put the version info at the bottom
        layout.addWidget(vers_label)  # adds the date modification/version number
        self.setLayout(layout)  # sets the widget to the one we defined

        center(self)  # centers the widget on the screen

        # if self.current_directory_name != 'No Directory Currently Chosen!':
        # starting adding any existing sessions in a different thread
        # self.RepeatAddSessionsThread = QtCore.QThread()
        self.RepeatAddSessionsThread.start()

        self.RepeatAddSessionsWorker = Worker(RepeatAddSessions, self)
        self.RepeatAddSessionsWorker.moveToThread(self.RepeatAddSessionsThread)
        self.RepeatAddSessionsWorker.start.emit("start")

        self.show()  # shows the widget

    def detect_sign_changed(self):

        current_value = self.detect_sign_combo.currentText()

        if 'Pos' in current_value and "Neg" in current_value:
            self.detect_sign = 0
        elif 'Pos' in current_value:
            self.detect_sign = 1
        elif 'Neg' in current_value:
            self.detect_sign = -1
        else:
            self.LogAppend.myGUI_signal_str.emit('detect sign value does not exist')

    def version_changed(self):
        current_value = self.version_combo.currentText()

        if hasattr(self, 'directory_queue'):
            self.analyzed_sessions = []
            self.directory_queue.clear()
            self.restart_add_sessions_thread()

        if 'MountainSort3' in current_value:
            self.version = 'ms3'
        elif 'MountainSort-Js' in current_value:
            self.version = 'js'
        else:
            self.LogAppend.myGUI_signal_str.emit('Version value does not exist')

    def run(self, directory):  # function that runs klustakwik

        """This method runs when the Run button is pressed on the GUI,
        and commences the analysis"""

        self.run_btn.setText('Stop')
        self.run_btn.setToolTip('Click to stop analysis.')  # defining the tool tip for the start button
        self.run_btn.clicked.disconnect()
        self.run_btn.clicked.connect(self.stopBatch)

        # self.AnalyzeThread = QtCore.QThread()
        self.AnalyzeThread.start()

        self.AnalyzeWorker = Worker(BatchAnalyze, self, directory)
        self.AnalyzeWorker.moveToThread(self.AnalyzeThread)
        self.AnalyzeWorker.start.emit("start")

    def close_app(self):
        # pop up window that asks if you really want to exit the app ------------------------------------------------

        choice = QtWidgets.QMessageBox.question(self, "Quitting %s" % gui_name,
                                            "Do you really want to exit?",
                                                QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No)
        if choice == QtWidgets.QMessageBox.Yes:
            sys.exit()  # tells the app to quit
        else:
            pass

    def raiseError(self, error_val):
        '''raises an error window given certain errors from an emitted signal'''

        if 'ManyFet' in error_val:
            self.choice = QtWidgets.QMessageBox.question(self, "No Chosen Directory:",
                                                     "You have chosen more than four features,\n"
                                                     "clustering will take a long time.\n"
                                                     "Do you realy want to continue?",
                                                 QtWidgets.QMessageBox.Yes, QtWidgets.QMessageBox.No)

        elif 'NoDir' in error_val:
            self.choice = QtWidgets.QMessageBox.question(self, "No Chosen Directory:",
                                                   "You have not chosen a directory,\n"
                                                   "please choose one to continue!",
                                                     QtWidgets.QMessageBox.Ok)

        elif 'NoSet' in error_val:
            self.choice = QtWidgets.QMessageBox.question(self, "No .Set Files!",
                                                     "You have chosen a directory that has no .Set files!\n"
                                                     "Please choose a different directory!",
                                                     QtWidgets.QMessageBox.Ok)

        elif 'InvDirBatch':
            self.choice = QtWidgets.QMessageBox.question(self, "Invalid Directory!",
                                                     "In 'Batch Mode' you need to choose a directory\n"
                                                     "with subdirectories that contain all your Tint\n"
                                                     "files. Press Abort and choose new file, or if you\n"
                                                     "plan on adding folders to the chosen directory press\n"
                                                     "continue.",
                                                     QtWidgets.QMessageBox.Abort | QtWidgets.QMessageBox.Ok)
        elif 'InvDirNonBatch':
            self.choice = QtWidgets.QMessageBox.question(self, "Invalid Directory!",
                                                     "In 'Non-Batch Mode' you need to choose a directory\n"
                                                     "that contain all your Tint files.\n",
                                                     QtWidgets.QMessageBox.Ok)

    def AppendLog(self, message):
        '''A function that will append the Log field of the main window (mainly
        used as a slot for a custom pyqt signal)'''

        if '#' in message:
            message = message.split('#')
            color = message[-1].lower()
            message = message[0]
            message = '<span style="color:%s">%s</span>' % (color, message)

        self.Log.append(message)

    def stopBatch(self):
        # self.run_btn.clicked.disconnect()
        self.run_btn.clicked.connect(lambda: self.run(self.current_directory_name))
        self.AnalyzeThread.terminate()
        # self.RepeatAddSessionsThread.quit()
        self.run_btn.setText('Run')
        self.run_btn.setToolTip(
            'Click to perform batch analysis!')  # defining the tool tip for the start button

    def moveQueue(self, direction):
        """This method is not threaded"""
        # get all the queue items

        while self.adding_session:
            if self.reordering_queue:
                self.reordering_queue = False
            time.sleep(0.1)

        time.sleep(0.1)
        self.reordering_queue = True

        item_count = self.directory_queue.topLevelItemCount()
        queue_items = {}
        for item_index in range(item_count):
            queue_items[item_index] = self.directory_queue.topLevelItem(item_index)

        # get selected options and their locations
        selected_items = self.directory_queue.selectedItems()
        selected_items_copy = []
        [selected_items_copy.append(item.clone()) for item in selected_items]

        add_to_new_queue = list(queue_items.values())

        # add_to_new_queue = self.directory_queue.items
        # for i in range(len(selected_items)):
        #     selected_items[i] = selected_items[i].clone()

        if not selected_items:
            # skips when there are no items selected
            return

        new_queue_order = {}

        # find if consecutive indices from 0 on are selected as these won't move any further up

        indices = find_keys(queue_items, selected_items)
        # non_selected_indices = sorted([index for index in range(item_count) if index not in indices])
        consecutive_indices = find_consec(indices)
        # this will spit a list of lists, these nested lists will have consecutive indices within them
        # i.e. if indices 0, 1 and 3 were chosen it would have [[0, 1], [3]]

        if 'up' in direction:
            # first add the selected items to their new spots
            for consecutive in consecutive_indices:
                if 0 in consecutive:
                    # these items can't move up any further
                    for index in consecutive:
                        new_item = queue_items[index].clone()
                        # new_item.setSelected(True)
                        new_queue_order[index] = new_item

                else:
                    for index in consecutive:
                        # move these up the list (decrease in index value since 0 is the top of the list)
                        new_item = queue_items[index].clone()
                        # new_item.setSelected(True)
                        new_queue_order[index-1] = new_item

            for key, val in new_queue_order.items():
                for index, item in enumerate(add_to_new_queue):
                    if val.data(0, 0) == item.data(0, 0):
                        add_to_new_queue.remove(item)  # remove item from the list
                        break

            _ = list(new_queue_order.keys())  # a list of already moved items

            # place the unplaced items that aren't moving
            for static_index, static_value in queue_items.items():
                # print(static_value.data(0,0))
                # place the unplaced items
                if static_index in _:
                    continue

                for queue_item in new_queue_order.values():
                    not_in_reordered = True
                    if static_value.data(0, 0) == queue_item.data(0, 0):
                        # don't re-add the one that is going to be moved
                        not_in_reordered = False
                        break

                if not_in_reordered:
                    # item = queue_items[non_selected_indices.pop()]
                    for value in add_to_new_queue:
                        if static_value.data(0, 0) == value.data(0, 0):
                            add_to_new_queue.remove(value)  # remove item from the list
                            break

                    new_queue_order[static_index] = static_value.clone()

        elif 'down' in direction:
            # first add the selected items to their new spots
            for consecutive in consecutive_indices:
                if (item_count-1) in consecutive:
                    # these items can't move down any further
                    for index in consecutive:
                        new_item = queue_items[index].clone()
                        # new_item.setSelected(True)
                        new_queue_order[index] = new_item
                else:
                    for index in consecutive:
                        # move these down the list (increase in index value since 0 is the top of the list)
                        new_item = queue_items[index].clone()
                        # new_item.setSelected(True)
                        new_queue_order[index + 1] = new_item

            for key, val in new_queue_order.items():
                for index, item in enumerate(add_to_new_queue):
                    if val.data(0, 0) == item.data(0, 0):
                        add_to_new_queue.remove(item)
                        break

            _ = list(new_queue_order.keys())  # a list of already moved items

            # place the unplaced items that aren't moving
            for static_index, static_value in queue_items.items():
                if static_index in _:
                    continue

                for queue_item in new_queue_order.values():
                    not_in_reordered = True
                    if static_value.data(0, 0) == queue_item.data(0, 0):
                        # don't re-add the one that is going to be moved
                        not_in_reordered = False
                        break

                if not_in_reordered:
                    # item = queue_items[non_selected_indices.pop()]
                    for value in add_to_new_queue:
                        if static_value.data(0, 0) == value.data(0, 0):
                            add_to_new_queue.remove(value)  # remove item from the list
                            break

                    new_queue_order[static_index] = static_value.clone()

        # add the remaining items

        indices_needed = [index for index in range(item_count) if index not in list(new_queue_order.keys())]
        for index, displaced_item in enumerate(add_to_new_queue):
            new_queue_order[indices_needed[index]] = displaced_item.clone()

        self.analyzed_sessions = []
        self.directory_queue.clear()  # clears the list

        for key, value in sorted(new_queue_order.items()):
            # for item in selected_items:
            #     if item.data(0, 0) == value.data(0, 0):
            #         value.setSelected(True)

            self.directory_queue.addTopLevelItem(value)

        # reselect the items
        iterator = QtWidgets.QTreeWidgetItemIterator(self.directory_queue)
        while iterator.value():
            for selected_item in selected_items_copy:
                item = iterator.value()
                if item.data(0, 0) == selected_item.data(0, 0):
                    item.setSelected(True)
                    break
            iterator += 1
        # for index in range(item_count):
        #   self.directory_queue.takeTopLevelItem(0)
        self.reordering_queue = False

    def takeTopLevel(self, item_count):
        item_count = int(item_count)
        self.directory_queue.takeTopLevelItem(item_count)
        self.top_level_taken = True

    def setChild(self, child_count):
        self.child_session = self.directory_item.child(int(child_count))
        self.child_set = True

    def takeChild(self, child_count):
        self.child_session = self.directory_item.takeChild(int(child_count))
        self.child_taken = True
        # return child_session

    def takeChildData(self, child_count):
        self.child_session = self.directory_item.takeChild(int(child_count)).data(0, 0)
        self.child_data_taken = True

    def removeChild(self, QTreeWidgetItem):
        root = self.directory_queue.invisibleRootItem()
        (QTreeWidgetItem.parent() or root).removeChild(QTreeWidgetItem)
        self.child_removed = True

    def changed_directory(self):
        self.current_directory_name = self.current_directory.text()

        # Find the sessions, and populate the conversion queue
        self.analyzed_sessions = []
        self.directory_queue.clear()
        self.restart_add_sessions_thread()

    def changed_whiten(self):
        self.analyzed_sessions = []
        self.directory_queue.clear()
        self.restart_add_sessions_thread()

    def restart_add_sessions_thread(self):

        self.reset_add_thread = True

        if not hasattr(self, 'repeat_thread_active'):
            return

        # while self.repeat_thread_active:
        #     time.sleep(0.1)

        if hasattr(self, 'RepeatAddSessionsThread'):
            self.RepeatAddSessionsThread.terminate()

        # self.reset_add_thread = False
        # self.RepeatAddSessionsThread = QtCore.QThread()
        self.RepeatAddSessionsThread.setTerminationEnabled(True)
        self.RepeatAddSessionsThread.start()

        self.RepeatAddSessionsWorker = Worker(RepeatAddSessions, self)
        self.RepeatAddSessionsWorker.moveToThread(self.RepeatAddSessionsThread)
        self.RepeatAddSessionsWorker.start.emit("start")


def find_keys(my_dictionary, value):
    """finds a key for a given value of a dictionary"""
    key = []
    if not isinstance(value, list):
        value = [value]
    [key.append(list(my_dictionary.keys())[list(my_dictionary.values()).index(val)]) for val in value]
    return key


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


@QtCore.pyqtSlot()
def raise_window(new_window, old_window):
    """ raise the current window"""
    if 'Choose' in str(new_window):
        new_window.raise_()
        new_window.setWindowFlags(QtCore.Qt.WindowStaysOnTopHint)
        new_window.show()
        time.sleep(0.1)

    elif "Choose" in str(old_window):
        time.sleep(0.1)
        old_window.hide()
        return
    else:
        new_window.raise_()
        new_window.show()
        time.sleep(0.1)
        old_window.hide()


@QtCore.pyqtSlot()
def cancel_window(new_window, old_window):
    """ raise the current window"""
    new_window.raise_()
    new_window.show()
    time.sleep(0.1)
    old_window.hide()


def new_directory(self, main):
    current_directory_name = str(QtWidgets.QFileDialog.getExistingDirectory(self, "Select Directory"))
    self.current_directory_name = current_directory_name
    self.current_directory_e.setText(current_directory_name)


class Worker(QtCore.QObject):
    # def __init__(self, main_window, thread):
    def __init__(self, function, *args, **kwargs):
        super(Worker, self).__init__()
        self.function = function
        self.args = args
        self.kwargs = kwargs
        self.start.connect(self.run)

    start = QtCore.pyqtSignal(str)

    @QtCore.pyqtSlot()
    def run(self):
        self.function(*self.args, **self.kwargs)


class Communicate(QtCore.QObject):
    '''A custom pyqtsignal so that errors and popups can be called from the threads
    to the main window'''
    myGUI_signal_str = QtCore.pyqtSignal(str)
    myGUI_signal_QTreeWidgetItem = QtCore.pyqtSignal(QtWidgets.QTreeWidgetItem)


def nonbatch(self, state):
    self.analyzed_sessions = []
    self.directory_queue.clear()
    self.restart_add_sessions_thread()

    with open(self.settings_fname, 'r+') as filename:
        settings = json.load(filename)
        if state:
            settings['nonbatch'] = 1
            self.nonbatch = 1
        else:
            settings['nonbatch'] = 0
            self.nonbatch = 0
    with open(self.settings_fname, 'w') as filename:
        json.dump(settings, filename)


def run():
    app = QtWidgets.QApplication(sys.argv)

    main_w = Window()  # calling the main window
    choose_dir_w = Choose_Dir()  # calling the Choose Directory Window

    # synchs the current directory on the main window
    choose_dir_w.current_directory_name = main_w.current_directory_name

    main_w.raise_()  # making the main window on top

    main_w.nonbatch_check.stateChanged.connect(lambda: nonbatch(main_w, main_w.nonbatch_check.isChecked()))
    # brings the directory window to the foreground
    main_w.choose_directory.clicked.connect(lambda: raise_window(choose_dir_w,main_w))
    # main_w.choose_directory.clicked.connect(lambda: raise_window(choose_dir_w))

    # brings the main window to the foreground
    choose_dir_w.backbtn.clicked.connect(lambda: raise_window(main_w, choose_dir_w))
    choose_dir_w.applybtn.clicked.connect(lambda: choose_dir_w.apply_dir(main_w))
    # choose_dir_w.backbtn.clicked.connect(lambda: raise_window(main_w))  # brings the main window to the foreground

    # prompts the user to choose a directory
    choose_dir_w.dirbtn.clicked.connect(lambda: new_directory(choose_dir_w, main_w))
    # choose_dir_w.dirbtn.clicked.connect(lambda: new_directory(choose_dir_w))  # prompts the user to choose a directory

    sys.exit(app.exec_())  # prevents the window from immediately exiting out


if __name__ == "__main__":
    run()  # the command that calls run()
