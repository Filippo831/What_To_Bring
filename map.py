import geopandas as gpd
from shapely.geometry import LineString, Point

def get_coords_information(_coords):
    # 1. Create the route line for the envelope
    route_line = LineString(_coords)
    search_envelope = route_line.envelope

    # 2. Load the data (filtering by envelope for speed)
    big_file = "map_data_baldo_trentino.gpkg"
    # We load ONLY the lines to keep things clean
    relevant_data = gpd.read_file(big_file, mask=search_envelope, engine="pyogrio")
    lines_only = relevant_data[relevant_data.geom_type.isin(['LineString', 'MultiLineString'])]

    # 3. Create your Point GeoDataFrame
    route_gdf = gpd.GeoDataFrame(
        geometry=[Point(c) for c in _coords], 
        crs="EPSG:4326"
    )

    # 4. CRITICAL STEP: Convert to a projected CRS (meters) to use a real-world buffer
    # EPSG:32632 is common for Trentino/Italy (WGS 84 / UTM zone 32N)
    route_gdf_m = route_gdf.to_crs("EPSG:32632")
    lines_only_m = lines_only.to_crs("EPSG:32632")

    # 5. Create a 10-meter buffer around each point
    route_gdf_m['geometry'] = route_gdf_m.buffer(10) 

    # 6. Spatial Join: Use 'intersects' instead of 'within'
    # This finds any line that passes through the 10m circle around your point
    results = gpd.sjoin(route_gdf_m, lines_only_m, how="left", predicate="intersects")

    results.to_csv("results.csv", index=False)

    print(results)
