tetrode_map = {'buzsaki32': {1: [5, 4, 6, 3],
                             2: [13, 12, 14, 11],
                             3: [7, 2, 8, 1],
                             4: [15, 10, 16, 9],
                             5: [21, 20, 22, 19],
                             6: [29, 28, 30, 27],
                             7: [23, 18, 24, 17],
                             8: [31, 26, 32, 25],
                             },

               'buzsaki16': {1: [5, 4, 6, 3],
                             2: [13, 12, 14, 11],
                             3: [7, 2, 8, 1],
                             4: [15, 10, 16, 9],
                             },

               'axona16_angled': {1: [1, 2, 3, 4],
                                  2: [5, 6, 7, 8],
                                  3: [9, 10, 11, 12],
                                  4: [13, 14, 15, 16]
                                  },

               'axona16_new': {1: [15, 13, 11, 9],
                               2: [16, 14, 12, 10],
                               3: [1, 3, 5, 7],
                               4: [2, 4, 6, 8]
                               },
               """
               'axona16_new': {1: [1, 2, 3, 4],
                               2: [5, 6, 7, 8],
                               3: [9, 10, 11, 12],
                               4: [13, 14, 15, 16]
                               },""" 

               'axona32_angled': {},
               }


def read_notes(notes, tetrode_map):
    probe = None
    experimenter = ''
    # reads through the notes to find useful information
    for note, note_val in notes.items():
        note_val = note_val.lower()
        if note_val != '':
            if note_val in list(tetrode_map.keys()):
                probe_list = list(tetrode_map.keys())
                probe = probe_list[probe_list.index(note_val)]
            elif 'probe:' in note_val:
                probe = note_val[note_val.find('probe:') + len('probe:'):].strip()
            else:
                experimenter = note_val

    if probe is None:
        # probe = 'axona16_angled'
        probe = 'axona16_new'

    return probe, experimenter