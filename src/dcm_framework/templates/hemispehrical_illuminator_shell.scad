//
//  Configuration
//

thickness    = 1.85;
outer_radius = 100 + thickness;
resolution   = 60;
emboss_depth = 1;

diode___h = 3.7 - 0.015;
diode___v = 3.5 + 0.015;

truncation_z          = 0;
display_emitter_order = false;


//
//  External angle data
//

include <angles.scad>;
angles_normalized = angles;


//
//  Functions and Modules
//

module cake_cylinder(
    height,
    radius,
    slice_start = 0,
    slice_end = 1,
    arc_fragments = 96,
    cylinder_fragments = 96
) {
    start = _norm_turn(slice_start);
    end   = _norm_turn(slice_end);

    if (_same_turn(start, end)) {
        cylinder(h = height, r = radius, $fn = cylinder_fragments);
    } else if (end > start) {
        intersection() {
            cylinder(h = height, r = radius, $fn = cylinder_fragments);
            _sector_prism(height, radius, start, end, arc_fragments);
        }
    } else {
        union() {
            intersection() {
                cylinder(h = height, r = radius, $fn = cylinder_fragments);
                _sector_prism(height, radius, start, 1, arc_fragments);
            }
            intersection() {
                cylinder(h = height, r = radius, $fn = cylinder_fragments);
                _sector_prism(height, radius, 0, end, arc_fragments);
            }
        }
    }
}

function inner_sphere_radius(outer_radius, wall_thickness) =
    assert(outer_radius > 0, "outer_radius must be > 0")
    assert(wall_thickness > 0, "wall_thickness must be > 0")
    assert(wall_thickness < outer_radius, "wall_thickness must be < outer_radius")
    outer_radius - wall_thickness;

function cut_circle_radius(sphere_radius, depth) =
    assert(sphere_radius > 0, "sphere_radius must be > 0")
    assert(depth >= 0, "depth must be >= 0")
    assert(depth <= sphere_radius, "depth must be <= sphere_radius")
    sqrt(sphere_radius * sphere_radius - depth * depth);

// Returns [outer_cut_radius, inner_cut_radius] at a given z-depth slice.
// inner_cut_radius is 0 when the cut plane is below the inner sphere.
function hollow_hemisphere_cut_radii(outer_radius, wall_thickness, depth) =
    assert(outer_radius > 0, "outer_radius must be > 0")
    assert(wall_thickness > 0, "wall_thickness must be > 0")
    assert(wall_thickness < outer_radius, "wall_thickness must be < outer_radius")
    assert(depth >= 0, "depth must be >= 0")
    assert(depth <= outer_radius, "depth must be <= outer_radius")
    let(
        inner_radius = inner_sphere_radius(outer_radius, wall_thickness),
        outer_cut_radius = sqrt(outer_radius * outer_radius - depth * depth),
        inner_cut_radius = (depth <= inner_radius)
            ? sqrt(inner_radius * inner_radius - depth * depth)
            : 0
    )
    [outer_cut_radius, inner_cut_radius];


//
//  Primitive shape modules
//

// Hollow hemispherical shell using the negative-z half of the sphere.
module hollow_hemisphere(outer_radius, thickness, resolution = resolution) {
    inner_radius = inner_sphere_radius(outer_radius, thickness);

    difference() {
        difference() {
            sphere(r = outer_radius, $fn = resolution);
            cylinder(h = outer_radius, r = outer_radius + 15, $fn = resolution);
        }
        sphere(r = inner_radius, $fn = resolution);
    }
}

// Hollow hemisphere truncated by a plane at z = -truncation_height.
module truncated_hollow_hemisphere(
    outer_radius,
    thickness,
    truncation_height,
    resolution = resolution
) {
    difference() {
        hollow_hemisphere(
            outer_radius = outer_radius,
            thickness    = thickness,
            resolution   = resolution
        );
        translate([0, 0, -truncation_height])
            cylinder(h = outer_radius, r = outer_radius * 2);
    }
}


//
//  Transformation / clipping modules
//

// Removes everything at and above z = -truncation_height.
module truncate_from_top(
    truncation_height,
    truncating_element_height,
    truncating_radius
) {
    difference() {
        children();
        translate([0, 0, -truncation_height])
            cylinder(
                h = truncating_element_height + truncation_height,
                r = 2 * truncating_radius
            );
    }
}


//
//  LED / emitter helper modules
//

// 2-D square footprint of a surface-mount emitter.
module square_emitter_shape(horizontal = diode___h, vertical = diode___v) {
    square([horizontal, vertical], center = true);
}

// Projects a 2-D child shape along a radial vector defined by
// normalised azimuth (step_angle_norm) and altitude (na_angle_norm).
module plot_vector_from_center(length, step_angle_norm, na_angle_norm) {
    rotate([na_angle_norm, 0, step_angle_norm - 90])
        translate([0, 0, -length])
            linear_extrude(height = length, center = false)
                rotate([0, 0, 90])
                    children();
}

// Clearance pockets for the four solder pads surrounding an emitter.
module solder_pad_clearance(length, step_angle_norm, na_angle_norm, h, v) {
    corner_offsets = [
        [-h / 2 - 0.48, -v / 2 + 0.741],
        [-h / 2 - 0.48,  v / 2 - 0.741],
        [ h / 2 + 0.48, -v / 2 + 0.741],
        [ h / 2 + 0.48,  v / 2 - 0.741]
    ];

    rotate([na_angle_norm, 0, step_angle_norm - 90])
        translate([0, 0, -length - 1])
            linear_extrude(height = 1, center = false)
                rotate([0, 0, 90])
                    union() {
                        for (offset = corner_offsets)
                            translate(offset)
                                square([1.1, 1.4], center = true);
                    }
}


//
//  Utility modules
//

// Distributes children in a radial array of `count` copies at `radius`.
module radial_array(count, radius, start_angle = 0) {
    assert(count > 0, "count must be > 0");
    assert(radius >= 0, "radius must be >= 0");

    angle_step = 360 / count;

    for (i = [0 : count - 1])
        rotate([0, 0, start_angle + i * angle_step])
            translate([radius, 0, 0])
                children();
}


//
//  Hub-bracket feature
//

module hub_bracket_feature(
    form_factor___strip___width = 12.5,
    trimming_sphere___radius = 20,
    resolution = resolution,
    m3_nut_width_across_flats = 6.263,
    remove_external_part = true
) {
    w = form_factor___strip___width;

    difference() {
        // --- Positive geometry ---
        cylinder(h = w, d = w * 2, $fn = resolution);

        // --- Fastening holes ---
        translate([0, 2 * w, w / 2])
            rotate([90, 0, 0])
                union() {
                    for (side = [-1, 1])
                        translate([side * w * 0.75, 0, 0])
                            union() {
                                cylinder(h = w * 4, d = 3.25, $fn = resolution);
                                translate([0, 0, -32])
                                    cylinder(h = w * 4, d = 6, $fn = resolution);
                                translate([side * 3, 0, -8])
                                    cube([6, 6, w * 4], center = true);
                                translate([0, 0, 32])
                                    cylinder(h = w * 4, d = m3_nut_width_across_flats, $fn = 6);
                            }
                }

        // --- Extra through-hole ---
        translate([w * 0.75, 2 * w, -trimming_sphere___radius + w / 2])
            rotate([90, 0, 0])
                cylinder(h = w * 4, d = 3.25, $fn = resolution);

        // --- Internal motor-hub D-shaft cutout ---
        linear_extrude(height = w, center = false)
            difference() {
                circle(r = 2.6, $fn = 100);
                translate([0, -2.6 * 1.2])
                    square([2.6 * 2, 2], center = true);
            }

        // --- Trim external material ---
        if (remove_external_part)
            translate([0, 10, 6.25])
                cube([50, 20, 12.5], center = true);
        else
            translate([0, -9.5, 6.25])
                cube([50, 20, 12.5], center = true);
    }
}


//
//  LED pocket subtraction — applied to dome shell
//

// Subtracts all emitter pockets and solder-pad clearances from children.
module subtract_led_pockets(
    angles,
    outer_radius,
    thickness,
    emboss_depth,
    diode___h,
    diode___v
) {
    emitter_length = outer_radius + emboss_depth * thickness;
    pad_length     = outer_radius - thickness + emboss_depth * thickness - 0.7;

    difference() {
        children();

        // Optional emitter index labels
        if (display_emitter_order)
            for (i = [0 : len(angles) - 1])
                led_label_cutter(
                    index           = i,
                    step_angle_norm = angles[i][0],
                    na_angle_norm   = angles[i][1],
                    outer_radius    = outer_radius,
                    emboss_depth    = emboss_depth,
                    thickness       = thickness
                );

        // Emitter square cutouts
        for (i = [0 : len(angles) - 1])
            plot_vector_from_center(
                emitter_length,
                angles[i][0],
                angles[i][1]
            )
                square_emitter_shape(diode___h, diode___v);

        // Solder-pad clearance pockets
        for (i = [0 : len(angles) - 1])
            solder_pad_clearance(
                pad_length,
                angles[i][0],
                angles[i][1],
                h = diode___h,
                v = diode___v
            );
    }
}


// Constructs a flat-ended cylinder with an index number engraved into its
// face, then places it at the correct position on the dome surface.
// Subtraction against the dome is the caller's responsibility.
module led_label_cutter(
    index,
    step_angle_norm,
    na_angle_norm,
    outer_radius,
    emboss_depth,
    thickness,
    text_size = 2,
    disc_radius = 3,
    resolution = 36
) {
    rotate([na_angle_norm, 0, step_angle_norm - 90])
        translate([0, 0, -(outer_radius + emboss_depth)])
            difference() {
                cylinder(
                    h = thickness + emboss_depth + 1,
                    r = disc_radius,
                    $fn = resolution
                );
                translate([0, 0, thickness + emboss_depth - 6 - 0.4])
                    linear_extrude(height = 5)
                        rotate([0, 180, 0])
                            text(
                                str(index),
                                size   = text_size,
                                halign = "center",
                                valign = "center"
                            );
            }
}


// Subtracts all LED label cutters from children as a single unioned mesh.

/*
module subtract_led_pockets(
    angles,
    outer_radius,
    thickness,
    emboss_depth,
    vector_length,
    diode___h,
    diode___v,
    resolution = resolution
) {
    union() {
        render() children();
        union() {
            for (i = [0 : len(angles) - 1])
                led_label_cutter(
                    index           = i,
                    step_angle_norm = angles[i][0],
                    na_angle_norm   = angles[i][1],
                    outer_radius    = outer_radius,
                    emboss_depth    = emboss_depth,
                    thickness       = thickness,
                    text_size       = 2,
                    disc_radius     = 3,
                    resolution      = 36
                );
        }
    }
}
*/


module _sector_prism(height, radius, start_turn, end_turn, arc_fragments) {
    linear_extrude(height = height)
        polygon(
            points = _sector_points(
                radius,
                start_turn * 360,
                end_turn * 360,
                arc_fragments
            )
        );
}

function _sector_points(radius, start_deg, end_deg, arc_fragments) =
    concat(
        [[0, 0]],
        [
            for (i = [0 : max(1, ceil(arc_fragments * (end_deg - start_deg) / 360))])
                let(
                    steps = max(1, ceil(arc_fragments * (end_deg - start_deg) / 360)),
                    a = start_deg + (end_deg - start_deg) * i / steps
                )
                [radius * cos(a), radius * sin(a)]
        ]
    );

function _norm_turn(t) =
    let(v = t % 1)
    (v < 0 ? v + 1 : v);

function _same_turn(a, b) = abs(a - b) < 1e-9;


//
//  Main Assembly
//

truncate_from_top(
    truncation_height         = truncation_z,
    truncating_element_height = outer_radius * 10,
    truncating_radius         = 2 * outer_radius
)
subtract_led_pockets(
    angles        = angles_normalized,
    outer_radius  = outer_radius,
    thickness     = thickness,
    emboss_depth  = emboss_depth,
    diode___h     = diode___h,
    diode___v     = diode___v
)
truncated_hollow_hemisphere(
    outer_radius      = outer_radius,
    thickness         = thickness,
    truncation_height = 5,
    resolution        = resolution
);