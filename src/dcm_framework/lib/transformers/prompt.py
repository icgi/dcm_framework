"""

T* that capture user input from interactive prompt as the basis of experiment protocol and manifest.

"""

import numpy
import pandas
import pathlib
import questionary

from ..entities.layout import GenericShell
from ..._vendor.protocol_engine import contract

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
        interactive=True,
    )
    def __call__(self, protocol, manifest):
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

        manifest["experiment_name"] = self.workspace.name
        manifest["shell_thickness___mm"] = shell_thickness___mm
        manifest["sphere_truncation_depth___mm"] = sphere_truncation_depth___mm
        manifest["shell_edge_padding___mm"] = shell_edge_padding___mm
        manifest["initial_coordinate_system"] = initial_coordinate_system
        manifest["path_to_experiment_container"] = self.workspace

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
        interactive=True,
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
            message="Number of concentric rings",
            default="9",
        ).ask())
        spacing___mm = float(questionary.text(
            message="Spacing between rings (mm)",
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
    """ Prompts user for spiral layout with lateral or polar spacing, or loads from file. """

    @contract(
        requires=[],
        provides=[
            ("layout", "ordinal"),
            ("layout", "x"),
            ("layout", "y"),
            ("layout", "distance_on_axis_to_sample___mm")],
        interactive=True,
    )
    def __call__(self, protocol, manifest):
        initial_coordinate_system = manifest.get("initial_coordinate_system", "")
        is_polar = "Polar" in initial_coordinate_system

        layout_source = questionary.select(
            message="Layout source",
            choices=["Generate spiral", "Load from file"],
        ).ask()

        if layout_source == "Load from file":
            protocol = self._load_from_file(is_polar=is_polar)
        else:
            protocol = self._generate_spiral(is_polar=is_polar)

        result = protocol, manifest
        return result

    def _generate_spiral(self, is_polar):
        result = None

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
            message="Number of concentric rings",
            default="9",
        ).ask())

        if is_polar:
            theta_step___deg = float(questionary.text(
                message="Theta step between rings (degrees)",
                default="5"
            ).ask())
            theta_step___rad = numpy.deg2rad(theta_step___deg)

            scale_per_shell___mm = numpy.array([
                distance_on_axis_to_sample___mm * numpy.tan(shell_index * theta_step___rad)
                if shell_index > 0 else 0.0
                for shell_index in range(n_shells + 1)
            ])
            scale_per_shell___mm = numpy.array([
                scale_per_shell___mm[shell_index] / shell_index
                if shell_index > 0 else 0.0
                for shell_index in range(n_shells + 1)
            ])
        else:
            spacing___mm = float(questionary.text(
                message="Spacing between rings (mm)",
                default="7"
            ).ask())
            scale_per_shell___mm = numpy.full(n_shells + 1, spacing___mm)

        result = _build_layout_frame(
            n_steps=n_steps,
            shell_type=shell_type,
            n_shells=n_shells,
            scale_per_shell___mm=scale_per_shell___mm,
            distance_on_axis_to_sample___mm=distance_on_axis_to_sample___mm,
        )

        return result

    def _load_from_file(self, is_polar):
        result = None

        path_to_file = pathlib.Path(
            questionary.text(
                message="Path to coordinate file (csv, xlsx, tsv)",
            ).ask()
        )

        distance_on_axis_to_sample___mm = float(
            questionary.text(
                message="Distance from center of grid to sample hemisphere radius (mm)",
                default="50"
            ).ask()
        )

        frame_input = _read_tabular_file(path_to_file)
        result = _normalize_coordinate_frame(
            frame_input,
            distance_on_axis_to_sample___mm=distance_on_axis_to_sample___mm,
            is_polar=is_polar,
        )

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



def _read_tabular_file(path_to_file):
    """ Reads a tabular file into a DataFrame. Supports csv, tsv, xlsx. """
    result = None

    suffix = path_to_file.suffix.lower()
    if suffix == ".xlsx":
        result = pandas.read_excel(str(path_to_file))
    elif suffix == ".tsv":
        result = pandas.read_csv(str(path_to_file), sep="\t")
    else:
        result = pandas.read_csv(str(path_to_file))

    return result


#
#    COLUMN RECOGNITION PATTERNS
#

_CARTESIAN_COLUMN_PATTERNS = {
    "x": [("layout", "x"), ("geometry", "x___mm"), "x", "x___mm"],
    "y": [("layout", "y"), ("geometry", "y___mm"), "y", "y___mm"],
}

_POLAR_COLUMN_PATTERNS = {
    "theta": [
        ("layout", "theta___rad"), ("geometry", "theta___rad"),
        "theta___rad", "theta_rad", "theta",
    ],
    "phi": [
        ("layout", "phi___rad"), ("geometry", "phi___rad"),
        "phi___rad", "phi_rad", "phi",
    ],
    "theta_deg": [
        ("layout", "theta___deg"), ("geometry", "theta___deg"),
        "theta___deg", "theta_deg",
    ],
    "phi_deg": [
        ("layout", "phi___deg"), ("geometry", "phi___deg"),
        "phi___deg", "phi_deg",
    ],
}


def _find_column(frame, candidates):
    """ Returns the first matching column name from candidates, or None. """
    result = None

    for candidate in candidates:
        if candidate in frame.columns:
            result = candidate
            break

    return result


def _normalize_coordinate_frame(frame_input, distance_on_axis_to_sample___mm, is_polar):
    """ Converts loaded coordinates into a standard layout protocol DataFrame. """
    result = None

    x_column = _find_column(frame_input, _CARTESIAN_COLUMN_PATTERNS["x"])
    y_column = _find_column(frame_input, _CARTESIAN_COLUMN_PATTERNS["y"])

    theta_rad_column = _find_column(frame_input, _POLAR_COLUMN_PATTERNS["theta"])
    phi_rad_column = _find_column(frame_input, _POLAR_COLUMN_PATTERNS["phi"])
    theta_deg_column = _find_column(frame_input, _POLAR_COLUMN_PATTERNS["theta_deg"])
    phi_deg_column = _find_column(frame_input, _POLAR_COLUMN_PATTERNS["phi_deg"])

    has_cartesian = x_column is not None and y_column is not None
    has_polar_rad = theta_rad_column is not None and phi_rad_column is not None
    has_polar_deg = theta_deg_column is not None and phi_deg_column is not None

    if has_cartesian and not is_polar:
        x___mm = frame_input[x_column].values.astype(numpy.float64)
        y___mm = frame_input[y_column].values.astype(numpy.float64)

    elif has_polar_rad:
        theta___rad = frame_input[theta_rad_column].values.astype(numpy.float64)
        phi___rad = frame_input[phi_rad_column].values.astype(numpy.float64)
        x___mm = distance_on_axis_to_sample___mm * numpy.tan(theta___rad) * numpy.cos(phi___rad)
        y___mm = distance_on_axis_to_sample___mm * numpy.tan(theta___rad) * numpy.sin(phi___rad)

    elif has_polar_deg:
        theta___rad = numpy.deg2rad(frame_input[theta_deg_column].values.astype(numpy.float64))
        phi___rad = numpy.deg2rad(frame_input[phi_deg_column].values.astype(numpy.float64))
        x___mm = distance_on_axis_to_sample___mm * numpy.tan(theta___rad) * numpy.cos(phi___rad)
        y___mm = distance_on_axis_to_sample___mm * numpy.tan(theta___rad) * numpy.sin(phi___rad)

    elif has_cartesian:
        # falls back to cartesian even in polar mode
        x___mm = frame_input[x_column].values.astype(numpy.float64)
        y___mm = frame_input[y_column].values.astype(numpy.float64)

    else:
        raise ValueError(
            f"Cannot find coordinate columns in loaded file. "
            f"Columns present: {list(frame_input.columns)}"
        )

    result = pandas.DataFrame({
        "x": x___mm,
        "y": y___mm,
        "z": None,
        "distance_on_axis_to_sample___mm": distance_on_axis_to_sample___mm,
    })
    result["ordinal"] = numpy.arange(0, len(result))
    result.columns = pandas.MultiIndex.from_product([["layout"], result.columns])

    return result