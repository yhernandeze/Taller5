-- Base para datos operacionales (separada del backend de MLflow)
CREATE DATABASE IF NOT EXISTS datasets_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- Asegura la cuenta de aplicación (MySQL 8 no crea usuarios con GRANT)
CREATE USER IF NOT EXISTS '${MYSQL_USER}'@'%' IDENTIFIED BY '${MYSQL_PASSWORD}';

-- Concede privilegios completos sobre la nueva DB
GRANT ALL PRIVILEGES ON datasets_db.* TO '${MYSQL_USER}'@'%';
FLUSH PRIVILEGES;

-- Tablas RAW y CURATED
CREATE TABLE IF NOT EXISTS datasets_db.forest_raw (
  id BIGINT AUTO_INCREMENT PRIMARY KEY,
  Elevation DOUBLE,
  Aspect DOUBLE,
  Slope DOUBLE,
  Horizontal_Distance_To_Hydrology DOUBLE,
  Vertical_Distance_To_Hydrology DOUBLE,
  Horizontal_Distance_To_Roadways DOUBLE,
  Hillshade_9am INT,
  Hillshade_Noon INT,
  Hillshade_3pm INT,
  Horizontal_Distance_To_Fire_Points DOUBLE,
  Wilderness_Area VARCHAR(64),
  Soil_Type VARCHAR(64),
  Cover_Type INT,
  batch INT,
  ingested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS datasets_db.forest_curated (
  id BIGINT AUTO_INCREMENT PRIMARY KEY,
  Elevation DOUBLE,
  Aspect DOUBLE,
  Slope DOUBLE,
  Horizontal_Distance_To_Hydrology DOUBLE,
  Vertical_Distance_To_Hydrology DOUBLE,
  Horizontal_Distance_To_Roadways DOUBLE,
  Hillshade_9am INT,
  Hillshade_Noon INT,
  Hillshade_3pm INT,
  Horizontal_Distance_To_Fire_Points DOUBLE,
  Wilderness_Area VARCHAR(64),
  Soil_Type VARCHAR(64),
  Cover_Type INT,
  batch INT,
  processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
