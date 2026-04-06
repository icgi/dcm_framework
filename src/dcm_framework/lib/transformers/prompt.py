"""

T* that capture user input from interactive prompt as the basis of experiment protocol and manifest.

"""

import numpy
import pandas
import base64
import datetime
import pathlib
import random
import uuid
import questionary

from ..entities.layout import GenericShell
from ..entities.protocol import contract

try:
    import friendly_names as _friendly_names_module

    _has_friendly_names = True
except ImportError:
    _has_friendly_names = False

SPIRAL_PRESETS = {
    "Spiral - Square rings": (4, "polygon"),
    "Spiral - Hexagonal rings": (6, "polygon"),
    "Spiral - Octagonal rings": (8, "polygon"),
    "Spiral - Circular rings": (6, "circle"),
}


class Manifest___from___Prompt:
    """ Prompts user for experiment metadata and populates the manifest. """

    @contract(
        requires=[],
        provides=[],
    )
    def __call__(self, protocol, manifest):
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
                default=".experiments",
            ).ask()
        )

        experiment_name = questionary.text(
            message="Experiment name",
            default=experiment_name_suggestion,
        ).ask()

        shell_thickness___mm = float(questionary.text(
            message="Shell thickness (mm)",
            default="1.5",
        ).ask())

        sphere_truncation_depth___mm = float(questionary.text(
            message="Sphere truncation depth (mm)",
            default="0",
        ).ask())

        shell_edge_padding___mm = float(questionary.text(
            message="Shell edge padding (mm)",
            default="10",
        ).ask())

        initial_coordinate_system = questionary.select(
            message="Choose a coordinate system",
            choices=[
                "Planar (initialize in Cartesian coordinate system)",
                "Hemispherical (initialize in Polar coordinate system)"
            ],
        ).ask()

        manifest["experiment_name"] = experiment_name
        manifest["shell_thickness___mm"] = shell_thickness___mm
        manifest["sphere_truncation_depth___mm"] = sphere_truncation_depth___mm
        manifest["shell_edge_padding___mm"] = shell_edge_padding___mm
        manifest["initial_coordinate_system"] = initial_coordinate_system
        manifest["path_to_experiment_container"] = path_to_experiment_container / experiment_name

        return protocol, manifest

class Layout___from___Prompt:
    """ Prompts user for spiral layout parameters and produces a layout protocol DataFrame. """

    @contract(
        requires=[],
        provides=[
            ("layout", "ordinal"),
            ("layout", "x"),
            ("layout", "y"),
            ("layout", "distance_on_axis_to_sample___mm")],
    )
    def __call__(self, protocol, manifest):
        illuminator_choice = questionary.select(
            message="Choose an illuminator layout",
            choices=list(SPIRAL_PRESETS.keys()),
        ).ask()

        distance_on_axis_to_sample___mm = float(
            questionary.text(
                message="Distance from center of grid to sample hemisphere radius (mm)",
                default="50"
            ).ask()
        )

        n_steps, shell_type = SPIRAL_PRESETS[illuminator_choice]

        n_shells = int(questionary.text(
            message="Number of concentric shells",
            default="9",
        ).ask())
        spacing___mm = float(questionary.text(
            message="Spacing between shells (mm)",
            default="7"
        ).ask())

        protocol = _build_layout_frame(
            n_steps=n_steps,
            shell_type=shell_type,
            n_shells=n_shells,
            scale_per_shell___mm=numpy.full(n_shells + 1, spacing___mm),
            distance_on_axis_to_sample___mm=distance_on_axis_to_sample___mm,
        )

        result = protocol, manifest
        return result


class Layout___from___Prompt___R2:
    """ Prompts user for spiral layout with lateral or polar spacing. """

    @contract(
        requires=[],
        provides=[
            ("layout", "ordinal"),
            ("layout", "x"),
            ("layout", "y"),
            ("layout", "distance_on_axis_to_sample___mm")],
    )
    def __call__(self, protocol, manifest):
        initial_coordinate_system = manifest.get("initial_coordinate_system", "")
        is_polar = "Polar" in initial_coordinate_system

        illuminator_choice = questionary.select(
            message="Choose an illuminator layout",
            choices=list(SPIRAL_PRESETS.keys()),
        ).ask()

        distance_on_axis_to_sample___mm = float(
            questionary.text(
                message="Distance from center of grid to sample hemisphere radius (mm)",
                default="50"
            ).ask()
        )

        n_steps, shell_type = SPIRAL_PRESETS[illuminator_choice]

        n_shells = int(questionary.text(
            message="Number of concentric shells",
            default="9",
        ).ask())

        if is_polar:
            theta_step___deg = float(questionary.text(
                message="Theta step between shells (degrees)",
                default="5"
            ).ask())
            theta_step___rad = numpy.deg2rad(theta_step___deg)

            # derives lateral distance per shell from polar angle
            scale_per_shell___mm = numpy.array([
                distance_on_axis_to_sample___mm * numpy.tan(shell_index * theta_step___rad)
                if shell_index > 0 else 0.0
                for shell_index in range(n_shells + 1)
            ])
            # converts cumulative radii to per-shell scale factors
            # GenericShell at radius=r produces positions at unit distance r,
            # so the scale factor for shell r is cumulative_radius / r
            scale_per_shell___mm = numpy.array([
                scale_per_shell___mm[shell_index] / shell_index
                if shell_index > 0 else 0.0
                for shell_index in range(n_shells + 1)
            ])
        else:
            spacing___mm = float(questionary.text(
                message="Spacing between shells (mm)",
                default="7"
            ).ask())
            scale_per_shell___mm = numpy.full(n_shells + 1, spacing___mm)

        protocol = _build_layout_frame(
            n_steps=n_steps,
            shell_type=shell_type,
            n_shells=n_shells,
            scale_per_shell___mm=scale_per_shell___mm,
            distance_on_axis_to_sample___mm=distance_on_axis_to_sample___mm,
        )

        result = protocol, manifest
        return result


# [>] into a superclass
def _build_layout_frame(n_steps, shell_type, n_shells, scale_per_shell___mm, distance_on_axis_to_sample___mm):
    """ Assembles a layout protocol DataFrame from shell positions scaled per shell. """
    result = None

    buffer_for_positions = []
    buffer_for_shell_indices = []
    for shell_index in range(n_shells + 1):
        shell = GenericShell(radius=shell_index, order=n_steps, shell_type=shell_type)
        coords = list(shell.positions.coords)[:-1]
        buffer_for_positions.extend(coords)
        buffer_for_shell_indices.extend([shell_index] * len(coords))

    positions_array = numpy.array(buffer_for_positions)
    shell_indices = numpy.array(buffer_for_shell_indices)

    x___mm = positions_array[:, 0] * scale_per_shell___mm[shell_indices]
    y___mm = positions_array[:, 1] * scale_per_shell___mm[shell_indices]

    result = pandas.DataFrame({
        "x": x___mm,
        "y": y___mm,
        "z": None,
        "distance_on_axis_to_sample___mm": distance_on_axis_to_sample___mm,
    })
    result["ordinal"] = numpy.arange(0, len(result))
    result.columns = pandas.MultiIndex.from_product([["layout"], result.columns])

    return result
