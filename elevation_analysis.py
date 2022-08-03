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

# inputdsm_path = os.getcwd() + "/files/DSM.gtif"        # che viene estratta dallo zip
# rastshpdsm_path = os.getcwd() + "/DSM_rastshp.gtif"
inputshp_path = os.getcwd() + "/files/elevation.shp"   # questi due path sono diversi perchè sono contenuti nella cartella 
intrpshp_path = os.getcwd() + "/elevation_intrp.shp"
smoothshp_path = os.getcwd() + "/elevation_smooth.shp"
splitshp_path = os.getcwd() + "/elevation_split.shp"
chaintickshp_path = os.getcwd() + "/output_lines.shp"
# jsonfull_path = os.getcwd() + "/ElevationValues_full.json"
# jsontrain_path = os.getcwd() + "/ElevationValues_training.json"

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


# def rasterize_shp2dsm(indsm_path, output_path, shp_path):
#     '''Rasterize Shapefile of perpendicular ticks to a NODATA DSM'''
#     shpds = ogr.Open(shp_path)
#     shpds_layer = shpds.GetLayer()
#     orig_ds = gdal.Open(indsm_path)
#     target_ds = gdal.GetDriverByName("GTiff").Create(output_path, xsize=orig_ds.RasterXSize, ysize=orig_ds.RasterYSize, 
#                                                   bands=1, eType=gdal.GDT_Float32)
#     target_ds.SetGeoTransform(orig_ds.GetGeoTransform())
#     target_ds.SetProjection(orig_ds.GetProjection())
#     target_ds.GetRasterBand(1).SetNoDataValue(np.nan) # set default nodata value
#     void_arr = np.array([[np.nan]], dtype = np.float32) # create nodata array to be used for filling the new raster
#     target_ds.GetRasterBand(1).WriteArray(void_arr) # overwrite original raster entirely with nodata
#     gdal.RasterizeLayer(target_ds, [1], shpds_layer, options = ["ATTRIBUTE=ID"])
#     target_ds.FlushCache() # clear the buffer, and ensure file is written

#     prova_ds = gdal.GetDriverByName("GTiff").Create(prova_path, xsize=orig_ds.RasterXSize, ysize=orig_ds.RasterYSize, 
#                                                   bands=1, eType=gdal.GDT_Float32,
#                                                   options=["TILED=YES",
#                                                   "COMPRESS=LZW",
#                                                   "INTERLEAVE=BAND"])
#     prova_ds.GetRasterBand(1).SetNoDataValue(np.nan) # set default nodata value
#     return


# def extract_rastcoords(rastdsm_path):
#     '''Save all extracted coordinates of rasterized segments in order of gray values'''
#     pxdict = defaultdict(list) # as of Python version 3.7, dictionaries are ordered
#     img = cv2.imread(rastdsm_path, -1) # returns ndarray, y-x order
#     yx_valid_coords = np.column_stack(np.where(img >= int(np.nanmin(img))))
    
#     #print(int(np.nanmax(img)))
#     #for gray in range(4403, 4903):
#     for gray in range(int(np.nanmin(img)), int(np.nanmax(img)+1)):  # max range we need is given by int(np.nanmax(img)+1)    
#         yx_gray_indices = np.column_stack(np.where(img[yx_valid_coords[:,0],yx_valid_coords[:,1]] == gray)) # create column-stacked ndarray of yx indices
#         yx_gray_coords = np.column_stack([yx_valid_coords[yx_gray_indices,0],yx_valid_coords[yx_gray_indices,1]]) # create column-stacked ndarray of yx coords
#         #print(yx_gray_coords.shape) # some shapes are different, less points, could be a problem
#         tuplist = list(map(tuple, yx_gray_coords)) # convert ndarray to a list of tuples
#         #print(tuplist)
#         pxdict[gray].append(tuplist)  # fill dict, key is "grey band/id" of rasterized segment, value is array of all yx coordinates (in tuples)
#     #print(pxdict)
#     return pxdict


# def save_dsmprofiles(indsm_path, rastdsm_path):
#     '''Save all obtained profile values in a dictionary'''
#     pxdict = extract_rastcoords(rastdsm_path)
#     img = cv2.imread(indsm_path, -1) # returns ndarray, y-x order
#     img_smooth = cv2.GaussianBlur(img,(27,27),0) # blur (Gaussian) input DSM in order to remove noise
#     #print(type(img))
#     #print(img.shape[0], img.shape[1])
#     #graydict = defaultdict(list)
#     graydict_smooth = defaultdict(list)
#     for key in pxdict:
#         valuelist = pxdict[key]
#         pixels_of_interest = [val for sublist in valuelist for val in sublist] # flatten list of lists to a single list containing values
#         #print(pixels_of_interest)
#         indices_to_read = tuple(zip(*pixels_of_interest))  # make advanced index tuple (groups all y and x coordinates into two separate tuples)
#         #print(indices_to_read)
#         #gray_values = img[indices_to_read]  # read gray values on original DSM
#         gray_values_smooth = img_smooth[indices_to_read]  # read gray values on smoothed DSM
#         #print(gray_values)
#         #print(type(gray_values_smooth))
#         if any(value == -9999 for value in gray_values_smooth):  # if "ValueError: The truth value of an array is ambiguous", increase create_ticks distance value from 0.1 to higher
#             print("NAN values found. Double check input data. Ending code execution.")   
#             exit()
#         #graydict[key].append(gray_values)
#         graydict_smooth[key].append(gray_values_smooth) 
#     #print(graydict)
#     #print(graydict_smooth)
#     return graydict_smooth


# def export_dsmprofiles_dict(indsm_path, rastdsm_path, json_fpath, json_tpath):
#     '''Manually classify terrain profiles and export them to JSON files'''
#     valuedict = save_dsmprofiles(indsm_path, rastdsm_path)
#     new_key = 'Status' # generic status label, key value will be 0 if not excavated, 1 if excavated
#     fdigdict = {new_key: 0}
#     tdigdict = {new_key: 1}
#     fulldict = defaultdict(list)
#     for key in valuedict:
#         valuelist = valuedict[key]
#         fulldict[key].append(valuelist)
#         merged_range = chain(range(0,745), range(4172,5371)) # define which elevation profiles must be set to 1
#         fulldict[key].append(tdigdict) if key in merged_range else fulldict[key].append(fdigdict)
#     #print(new_valuedict)
#     with open(json_fpath, 'w') as fpf:
#         json.dump(fulldict, fpf, cls=NumpyEncoder)
#     subdict = {x: fulldict[x] for x in range(int(len(fulldict)/2),int(len(fulldict)+1)) if x in fulldict}    
#     with open(json_tpath, 'w') as fps:
#         json.dump(subdict, fps, cls=NumpyEncoder)
#     return
    

# def plot_dsmprofiles(indsm_path, rastdsm_path):
#     '''Plot all profile values obtained from DSM'''
#     valuedict = save_dsmprofiles(indsm_path, rastdsm_path)
#     fig, ax = plt.subplots(nrows=1, ncols=1)
#     for item in valuedict:
#         vallist = valuedict[item]
#         vals_of_interest = [val for sublist in vallist for val in sublist] # flatten list of lists to a single list containing values
#         #vals_of_interest -= min(vals_of_interest) # subtract minimum from list, so that the plot is normalized (from 0 to max elevation)
#         vals_of_interest = vals_of_interest-np.min(vals_of_interest)
#         plt.plot(vals_of_interest*100) # from meters to centimeters
#         ax.set_xlabel('Length [cm]')
#         ax.set_ylabel('Elevation [cm]')
#         ticks = ticker.FuncFormatter(lambda x, pos: '{0:g}'.format(x*0.5*10)) # arbitrary correction, num_points*pixel_size*10
#         ax.xaxis.set_major_formatter(ticks)
#         ax.set_title('Terrain Profile')
#         fig.tight_layout()
#     plt.show()
#     return

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
    # rasterize_shp2dsm(inputdsm_path, rastshpdsm_path, chaintickshp_path)
    #extract_rastcoords(rastshpdsm_path)
    #save_dsmprofiles(inputdsm_path, rastshpdsm_path)
    #plot_dsmprofiles(inputdsm_path, rastshpdsm_path)
    # export_dsmprofiles_dict(inputdsm_path, rastshpdsm_path, jsonfull_path, jsontrain_path)
