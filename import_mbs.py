#!/usr/bin/python3
# -*- coding: utf-8 -*-

"""
2019-02-04
Paper: property variability in sea ice

Import data from the mass balance of the SIZONet project

"""

import configparser
import os
import pickle

import pandas as pd

from mbs import mbs

DEBUG = 1

if os.uname()[1] == 'adak':
    config = '/home/megavolts/git/SIZONet/BRW.conf'
else:
    print('No directory defined for this machine')

# -------------------------------------------------------------------------------------------------------------------- #
# LOAD CONFIG
# -------------------------------------------------------------------------------------------------------------------- #
config_file = configparser.ConfigParser()
config_file.read(config)

# -------------------------------------------------------------------------------------------------------------------- #
# IMPORTATION
# -------------------------------------------------------------------------------------------------------------------- #
mbs_subdir = os.path.join(config_file['SIZONet']['dir'], config_file['mbs']['subdir'])

# generate mbs files list
mbs.list_folder(mbs_subdir)

mbs_data = pd.DataFrame()
# read mbs:
for mbs_path in mbs.list_folder(mbs_subdir):
    print('Import data from %s' % mbs_path)
    data = mbs.read(mbs_path)
    mbs_data = pd.concat([mbs_data, data], join='outer', sort=False)

# -------------------------------------------------------------------------------------------------------------------- #
# EXPORTATION
# -------------------------------------------------------------------------------------------------------------------- #
mbs_pkl = os.path.join(mbs_subdir, config_file['mbs']['pkl'])
with open(mbs_pkl, 'wb') as f:
    pickle.dump(mbs_data, f)


# fu_path = os.path.join(config_file['SIZONet']['dir'], config_file['mbs']['subdir'], config_file['mbs']['freezup_obs'])
# freezup_data = mbs.load_freezup(fu_path)
