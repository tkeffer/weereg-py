DROP TABLE IF EXISTS stations;

CREATE TABLE weereg.stations (
  `station_url` varchar(255) NOT NULL,
  `description` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT NULL,
  `latitude` float DEFAULT NULL,
  `longitude` float DEFAULT NULL,
  `station_type` varchar(64) DEFAULT NULL,
  `station_model` varchar(128) DEFAULT NULL,
  `weewx_info` varchar(64) DEFAULT NULL,
  `python_info` varchar(64) DEFAULT NULL,
  `platform_info` varchar(128) DEFAULT NULL,
  `config_path` varchar(64) DEFAULT NULL,
  `entry_path` varchar(64) DEFAULT NULL,
  `last_addr` varchar(44) NOT NULL,
  `last_seen` int NOT NULL,
  KEY `index_station_url` (`station_url`),
  KEY `index_last_seen` (`last_seen`),
  KEY `index_ip` (`last_addr`)
) ENGINE=MyISAM DEFAULT CHARSET=latin1;
