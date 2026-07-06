import base64
import datetime
import pathlib
import random
import uuid

import fire
import questionary

from ._vendor.protocol_engine import Protocol
from ._vendor.protocol_engine.mixins import VerboseProtocol

from .lib.transformers.assets import *
from .lib.transformers.prompt import *
from .lib.transformers.protocol import *

try:
    import friendly_names as _friendly_names_module
    _has_friendly_names = True
except ImportError:
    _has_friendly_names = False


class DcmProtocol(
    Manifest___from___Prompt,
    Layout___from___Prompt___R2,
    StereographicProjection___from___Protocol,
    GnomonicProjection___from___Protocol,
    EquidistantProjection___from___Protocol,
    OrthographicProjection___from___Protocol,
    LambertProjection___from___Protocol,
    PolarLayout___from___Protocol,
    Paths___from___Protocol,
    EmitterGeometryDefaults___from___Protocol,
    PlaceholderImages___from___Protocol,
    PtychogramNavigator___from___Protocol,
    IlluminatorShells___from___Protocol,
    LayoutOverviewImage___from___Protocol,
    ExcelProtocol___from___Protocol,
    VerboseProtocol,
):
    pass


def _prompt_for_workspace():
    """ Prompts for experiment container path and name, returns the workspace path. """
    result = None

    date_string = datetime.date.today().strftime("%Y-%m-%d")
    random_integer = random.randint(0, 999)

    if _has_friendly_names:
        identifier = _friendly_names_module.generate(words=3, separator="-")
    else:
        identifier = (
            base64.urlsafe_b64encode(uuid.uuid4().bytes)
            .rstrip(b"=")
            .decode("ascii")
        )

    experiment_name_suggestion = f"experiment___{identifier}___{random_integer:03d}___{date_string}"

    path_to_experiment_container = pathlib.Path(
        questionary.text(
            message="Path to experiment container (folder)",
            default="./experiments",
        ).ask()
    )

    experiment_name = questionary.text(
        message="Experiment name",
        default=experiment_name_suggestion,
    ).ask()

    result = path_to_experiment_container / experiment_name
    return result


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
              manifest.scad
                  OpenSCAD source defining manifest parameters (shell thickness, padding, etc.).
              illuminator_shell___hemispherical.scad
              illuminator_shell___planar.scad
                  Parametric OpenSCAD shell templates that use emitters.scad and manifest.scad
                  to produce illuminator housings with emitter cutouts. The hemispherical
                  shell optionally engraves ring transition markers between theta rings,
                  renders the support alongside the shell, and clips the model to an
                  angular sector for test prints.
              shell_support.scad
                  Standalone parametric support for the hemispherical shell: upper and lower
                  rings (heights and widths adjustable separately), pillars sized relative
                  to the shell radius, and an alignment notch.
              layout_overview.png
                  Matplotlib plot showing emitter positions with ordinal labels,
                  concentric-ring overlays, and crosshairs.

            """
            workspace = _prompt_for_workspace()
            protocol = DcmProtocol(workspace=workspace)
            protocol.build()


def main():
    fire.Fire(DcmFrameworkRunner)


if __name__ == "__main__":
    main()
