# weereg

A Flask-based station registry for WeeWX.

# Install

## Prerequisites
- Python 3.8 or greater

## Setting up weereg

You can set up weereg either as a development environment, or as a production
environment.

### Common elements
This section has the steps common to both.

These steps assume the weereg code will be in your home directory in 
`~/weereg-py`, but they can easily be modified to set it up someplace else.

1. Clone weereg into your user directory:

    ```shell
    cd ~
    git clone https://github.com/tkeffer/weereg-py.git
   
    # cd into it for the rest of the steps
    cd weereg-py
    ```

2. Copy the sample configuration file, then edit it.
   DO NOT EDIT `config-sample.py`! It would be too easy to accidentally
   include your credentials, then commit the file. Edit the copy!

   ```shell
   cp config-sample.py config.py
   nano config.py
   ```

3. Set up the virtual environment:

    ```shell
    # Create a virtual environment
    python3 -m venv venv
    # Activate it
    source ./venv/bin/activate
    # Install dependencies:
    python3 -m pip install -r requirements.txt
    ```

4. If necessary, create and initialize the database:
    
   ```shell
    # Create the database if necessary:
    python3 -m flask --app weereg init-db
    ```

### Setting up a development environment

To set up a development environment, follow the "Common" steps above, then...

1. Create a user `weereg` with password `weereg`:

   ```
   mysql -u root -p
   mysql> create user 'weereg' identified by 'weereg';
   mysql> grant select,update,create,delete,insert,alter,drop on weereg.* to weereg;
   ```

2. Run the application directly, using debug mode:

    ```shell
    # Run the application:
    python3 -m flask --app weereg run --debug
    ```
   
   The flask application will now be up and running, and monitoring port 5000.

3. Set up a mini reverse proxy on the nginx server. This will only work for V2
   API requests.

   ````nginx configuration
   server {
   
        ... # Previous content
        
        Forward all V2 API requests on to the app server.
        location /api/v2 {
            include proxy_params;
            proxy_pass http://localhost:5000;
        }
        
        ...
   }
   ```


### Setting up a production environment

To set up a production environment, follow the "Common" steps above. We will
then add some steps that will allow weereg to be run as a standalone WSGI
application using the application server [gunicorn](https://gunicorn.org/),
proxied by an nginx server.

1. Create a location where we will have write privileges for the log:
   ```
   sudo mkdir /var/log/weereg
   sudo chown www-data:www-data /var/log/weereg
   ```

2. Edit the configuration file `config.py` to reflect the new location of the 
   log. For example, change
 
       'filename': '/var/tmp/weereg.log',

   to   

        'filename': '/var/log/weereg/weereg.log',
   
3. Create a systemd unit file called `weereg.service` with the following
   contents. Be sure to replace `username` with your username:

    ```unit file (systemd)
    # File /etc/systemd/system/weereg.service
    
    [Unit]
       Description=Gunicorn instance of weereg
       After=network.target
       After=mysql.service
    
    [Service]
       User=www-data
       Group=www-data
       
       WorkingDirectory=/home/username/weereg-py
       RuntimeDirectory=weereg
       ExecStart=/home/username/weereg-py/venv/bin/gunicorn --workers 3 --bind unix:/run/weereg/weereg.sock -m 007 wsgi:weereg
    
    [Install]
       WantedBy=multi-user.target
    ```

4. Reread the service files
   ```
   sudo systemctl daemon-reload
   ```
   
5. Start and enable the service

   ```shell
   sudo systemctl start weereg
   sudo systemctl enable weereg
   ```
   
The weereg application server will now be up and running, monitoring a
socket in the directory `/run/weereg`. Its log will be written to
`/var/log/weereg/weereg.log`. It will be running as user `www-data`.

### Set up a reverse proxy server

In this section, we set up nginx as a reverse proxy server to the Gunicorn
application server.

Open the file `/etc/nginx/sites-available/default` in a text editor, using root
privileges. Look inside the `server { ... }` context and identify the `location
/` context. Underneath it, add three new `location` contexts so that when you're
done, it looks something like the following.

```nginx configuration
server {

     ... # Previous content
     
     location / {
         # First attempt to serve request as file, then
         # as directory, then fall back to displaying a 404.
         try_files $uri $uri/ =404;
     }
     
     # Add the following 3 "location" sections:
     
     # 1. Support legacy registrations by rewriting them to the weereg "v1" 
     #    API. They will then get forwarded to the weereg app server.
     location /register/register.cgi {
         rewrite ^/register/register.cgi /api/v1/stations/?$args last;
     }

     # 2. Forward V1 "GET" registrations to /api/v1 to the weereg app server.
     #    Deny all other methods.
     location /api/v1/stations/ {
         limit_except GET { deny all; }
         include proxy_params;
         proxy_pass http://unix:/run/weereg/weereg.sock;
     }

     # 3. Forward all V2 API requests on to the app server.
     location /api/v2 {
         include proxy_params;
         proxy_pass http://unix:/run/weereg/weereg.sock;
     }
     
     ...
}
```

Here's what the three new sections mean:

1. If a registration comes in to `/register/register.cgi/?...`,
   which is the old Perl-based station registry API, rewrite it so that it looks
   like `/api/v1/stations/?...`.

2. If a station registry comes in to the weereg v1 registry API, perhaps as a
   result of the rewrite rule above, send it on to our Gunicorn-hosted
   application server. Deny all other HTTP methods (such as `POST`).

3. If a request comes in to the v2 API, forward it on to the application server.
   For example, if a request comes in to `/api/v2/stations`, it will be 
   forwarded.

When you're done, restart the nginx server.

```
sudo systemctl restart nginx
```

# V1 (Legacy) API

## Register a station 

This is to support the legacy station registry, which uses an HTTP GET
method to post to the database. 

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

| *Status* | *Meaning*                                              |
|:---------|:-------------------------------------------------------|
| `200`    | Message bodies with errors start with the word `FAIL`. |
| `429`    | Posting too frequently                                 |

**Errors**

If the post is not successful, the message body will start with the word `FAIL`.
The rest of the body will say why.

**Examples**

Post information about a station. Note the response code of `200`.

```shell
$ curl -i --silent -X GET 'http://localhost:5000/api/v1/stations?station_url=https%3A%2F%2Facme.com%2Fweather&description=Test+of+4.10.2&latitude=45.0000&longitude=-122.0000&station_type=Vantage&station_model=Vantage+Pro2&python_info=3.10.5&platform_info=Linux-5.15.0-60-generic-x86_64-with-glibc2.35&config_path=%2Fhome%2Fweewx%2Fweewx.conf&entry_path=%2Fhome%2Fweewx%2Fbin%2Fweewxd&weewx_info=4.10.2'
HTTP/1.1 200 OK
Server: Werkzeug/3.0.2 Python/3.8.10
Date: Tue, 09 Apr 2024 00:33:34 GMT
Content-Type: text/html; charset=utf-8
Content-Length: 2
Connection: close
```

Do it again immediately. By default, the app limits posts to once every 23
hours. If you exceed this, it returns an error code of `429`.

```shell
$ curl -i --silent -X GET 'http://localhost:5000/api/v1/stations?station_url=https%3A%2F%2Facme.com%2Fweather&description=Test+of+4.10.2&latitude=45.0000&longitude=-122.0000&station_type=Vantage&station_model=Vantage+Pro2&python_info=3.10.5&platform_info=Linux-5.15.0-60-generic-x86_64-with-glibc2.35&config_path=%2Fhome%2Fweewx%2Fweewx.conf&entry_path=%2Fhome%2Fweewx%2Fbin%2Fweewxd&weewx_info=4.10.2'
HTTP/1.1 429 TOO MANY REQUESTS
Server: Werkzeug/3.0.2 Python/3.8.10
Date: Tue, 09 Apr 2024 00:34:11 GMT
Content-Type: text/html; charset=utf-8
Content-Length: 32
Connection: close

FAIL. Registering too frequently
```

This time leave out the required parameter `station_url`. Note that an HTTP code
of `200` is still returned, but the first word in the message body is `FAIL`.
The rest of the body will tell why.

``` shell
$ curl -i --silent -X GET 'http://localhost:5000/api/v1/stations?latitude=45.0000&longitude=-122.0000&station_type=Vantage&station_model=Vantage+Pro'
HTTP/1.1 200 OK
Server: Werkzeug/3.0.2 Python/3.8.10
Date: Tue, 09 Apr 2024 00:36:03 GMT
Content-Type: text/html; charset=utf-8
Content-Length: 35
Connection: close

FAIL. Missing parameter station_url
```


# V2 API

## Register a station 

This is the more modern method of using an HTTP POST method to register a
station.

```
POST /api/v2/stations
```

**Parameters**

None

**JSON input**

The body of the post should include a JSON structure with the station
registry information as a dictionary. It must include a key `station_url`.

**Response codes**

| *Status* | *Meaning*                                           |
|:---------|:----------------------------------------------------|
| `200`    | Success                                             |
| `429`    | Posting too frequently                              |


**Errors**

If the post is not successful, the message body will start with the word `FAIL`.
The rest of the body will say why.


## Get active stations

Return the latest information about stations since some time ago.

```
GET /api/v2/stations
```

**Parameters**

| *Name*    | *Type* | *Description*                                                                                                           |
|:----------|:-------|:------------------------------------------------------------------------------------------------------------------------|
| `since`   | int    | Include results since this time in unix epoch time. Optional.                                                           |
| `max_age` | int    | How old a station can be to be included. Can use [*duration notation*](#duration-notation). Default is `30d`. Optional. |
| `limit`   | int    | Maximum number of stations to return. Default is `2000`. Optional.                                                      |

NB: You can specify `since` or `max_age`, but not both.

**Response codes**

| *Status* | *Meaning*                                                              |
|:---------|:-----------------------------------------------------------------------|
| `200`    | Success                                                                |
| `400`    | Badly formed request. Perhaps a character where a number was expected? |      

If successful (`200`), the server will return the results as a JSON list of
dictionaries, sorted in ascending order of `last_seen`.

**Examples**

Request stations since 90 days ago, returning only the first 4.

```shell
$ curl -i --silent -X GET 'http://127.0.0.1:5000/api/v2/stations?max_age=90d&limit=4'
HTTP/1.1 200 OK
Server: Werkzeug/3.0.2 Python/3.8.10
Date: Tue, 09 Apr 2024 00:41:33 GMT
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

## Get statistics

Returns information on how many stations had a certain property as a function of
time. For example, how Python usage varied over time.

```
GET /api/v2/stats/<info_type>
```

**Path parameters**

| *Name*      | *Type* | *Description*                                                                                                                                                      |
|:------------|:-------|:-------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `info_type` | str    | The type of information desired. Must be one of `station_type`, `station_model`, `weewx_info`, `python_info`,<br/>`platform_info`, `config_path`, or `entry_path`. |


**Parameters**

| *Name*        | *Type* | *Description*                                                                                                              |
|:--------------|:-------|:---------------------------------------------------------------------------------------------------------------------------|
| `since`       | int    | Include results since this time in unix epoch time. Optional. Default is to include all time.                              |
| `max_age`     | int    | How old a station can be to be included. Can use [*duration notation*](#duration-notation). Optional. Default is all time. |
| `consolidate` | bool   | If present, consolidate `entry_path` and `config_path` entries. Default is to not consolidate.                             |

NB: You can specify `since` or `max_age`, but not both.

The `consolidate` parameter groups similar path entries together. For example,
`/home/dennis/weewx-data/weewx.conf` and `/home/joe/weewx-data/weewx.conf`
would be grouped under a wildcard: `/home/*/weewx-data/weewx.conf`.
Similarly, `/home/dennis/weewx-venv/bin/weewxd` and
`/home/joe/venv/lib/python3.7/site-packages/weewxd.py` would get grouped
together under `/home/*/weewx-venv/bin/weewxd`.

For Python and WeeWX versions, `consolidate` returns only "dot" releases. That
is, Python 3.6.0, 3.6.1, 3.6.2, etc., would all be lumped together as "3.6".
Similarly with WeeWX versions.


**Response codes**

| *Status* | *Meaning*                                                              |
|:---------|:-----------------------------------------------------------------------|
| `200`    | Success                                                                |
| `400`    | Badly formed request. Perhaps a character where a number was expected? |      

If successful (`200`), the server will return the results as a JSON dictionary,
where the key is a value for the information type, and the value is two lists.
The first list is a timeseries, the second the number of stations with that
information type.

**Examples**

Request time evolution of WeeWX versions:

```shell
curl -i --silent -X GET 'http://127.0.0.1:5000/api/v2/stats/weewx_info'
HTTP/1.1 200 OK
Server: Werkzeug/3.0.2 Python/3.8.10
Date: Mon, 15 Apr 2024 19:42:39 GMT
Content-Type: application/json
Content-Length: 170853
Connection: close

{
  "2.5.0": [
    [
      "1509174000",
      "1510387200",
      "1510992000",
      "1513411200",
      ...
    ],
    [
      1,
      1,
      1,
      5,
      ...
    ]
  ],
  [
  "2.5.1": [
    [
      "1510387200",
      "1513411200",
      "1514016000",
      "1514620800",
      ...
    ],
    [
      1,
      2,
      3,
      3,
      ...
    ]
  ],
  ...
```

## Duration notation

| *Example* | *Meaning*                     |
|:----------|:------------------------------|
| `7200`    | 7,200 seconds                 |
| `2h`      | 2 hours (7,200 seconds)       |
| `120M`    | 120 minutes (7,200 seconds)   |
| `7d`      | 7 days (604,800 seconds)      |
| `1y`      | 365 days (31,536,000 seconds) |

# License & Copyright

Copyright (c) 2024 Tom Keffer <tkeffer@gmail.com>

  See the file LICENSE.txt for your full rights.
