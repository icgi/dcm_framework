include <emitters.scad>;

$fs = 0.5;
$fa = 0.1;

shell_thickness = 1.5;
neg___shell_radius = 50;

// derived
pos___shell_radius = neg___shell_radius + shell_thickness;

function emitter_magnitude___mm(emitter, eps = 0.01) =
    emitter[LAYOUT___DISTANCE_ON_AXIS_TO_SAMPLE___MM] + shell_thickness + eps;

module pos___shell(radius) {
    sphere(radius);
}

module neg___shell(radius) {
    sphere(radius);
}

module shell(
    pos___shell_radius,
    neg___shell_radius,
    neg___shell_truncation_distance = 0,
    align_to_base_plane = false,
    eps = 0.01
) {
    translate([
        0,
        0,
        align_to_base_plane ? neg___shell_truncation_distance : 0
    ])
        difference() {
            pos___shell(pos___shell_radius);
            neg___shell(neg___shell_radius);

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

module emitter_transform(emitter) {
    let(
        theta_polar___deg = emitter[LAYOUT___THETA___DEG],
        phi_azimuthal___deg = emitter[LAYOUT___PHI___DEG],
        rotation___deg = emitter[EMITTER_GEOMETRY___YAW___DEG],
        x_scaling = emitter[EMITTER_GEOMETRY___SCALING_X],
        y_scaling = emitter[EMITTER_GEOMETRY___SCALING_Y]
    )
        scale([x_scaling, y_scaling, 1])
            rotate([
                theta_polar___deg,
                0,
                phi_azimuthal___deg - 90 + rotation___deg
            ])

                children();
}

module emitter_volume(emitter, mode = "profile", eps = 0.01) {
    magnitude___mm = emitter_magnitude___mm(emitter, eps);

    if (mode == "profile")
        translate([0, 0, -magnitude___mm])
            linear_extrude(height = magnitude___mm)
                rotate([0, 0, 90])
                    children();
    else if (mode == "body")
        children();
    else
        assert(false, "mode must be \"profile\" or \"body\"");
}

module emit(emitter, mode = "profile", eps = 0.01) {
    emitter_transform(emitter)
        emitter_volume(emitter, mode, eps)
            children();
}

module neg___quiver(emitters, mode = "profile", eps = 0.01) {
    union() {
        for (emitter = emitters)
            emit(emitter, mode, eps)
                children();
    }
}

module emitter_path() {
    translate([0, 0, -pos___shell_radius + 1.5]) {
        union() {
            cylinder(h = pos___shell_radius, d = 3);
            translate([0, 0, -1])
                cube([2, 2, 2], center = true);
        }
    }
}


difference() {
    shell(
        pos___shell_radius,
        neg___shell_radius,
        neg___shell_truncation_distance = 0
    );

    neg___quiver(emitters, mode = "profile")
        circle(2, $fn = 6);
}

/*
difference() {
    shell(
        pos___shell_radius,
        neg___shell_radius,
        neg___shell_truncation_distance = 0
    );

    neg___quiver(emitters, mode = "body")
        emitter_path();
}
*/