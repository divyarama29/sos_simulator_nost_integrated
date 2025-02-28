# Entity Class

from datetime import datetime, timedelta
import logging
from typing import List

from geojson_pydantic import Polygon, MultiPolygon
from joblib import Parallel, delayed
from nost_tools import Entity
import numpy as np
import geopandas as gpd
import pandas as pd
import shapely
from shapely.geometry import Point
from skyfield.api import wgs84
from tatc.analysis import collect_ground_track, collect_observations
from tatc.schemas import Satellite as TATC_Satellite, Point as TATC_Point

from nost_sim_integrated_code.function import (
    compute_opportunity,
    update_requests,
    Snowglobe_constellation,
    compute_ground_track_and_format,
    filter_requests,
)

# from .schemas import Request, Observation

logger = logging.getLogger(__name__)


class Collect_Observations(Entity):
    """
    Reports the next observation opportunity and
    records observations when collected.
    """

    # defining class constants

    PROPERTY_OBSERVATION = "observation_collected"

    def __init__(
        self,
        constellation: List[TATC_Satellite],
        requests: List[TATC_Point],
    ):
        super().__init__()
        # save initial values
        self.init_constellation = constellation
        self.init_requests = requests

        # declare state variables
        self.constellation = None
        self.requests = None
        self.next_requests = None
        self.observation_collected = None
        self.new_requests = None

    def initialize(self, init_time: datetime):
        super().initialize(init_time)

        # initialize state variables
        self.constellation = {sat.name: sat for sat in self.init_constellation}
        self.requests = self.init_requests.copy()
        self.next_requests = None
        self.observation_collected = None
        self.new_requests = None

    def tick(self, time_step: timedelta):
        super().tick(time_step)
        # Set all the tick operations here

        self.observation_collected = compute_opportunity(
            self.constellation.values(), self._time, time_step, self.requests
        )

        if self.observation_collected is not None:
            if np.random.rand() <= 0.75:
                # get the satellite that collected the observation
                satellite = self.constellation[self.observation_collected["satellite"]]
                # Call the groundtrack function
                self.observation_collected["ground_track"] = (
                    compute_ground_track_and_format(
                        satellite, self.observation_opportunity
                    )
                )
                self.next_requests = self.requests.copy()
                # update next_requests to reflect collected observation
            else:
                self.observation_collected = None

    def tock(self):
        super().tock()
        if self.observation_collected is not None:
            self.notify_observers(
                self.PROPERTY_OBSERVATION,
                None,
                self.observation_collected["ground_track"],
            )
            # update requests (maybe a spatial join?)
            self.requests = self.next_requests

        # check for new requests
        if self.new_requests is not None:
            for request in self.new_requests:
                self.requests.append(request)
            self.new_requests = None
