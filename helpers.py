import math
from constants import CLIMB_LENGTH, GRADIENT, RADIUS
from classes import Gpx_features, Climb


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
    - distance_elevation: list with tuples indicating for each point the distance from the beginning and the altitude
    @body:
    - calculate the first derivative of the altitude to get the gradient and identify the climbs from that
    @return:
    - length
    - elevation_gain
    - start_distance
    - start_elevation
"""


def extract_climbs(distance_elevation):
    gradient_list: list[float] = [0]

    for iterator_index in range(len(distance_elevation) - 1):
        distance_delta = (
            distance_elevation[iterator_index + 1][0]
            - distance_elevation[iterator_index][0]
        )
        elevation_delta = (
            distance_elevation[iterator_index + 1][1]
            - distance_elevation[iterator_index][1]
        )

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
                    distance_elevation[index][0] - distance_elevation[starting_index][0]
                    > CLIMB_LENGTH
                ):
                    yield (
                        distance_elevation[starting_index],
                        distance_elevation[index],
                    )

                on_climb = False


def extract_features(gpx) -> Gpx_features:
    gpx_features = Gpx_features()
    total_distance = 0
    total_elevation = 0

    intermediate_points = []

    # list of tuples [(distance, altitude)]
    distance_elevation = []

    for track in gpx.tracks:
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

                # if the list is empty it means we have to include the first point as well
                if not distance_elevation:
                    distance_elevation.append((before_distance, first.elevation))

                distance_elevation.append((total_distance, second.elevation))

                # every km take a point to get the weather information
                if (
                    math.floor(total_distance / 1000)
                    != math.floor(before_distance / 1000)
                    or point_index == 0
                ):
                    intermediate_points.append((second.latitude, second.longitude))

    for climb in extract_climbs(distance_elevation):
        new_climb = Climb(climb[0], climb[1])
        gpx_features.add_climbs(new_climb)

    gpx_features.set_distance(total_distance)
    gpx_features.set_weather_points(intermediate_points)
    gpx_features.set_elevation_gain(total_elevation)
    gpx_features.calculate_hiking_time()

    return gpx_features
