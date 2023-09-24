weereg change history
--------------------

### 1.5.0 23-sep-2023

Kick off screen capture in a separate thread with a timeout. This avoids
zombie processes.


### 1.4.1 7-aug-2023

Change SQL column `last_addr` to 44 characters to accommodate IPv6.
Record `last_addr` in log.


### 1.4.0 10-apr-2023

New stations kick off a screen capture.


### 1.3.2 24-mar-2023

Change how often a client can post from once an hour, to once every 23 hours.


### 1.3.1 04-mar-2023

Filter out double quotes.


### 1.3.0 04-mar-2023

Install using a `requirements.txt` file.


### 1.2.1 04-mar-2023

Log stations that have not passed validation and why.


### 1.2.0 04-mar-2023

Check latitude and longitude ranges.
Validate `station_url`.


### 1.1.0 03-mar-2023

Perform some rudimentary quality control.


### 1.0.0 03-mar-2023

Initial version

