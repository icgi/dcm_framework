module place_on_shell_face(
    outer_radius,
    offset = 0
) {
    translate([0, 0, -(outer_radius + offset)])
        children();
}

module emitter_profile_body(magnitude___mm) {
    translate([0, 0, -magnitude___mm])
        linear_extrude(height = magnitude___mm)
            rotate([0, 0, 90])
                children();
}

module emit(emitter, mode = "profile", eps = 0.01) {
    emitter_transform(emitter, eps)
        if (mode == "profile")
            emitter_profile_body(emitter_magnitude___mm(emitter, eps))
                children();
        else if (mode == "body")
            children();
        else
            assert(false, "mode must be \"profile\" or \"body\"");
}

module neg___quiver(emitters, mode = "profile", eps = 0.01) {
    union() {
        for (emitter = emitters)
            emit(emitter, mode, eps)
                children();
    }
}

module emitter_label_text_profile(
    index,
    text_size = 2,
    font = undef,
    surface_side = "outer",
    text_rotation___deg = 0
) {
    if (surface_side == "outer")
        mirror([1, 0, 0])
            rotate([0, 0, text_rotation___deg])
                text(
                    str(index),
                    size = text_size,
                    font = font,
                    halign = "center",
                    valign = "center"
                );
    else if (surface_side == "inner")
        rotate([0, 0, text_rotation___deg])
            text(
                str(index),
                size = text_size,
                font = font,
                halign = "center",
                valign = "center"
            );
    else
        assert(false, "surface_side must be \"outer\" or \"inner\"");
}

module emitter_label_text_body(
    index,
    label_height___mm,
    text_depth___mm = 0.4,
    text_size = 2,
    font = undef,
    surface_side = "outer",
    text_rotation___deg = 0,
    eps = 0.01
) {
    if (surface_side == "outer")
        translate([0, 0, -label_height___mm])
            linear_extrude(height = text_depth___mm + eps)
                emitter_label_text_profile(
                    index = index,
                    text_size = text_size,
                    font = font,
                    surface_side = surface_side,
                    text_rotation___deg = text_rotation___deg
                );
    else if (surface_side == "inner")
        translate([0, 0, label_height___mm - text_depth___mm])
            linear_extrude(height = text_depth___mm + eps)
                emitter_label_text_profile(
                    index = index,
                    text_size = text_size,
                    font = font,
                    surface_side = surface_side,
                    text_rotation___deg = text_rotation___deg
                );
    else
        assert(false, "surface_side must be \"outer\" or \"inner\"");
}

module emitter_label_body(
    index,
    label_height___mm,
    text_depth___mm = 0.4,
    cylinder_radius___mm = 3,
    text_size = 2,
    cylinder_fn = 24,
    font = undef,
    surface_side = "outer",
    text_rotation___deg = 0,
    eps = 0.01
) {
    difference() {
        if (surface_side == "outer")
            translate([0, 0, -label_height___mm])
                cylinder(
                    h = label_height___mm + eps,
                    r = cylinder_radius___mm,
                    $fn = cylinder_fn
                );
        else if (surface_side == "inner")
            translate([0, 0, -eps])
                cylinder(
                    h = label_height___mm + eps,
                    r = cylinder_radius___mm,
                    $fn = cylinder_fn
                );
        else
            assert(false, "surface_side must be \"outer\" or \"inner\"");

        emitter_label_text_body(
            index = index,
            label_height___mm = label_height___mm,
            text_depth___mm = text_depth___mm,
            text_size = text_size,
            font = font,
            surface_side = surface_side,
            text_rotation___deg = text_rotation___deg,
            eps = eps
        );
    }
}

module pos___emitter_labels(
    emitters,
    label_height___mm,
    text_depth___mm = 0.4,
    eps = 0.01,
    cylinder_radius___mm = 3,
    text_size = 2,
    cylinder_fn = 24,
    font = undef,
    surface_side = "outer",
    text_rotation___deg = 0
) {
    union() {
        for (i = [0 : len(emitters) - 1])
            enumeration_transform(emitters[i], surface_side = surface_side, eps = eps)
                emitter_label_body(
                    index = i,
                    label_height___mm = label_height___mm,
                    text_depth___mm = text_depth___mm,
                    cylinder_radius___mm = cylinder_radius___mm,
                    text_size = text_size,
                    cylinder_fn = cylinder_fn,
                    font = font,
                    surface_side = surface_side,
                    text_rotation___deg = text_rotation___deg,
                    eps = eps
                );
    }
}

module add_emitter_labels(
    emitters,
    label_height___mm,
    text_depth___mm = 0.4,
    eps = 0.01,
    cylinder_radius___mm = 3,
    text_size = 2,
    cylinder_fn = 24,
    font = undef,
    surface_side = "outer",
    text_rotation___deg = 0
) {
    union() {
        children();

        pos___emitter_labels(
            emitters = emitters,
            label_height___mm = label_height___mm,
            text_depth___mm = text_depth___mm,
            eps = eps,
            cylinder_radius___mm = cylinder_radius___mm,
            text_size = text_size,
            cylinder_fn = cylinder_fn,
            font = font,
            surface_side = surface_side,
            text_rotation___deg = text_rotation___deg
        );
    }
}
