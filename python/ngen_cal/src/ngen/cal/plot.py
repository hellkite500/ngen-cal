from __future__ import annotations

import geopandas as gpd
import pandas as pd
import json
import matplotlib.pyplot as plt
from typing import TYPE_CHECKING

from hypy.hydrolocation import NWISLocation # type: ignore
from hypy.nexus import Nexus # type: ignore

from .calibration_cathment import CalibrationCatchment

if TYPE_CHECKING:
    from pathlib import Path

def plot_objective(objective_log_file: Path):
    """
        Plot the objective funtion
    """

    data = pd.read_csv(objective_log_file, names=['iteration', 'objective'], index_col=0)
    plt.figure()
    data.plot()

def plot_stuff(workdir, catchment_data, nexus_data, cross_walk, config_file):

    catchments = []
    #Read the catchment hydrofabric data
    catchment_hydro_fabric = gpd.read_file(catchment_data)
    catchment_hydro_fabric.set_index('ID', inplace=True)
    nexus_hydro_fabric = gpd.read_file(nexus_data)
    nexus_hydro_fabric.set_index('ID', inplace=True)

    x_walk = pd.read_json(cross_walk, dtype=str)

    #Read the calibration specific info
    with open(config_file) as fp:
        data = json.load(fp)
    try:
        start_t = data['time']['start_time']
        end_t = data['time']['end_time']
    except KeyError as e:
        raise(RuntimeError(f"Invalid time configuration: {e.args[0]} key missing from {config_file}"))

    #Setup each calibration catchment
    for id, catchment in data['catchments'].items():
        if 'calibration' in catchment.keys():
            try:
                fabric = catchment_hydro_fabric.loc[id]
            except KeyError:
                #TODO log WARNING:
                continue
            try:
                nwis = x_walk[id]['site_no']
            except KeyError:
                raise(RuntimeError(f"Cannot establish mapping of catchment {id} to nwis location in cross walk"))
            try:
                nexus_data = nexus_hydro_fabric.loc[fabric['toID']]
            except KeyError:
                raise(RuntimeError(f"No suitable nexus found for catchment {id}"))

            #establish the hydro location for the observation nexus associated with this catchment
            location = NWISLocation(nwis, nexus_data.name, nexus_data.geometry)
            nexus = Nexus(nexus_data.name, location, id)
            catchments.append(CalibrationCatchment(workdir, id, nexus, start_t, end_t, catchment))

    for catchment in catchments:
        c_id = catchment.id
        n_id = catchment.outflow.id
        ax = catchment_hydro_fabric.plot()
        nexus_hydro_fabric.plot(ax=ax, color='r')

        ax2 = catchment.observed.plot(label='observed')
        catchment.output.plot(ax=ax2, label='simulated')

def plot_obs(id, catchment_data, nexus_data, cross_walk):
    #Read the catchment hydrofabric data
    catchment_hydro_fabric = gpd.read_file(catchment_data)
    catchment_hydro_fabric.set_index('ID', inplace=True)
    nexus_hydro_fabric = gpd.read_file(nexus_data)
    nexus_hydro_fabric.set_index('ID', inplace=True)
    x_walk = pd.read_json(cross_walk, dtype=str)
    try:
        fabric = catchment_hydro_fabric.loc[id]
    except KeyError:
        raise(RuntimeError(f"No data for id {id}"))
    try:
        nwis = x_walk[id]['site_no']
    except KeyError:
        raise(RuntimeError(f"Cannot establish mapping of catchment {id} to nwis location in cross walk"))
    try:
        nexus_data = nexus_hydro_fabric.loc[fabric['toID']]
    except KeyError:
        raise(RuntimeError(f"No suitable nexus found for catchment {id}"))

    #establish the hydro location for the observation nexus associated with this catchment
    location = NWISLocation(nwis, nexus_data.name, nexus_data.geometry)
    nexus = Nexus(nexus_data.name, location, id)
    #use the nwis location to get observation data
    #TODO/FIXME make a more general hydrofabric object
    obs = nexus._hydro_location.get_data("2015-12-01 00:00:00", "2015-12-30 23:00:00")
    #make sure data is hourly
    obs = obs.set_index('value_date')['value'].resample('1H').nearest()
    obs = obs * 0.028316847 #convert to m^3/s
    obs.rename('obs_flow', inplace=True)
    plt.figure()
    obs.plot(title=f'Observation at USGS {nwis}')

def plot_output(output_file: Path):
    #output = pd.read_csv(output_file, usecols=["Time", "Flow"], parse_dates=['Time'], index_col='Time')
    #output.rename(columns={'Flow':'sim_flow'}, inplace=True)
    output = pd.read_csv(output_file, parse_dates=['Time'], index_col='Time')
    original_output_vars = ['Rainfall', 'Direct Runoff', 'GIUH Runoff', 'Lateral Flow', 'Base Flow', 'Total Discharge']
    output[original_output_vars].plot(subplots=True)
    #original_output_vars.extend( [])
    # CHECK OUT GIUH ORDINATES/INPUT/USAGE
    plt.figure()
    output['Flow'].plot(title='simulated flow')

def plot_parameter_space(path: Path):
    params = pd.read_parquet(path)
    params.drop(columns=['min', 'max', 'sigma'], inplace=True)
    params.set_index('param', inplace=True)

    params.T.plot(subplots=True)
