//
//  Shell support
//
//  Standalone parametric support for the hemispherical illuminator shell:
//  an upper ring seated at the truncation plane, a lower reference ring, and
//  radial pillars spanning between them, with an alignment notch cut into the
//  +Y side of the upper ring. Shares the shell coordinate frame, so support
//  and shell align when imported into a common assembly.
//

include <manifest.scad>;
include <emitters.scad>;

$fs = 0.5;
$fa = 0.1;

eps = 0.01;

/* [Rings] */
// height of the upper ring seated at the truncation plane
ring_top_height___mm = 3;
// radial width of the upper ring (0 = match shell rim width)
ring_top_width___mm = 0;
// height of the lower reference ring
ring_bottom_height___mm = 10;
// radial width of the lower ring (0 = match shell rim width)
ring_bottom_width___mm = 0;

/* [Pillars] */
// pillar length as a fraction of the outer hemisphere radius
pillar_height_to_shell_radius_ratio = 1.25;
pillar_count = 6;
// blade thickness along the radial direction
pillar_radial_thickness___mm = 3;
// blade width along the tangential direction
pillar_tangential_width___mm = 20;

/* [Alignment notch] */
enable_alignment_notch___bool = true;
// tangential length of the diagonal slot
alignment_notch_length___mm = 20;
// square cross-section, rotated 45 degrees into a diamond
alignment_notch_section___mm = 2.8;
// y-position of the slot center (0 = just outside the upper ring outer wall)
alignment_notch_radial_position___mm = 0;

// derived from shell geometry
neg___shell_radius = emitters[0][LAYOUT___DISTANCE_ON_AXIS_TO_SAMPLE___MM];
pos___shell_radius = neg___shell_radius + shell_thickness___mm;

assert(
    sphere_truncation_depth___mm < pos___shell_radius,
    "sphere_truncation_depth___mm must be smaller than the outer shell radius"
);

truncation_plane_z = -sphere_truncation_depth___mm;

// ring radii at the truncation plane
ring_outer_radius___mm = sqrt(
    pos___shell_radius * pos___shell_radius
    - sphere_truncation_depth___mm * sphere_truncation_depth___mm
);
ring_rim_inner_radius___mm = sphere_truncation_depth___mm < neg___shell_radius
    ? sqrt(
        neg___shell_radius * neg___shell_radius
        - sphere_truncation_depth___mm * sphere_truncation_depth___mm
    )
    : 0;
rim_width___mm = ring_outer_radius___mm - ring_rim_inner_radius___mm;

effective_ring_top_width___mm =
    ring_top_width___mm > 0 ? ring_top_width___mm : rim_width___mm;
effective_ring_bottom_width___mm =
    ring_bottom_width___mm > 0 ? ring_bottom_width___mm : rim_width___mm;

// support leg length derived from the outer hemisphere radius
pillar_height___mm = pillar_height_to_shell_radius_ratio * pos___shell_radius;

pillar_radial_position___mm = ring_outer_radius___mm - pillar_radial_thickness___mm / 2;
pillar_top_z = truncation_plane_z + ring_top_height___mm;
pillar_bottom_z = pillar_top_z - pillar_height___mm;
pillar_center_z = (pillar_top_z + pillar_bottom_z) / 2;

effective_alignment_notch_radial_position___mm =
    alignment_notch_radial_position___mm > 0
        ? alignment_notch_radial_position___mm
        : ring_outer_radius___mm + alignment_notch_section___mm / 2;

module radial_array(count, radius, start_angle = 0) {
    assert(count > 0, "count must be > 0");
    assert(radius >= 0, "radius must be >= 0");

    angle_step = 360 / count;

    for (i = [0 : count - 1])
        rotate([0, 0, start_angle + i * angle_step])
            translate([radius, 0, 0])
                children();
}

module support_ring(outer_radius, width, height) {
    difference() {
        cylinder(h = height, r = outer_radius);
        translate([0, 0, -eps])
            cylinder(h = height + 2 * eps, r = outer_radius - width);
    }
}

module support_pillars() {
    radial_array(pillar_count, pillar_radial_position___mm)
        translate([0, 0, pillar_center_z])
            cube(
                [pillar_radial_thickness___mm, pillar_tangential_width___mm, pillar_height___mm],
                center = true
            );
}

module alignment_notch() {
    translate([0, effective_alignment_notch_radial_position___mm, pillar_top_z])
        rotate([90, 0, 90])
            rotate([45, 0, 0])
                cube(
                    [alignment_notch_length___mm, alignment_notch_section___mm, alignment_notch_section___mm],
                    center = true
                );
}

// empty inner volume of the hemisphere, limited to below the truncation
// plane so the upper ring seated on the rim is not consumed by the cut
module neg___shell_cavity() {
    difference() {
        sphere(neg___shell_radius);
        translate([0, 0, truncation_plane_z])
            cylinder(
                h = neg___shell_radius + sphere_truncation_depth___mm + eps,
                r = neg___shell_radius + eps
            );
    }
}

// clears the rim opening above the truncation plane; the sphere cut alone
// leaves knife-edge residue on the support feet, the cylinder trims it flush
module neg___rim_opening() {
    translate([0, 0, truncation_plane_z - eps])
        cylinder(
            h = pos___shell_radius,
            r = ring_rim_inner_radius___mm
        );
}

module shell_support() {
    difference() {
        union() {
            translate([0, 0, truncation_plane_z])
                support_ring(
                    ring_outer_radius___mm,
                    effective_ring_top_width___mm,
                    ring_top_height___mm
                );

            translate([0, 0, pillar_bottom_z])
                support_ring(
                    ring_outer_radius___mm,
                    effective_ring_bottom_width___mm,
                    ring_bottom_height___mm
                );

            support_pillars();
        }

        if (enable_alignment_notch___bool)
            alignment_notch();

        neg___shell_cavity();
        neg___rim_opening();
    }
}

// standalone rendering; not executed when this file is imported via use <...>
shell_support();

