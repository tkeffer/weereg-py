1. Implement a blacklist to filter out bad stations. It would consist of keys,
such as `station_url`, and values to be filtered out.

2. Put `station_url` in a canonical form. This would require either rebuilding the
database, or upgrading the database.

3. Occasionally scan the capture database, and try again all stations that have a
placeholder image.