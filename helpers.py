import math
from constants import *
from classes import Gpx_features


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


def extract_features(gpx) -> Gpx_features:
    gpx_features = Gpx_features()
    total_distance = 0

    intermediate_points = []
    for track in gpx.tracks:
        for segment in track.segments:
            for point_index in range(len(segment.points) - 1):
                first = segment.points[point_index]
                second = segment.points[point_index + 1]

                # calculate the total distance of the gpx route
                before_distance = total_distance
                total_distance += haversine_distance(first, second)

                # every km take a point to get the weather information
                if (
                    math.floor(total_distance / 1000)
                    != math.floor(before_distance / 1000)
                    or point_index == 0
                ):
                    intermediate_points.append(segment.points[point_index])

    gpx_features.set_distance(total_distance)
    gpx_features.set_weather_points(intermediate_points)

    return gpx_features
