// base modules call back into shell-defined emitter_transform and
// emitter_magnitude___mm, so include <...> is required to share scope
include <illuminator_shell___base.scad>;

// self-contained libraries; use <...> imports their modules and functions
// without executing their standalone test renderings
use <emitter_footprint.scad>;
use <ring_transition_markers.scad>;
use <shell_support.scad>;

// generated data files defining top-level variables; must be include <...>
include <manifest.scad>;
include <emitters.scad>;

$fs = 0.5;
$fa = 0.1;

/* [Features] */
enable_enumeration___bool = false;
enumeration_height___mm = shell_thickness___mm;
enumeration_text_depth___mm = 0.4;
enumeration_cylinder_radius___mm = 3;
enumeration_on_outer_surface___bool = true;
enumeration_font_size___mm = 2;

/* [Support] */
// renders the support from shell_support.scad together with the shell
enable_support___bool = false;

/* [Sector mode] */
// keeps only an angular wedge of the model, e.g. for test prints
enable_sector_mode___bool = false;
sector_start_angle___deg = 0;
sector_end_angle___deg = 60;

/* [Ring transition markers] */
enable_ring_transition_markers___bool = true;
ring_transition_line_width___mm = 0.7;
// engraving depth into the outer surface
ring_transition_line_depth___mm = 0.3;
ring_transition_surface_clearance___mm = 0.15;
// half extents of the emitter footprint used to trim the marker line,
// fetched from the default LED body in emitter_footprint.scad
ring_transition_emitter_half_extent_x___mm = emitter_body_size___mm()[0] / 2;
ring_transition_emitter_half_extent_y___mm = emitter_body_size___mm()[1] / 2;

neg___shell_radius = emitters[0][LAYOUT___DISTANCE_ON_AXIS_TO_SAMPLE___MM];

// derived
pos___shell_radius = neg___shell_radius + shell_thickness___mm;

// [step_angle___deg, na_angle___deg] per emitter for ring transition markers
ring_transition_angles = [
    for (emitter = emitters)
        [emitter[LAYOUT___PHI___DEG], emitter[LAYOUT___THETA___DEG]]
];

function emitter_magnitude___mm(emitter, eps = 0.01) =
    emitter[LAYOUT___DISTANCE_ON_AXIS_TO_SAMPLE___MM] + shell_thickness___mm + eps;

module shell(
    pos___shell_radius,
    neg___shell_radius,
    neg___shell_truncation_distance = sphere_truncation_depth___mm,
    align_to_base_plane = false,
    eps = 0.01
) {
    translate([
        0,
        0,
        align_to_base_plane ? neg___shell_truncation_distance : 0
    ])
        difference() {
            sphere(pos___shell_radius);
            sphere(neg___shell_radius);

            translate([
                -pos___shell_radius - eps,
                -pos___shell_radius - eps,
                -neg___shell_truncation_distance
            ])
                cube([
                    2 * (pos___shell_radius + eps),
                    2 * (pos___shell_radius + eps),
                    pos___shell_radius + neg___shell_truncation_distance + eps
                ]);
        }
}

module emitter_transform(emitter, eps = 0.01) {
    let(
        theta_polar___deg = emitter[LAYOUT___THETA___DEG],
        phi_azimuthal___deg = emitter[LAYOUT___PHI___DEG],
        yaw___deg = emitter[EMITTER_GEOMETRY___YAW___DEG],
        x_scaling = emitter[EMITTER_GEOMETRY___SCALING_X],
        y_scaling = emitter[EMITTER_GEOMETRY___SCALING_Y]
    )
        scale([x_scaling, y_scaling, 1])
            rotate([
                theta_polar___deg,
                0,
                phi_azimuthal___deg - 90 + yaw___deg
            ])
                children();
}

module enumeration_transform(emitter, surface_side = "outer", eps = 0.01) {
    emitter_transform(emitter, eps)
        if (surface_side == "outer")
            place_on_shell_face(pos___shell_radius)
                children();
        else if (surface_side == "inner")
            place_on_shell_face(neg___shell_radius)
                children();
        else
            assert(false, "surface_side must be \"outer\" or \"inner\"");
}

module illuminator_assembly() {
    union() {
        if (enable_enumeration___bool)
            add_emitter_labels(
                emitters = emitters,
                label_height___mm = enumeration_height___mm,
                text_depth___mm = enumeration_text_depth___mm,
                cylinder_radius___mm = enumeration_cylinder_radius___mm,
                text_size = enumeration_font_size___mm,
                surface_side = enumeration_on_outer_surface___bool ? "outer" : "inner"
            )
                shell(
                    pos___shell_radius,
                    neg___shell_radius
                );
        else
            difference() {
                shell(
                    pos___shell_radius,
                    neg___shell_radius
                );

                neg___quiver(emitters, mode = "body")
                    mirror([0, 0, 1])
                        emitter_footprint(pos___shell_radius);

                if (enable_ring_transition_markers___bool)
                    neg___ring_transition_markers(
                        angles = ring_transition_angles,
                        shell_outer_radius = pos___shell_radius,
                        line_width___mm = ring_transition_line_width___mm,
                        line_depth___mm = ring_transition_line_depth___mm,
                        surface_clearance___mm = ring_transition_surface_clearance___mm,
                        emitter_half_extent_x___mm = ring_transition_emitter_half_extent_x___mm,
                        emitter_half_extent_y___mm = ring_transition_emitter_half_extent_y___mm
                    );
            }

        if (enable_support___bool)
            shell_support();
    }
}

if (enable_sector_mode___bool)
    sector_clip(
        sector_start_angle___deg,
        sector_end_angle___deg,
        3 * pos___shell_radius
    )
        illuminator_assembly();
else
    illuminator_assembly();
