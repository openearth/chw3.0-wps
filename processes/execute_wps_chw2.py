import os
from sqlalchemy import create_engine

import requests
from jinja2 import Environment, PackageLoader
import json

def gettransectdata(x1,y1,x2,y2):
    transect = json.dumps(
        {
            "type": "Feature",
            "properties": {},
            "geometry": {
                "type": "LineString",
                #"coordinates": [[-75.605441, 37.562595], [-75.616183, 37.568836]],
                "coordinates": [[x1, y1], [x2, y2]],
            },
        }
    )
    #print(transect)
    env = Environment(loader=PackageLoader("execute_wps_chw2", "templates"))
    template = env.get_template("template_request_chw2.xml")
    xml_request = template.render(transect=transect)
    
    
    headers = {"Content-Type": "application/xml"}
    
    response = json.loads(
        requests.post(
            "https://coastalhazardwheel.avi.deltares.nl/wps",
            data=xml_request,
            headers=headers,
        ).text
    )

    return response

# create connection to the database
# credential file

cf = r'D:\projecten\datamanagement\global\CHW\tools\dpcconnection.txt'
f = open(cf)
engine = create_engine(f.read(), echo=False)
f.close()

# prepare a table
stmt = 'drop table if exists chw.cl1000hazard'
engine.execute(stmt)

stmt = 'create table chw.cl1000hazard (gid bigint,coast_env character varying(5))'
engine.execute(stmt)

# create list of id's with points from the osm_segment1000m
stmt = """select st_x(st_centroid(geom)) as x1,st_y(st_centroid(geom)) as y1,
       st_x(st_centroid(st_offsetcurve(geom,0.01))) as x2,
	   st_y(st_centroid(st_offsetcurve(geom,0.01))) as y2,
		gid from coast.osm_segment1000m"""
sp = engine.execute(stmt)
for i in sp:
    for j in range(3):
        if str(i[j]) == 'None':
            stmt = """insert into chw.cl1000hazard (gid,coast_env) VALUES ({id},'{ce}')""".format(id=i[4],ce='error')
        else:
            try:
                response = gettransectdata(i[0], i[1], i[2], i[3])
                stmt = """insert into chw.cl1000hazard (gid,coast_env) VALUES ({id},'{ce}')""".format(id=i[4],ce=response[0]['info'][1]['info']['code'])
            except:
                print('oeps, boo boo or not? Check the query')
                print(stmt)
        engine.execute(stmt)


#finally the following query creates a new table where lines and hazards are combined using the gid and the coast_env
stmt = """dropt table if exists chw.hazardgeom"""
engine.execute(stmt)

stmt = """create table chw.hazardgeom as
select c.gid,c.geom,ecosystem_disruption, gradual_inundation,salt_water_intrusion,erosion, flooding 
from coast.osm_segment1000m c
join chw.cl1000hazard h on h.gid = c.gid
join chw.decision_wheel chw on chw.code = h.coast_env"""
engine.execute(stmt)
engine.dispose()
