import os
from PyQt5 import QtWidgets
import time
from core.intan_mountainsort import validate_session
from core.utils import find_bin_basenames


def addSessions(self):
    """Adds any sessions that are not already on the list"""

    while self.reordering_queue:
        # pauses add Sessions when the individual is reordering
        time.sleep(0.1)

    current_directory = self.current_directory_name

    if self.nonbatch == 0:
        try:
            sub_directories = [d for d in os.listdir(current_directory)
                               if os.path.isdir(os.path.join(current_directory, d)) and d not in ['Processed',
                                                                                                  'Converted']]
        except PermissionError:
            return
        except OSError:
            return
    else:
        sub_directories = [os.path.basename(current_directory)]
        current_directory = os.path.dirname(current_directory)

    added_bin_files = []

    iterator = QtWidgets.QTreeWidgetItemIterator(self.directory_queue)
    # loops through all the already added sessions
    added_directories = []
    while iterator.value():
        directory_item = iterator.value()

        # check if the path still exists
        if not os.path.exists(os.path.join(current_directory, directory_item.data(0, 0))):
            # then remove from the list since it doesn't exist anymore
            root = self.directory_queue.invisibleRootItem()
            for child_index in range(root.childCount()):
                if root.child(child_index) == directory_item:
                    self.RemoveChildItem.myGUI_signal_QTreeWidgetItem.emit(directory_item)
        else:
            try:
                added_directories.append(directory_item.data(0, 0))
            except RuntimeError:
                # prevents issues where the object was deleted before it could be added
                return

        iterator += 1

    for directory in sub_directories:

        try:
            bin_files = find_bin_basenames(os.path.join(current_directory, directory))
        except FileNotFoundError:
            return

        if bin_files:
            if directory in added_directories:
                # add sessions that aren't already added
                # find the treewidget item
                iterator = QtWidgets.QTreeWidgetItemIterator(self.directory_queue)
                while iterator.value():
                    directory_item = iterator.value()
                    if directory_item.data(0, 0) == directory:
                        break
                    iterator += 1

                # find added rhd_files
                try:
                    iterator = QtWidgets.QTreeWidgetItemIterator(directory_item)
                except UnboundLocalError:
                    return
                except RuntimeError:
                    return

                while iterator.value():
                    session_item = iterator.value()
                    added_bin_files.append(session_item.data(0, 0))
                    iterator += 1

                for bin_file in bin_files:
                    if bin_file in added_bin_files:
                        continue

                    added_bin_files = addSession(self, bin_file, current_directory, directory, added_bin_files,
                                                 directory_item)

            else:
                # the directory has not been added yet
                directory_item = QtWidgets.QTreeWidgetItem()
                directory_item.setText(0, directory)

                for bin_file in bin_files:

                    if bin_file in added_bin_files:
                        continue

                    added_bin_files = addSession(self, bin_file, current_directory, directory, added_bin_files,
                                                 directory_item)


def addSession(self, bin_file, current_directory, directory, added_bin_files, directory_item):

    directory = os.path.join(current_directory, directory)

    tint_basename = os.path.basename(os.path.splitext(bin_file)[0])
    tint_fullpath = os.path.join(directory, tint_basename)
    output_basename = '%s_ms' % tint_fullpath
    session_valid = validate_session(directory, tint_basename, output_basename, self=self, verbose=False)
    if session_valid and tint_basename != self.current_session:

        # only adds the sessions that haven't been added already
        session_item = QtWidgets.QTreeWidgetItem()
        session_item.setText(0, tint_basename)

        added_bin_files.append(bin_file)

        directory_item.addChild(session_item)

        self.directory_queue.addTopLevelItem(directory_item)

    return added_bin_files


def RepeatAddSessions(self):
    """This will continuously look for files to add to the Queue"""

    self.repeat_thread_active = True

    try:
        self.adding_session = True
        addSessions(self)
        # time.sleep(0.1)
        self.adding_session = False
    except FileNotFoundError:
        pass
    except RuntimeError:
        pass

    while True:

        if self.reset_add_thread:
            self.repeat_thread_active = False
            self.reset_add_thread = False
            return

        try:
            self.adding_session = True
            # time.sleep(0.1)
            addSessions(self)
            self.adding_session = False
            # time.sleep(0.1)
        except FileNotFoundError:
            pass
        except RuntimeError:
            pass
