import os
import numpy as np
import manifold3d
from manifold3d import Manifold, CrossSection, JoinType
import trimesh

def create_rounded_rect_2d(width, length, radius):
    """Creates a 2D rounded rectangle centered at (0, 0)."""
    inner = CrossSection.square([width - 2 * radius, length - 2 * radius], center=True)
    return inner.offset(radius, JoinType.Round)

def build_base():
    print("Building Base Enclosure (Premium Plan A: 66.0 x 82.0 x 18.4 mm)...")
    w_out, l_out = 66.0, 82.0
    h_base = 18.4
    r_corner = 8.0
    t_wall = 2.2
    t_floor = 2.0
    
    # 1. Main outer solid
    base_outer_cs = create_rounded_rect_2d(w_out, l_out, r_corner)
    base_solid = Manifold.extrude(base_outer_cs, h_base)
    
    # 2. Interior cavity (Target: 61.6 mm x 77.6 mm x 16.4 mm)
    w_in = 61.6
    l_in = 77.6
    r_in = max(1.0, r_corner - t_wall) # 5.8 mm
    inner_cs = create_rounded_rect_2d(w_in, l_in, r_in)
    cavity = Manifold.extrude(inner_cs, h_base - t_floor + 2.0).translate([0, 0, t_floor])
    base = base_solid - cavity
    
    # 3. Top Mating Rim Step (Recessed tongue for lid lip with 0.6mm shadow-line reveal)
    step_cut_outer = Manifold.extrude(base_outer_cs, 2.5).translate([0, 0, 16.4])
    step_inner_cs = create_rounded_rect_2d(w_out - 1.8, l_out - 1.8, r_corner - 0.9)
    step_keep = Manifold.extrude(step_inner_cs, 3.0).translate([0, 0, 15.8])
    step_cutter = step_cut_outer - step_keep
    base = base - step_cutter
    
    # Premium: Parting-line 45-degree shadow-gap chamfer (0.6 mm) around top edge
    shadow_cs_outer = base_outer_cs.offset(1.0, JoinType.Round)
    shadow_cs_inner = create_rounded_rect_2d(w_out - 1.2, l_out - 1.2, r_corner - 0.6)
    shadow_band = shadow_cs_outer - shadow_cs_inner
    shadow_groove = Manifold.extrude(shadow_band, 0.6).translate([0, 0, 15.8])
    base = base - shadow_groove
    
    # 4. USB Type-C Cutout with Smooth Cable Lead-in Pocket
    # Inner port: 13.0 mm x 7.0 mm (Target)
    usb_cs = create_rounded_rect_2d(13.0, 7.0, 1.8)
    usb_cut = Manifold.extrude(usb_cs, 8.0).rotate([90, 0, 0]).translate([0, -41.0, 6.2])
    # Outer lead-in bezel pocket (15.0 mm x 9.0 mm x 1.0 mm deep)
    usb_bezel_cs = create_rounded_rect_2d(15.4, 9.2, 2.4)
    usb_bezel = Manifold.extrude(usb_bezel_cs, 1.4).rotate([90, 0, 0]).translate([0, -40.0, 6.2])
    base = base - usb_cut - usb_bezel
    
    # 5. Prototype PCB Support Rails / Corner Ledges (PCB size: 68.0 mm x 55.0 mm)
    pcb_w, pcb_l = 55.0, 68.0
    shelf_h = 1.8
    for sx in [-(pcb_w/2), (pcb_w/2) - 4.0]:
        for sy in [-(pcb_l/2) - 3.5, (pcb_l/2) - 0.5]:
            shelf = Manifold.cube([4.0, 4.0, shelf_h]).translate([sx, sy, t_floor])
            base = base + shelf
            
    # Center PCB side guide rails
    rail_l = Manifold.cube([1.8, 30.0, shelf_h + 1.2]).translate([-(pcb_w/2) - 1.8, -15.0, t_floor])
    rail_r = Manifold.cube([1.8, 30.0, shelf_h + 1.2]).translate([(pcb_w/2), -15.0, t_floor])
    base = base + rail_l + rail_r
    
    # 6. Snap-Fit Catch Recesses in Sidewalls (X = +/- 30.8 mm, Y = +/- 18.0 mm)
    catch_pts = [
        [0.0, 0.0],
        [0.9, 1.2],
        [0.9, 2.2],
        [0.0, 2.2]
    ]
    catch_cs = CrossSection([catch_pts])
    for cy in [-18.0, 18.0]:
        c_left = Manifold.extrude(catch_cs, 7.0).rotate([90, 0, 0]).scale([-1, 1, 1]).translate([-30.8, cy + 3.5, 13.5])
        c_right = Manifold.extrude(catch_cs, 7.0).rotate([90, 0, 0]).translate([30.8, cy + 3.5, 13.5])
        base = base - c_left - c_right
        
    # 7. Dedicated Wall-Hanging Keyhole on Floor (Underside, Top Center)
    ky = 23.0
    kh_entry = Manifold.cylinder(t_floor + 0.5, 3.5, 3.5, 24).translate([0, ky, -0.1])
    kh_slot = Manifold.cube([3.8, 6.5, t_floor + 0.5], center=True).translate([0, ky + 3.25, t_floor/2])
    kh_undercut = Manifold.cube([7.6, 8.5, 1.2], center=True).translate([0, ky + 3.25, 1.4])
    base = base - kh_entry - kh_slot - kh_undercut
    
    # 8. Corner Pry Notch
    pry_notch = Manifold.cube([5.0, 2.2, 1.6], center=True).translate([31.0, 38.5, 17.5])
    base = base - pry_notch
    
    print(f"Base completed! Status: {base.status()}, Volume: {base.volume():.1f} mm3")
    return base

def build_lid():
    print("Building Lid Enclosure (Premium Plan A: 66.0 x 82.0 x 5.6 mm)...")
    w_out, l_out = 66.0, 82.0
    r_corner = 8.0
    t_roof = 1.8
    h_lip = 3.8
    clearance = 0.25
    
    # 1. Main Outer Lid Plate with 45-degree Perimeter Bevel (0.8 mm)
    # Printed face down on bed (Z=0 is top face of device)
    cs_full = create_rounded_rect_2d(w_out, l_out, r_corner)
    cs_chamfer = create_rounded_rect_2d(w_out - 1.6, l_out - 1.6, r_corner - 0.8)
    
    # Tapered first 0.8mm for ergonomic rounded chamfer edge
    plate_chamfer = Manifold.extrude(cs_chamfer, 0.8, scale_top=(w_out / (w_out - 1.6), l_out / (l_out - 1.6)))
    plate_body = Manifold.extrude(cs_full, 1.0).translate([0, 0, 0.8])
    lid_plate = plate_chamfer + plate_body
    
    # 2. Inner Mating Lip
    w_lip_out = w_out - 2 * (2.2 + clearance)  # 61.1 mm
    l_lip_out = l_out - 2 * (2.2 + clearance)  # 77.1 mm
    r_lip_out = max(1.0, r_corner - (2.2 + clearance))
    lip_outer_cs = create_rounded_rect_2d(w_lip_out, l_lip_out, r_lip_out)
    
    lip_wall_thick = 1.3
    w_lip_in = w_lip_out - 2 * lip_wall_thick
    l_lip_in = l_lip_out - 2 * lip_wall_thick
    r_lip_in = max(0.5, r_lip_out - lip_wall_thick)
    lip_inner_cs = create_rounded_rect_2d(w_lip_in, l_lip_in, r_lip_in)
    
    lip_cs = lip_outer_cs - lip_inner_cs
    lid_lip = Manifold.extrude(lip_cs, h_lip).translate([0, 0, t_roof])
    lid = lid_plate + lid_lip
    
    # 3. Four Snap-Fit Cantilever Hooks on Lip
    hook_pts = [
        [0.0, 0.0],
        [0.85, 1.2],
        [0.85, 2.2],
        [0.0, 2.2]
    ]
    hook_cs = CrossSection([hook_pts])
    for hy in [-18.0, 18.0]:
        h_left = Manifold.extrude(hook_cs, 6.5).rotate([90, 0, 0]).scale([-1, 1, 1]).translate([-w_lip_out/2, hy + 3.25, t_roof + 0.8])
        h_right = Manifold.extrude(hook_cs, 6.5).rotate([90, 0, 0]).translate([w_lip_out/2, hy + 3.25, t_roof + 0.8])
        lid = lid + h_left + h_right
        
    # 4. Premium Beveled Picture-Frame OLED Window
    # Aperture at Z=0: 23.6 x 12.6 mm, tapering to 22.2 x 11.2 mm
    oled_win_outer = create_rounded_rect_2d(23.6, 12.6, 1.5)
    oled_bevel = Manifold.extrude(oled_win_outer, 0.8, scale_top=(22.2/23.6, 11.2/12.6)).translate([0, 21.0, -0.05])
    oled_thru = Manifold.extrude(create_rounded_rect_2d(22.2, 11.2, 1.2), t_roof + h_lip + 1.0).translate([0, 21.0, 0.7])
    lid = lid - oled_bevel - oled_thru
    
    # OLED PCB Seating Frame on Underside (27.4 mm x 27.4 mm)
    for ox in [-13.7, 13.7]:
        for oy in [7.3, 34.7]:
            tab = Manifold.cylinder(2.6, 1.4, 1.4, 16).translate([ox, oy, t_roof])
            lip_dot = Manifold.sphere(0.6, 12).translate([ox * 0.94, oy * 0.96, t_roof + 2.4])
            lid = lid + tab + lip_dot
            
    # 5. RC522 Mini RFID Module Underside Frame (37.5 mm x 33.0 mm)
    rc_w, rc_l = 33.4, 37.8
    for rx in [-(rc_w/2), (rc_w/2)]:
        for ry in [-16.0 - (rc_l/2), -16.0 + (rc_l/2)]:
            rc_tab = Manifold.cylinder(3.2, 1.5, 1.5, 16).translate([rx, ry, t_roof])
            rc_lip = Manifold.sphere(0.6, 12).translate([rx * 0.93, ry * 0.96, t_roof + 3.0])
            lid = lid + rc_tab + rc_lip
            
    # 6. Status LED Apertures with Debossed Accent Rings
    for ly in [17.0, 25.0]:
        led_hole = Manifold.cylinder(t_roof + 2.0, 2.6, 2.6, 24).translate([21.0, ly, -0.5])
        led_collar = Manifold.cylinder(1.2, 3.05, 3.05, 24).translate([21.0, ly, t_roof - 0.4])
        # Premium accent ring around LED on front face (dia 7.2 mm x 0.4 mm deep)
        ring_cs = CrossSection.circle(3.6, 24) - CrossSection.circle(2.7, 24)
        accent_ring = Manifold.extrude(ring_cs, 0.45).translate([21.0, ly, -0.05])
        lid = lid - led_hole - led_collar - accent_ring
        
    # 7. Acoustic Buzzer Sound Grill
    for sy in [15.5, 18.5, 21.5, 24.5]:
        slot_cs = create_rounded_rect_2d(6.5, 1.2, 0.5)
        slot = Manifold.extrude(slot_cs, t_roof + 1.0).translate([-21.0, sy, -0.5])
        lid = lid - slot
        
    # 8. RFID Tap Target Zone on Top Face
    card_cs_outer = create_rounded_rect_2d(38.0, 28.0, 2.5)
    card_cs_inner = create_rounded_rect_2d(36.0, 26.0, 2.0)
    card_border = card_cs_outer - card_cs_inner
    card_cut = Manifold.extrude(card_border, 0.5).translate([0, -16.0, -0.05])
    lid = lid - card_cut
    
    # 4 Card Corner Indicator Dots
    for cx in [-15.0, 15.0]:
        for cy in [-25.0, -7.0]:
            corner_dot = Manifold.cylinder(0.5, 1.0, 1.0, 16).translate([cx, cy, -0.05])
            lid = lid - corner_dot
            
    # RFID / NFC Concentric Signal Waves
    wave_center_y = -16.0
    lid = lid - Manifold.cylinder(0.5, 1.1, 1.1, 20).translate([0, wave_center_y, -0.05])
    for r_wave in [4.0, 7.5, 11.0]:
        arc_outer = CrossSection.circle(r_wave, 36)
        arc_inner = CrossSection.circle(r_wave - 0.8, 36)
        ring = arc_outer - arc_inner
        cutter_half = CrossSection.square([28, 28], center=False).translate([-14, -28])
        arc_cs = ring - cutter_half
        arc_3d = Manifold.extrude(arc_cs, 0.5).translate([0, wave_center_y, -0.05])
        lid = lid - arc_3d
        
    # 9. Matching Corner Pry Notch
    pry_notch = Manifold.cube([5.0, 2.2, 1.5], center=True).translate([31.0, 38.5, 0.75])
    lid = lid - pry_notch
    
    print(f"Lid completed! Status: {lid.status()}, Volume: {lid.volume():.1f} mm3")
    return lid

def export_mesh(manifold_obj, filepath):
    mesh = manifold_obj.to_mesh()
    verts = mesh.vert_properties[:, :3]
    faces = mesh.tri_verts
    tm = trimesh.Trimesh(vertices=verts, faces=faces)
    tm.export(filepath)
    print(f"Exported: {filepath}")
    print(f"  Watertight: {tm.is_watertight}, Faces: {len(faces)}, Vertices: {len(verts)}")
    print(f"  Bounds: X={tm.bounds[0][0]:.1f}..{tm.bounds[1][0]:.1f}, Y={tm.bounds[0][1]:.1f}..{tm.bounds[1][1]:.1f}, Z={tm.bounds[0][2]:.1f}..{tm.bounds[1][2]:.1f}")
    return tm

if __name__ == '__main__':
    base = build_base()
    lid = build_lid()
    
    out_dir = r"D:\Others"
    os.makedirs(out_dir, exist_ok=True)
    
    # Export individual parts
    base_path = os.path.join(out_dir, "esp32_rfid_enclosure_base_improved.stl")
    lid_path = os.path.join(out_dir, "esp32_rfid_enclosure_lid_improved.stl")
    export_mesh(base, base_path)
    export_mesh(lid, lid_path)
    
    # Combined Print-Bed Layout (side-by-side with 8mm clearance)
    base_placed = base.translate([-37.0, 0, 0])
    lid_placed = lid.translate([37.0, 0, 0])
    combined = base_placed + lid_placed
    
    combined_path = os.path.join(out_dir, "esp32_rfid_flat_snapfit_enclosure.stl")
    export_mesh(combined, combined_path)
    print("\nALL PREMIUM PLAN-A ENCLOSURE FILES SUCCESSFULLY GENERATED!")
