import fire

from .lib.entities.protocol import contract, Protocol

from .lib.transformers.assets import *
from .lib.transformers.prompt import *
from .lib.transformers.protocol import *


class DcmProtocol(
    Manifest___from___Prompt,
    Layout___from___Prompt,
    StereographicProjection___from___Protocol,
    GnomonicProjection___from___Protocol,
    PolarLayout___from___Protocol,
    Paths___from___Protocol,
    EmitterGeometryDefaults___from___Protocol,
    ExcelProtocol___from___Protocol,
    PlaceholderImages___from___Protocol,
    PtychogramNavigator___from___Protocol,
    PositionsScad___from___Protocol,
    LayoutOverviewImage___from___Protocol,
    Protocol,
):
    pass


class DcmFrameworkRunner:
    class experiment:
        def build(self):
            """

            Interrogates the user to create a detailed description of the illumination model.
            Provides assets and container structure for your experiment.

            While performing image acquisition, save images into the container as specified
            in the protocol.

            Protocol column groups (upper multi-index level):

              layout
                  x, y                             - Cartesian emitter positions in mm
                  distance_on_axis_to_sample___mm  - axial distance from emitter plane to sample
                  ordinal                          - integer emitter index
                  theta___rad, phi___rad           - polar and azimuthal angles in radians
                  theta___deg, phi___deg           - polar and azimuthal angles in degrees
                  magnitude___mm                   - Euclidean distance from origin to emitter

              projection
                  x_stereographic, y_stereographic - stereographic projection of direction vector
                  x_gnomonic, y_gnomonic           - gnomonic projection of direction vector
              paths
                  path_to_image                    - expected path for acquired emitter image
                  path_to_preview_image            - path for preview thumbnail

              emitter_geometry
                  yaw___deg                        - emitter rotation around its normal axis
                  scaling_x, scaling_y             - emitter cutout scale factors for CAD
            Generated assets:

              protocol.xlsx
                  Full protocol DataFrame exported to Excel for inspection and downstream use.

              preview/image_<ordinal>.jpg
                  Placeholder preview images (512x512 JPEG) for each emitter position.
                  Replaced by real acquisitions during the experiment.
              PtychogramNavigator___Stereographic.html
              PtychogramNavigator___Gnomonic.html
                  Interactive HTML viewers that place preview thumbnails at their projected
                  positions with pan, zoom, and switchable image channels.
              emitters.scad
                  OpenSCAD source defining emitter positions and parameters as structured data.
                  Consumed by the parametric shell templates to generate 3D-printable geometry.
              hemispherical_illuminator_shell.scad
              planar_illuminator_shell.scad
                  Parametric OpenSCAD shell templates that use emitters.scad to produce
                  illuminator housings with emitter cutouts.
              layout_overview.png
                  Matplotlib plot showing emitter positions with ordinal labels,
                  concentric-ring overlays, and crosshairs.

            """
            protocol = DcmProtocol()
            protocol.build()


def main():
    fire.Fire(DcmFrameworkRunner)


if __name__ == "__main__":
    main()
