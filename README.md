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


# API

## Legacy (v1) post to station registry 

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
| 200      | Success                                             |
| 400      | Malformed post (usually from missing `station_url`) |
| 429      | Posting too frequently                              |

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

# License & Copyright

Copyright (c) 2023 Tom Keffer <tkeffer@gmail.com>

  See the file LICENSE.txt for your full rights.
