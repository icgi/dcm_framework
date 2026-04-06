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

        shell_shape = questionary.select(
            message="Choose a shell shape",
            choices=["Planar", "Hemispherical"],
        ).ask()

        manifest["experiment_name"] = experiment_name
        manifest["shell_shape"] = shell_shape
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

        buffer_for_positions = []
        for radius in range(n_shells + 1):
            shell = GenericShell(radius=radius, order=n_steps, shell_type=shell_type)
            buffer_for_positions.extend(list(shell.positions.coords)[:-1])

        positions_array = numpy.array(buffer_for_positions)
        x___mm = positions_array[:, 0] * spacing___mm
        y___mm = positions_array[:, 1] * spacing___mm

        protocol = pandas.DataFrame({
            "x": x___mm,
            "y": y___mm,
            "z": None,
            "distance_on_axis_to_sample___mm": distance_on_axis_to_sample___mm,
        })
        protocol["ordinal"] = numpy.arange(0, len(protocol))
        # protocol = protocol.set_index("ordinal")  # moved to serialization step
        protocol.columns = pandas.MultiIndex.from_product([["layout"], protocol.columns])

        result = protocol, manifest
        return result
