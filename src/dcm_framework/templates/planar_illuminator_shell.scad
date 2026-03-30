//
//  Configuration
//

thickness    = 3.0;
disk_radius  = 100;
resolution   = 60;
emboss_depth = 1;

diode___h = 3.7 - 0.015;
diode___v = 3.5 + 0.015;

display_emitter_order = false;


//
//  External position data
//

include <positions.scad>;
positions_normalized = positions;


//
//  Functions and Modules
//

module cake_cylinder(
    height,
    radius,
    slice_start    = 0,
    slice_end      = 1,
    arc_fragments  = 96,
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


//
//  Primitive shape modules
//

// Flat disk oriented with the emitter face at z = 0, back face at z = thickness.
module hollow_disk(disk_radius, thickness, resolution = resolution) {
    cylinder(h = thickness, r = disk_radius, $fn = resolution);
}


//
//  LED / emitter helper modules
//

// 2-D square footprint of a surface-mount emitter.
module square_emitter_shape(horizontal = diode___h, vertical = diode___v) {
    square([horizontal, vertical], center = true);
}

// Projects a 2-D child shape straight into the emitter face at a flat (x, y) position.
// Pocket drilled from z = 0 upward by `depth` into the disk.
module plot_position_on_disk(x, y, depth, rotation___deg = 0, scaling_x = 1, scaling_y = 1) {
    translate([x, y, 0])
        linear_extrude(height = depth + 0.01, center = false)
            rotate([0, 0, rotation___deg])
                scale([scaling_x, scaling_y, 1])
                    children();
}

// Clearance pockets for the four solder pads surrounding an emitter.
module solder_pad_clearance_flat(x, y, h, v, rotation___deg = 0) {
    corner_offsets = [
        [-h / 2 - 0.48, -v / 2 + 0.741],
        [-h / 2 - 0.48,  v / 2 - 0.741],
        [ h / 2 + 0.48, -v / 2 + 0.741],
        [ h / 2 + 0.48,  v / 2 - 0.741]
    ];

    translate([x, y, 0])
        linear_extrude(height = 1 + 0.01, center = false)
            rotate([0, 0, rotation___deg])
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
//  LED pocket subtraction - applied to disk shell
//

// Subtracts all emitter pockets and solder-pad clearances from children.
module subtract_led_pockets_flat(
    positions,
    disk_radius,
    thickness,
    emboss_depth,
    diode___h,
    diode___v
) {
    emitter_depth = thickness + emboss_depth;
    pad_depth     = 1;

    difference() {
        children();

        // Optional emitter index labels
        if (display_emitter_order)
            for (i = [0 : len(positions) - 1])
                led_label_cutter_flat(
                    index        = i,
                    x            = positions[i][0],
                    y            = positions[i][1],
                    emboss_depth = emboss_depth,
                    thickness    = thickness
                );

        // Emitter square cutouts
        for (i = [0 : len(positions) - 1])
            plot_position_on_disk(
                positions[i][0],
                positions[i][1],
                emitter_depth,
                rotation___deg = positions[i][2],
                scaling_x      = positions[i][3],
                scaling_y      = positions[i][4]
            )
                square_emitter_shape(diode___h, diode___v);

        // Solder-pad clearance pockets
        for (i = [0 : len(positions) - 1])
            solder_pad_clearance_flat(
                positions[i][0],
                positions[i][1],
                h              = diode___h * positions[i][3],
                v              = diode___v * positions[i][4],
                rotation___deg = positions[i][2]
            );
    }
}


// Constructs a flat-ended cylinder with an index number engraved into its face,
// then places it at the correct (x, y) position on the disk.
// Subtraction against the disk is the caller's responsibility.
module led_label_cutter_flat(
    index,
    x,
    y,
    emboss_depth,
    thickness,
    text_size   = 2,
    disc_radius = 3,
    resolution  = 36
) {
    translate([x, y, 0])
        difference() {
            cylinder(
                h  = emboss_depth + 1,
                r  = disc_radius,
                $fn = resolution
            );
            translate([0, 0, emboss_depth + 1 - 5 - 0.4])
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

subtract_led_pockets_flat(
    positions    = positions_normalized,
    disk_radius  = disk_radius,
    thickness    = thickness,
    emboss_depth = emboss_depth,
    diode___h    = diode___h,
    diode___v    = diode___v
)
hollow_disk(
    disk_radius = disk_radius,
    thickness   = thickness,
    resolution  = resolution
);
