import geopandas as gpd
from shapely.geometry import LineString, Point
import re


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
    results = results.drop(columns=["geometry", "index_right"])

    # for all the results given for one point, extract only the lines with some value under the highway column
    # if there is no value, it means that there is no road at that point, so create an empty value that will be filled with "no road"
    filtered_results = results[results["highway"].notna()]
    filtered_results["highway"] = filtered_results["highway"].fillna("no road")

    highway_sequence = ["path", "track", "footway"]

    # iterate over the results by chunks of rows with same index
    for index, group in filtered_results.groupby(filtered_results.index):
        sequence_index = len(highway_sequence)  # default to length of the list if no match
        for _, row in group.iterrows():
            # if no road copy the previous surface
            if row["highway"] == "no road":
                if index > 0:
                    previous_surface = filtered_results.loc[index - 1, "surface"]
                    filtered_results.at[index, "surface"] = previous_surface
                
            # get the row with the lowest index value in the highway_sequence list. If not present the index value is the length of the list
            elif row["highway"] in highway_sequence:
                current_index = highway_sequence.index(row["highway"])
                if current_index < sequence_index:
                    sequence_index = current_index
                    # in other_tags get the value of surface and copy it in the surface column
                    regex = r'"surface"=>"([^"]*)"'
                    try:
                        surface_value = re.findall(regex, row["other_tags"])[0]
                        filtered_results.at[index, "surface"] = surface_value
                    except:
                        filtered_results.at[index, "surface"] = "unknown"



            




    # write in results.csv
    filtered_results.to_csv("results.csv", index=True)

    

