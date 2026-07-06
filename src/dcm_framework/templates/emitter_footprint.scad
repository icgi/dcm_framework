//
//  Emitter footprint
//
//  Defines the 3D shape subtracted from the illuminator shell at each emitter position.
//  Replace with custom geometry as needed - this module is called once per emitter
//  inside neg___quiver with mode = "body". The shape is positioned and oriented
//  by emitter_transform before subtraction. Define it centered at the origin in XY
//  and extending along +Z, with z = shell_depth___mm landing on the outer shell
//  surface (the hemispherical shell mirrors the footprint outward through the wall).
//
//  Default footprint: rectangular LED body through-pocket with four solder pad
//  clearance pockets recessed into the outer surface.
//
//  The shell templates fetch this file via use <...>, so the standalone test
//  rendering at the bottom executes only when the file is opened directly.
//

/* [LED body] */
emitter_body_width___mm = 3.7;
emitter_body_height___mm = 3.525;
// extra cut beyond the outer surface, clears shell curvature under the body rectangle
emitter_body_surface_clearance___mm = 1.0;

/* [Solder pads] */
solder_pad_width___mm = 1.1;
solder_pad_height___mm = 1.4;
// outward offset of pad centers beyond the body half width
solder_pad_overhang_x___mm = 0.48;
// inward offset of pad centers from the body half height
solder_pad_inset_y___mm = 0.741;
// pocket depth into the outer surface
solder_pad_pocket_depth___mm = 0.9;
// extra cut beyond the outer surface, clears shell curvature under the pads
solder_pad_surface_clearance___mm = 0.2;

// exposes the body dimensions to files importing this footprint via use <...>
function emitter_body_size___mm() = [emitter_body_width___mm, emitter_body_height___mm];

module emitter_body_shape(
    width___mm = emitter_body_width___mm,
    height___mm = emitter_body_height___mm
) {
    square([width___mm, height___mm], center = true);
}

module solder_pad_shape(
    body_width___mm = emitter_body_width___mm,
    body_height___mm = emitter_body_height___mm
) {
    pad_center_offsets = [
        [-body_width___mm / 2 - solder_pad_overhang_x___mm, -body_height___mm / 2 + solder_pad_inset_y___mm],
        [-body_width___mm / 2 - solder_pad_overhang_x___mm,  body_height___mm / 2 - solder_pad_inset_y___mm],
        [ body_width___mm / 2 + solder_pad_overhang_x___mm, -body_height___mm / 2 + solder_pad_inset_y___mm],
        [ body_width___mm / 2 + solder_pad_overhang_x___mm,  body_height___mm / 2 - solder_pad_inset_y___mm]
    ];

    for (pad_center = pad_center_offsets)
        translate(pad_center)
            square([solder_pad_width___mm, solder_pad_height___mm], center = true);
}

module emitter_footprint(shell_depth___mm, eps = 0.01) {
    // LED body through-pocket
    translate([0, 0, -eps])
        linear_extrude(
            height = shell_depth___mm + emitter_body_surface_clearance___mm + 2 * eps,
            convexity = 8
        )
            rotate([0, 0, 90])
                emitter_body_shape();

    // solder pad clearance pockets recessed into the outer surface
    translate([0, 0, shell_depth___mm - solder_pad_pocket_depth___mm])
        linear_extrude(
            height = solder_pad_pocket_depth___mm + solder_pad_surface_clearance___mm,
            convexity = 8
        )
            rotate([0, 0, 90])
                solder_pad_shape();
}

//
//    STANDALONE TEST RENDERING
//

// demo slab with the footprint subtracted; not executed when this file is
// imported via use <...>
demo_shell_depth___mm = 2;
demo_slab_extent___mm = 12;

difference() {
    translate([-demo_slab_extent___mm / 2, -demo_slab_extent___mm / 2, 0])
        cube([demo_slab_extent___mm, demo_slab_extent___mm, demo_shell_depth___mm]);

    emitter_footprint(demo_shell_depth___mm);
}
