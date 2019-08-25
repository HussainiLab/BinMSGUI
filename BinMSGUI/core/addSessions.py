import os
from PyQt5 import QtWidgets
import time
import threading
from core.intan_mountainsort import validate_session
from core.utils import find_bin_basenames

threadLock = threading.Lock()


def get_added(queue):
    added = []
    directories = []
    item_count = queue.topLevelItemCount()
    for item_index in range(item_count):
        parent_item = queue.topLevelItem(item_index)

        parent_directory = parent_item.data(0, 0)

        if parent_directory not in directories:
            directories.append(parent_directory)

        for child_i in range(parent_item.childCount()):
            added.append(os.path.join(parent_directory, parent_item.child(child_i).data(0, 0) + '.set'))

    return added, directories


def addSessions(self):
    """Adds any sessions that are not already on the list"""

    while self.reordering_queue or self.modifying_list:
        # pauses add Sessions when the individual is reordering
        time.sleep(0.1)

    directory_added = False

    current_directory = self.current_directory.text()

    if not self.nonbatch_check.isChecked():
        try:
            sub_directories = [d for d in os.listdir(current_directory)
                               if os.path.isdir(os.path.join(current_directory, d)) and
                               len([file for file in os.listdir(os.path.join(current_directory, d))
                                    if '.set' in file]) != 0 and
                               d not in ['Processed', 'Converted']]
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

    added, add_dirs = get_added(self.directory_queue)

    # check if directories still exist
    item_count = self.directory_queue.topLevelItemCount()
    for item_index in range(item_count):
        parent_item = self.directory_queue.topLevelItem(item_index)
        parent_directory = parent_item.data(0, 0)
        if not os.path.exists(os.path.join(current_directory, parent_directory)):
            # the path no longer exists
            root = self.directory_queue.invisibleRootItem()
            for child_index in range(root.childCount()):
                if root.child(child_index) == parent_item:
                    self.RemoveChildItem.myGUI_signal_QTreeWidgetItem.emit(parent_item)
        else:
            # the path exists
            added_directories.append(parent_directory)
            # check if the children exists
            for child_i in range(parent_item.childCount()):
                child_item = parent_item.child(child_i)
                if not os.path.exists(os.path.join(current_directory, parent_directory, child_item.data(0, 0) + '.set')):
                    # the path does not exist

                    # remove the child value
                    self.child_removed = False
                    self.RemoveChildItem.myGUI_signal_QTreeWidgetItem.emit(child_item)
                    while not self.child_removed:
                        time.sleep(0.1)

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
        except PermissionError:
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

                added, add_dirs = get_added(self.directory_queue)

                for value in added:
                    if value not in added_bin_files:
                        added_bin_files.append(value)

                for bin_file in bin_files:
                    if os.path.join(directory, bin_file) + '.set' in added_bin_files:
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
    """
    takes the session information and adds the session if valid
    """

    added_bin_directory = directory
    directory = os.path.join(current_directory, directory)

    tint_basename = os.path.basename(os.path.splitext(bin_file)[0])
    tint_fullpath = os.path.join(directory, tint_basename)
    output_basename = '%s_ms' % tint_fullpath
    session_valid = validate_session(directory, tint_basename, output_basename, self=self, verbose=False)

    if session_valid:

        # only adds the sessions that haven't been added already
        session_item = QtWidgets.QTreeWidgetItem()
        session_item.setText(0, tint_basename)

        added_bin_files.append(os.path.join(added_bin_directory, bin_file))

        directory_item.addChild(session_item)

        self.directory_queue.addTopLevelItem(directory_item)

    return added_bin_files


def RepeatAddSessions(self):
    """This will continuously look for files to add to the Queue"""

    self.repeat_thread_active = True

    while True:
        with threadLock:
            if self.reset_add_thread:
                self.repeat_thread_active = False
                self.reset_add_thread = False
                return

        if self.directory_changed:
            # then we have changed the directory name
            while (time.time() - self.change_directory_time) < 0.5:
                time.sleep(0.1)
            self.directory_queue.clear()
            self.directory_changed = False

        elif self.whiten_changed:
            # then we have changed the whitened option
            while (time.time() - self.change_whiten_time) < 0.5:
                time.sleep(0.1)
            self.directory_queue.clear()
            self.whiten_changed = False

        elif self.batch_changed:
            # then we have changed the batch
            while (time.time() - self.change_batch_time) < 0.5:
                time.sleep(0.1)
            self.directory_queue.clear()
            self.batch_changed = False

        try:
            with threadLock:
                self.adding_session = True
            addSessions(self)

            with threadLock:
                self.adding_session = False
                time.sleep(0.1)
        except FileNotFoundError:
            pass
        except RuntimeError:
            pass
