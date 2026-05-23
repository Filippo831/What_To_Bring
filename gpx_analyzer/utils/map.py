# pyright: basic

import re
from typing import Any, cast

import geopandas as gpd
import pandas as pd
from shapely.geometry import LineString, Point

from gpx_analyzer.utils.classes import Gpx_features
from gpx_analyzer.utils.constants import MAP_PATH

"""
    @params
    - tags: string = the string containing the other_tags information from the map file
    @returns
    - sac_scale: string or None = the value of the sac_scale tag if it exists, otherwise None
    @body
    - Use regex to extract the value of the sac_scale tag from the tags string. If the tag does not exist, return None.
"""


def extract_sac_scale(tags: Any) -> str | None:  # pyright: ignore[reportExplicitAny, reportAny]
    if not isinstance(tags, str):
        return None

    # Look for "sac_scale"=>"{value}" using regex
    match = re.search(r'"sac_scale"=>"([^"]+)"', tags)
    return match.group(1) if match else None


"""
    def extract_mtb_scale(tags):
    @params
    - tags: string = the string containing the other_tags information from the map file
    @returns
    - mtb_scale: string or None = the value of the mtb_scale tag if it exists, otherwise None
    @body
    - Use regex to extract the value of the mtb_scale tag from the tags string. If the tag does not exist, return None.
"""


def extract_mtb_scale(tags: Any) -> str | None:    # pyright: ignore[reportExplicitAny, reportAny]
    if not isinstance(tags, str):
        return None

    # Look for "mtb_scale"=>{"value"} using regex
    match = re.search(r'"mtb:scale"=>"([^"]+)"', tags)
    return match.group(1) if match else None


"""
    def process_row(row):
    @params
    - row: pandas Series = a row from the DataFrame containing the map information for a specific point
    @returns
    - pandas Series = a Series containing the surface, sac_scale, and mtb_scale information extracted from the row
    @body
    - Extract the surface, sac_scale, and mtb_scale information from the row using regex and the helper functions defined above. If the surface information is missing or generic (asphalt) and
"""


def process_row(row: pd.Series) -> pd.Series:
    tags: Any = row["other_tags"]  # pyright: ignore[reportExplicitAny, reportAny]
    if not isinstance(tags, str):
        surface = "asphalt"
        if row["highway"] == "track":
            surface = "ground"

        return pd.Series({"surface": surface, "sac_scale": None, "mtb_scale": None})

    surface_match = re.search(r'"surface"=>"([^"]+)"', tags)
    surface = surface_match.group(1) if surface_match else "asphalt"

    # Logic: if highway is track and surface is missing/generic, set to ground
    if row["highway"] == "track" and (pd.isna(surface) or surface == "asphalt"):
        surface = "ground"

    sac_scale = extract_sac_scale(tags)
    mtb_scale = extract_mtb_scale(tags)

    return pd.Series(
        {"surface": surface, "sac_scale": sac_scale, "mtb_scale": mtb_scale}
    )


def get_surface_percentage(_result: pd.DataFrame, _gpx_features: Gpx_features) -> dict[str, float]:
    points_count = len(_gpx_features.points)
    dataframe_rows = _result.shape[0]

    assert points_count == dataframe_rows, (
        "The number of points and the number of rows in the result dataframe must be the same."
    )

    surface_length: dict[str, float] = {}

    for i in range(1, dataframe_rows):
        sac_scale: Any = _result.iloc[i]["sac_scale"]  # pyright: ignore[reportExplicitAny, reportAny]
        mtb_scale: Any = _result.iloc[i]["mtb_scale"]  # pyright: ignore[reportExplicitAny, reportAny]
        surface: Any = _result.iloc[i]["surface"]  # pyright: ignore[reportExplicitAny, reportAny]

        surface_type: str = ""
        # if the sac_scale is defined, use that to derive the surface type
        if isinstance(sac_scale, str):
            try:
                surface_type = sac_scale.replace("demanding_", "")
            except AttributeError:
                raise ValueError(
                    f"Invalid sac_scale value: {_result.iloc[i]['sac_scale']}"
                )

        elif isinstance(mtb_scale, str):
            """
            if the sac_scale is not defined but the mtb_scale is defined, use that to derive the surface type
            - mtb_scale 0 and 1 correspond to hiking
            - mtb_scale 2 to 4 correspond to mountain_hiking
            - mtb_scale 5 and above correspond to alpine_hiking
            """
            if mtb_scale in ["0", "1"]:
                surface_type = "path"
            elif mtb_scale in ["2", "3", "4"]:
                surface_type = "mountain_hiking"
            else:
                surface_type = "alpine_hiking"

        else:
            if isinstance(surface, str) and surface in ["ground", "dirt", "earth"]:
                surface_type = "path"
            else:
                surface_type = "asphalt"

        distance = (
            _gpx_features.points[i].cumulative_distance
            - _gpx_features.points[i - 1].cumulative_distance
        )
        surface_length[surface_type] = surface_length.get(surface_type, 0) + distance

    surface_percentage: dict[str, float] = dict()
    for k, v in surface_length.items():
        surface_percentage[k] = (v / _gpx_features.distance) * 100

    return surface_percentage


"""
    def analyze_path(_gpx_features):
    @params
    - gpx_features: Gpx_features = the features of the gpx route, including the points of the route and the weather points
    @returns
    - None (the path information is added to the gpx_features object)
    @body
    - For each point in the gpx route, find the corresponding information from the map file (such as surface, sac_scale, mtb_scale) based on the location of the point.
"""


def analyze_path(_gpx_features: Gpx_features):
    # Create a LineString from the GPX points to define the route
    print(f"[DEBUG] Number of input GPX points: {len(_gpx_features.points)}")
    route_line = LineString([(p.longitude, p.latitude) for p in _gpx_features.points])
    search_envelope = route_line.envelope

    # load opm information from the map file
    big_file = MAP_PATH

    # We load ONLY the lines to keep things clean
    print(f"[DEBUG] Loading lines from '{big_file}' using envelope mask...")

    # check if big_file exists

    relevant_data = gpd.read_file(  # pyright: ignore[reportUnknownMemberType]
        big_file, mask=search_envelope, engine="pyogrio", layer="lines"
    )
    print(f"[DEBUG] Loaded {len(relevant_data)} relevant map lines within the route envelope.")

    route_gdf = gpd.GeoDataFrame(
        geometry=[Point((p.longitude, p.latitude)) for p in _gpx_features.points],
        crs="EPSG:4326",
    )

    # Automatically picks the best meter-based projection for your specific points
    best_crs = route_gdf.estimate_utm_crs()
    print(f"[DEBUG] Automatically selected UTM CRS: {best_crs}")
    route_gdf_m = route_gdf.to_crs(best_crs)
    lines_only_m = relevant_data.to_crs(best_crs)

    route_gdf_m["geometry"] = route_gdf_m.buffer(10)  # pyright: ignore[reportUnknownMemberType]

    # This finds any line that passes through the 10m circle around your point
    results = gpd.sjoin(route_gdf_m, lines_only_m, how="left", predicate="intersects")
    print(f"[DEBUG] Spatial join completed. Total raw intersection rows found: {len(results)}")

    # get rid of the geometry column and the index_right column
    results = results.drop(
        columns=[
            "geometry",
            "index_right",
        ]
    )
    # output the results inside a csv file to check what's inside
    results.to_csv("results.csv", index=False)
    print("[DEBUG] Wrote raw spatial join results to 'results.csv'.")

    # for all the results given for one point, extract only the lines with some value under the highway column
    # if there is no value, it means that there is no road at that point, so create an empty value that will be filled with "no road"
    filtered_results = cast(pd.DataFrame, results[results["highway"].notna()].copy())
    print(f"[DEBUG] Rows with valid 'highway' tags: {len(filtered_results)} (Dropped {len(results) - len(filtered_results)} rows with NaN 'highway')")
    filtered_results["highway"] = filtered_results["highway"].fillna("no road")

    # Lower number = Higher priority
    priority_map = {"path": 1, "track": 2, "footway": 3}
    # Default high value for any highway types not in your list
    filtered_results["priority"] = (
        filtered_results["highway"].map(priority_map).fillna(99)
    )

    sorted_df = filtered_results.sort_values(by="priority").sort_index()

    final_extract = sorted_df.groupby(level=0).first()
    print(f"[DEBUG] After deduplication (highest priority per point), final unique points to process: {len(final_extract)}")
    
    if not final_extract.empty and "highway" in final_extract.columns:
        print("[DEBUG] Breakdown of final highway types selected:")
        print(final_extract["highway"].value_counts())

    result = final_extract.apply(process_row, axis=1)

    surface_percentage = get_surface_percentage(result, _gpx_features)
    print(f"[DEBUG] Calculated surface percentages: {surface_percentage}")

    _gpx_features.set_surface_percentage(surface_percentage)
