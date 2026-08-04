# What To Bring

## project structure
```
.
├── samples/                # fake people doing fake hikes for test purposes
├── input_handler/          # input handler and xml creation
├── model/                  # build prompt and call Gemini API
├── presentation/           # output presentation and performance analysis
├── evaluation/             # automated evaluation harness against the samples
├── server/                 # flask server + demo interface
├── tests/                  # unittest
└── what_to_bring.py        # entry point

```

## evaluate the model

Runs the model on every sample, scores it against the ground truth and prints
per-sample averages plus pooled micro-averages. Results are written to a JSON report.

```
$ python -m evaluation.run_evaluation --model mock            # deterministic mock, no API key
$ python -m evaluation.run_evaluation --model real            # calls the Gemini API (needs GEMINI_API_KEY)
$ python -m evaluation.run_evaluation --model mock --no-weather --output report.json
```

## run the estimation server (with demo interface)

Starts a Flask server exposing the estimation service and a simple web demo on `http://localhost:5000`.

```
$ python run_server.py
```

API:
- `POST /api/estimate` — multipart form with `gpx` (file) and `personal_information` + `hike_information` (files or JSON text). Returns `{hike_features, recommendations, overall_strategy}`.
- `GET /api/health` — health check.
- `GET /` — demo page where you can upload a GPX and paste the two JSONs.

## setup
- Clone the repository
```
$ git clone https://github.com/Filippo831/What_To_Bring.git
$ cd What_To_bring.git
```
- If the first time, create the virtual environment
```
$ python -m venv venv
```
- Activate virtual environment
```
$ source venv/bin/activate
```
- Install the requirements
```
$ pip install -r requirements.txt
```
- Download the map
```
$ wget https://download.geofabrik.de/europe/italy/nord-est-latest.osm.pbf
$ mv nord-est-latest.osm.pbf ./assets/map/
```
- install gdal tools to convert the map to a more efficient format (not tested)
```
ON WINDOWS:
$ winget install GISInternals.GDAL

ON MACOS:
$ brew install gdal
```
- Convert the map to a more efficient format
```
$ ogr2ogr -f GPKG ./assets/map/nord-est-custom.gpkg ./assets/map/nord-est-latest.osm.pbf lines
```
