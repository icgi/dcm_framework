//
//  Ring transition markers
//
//  Engraves a short groove on the shell outer surface between the last emitter
//  of one ring and the first emitter of the next, marking theta transitions.
//  Angles are [step_angle___deg, na_angle___deg] pairs (azimuthal, polar), one
//  per emitter, matching the hemispherical emitter placement convention.
//

function clamp_value(value, low, high) =
    value < low ? low : (value > high ? high : value);

function vector_add(a, b) =
    [a[0] + b[0], a[1] + b[1], a[2] + b[2]];

function vector_sub(a, b) =
    [a[0] - b[0], a[1] - b[1], a[2] - b[2]];

function vector_scale(v, factor) =
    [v[0] * factor, v[1] * factor, v[2] * factor];

function vector_dot(a, b) =
    a[0] * b[0] + a[1] * b[1] + a[2] * b[2];

function vector_norm(v) =
    sqrt(vector_dot(v, v));

function vector_unit(v) =
    let(length = vector_norm(v))
    (length > 0
        ? [v[0] / length, v[1] / length, v[2] / length]
        : [0, 0, 0]);

function rotate_x_vector(v, angle___deg) =
    [
        v[0],
        v[1] * cos(angle___deg) - v[2] * sin(angle___deg),
        v[1] * sin(angle___deg) + v[2] * cos(angle___deg)
    ];

function rotate_z_vector(v, angle___deg) =
    [
        v[0] * cos(angle___deg) - v[1] * sin(angle___deg),
        v[0] * sin(angle___deg) + v[1] * cos(angle___deg),
        v[2]
    ];

// matches rotate([na_angle___deg, 0, step_angle___deg - 90])
function orient_vector(v, step_angle___deg, na_angle___deg) =
    rotate_z_vector(
        rotate_x_vector(v, na_angle___deg),
        step_angle___deg - 90
    );

// matches the emitter placement convention of the hemispherical shell
function point_from_angles(step_angle___deg, na_angle___deg, radius = 1) =
    [
        radius * sin(na_angle___deg) * cos(step_angle___deg),
        radius * sin(na_angle___deg) * sin(step_angle___deg),
        -radius * cos(na_angle___deg)
    ];

function vector_to_step_angle(v) =
    atan2(v[1], v[0]);

function vector_to_na_angle(v) =
    acos(clamp_value(-v[2] / max(1e-12, vector_norm(v)), -1, 1));

// distance from rectangle center to its edge along a unit 2D direction
function rectangle_edge_distance(half_w, half_h, dir_x, dir_y) =
    let(
        abs_x = abs(dir_x),
        abs_y = abs(dir_y),
        t_x = (abs_x < 1e-12) ? 1e12 : half_w / abs_x,
        t_y = (abs_y < 1e-12) ? 1e12 : half_h / abs_y
    )
    min(t_x, t_y);

// indices where the polar angle changes between consecutive emitters
function ring_transition_indices(angles, tolerance = 1e-6) =
    len(angles) < 2
        ? []
        : [
            for (i = [1 : len(angles) - 1])
                if (abs(angles[i][1] - angles[i - 1][1]) > tolerance)
                    i
        ];

// projects a 2D child shape inward from the outer surface
module ring_transition_radial_cut(surface_offset, cut_depth, step_angle___deg, na_angle___deg) {
    rotate([na_angle___deg, 0, step_angle___deg - 90])
        translate([0, 0, -surface_offset])
            linear_extrude(height = cut_depth, center = false, convexity = 8)
                rotate([0, 0, 90])
                    children();
}

module ring_transition_marker(
    angles,
    transition_index,
    shell_outer_radius,
    line_width___mm = 0.7,
    line_depth___mm = 0.3,
    surface_clearance___mm = 0.15,
    emitter_half_extent_x___mm = 1.5,
    emitter_half_extent_y___mm = 1.5
) {
    previous_angle = angles[transition_index - 1];
    current_angle = angles[transition_index];

    previous_step = previous_angle[0];
    previous_na = previous_angle[1];

    current_step = current_angle[0];
    current_na = current_angle[1];

    previous_point = point_from_angles(previous_step, previous_na, shell_outer_radius);
    current_point = point_from_angles(current_step, current_na, shell_outer_radius);

    previous_basis_x = orient_vector([0, 1, 0], previous_step, previous_na);
    previous_basis_y = orient_vector([-1, 0, 0], previous_step, previous_na);

    current_basis_x = orient_vector([0, 1, 0], current_step, current_na);
    current_basis_y = orient_vector([-1, 0, 0], current_step, current_na);

    forward_vector = vector_sub(current_point, previous_point);
    backward_vector = vector_sub(previous_point, current_point);

    previous_local_x = vector_dot(forward_vector, previous_basis_x);
    previous_local_y = vector_dot(forward_vector, previous_basis_y);
    previous_local_length = sqrt(previous_local_x * previous_local_x + previous_local_y * previous_local_y);

    current_local_x = vector_dot(backward_vector, current_basis_x);
    current_local_y = vector_dot(backward_vector, current_basis_y);
    current_local_length = sqrt(current_local_x * current_local_x + current_local_y * current_local_y);

    previous_dir_x = previous_local_x / max(1e-12, previous_local_length);
    previous_dir_y = previous_local_y / max(1e-12, previous_local_length);

    current_dir_x = current_local_x / max(1e-12, current_local_length);
    current_dir_y = current_local_y / max(1e-12, current_local_length);

    previous_trim = rectangle_edge_distance(
        emitter_half_extent_x___mm,
        emitter_half_extent_y___mm,
        previous_dir_x,
        previous_dir_y
    );

    current_trim = rectangle_edge_distance(
        emitter_half_extent_x___mm,
        emitter_half_extent_y___mm,
        current_dir_x,
        current_dir_y
    );

    previous_edge_point = vector_add(
        previous_point,
        vector_add(
            vector_scale(previous_basis_x, previous_dir_x * previous_trim),
            vector_scale(previous_basis_y, previous_dir_y * previous_trim)
        )
    );

    current_edge_point = vector_add(
        current_point,
        vector_add(
            vector_scale(current_basis_x, current_dir_x * current_trim),
            vector_scale(current_basis_y, current_dir_y * current_trim)
        )
    );

    edge_to_edge_vector = vector_sub(current_edge_point, previous_edge_point);
    edge_to_edge_length = vector_norm(edge_to_edge_vector);

    if (edge_to_edge_length > 1e-6) {
        midpoint_normal = vector_unit(vector_add(previous_edge_point, current_edge_point));
        midpoint_step = vector_to_step_angle(midpoint_normal);
        midpoint_na = vector_to_na_angle(midpoint_normal);

        // local square X maps to orient_vector([0, 1, 0], ...)
        // local square Y maps to orient_vector([-1, 0, 0], ...)
        midpoint_basis_x = orient_vector([0, 1, 0], midpoint_step, midpoint_na);
        midpoint_basis_y = orient_vector([-1, 0, 0], midpoint_step, midpoint_na);

        local_x = vector_dot(edge_to_edge_vector, midpoint_basis_x);
        local_y = vector_dot(edge_to_edge_vector, midpoint_basis_y);

        local_rotation = atan2(local_y, local_x);
        line_length = sqrt(local_x * local_x + local_y * local_y);

        ring_transition_radial_cut(
            shell_outer_radius + surface_clearance___mm,
            surface_clearance___mm + line_depth___mm,
            midpoint_step,
            midpoint_na
        )
            rotate([0, 0, local_rotation])
                square([line_length, line_width___mm], center = true);
    }
}

module neg___ring_transition_markers(
    angles,
    shell_outer_radius,
    line_width___mm = 0.7,
    line_depth___mm = 0.3,
    surface_clearance___mm = 0.15,
    emitter_half_extent_x___mm = 1.5,
    emitter_half_extent_y___mm = 1.5,
    tolerance = 1e-6
) {
    for (transition_index = ring_transition_indices(angles, tolerance))
        ring_transition_marker(
            angles = angles,
            transition_index = transition_index,
            shell_outer_radius = shell_outer_radius,
            line_width___mm = line_width___mm,
            line_depth___mm = line_depth___mm,
            surface_clearance___mm = surface_clearance___mm,
            emitter_half_extent_x___mm = emitter_half_extent_x___mm,
            emitter_half_extent_y___mm = emitter_half_extent_y___mm
        );
}
