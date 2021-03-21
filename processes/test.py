from db_utils import DB


host = "openearth-coastal-hazard-wheel-db.avi.directory.intra"
user = "oet_data"
password = "KOO0nyMZGe6ogpLxGFHs"
database = "oet_data"
port = "5432"

db = DB(user, password, host, database)


sea_point = "POINT(-96.496556088961 71.8637471632084)"  # wkt


print(db.point_in_landpolygon(sea_point))
db.close_db_connection()