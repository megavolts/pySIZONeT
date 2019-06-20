#! /usr/bin/python3.5
# -*- coding: UTF-8 -*-

"""
Created on Fri Aug 29 08:47:19 2014
__author__ = "Marc Oggier"
__license__ = "GPL"
__version__ = "1.0.0"
__maintainer__ = "Marc Oggier"
__contact__ = "Marc Oggier"
__email__ = "marc.oggier@gi.alaska.edu"
__status__ = "development"
__date__ = "2019/02/22"
"""
import logging
import os

import numpy as np
import pandas as pd

import seaice


# ----------------------------------------------------------------------------------------------------------------------#

# create list or source
def list_folder(dirpath, fileext='.csv', level=0):
    """
    list all files with specific extension in a directory

    :param dirpath: str; directory to scan for ice core
    :param fileext: str, default .xlsx; file extension for ice core data
    :param level: numeric, default 0; level of recursitivy in directory search
    :return ic_list: list
        list of ice core path
    """
    _ics = []

    logger = logging.getLogger(__name__)

    def walklevel(some_dir, level=level):
        some_dir = some_dir.rstrip(os.path.sep)
        assert os.path.isdir(some_dir)
        num_sep = some_dir.count(os.path.sep)
        for root, dirs, files in os.walk(some_dir):
            yield root, dirs, files
            num_sep_this = root.count(os.path.sep)
            if num_sep + level <= num_sep_this:
                del dirs[:]

    for dirName, subdirList, fileList in walklevel(dirpath, level=level):
        _ics.extend([dirName + '/' + f for f in fileList if f.endswith(fileext)])

    ics_set = set(_ics)
    logger.info("Found %i ice mass balance datafile in %s" % (ics_set.__len__(), dirpath))

    return ics_set


def read(mbs_path):
    """
    Import mass balance data from SIZONet, downloaded from  https://arcticdata.io/catalog/view/doi:10.18739/A2D08X

    :param mbs_path: string
    :return mbs_data: pd.DataFrame()
    """
    logger = logging.getLogger(__name__)

    data = pd.read_csv(mbs_path)

    # distance are positive from ice surface to ice bottom
    d_th = 10  # distance in between thermistor



    # h_th_i : distance from ice/snow interface for thermistor i
    #          distance are measured positive from ice surface downwards
    year = int(mbs_path.split('/')[-1].split('_')[-1].split('.')[0])
    if year == 2007:
        h_th_0 = 5  # distance thermistor 0 from ice/snow interface
        n_th = 29  # number of thermistors
    elif 2008 <= year < 2010 or year == 2006:  # 2008, 2009
        h_th_0 = -40  # distance thermistor 0 from ice/snow interface, 40 cm above ice
        n_th = 29  # number of thermistors
        # if year == 2008:
        #     nan_value = [-97, 103]  # for underwater altimeters
        #     # snow depth error after day 157
        #     data[data.doy > 157, ['Hs (#0-Mast)', 'Hs (#1)', 'Hs (#2)']] = np.nan
    elif 2010 <= year < 2013:  # 2010, 2011, 2012
        data = data.iloc[1:].reset_index(drop=True)  # bad data on first entry row
        h_th_0 = -70  # distance thermistor 0 from ice/snow interface, 40 cm above ice
        n_th = 30  # number of thermistors
        if year == 2011:
            data = data.iloc[1:].reset_index(drop=True)  # remove secondary header
        if year == 2012:
            h_th_0 = -40
    if 2013 <= year:  # 2013, 2014, 2015, 2016
        h_th_0 = -70  # distance thermistor 0 from ice/snow interface, 70 cm above ice
        n_th = 30  # number of thermistors
        if year == 2013:
            data = data.iloc[1:].reset_index(drop=True)  # bad data on first entry row

    # invalid data
    nan_value = -9999
    data = data.apply(pd.to_numeric)
    data = data.replace(nan_value, np.nan)

    # parse column name
    col_dict = {}
    for col in data.columns:
        if col.startswith('T') and col.split('T')[-1].isdigit():
            col_dict[col] = h_th_0 + (int(col.split('T')[-1])-1)*d_th
        if col.startswith('Hs'):
            if 'Mast' in col:
                col_dict[col] = 'Hs'
            else:
                col_dict[col] = 'Hs_'+str(col.split('#')[-1][0])
        if 'UTC time' in col:
            col_dict[col] = 'Time (hhmm)'
    data = data.rename(columns = col_dict)
    del col_dict

    # parse datetime
    data['Year'] = data['Year'].astype(int)
    data['DOY'] = data['DOY'].astype(int)
    data['Time (hhmm)'] = data['Time (hhmm)'].astype(int)
    data['datetime'] = pd.to_datetime(data['Year'].astype(str) + '-' +
                                      data['DOY'].astype(str) + '-' +
                                      data['Time (hhmm)'].astype(str).str.zfill(4), format='%Y-%j-%H%M')
    data = data.reset_index(drop=True)

    col = [c for c in data.columns if isinstance(c, (int,float))]
    data[col] = data[col].apply(pd.to_numeric)
    return data


def generate_full_t_profile(mbs_data, day, location='BRW', hi=None, display_figure=False):
    """
    :param mbs_data: pd.DataFrame()
    :param day: pd.datetime()
    :param ice_thickness: float
    :return:
    """
    logger = logging.getLogger(__name__)

    if not isinstance(day, pd.datetime):
        try:
            day = pd.to_datetime(day)
        except ValueError:
            logger.error("wrong format for day, should be a pd.datetime")
            return seaice.Core(None, pd.NaT)

    # (1) Match day:
    day_data = mbs_data.loc[mbs_data.datetime.dt.date == day.date()]

    if day_data.empty:
        logger.info("No data for selected day %s" % day.isoformat())
        return seaice.Core(None, pd.NaT)
    else:
        depth = [c for c in day_data.columns if isinstance(c, (int, float))]

        if day.hour is not 0:
            # try hourly average
            t_mbs = day_data.loc[day_data.datetime.dt.hour == day.hour, depth].mean(skipna=True).dropna()
        else:
            # try 12-hourly average from 600 to 1800
            t_mbs = day_data.loc[(6 <= day_data.datetime.dt.hour) & (day_data.datetime.dt.hour <=18), depth].mean()

        if t_mbs.empty:
            # use daily mean:
            t_mbs = day_data[depth].mean().dropna()

        name = 'mbs-' + day.strftime('%Y%m%d')
        location = location

        if day_data['Hi'].notnull().any():
            h_mbs = day_data['Hi'].astype(float).mean()
            c = 'hi measured by mbs;'
        elif hi is not None:
            h_mbs = hi
            c = 'hi from user;'
        else:
            # TODO double linear regression for the flat part and the non flat part
            h_mbs = t_mbs.loc[(-1.8 < t_mbs.T)].sort_index().index[1] / 100
            c = 'hi computed from mbs;'
        snow_thickness = day_data['Hs'].astype(float).mean()

        ic = seaice.Core(name, day, location, lat=None, lon=None, ice_thickness=h_mbs,
                         snow_depth=snow_thickness, freeboard=np.nan)
        ic.add_comment(c)

        columns = ['temperature', 'y_mid', 'comment', 'variable', 'name', 'ice_core_length',
                   'sample_name']
        t_mbs = t_mbs.reset_index().rename(columns={'index': 'y_mid', 0: 'temperature'})
        t_mbs['y_mid'] = t_mbs['y_mid'] / 100
        t_mbs = t_mbs.sort_values(by='y_mid').reset_index(drop=True)

        t_mbs = t_mbs.dropna().reset_index(drop=True)

        t_mbs['name'] = name
        t_mbs['length'] = h_mbs
        t_mbs['ice thickness'] = h_mbs
        t_mbs['variable'] = 'temperature'

        ic.add_profile(t_mbs)

        if display_figure:
            import matplotlib.pyplot as plt
            fig, ax = plt.subplots(1, 1)
            ax.plot(t_mbs.temperature, t_mbs.y_mid)
            ax.plot(t_mbs.temperature, t_mbs.y_mid, 'x')
            ax.plot([t_mbs.temperature.min(), t_mbs.temperature.max()], [0, 0], 'b')
            ax.plot([t_mbs.temperature.min(), t_mbs.temperature.max()], [h_mbs, h_mbs])
            ax.set_ylim([max(ax.get_ylim()), min(ax.get_ylim())])
            plt.show()
    return ic



def generate_t_profile(mbs_data, day, location='BRW', hi=None):
    """
    :param mbs_data: pd.DataFrame()
    :param day: pd.datetime()
    :param ice_thickness: float
    :return:
    """
    logger = logging.getLogger(__name__)

    if not isinstance(day, pd.datetime):
        try:
            day = pd.to_datetime(day)
        except ValueError:
            logger.error("wrong format for day, should be a pd.datetime")
            return seaice.Core(None, pd.NaT)

    # (1) Match day:
    day_data = mbs_data.loc[mbs_data.datetime.dt.date == day.date()]

    if day_data.empty:
        logger.info("No data for selected day %s" % day.isoformat())
        return seaice.Core(None, pd.NaT)
    else:
        depth = [c for c in day_data.columns if isinstance(c, (int, float))]

        if day.hour is not 0:
            # try hourly average
            t_mbs = day_data.loc[day_data.datetime.dt.hour == day.hour, depth].mean(skipna=True).dropna()
        else:
            # try 12-hourly average from 600 to 1800
            t_mbs = day_data.loc[(6 <= day_data.datetime.dt.hour) & (day_data.datetime.dt.hour <=18), depth].mean()

        if t_mbs.empty:
            # use daily mean:
            t_mbs = day_data[depth].mean().dropna()

        name = 'mbs-' + day.strftime('%Y%m%d')
        location = location

        if day_data['Hi'].notnull().any():
            h_mbs = day_data['Hi'].astype(float).mean()
            c = 'hi measured by mbs;'
        elif hi is not None:
            h_mbs = hi
            c = 'hi from user;'
        else:
            # TODO double linear regression for the flat part and the non flat part
            h_mbs = t_mbs.loc[(-1.8 < t_mbs.T)].sort_index().index[1] / 100
            c = 'hi computed from mbs;'
        snow_thickness = day_data['Hs'].astype(float).mean()

        ic = seaice.Core(name, day, location, lat=None, lon=None, ice_thickness=h_mbs,
                         snow_depth=snow_thickness, freeboard=np.nan)
        ic.add_comment(c)

        columns = ['temperature', 'y_mid', 'comment', 'variable', 'name', 'ice_core_length',
                   'sample_name']
        t_mbs = t_mbs.reset_index().rename(columns={'index': 'y_mid', 0: 'temperature'})
        t_mbs['y_mid'] = t_mbs['y_mid'] / 100
        t_mbs = t_mbs.sort_values(by='y_mid').reset_index(drop=True)


        # todo: interpolate ice surface and ice bottom location
        # upper bound is 0, or t_air closer to the ice surface
        try:
            u_index = np.where(t_mbs.y_mid < 0)[-1][-1]
        except IndexError:
            u_index = t_mbs.index.min()
        # lower bound is h_mbs, or t_water closer to the ice bottom
        l_index = np.where(h_mbs < t_mbs.y_mid)[-1][0]
        t_mbs = t_mbs.iloc[range(u_index, l_index+1)].dropna().reset_index(drop=True)

        # set the lower most y_mid to the ice thickness value, and the temperature to sea water
        t_mbs.loc[t_mbs.y_mid == t_mbs.y_mid.max(), 'y_mid'] = h_mbs

        t_mbs['name'] = name
        t_mbs['length'] = h_mbs
        t_mbs['ice thickness'] = h_mbs
        t_mbs['variable'] = 'temperature'

        ic.add_profile(t_mbs)
    return ic

#
# def daily_max(mbs_data, year, ii_col):
#     day_start = mbs_data.loc[mbs_data.datetime.dt.year == year].datetime.dt.date.min()
#     day_end = mbs_data.loc[mbs_data.datetime.dt.year == year].datetime.dt.date.max()
#     ii_day = day_start
#     ii_col = 6
#     hi_day = []
#     while ii_day <= day_end:
#         day_index = toolbox.index_from_day(mbs_data[year], ii_day)
#         try:
#             hi_mean = np.nanmean(mbs_data[year][day_index, ii_col - 1])
#         except IndexError:
#             hi_mean = np.nan
#         else:
#             hi_day.append(hi_mean)
#         ii_day += datetime.timedelta(1)
#     hi_max = np.nanmax(hi_day)
#     np.where(np.array(hi_day) == hi_max)
#     hi_max_index = np.where(np.array(hi_day) == hi_max)[0]
#     hi_max_index
#     if len(np.atleast_1d(hi_max_index)) > 1:
#         hi_max_index = hi_max_index[-1]
#     hi_max_day = day_start + datetime.timedelta(np.float(hi_max_index))
#     return hi_max_day, hi_max

def load_freezup(path):
    """
    :param path:
    :return:
    """
    freezup_data = pd.read_csv(path, skiprows=7, sep='\t').replace('-', np.nan).set_index('year', drop=True)

    freezup_data['all'] = freezup_data['he']
    freezup_data.loc[freezup_data['he'].isnull(), 'all'] = freezup_data.loc[freezup_data['he'].isnull(), 'jl']
    return freezup_data


def freezup_date_of_year(freezup_data, year=None, source='all'):
    '''
    :param freezup_dates_data:
    :param year:
        if year is none, look for freezup year for the entire array
    :param source:
    :return:
    '''
    # if year is none, return freezup year for every year
    if year is None:
        year = freezup_data.index
    elif not isinstance(year, list):
        year = [year]

    # select source
    if source not in freezup_data.columns:
        logging.warning('source not defined')
        return 0

    freezup_dates = {}
    for ii_year in year:
        ii_year = int(ii_year)

        doy = freezup_data.loc[freezup_data.index == ii_year, source].unique()[0]

        freezup_dates[ii_year] = pd.to_datetime(str(ii_year-1) + str(doy), format="%Y%j")
    return freezup_dates
