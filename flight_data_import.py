## make sure to be in 'flight_venv' virtual environment

import pandas as pd
from sqlalchemy import create_engine, text
import os

# Connection details - replace with your own
DB_USER = 'cooperpenniman'
DB_PASSWORD = ''
DB_HOST = 'localhost'  # or your cloud database host
DB_PORT = '5432'
DB_NAME = 'nycflights'

# Create connection string
conn_string = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
engine = create_engine(conn_string)

# Local paths for the nycflights13 data CSV files
data_dir = os.path.join(os.getcwd(), 'nycflights_data')
tables = {
    'airlines': os.path.join(data_dir, 'airlines.csv'),
    'airports': os.path.join(data_dir, 'airports.csv'),
    'planes': os.path.join(data_dir, 'planes.csv'),
    'weather': os.path.join(data_dir, 'weather.csv'),
    'flights': os.path.join(data_dir, 'flights.csv')
}

# Drop tables in reverse dependency order
print("Dropping tables if they exist...")
drop_order = ['flights', 'weather', 'planes', 'airports', 'airlines']
with engine.begin() as conn:
    for table in drop_order:
        conn.execute(text(f"DROP TABLE IF EXISTS {table} CASCADE;"))

# Load data into tables in the correct order
load_order = ['airlines', 'airports', 'planes', 'weather', 'flights']
for table_name in load_order:
    path = tables[table_name]
    print(f"Loading {table_name} data from {path} ...")
    data = pd.read_csv(path)
    if 'time_hour' in data.columns:
        data['time_hour'] = pd.to_datetime(data['time_hour'])
    data.to_sql(table_name, engine, if_exists='replace', index=False)

print("Data loading complete!\n")

# --- Verification Queries ---
from sqlalchemy import text

with engine.connect() as conn:
    print("Row counts for each table:")
    result = conn.execute(text('''
        SELECT 'airlines' AS table, COUNT(*) FROM airlines
        UNION ALL
        SELECT 'airports', COUNT(*) FROM airports
        UNION ALL
        SELECT 'planes', COUNT(*) FROM planes
        UNION ALL
        SELECT 'weather', COUNT(*) FROM weather
        UNION ALL
        SELECT 'flights', COUNT(*) FROM flights;
    '''))
    for row in result:
        print(row)

    print("\nFirst 5 rows from airlines:")
    for row in conn.execute(text('SELECT * FROM airlines LIMIT 5;')):
        print(row)

    print("\nFirst 5 rows from airports:")
    for row in conn.execute(text('SELECT * FROM airports LIMIT 5;')):
        print(row)

    print("\nFirst 5 rows from planes:")
    for row in conn.execute(text('SELECT * FROM planes LIMIT 5;')):
        print(row)

    print("\nFirst 5 rows from weather:")
    for row in conn.execute(text('SELECT * FROM weather LIMIT 5;')):
        print(row)

    print("\nFirst 5 rows from flights:")
    for row in conn.execute(text('SELECT * FROM flights LIMIT 5;')):
        print(row)

    print("\nCarriers in flights not in airlines (should be zero rows):")
    for row in conn.execute(text('''
        SELECT DISTINCT carrier
        FROM flights
        WHERE carrier NOT IN (SELECT carrier FROM airlines);
    ''')):
        print(row)

    print("\nFlights with missing tailnum:")
    for row in conn.execute(text('SELECT COUNT(*) FROM flights WHERE tailnum IS NULL OR tailnum = \'\';')):
        print(row)

    print("\nFlights without matching weather data:")
    for row in conn.execute(text('''
        SELECT COUNT(*) AS flights_without_weather
        FROM flights f
        LEFT JOIN weather w
          ON f.origin = w.origin AND f.time_hour = w.time_hour
        WHERE w.origin IS NULL;
    ''')):
        print(row)