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

function emitter_magnitude___mm(emitter, eps = 0.01) =
    shell_thickness___mm + 2 * eps;

module emitter_transform(emitter, eps = 0.01) {
    translate([
        emitter[LAYOUT___X],
        emitter[LAYOUT___Y],
        -eps
    ])
        children();
}

module enumeration_transform(emitter, surface_side = "outer", eps = 0.01) {
    translate([
        emitter[LAYOUT___X],
        emitter[LAYOUT___Y],
        surface_side == "outer" ? 0 : shell_thickness___mm
    ])
        children();
}

module shell() {
    translate([-shell_half_extent___mm, -shell_half_extent___mm, 0])
        cube([
            2 * shell_half_extent___mm,
            2 * shell_half_extent___mm,
            shell_thickness___mm
        ]);
}

module emitter_path(eps = 0.01) {
    cylinder(h = shell_thickness___mm + 2 * eps, d = 3);

    translate([0, 0, -1])
        cube([2, 2, 2], center = true);
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
        shell();
else
    difference() {
        shell();

        neg___quiver(emitters, mode = "body")
            emitter_path();
    }
