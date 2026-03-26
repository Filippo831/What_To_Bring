import math
from utils.constants import (
    CLIMB_LENGTH,
    GRADIENT,
    RADIUS,
    ELEVATION_PER_HOUR,
    HIKING_SPEED,
)
from utils.classes import Gpx_features, Climb, Point
from itertools import pairwise
import datetime


# calculate the hiking time using Naismith's rule if the gpx is planned
# otherwise calculate the time between the first and the last point of the gpx
def calculate_hiking_time(
    _points: list[Point], _elevation_gain: int, _is_recorded: bool
) -> int:
    total_distance = _points[-1].cumulative_distance

    if not _is_recorded:
        hiking_time = round(
            total_distance / HIKING_SPEED * 3600
            + _elevation_gain / ELEVATION_PER_HOUR * 3600
        )
        return hiking_time

    else:
        if _points[0].time is not None and _points[-1].time is not None:
            return int((_points[-1].time - _points[0].time).total_seconds())
        else:
            return 0


# compute the distance between 2 points
def haversine_distance(first, second) -> float:
    inter_result = (
        (1 - math.cos(math.radians(first.latitude - second.latitude))) / 2
    ) + math.cos(math.radians(first.latitude)) * math.cos(
        math.radians(second.latitude)
    ) * ((1 - math.cos(math.radians(first.longitude - second.longitude))) / 2)

    ground_distance = 2 * math.asin(math.sqrt(inter_result)) * RADIUS

    new_distance = math.sqrt(
        pow(first.elevation - second.elevation, 2) + pow(ground_distance, 2)
    )

    return new_distance


"""
    @param:
    @body:
    - calculate the first derivative of the altitude to get the gradient and identify the climbs from that
    @return:
    - length
    - elevation_gain
    - start_distance
    - start_elevation
"""


def extract_climbs(points: list[Point]):
    gradient_list: list[float] = [0]

    for first, second in pairwise(points):
        distance_delta = second.cumulative_distance - first.cumulative_distance
        elevation_delta = first.elevation - second.elevation
        if distance_delta == 0:
            pass

        gradient = elevation_delta / distance_delta * 100

        gradient_list.append(gradient)

    on_climb = False
    starting_index = 0

    for index in range(len(gradient_list) - 1):
        if gradient_list[index] > GRADIENT:
            if not on_climb:
                on_climb = True
                starting_index = index

        else:
            if on_climb:
                if (
                    points[index].cumulative_distance
                    - points[starting_index].cumulative_distance
                    > CLIMB_LENGTH
                ):
                    yield (points[starting_index], points[index])

                on_climb = False


def extract_features(_gpx, _is_recorded, _starting_time) -> Gpx_features:
    gpx_features = Gpx_features()

    gpx_features.is_recorded = _is_recorded
    total_distance = 0
    total_elevation = 0

    for track in _gpx.tracks:
        for segment in track.segments:
            for point_index in range(len(segment.points) - 1):
                first = segment.points[point_index]
                second = segment.points[point_index + 1]

                # calculate the total distance of the gpx route
                before_distance = total_distance
                total_distance += haversine_distance(first, second)

                # calculate total poisitive elevation of the hike
                elevation_delta = second.elevation - first.elevation

                if elevation_delta > 0:
                    total_elevation += elevation_delta

                if len(gpx_features.points) == 0:
                    gpx_features.points.append(
                        Point(
                            first.latitude,
                            first.longitude,
                            0,
                            first.elevation,
                            _starting_time,
                        )
                    )

                gpx_features.points.append(
                    Point(
                        second.latitude,
                        second.longitude,
                        total_distance,
                        second.elevation,
                        (
                            second.time
                            if _is_recorded
                            else _starting_time
                            + calculate_hiking_time(
                                gpx_features.points, total_elevation, False
                            )
                        ),
                    )
                )

                # every km take a point to get the weather information
                if (
                    math.floor(total_distance / 1000)
                    != math.floor(before_distance / 1000)
                    or point_index == 0
                ):
                    gpx_features.append_weather_point(
                        Point(
                            second.latitude,
                            second.longitude,
                            total_distance,
                            second.elevation,
                            second.time if _is_recorded else None,
                        )
                    )

    for climb in extract_climbs(gpx_features.points):
        new_climb = Climb(climb[0], climb[1])
        gpx_features.add_climbs(new_climb)

    gpx_features.set_distance(total_distance)
    gpx_features.set_elevation_gain(total_elevation)

    hiking_time = calculate_hiking_time(
        gpx_features.points, total_elevation, _is_recorded
    )
    gpx_features.set_hiking_time(hiking_time)

    return gpx_features
