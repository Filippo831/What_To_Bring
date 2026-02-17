from constants import WEATHER_FEATURES
import openmeteo_requests

import pandas as pd
import requests_cache
from retry_requests import retry

"""
    @params
    - point: tuple(latitude, longitude) = the point where we want to get the weather information
    @returns
    - response: dict = the weather information for the given point
    @body
    - Setup the Open-Meteo API client with cache and retry on error
"""


def get_weather(point):
    # Setup the Open-Meteo API client with cache and retry on error
    cache_session = requests_cache.CachedSession(".cache", expire_after=3600)
    retry_session = retry(cache_session, retries=5, backoff_factor=0.2)
    openmeteo = openmeteo_requests.Client(session=retry_session)

    # Make sure all required weather variables are listed here
    # The order of variables in hourly or daily is important to assign them correctly below
    url = "https://api.open-meteo.com/v1/forecast"
    params = {"latitude": point[0], "longitude": point[1], "hourly": WEATHER_FEATURES}
    responses = openmeteo.weather_api(url, params=params)

    # Process first location. Add a for-loop for multiple locations or weather models

    response = responses[0]

    # Process hourly data. The order of variables needs to be the same as requested.
    hourly = response.Hourly()

    hourly_data = {
        "date": pd.date_range(
            start=pd.to_datetime(hourly.Time(), unit="s", utc=True),
            end=pd.to_datetime(hourly.TimeEnd(), unit="s", utc=True),
            freq=pd.Timedelta(seconds=hourly.Interval()),
            inclusive="left",
        )
    }

    # extract the weather features from the hourly data and add them to the hourly_data dictionary
    for index, feature in enumerate(WEATHER_FEATURES):
        hourly_data[feature] = hourly.Variables(index).ValuesAsNumpy()


    hourly_dataframe = pd.DataFrame(data=hourly_data)

    return hourly_dataframe

'''
    @params
    - starting_time: int = the unix time of the starting point of the hike
    - gpx_features: Gpx_features = the features of the gpx route, including the weather points and hiking time
    @returns
    - None (the weather information is added to the gpx_features object)
    @body
    - For each weather point, calculate the time when the hiker will reach that point based on the average speed of the hike and get the weather information for that point at that time. The weather information is then added to the gpx_features object.
'''

def analyze_weather_points(starting_time, gpx_features):
    # average speed in seconds per kilometer
    average_speed = gpx_features.hiking_time / gpx_features.distance * 1000

    for point_index, point in enumerate(gpx_features.weather_points):
        point_time = starting_time + round(point_index * average_speed)

        # round the time to the closest hour
        round_time = point_time % 3600
        if round_time > 1800:
            point_time += 3600 - round_time
        else:
            point_time -= round_time

        # convert point_time (unix time format) to readable time format
        point_time = pd.to_datetime(point_time, unit="s", utc=True)

        hourly_dataframe = get_weather(point)

        # get the row of the hourly dataframe with the same date as point_time
        weather_information = hourly_dataframe[hourly_dataframe["date"] == point_time]

        gpx_features.weather_information.append(weather_information.to_dict)

    return
