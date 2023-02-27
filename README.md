# weereg

# Install

## Prerequisites
- Python 3.6 or greater

## Steps

Change to the directory `weereg-py` is in, then

```shell
# Create a virtual environment
python3 -m venv venv
# Activate it
source ./venv/bin/activate
# Install dependencies:
python3 -m pip install flask
python3 -m pip install pymysql

# Create the database if necessary:
python3 -m flask --app weereg init-db

# Run the application:
python3 -m flask --app weereg run
```


# V1 (Legacy) API

## Post to station registry 

This is the legacy API to post information about a station to the
database. While it "posts", it actually uses an HTTP GET method.

```
GET /api/v1/stations
```

**Parameters**

| *Name*          | *Type* | *Description*                                                                                       |
|:----------------|:-------|:----------------------------------------------------------------------------------------------------|
| `station_url`   | string | A unique descriptor that identifies a station. Can be an URL, but it doesn't have to be. Required.  |
| `description`   | string | A description of the station or its location. E.g., "North Pole, Earth" Optional.                   |
| `latitude`      | float  | The station latitude Optional.                                                                      |
| `longitude`     | float  | The station longitude Optional.                                                                     |
| `station_type`  | string | The hardware family. E.g., "Vantage". Optional.                                                     |
| `station_model` | string | The specific station model. E.g., "Vantage Pro2". Optional.                                         |
| `weewx_info`    | string | The WeeWX version. E.g., "4.10.2". Optional.                                                        |
| `python_info`   | string | The version of Python. E.g., "3.10.5". Optional.                                                    |
| `platform_info` | string | As returned by `platform.platform`. E.g., "Linux-5.15.0-60-generic-x86_64-with-glibc2.35" Optional. |
| `config_path`   | string | The path to the configuration file. E.g., "/home/weewx/weewx.conf" Optional.                        |
| `entry_path`    | string | The path to `weewxd`. E.g., "/home/weewx/bin/weewxd" Optional.                                      |                         


**Response codes**

| *Status* | *Meaning*                                           |
|:---------|:----------------------------------------------------|
| `200`    | Success                                             |
| `400`    | Malformed post (usually from missing `station_url`) |
| `429`    | Posting too frequently                              |

**Examples**

Post information about a station. Note the response code of `200`.

```shell
$ curl -i --silent -X GET 'http://localhost:5000/api/v1/stations?station_url=https%3A%2F%2Fthreefools.org%2Fweather&description=Test+of+4.10.2&latitude=45.0000&longitude=-122.0000&station_type=Vantage&station_model=Vantage+Pro2&python_info=3.10.5&platform_info=Linux-5.15.0-60-generic-x86_64-with-glibc2.35&config_path=%2Fhome%2Fweewx%2Fweewx.conf&entry_path=%2Fhome%2Fweewx%2Fbin%2Fweewxd&weewx_info=4.10.2'
HTTP/1.1 200 OK
Server: Werkzeug/2.2.3 Python/3.8.10
Date: Mon, 27 Feb 2023 15:53:22 GMT
Content-Type: text/html; charset=utf-8
Content-Length: 2
Connection: close
```

Do it again immediately. By default, the app limits posts to once an hour. 
If you exceed this, it returns an error code of `429`.

```shell
$ curl -i --silent -X GET 'http://localhost:5000/api/v1/stations?station_url=https%3A%2F%2Fthreefools.org%2Fweather&description=Test+of+4.10.2&latitude=45.0000&longitude=-122.0000&station_type=Vantage&station_model=Vantage+Pro2&python_info=3.10.5&platform_info=Linux-5.15.0-60-generic-x86_64-with-glibc2.35&config_path=%2Fhome%2Fweewx%2Fweewx.conf&entry_path=%2Fhome%2Fweewx%2Fbin%2Fweewxd&weewx_info=4.10.2'
HTTP/1.1 429 TOO MANY REQUESTS
Server: Werkzeug/2.2.3 Python/3.8.10
Date: Mon, 27 Feb 2023 15:55:14 GMT
Content-Type: text/html; charset=utf-8
Content-Length: 26
Connection: close

Registering too frequently
```

This time leave out the required parameter `station_url`. An error code of `400`
(`BAD REQUEST`) is returned.

``` shell
$ curl -i --silent -X GET 'http://localhost:5000/api/v1/stations?latitude=45.0000&longitude=-122.0000&station_type=Vantage&station_model=Vantage+Pro'
HTTP/1.1 400 BAD REQUEST
Server: Werkzeug/2.2.3 Python/3.8.10
Date: Mon, 27 Feb 2023 16:03:57 GMT
Content-Type: text/html; charset=utf-8
Content-Length: 29
Connection: close

Missing parameter station_url
```


# V2 API

## Get active stations 

Return the latest information about stations since some time ago.

```
GET /api/v2/stations
```

**Parameters**

| *Name*    | *Type* | *Description*                                                                                                           |
|:----------|:-------|:------------------------------------------------------------------------------------------------------------------------|
| `since`   | int    | Include results since this time. Optional.                                                                              |
| `max_age` | int    | How old a station can be to be included. Can use [*duration notation*](#duration-notation). Default is `30d`. Optional. |
| `limit`   | int    | Maximum number of stations to return. Default is 2000. Optional.                                                        |

NB: You can specify `since` or `max_age`, but not both.

Results are returned in ascending order of `last_seen`.

**Response codes**

| *Status* | *Meaning*                                                              |
|:---------|:-----------------------------------------------------------------------|
| `200`    | Success                                                                |
| `400`    | Badly formed request. Perhaps a character where a number was expected? |      

**Examples**

Request stations since 90 days ago, returning only the first 4.

```shell
$ curl -i --silent -X GET 'http://127.0.0.1:5000/api/v2/stations?max_age=90d&limit=4'
HTTP/1.1 200 OK
Server: Werkzeug/2.2.3 Python/3.8.10
Date: Mon, 27 Feb 2023 22:17:23 GMT
Content-Type: application/json
Content-Length: 2486
Connection: close

[
 {
    "description": "Froggit Bft",
    "last_addr": "41.13.67.20",
    "last_seen": 1669797930,
    "latitude": 45.24,
    "longitude": 18.3,
    "platform_info": "Linux-5.15.32-v7+-armv7l-with-glibc2.31",
    "python_info": "3.9.2",
    "station_model": "ecowitt-client",
    "station_type": "Interceptor",
    "station_url": "https://acme.com",
    "weewx_info": "4.7.0"
  },
  {
    "description": "Jakarta Selatan",
    "last_addr": "108.117.139.28",
    "last_seen": 1669863022,
    "latitude": -7.14,
    "longitude": 108.6,
    "platform_info": "Linux-4.19.66+-armv6l-with-debian-9.11",
    "python_info": "2.7.13",
    "station_model": "WA1091",
    "station_type": "FineOffsetUSB",
    "station_url": "https://whizbang.com/weewx/",
    "weewx_info": "4.0.0"
  },
  {
    "description": "Seattle, WA",
    "last_addr": "93.13.18.0",
    "last_seen": 1669875026,
    "latitude": 47.10,
    "longitude": -122.1,
    "platform_info": "Linux-4.19.66-v7+-armv7l-with-debian-9.13",
    "python_info": "2.7.13",
    "station_model": "AcuRite 02032",
    "station_type": "AcuRite",
    "station_url": "https://fabulous.com",
    "weewx_info": "4.5.1"
  },
  {
    "description": "Santiago",
    "last_addr": "136.118.127.11",
    "last_seen": 1670095166,
    "latitude": -39.5,
    "longitude": -58.7,
    "platform_info": "Linux-4.19.66-v7+-armv7l-with-debian-9.13",
    "python_info": "2.7.13",
    "station_model": "ecowitt-client",
    "station_type": "Interceptor",
    "station_url": "https://myweather.com/weewx",
    "weewx_info": "4.3.0"
  }
]
```
Do it again, but note the malformed `max_age`. Returns a 400 ("BAD REQUEST")
response.

```shell
$ curl -i --silent -X GET 'http://127.0.0.1:5000/api/v2/stations?max_age=90b&limit=4'
HTTP/1.1 400 BAD REQUEST
Server: Werkzeug/2.2.3 Python/3.8.10
Date: Mon, 27 Feb 2023 22:36:00 GMT
Content-Type: text/html; charset=utf-8
Content-Length: 20
Connection: close

Badly formed request
```

## Duration notation

| *Example* | *Meaning*                   |
|:----------|:----------------------------|
| `7200`    | 7,200 seconds               |
| `2h`      | 2 hours (7,200 seconds)     |
| `120M`    | 120 minutes (7,200 seconds) |
| `7d`      | 7 days (604,800 seconds)    |

# License & Copyright

Copyright (c) 2023 Tom Keffer <tkeffer@gmail.com>

  See the file LICENSE.txt for your full rights.
