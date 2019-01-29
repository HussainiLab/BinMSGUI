from PyQt5 import QtWidgets, QtCore
from core.gui_utils import background, gui_name, center
import json
import os


class Choose_Dir(QtWidgets.QWidget):

    def __init__(self):
        super(Choose_Dir, self).__init__()
        background(self)
        # deskW, deskH = background.Background(self)
        width = self.deskW / 5
        height = self.deskH / 5
        self.setGeometry(0, 0, width, height)

        with open(self.directory_settings, 'r+') as filename:
            directory_data = json.load(filename)
            current_directory_name = directory_data['directory']
            if not os.path.exists(current_directory_name):
                current_directory_name = 'No Directory Currently Chosen!'

        self.setWindowTitle("%s - Choose Directory" % gui_name)

        # ---------------- defining instructions -----------------
        instr = QtWidgets.QLabel("For Batch Processing: choose the directory that contains subdirectories where these\n"
                             "subdirectories contain all the session files (.set, .pos, .eeg, .N, etc.). The GUI\n"
                             "will iterate through each sub-directory and each session within those sub-directories.\n\n"
                             "For Non-Batch: choose the directory that directly contains the contain all the session\n"
                             "files (.set, .pos, .eeg, .N, etc.) and the GUI will iterate through each session.\n")

        # ----------------- buttons ----------------------------
        self.dirbtn = QtWidgets.QPushButton('Choose Directory', self)
        self.dirbtn.setToolTip('Click to choose a directory!')
        # dirbtn.clicked.connect(self.new_dir)

        cur_dir_t = QtWidgets.QLabel('Current Directory:')  # the label saying Current Directory
        self.current_directory_e = QtWidgets.QLineEdit()  # the label that states the current directory
        self.current_directory_e.setText(current_directory_name)
        self.current_directory_e.setAlignment(QtCore.Qt.AlignHCenter)
        self.current_directory_name = current_directory_name

        self.backbtn = QtWidgets.QPushButton('Back', self)
        self.applybtn = QtWidgets.QPushButton('Apply', self)

        # ---------------- save checkbox -----------------------
        self.save_cb = QtWidgets.QCheckBox('Leave Checked To Save Directory', self)
        self.save_cb.toggle()
        self.save_cb.stateChanged.connect(self.save_dir)

        # ----------------- setting layout -----------------------

        layout_dir = QtWidgets.QVBoxLayout()

        layout_h1 = QtWidgets.QHBoxLayout()
        layout_h1.addWidget(cur_dir_t)
        layout_h1.addWidget(self.current_directory_e)

        layout_h2 = QtWidgets.QHBoxLayout()
        layout_h2.addWidget(self.save_cb)

        btn_layout = QtWidgets.QHBoxLayout()
        btn_order = [self.dirbtn, self.applybtn, self.backbtn]

        # btn_layout.addStretch(1)
        for butn in btn_order:
            btn_layout.addWidget(butn)
            # btn_layout.addStretch(1)

        layout_order = [instr, layout_h1, self.save_cb, btn_layout]

        for order in layout_order:
            if 'Layout' in order.__str__():
                layout_dir.addLayout(order)
            else:
                layout_dir.addWidget(order, 0, QtCore.Qt.AlignCenter)

        self.setLayout(layout_dir)

        center(self)
        # self.show()

    def save_dir(self, state):
        self.current_directory_name = str(self.current_directory_e.text())
        if state == QtCore.Qt.Checked:  # do this if the Check Box is checked
            # print('checked')
            with open(self.directory_settings, 'w') as filename:
                directory_data = {'directory': self.current_directory_name}
                json.dump(directory_data, filename)
        else:
            # print('unchecked')
            pass

    def apply_dir(self, main):
        self.current_directory_name = str(self.current_directory_e.text())
        self.save_cb.checkState()

        if self.save_cb.isChecked():  # do this if the Check Box is checked
            self.save_dir(self.save_cb.checkState())
        else:
            pass

        # main.directory_queue.clear()
        main.current_directory.setText(self.current_directory_name)
        # main.current_directory_name = self.current_directory_name

        self.backbtn.animateClick()