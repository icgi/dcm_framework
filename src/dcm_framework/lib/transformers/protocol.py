"""

T* transforming data from required to provided columns of the contract.

"""

import numpy
import pandas
import pathlib

from ..entities.protocol import contract


class StereographicProjection___from___Protocol:
    """ Appends stereographic projection columns to the protocol. """

    @contract(
        requires=[("layout", "x"), ("layout", "y"), ("layout", "distance_on_axis_to_sample___mm")],
        provides=[("projection", "x_stereographic"), ("projection", "y_stereographic")],
    )
    def __call__(self, protocol, manifest):
        x___mm = protocol[("layout", "x")].values.astype(numpy.float64)
        y___mm = protocol[("layout", "y")].values.astype(numpy.float64)
        z___mm = protocol[("layout", "distance_on_axis_to_sample___mm")].values.astype(numpy.float64)

        magnitude___mm = numpy.sqrt(x___mm ** 2 + y___mm ** 2 + z___mm ** 2)
        direction_x = x___mm / magnitude___mm
        direction_y = y___mm / magnitude___mm
        direction_z = z___mm / magnitude___mm

        # avoids division by zero when direction_z approaches -1 (emitter at antipodal pole)
        denominator = numpy.maximum(1.0 + direction_z, numpy.finfo(numpy.float64).tiny)
        x_stereographic = direction_x / denominator
        y_stereographic = direction_y / denominator

        frame_projection = pandas.DataFrame(
            {"x_stereographic": x_stereographic, "y_stereographic": y_stereographic},
            index=protocol.index,
        )
        frame_projection.columns = pandas.MultiIndex.from_product(
            [["projection"], frame_projection.columns],
        )

        protocol = pandas.concat([protocol, frame_projection], axis="columns")
        return protocol, manifest


class GnomonicProjection___from___Protocol:
    """ Appends gnomonic projection columns to the protocol. """

    @contract(
        requires=[("layout", "x"), ("layout", "y"), ("layout", "distance_on_axis_to_sample___mm")],
        provides=[("projection", "x_gnomonic"), ("projection", "y_gnomonic")],
    )
    def __call__(self, protocol, manifest):
        x___mm = protocol[("layout", "x")].values.astype(numpy.float64)
        y___mm = protocol[("layout", "y")].values.astype(numpy.float64)
        z___mm = protocol[("layout", "distance_on_axis_to_sample___mm")].values.astype(numpy.float64)

        magnitude___mm = numpy.sqrt(x___mm ** 2 + y___mm ** 2 + z___mm ** 2)
        direction_x = x___mm / magnitude___mm
        direction_y = y___mm / magnitude___mm
        direction_z = z___mm / magnitude___mm

        # avoids division by zero when direction_z approaches 0 (emitter at 90 degrees)
        safe_direction_z = numpy.where(
            numpy.abs(direction_z) < numpy.finfo(numpy.float64).tiny,
            numpy.copysign(numpy.finfo(numpy.float64).tiny, direction_z),
            direction_z,
        )
        x_gnomonic = direction_x / safe_direction_z
        y_gnomonic = direction_y / safe_direction_z

        frame_projection = pandas.DataFrame(
            {"x_gnomonic": x_gnomonic, "y_gnomonic": y_gnomonic},
            index=protocol.index,
        )
        frame_projection.columns = pandas.MultiIndex.from_product(
            [["projection"], frame_projection.columns],
        )

        protocol = pandas.concat([protocol, frame_projection], axis="columns")
        return protocol, manifest


class PolarLayout___from___Protocol:
    """ Appends theta and phi spherical angle columns to the protocol. """

    @contract(
        requires=[
            ("layout", "x"),
            ("layout", "y"),
            ("layout", "distance_on_axis_to_sample___mm")
        ],
        provides=[
            ("layout", "theta___rad"),
            ("layout", "phi___rad"),
            ("layout", "theta___deg"),
            ("layout", "phi___deg"),
        ],
    )
    def __call__(self, protocol, manifest):
        x___mm = protocol[("layout", "x")].values.astype(numpy.float64)
        y___mm = protocol[("layout", "y")].values.astype(numpy.float64)
        z___mm = protocol[("layout", "distance_on_axis_to_sample___mm")].values.astype(numpy.float64)

        # arctan2 is numerically stable for all quadrants including near-axis points
        radial_distance___mm = numpy.hypot(x___mm, y___mm)
        theta___rad = numpy.arctan2(radial_distance___mm, z___mm)

        # wraps phi to [0, 2*pi) via modulo
        phi___rad = numpy.arctan2(y___mm, x___mm) % (2.0 * numpy.pi)

        theta___deg = numpy.rad2deg(theta___rad)
        phi___deg = numpy.rad2deg(phi___rad)

        frame = pandas.DataFrame(
            {
                "theta___rad": theta___rad,
                "phi___rad": phi___rad,
                "theta___deg": theta___deg,
                "phi___deg": phi___deg,
            },
            index=protocol.index,
        )
        frame.columns = pandas.MultiIndex.from_product(
            [["layout"], frame.columns],
        )

        protocol = pandas.concat([protocol, frame], axis="columns")
        return protocol, manifest


class Paths___from___Protocol:
    """ Appends image path columns to the protocol. """

    @contract(
        requires=[("layout", "ordinal")],
        provides=[("paths", "path_to_image"), ("paths", "path_to_preview_image")],
    )
    def __call__(self, protocol, manifest):
        path_to_experiment_container = pathlib.Path(
            manifest["path_to_experiment_container"]
        )

        frame = pandas.DataFrame(index=protocol.index)
        frame[("paths", "path_to_image")] = protocol.apply(
            lambda row: str(
                path_to_experiment_container / f"default/image_{row.name}.tif"
            ),
            axis="columns",
        )
        frame[("paths", "path_to_preview_image")] = protocol.apply(
            lambda row: str(
                path_to_experiment_container / f"preview/image_{row.name}.jpg"
            ),
            axis="columns",
        )

        protocol = pandas.concat([protocol, frame], axis="columns")
        return protocol, manifest


class EmitterGeometryDefaults___from___Protocol:
    """ Appends default CAD geometry columns to the protocol. """

    @contract(
        requires=[],
        provides=[
            ("emitter_geometry", "yaw___deg"),
            ("emitter_geometry", "scaling_x"),
            ("emitter_geometry", "scaling_y"),
        ],
    )
    def __call__(self, protocol, manifest):
        frame = pandas.DataFrame(index=protocol.index)
        frame[("emitter_geometry", "yaw___deg")] = 0.0
        frame[("emitter_geometry", "scaling_x")] = 1.0
        frame[("emitter_geometry", "scaling_y")] = 1.0

        protocol = pandas.concat([protocol, frame], axis="columns")
        return protocol, manifest