import os


def find_sub(string, sub):
    '''finds all instances of a substring within a string and outputs a list of indices'''
    result = []
    k = 0
    while k < len(string):
        k = string.find(sub, k)
        if k == -1:
            return result
        else:
            result.append(k)
            k += 1  # change to k += len(sub) to not search overlapping results
    return result


def find_bin_basenames(directory):
    file_list = os.listdir(directory)

    tint_basenames = [os.path.splitext(file)[0] for file in file_list if '.bin' in file]

    return tint_basenames


def find_converted_bin_basenames(directory):
    file_list = os.listdir(directory)

    mda_basenames = [os.path.splitext(file)[0] for file in file_list if '_filt.mda' in file]
    mda_basenames = [file[:find_sub(file, '_')[-1]] for file in mda_basenames]

    tint_basenames = []

    for file in mda_basenames:
        basename = file[:find_sub(file, '_')[-1]]
        if basename not in tint_basenames:
            tint_basenames.append(basename)

    return tint_basenames