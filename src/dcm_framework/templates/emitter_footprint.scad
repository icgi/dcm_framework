//
//  Emitter footprint
//
//  Defines the 3D shape subtracted from the illuminator shell at each emitter position.
//  Replace with custom geometry as needed - this module is called once per emitter
//  inside neg___quiver with mode = "body". The shape is positioned and oriented
//  by emitter_transform before subtraction, so define it centered at the origin
//  extending downward along -Z (into the shell).
//

module emitter_footprint(shell_depth___mm, eps = 0.01) {
    cylinder(h = shell_depth___mm + 2 * eps, d = 3, $fn = 24);
}
