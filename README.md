# PNW Trail Planner (CS361 Milestone #3)

A text-based command-line tool that helps Pacific Northwest hikers plan multi-night backcountry trips. The main program integrates with four microservices over ZeroMQ to fetch weather forecasts, daylight hours, drive times, and filtered trail lists.

## Architecture

| Component             | Repo                          | Port   |
| --------------------- | ----------------------------- | ------ |
| Main Program          | this repo                     | (none) |
| Daylight Microservice | `cs361-daylight-microservice` | 5555   |
| Geocoder Microservice | `cs361-geocoder-microservice` | 5556   |
| Weather Microservice  | `cs361-weather-microservice`  | 5557   |
| Filter Microservice   | `cs361-filter-microservice`   | 5558   |

Each microservice runs in its own process. The main program communicates with each one via JSON requests and responses over ZeroMQ REQ/REP sockets — no direct function calls between programs.

## Setup

```bash
pip install pyzmq astral
```

## Run

Open **five** terminal windows. In each of the four microservice repos:

```bash
# Terminal 1
cd ../cs361-daylight-microservice
python3 daylight_service.py

# Terminal 2
cd ../cs361-geocoder-microservice
python3 geocoder_service.py

# Terminal 3
cd ../cs361-weather-microservice
python3 weather_service.py

# Terminal 4
cd ../cs361-filter-microservice
python3 filter_service.py
```

Then in this repo:

```bash
# Terminal 5
python3 main.py
```
