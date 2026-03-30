import base64
import datetime
import random
import uuid

import cv2
import shutil
import fire
import matplotlib.patches
import matplotlib.pyplot
import jinja2
import numpy
import pandas
import pathlib
import questionary
import shapely

try:
    import friendly_names as _friendly_names_module

    _has_friendly_names = True
except ImportError:
    _has_friendly_names = False


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


class DcmFrameworkRunner:
    def __init__(self):
        self.context = {}

    def build_experiment(self):

        self.context["path_to_experiment_container"] = pathlib.Path(
            questionary.text(
                message="Path to experiment container (folder)",
                default=".",
            ).ask()
        )

        self.context["experiment_name"] = questionary.text(
            message="Experiment name",
            default=DcmFrameworkRunner.util.generate_experiment_name_suggestion(),
        ).ask()

        self.context["path_to_experiment_container"] = (
            self.context["path_to_experiment_container"]
            / self.context["experiment_name"]
        )

        self.context["mode"] = questionary.select(
            message="Choose a shell shape", choices=["Planar", "Hemispherical"]
        ).ask()

        illuminator_choice = questionary.select(
            message="Choose an illuminator layout",
            choices=[
                "Rectangular Grid",
                "Spiral - Square rings",
                "Spiral - Hexagonal rings",
                "Spiral - Octagonal rings",
                "Spiral - Circular rings",
            ],
        ).ask()
        self.context["illuminator_choice"] = illuminator_choice

        self.context["distance_on_axis_to_sample___mm"] = float(
            questionary.text(
                message="Distance from center of grid to sample hemisphere radius (mm)",
            ).ask()
        )

        if illuminator_choice == "Rectangular Grid":
            self.context["n_emitters_x"] = float(
                questionary.text(
                    message="Grid layout. Number of emitters in x-direction (total)",
                ).ask()
            )
            self.context["n_emitters_y"] = float(
                questionary.text(
                    message="Grid layout. Number of emitters in y-direction (total)",
                ).ask()
            )
            self.context["spacing___mm"] = float(
                questionary.text(
                    message="Grid layout. Spacing between emitters (mm)",
                ).ask()
            )
        else:
            spiral_presets = {
                "Spiral - Square rings": (4, "polygon"),
                "Spiral - Hexagonal rings": (6, "polygon"),
                "Spiral - Octagonal rings": (8, "polygon"),
                "Spiral - Circular rings": (6, "circle"),
            }
            n_steps, shell_type = spiral_presets[illuminator_choice]
            self.context["n_steps"] = n_steps
            self.context["shell_type"] = shell_type
            self.context["n_shells"] = int(
                questionary.text(
                    message="Spiral layout. Number of concentric shells",
                    default="4",
                ).ask()
            )
            self.context["spacing___mm"] = float(
                questionary.text(
                    message="Spiral layout. Spacing between shells (mm)",
                ).ask()
            )

        output_container = pathlib.Path(self.context["path_to_experiment_container"])

        output_container.mkdir(parents=True, exist_ok=True)

        if self.context["illuminator_choice"] == "Rectangular Grid":
            protocol = DcmFrameworkRunner.util.construct_grid(context=self.context)
        else:
            protocol = DcmFrameworkRunner.util.construct_spiral_layout(context=self.context)
        protocol = DcmFrameworkRunner.util.compute_stereographic_projection(
            protocol=protocol
        )
        protocol = DcmFrameworkRunner.util.compute_gnomonic_projection(
            protocol=protocol
        )
        protocol = DcmFrameworkRunner.util.compute_geometry_angles(protocol=protocol)
        protocol = DcmFrameworkRunner.util.render_paths(
            context=self.context, protocol=protocol
        )
        protocol = DcmFrameworkRunner.util.set_default_values_for_cad(protocol=protocol)

        protocol.to_excel(output_container / "protocol.xlsx")

        DcmFrameworkRunner.util.generate_placeholder_images(protocol)

        DcmFrameworkRunner.util.render_projection_navigator(
            protocol,
            "stereographic",
            output_container / "PtychogramNavigator___Stereographic.html",
        )
        DcmFrameworkRunner.util.render_projection_navigator(
            protocol,
            "gnomonic",
            output_container / "PtychogramNavigator___Gnomonic.html",
        )

        DcmFrameworkRunner.util.render_positions_scad(
            protocol,
            output_container / "positions.scad",
        )

        DcmFrameworkRunner.util.render_layout_overview(
            protocol,
            output_container / "layout_overview.png",
        )

    class util:
        @staticmethod
        def hello():
            print("hello.")

        @staticmethod
        def construct_grid(context, protocol=None):
            n_x = int(context["n_emitters_x"])
            n_y = int(context["n_emitters_y"])
            spacing___mm = context["spacing___mm"]

            x_positions___mm = numpy.linspace(
                -(n_x - 1) / 2 * spacing___mm,
                (n_x - 1) / 2 * spacing___mm,
                n_x,
            )
            y_positions___mm = numpy.linspace(
                -(n_y - 1) / 2 * spacing___mm,
                (n_y - 1) / 2 * spacing___mm,
                n_y,
            )

            grid_x___mm, grid_y___mm = numpy.meshgrid(
                x_positions___mm, y_positions___mm
            )

            protocol = pandas.DataFrame(
                {
                    "x": grid_x___mm.ravel(),
                    "y": grid_y___mm.ravel(),
                    "z": None,
                    "distance_on_axis_to_sample___mm": context[
                        "distance_on_axis_to_sample___mm"
                    ],
                }
            )

            protocol["ordinal"] = numpy.arange(0, len(protocol))

            protocol = protocol.set_index("ordinal")

            protocol.columns = pandas.MultiIndex.from_product(
                [["layout"], protocol.columns],
            )

            return protocol

        @staticmethod
        def construct_spiral_layout(context):
            result = None

            n_shells = int(context["n_shells"])
            n_steps = int(context["n_steps"])
            shell_type = context["shell_type"]
            spacing___mm = context["spacing___mm"]
            distance_on_axis_to_sample___mm = context["distance_on_axis_to_sample___mm"]

            buffer_for_positions = []
            for radius in range(n_shells + 1):
                shell = GenericShell(radius=radius, order=n_steps, shell_type=shell_type)
                buffer_for_positions.extend(list(shell.positions.coords)[:-1])

            positions_array = numpy.array(buffer_for_positions)
            x___mm = positions_array[:, 0] * spacing___mm
            y___mm = positions_array[:, 1] * spacing___mm

            protocol = pandas.DataFrame(
                {
                    "x": x___mm,
                    "y": y___mm,
                    "z": None,
                    "distance_on_axis_to_sample___mm": distance_on_axis_to_sample___mm,
                }
            )

            protocol["ordinal"] = numpy.arange(0, len(protocol))
            protocol = protocol.set_index("ordinal")
            protocol.columns = pandas.MultiIndex.from_product(
                [["layout"], protocol.columns],
            )

            result = protocol
            return result

        @staticmethod
        def compute_stereographic_projection(protocol):
            result = None

            x___mm = protocol[("layout", "x")].values
            y___mm = protocol[("layout", "y")].values

            z_distance___mm = protocol[
                ("layout", "distance_on_axis_to_sample___mm")
            ].values

            magnitude = numpy.sqrt(x___mm**2 + y___mm**2 + z_distance___mm**2)
            nx = x___mm / magnitude
            ny = y___mm / magnitude
            nz = z_distance___mm / magnitude

            x_stereographic = nx / (1 + nz)
            y_stereographic = ny / (1 + nz)

            frame_projection = pandas.DataFrame(
                {
                    "x_stereographic": x_stereographic,
                    "y_stereographic": y_stereographic,
                },
                index=protocol.index,
            )
            frame_projection.columns = pandas.MultiIndex.from_product(
                [["projection"], frame_projection.columns],
            )

            result = pandas.concat([protocol, frame_projection], axis=1)

            return result

        @staticmethod
        def render_projection_navigator(protocol, projection, output_path):
            result = None

            marker_size_percentage = 3.5
            column_x = f"x_{projection}"
            column_y = f"y_{projection}"
            title = f"Ptychogram Navigator ({projection.capitalize()})"

            values_x = protocol[("projection", column_x)].values
            values_y = protocol[("projection", column_y)].values

            max_abs = numpy.max(numpy.abs(numpy.concatenate([values_x, values_y])))
            scale_percentage = 45.0 / max_abs if max_abs > 0 else 1.0

            frame_markers = pandas.DataFrame(
                {"x_proj": values_x, "y_proj": values_y},
                index=protocol.index,
            )
            frame_markers = frame_markers.assign(
                left_percentage=lambda frame: (
                    50 + frame["x_proj"] * scale_percentage
                ).round(4),
                top_percentage=lambda frame: (
                    50 - frame["y_proj"] * scale_percentage
                ).round(4),
                path_to_preview_image=lambda frame: protocol[
                    ("paths", "path_to_preview_image")
                ].apply(lambda path: "/".join(pathlib.Path(path).parts[-2:])),
                ordinal=lambda frame: frame.index,
            )
            buffer_for_markers = frame_markers[
                [
                    "ordinal",
                    "path_to_preview_image",
                    "left_percentage",
                    "top_percentage",
                ]
            ].to_dict(orient="records")

            templates_dir = pathlib.Path(__file__).parent / "templates"
            jinja2_environment = jinja2.Environment(
                loader=jinja2.FileSystemLoader(str(templates_dir)),
            )
            template = jinja2_environment.get_template("PtychogramNavigator.jinja2")

            html = template.render(
                title=title,
                projection=projection,
                marker_size_percentage=marker_size_percentage,
                markers=buffer_for_markers,
            )

            pathlib.Path(output_path).write_text(html, encoding="utf-8")
            result = output_path

            return result

        @staticmethod
        def render_positions_scad(protocol, output_path):
            result = None

            output_dir = pathlib.Path(output_path).parent
            templates_dir = pathlib.Path(__file__).parent / "templates"
            jinja2_environment = jinja2.Environment(
                loader=jinja2.FileSystemLoader(str(templates_dir)),
            )

            frame_positions = pandas.DataFrame(
                {
                    "x___mm": protocol[("layout", "x")].round(6).values,
                    "y___mm": protocol[("layout", "y")].round(6).values,
                    "rotation___deg": protocol[("cad___emitter_slot", "rotation___deg")].values,
                    "scaling_x": protocol[("cad___emitter_slot", "scaling_x")].values,
                    "scaling_y": protocol[("cad___emitter_slot", "scaling_y")].values,
                },
                index=protocol.index,
            )
            positions_scad = jinja2_environment.get_template("positions.scad.jinja2").render(
                positions=frame_positions.to_dict(orient="records")
            )
            pathlib.Path(output_path).write_text(positions_scad, encoding="utf-8")

            frame_angles = pandas.DataFrame(
                {
                    "phi_deg": protocol[("geometry", "phi_deg")].round(6).values,
                    "theta_deg": protocol[("geometry", "theta_deg")].round(6).values,
                    "rotation___deg": protocol[("cad___emitter_slot", "rotation___deg")].values,
                    "scaling_x": protocol[("cad___emitter_slot", "scaling_x")].values,
                    "scaling_y": protocol[("cad___emitter_slot", "scaling_y")].values,
                },
                index=protocol.index,
            )
            angles_scad = jinja2_environment.get_template("angles.scad.jinja2").render(
                angles=frame_angles.to_dict(orient="records")
            )
            (output_dir / "angles.scad").write_text(angles_scad, encoding="utf-8")

            for shell_filename in [
                "hemispehrical_illuminator_shell.scad",
                "planar_illuminator_shell.scad",
            ]:
                shutil.copy(templates_dir / shell_filename, output_dir / shell_filename)

            result = output_path
            return result

        @staticmethod
        def render_layout_overview(protocol, output_path):
            result = None

            x___mm = protocol[("layout", "x")].values
            y___mm = protocol[("layout", "y")].values
            ordinals = protocol.index.values

            figure, axis = matplotlib.pyplot.subplots(1, 1, figsize=(10, 10))

            radii___mm = numpy.sqrt(x___mm**2 + y___mm**2)
            for unique_radius___mm in numpy.unique(radii___mm.round(4)):
                axis.add_patch(
                    matplotlib.patches.Circle(
                        (0, 0),
                        radius=unique_radius___mm,
                        facecolor="none",
                        edgecolor="black",
                        alpha=0.1,
                    )
                )

            axis.plot(x___mm, y___mm, marker="o", color="red", markersize=22)

            for ordinal, x, y in zip(ordinals, x___mm, y___mm):
                axis.text(
                    x=x, y=y, s=str(ordinal),
                    va="center", ha="center",
                    color="white", fontsize=10,
                )

            axis.axhline(0, color="black", linewidth=0.5, alpha=0.25, linestyle="dashed")
            axis.axvline(0, color="black", linewidth=0.5, alpha=0.25, linestyle="dashed")

            axis.set_aspect("equal")
            axis.axis("off")

            figure.savefig(str(output_path), dpi=150, bbox_inches="tight")
            matplotlib.pyplot.close(figure)

            result = output_path
            return result

        @staticmethod
        def compute_gnomonic_projection(protocol):
            result = None

            x___mm = protocol[("layout", "x")].values
            y___mm = protocol[("layout", "y")].values
            z_distance___mm = protocol[
                ("layout", "distance_on_axis_to_sample___mm")
            ].values

            magnitude = numpy.sqrt(x___mm**2 + y___mm**2 + z_distance___mm**2)
            nx = x___mm / magnitude
            ny = y___mm / magnitude
            nz = z_distance___mm / magnitude

            x_gnomonic = nx / nz
            y_gnomonic = ny / nz

            frame = pandas.DataFrame(
                {"x_gnomonic": x_gnomonic, "y_gnomonic": y_gnomonic},
                index=protocol.index,
            )
            frame.columns = pandas.MultiIndex.from_product(
                [["projection"], frame.columns],
            )

            result = pandas.concat([protocol, frame], axis=1)

            return result

        @staticmethod
        def compute_geometry_angles(protocol):
            """Appends theta and phi spherical angles to the protocol under the 'geometry' group."""
            result = None

            x___mm = protocol[("layout", "x")].values
            y___mm = protocol[("layout", "y")].values
            z_distance___mm = protocol[
                ("layout", "distance_on_axis_to_sample___mm")
            ].values

            radial_distance___mm = numpy.sqrt(x___mm**2 + y___mm**2)
            theta_rad = numpy.arctan2(radial_distance___mm, z_distance___mm)

            phi_rad = numpy.arctan2(y___mm, x___mm) % (2 * numpy.pi)

            theta_deg = numpy.degrees(theta_rad)
            phi_deg = numpy.degrees(phi_rad)

            frame_geometry = pandas.DataFrame(
                {
                    "theta_rad": theta_rad,
                    "phi_rad": phi_rad,
                    "theta_deg": theta_deg,
                    "phi_deg": phi_deg,
                },
                index=protocol.index,
            )
            frame_geometry.columns = pandas.MultiIndex.from_product(
                [["geometry"], frame_geometry.columns],
            )

            result = pandas.concat([protocol, frame_geometry], axis=1)

            return result

        @staticmethod
        def render_paths(context, protocol):
            path_to_experiment_container = pathlib.Path(
                context["path_to_experiment_container"]
            )

            frame = pandas.DataFrame()

            frame[("paths", "path_to_image")] = protocol.apply(
                lambda entry: path_to_experiment_container
                / f"default/image_{entry.name}.tif",
                axis="columns",
            )

            frame[("paths", "path_to_preview_image")] = protocol.apply(
                lambda entry: path_to_experiment_container
                / f"preview/image_{entry.name}.jpg",
                axis="columns",
            )

            result = pandas.concat([protocol, frame], axis="columns")

            return result

        @staticmethod
        def set_default_values_for_cad(protocol):
            frame = pandas.DataFrame(index=protocol.index)

            frame[("cad___emitter_slot", "rotation___deg")] = 0.0
            frame[("cad___emitter_slot", "scaling_x")] = 1.0
            frame[("cad___emitter_slot", "scaling_y")] = 1.0

            result = pandas.concat([protocol, frame], axis="columns")

            return result

        #
        #    HELPER METHODS FOR DEVELOPMENT
        #

        @staticmethod
        def generate_experiment_name_suggestion():
            """Builds the default experiment name shown in the prompt."""
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

            result = f"experiment___{identifier}___{random_integer:03d}___{date_string}"

            return result

        @staticmethod
        def generate_placeholder_images(protocol):
            result = None

            image_size_px = 512
            background_color = (40, 40, 40)
            text_color = (220, 220, 220)
            font = cv2.FONT_HERSHEY_SIMPLEX
            font_scale = 1.0
            line_thickness = 2

            def write_placeholder(row):
                inner_result = None

                output_path = pathlib.Path(row[("paths", "path_to_preview_image")])
                output_path.parent.mkdir(parents=True, exist_ok=True)
                name_of_file = output_path.name

                image = numpy.full(
                    (image_size_px, image_size_px, 3),
                    background_color[0],
                    dtype=numpy.uint8,
                )

                for line_index, text in enumerate(["PLACEHOLDER", name_of_file]):
                    (text_width, text_height), _ = cv2.getTextSize(
                        text, font, font_scale, line_thickness
                    )
                    x = (image_size_px - text_width) // 2
                    y = (
                        image_size_px // 2
                        + (line_index - 1) * (text_height + 16)
                        + text_height // 2
                    )
                    cv2.putText(
                        image,
                        text,
                        (x, y),
                        font,
                        font_scale,
                        text_color,
                        line_thickness,
                        cv2.LINE_AA,
                    )

                inner_result = cv2.imwrite(str(output_path), image)

                return inner_result

            result = protocol.apply(write_placeholder, axis="columns")

            return result


def main():
    fire.Fire(DcmFrameworkRunner)


if __name__ == "__main__":
    main()
