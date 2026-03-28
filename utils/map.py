import geopandas as gpd
import pandas as pd
from shapely.geometry import LineString, Point
import re
from utils.constants import MAP_PATH


def extract_sac_scale(tags):
    if pd.isna(tags):
        return None
    # Look for "sac_scale"=>"value" using regex
    match = re.search(r'"sac_scale"=>"([^"]+)"', tags)
    return match.group(1) if match else None


def extract_mtb_scale(tags):
    if pd.isna(tags):
        return None
    # Look for "mtb_scale"=>"value" using regex
    match = re.search(r'"mtb:scale"=>"([^"]+)"', tags)
    return match.group(1) if match else None


def process_row(row):
    tags = row["other_tags"]
    if pd.isna(tags):
        return pd.Series({"surface": "asphalt", "sac_scale": None})

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


def analyze_path(_gpx_features):
    # Create a LineString from the GPX points to define the route
    route_line = LineString([(p.longitude, p.latitude) for p in _gpx_features.points])
    search_envelope = route_line.envelope

    # load opm information from the map file
    big_file = MAP_PATH

    # We load ONLY the lines to keep things clean
    relevant_data = gpd.read_file(
        big_file, mask=search_envelope, engine="pyogrio", layer="lines"
    )

    route_gdf = gpd.GeoDataFrame(
        geometry=[Point((p.longitude, p.latitude)) for p in _gpx_features.points],
        crs="EPSG:4326",
    )

    # Automatically picks the best meter-based projection for your specific points
    best_crs = route_gdf.estimate_utm_crs()
    route_gdf_m = route_gdf.to_crs(best_crs)
    lines_only_m = relevant_data.to_crs(best_crs)

    route_gdf_m["geometry"] = route_gdf_m.buffer(10)

    # This finds any line that passes through the 10m circle around your point
    results = gpd.sjoin(route_gdf_m, lines_only_m, how="left", predicate="intersects")

    # get rid of the geometry column and the index_right column
    results = results.drop(
        columns=[
            "geometry",
            "index_right",
            "waterway",
            "aerialway",
            "barrier",
            "man_made",
            "railway",
            "z_order",
        ]
    )

    # for all the results given for one point, extract only the lines with some value under the highway column
    # if there is no value, it means that there is no road at that point, so create an empty value that will be filled with "no road"
    filtered_results = results[results["highway"].notna()]
    filtered_results["highway"] = filtered_results["highway"].fillna("no road")

    # Lower number = Higher priority
    priority_map = {"path": 1, "track": 2, "footway": 3}
    # Default high value for any highway types not in your list
    filtered_results["priority"] = (
        filtered_results["highway"].map(priority_map).fillna(99)
    )

    sorted_df = filtered_results.sort_values(by="priority").sort_index()

    final_extract = sorted_df.groupby(level=0).first()
    # final_extract.to_csv("results.csv", index=True)

    result = final_extract.apply(process_row, axis=1)

    print(result)
    _gpx_features.set_path_information(result)

