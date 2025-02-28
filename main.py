# Main Execution Script
# Author: Divya Ramachandran

from datetime import datetime, timedelta, timezone
import logging
from typing import List
from nost_tools import Simulator
from pydantic import TypeAdapter
import pandas as pd
from tatc.schemas import Satellite as TATC_Satellite
import geopandas as gpd

from sos_sim.entities import Satellite
from sos_sim.observers import ScenarioTimeIntervalCallback, PropertyChangeCallback
from sos_sim.schemas import Observation, Request
from tatc.analysis import collect_ground_track
from tatc.analysis import compute_ground_track
from tatc.schemas import PointedInstrument, WalkerConstellation, SunSynchronousOrbit
from tatc.analysis import collect_multi_observations
from tatc.utils import swath_width_to_field_of_regard, swath_width_to_field_of_view
from tatc.analysis import collect_multi_observations
from tatc.schemas import Satellite
from tatc.schemas import Point
from nost_sim_integrated_code.function import (
    read_master_file,
    compute_opportunity,
    update_requests,
    Snowglobe_constellation,
    compute_ground_track_and_format,
    filter_requests,
    write_back_to_appender,
)
from nost_sim_integrated_code.entity import Collect_Observations

# configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# configure scenario
start = datetime(2025, 1, 16, tzinfo=timezone.utc)  # nost simulation start
duration = timedelta(hours=1)  # nost simulation duration
time_step = timedelta(minutes=1)  # nost simulation time step
time_scale_factor = 60  # 5 seconds wallclock for 5 minutes scenario
view_time_step = timedelta(seconds=2)  # time step for ground track

simulator = Simulator()

# Initial Requests
master = read_master_file()
request_data = filter_requests(master)

request_points = request_data.apply(
    lambda r: Point(id=r["id"], latitude=r["latitude"], longitude=r["longitude"]),
    axis=1,
)

# Add Collect_Observations entity
entity = Collect_Observations(
    constellation=Snowglobe_constellation(start), requests=request_points
)

# add new requests
# entity.new_requests = [ Point(id=50, latitude=0, longitude=0) ]

simulator.add_entity(entity)

# OBSERVERS

# PROBLEM HERE, FUNCTION TAKES ARGUMENTS
# add an observer to save observations at a specified interval
simulator.add_observer(
    ScenarioTimeIntervalCallback(simulator, write_back_to_appender, time_step * 1440)
)

# PROBLEM HERE, FUNCTION TAKES ARGUMENTS, AND  HAD TO TRIGGER SERIES OF OTHER FUNCTIONS
entity.add_observer(
    PropertyChangeCallback(Satellite.PROPERTY_OBSERVATION, update_requests)
)


# initialize the simulator
simulator.initialize(start, None, time_scale_factor)

# execute the simulator
simulator.execute(start, duration, time_step, None, time_scale_factor)
