import numpy
import shapely


class GenericShell:
    """ Generates a single ring of emitter positions on a polygon or circle of given radius. """

    def __init__(self, radius, order, *, shell_type="polygon", transition=-1, rotation=None, radial_ordering=None):
        self.radius = radius
        self.order = order
        self.shell_type = shell_type

        if radius > 0:
            n_position_nodes = order * radius
            if order == 4:
                n_position_nodes *= 2

            shape_fractions = numpy.linspace(0, 1, order + 1)
            position_fractions = numpy.linspace(0, 1, n_position_nodes + 1)
            position_fractions = numpy.roll(position_fractions, transition)

            shape_polygon = shapely.Point(0, 0).buffer(radius).exterior

            if shell_type == "polygon":
                shape = shapely.geometry.LineString(
                    shape_polygon.interpolate(shape_fractions, normalized=True)
                )
                rotation_correction___deg = 90
                resolved_rotation___deg = (
                    (180 / order + rotation_correction___deg) if rotation is None else rotation
                )
            else:
                shape = shape_polygon
                resolved_rotation___deg = 90 if rotation is None else rotation

            positions = shapely.LineString(
                shape.interpolate(position_fractions, normalized=True)
            )
            positions = shapely.affinity.rotate(positions, resolved_rotation___deg)
            shape = shapely.affinity.rotate(shape, resolved_rotation___deg)

            if radial_ordering == "ccw":
                positions = shapely.affinity.scale(positions, xfact=-1, origin=(0, 0))
                shape = shapely.affinity.scale(shape, xfact=-1, origin=(0, 0))
        else:
            positions = shapely.LineString([[0, 0], [0, 0]])
            shape = shapely.geometry.LineString([[0, 0], [0, 0]])

        self.positions = positions
        self.shape = shape
