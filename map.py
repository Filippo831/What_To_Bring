import geopandas as gpd
import pandas as pd
from shapely.geometry import LineString, Point
import re


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

    return pd.Series({"surface": surface, "sac_scale": sac_scale, "mtb_scale": mtb_scale})


def get_coords_information(_gpx_features):
    # 1. Create the route line for the envelope
    route_line = LineString([(p[0], p[1]) for p in _gpx_features.points])
    search_envelope = route_line.envelope

    # 2. Load the data (filtering by envelope for speed)
    big_file = "map_data_baldo_trentino.gpkg"
    # We load ONLY the lines to keep things clean
    relevant_data = gpd.read_file(
        big_file, mask=search_envelope, engine="pyogrio", layer="lines"
    )

    # 3. Create your Point GeoDataFrame
    route_gdf = gpd.GeoDataFrame(
        geometry=[Point((c[0], c[1])) for c in _gpx_features.points], crs="EPSG:4326"
    )

    # Automatically picks the best meter-based projection for your specific points
    best_crs = route_gdf.estimate_utm_crs()
    route_gdf_m = route_gdf.to_crs(best_crs)
    lines_only_m = relevant_data.to_crs(best_crs)

    # 5. Create a 10-meter buffer around each point
    route_gdf_m["geometry"] = route_gdf_m.buffer(10)

    # 6. Spatial Join
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

    # 1. Define the priority mapping
    # Lower number = Higher priority
    priority_map = {"path": 1, "track": 2, "footway": 3}
    # Default high value for any highway types not in your list
    filtered_results["priority"] = (
        filtered_results["highway"].map(priority_map).fillna(99)
    )

    # 2. Sort by index and then priority
    # sorted_df = filtered_results.sort_values(by=[filtered_results.index.name or 'index', 'priority'])
    sorted_df = filtered_results.sort_values(by="priority").sort_index()

    # 3. Group by the index and take the first occurrence (the one with highest priority)
    final_extract = sorted_df.groupby(level=0).first()
    # final_extract.to_csv("results.csv", index=True)

    # 5. Get the final result
    result = final_extract.apply(process_row, axis=1)

    # write in results.csv
    result.to_csv("results.csv", index=True)
    # filtered_results.to_csv("results.csv", index=True)
