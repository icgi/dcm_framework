include <illuminator_shell___base.scad>;

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

neg___shell_radius = emitters[0][LAYOUT___DISTANCE_ON_AXIS_TO_SAMPLE___MM];

// derived
pos___shell_radius = neg___shell_radius + shell_thickness___mm;

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

module emitter_path() {
    translate([0, 0, -pos___shell_radius + 1.5]) {
        cylinder(h = pos___shell_radius, d = 3);
        translate([0, 0, -1])
            cube([2, 2, 2], center = true);
    }
}

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

        neg___quiver(emitters, mode = "profile")
            circle(2, $fn = 6);
    }

/*
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
            emitter_path();
    }
*/
