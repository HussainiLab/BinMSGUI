# ----- sorting parameters # -------------
whiten = 'true'  # do you want to whiten the data?
# whiten = 'false'

detect_interval = 20  # roughly the number of samples to check for a spike
# the algorithm will take the detect_interval value and bin the data in bin sizes of that many
# samples. Then it will find the peak (or trough, or both) of each bin and evaluate that event
# if it exceeds the threshold value.

# recommend only doing positive peaks so we don't get any weird issues with a cell that is
# aligned with the peak, and seemingly the same cell aligned with the trough (in this case
# both peak and trough would have to exceed the threshold).

# detect_sign = 0  # positive or negative peaks
detect_sign = 1  # only positive peaks
# detect_sign = -1  # only negative peaks

# threshold values, I changed it into a whitened and non whitened threshold
# this is because if you whiten the data you normalize it by the variance, thus
# a threshold of 3 is essentially saying 3 standard deviations. However if you do not whiten
# the data is not normalized and thus, you would be using a bit value, maybe should take whatever
# value is in the threshold from the set file.

if whiten == 'true':
    detect_threshold = 4  # units: ~sd's
    # ---------------
    automate_threshold = False  # Don't Change this

else:
    # this mean's the data was not whitened

    detect_threshold = 1000  # units: bits

    # if you want to find the threshold from the .set file and use that
    # set automate_threshold to True, otherwise False. This threshold would override any
    # value set above. I'd recommend setting this to true as this is variable from .set file
    # to .set file it seems.
    automate_threshold = True
    # automate_threshold = False

pre_spike = 15
post_spike = 35

# bandpass filtering parameters, don't really know this
freq_min = 300  # this doesn't really matter because data is already filtered so it won't do the filtering
freq_max = 7000  # this doesn't really matter because data is already filtered so it won't do the filtering

# artifact masking parameters
# here we bin the data into masked_chunk_size bins, and it will take the sqrt of the sum of
# the squares (RSS) for each bin. It will then find the SD for all the bins, and if the bin is
# above mask_threshold SD's from the average bin RSS, it will consider it as high amplitude noise
# and remove this chunk (and neighboring chunks).

# mask = True
mask = False
mask_threshold = 6  # units: SD's
masked_chunk_size = None  # if none it will default to Fs/10
mask_num_write_chunks = 100  #

# feature parameters
num_features = 10
max_num_clips_for_pca = 3000

# random parameters, probably don't need to change

clip_size = 50  # this needs to be left at 50 for Tint, Tint only likes 50 samples
notch_filter = False  # the data is already notch filtered likely
self = None  # don't worry about this, this is for objective oriented programming (my GUIs)
