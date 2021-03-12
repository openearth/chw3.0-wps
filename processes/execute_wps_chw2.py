import requests
from jinja2 import Environment, PackageLoader
import json

transect = json.dumps(
    {
        "type": "Feature",
        "properties": {},
        "geometry": {
            "type": "LineString",
            "coordinates": [[-75.605441, 37.562595], [-75.616183, 37.568836]],
        },
    }
)
print(transect)
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

print(response)
