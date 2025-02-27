# Entity Class

from datetime import datetime, timedelta
import logging
from typing import List

from geojson_pydantic import Polygon, MultiPolygon
from joblib import Parallel, delayed
from nost_tools import Entity
import numpy as np
import pandas as pd
import shapely
from shapely.geometry import Point
from skyfield.api import wgs84
from tatc.analysis import collect_ground_track, collect_observations
from tatc.schemas import Satellite as TATC_Satellite, Point as TATC_Point

from nost_sim_integrated_code.function import compute_opportunity, update_requests,Snowglobe_constellation,compute_ground_track_and_format,filter_requests

# from .schemas import Request, Observation

logger = logging.getLogger(__name__)

class Collect_Observations(Entity):
  """
     Observation opportunity entity.
    """  
  
  # defining class constants

  PROPERTY_OBSERVATION = "observation_collected" 

  def __init__(
      self,
      constellation: TATC_Satellite,
      start_time: datetime,     
      requests: List[TATC_Point],
  ) :
    super().__init__()
    self.constellation = constellation,    
    self.requests = requests
    self.previous_observation = None
    self.observation_opportunity = None

    def initialize(self, init_time: datetime):
      super().initialize(init_time)
      # Set all the initializations here

      # Snowglobe constellation      
      const,satellite_dict = Snowglobe_constellation()
      self.constellation = const 
      self.satellite_dict = satellite_dict      

      # Previous observation to simulation start time
      self.previous_observation = init_time

      # Observation flag 
      self.observation_collected = False

      # tatc result with satellite, epoch time and id
      self.tatc_result = compute_opportunity(self.constellation,init_time,self.requests)
      self.observation_opportunity = self.tatc_result['epoch']


    def tick(self, time_step: timedelta):
      super().tick(time_step)
      # Set all the tick operations here
      if self.observation_opportunity < self._time + time_step and self.observation_opportunity is not None:
        if np.random.rand() <= 0.75:
          self.previous_observation = self.observation_opportunity
          self.observation_collected = True
          satellite = self.satellite_dict[self.tatc_result['satellite']]
          # Call the groundtrack function
          self.ground_track = compute_ground_track_and_format(satellite,self.observation_opportunity,self.tatc_result)
        else:
          self.observation_collected = False
          start_time = self._time + timedelta(minutes=1)
          self.tatc_result = compute_opportunity(self.constellation,start_time,self.requests)
          self.observation_opportunity = self.tatc_result['epoch']
          
    def tock(self, time_step: timedelta):
      super().tock()
      if self.observation_collected == True:
        updated_data = self.notify_observers(self.PROPERTY_OBSERVATION,self.ground_track)
        self.requests = filter_requests(updated_data)
        self.tatc_result = compute_opportunity(self.constellation,start_time,self.requests)
        self.observation_opportunity = self.tatc_result['epoch']


        












      

  






      

        


        

        
      