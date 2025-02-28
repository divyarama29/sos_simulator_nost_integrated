# This Script stores all the functions that are used in the simulator code
# The functions are stored in a separate file to make the main code more readable

from typing import List

# Importing Libraries
import pandas as pd
import geopandas as gpd
from shapely import Geometry
from datetime import datetime, timedelta, timezone
from tatc.schemas import PointedInstrument, WalkerConstellation, SunSynchronousOrbit
from tatc.analysis import collect_multi_observations
from tatc.utils import swath_width_to_field_of_regard, swath_width_to_field_of_view
from tatc.analysis import collect_multi_observations
from tatc.schemas import Satellite
from tatc.schemas import Point
from tatc.analysis import collect_ground_track

# Configure Constellation


def Snowglobe_constellation(start: datetime) -> List[Satellite]:
    roll_angle = (30 + 33.5) / 2
    roll_range = 33.5 - 30
    # start = datetime(2019, 3, 1, tzinfo=timezone.utc)
    constellation = WalkerConstellation(
        name="SnowGlobe Ku",
        orbit=SunSynchronousOrbit(
            altitude=555e3,
            equator_crossing_time="06:00:30",
            equator_crossing_ascending=False,
            epoch=start,
        ),
        number_planes=1,
        number_satellites=5,
        instruments=[
            PointedInstrument(
                name="SnowGlobe Ku-SAR",
                roll_angle=-roll_angle,
                field_of_regard=2 * roll_angle
                + swath_width_to_field_of_regard(555e3, 50e3),
                along_track_field_of_view=swath_width_to_field_of_view(555e3, 50e3, 0),
                cross_track_field_of_view=roll_range
                + swath_width_to_field_of_view(555e3, 50e3, roll_angle),
                is_rectangular=True,
            )
        ],
    )
    satellites = constellation.generate_members()
    # satellite_dict = {sat.name: sat for sat in satellites}
    return satellites  # , satellite_dict


# Compute next observation opportunity using TATC collect observations

from joblib import Parallel, delayed


def compute_opportunity(
    constellation: List[Satellite],
    time: datetime,
    duration: timedelta,
    requests: List[Point],
) -> gpd.GeoSeries:
    # filter requests
    filtered_requsts = requests
    # filtered_requsts = [
    #     request
    #     for request in requests
    #     if request["simulation_status"].isna() or request["simulation_status"] is None
    # ]
    obsevations = pd.concat(
        Parallel(-1)(
            delayed(collect_multi_observations)(
                point, constellation, time, time + duration
            )
            for point in filtered_requsts
        ),
        ignore_index=True,
    ).sort_values(by="epoch", ascending=True)

    if not obsevations.empty:
        return obsevations.iloc[0]
    return None


# Computing Groundtrack and formatting into a dataframe


def compute_ground_track_and_format(
    sat_object: Satellite, observation_time: datetime
) -> Geometry:
    results = collect_ground_track(sat_object, [observation_time], crs="spice")
    # Formatting the dataframe
    return results.iloc[0]["geometry"]


# Code to filter requests
def filter_requests(requests: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    filtered_req = requests[
        requests["simulation_status"].isna() | (requests["simulation_status"] == "None")
    ]
    return filtered_req


# CALLBACK FUNCTIONS

# Reading master file


def read_master_file():
    req = gpd.read_file("Master_file")
    return req


# Update Requests in temporary dataframe
def update_requests(requests, collected_observation):
    merged = requests.merge(collected_observation, on="id", how="left")
    return merged


# Write to Master File
# Occurs at fixed time step


def write_back_to_appender(dataframe):
    constellation, satellite_dict = Snowglobe_constellation()
    req = gpd.read_file("Master_file")
    merged = req.merge(dataframe, on="id", how="left")
