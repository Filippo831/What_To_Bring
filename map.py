import geopandas as gpd
from shapely.geometry import LineString, Point


def get_coords_information(_gpx_features):
    # 1. Create the route line for the envelope
    route_line = LineString(_gpx_features.points)
    search_envelope = route_line.envelope

    # 2. Load the data (filtering by envelope for speed)
    big_file = "map_data_baldo_trentino.gpkg"
    # We load ONLY the lines to keep things clean
    relevant_data = gpd.read_file(
        big_file, mask=search_envelope, engine="pyogrio", layer="lines"
    )

    # 3. Create your Point GeoDataFrame
    route_gdf = gpd.GeoDataFrame(
        geometry=[Point(c) for c in _gpx_features.points], crs="EPSG:4326"
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

    results.to_csv("results.csv", index=False)

    print(results)
