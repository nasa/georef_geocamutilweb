import json
from django.http import HttpResponse


class ErrorJSONResponse(HttpResponse):
    """
    Packages up a form error into a JSON response that will be nice to deal with client-side.
    The errors argument expects a django forms ErrorDict object.
    If a string is given as the errors argument, the ErrorDict will be emulated.
    """
    def __init__(self, errors, *args, **kwargs):
        if isinstance(errors, basestring):
            errors = {"__all__": [errors]}
        super(ErrorJSONResponse, self).__init__(json.dumps(errors), *args, status=400, content_type="application/json", **kwargs)


def checkIfErrorJSONResponse(retval):
    """
    Checks if the JSON returned is of the calss ErrorJSONReponse
    """
    return retval.__class__.__name__ == "ErrorJSONResponse"