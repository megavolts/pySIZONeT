#!/usr/bin/python3
# -*- coding: utf-8 -*-

"""
2019-02-04

import_icecore.py provides function to import raw data from ice core

Paper: property variability in sea ice

Import ice core data from Barrow, collected from 1998 to 2018

HSVA.import provides function to import raw data and load process data
"""

import configparser
import os
import pickle
from pandas import DataFrame
import seaice

DEBUG = 1

if os.uname()[1] == 'adak':
    config_fp = '/home/megavolts/git/SIZONet/mbs/BRW.conf'
else:
    print('No directory defined for this machine')

import logging
logging.getLogger().setLevel(logging.INFO)

# -------------------------------------------------------------------------------------------------------------------- #
# LOAD CONFIG
# -------------------------------------------------------------------------------------------------------------------- #
config_file = configparser.ConfigParser()
config_file.read(config_fp)

# -------------------------------------------------------------------------------------------------------------------- #
# IMPORTATION
# -------------------------------------------------------------------------------------------------------------------- #
# Import pickled ice core data
core_subdir = os.path.join(config_file['SIZONet']['dir'], config_file['core']['subdir'])

# generate ice core list
ic_list = seaice.core.list_folder(core_subdir, level=1)

# import data from ice core list
ic_dict = seaice.core.import_ic_list(ic_list, verbose=True)

# create ice core stack
ic_df = seaice.core.corestack.stack_cores(ic_dict)

# -------------------------------------------------------------------------------------------------------------------- #
# EXPORTATION
# -------------------------------------------------------------------------------------------------------------------- #
core_pkl = os.path.join(core_subdir, config_file['core']['pkl'])
with open(core_pkl, 'wb') as f:
    pickle.dump(DataFrame(ic_df), f)
    print(core_pkl)
