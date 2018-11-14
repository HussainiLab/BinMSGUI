import os
import numpy as np
import json
import datetime


def write_cut(cut_filename, cut, basename=None):
    if basename is None:
        basename = os.path.basename(os.path.splitext(cut_filename)[0])

    unique_cells = np.unique(cut)

    if 0 not in unique_cells:
        # if it happens that there is no zero cell, add it anyways
        unique_cells = np.insert(unique_cells, 0, 0)  # object, index, value to insert

    n_clusters = len(np.unique(cut))
    n_spikes = len(cut)

    write_list = []  # the list of values to write

    tab = '    '  # the spaces didn't line up with my tab so I just created a string with enough spaces
    empty_space = '               '  # some of the empty spaces don't line up to x tabs

    # we add 1 to n_clusters because zero is the garbage cell that no one uses
    write_list.append('n_clusters: %d\n' % (n_clusters))
    write_list.append('n_channels: 4\n')
    write_list.append('n_params: 2\n')
    write_list.append('times_used_in_Vt:%s' % ((tab + '0') * 4 + '\n'))

    zero_string = (tab + '0') * 8 + '\n'

    for cell_i in np.arange(n_clusters):
        write_list.append(' cluster: %d center:%s' % (cell_i, zero_string))
        write_list.append('%smin:%s' % (empty_space, zero_string))
        write_list.append('%smax:%s' % (empty_space, zero_string))
    write_list.append('\nExact_cut_for: %s spikes: %d\n' % (basename, n_spikes))

    # now the cut file lists 25 values per row
    n_rows = int(np.floor(n_spikes / 25))  # number of full rows

    remaining = int(n_spikes - n_rows * 25)
    cut_string = ('%3u' * 25 + '\n') * n_rows + '%3u' * remaining

    write_list.append(cut_string % (tuple(cut)))

    with open(cut_filename, 'w') as f:
        f.writelines(write_list)


def is_json(file):
    if os.path.splitext(file)[-1] == '.json':
        return True
    return False


def get_metric_files(session_filename, metrics_string='_metrics'):
    directory = os.path.dirname(session_filename)

    basename = os.path.basename(os.path.splitext(session_filename)[0])

    file_list = os.listdir(directory)

    metric_list = [os.path.join(directory, file) for file in file_list
                   if metrics_string in file and is_json(file)]

    return metric_list


def get_mua_cells(metrics_filename):
    with open(metrics_filename, 'r') as f:
        data = json.load(f)
    data = data['clusters']
    mua_list = []
    for unit in data:
        label = unit['label']
        tag = unit['tags']

        if 'mua' in tag:
            mua_list.append(label)
    return mua_list


def get_tint_cut(cut, mua_cells):
    """This will make it so that the good cells are consecutive and in the beginning of the cut file, and the
    MUA (noise + cells that just didn't meet our criteria), will be in the back, separated by an emtpy cell.
    It will also sort the mua cells from most least to most spikes."""
    from operator import itemgetter

    mua_cells = np.asarray(mua_cells)

    cut_dict = {0: 0}  # cut_value, new_consecutive_cut_value

    # for the curated the cut values might not be consecutive numbers, lets turn these values
    # into consecutive numbers

    if 0 in cut:
        add_one = 0
    else:
        add_one = 1

    cells = np.setdiff1d(np.unique(cut), mua_cells)

    i = 0  # initialize i, if all the cells are mua, it will skip the next for loop and i will not be initialized
    for i, cut_value in enumerate(np.unique(cells)):
        if cut_value == 0:
            continue

        cut_dict[cut_value] = i + add_one  # +1 because we already have zero

    if len(mua_cells) != len(np.unique(cut)):
        i_offset = i + 1 + 1  # +1 for the gap as well as incrementing +1 from what we have already done above
    else:
        i_offset = i + 1  # +1 for the gap as well as incrementing +1 from what we have already done above

    count_dict = {}
    for cut_value in mua_cells:
        count_dict[cut_value] = sum(cut.flatten() == cut_value)

    for i, cut_value in enumerate(sorted(count_dict.items(), key=lambda x: x[1])):
        cut_value = cut_value[0]
        if cut_value == 0:
            continue

        cut_dict[cut_value] = i + i_offset + add_one  # +1 because we already have zero

    return itemgetter(*list(cut))(cut_dict), cut_dict


def create_cut(cut_filename, cell_numbers, tetrode, tint_basename, output_basename, self=None):

    metric_file = tint_basename + '_T%d_metrics.json' % tetrode

    if not os.path.exists(metric_file):
        msg = '[%s %s]: The following metrics filename does not exist: %s, skipping!' % (
            str(datetime.datetime.now().date()),
            str(datetime.datetime.now().time())[
            :8], metric_file)

        if self is None:
            print(msg)
        else:
            self.LogAppend.myGUI_signal_str.emit(msg)

        raise FileNotFoundError('Could not find the following filename: %s' % metric_file)

    mua_cells = get_mua_cells(metric_file)

    # re-ordering the cell number so in tint the mua cells are in the back
    # also re-ordered by number of spikes
    cut_cont, cut_dict = get_tint_cut(cell_numbers, mua_cells)

    write_cut(cut_filename, cut_cont, basename=output_basename)
