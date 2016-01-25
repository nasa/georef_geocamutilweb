import os
import PIL
import urllib2
import logging
import PIL.Image
from geocamTiePoint import settings
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
    # if url is from eol website, extract the image id.
    if ("eol.jsc.nasa.gov" in imageUrl) or ("eo-web.jsc.nasa.gov" in imageUrl):
        imageName = imageUrl.split("/")[-1]  # get the image id (last elem in list)
        imageId = imageName.split('.')[0]
    # we have a url, try to download it
    try:
        response = urllib2.urlopen(imageUrl)
    except urllib2.HTTPError as e:
        return ErrorJSONResponse("There was a problem fetching the image at this URL.")
    if response.code != 200:
        return ErrorJSONResponse("There was a problem fetching the image at this URL.")
      
    if not validOverlayContentType(response.headers.get('content-type')):
        # we didn't receive an image,
        # or we did and the server didn't say so.
        logging.error("Non-image content-type:" + response.headers['Content-Type'].split('/')[0])
        return ErrorJSONResponse("The file at this URL does not seem to be an image.")
      
    imageSize = int(response.info().get('content-length'))
    if imageSize > settings.MAX_IMPORT_FILE_SIZE:
        return ErrorJSONResponse("The submitted file is larger than the maximum allowed size. " +
                                 "Maximum size is %d bytes." % settings.MAX_IMPORT_FILE_SIZE)
    file = StringIO(response.read())
    type = response.headers['Content-Type']
    name = imageUrl.split('/')[-1]
    response.close()
    return dotdict({'name': name, 'file': file, 'content_type': type, 'id': imageId})


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


def getIssImageInfo(issImage):
    """
    Given Mission, Roll, Frame, returns the image info 
    such as latitude, longitude, altitude of ISS nadir position and
    the initial focal length (these values are fetched from JSC website)
    """
    # get image size
    imageSize = getImageWidthHeight(issImage)
    if checkIfErrorJSONResponse(imageSize):
        return imageSize
    # fetch meta info from image
    urlpath = urllib2.urlopen(issImage.infoUrl)
    string = urlpath.read().decode('utf-8') 
    params = string.split('\n')
    paramsDict = {}
    for param in params:
        paramsDict[param.split(':')[0]] = param.split(':')[-1]
    
    nadirLat = None
    nadirLon = None
    centerLat = None
    centerLon = None
    altitude = None
    initialFocalLength = None
    date = None
    
    sensorSize = (.036,.0239)  #TODO: figure out a way to not hard code this.
    for key, value in paramsDict.items():
        if 'Nadir latitude,longitude in degrees' in key:
            value = value.strip()
            nadirLat = float(value.split(',')[0].strip()) 
            nadirLon = float(value.split(',')[1].strip()) 
        elif 'Spacecraft altitude in nautical miles' in key:
            altitude = float(value.strip()) * 1609.34  # convert miles to meters
        elif 'Focal length' in key:
            initialFocalLength = float(value.strip())
        elif 'Center point latitude,longitude in degrees' in key:
            if value:
                try: 
                    centerPoint = value.strip()
                    centerLat = float(value.split(',')[0].strip()) 
                    centerLon =  float(value.split(',')[1].strip()) 
                except: 
                    print "center lat and lon are not available. use nadir and calculate the center point instead."
        elif 'Photo Date' in key:
            date = value.strip()
    focalLength = getAccurateFocalLengths(imageSize, initialFocalLength, sensorSize)
    focalLength = [round(focalLength[0]), round(focalLength[1])]
    return {'nadirLat': nadirLat, 'nadirLon':  nadirLon, 'altitude': altitude, 
            'centerLat': centerLat, 'centerLon': centerLon,
            'focalLength_unitless': initialFocalLength, # this is the unitless focallength directly from the EOL website (in mm).
            'focalLength': focalLength, 'sensorSize': sensorSize,
            'width': imageSize[0], 'height': imageSize[1],'centerPoint': centerPoint, 'date': date}
    