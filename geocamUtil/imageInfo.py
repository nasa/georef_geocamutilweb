#__BEGIN_LICENSE__
# Copyright (c) 2017, United States Government, as represented by the
# Administrator of the National Aeronautics and Space Administration.
# All rights reserved.
#
# The GeoRef platform is licensed under the Apache License, Version 2.0
# (the "License"); you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
# http://www.apache.org/licenses/LICENSE-2.0.
#
# Unless required by applicable law or agreed to in writing, software distributed
# under the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR
# CONDITIONS OF ANY KIND, either express or implied. See the License for the
# specific language governing permissions and limitations under the License.
#__END_LICENSE__


import os
import PIL
import urllib2
import logging
import PIL.Image
from django.conf import settings
from geocamUtil.ErrorJSONResponse import ErrorJSONResponse, checkIfErrorJSONResponse

try:
    from cStringIO import StringIO
except ImportError:
    from StringIO import StringIO


def getAccurateFocalLengths(imageSize, focalLength, sensorSize):
    """
    Parameters: image size x,y (pixels), focalLength (mili meters), sensorSize x,y (meters)
    
    Focal length listed on the image exif is unitless...
    We need focal length in pixels / meters. 
    Therefore, we scale the exif focal length by number of 
    pixels per meter on the actual CCD sensor.
    """
    w_s = sensorSize[0]  # in meters
    h_s = sensorSize[1]
    
    w_i = imageSize[0]  # in pixels
    h_i = imageSize[1]
    
    f = focalLength / 1000.0 # milimeters to meters
    
    focalLengthPixelsPerMeter = (w_i / w_s * f, h_i / h_s * f)
    return focalLengthPixelsPerMeter    


def validOverlayContentType(contentType):
    if settings.PDF_IMPORT_ENABLED and contentType in settings.PDF_MIME_TYPES:
        # this will change to False when pdf conversion goes away
        return True
    if contentType.startswith('image/'):
        return True
    return False


class dotdict(dict):
    """dot.notation access to dictionary attributes"""
    def __getattr__(self, attr):
        return self.get(attr)
    __setattr__= dict.__setitem__
    __delattr__= dict.__delitem__
    

def getImageFile(imageUrl):
    """
    Given a url to an image, get 
    file, size, type, name needed for constructing the overlay. 
    """
    imageId = None  # mission-roll-frame
    imageDict = {}
    # if url is from eol website, extract the image id.
    if ("eol.jsc.nasa.gov" in imageUrl) or ("eo-web.jsc.nasa.gov" in imageUrl):
        imageName = imageUrl.split("/")[-1]  # get the image id (last elem in list)
        imageId = imageName.split('.')[0]
    # we have a url, try to download it
    try:
        response = urllib2.urlopen(imageUrl)
    except urllib2.HTTPError as e:
        logging.error("getImageFile failed to fetch "+imageUrl+" "+str(e))
        return ErrorJSONResponse("There was a problem fetching the image at this URL.")
    if response.code != 200:
        logging.error("getImageFile failed to fetch "+imageUrl+" giving HTTP response code "+str(response.code))
        return ErrorJSONResponse("There was a problem fetching the image at this URL.")
      
    if not validOverlayContentType(response.headers.get('content-type')):
        # we didn't receive an image,
        # or we did and the server didn't say so.
        logging.error("Non-image content-type:" + response.headers['Content-Type'].split('/')[0])
        return ErrorJSONResponse("The file at this URL does not seem to be an image.")  
    imageSize = int(response.info().get('content-length'))
    if imageSize > settings.MAX_IMPORT_FILE_SIZE:
        logging.error("The submitted file is larger than the maximum allowed size. Maximum size is %d bytes." % settings.MAX_IMPORT_FILE_SIZE)
        return ErrorJSONResponse("The submitted file is larger than the maximum allowed size. " +
                                 "Maximum size is %d bytes." % settings.MAX_IMPORT_FILE_SIZE)
    file = StringIO(response.read())
    type = response.headers['Content-Type']
    name = imageUrl.split('/')[-1]
    response.close()
    imageDict = {'name': name, 'file': file, 'content_type': type, 'id': imageId}
    return dotdict(imageDict)


def getImageWidthHeight(issImage):
    # generate the image url from mrf
    # open the image url and retrieve info
    retval = getImageFile(issImage.imageUrl)
    if checkIfErrorJSONResponse(retval):
        return retval
    # get image bits
    bits = retval.file.read()
    try:  # open it as a PIL image
        image = PIL.Image.open(StringIO(bits))
    except Exception as e:  # pylint: disable=W0703
        logging.error("PIL failed to open image: " + str(e))
        return ErrorJSONResponse("There was a problem reading the image.")
    return image.size


def constructExtrasDict(infoUrl):
    """
    Helper that takes the image info script output from JSC and constructs a python dict.
    """
    urlpath = urllib2.urlopen(infoUrl)
    string = urlpath.read().decode('utf-8') 
    params = string.split('\n')
    extrasDict = {'id': None, 
                  'nadirLat': None, 
                  'nadirLon': None, 
                  'centerLat': None, 
                  'centerLon': None, 
                  'altitude': None, 
                  'azimuth': None, 
                  'sunElevationDeg': None, 
                  'focalLength_unitless': None, 
                  'focalLength': None, 
                  'camera': None, 
                  'acquisitionDate': None, 
                  'acquisitionTime': None}
    for param in params:
        splitLine = param.split(':')
        try: 
            key = splitLine[0]
            value = splitLine[1:]
        except: 
            continue
        if "Photo" == key:
            try:
                extrasDict['id'] = value[0].strip()  
            except: 
                continue
        elif "Nadir latitude,longitude in degrees" in key:
            try: 
                value = value[0].strip()
                extrasDict['nadirLat'] = float(value.split(',')[0].strip()) 
                extrasDict['nadirLon'] = float(value.split(',')[1].strip())
            except:
                continue 
        elif "Center point latitude,longitude in degrees" in key:
            try: 
                centerPoint = value[0].strip()
                extrasDict['centerLat'] = float(value[0].split(',')[0].strip()) 
                extrasDict['centerLon'] =  float(value[0].split(',')[1].strip()) 
            except: 
                extrasDict['centerLat'] = None
                extrasDict['centerLon'] = None
                print "center lat and lon are not available. use nadir and calculate the center point instead."
        elif "Spacecraft altitude in nautical miles" in key:
            try: 
                extrasDict['altitude'] = float(value[0].strip()) * 1609.34  # convert miles to meters
            except: 
                continue
        elif "Sun azimuth" in key:
            try: 
                extrasDict['azimuth'] = float(value[0].strip())
            except:
                continue
        elif "Sun elevation angle" in key:
            try: 
                extrasDict['sunElevationDeg'] = float(value[0].strip())
            except:
                continue
        elif "Focal length in millimeters" in key:
            try: 
                extrasDict['focalLength_unitless'] = float(value[0].strip())
            except:
                continue
        elif "Camera" in key:
            try: 
                extrasDict['camera'] = value[0].strip()
            except:
                continue
        elif "Photo Date" == key:
            try:
                extrasDict['acquisitionDate'] = value[0].strip()
            except:
                continue
        elif "Photo Time" == key:
            try: 
                extrasDict['acquisitionTime'] = value[0].strip()
            except:
                continue
    return dotdict(extrasDict)
