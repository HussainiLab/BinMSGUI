import numpy as np
import struct, os
import core.intan_rhd_functions as f_intan


def readMDA(filename):
    with open(filename, 'rb') as f:

        code = struct.unpack('<l', f.read(4))[0]

        if code > 0:
            num_dims = code
            code = -1
        else:
            f.read(4)
            num_dims = struct.unpack('<l', f.read(4))[0]

        S = np.zeros((1, num_dims))

        for j in np.arange(num_dims):
            S[0, j] = struct.unpack('<l', f.read(4))[0]

        N = int(np.prod(S))  # number of spikes

        A = np.zeros((int(S[0, 0]), int(S[0, 1])))

        if code == -1:
            # complex float
            M = np.zeros((1, N * 2))
            # there are N*2 samples, and 4 bytes per float
            M[0, :] = np.asarray(struct.unpack('<%df' % (N * 2), f.read(N * 2 * 4)))
            A = (M[0, 0:N * 2:2] + 1j * M[0, 1:N * 2:2]).reshape(
                A.shape, order='F')

        elif code == -2:
            # uint8
            A[0, :] = np.asarray(struct.unpack('<%dB' % (N), f.read(N)))

        elif code == -3:
            # float, float32
            A = np.asarray(
                struct.unpack('<%df' % (N), f.read(N * 4))).reshape(
                A.shape, order='F')  # 4 bytes per float

        elif code == -4:
            # short, int16
            A = np.asarray(
                struct.unpack('<%dh' % (N), f.read(N * 2))).reshape(
                A.shape, order='F')  # 2 bytes per short

        elif code == -5:
            # int, int32
            A = np.asarray(
                struct.unpack('<%di' % (N), f.read(N * 4))).reshape(
                A.shape, order='F')  # 2 bytes per int

        elif code == -6:
            # uint16
            A = np.asarray(
                struct.unpack('<%dH' % (N), f.read(N * 2))).reshape(
                A.shape, order='F')  # 2 bytes per uint16

        elif code == -7:
            # double, float64
            # B = struct.unpack('<%dd' % (N), f.read(N*8))
            A = np.asarray(
                struct.unpack('<%dd' % (N), f.read(N * 8))).reshape(
                A.shape, order='F')  # 8 bytes per double

        elif code == -8:
            # uint32
            A = np.asarray(
                struct.unpack('<%dI' % (N), f.read(N * 4))).reshape(
                A.shape, order='F')  # 4 bytes per uint32

        else:
            print('Have not coded for this case yet!')

            return

    return A, code


def get_Fs(spike_filename):
    # find the basename that we name all of our files so we can find the associated intan directory
    basename = os.path.basename(spike_filename[:spike_filename.find('_firings')])

    rhd_filename = os.path.join(os.path.dirname(spike_filename), '%s.rhd' % basename)

    header = f_intan.read_header(rhd_filename)

    # the sampling frequency of the intan recording system
    Fs_intan = int(header['frequency_parameters']['amplifier_sample_rate'])

    return Fs_intan