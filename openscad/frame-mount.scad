frame_w = 126.5;
frame_h = 177.5;
frame_t = 5.1;

screen_w = 101;
screen_h = 126.5;
screen_t = 3;

screen_margin_l = 4.5;
screen_margin_r = 10;
screen_margin_t = 5;
screen_margin_b = 5;

camera = true;
camera_inset = 7;
camera_w = 9;
camera_h = 9.5;

// These are physical measurements of the RPi
standoff_y_sep = 58;
standoff_x_sep = 49;


aperture_w = screen_w - screen_margin_l - screen_margin_r;
aperture_h = screen_h - screen_margin_t - screen_margin_b;

aperture_offset_x = (frame_w - aperture_w) / 2;
aperture_offset_y = (frame_h - aperture_h) / 2;

recess_offset_x = aperture_offset_x - screen_margin_r;
recess_offset_y = aperture_offset_y - screen_margin_b;

bottom_t = 1;

back_t = frame_t - screen_t - bottom_t;

button_xs = [26, 47, 69, 90];
standoff_bottom_y = 66.5;
standoff_ys = [standoff_bottom_y, standoff_bottom_y + standoff_y_sep];


button_hole_w = 10;
button_hole_h = 8;
button_hole_bottom_y = 22;

button_extender_gap = 5;
button_extender_w = button_hole_w - 3;
button_extender_inner_w = button_extender_w - 3;

module mount() {
    difference() {
        cube([frame_w, frame_h, screen_t + bottom_t]);
        translate([aperture_offset_x, aperture_offset_y, -1]) {
            cube([aperture_w, aperture_h, 10]);
        };
        translate([recess_offset_x, recess_offset_y, bottom_t]) {
            cube([screen_w, screen_h, 10]);
        };
        camera_hole();
    }
}

module camera_hole() {
    if (camera) {
        translate([74, frame_h - camera_inset - camera_h, -1]) {
            cube([camera_w, camera_h, frame_t + 2]);
        }
    }
}

module eq_tri_prism(width, height) {
    linear_extrude(height) {
        polygon(points=[[0, 0], [width, 0], [width / 2, width * sin(60)]]);
    }
}

module button_extender_duct(len, wid, inner_wid) {
    // Using triangles because they should be ok to print without support
    rotate([90, 0, 0]) {
        difference() {
            // casing
            eq_tri_prism(wid, len);
            // hole
            translate([(wid - inner_wid) / 2, 0, -1]){
                eq_tri_prism(inner_wid, len+2);
            }
            // flatten the top
            translate([0, inner_wid * sin(60) + 1, -1]) {
                cube([10, 10, len + 2]);
            }
        }
    }
}

module button_extender_shaft(len, wid, chamfer_angle=60) {
    end_wid = 0.6 * button_hole_w;
    height = wid * sin(60);
    difference() {
        union() {
            // triangular prism shaft
            rotate([90, 0, 0]) {
                eq_tri_prism(wid, len);
            }
            // cuboid end
            translate([(wid - end_wid) / 2, 0, 0]){
                cube([end_wid, button_extender_gap + 2, height]);
            }
        }
        // chamfer on end of shaft
        translate([0, -len, 0]) {
            rotate([chamfer_angle, 0, 0]) {
                chamfer_length = height / sin(chamfer_angle);
                cube([wid, chamfer_length, wid]);
            }
        }

    }
}

module back_cover() {
    difference() {
        cube([frame_w, frame_h, back_t]);

        // GPIO breakout
        translate([11.5, 117, -1]) cube([14, 34, back_t + 2]);

        // central components & ribbon cable
        translate([22.5, 75, -1]) cube([30.5, 27, back_t + 2]);

        // standoffs
        for (y = standoff_ys) {
            translate([41, y, -1]) cylinder(back_t + 2, d=8, $fn=32);
        }

        // button holes
        for (x = button_xs) {
            translate([x, button_hole_bottom_y, -1]) cube([button_hole_w, button_hole_h, back_t + 2]);
        }

        // Pi Zero
        translate([60, 59, -1]) cube([37, 73, back_t + 2]);

        // Camera hole
        camera_hole();
    }
    for (x = button_xs) {
        translate([x + (button_hole_w - button_extender_w) / 2, button_hole_bottom_y - button_extender_gap, back_t]){
            button_extender_duct(
                len=button_hole_bottom_y - button_extender_gap,
                wid=button_extender_w,
                inner_wid=button_extender_inner_w
            );
        }
    }
}

module spacer() {
    outer_dia = 8;
    inner_dia = 3;
    countersink_dia = 5.8;
    countersink_depth = 4;
    thickness = 1;

    difference() {
        cylinder(d=outer_dia, h=countersink_depth + thickness, $fn=6);
        translate([0, 0, -1]) cylinder(d=inner_dia, h=countersink_depth + thickness + 1, $fn=32);
        translate([0, 0, thickness]) cylinder(d=countersink_dia, h=countersink_depth + 1, $fn=6);
    }
}

mount();

//translate([frame_w + 20, 0, 0])

//back_cover();

//button_extender_shaft(30, button_extender_inner_w - 1);

//spacer();

