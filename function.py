# This Script stores all the functions that are used in the simulator code
# The functions are stored in a separate file to make the main code more readable

# Importing Libraries
import pandas as pd
import geopandas as gpd
from datetime import datetime,timedelta, timezone
from tatc.schemas import PointedInstrument, WalkerConstellation, SunSynchronousOrbit
from tatc.analysis import collect_multi_observations
from tatc.utils import swath_width_to_field_of_regard, swath_width_to_field_of_view
from tatc.analysis import collect_multi_observations
from tatc.schemas import Satellite
from tatc.schemas import Point
from tatc.analysis import collect_ground_track

# Configure Constellation

def Snowglobe_constellation():
    roll_angle = (30 + 33.5)/2
    roll_range = (33.5 - 30)
    start = datetime(2019, 3, 1, tzinfo=timezone.utc)
    constellation = WalkerConstellation(
        name="SnowGlobe Ku",
        orbit=SunSynchronousOrbit(
            altitude=555e3, 
            equator_crossing_time="06:00:30", 
            equator_crossing_ascending=False,
            epoch=start
        ),
        number_planes=1,
        number_satellites=5,
        instruments=[
            PointedInstrument(
                name="SnowGlobe Ku-SAR",
                roll_angle=-roll_angle,
                field_of_regard=2*roll_angle + swath_width_to_field_of_regard(555e3, 50e3),
                along_track_field_of_view=swath_width_to_field_of_view(555e3, 50e3, 0),
                cross_track_field_of_view=roll_range + swath_width_to_field_of_view(555e3, 50e3, roll_angle),
                is_rectangular=True
            )
        ]
    )
    satellites = constellation.generate_members()
    satellite_dict = {sat.name: sat for sat in satellites}
    return constellation, satellite_dict


# Compute next observation opportunity using TATC collect observations

def compute_opportunity(constellation,start_time,requests):              
    end = start_time + timedelta(days=1)
    combined_results = pd.DataFrame()
    for index,row in requests.iterrows():    
        loc = Point(id=row['id'],latitude=row['latitude'],longitude=row['longitude'])
        results = collect_multi_observations(loc, constellation, start_time, end)
        combined_results = pd.concat([combined_results, results], ignore_index=True)    
    combined_results = combined_results.sort_values(by='epoch', ascending=True)
    return combined_results.iloc[0]


# Computing Groundtrack and formatting into a dataframe

def compute_ground_track_and_format(sat_object,observation_time,tatc_result):
    results = collect_ground_track(sat_object,observation_time,crs='spice')
    # Formatting the dataframe
    tatc_result['ground_track'] = results['geometry']
    selected_columns = ['id', 'geometry', 'epoch', 'satellite', 'ground_track']
    ground_track = results[selected_columns]
    return ground_track


# Code to filter requests
def filter_requests(requests):
    filtered_req = requests[requests['simulation_status'].isna() | (requests['simulation_status'] == "None")]
    return filtered_req


# CALLBACK FUNCTIONS

# Reading master file

def read_master_file():
    req = gpd.read_file('Master_file')
    return req

# Update Requests in temporary dataframe
def update_requests(requests,collected_observation):
    merged = requests.merge(collected_observation, on='id', how='left')
    return merged

# Write to Master File  
# Occurs at fixed time step

def write_back_to_appender(dataframe):
    constellation, satellite_dict = Snowglobe_constellation()
    req = gpd.read_file('Master_file')
    merged = req.merge(dataframe, on='id', how='left')

