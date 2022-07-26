#!/usr/local/bin/python3.9
# encoding: utf-8

from osgeo import ogr
from shapely.geometry import LineString, Point
from shapely import wkt
import math

## http://wikicode.wikidot.com/get-angle-of-line-between-two-points
## angle between two points
def getAngle(pt1, pt2):
    x_diff = pt2.x - pt1.x
    y_diff = pt2.y - pt1.y
    return math.degrees(math.atan2(y_diff, x_diff))

## start and end points of chainage tick
## get the first end point of a tick
def getPoint1(pt, bearing, dist):
    angle = bearing + 90
    bearing = math.radians(angle)
    x = pt.x + dist * math.cos(bearing)
    y = pt.y + dist * math.sin(bearing)
    return Point(x, y)
## get the second end point of a tick
def getPoint2(pt, bearing, dist):
    bearing = math.radians(bearing)
    x = pt.x + dist * math.cos(bearing)
    y = pt.y + dist * math.sin(bearing)
    return Point(x, y)


def create_ticks(shp_path,distance,tick_length):

    ## set the driver for the data
    driver = ogr.GetDriverByName("ESRI Shapefile")
    ## open the Shapefile in write mode (1)
    ds = driver.Open(shp_path, 1)

    inputshp = ogr.Open(shp_path)
    lyr = inputshp.GetLayer()

    ## linear feature class
    input_lyr_name = "output"

    ## distance between points
    #distance = 1
    ## the length of each tick
    #tick_length = 5

    ## output tick line fc name
    #output_lns = "{0}_{1}m_lines".format(input_lyr_name, distance)
    output_lns = "{0}_lines".format(input_lyr_name)

    ## list to hold all the point coords
    list_points = []

    ## reference the layer using the layers name
    if input_lyr_name in [ds.GetLayerByIndex(lyr_name).GetName() for lyr_name in range(ds.GetLayerCount())]:
        lyr = ds.GetLayerByName(input_lyr_name)
        print ("{0} found in {1}".format(input_lyr_name, shp_path))

    ## if the output already exists then delete it
    if output_lns in [ds.GetLayerByIndex(lyr_name).GetName() for lyr_name in range(ds.GetLayerCount())]:
        ds.DeleteLayer(output_lns)
        print ("Deleting: {0}".format(output_lns))

    ## create a new line layer with the same spatial ref as lyr
    out_ln_lyr = ds.CreateLayer(output_lns, lyr.GetSpatialRef(), ogr.wkbLineString)

    ## distance/chainage attribute
    chainage_fld = ogr.FieldDefn("CHAINAGE", ogr.OFTReal)
    id_fld = ogr.FieldDefn("ID", ogr.OFTInteger)
    out_ln_lyr.CreateField(chainage_fld)
    out_ln_lyr.CreateField(id_fld)
    ## check the geometry is a line
    first_feat = lyr.GetFeature(0)

    ## accessing linear feature classes using FileGDB driver always returns a MultiLinestring
    if first_feat.geometry().GetGeometryName() in ["LINESTRING", "MULTILINESTRING"]:
        for ln in lyr:
            ## list to hold all the point coords
            list_points = []
            ## set the current distance to place the point
            current_dist = distance
            ## get the geometry of the line as wkt
            line_geom = ln.geometry().ExportToWkt()
            ## make shapely LineString object
            #shapely_line = MultiLineString(wkt.loads(line_geom))
            shapely_line = LineString(wkt.loads(line_geom))
            #print(shapely_line)
            ## get the total length of the line
            line_length = shapely_line.length
            #print(line_length)
            ## append the starting coordinate to the list
            #list_points.append(Point(list(shapely_line[0].coords)[0]))
            list_points.append(Point(list(shapely_line.coords)[0]))
            ## https://nathanw.net/2012/08/05/generating-chainage-distance-nodes-in-qgis/
            ## while the current cumulative distance is less than the total length of the line
            while current_dist < line_length:
                ## use interpolate and increase the current distance
                list_points.append(shapely_line.interpolate(current_dist))
                current_dist += distance
            ## append end coordinate to the list
            #list_points.append(Point(list(shapely_line[0].coords)[-1]))
            list_points.append(Point(list(shapely_line.coords)[-1]))

            ## add lines to the layer
            ## this can probably be cleaned up better
            ## but it works and is fast!
            for num, pt in enumerate(list_points, 1):
                ## start chainage 0
                '''if num == 1:
                    angle = getAngle(pt, list_points[num])
                    line_end_1 = getPoint1(pt, angle, tick_length/2)
                    angle = getAngle(line_end_1, pt)
                    line_end_2 = getPoint2(line_end_1, angle, tick_length)
                    tick = LineString([(line_end_1.x, line_end_1.y), (line_end_2.x, line_end_2.y)])
                    feat_dfn_ln = out_ln_lyr.GetLayerDefn()
                    feat_ln = ogr.Feature(feat_dfn_ln)
                    feat_ln.SetGeometry(ogr.CreateGeometryFromWkt(tick.wkt))
                    feat_ln.SetField("CHAINAGE", 0)
                    feat_ln.SetField("ID", 0)
                    out_ln_lyr.CreateFeature(feat_ln)'''

                ## everything in between
                if num < len(list_points) - 1:
                    angle = getAngle(pt, list_points[num])
                    line_end_1 = getPoint1(list_points[num], angle, tick_length/2)
                    angle = getAngle(line_end_1, list_points[num])
                    line_end_2 = getPoint2(line_end_1, angle, tick_length)
                    tick = LineString([(line_end_1.x, line_end_1.y), (line_end_2.x, line_end_2.y)])
                    feat_dfn_ln = out_ln_lyr.GetLayerDefn()
                    feat_ln = ogr.Feature(feat_dfn_ln)
                    feat_ln.SetGeometry(ogr.CreateGeometryFromWkt(tick.wkt))
                    feat_ln.SetField("CHAINAGE", distance * num)
                    feat_ln.SetField("ID", num)
                    out_ln_lyr.CreateFeature(feat_ln)

                ## end chainage
                '''if num == len(list_points):
                    angle = getAngle(list_points[num - 2], pt)
                    line_end_1 = getPoint1(pt, angle, tick_length/2)
                    angle = getAngle(line_end_1, pt)
                    line_end_2 = getPoint2(line_end_1, angle, tick_length)
                    tick = LineString([(line_end_1.x, line_end_1.y), (line_end_2.x, line_end_2.y)])
                    feat_dfn_ln = out_ln_lyr.GetLayerDefn()
                    feat_ln = ogr.Feature(feat_dfn_ln)
                    feat_ln.SetGeometry(ogr.CreateGeometryFromWkt(tick.wkt))
                    feat_ln.SetField("CHAINAGE", int(line_length))
                    feat_ln.SetField("ID", num-1)
                    out_ln_lyr.CreateFeature(feat_ln)'''

    del ds            