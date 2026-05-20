# What To Bring

## project structure
``` 
.
├── input_handler/          # input handler and xml creation
├── model/                  # build prompt and call Gemini API
├── presentation/           # output presentation and performance analysis
└── what_to_bring.py        # entry point
```

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
$ wget https://download.geofabrik.de/europe/italy/nord-est-latest-free.gpkg.zip
$ unzip nord-est-latest-free.gpkg.zip -d ./assets/map

```

