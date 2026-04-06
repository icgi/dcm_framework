from typing import Any, Optional, Sequence, Tuple

import matplotlib.patheffects as matplotlib_patheffects
import matplotlib.pyplot as matplotlib_pyplot
import numpy
import pandas


#
#    VISUALIZATION OF LAYOUTS AND DCM EXPERIMENT PROTOCOLS
#

class GeometricLayoutVisualizer:
    """
    Provides 3D hemisphere-ray visualization and hemisphere intersection visualization on a shared hemisphere canvas.
    """

    def __init__(
        self,
        *,
        single_figure_size: Tuple[float, float] = (10.0, 8.0),
        grid_figure_size: Tuple[float, float] = (10, 12.0),
        hemisphere_alpha: float = 0.30,
        ray_color: str = "0.55",
        ray_alpha: float = 1.0,
        ray_linewidth: float = 0.8,
        point_color: str = "black",
        point_edgecolor: str = "black",
        point_edgewidth: float = 1.0,
        axis_label_color: str = "0.55",
        axis_tick_color: str = "0.55",
        axis_line_alpha: float = 0.18,
        grid_alpha: float = 0.06,
        axis_padding_fraction: float = 0.04,
        annotation_color: str = "0.15",
        annotation_alpha: float = 1.0,
        annotation_fontsize: float = 10.0,
        annotation_fontweight: str = "bold",
        annotation_stroke_color: str = "1.0",
        annotation_stroke_width: float = 2.5,
        ordinal_path_color: str = "0.20",
        ordinal_path_alpha: float = 0.55,
        ordinal_path_linewidth: float = 1.1,
        ordinal_path_linestyle: str = "--",
    ) -> None:
        self.single_figure_size = single_figure_size
        self.grid_figure_size = grid_figure_size

        self.hemisphere_alpha = hemisphere_alpha

        self.ray_color = ray_color
        self.ray_alpha = ray_alpha
        self.ray_linewidth = ray_linewidth

        self.point_color = point_color
        self.point_edgecolor = point_edgecolor
        self.point_edgewidth = point_edgewidth

        self.axis_label_color = axis_label_color
        self.axis_tick_color = axis_tick_color
        self.axis_line_alpha = axis_line_alpha
        self.grid_alpha = grid_alpha
        self.axis_padding_fraction = axis_padding_fraction

        self.annotation_color = annotation_color
        self.annotation_alpha = annotation_alpha
        self.annotation_fontsize = annotation_fontsize
        self.annotation_fontweight = annotation_fontweight
        self.annotation_stroke_color = annotation_stroke_color
        self.annotation_stroke_width = annotation_stroke_width

        self.ordinal_path_color = ordinal_path_color
        self.ordinal_path_alpha = ordinal_path_alpha
        self.ordinal_path_linewidth = ordinal_path_linewidth
        self.ordinal_path_linestyle = ordinal_path_linestyle

    #
    #    PUBLIC API
    #

    def plot_rays_3d_truncated_hemisphere(
        self,
        frame: pandas.DataFrame,
        *,
        sphere_radius: float,
        x_column: str = "x",
        y_column: str = "y",
        elevation: float = 25.0,
        azimuth: float = 135.0,
        axis: Optional[Any] = None,
        show: bool = True,
        title: str = "",
        orthographic_if_axis_aligned: bool = True,
        show_legend: bool = True,
        ray_alpha: Optional[float] = None,
        ray_color: Optional[str] = None,
    ) -> Any:
        self._require_columns(frame=frame, required_columns=(x_column, y_column))

        axis, created_figure = self._get_3d_axis(
            axis=axis, figure_size=self.single_figure_size
        )

        x_sphere, y_sphere, z_sphere = self._draw_truncated_hemisphere(
            axis=axis, sphere_radius=sphere_radius
        )

        resolved_ray_alpha = self.ray_alpha if ray_alpha is None else float(ray_alpha)
        resolved_ray_color = self.ray_color if ray_color is None else ray_color

        for _, row in frame.iterrows():
            x0 = float(row[x_column])
            y0 = float(row[y_column])
            axis.plot(
                [x0, 0.0],
                [y0, 0.0],
                [-sphere_radius, 0.0],
                linewidth=self.ray_linewidth,
                color=resolved_ray_color,
                alpha=resolved_ray_alpha,
            )

        self._scatter_points(
            axis=axis,
            x_values=frame[x_column].to_numpy(),
            y_values=frame[y_column].to_numpy(),
            z_values=numpy.ones_like(frame[x_column].to_numpy()) * (-sphere_radius),
            label="Illuminators",
            point_size=15.0,
            alpha=1.0,
        )

        # Ensures limits accommodate both the full sphere and the full ray geometry (including the origin).
        self._apply_axis_limits_for_scene(
            axis=axis,
            x_sphere=x_sphere,
            y_sphere=y_sphere,
            z_sphere=z_sphere,
            x_extra=numpy.concatenate([frame[x_column].to_numpy(), numpy.array([0.0])]),
            y_extra=numpy.concatenate([frame[y_column].to_numpy(), numpy.array([0.0])]),
            z_extra=numpy.concatenate(
                [
                    numpy.ones(len(frame), dtype=float) * (-sphere_radius),
                    numpy.array([0.0]),
                ]
            ),
        )

        self._configure_3d_axis(
            axis=axis,
            elevation=elevation,
            azimuth=azimuth,
            title=title,
            orthographic_if_axis_aligned=orthographic_if_axis_aligned,
        )

        if show_legend:
            axis.legend()

        self._finalize_show(axis=axis, show=show, created_figure=created_figure)

        return axis

    def plot_hemisphere_intersection(
        self,
        frame: pandas.DataFrame,
        *,
        sphere_radius: float,
        x_column: str = "x_3d",
        y_column: str = "y_3d",
        z_column: str = "z_3d",
        elevation: float = 25.0,
        azimuth: float = 135.0,
        point_size: float = 15.0,
        alpha: float = 1.0,
        axis: Optional[Any] = None,
        show: bool = True,
        title: str = "Hemisphere Intersection",
        orthographic_if_axis_aligned: bool = True,
        z_offset: Optional[float] = None,
        show_legend: bool = True,
    ) -> Any:
        self._require_columns(
            frame=frame, required_columns=(x_column, y_column, z_column)
        )

        axis, created_figure = self._get_3d_axis(
            axis=axis, figure_size=self.single_figure_size
        )

        x_sphere, y_sphere, z_sphere = self._draw_truncated_hemisphere(
            axis=axis, sphere_radius=sphere_radius
        )

        if z_offset is None:
            z_offset = sphere_radius

        z_values = frame[z_column].to_numpy() - float(z_offset)

        self._scatter_points(
            axis=axis,
            x_values=frame[x_column].to_numpy(),
            y_values=frame[y_column].to_numpy(),
            z_values=-z_values - sphere_radius,
            label="Hemisphere intersection",
            point_size=point_size,
            alpha=alpha,
        )

        # Keeps the canvas consistent with the ray plots; includes points so nothing clips.
        self._apply_axis_limits_for_scene(
            axis=axis,
            x_sphere=x_sphere,
            y_sphere=y_sphere,
            z_sphere=z_sphere,
            x_extra=frame[x_column].to_numpy(),
            y_extra=frame[y_column].to_numpy(),
            z_extra=z_values,
        )

        self._configure_3d_axis(
            axis=axis,
            elevation=elevation,
            azimuth=azimuth,
            title=title,
            orthographic_if_axis_aligned=orthographic_if_axis_aligned,
        )

        if show_legend:
            axis.legend()

        self._finalize_show(axis=axis, show=show, created_figure=created_figure)

        return axis

    # Backward-compatible alias (optional to keep; remove if you want a hard rename).
    def plot_fourier_projection_3d(self, *args: Any, **kwargs: Any) -> Any:
        return self.plot_hemisphere_intersection(*args, **kwargs)

    def plot_rays_3d_truncated_hemisphere_grid(
        self,
        frame: pandas.DataFrame,
        *,
        sphere_radius: float,
        x_column: str = "x",
        y_column: str = "y",
        show: bool = True,
        annotate_top_down_order: bool = True,
        annotation_start_index: int = 1,
        top_down_ray_alpha: float = 0.14,
        top_down_ray_color: str = "0.75",
        show_ordinal_path: bool = True,
    ) -> Any:
        self._require_columns(frame=frame, required_columns=(x_column, y_column))

        figure, subplots = matplotlib_pyplot.subplots(
            3, 2, squeeze=False, subplot_kw={"projection": "3d"}
        )
        figure.set_size_inches(self.grid_figure_size[0], self.grid_figure_size[1])
        figure.set_dpi(300)

        perspective_axis = subplots[0, 0]
        side_axis = subplots[1, 0]
        top_down_axis = subplots[0, 1]
        diagonal_side_axis = subplots[1, 1]
        intersection_top_down_axis = subplots[2, 0]
        intersection_side_axis = subplots[2, 1]

        self.plot_rays_3d_truncated_hemisphere(
            frame,
            sphere_radius=sphere_radius,
            x_column=x_column,
            y_column=y_column,
            axis=perspective_axis,
            show=False,
            title="Perspective Projection",
            show_legend=False,
        )

        self.plot_rays_3d_truncated_hemisphere(
            frame,
            sphere_radius=sphere_radius,
            x_column=x_column,
            y_column=y_column,
            azimuth=0.0,
            elevation=0.0,
            axis=side_axis,
            show=False,
            title="Side View Parallel Projection",
            show_legend=False,
        )

        self.plot_rays_3d_truncated_hemisphere(
            frame,
            sphere_radius=sphere_radius,
            x_column=x_column,
            y_column=y_column,
            azimuth=0.0,
            elevation=90.0,
            axis=top_down_axis,
            show=False,
            title="Top Down Parallel Projection",
            show_legend=False,
            ray_alpha=top_down_ray_alpha,
            ray_color=top_down_ray_color,
        )

        if annotate_top_down_order:
            self._annotate_point_order(
                axis=top_down_axis,
                x_values=frame[x_column].to_numpy(),
                y_values=frame[y_column].to_numpy(),
                z_value=-sphere_radius,
                start_index=annotation_start_index,
            )

        if show_ordinal_path:
            self._plot_ordinal_path(
                axis=top_down_axis,
                x_values=frame[x_column].to_numpy(),
                y_values=frame[y_column].to_numpy(),
                z_value=-sphere_radius,
            )

        # Side-view with both x and y axes presented toward the viewer (diagonal in the XY plane).
        self.plot_rays_3d_truncated_hemisphere(
            frame,
            sphere_radius=sphere_radius,
            x_column=x_column,
            y_column=y_column,
            azimuth=-90.0,
            elevation=0.0,
            axis=diagonal_side_axis,
            show=False,
            title="Diagonal Side View Parallel Projection",
            show_legend=False,
        )

        # Hemisphere intersection projections (bottom row): top-down and side view (current).
        self.plot_hemisphere_intersection(
            frame,
            sphere_radius=sphere_radius,
            axis=intersection_top_down_axis,
            azimuth=0.0,
            elevation=90.0,
            show=False,
            title="Intersection Top Down Projection",
            show_legend=False,
        )

        self.plot_hemisphere_intersection(
            frame,
            sphere_radius=sphere_radius,
            axis=intersection_side_axis,
            azimuth=0.0,
            elevation=0.0,
            show=False,
            title="Intersection Side View Parallel Projection",
            show_legend=False,
        )

        for axis in subplots.ravel():
            if axis is top_down_axis:
                continue
            self._style_3d_axis_subtle(axis=axis)

        top_down_axis.set_axis_off()

        figure.tight_layout()

        if show:
            matplotlib_pyplot.show()
            matplotlib_pyplot.close(figure)
            return None

        return figure

    #
    #    CANVAS AND STYLING
    #

    @staticmethod
    def _get_3d_axis(
        axis: Optional[Any], figure_size: Tuple[float, float]
    ) -> Tuple[Any, bool]:
        # Creates a 3D axis when none is provided.
        if axis is not None:
            return axis, False
        figure = matplotlib_pyplot.figure(figsize=figure_size)
        axis = figure.add_subplot(111, projection="3d")
        return axis, True

    def _draw_truncated_hemisphere(
        self, *, axis: Any, sphere_radius: float
    ) -> Tuple[numpy.ndarray, numpy.ndarray, numpy.ndarray]:
        # Draws a downward truncated hemisphere surface and returns the surface coordinate arrays.
        u_values = numpy.linspace(0.0, 2.0 * numpy.pi, 60)
        v_values = numpy.linspace(0.0, 0.5 * numpy.pi, 30)

        x_sphere = sphere_radius * numpy.outer(numpy.cos(u_values), numpy.sin(v_values))
        y_sphere = sphere_radius * numpy.outer(numpy.sin(u_values), numpy.sin(v_values))
        z_sphere = -sphere_radius * numpy.outer(
            numpy.ones_like(u_values), numpy.cos(v_values)
        )

        axis.plot_surface(
            x_sphere,
            y_sphere,
            z_sphere,
            rstride=1,
            cstride=1,
            alpha=self.hemisphere_alpha,
            linewidth=0,
        )

        return x_sphere, y_sphere, z_sphere

    def _configure_3d_axis(
        self,
        *,
        axis: Any,
        elevation: float,
        azimuth: float,
        title: str,
        orthographic_if_axis_aligned: bool,
    ) -> None:
        # Configures axis labeling and viewpoint and applies subtle styling.
        axis.set_xlabel("X")
        axis.set_ylabel("Y")
        axis.set_zlabel("Z")
        axis.set_title(title)
        axis.view_init(elev=elevation, azim=azimuth)

        if orthographic_if_axis_aligned and (azimuth == 0.0 or elevation == 0.0):
            axis.set_proj_type("ortho")

        self._style_3d_axis_subtle(axis=axis)

    def _style_3d_axis_subtle(self, *, axis: Any) -> None:
        # Styles axis labels, ticks, and grid to appear subtle.
        axis.xaxis.label.set_color(self.axis_label_color)
        axis.yaxis.label.set_color(self.axis_label_color)
        axis.zaxis.label.set_color(self.axis_label_color)

        axis.tick_params(colors=self.axis_tick_color, labelcolor=self.axis_tick_color)
        axis.grid(True, alpha=self.grid_alpha)

        for axis_component in (axis.xaxis, axis.yaxis, axis.zaxis):
            try:
                axis_component.line.set_color(self.axis_tick_color)
                axis_component.line.set_alpha(self.axis_line_alpha)
            except Exception:
                pass

            try:
                axis_component.pane.set_edgecolor(self.axis_tick_color)
                axis_component.pane.set_alpha(0.0)
            except Exception:
                pass

    #
    #    DATA LAYERS
    #

    def _scatter_points(
        self,
        *,
        axis: Any,
        x_values: numpy.ndarray,
        y_values: numpy.ndarray,
        z_values: numpy.ndarray,
        label: str,
        point_size: float,
        alpha: float,
    ) -> Any:
        # Scatters points with the shared marker style.
        return axis.scatter(
            x_values,
            y_values,
            z_values,
            s=point_size,
            color=self.point_color,
            marker="o",
            edgecolors=self.point_edgecolor,
            linewidths=self.point_edgewidth,
            alpha=alpha,
            label=label,
        )

    def _annotate_point_order(
        self,
        *,
        axis: Any,
        x_values: numpy.ndarray,
        y_values: numpy.ndarray,
        z_value: float,
        start_index: int,
    ) -> None:
        # Annotates points with ordinal labels using input order, with an outline for contrast.
        for offset, (x_value, y_value) in enumerate(
            zip(x_values, y_values), start=start_index
        ):
            text_artist = axis.text(
                float(x_value),
                float(y_value),
                float(z_value),
                str(offset),
                color=self.annotation_color,
                alpha=self.annotation_alpha,
                fontsize=self.annotation_fontsize,
                fontweight=self.annotation_fontweight,
                horizontalalignment="center",
                verticalalignment="center",
            )

            text_artist.set_path_effects(
                [
                    matplotlib_patheffects.Stroke(
                        linewidth=self.annotation_stroke_width,
                        foreground=self.annotation_stroke_color,
                    ),
                    matplotlib_patheffects.Normal(),
                ]
            )

    def _plot_ordinal_path(
        self,
        *,
        axis: Any,
        x_values: numpy.ndarray,
        y_values: numpy.ndarray,
        z_value: float,
    ) -> None:
        # Plots a polyline connecting ordinal points in input order.
        axis.plot(
            x_values,
            y_values,
            numpy.ones_like(x_values) * float(z_value),
            color=self.ordinal_path_color,
            alpha=self.ordinal_path_alpha,
            linewidth=self.ordinal_path_linewidth,
            linestyle=self.ordinal_path_linestyle,
        )

    #
    #    GEOMETRY AND DISPLAY UTILITIES
    #

    def _apply_axis_limits_for_scene(
        self,
        *,
        axis: Any,
        x_sphere: numpy.ndarray,
        y_sphere: numpy.ndarray,
        z_sphere: numpy.ndarray,
        x_extra: Optional[numpy.ndarray] = None,
        y_extra: Optional[numpy.ndarray] = None,
        z_extra: Optional[numpy.ndarray] = None,
    ) -> None:
        # Applies equal scaling using sphere geometry plus any additional primitives (rays/points) to avoid clipping.
        x_data = x_sphere.flatten()
        y_data = y_sphere.flatten()
        z_data = z_sphere.flatten()

        if (x_extra is not None) and (y_extra is not None) and (z_extra is not None):
            x_data = numpy.concatenate([x_data, x_extra.astype(float).ravel()])
            y_data = numpy.concatenate([y_data, y_extra.astype(float).ravel()])
            z_data = numpy.concatenate([z_data, z_extra.astype(float).ravel()])

        self._set_equal_3d_axis_scaling(
            axis=axis,
            x_data=x_data,
            y_data=y_data,
            z_data=z_data,
            padding_fraction=self.axis_padding_fraction,
        )

    @staticmethod
    def _finalize_show(*, axis: Any, show: bool, created_figure: bool) -> None:
        # Displays exactly once for internally-created figures and prevents duplicate notebook rendering.
        if show and created_figure:
            figure = axis.get_figure()
            matplotlib_pyplot.show()
            matplotlib_pyplot.close(figure)

    @staticmethod
    def _require_columns(
        frame: pandas.DataFrame, required_columns: Sequence[str]
    ) -> None:
        # Ensures that required columns exist.
        missing_columns = [
            column_name
            for column_name in required_columns
            if column_name not in frame.columns
        ]
        if missing_columns:
            raise ValueError(f"Missing required columns: {missing_columns}")

    @staticmethod
    def _set_equal_3d_axis_scaling(
        axis: Any,
        x_data: numpy.ndarray,
        y_data: numpy.ndarray,
        z_data: numpy.ndarray,
        *,
        padding_fraction: float,
    ) -> None:
        # Forces equal scaling across x, y, z dimensions with a small padding to avoid edge clipping.
        max_range = max(numpy.ptp(x_data), numpy.ptp(y_data), numpy.ptp(z_data)) / 2.0
        mid_x = (float(numpy.max(x_data)) + float(numpy.min(x_data))) / 2.0
        mid_y = (float(numpy.max(y_data)) + float(numpy.min(y_data))) / 2.0
        mid_z = (float(numpy.max(z_data)) + float(numpy.min(z_data))) / 2.0

        padding = max_range * float(padding_fraction)

        axis.set_xlim(mid_x - (max_range + padding), mid_x + (max_range + padding))
        axis.set_ylim(mid_y - (max_range + padding), mid_y + (max_range + padding))
        axis.set_zlim(mid_z - (max_range + padding), mid_z + (max_range + padding))


#
#    VISUALIZATION OF EXPERIMENT RESULTS IN THE WEB BROWSER
#

import pathlib
from typing import Any, Dict, List, Optional

import jinja2
import pandas


class HtmlExperimentRenderer:
    """
    Renders an experiment preview HTML document from a pandas DataFrame using a Jinja2 template
    loaded from a filesystem path.

    Default template location (if not provided):
      - lib/templates/experiment_preview.jinja

    Required DataFrame columns:
      - index: identifier used to build the image filename image{index}.jpg
      - x: x coordinate in pixels
      - y: y coordinate in pixels
    """

    def render(
        self,
        frame: pandas.DataFrame,
        image_dir: str,
        sort_by_index: bool = True,
        strict_undefined: bool = True,
        template_path: str | pathlib.Path | None = None,
        encoding: str = "utf-8",
    ) -> str:
        rows = self._prepare_rows(frame=frame, sort_by_index=sort_by_index)

        template_path_object = self._resolve_template_path(template_path=template_path)
        template_directory = str(template_path_object.parent)
        template_filename = template_path_object.name

        undefined_type = jinja2.StrictUndefined if strict_undefined else jinja2.Undefined
        environment = jinja2.Environment(
            loader=jinja2.FileSystemLoader(template_directory, encoding=encoding),
            autoescape=True,
            undefined=undefined_type,
        )
        template = environment.get_template(template_filename)

        return template.render(rows=rows, image_dir=image_dir)

    def write_html(self, html: str, output_path: str | pathlib.Path, encoding: str = "utf-8") -> None:
        output_path_object = pathlib.Path(output_path)
        output_path_object.parent.mkdir(parents=True, exist_ok=True)
        output_path_object.write_text(html, encoding=encoding)

    def _resolve_template_path(self, template_path: str | pathlib.Path | None) -> pathlib.Path:
        if template_path is not None:
            template_path_object = pathlib.Path(template_path)
            return self._validate_template_path(template_path_object)

        module_directory = self._get_module_directory()
        if module_directory is not None:
            candidate = module_directory / "templates" / "experiment_preview.jinja"
            if candidate.exists():
                return self._validate_template_path(candidate)

        candidate = pathlib.Path.cwd() / "lib" / "templates" / "experiment_preview.jinja"
        return self._validate_template_path(candidate)

    def _get_module_directory(self) -> Optional[pathlib.Path]:
        file_value = globals().get("__file__")
        if isinstance(file_value, str) and file_value:
            return pathlib.Path(file_value).resolve().parent
        return None

    def _validate_template_path(self, template_path_object: pathlib.Path) -> pathlib.Path:
        if not template_path_object.exists():
            raise FileNotFoundError(f"Template file not found at: {template_path_object}")
        if not template_path_object.is_file():
            raise FileNotFoundError(f"Template path is not a file: {template_path_object}")
        return template_path_object

    def _prepare_rows(self, frame: pandas.DataFrame, sort_by_index: bool) -> List[Dict[str, Any]]:
        required_columns = {"index", "x", "y"}
        missing_columns = required_columns.difference(set(frame.columns))
        if missing_columns:
            missing_text = ", ".join(sorted(missing_columns))
            raise ValueError(f"Missing required columns: {missing_text}")

        working_frame = (
            frame.loc[:, ["index", "x", "y"]]
        )

        if sort_by_index:
            working_frame = (
                working_frame.sort_values(by="index", kind="stable")
            )

        rows = (
            working_frame.to_dict(orient="records")
        )

        return rows
