# Based on https://github.com/phire/Python-Ray-tracer/blob/master/sphere.py
# http://www.lighthouse3d.com/tutorials/maths/ray-sphere-intersection/
# Intersect code from https://gist.github.com/rossant/6046463   

"""A ray-traceable sphere is a sphere with a given
   centre and radius and a given surface material.
   It needs an intersect method that returns the
   point of intersection of a given ray with the
   sphere and a normal method that returns the
   surface at a given point on the sphere surface."""

from geom3 import Vector3, Point3, Ray3, dot, unit, length
from math import sqrt
 

class Sphere(object):
    """A ray-traceable sphere"""
    
    def __init__(self, center, radius):
        """Create a sphere with a given centre point, radius
        and surface material"""
        self.center = center
        self.radius = radius


    def normal(self, p):
        """The surface normal at the given point on the sphere"""
        return unit(p - self.center)


    def intersect(self, ray):
        # Return the distance from O to the intersection of the ray (O, D) with the 
        # sphere (S, R), or None if there is no intersection.
        # O and S are 3D points, D (direction) is a normalized vector, R is a scalar.
        O = ray.start
        D = ray.dir
        S = self.center
        R = self.radius
        a = D.dot(D)
        OS = O - S
        b = 2 * D.dot(OS)
        c = OS.dot(OS) - R * R
        disc = b * b - 4 * a * c
        if disc > 0:
            distSqrt = sqrt(disc)
            q = (-b - distSqrt) / 2.0 if b < 0 else (-b + distSqrt) / 2.0
            t0 = q / a
            t1 = c / q
            t0, t1 = min(t0, t1), max(t0, t1)
            if t1 >= 0:
                return t1 if t0 < 0 else t0
        return float("inf")

    def __repr__(self):
        return "Sphere(%s, %.3f)" % (str(self.center), self.radius)

# Two simple sanity tests if module is run directly

if __name__ == "__main__":
    sphere = Sphere(Point3(1,0,0), 1)
    ray = Ray3(Point3(1,0,5), Vector3(0,0,-1))
    missingRay = Ray3(Point3(1,0,5), Vector3(0,0,1))
    assert abs(sphere.intersect(ray) - 4.0) < 0.00001
    assert sphere.intersect(missingRay) is None