# Based on https://github.com/phire/Python-Ray-tracer/blob/master/plane.py
# https://gist.github.com/rossant/6046463

"""A ray-traceable Plane is a Plane through a given
   point with a given normal and surface material.
   It needs an intersect method that returns the
   point of intersection of a given ray with the
   plane and a normal method that returns the normal
   at a given point (which is irrelevant for a plane
   as the normal is the same everywhere)."""

from geom3 import Vector3, Point3, Ray3, dot, unit
from math import sqrt
from hit import Hit

class Plane(object):
    """A ray-traceable plane"""
    
    def __init__(self, point, normal):
        """Create a plane through a given point with given normal"""
        self.point = point
        self.norm = unit(normal)

    def intersect(self, ray):
        # Return the distance from O to the intersection of the ray (O, D) with the 
        # plane (P, N), or +inf if there is no intersection.
        # O and P are 3D points, D and N (normal) are normalized vectors.
        O = ray.start
        D = ray.dir
        P = self.point # some point on the plane
        N = self.norm # normal vector to the plane
        denom = np.dot(D, N)
        if np.abs(denom) < 1e-6:
            return np.inf
        d = np.dot(P - O, N) / denom
        if d < 0:
            return np.inf
        return d