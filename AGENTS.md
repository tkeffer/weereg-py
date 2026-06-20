# Agent Context: weereg

This document provides essential context for AI agents working on the `weereg` project.

## Project Overview
`weereg` is a Flask-based station registry for the WeeWX weather station software. It allows weather stations to register themselves and provides APIs to retrieve active stations and usage statistics.

## Technology Stack
- **Language**: Python 3.10+
- **Framework**: Flask 3.x
- **Database**: MySQL (using PyMySQL)
- **Application Server**: Gunicorn
- **Reverse Proxy**: Nginx
- **Build System**: setuptools (pyproject.toml)

## Core Architecture
The project follows a standard Flask application factory pattern.

### Key Components
- `weereg/__init__.py`: Contains the `create_app` factory, route definitions for API V1 and V2, station registration logic (including validation and sanitation), and a background threading mechanism for station screenshots.
- `weereg/db.py`: Handles database connections and queries. It manages the `stations` table and provides functions for inserting station data, retrieving recent stations, and calculating statistics.
- `weereg/stations_schema.sql`: Defines the MySQL schema for the `stations` table (using MyISAM engine).
- `wsgi.py`: The entry point for WSGI servers like Gunicorn.
- `config-sample.py`: A template for the project configuration. Users should copy this to `config.py`.

## Database Schema
The primary table is `stations` in the `weereg` database.
- **Table Engine**: MyISAM
- **Key Columns**:
    - `station_url`: Unique identifier (VARCHAR 255) for the station.
    - `latitude`, `longitude`: Float coordinates of the station.
    - `last_seen`: Unix timestamp of the last time a station registered.
    - `last_addr`: IP address of the reporting station (supports IPv6).
    - `weewx_info`, `python_info`, `platform_info`: Version and environment metadata.
    - `config_path`, `entry_path`: Internal paths (not exposed via public API).

## API Versions
### V1 (Legacy)
- **Endpoint**: `GET /api/v1/stations`
- **Method**: GET (used for registration via query parameters).
- **Purpose**: Backward compatibility with older WeeWX versions and legacy Perl-based registries.

### V2 (Modern)
- **Endpoint**: `/api/v2/stations`
- **Methods**:
    - `POST`: Modern registration using JSON body.
    - `GET`: Retrieve active stations (supports filtering via `since`, `max_age`, `limit`, and `slim`).
- **Endpoint**: `GET /api/v2/stats/<info_type>`
- **Purpose**: Usage statistics for various properties (e.g., Python versions, hardware types, and `installer_info`). Supports `consolidate` parameter for grouping similar versions.

## Key Workflows
### Station Registration
1. **Request**: Received via V1 (GET) or V2 (POST).
2. **Sanitation**: `sanitize_station` removes control characters and double quotes.
3. **Validation**: `check_station` verifies URL format, coordinate ranges, and ensures mandatory fields (like `station_url`) are present.
4. **Rate Limiting**: Checks if the station has reported in the last 23 hours.
5. **Persistence**: Updates existing or inserts new record into the `stations` table.
6. **Screenshot**: If it's a new station, a background thread is spawned to run `/var/www/html/register/capture-one.sh` (external script) to capture the station's website.

## Development & Operations
- **Initialization**: Run `python3 -m flask --app weereg init-db` to (re)initialize the database.
- **Configuration**: `config.py` is required and must contain MySQL credentials and other settings.
- **Logging**: Uses standard Python logging, configured via `LOGGING_CONFIG` in `config.py`.
- **Testing**: No formal test suite is currently present in the repository; manual verification via `curl` is commonly used.

## Important Constraints & Notes
- **Thread Safety**: Screenshots are handled in a separate thread. Ensure any modifications to the app factory or database connection handling don't break this.
- **Database Connection**: Uses a global `g.db` object managed by Flask's application context.
- **Deployment**: Typically runs behind Nginx and Gunicorn. Systemd unit files and Nginx configs are documented in `README.md`.
- **TODOs**:
    - Improve performance of statistics queries.
    - Implement a blacklist for bad stations.
    - Canonicalize `station_url`.
