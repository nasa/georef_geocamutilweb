import numpy as np
import urllib2
import logging
from numpy import linalg as LA

import PIL.Image
try:
    from cStringIO import StringIO
except ImportError:
    from StringIO import StringIO

from geocamTiePoint import settings

from geocamUtil.geom3 import Vector3, Point3, Ray3
from geocamUtil.sphere import Sphere
from geocamUtil.imageInfo import getIssImageInfo
from geocamUtil.geomath import EARTH_RADIUS_METERS, transformLonLatAltToEcef, transformEcefToLonLatAlt

#####################################################
# Utility functions for image registration in 
# geocamspace geoRef ground tool.
#####################################################


def degreesToRadians(degrees):
    return degrees * (np.pi / 180.)


def pixelToVector(opticalCenter, focalLength, pixelCoord):
    """
    For transforming image 2d pixel coordinates (x,y) to
    a normalized direction vector in camera coordinates.
    
    Assumptions: 
    - optical center is center of the image
    - focal length in x is equal to focal length in y
    """
    x = (pixelCoord[0] - opticalCenter[0]) / focalLength[0]
    y = (pixelCoord[1] - opticalCenter[1]) / focalLength[1]
    z = 1
    dirVec = Vector3(x,y,z)
    normDir = dirVec.norm()
    return normDir


def rotMatrixFromCameraToEcef(longitude, camPoseEcef):
    """
    Given the camera pose in ecef and camera longitude, provides rotation matrix for 
    transforming a vector from camera frame to ecef frame.
    """
    longitude = degreesToRadians(longitude)
    c1 = np.array([-1 * np.sin(longitude), np.cos(longitude), 0])
    c3 = np.array([-1 * camPoseEcef[0], -1 * camPoseEcef[1], -1 * camPoseEcef[2]])
    c3 = c3 / LA.norm(c3)  # normalize the vector
    c2 = np.cross(c3, c1)
    c2 = c2 / LA.norm(c2)  # normalize
    rotMatrix = np.matrix([c1, c2, c3])
    return np.transpose(rotMatrix)
    
    
def pointToTuple(point):
    """converts geom3 point object to a tuple"""
    pointTuple = (float(point.x), float(point.y), float(point.z)) 
    return pointTuple


# TODO: http://gis.stackexchange.com/questions/20780/point-of-intersection-for-a-ray-and-earths-surface
def imageCoordToEcef(cameraLonLatAlt, pixelCoord, opticalCenter, focalLength):
    """
    Given the camera position in ecef and image coordinates x,y
    returns the coordinates in ecef frame (x,y,z)
    """
    cameraPoseEcef = transformLonLatAltToEcef(cameraLonLatAlt)
    cameraPose = Point3(cameraPoseEcef[0], cameraPoseEcef[1], cameraPoseEcef[2])  # ray start is camera position in world coordinates
    dirVector = pixelToVector(opticalCenter, focalLength, pixelCoord)  # vector from center of projection to pixel on image.
    # rotate the direction vector (center of proj to pixel) from camera frame to ecef frame 
    rotMatrix = rotMatrixFromCameraToEcef(cameraLonLatAlt[0], cameraPoseEcef)
    dirVector_np = np.array([[dirVector.dx], [dirVector.dy], [dirVector.dz]])         
    dirVecEcef_np = rotMatrix * dirVector_np
    # normalize the direction vector
    dirVectorEcef = Vector3(dirVecEcef_np[0], dirVecEcef_np[1], dirVecEcef_np[2])
    dirVectorEcef = dirVectorEcef.norm()
    #construct the ray
    ray = Ray3(cameraPose, dirVectorEcef)
    #intersect it with Earth
    earthCenter = Point3(0,0,0)  # since we use ecef, earth center is 0 0 0
    earth = Sphere(earthCenter, EARTH_RADIUS_METERS)
    t = earth.intersect(ray)
    
    if t != float("inf"):
        # convert t to ecef coords
        ecefCoords = ray.start + t*ray.dir
        return pointToTuple(ecefCoords)
    else: 
        return None


def getCenterPoint(width, height, mission, roll, frame):
    """
    Center point is only available if the image has mission, roll, and frame.
    """
    imageInfo = getIssImageInfo(mission, roll, frame)
    try: 
        latitude = imageInfo['latitude']
        longitude = imageInfo['longitude']
        altitude = imageInfo['altitude']
        focalLength = imageInfo['focalLength']
        sensorSize = imageInfo['sensorSize']
    except Exception as e:
        errorMsg = "Failed to get ISS image info from ISS MRF. " + str(e)
        logging.error(errorMsg)
        print errorMsg
             
    longLatAlt = (longitude, latitude, altitude)
    centerCoords = [width / 2.0, height / 2.0]
    opticalCenter = (int(width / 2.0) , int(height / 2.0))
    
    centerPointEcef = imageCoordToEcef(longLatAlt, centerCoords, opticalCenter, focalLength)       
    centerPointLonLatAlt = transformEcefToLonLatAlt(centerPointEcef)
    return {"lon": centerPointLonLatAlt[0], "lat": centerPointLonLatAlt[1], "alt": centerPointLonLatAlt[2]}
    