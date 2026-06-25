from typing import Any, Hashable
from input_handler.gpx_analyzer.utils.classes import Gpx_features, Point
from input_handler.gpx_analyzer.utils.constants import WEATHER_FEATURES, HISTORICAL_YEARS
import openmeteo_requests
import numpy as np

import pandas as pd
import requests_cache
from retry_requests import retry  # pyright: ignore[reportUnknownVariableType]


def call_api(_point: Point, _is_recorded: bool):
    # Setup the Open-Meteo API client with cache and retry on error
    cache_session = requests_cache.CachedSession(".cache", expire_after=3600)
    retry_session = retry(cache_session, retries=5, backoff_factor=0.2)
    openmeteo = openmeteo_requests.Client(session=retry_session)  # pyright: ignore[reportArgumentType]
        
    # Make sure all required weather variables are listed here
    # The order of variables in hourly or daily is important to assign them correctly below
    if _is_recorded:
        url = "https://historical-forecast-api.open-meteo.com/v1/forecast"
        # get the date of the _point.time. The date should be in the format "YYYY-MM-DD"
        date = pd.to_datetime(_point.time, unit="s", utc=True).strftime("%Y-%m-%d")

        # TODO: uset he points inside 
        params = {
            "latitude": _point.latitude,
            "longitude": _point.longitude,
            "start_date": date,
            "end_date": date,
            "hourly": WEATHER_FEATURES,
        }
    else:
        url = "https://api.open-meteo.com/v1/forecast"
        params = {
            "latitude": _point.latitude,
            "longitude": _point.longitude,
            "hourly": WEATHER_FEATURES,
        }

    responses = openmeteo.weather_api(url, params=params)  # pyright: ignore[reportUnknownMemberType]

    # Process first location. Add a for-loop for multiple locations or weather models

    response = responses[0]

    return response


"""
    @params
    - point: tuple(latitude, longitude) = the point where we want to get the weather information
    @returns
    - response: dict = the weather information for the given point
    @body
    - Setup the Open-Meteo API client with cache and retry on error
"""


def get_weather(_point: Point, _is_recorded: bool):

    response = call_api(_point, _is_recorded)
    # Process hourly data. The order of variables needs to be the same as requested.
    hourly = response.Hourly()

    if hourly is None:
        return pd.DataFrame()

    hourly_data: dict[str, Any] = {  # pyright: ignore[reportExplicitAny]
        "date": pd.date_range(
            start=pd.to_datetime(hourly.Time(), unit="s", utc=True),
            end=pd.to_datetime(hourly.TimeEnd(), unit="s", utc=True),
            freq=pd.Timedelta(seconds=hourly.Interval()),
            inclusive="left",
        )
    }

    # extract the weather features from the hourly data and add them to the hourly_data dictionary
    for index, feature in enumerate(WEATHER_FEATURES):
        variable = hourly.Variables(index)
        if variable is not None:
            hourly_data[feature] = variable.ValuesAsNumpy()
        else:
            hourly_data[feature] = np.array([])

    hourly_dataframe = pd.DataFrame(data=hourly_data)

    return hourly_dataframe

def get_historical_average_weather(_point: Point, _target_time: pd.Timestamp) -> pd.DataFrame:
    """
    Fetches historical archive data for the same day/month over the past HISTORICAL_YEARS
    and averages the values
    """
    cache_session = requests_cache.CachedSession(".cache", expire_after=3600)
    retry_session = retry(cache_session, retries=5, backoff_factor=0.2)
    openmeteo = openmeteo_requests.Client(session=retry_session)  # pyright: ignore[reportArgumentType]
    
    url = "https://archive-api.open-meteo.com/v1/archive"
    
    # Store pulled arrays per feature across all target years
    feature_data: dict[str, list[np.ndarray]] = {feature: [] for feature in WEATHER_FEATURES}
    
    for year in range(1, HISTORICAL_YEARS + 1):
        # Shift target date back by 'year' years safely (handles leap years cleanly)
        hist_time = _target_time - pd.DateOffset(years=year)
        date_str = hist_time.strftime("%Y-%m-%d")
        
        params = {
            "latitude": _point.latitude,
            "longitude": _point.longitude,
            "start_date": date_str,
            "end_date": date_str,
            "hourly": WEATHER_FEATURES,
        }
        
        try:
            responses = openmeteo.weather_api(url, params=params)  # pyright: ignore[reportUnknownMemberType]
            if not responses:
                continue
            
            response = responses[0]
            hourly = response.Hourly()
            if hourly is None:
                continue
                
            for index, feature in enumerate(WEATHER_FEATURES):
                variable = hourly.Variables(index)
                if variable is not None:
                    feature_data[feature].append(variable.ValuesAsNumpy())
        except Exception:
            continue

    # Generate a matching 24-hour date range for the future target date
    target_date_start = _target_time.normalize()
    date_range = pd.date_range(
        start=target_date_start,
        periods=24,
        freq="h",
        tz="UTC"
    )
    
    hourly_data: dict[str, Any] = {"date": date_range}
    
    # Aggregate and average the collected historical data matrices
    for feature in WEATHER_FEATURES:
        arrays = feature_data[feature]
        valid_arrays = [arr for arr in arrays if len(arr) == 24]  # Ensure consistent dimensions
        
        if valid_arrays:
            # Average arrays across axis 0 (the years axis)
            hourly_data[feature] = np.mean(np.stack(valid_arrays, axis=0), axis=0)
        else:
            # Fallback gracefully if no historical information could be queried
            hourly_data[feature] = np.full(24, np.nan)
            
    return pd.DataFrame(data=hourly_data)

"""
    @params
    - starting_time: int = the unix time of the starting point of the hike
    - gpx_features: Gpx_features = the features of the gpx route, including the weather points and hiking time
    @returns
    - None (the weather information is added to the gpx_features object)
    @body
    - For each weather point, calculate the time when the hiker will reach that point based on the average speed of the hike and get the weather information for that point at that time. The weather information is then added to the gpx_features object.
"""

def analyze_weather_points(_gpx_features: Gpx_features):
    # average speed in seconds per kilometer
    # average_speed = gpx_features.hiking_time / gpx_features.distance * 1000
    weather_array: list[dict[Hashable, Any]] = []  # pyright: ignore[reportExplicitAny]

    for point in _gpx_features.weather_points:
        point_time = point.time

        # round the time to the closest hour
        round_time = point_time % 3600
        if round_time > 1800:
            point_time += 3600 - round_time
        else:
            point_time -= round_time

        # convert point_time (unix time format) to readable time format
        point_time = pd.to_datetime(point_time, unit="s", utc=True)

        # Check if the hike estimation is more than 14 days into the future
        now = pd.Timestamp.now(tz="UTC")
        if point_time > now + pd.Timedelta(days=14):
            hourly_dataframe = get_historical_average_weather(point, point_time)
        else:
            hourly_dataframe = get_weather(point, _gpx_features.is_recorded)

        # get the row of the hourly dataframe with the same date as point_time
        weather_information = hourly_dataframe[hourly_dataframe["date"] == point_time]

        # drop the date column from the weather_information dataframe
        weather_information = weather_information.drop(columns=["date"])

        # cast the dataframe to a dict and append it to weather_array
        weather_array.append(weather_information.to_dict(orient="records")[0])

    _gpx_features.set_weather_information(weather_array)

    return
