"""

T* producing serializable experiment assets.

"""

import importlib.resources
import shutil
import jinja2
import numpy
import pandas
import pathlib
import matplotlib.patches
import matplotlib.pyplot as plt

from ..entities.protocol import contract


class ExcelProtocol___from___Protocol:
    """ Writes the protocol DataFrame to an Excel file. """

    @contract(
        requires=[],
        provides=[],
    )
    def __call__(self, protocol, manifest):
        output_path = pathlib.Path(manifest["path_to_experiment_container"]) / "protocol.xlsx"
        output_path.parent.mkdir(parents=True, exist_ok=True)
        protocol.to_excel(str(output_path))

        return protocol, manifest


class PlaceholderImages___from___Protocol:
    """ Generates placeholder preview images for each emitter entry. """

    IMAGE_SIZE___PX = 512
    BACKGROUND_COLOR = (40, 40, 40)
    TEXT_COLOR = (220, 220, 220)
    FONT_SIZE_TITLE = 22
    FONT_SIZE_SUBTITLE = 16

    @contract(
        requires=[("paths", "path_to_preview_image")],
        provides=[],
    )
    def __call__(self, protocol, manifest):
        from PIL import Image, ImageDraw, ImageFont

        def write_placeholder(row):
            inner_result = None

            output_path = pathlib.Path(row[("paths", "path_to_preview_image")])
            output_path.parent.mkdir(parents=True, exist_ok=True)
            name_of_file = output_path.name

            image = Image.new(
                "RGB",
                (PlaceholderImages___from___Protocol.IMAGE_SIZE___PX,
                 PlaceholderImages___from___Protocol.IMAGE_SIZE___PX),
                color=PlaceholderImages___from___Protocol.BACKGROUND_COLOR,
            )
            draw = ImageDraw.Draw(image)

            try:
                font_title = ImageFont.truetype("arial.ttf", PlaceholderImages___from___Protocol.FONT_SIZE_TITLE)
                font_subtitle = ImageFont.truetype("arial.ttf", PlaceholderImages___from___Protocol.FONT_SIZE_SUBTITLE)
            except OSError:
                font_title = ImageFont.load_default()
                font_subtitle = ImageFont.load_default()

            center_x = PlaceholderImages___from___Protocol.IMAGE_SIZE___PX // 2
            center_y = PlaceholderImages___from___Protocol.IMAGE_SIZE___PX // 2

            draw.text(
                (center_x, center_y - 16),
                "PLACEHOLDER",
                fill=PlaceholderImages___from___Protocol.TEXT_COLOR,
                font=font_title,
                anchor="mm",
            )
            draw.text(
                (center_x, center_y + 20),
                name_of_file,
                fill=PlaceholderImages___from___Protocol.TEXT_COLOR,
                font=font_subtitle,
                anchor="mm",
            )

            image.save(str(output_path), "JPEG")
            inner_result = output_path
            return inner_result

        protocol.apply(write_placeholder, axis="columns")

        return protocol, manifest


class PtychogramNavigator___from___Protocol:
    """ Renders interactive HTML navigators for stereographic and gnomonic projections. """

    MARKER_SIZE___PERCENTAGE = 3.5

    PROJECTIONS = [
        "stereographic",
        "gnomonic",
        "equidistant",
        "orthographic",
        "lambert",
    ]

    @contract(
        requires=[
            ("projection", "x_stereographic"),
            ("projection", "y_stereographic"),
            ("projection", "x_gnomonic"),
            ("projection", "y_gnomonic"),
            ("projection", "x_equidistant"),
            ("projection", "y_equidistant"),
            ("projection", "x_orthographic"),
            ("projection", "y_orthographic"),
            ("projection", "x_lambert"),
            ("projection", "y_lambert"),
            ("paths", "path_to_preview_image"),
        ],
        provides=[],
    )
    def __call__(self, protocol, manifest):
        output_container = pathlib.Path(manifest["path_to_experiment_container"])
        templates_directory = importlib.resources.files("dcm_framework") / "templates"
        jinja2_environment = jinja2.Environment(
            loader=jinja2.FileSystemLoader(str(templates_directory)),
        )
        template = jinja2_environment.get_template("PtychogramNavigator.jinja2")

        for projection in PtychogramNavigator___from___Protocol.PROJECTIONS:
            self._render_single_navigator(
                protocol=protocol,
                projection=projection,
                template=template,
                output_path=output_container / f"PtychogramNavigator___{projection.capitalize()}.html",
            )

        return protocol, manifest

    def _render_single_navigator(self, protocol, projection, template, output_path):
        column_x = f"x_{projection}"
        column_y = f"y_{projection}"
        title = f"Ptychogram Navigator ({projection.capitalize()})"

        values_x = protocol[("projection", column_x)].values.astype(numpy.float64)
        values_y = protocol[("projection", column_y)].values.astype(numpy.float64)

        max_abs = numpy.max(numpy.abs(numpy.concatenate([values_x, values_y])))
        scale___percentage = 45.0 / max_abs if max_abs > 0.0 else 1.0

        frame_markers = (
            pandas.DataFrame(
                {"x_proj": values_x, "y_proj": values_y},
                index=protocol.index,
            )
            .assign(
                left_percentage=lambda frame: (50.0 + frame["x_proj"] * scale___percentage).round(4),
                top_percentage=lambda frame: (50.0 - frame["y_proj"] * scale___percentage).round(4),
                path_to_preview_image=lambda frame: protocol[
                    ("paths", "path_to_preview_image")
                ].apply(lambda path: "/".join(pathlib.Path(path).parts[-2:])),
                ordinal=lambda frame: frame.index,
            )
        )

        buffer_for_markers = frame_markers[
            ["ordinal", "path_to_preview_image", "left_percentage", "top_percentage"]
        ].to_dict(orient="records")

        html = template.render(
            title=title,
            projection=projection,
            marker_size_percentage=PtychogramNavigator___from___Protocol.MARKER_SIZE___PERCENTAGE,
            markers=buffer_for_markers,
        )

        pathlib.Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        pathlib.Path(output_path).write_text(html, encoding="utf-8")


class IlluminatorShells___from___Protocol:
    """ Renders OpenSCAD illuminator shell assets from the protocol. """

    SHELL_TEMPLATES = [
        "illuminator_shell___base.scad",
        "illuminator_shell___hemispherical.scad",
        "illuminator_shell___planar.scad",
    ]

    @contract(
        requires=[("layout", "x"), ("layout", "y")],
        provides=[],
    )
    def __call__(self, protocol, manifest):
        output_directory = pathlib.Path(manifest["path_to_experiment_container"])
        output_directory.mkdir(parents=True, exist_ok=True)

        templates_directory = importlib.resources.files("dcm_framework") / "templates"
        jinja2_environment = jinja2.Environment(
            loader=jinja2.FileSystemLoader(str(templates_directory)),
        )

        frame_emitters = protocol.copy()
        frame_emitters.columns = [
            "___".join(levels).upper()
            for levels in protocol.columns
        ]
        for column_name in frame_emitters.select_dtypes(include="object").columns:
            frame_emitters[column_name] = frame_emitters[column_name].apply(
                lambda value: str(value).replace("\\", "/")
            )

        columns = list(frame_emitters.columns)
        emitters_scad = jinja2_environment.get_template("emitters.scad.jinja2").render(
            columns=columns,
            emitters=frame_emitters.round(6).to_dict(orient="records"),
        )
        (output_directory / "emitters.scad").write_text(emitters_scad, encoding="utf-8")

        # computes shell extent from emitter positions
        x___mm = protocol[("layout", "x")].values.astype(numpy.float64)
        y___mm = protocol[("layout", "y")].values.astype(numpy.float64)
        max_extent___mm = float(numpy.max(numpy.abs(numpy.concatenate([x___mm, y___mm]))))
        manifest["shell_half_extent___mm"] = (
            max_extent___mm
            + manifest.get("shell_thickness___mm", 1.5)
            + manifest.get("shell_edge_padding___mm", 10.0)
        )

        parameters_scad = jinja2_environment.get_template("manifest.scad.jinja2").render(
            parameters={
                key: value
                for key, value in manifest.items()
                if not isinstance(value, pathlib.PurePath)
            },
        )
        (output_directory / "manifest.scad").write_text(parameters_scad, encoding="utf-8")

        for shell_filename in IlluminatorShells___from___Protocol.SHELL_TEMPLATES:
            shutil.copy(templates_directory / shell_filename, output_directory / shell_filename)

        return protocol, manifest


class LayoutOverviewImage___from___Protocol:
    """ Renders a matplotlib layout overview plot to an image file. """

    @contract(
        requires=[("layout", "x"), ("layout", "y")],
        provides=[],
    )
    def __call__(self, protocol, manifest):
        output_path = pathlib.Path(manifest["path_to_experiment_container"]) / "layout_overview.png"
        output_path.parent.mkdir(parents=True, exist_ok=True)

        x___mm = protocol[("layout", "x")].values.astype(numpy.float64)
        y___mm = protocol[("layout", "y")].values.astype(numpy.float64)
        ordinals = protocol.index.values

        figure, axis = matplotlib.pyplot.subplots(1, 1, figsize=(10, 10))

        radii___mm = numpy.hypot(x___mm, y___mm)
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

        axis.plot(x___mm, y___mm, marker="o", color="red", linestyle="none", markersize=22)

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

        return protocol, manifest
