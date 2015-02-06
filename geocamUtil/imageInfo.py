import os
import PIL
import urllib2
import logging
from geocamTiePoint import settings
from geocamUtil.ErrorJSONResponse import ErrorJSONResponse, checkIfErrorJSONResponse

try:
    from cStringIO import StringIO
except ImportError:
    from StringIO import StringIO


PDF_MIME_TYPES = ('application/pdf',
                  'application/acrobat',
                  'application/nappdf',
                  'application/x-pdf',
                  'application/vnd.pdf',
                  'text/pdf',
                  'text/x-pdf',
                  )

def getAccurateFocalLengths(imageSize, focalLength, sensorSize):
    """
    Parameters: image size x,y (pixels), focalLength (meters), sensorSize x,y (meters)
    
    Focal length listed on the image exif is unitless...
    We need focal length in pixels / meters. 
    Therefore, we scale the exif focal length by number of 
    pixels per meter on the actual CCD sensor.
    """
    w_s = sensorSize[0]  # in meters
    h_s = sensorSize[0]
    
    w_i = imageSize[0]  # in pixels
    h_i = imageSize[1]
    
    f = focalLength  # unit less
    
    focalLengthPixelsPerMeter = (w_i / w_s * f, h_i / h_s * f)
    return focalLengthPixelsPerMeter    


def validOverlayContentType(contentType):
    if settings.PDF_IMPORT_ENABLED and contentType in PDF_MIME_TYPES:
        # this will change to False when pdf conversion goes away
        return True
    if contentType.startswith('image/'):
        return True
    return False


def getUrlForImageInfo(mission, roll, frame):
    """
    Returns url for image info page that includes
    focal length, iss position, etc.
    """
    url = "http://eol.jsc.nasa.gov/GeoCam/PhotoInfo.pl?photo=%s-%s-%s" % (mission, roll, frame)
    return url


def getUrlForImage(mission, roll, frame, imageSize = 'small'):
    """
    Returns url for iss image.
    """
    rootUrl = "http://eol.jsc.nasa.gov/DatabaseImages/ESC/" 
    return  rootUrl + imageSize + "/" + mission + "/" + mission + "-" + roll + "-" + frame + ".jpg"


def getImageDataFromImageUrl(imageUrl):
    """
    Given a url to an image, get imageSize, imageFB, 
    imageType, and imageName needed for constructing the overlay. 
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
    imageFB = StringIO(response.read())
    imageType = response.headers['Content-Type']
    imageName = imageUrl.split('/')[-1]
    response.close()
    return imageName, imageFB, imageType, imageId


def getImageSizeFromMRF(mission, roll, frame):
    # generate the image url from mrf
    imageUrl = getUrlForImage(mission, roll, frame, 'small')
    # open the image url and retrieve info
    retval = getImageDataFromImageUrl(imageUrl)
    if checkIfErrorJSONResponse(retval):
        return retval
    else: 
        imageName, imageFB, imageType, imageId = retval
    # get image bits
    bits = imageFB.read()
    try:  # open it as a PIL image
        image = PIL.Image.open(StringIO(bits))
    except Exception as e:  # pylint: disable=W0703
        logging.error("PIL failed to open image: " + str(e))
        return ErrorJSONResponse("There was a problem reading the image.")
    width, height = image.size
    return {'width': width, 'height': height}


def getIssImageInfo(mission, roll, frame, width=None, height=None):
    """
    Given Mission, Roll, Frame, returns the image info 
    such as latitude, longitude, altitude of ISS nadir position and
    the initial focal length (these values are fetched from JSC website)
    """
    if not (width and height): 
        imageSize = getImageSizeFromMRF(mission, roll, frame)
        # if getImageSizeFromMRF returned an errorJSON, return right away.
        if checkIfErrorJSONResponse(imageSize):
            return imageSize
        width = imageSize['width']
        height = imageSize['height']
                 
    url = getUrlForImageInfo(mission, roll, frame)
    urlpath = urllib2.urlopen(url)
    string = urlpath.read().decode('utf-8') 
    params = string.split('\n')
    paramsDict = {}
    for param in params:
        paramsDict[param.split(':')[0]] = param.split(':')[-1]
    latitude = None
    longitude = None
    Altitude = None
    initialFocalLength = None
    sensorSize = (.036,.0239)  #TODO: figure out a way to not hard code this.
    
    for key, value in paramsDict.items():
         if 'latitude' in key:
             latitude = float(value.split(',')[0]) 
             longitude = float(value.split(',')[1]) 
         elif 'altitude' in key:
             altitude = float(value) * 1609.34  # convert miles to meters
         elif 'Focal length' in key:
             print "focal length"
             print value
             initialFocalLength = float(value)
    focalLength = getAccurateFocalLengths([width, height], initialFocalLength, sensorSize)
    return {'latitude': latitude, 'longitude':  longitude, 'altitude': altitude, 
            'focalLength': focalLength, 'sensorSize': sensorSize,
            'width': width, 'height': height}
