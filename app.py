import sys
import json
from elevation_analysis import run

def handler(event, context):
    run(event["url"], float(event["distance"]), event["cantiere"])
    return{
        'StatusCode': 200,
        'body': json.dumps("url :" + event["url"] + " distance: " + event["distance"] + " cantiere: " + event["cantiere"])
    }
    #return "url :" + event["url"] + " distance: " + event["distance"] + " cantiere: " + event["cantiere"]