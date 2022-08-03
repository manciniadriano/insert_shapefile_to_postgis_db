#!/usr/local/bin/python3.9
# encoding: utf-8

from chaintick import create_ticks
from collections import defaultdict
from itertools import chain
from osgeo import gdal, ogr
from shapely.geometry import LineString, Point
import cv2
import geopandas as gpd
import json
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
import numpy as np
import os 
import requests
import zipfile
import psycopg2
import requests
from io import BytesIO

inputshp_path = os.getcwd() + "/files/elevation.shp"   # questi due path sono diversi perchè sono contenuti nella cartella 
intrpshp_path = os.getcwd() + "/elevation_intrp.shp"
smoothshp_path = os.getcwd() + "/elevation_smooth.shp"
splitshp_path = os.getcwd() + "/elevation_split.shp"
chaintickshp_path = os.getcwd() + "/output_lines.shp"

result_txt = os.getcwd()+"/result.txt"

class NumpyEncoder(json.JSONEncoder):
    """Custom JSON encoder for numpy types, since JSON does not handle them by default"""
    def default(self, obj):
        if isinstance(obj, np.integer):
            return int(obj)
        elif isinstance(obj, np.floating):
            return float(obj)
        elif isinstance(obj, np.ndarray):
            return obj.tolist()
        return json.JSONEncoder.default(self, obj)


def split_shp(shp_path):
    '''Dissect shapefile, extract points, build dictlist of segments, create new shapefile of LineStrings having unique IDs'''
    shp_file = gpd.read_file(shp_path)
    tmp_dict = defaultdict(list)
    for coords in shp_file.geometry:  # extract coordinates from geometry of shapefile
        print(coords)
        points = np.array(coords)  # convert coordinates into array
        print(points)        
        i=0
        for _ in range(len(points)-1):
            ptA = Point(points[i])  # save ptA of segment, index i
            ptB = Point(points[i+1])  # save ptB of segment, index i+1
            distance_pts = ptB.distance(ptA)  # calculate euclidean distance between ptA and ptB
            print(ptA, ptB, distance_pts)
            lineAB = LineString([ptA, ptB])  # create LineString between two points
            print(lineAB.length)
            tmp_dict["id"].append(int(i))  # fill temporary dict, "id" col of segment
            tmp_dict["geometry"].append(lineAB)  # fill temporary dict, "geometry" col of segment
            i=i+1
    splitshp_geodf = gpd.GeoDataFrame(tmp_dict, crs=shp_file.crs)  # create GDF from temporary dict     
    #print(splitshp_geodf)
    splitshp_geodf.to_file(splitshp_path)  # save SHP converted from GDF
    return


def geojson2shp(src_path, save_path):
    '''Simply convert GeoJSON to Shapefile'''
    gdf = gpd.read_file(src_path)
    gdf.to_file(save_path)
    return


def interpolate_shp2points(shp_path, n):
    '''Interpolate input Shapefile, add 'n' predetermined number of points between extreme points'''
    shp_file = gpd.read_file(shp_path)
    #print(shp_file.__class__)
    for coords in shp_file.geometry:  # extract coordinates from geometry of shapefile
        points = np.array(coords)  # convert coordinates into array
        line = LineString(points)
        #print(line)
    distances = np.linspace(0, line.length, n)
    interpoints = [line.interpolate(distance) for distance in distances]
    new_line = LineString(interpoints)
    #print(new_line)
    tmp_dict = defaultdict(list)
    tmp_dict["geometry"].append(new_line)
    newshp_geodf = gpd.GeoDataFrame(tmp_dict, crs=shp_file.crs)
    #print(newshp_geodf)
    newshp_geodf.to_file(intrpshp_path)
    return

def chaikins_smoothing(shp_path, refinements):
    '''Smooth Shapefile with Chaikin's algorithm'''
    shp_file = gpd.read_file(shp_path)
    for coords in shp_file.geometry:
        points = np.array(coords)
    for _ in range(refinements):
        L = points.repeat(2, axis=0)
        R = np.empty_like(L)
        R[0] = L[0]
        R[2::2] = L[1:-1:2]
        R[1:-1:2] = L[2::2]
        R[-1] = L[-1]
        points = L * 0.75 + R * 0.25
    line = LineString(points)
    tmp_dict = defaultdict(list)
    tmp_dict["geometry"].append(line)
    newshp_geodf = gpd.GeoDataFrame(tmp_dict, crs=shp_file.crs)
    newshp_geodf.to_file(smoothshp_path)
    return

def insert_to_db(idCantiere):
    #connect to the db
    con = psycopg2.connect(
        database="prova_gis",
        user="postgres",
        password="sinergia",
        host="172.17.0.2",
        port="5432"
    )
    print("Connected...")    
    cursor = con.cursor()
    print("Cursor obtained...")    
    srcFile = chaintickshp_path
    #shp = ogr.Open(chaintickshp_path) 
    shapefile = ogr.Open(srcFile) 
    layer = shapefile.GetLayer(0)    
    for i in range(layer.GetFeatureCount()):  
        feature = layer.GetFeature(i)  
        id = feature.GetField("ID")
        chainage = feature.GetField("CHAINAGE")
        wkt = feature.GetGeometryRef().ExportToWkt()
        cursor.execute("INSERT INTO \"Segmenti\" (id,chainage,id_cantiere,id_rev,geom) " +
                       "VALUES (%s,%s,%s,%s, ST_GeometryFromText(%s, " +"0))", 
                        (id,chainage,idCantiere,1,wkt))
        #record = record+str(wkt)+"-"
        # Open a file with access mode 'a'
        # with open(result_txt, "a") as file_object:
        #     # Append 'hello' at the end of file
        #     file_object.write("id: "+str(id)+" chainage: "+str(chainage)+" wkt: "+str(wkt)+"\n")
    con.commit()
    cursor.close()
    con.close()
    return

# funzione per download dello zip e estrazione classica del suo contenuto nella cartella corrente
def download_zip (url):
    print('Downloading started')

    # Split URL to get the file name
    filename = url.split('/')[-1]

    # Downloading the file by sending the request to the URL
    req = requests.get(url)
    print('Downloading Completed')

    # extracting the zip file contents
    z = zipfile.ZipFile(BytesIO(req.content))
    z.extractall(os.getcwd())

def run (url, distance, id):

    # richiamo la funzione che scarica e unzippa il shapefile
    download_zip(url)    # <-- problemi qui
    
    # una volta ricavati i file dello shapefile elaboro il shapefile con la singola linea
    # in una linea segmentata in linee
    #inserire altri elevation, eccetto cpg+
    interpolate_shp2points(inputshp_path, 200)
    chaikins_smoothing(intrpshp_path, 5)   
    create_ticks(smoothshp_path,distance, 7)

    # invoco la funzione che inserisce i segmenti nel db
    insert_to_db(id)
    return
