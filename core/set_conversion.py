import numpy as np
import shutil
import os
import datetime


def convert_setfile(set_filename, output_set_filename, self=None):

    # make a copy of the set_filename with a new set_filename

    if os.path.exists(output_set_filename):
        msg = '[%s %s]: The following set file has already been created: %s, skipping creation!#Red' % \
              (str(datetime.datetime.now().date()),
               str(datetime.datetime.now().time())[:8], output_set_filename)

        if self:
            self.LogAppend.myGUI_signal_str.emit(msg)
        else:
            print(msg)
        return

    shutil.copy(set_filename, output_set_filename)

    with open(output_set_filename, 'r+') as f:

        header = ''
        footer = ''

        header_values = True

        for line in f:

            if header_values:
                if 'duration' in line:
                    line = line.strip()
                    duration = int(np.ceil(float(line.split(' ')[-1])))
                    header += 'duration %d\n' % duration
                    continue
                header += line

            else:
                footer += line

    with open(output_set_filename, 'w') as f:

        f.writelines([header, footer])
