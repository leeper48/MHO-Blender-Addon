"""
MHO Actions
-----------
Toolset for MHO modding work, packaged as a Blender 5.x Extension
(metadata lives in blender_manifest.toml, not a bl_info dict).

Includes:
  1. FBX -> Actions: batch-imports animated FBX exports from
     MHModelEditor and converts each into a reusable Action, saved
     into an "action library" .blend file.
  2. Actions -> NLA: appends every Action from that library .blend
     into the current file and pushes each one down onto a chosen
     armature as its own NLA track/strip. If the armature has no NLA
     tracks yet, an "Add Root Pose Track" button appears first - it
     keys the armature's neutral pose at frame 1 and pushes that down
     as a starting 'Root' track, so you don't have to remember to do
     it manually before appending the rest. Below that, "Isolate to
     Root Pose" mutes every NLA track except 'Root' (remembering
     which were active) so the armature shows a clean rest pose -
     "Restore NLA Tracks" (which replaces the button once isolated)
     puts them back exactly, mutes and current frame included.
     Below that, "Offset" builds (or updates) an "Offset" action
     that shifts the bone(s) directly under "root" by a chosen
     amount along a chosen world-space axis (X/Y/Z - pick whichever
     one actually corresponds to scene-vertical for a given
     armature/import convention) - their children follow
     automatically via forward kinematics, so only the top of each
     chain needs to move, not every bone (offsetting every bone
     compounds the shift once per level of hierarchy depth and
     distorts the mesh) - and pushes it onto a new NLA track at the
     very top of the stack with additive ("Add"/"Combine") blending -
     a way to correct a flying/hover animation that sits too high,
     low, or off to one side, without touching the animation itself.
     Re-running it with a different axis/amount updates the same
     track/action in place rather than piling up duplicates.
  3. Prepare Viewport: sets every armature's viewport display type to
     "Stick", sets the Weight Paint overlay opacity/Zero Weights
     display, and switches the viewport to Material Preview shading,
     in one click.
  4. Weight Transfer: transfers vertex group weights from a source
     mesh to a target mesh (nearest face interpolated), matching
     groups onto the target by name, optionally smooths the result,
     can add an Armature modifier to the target pointed at the
     same armature as the source, and can sort the target's vertex
     groups to match that armature's bone hierarchy.
  5. MFF Model Prep: two steps. (a) Scale & Rotate - scales up,
     rotates 90 on Z, and applies transforms on each selected mesh
     part individually (no join), so tiny imported parts become
     visible enough to pick which ones belong together. (b) Join &
     Merge - joins the selected parts into one object, unparents it,
     merges overlapping vertices at a tight threshold, and strips
     custom split normals so shading rebuilds clean.
  6. Symmetrical Sculpt Adjust: enters Sculpt Mode on the selected
     mesh, switches to the Elastic Deform (Elastigrab) tool, and sets
     sculpt symmetry to whichever single axis (X, Y, or Z) is picked
     in the panel.
  7. Shader Slot Maps: per material slot, lets you assign a diffuse
     image (-> Base Color), a normal image (-> Normal Map node ->
     Normal), a specular mask image (Separate RGB/Color: R ->
     Roughness [x -0.5, clamped], G -> Metallic [x 0.5, clamped],
     B -> Specular IOR Level), and a spec color image (-> Specular
     Tint), then builds/updates the node graph on demand.
  8. Export for Game: expands the current selection to its full
     connected hierarchy (parents and children), then exports an FBX
     file next to the current .blend using game-ready export settings
     (selection only, all object types, -Z Forward/Y Up, baked
     transforms, animation baked with all bones keyed). Below it,
     "Batch Export Animations" exports one FBX per NLA animation
     track on the target armature (skipping tracks named "Offset" or
     "Root"), named after each track, into a "Blend_anims" subfolder
     - using the same game-ready settings. This relies on standard
     NLA Replace blending: every individual clip track normally uses
     Replace, so whichever unmuted track sits highest in the stack
     completely overrides everything below it. The tool unmutes
     every track, then walks the list from the top down exporting
     one clip at a time and muting each as it finishes (revealing
     the next one down), while "Offset" (additive) and "Root" (the
     base rest pose) stay unmuted throughout so they keep layering
     under/over every clip exactly as they normally would. Each
     clip's export range matches its own strip, not the whole scene
     range. Every track's original mute state and the scene's frame
     range are restored afterward.
  9. Texture Baker: for each selected mesh object separately (one
     atlas per object, no merging across objects), duplicates it (or,
     if "Selected Faces Only" is on, just that object's selected
     faces), welds unconnected verts (Merge Distance from MFF Model
     Prep), then normalizes its original UV map to a "MHO_Source"
     layer and adds a fresh "Atlas" UV layer alongside it (removed
     again once baking is done, leaving just Atlas). Atlas is
     unwrapped by auto-marking seams - reusing the island boundaries
     already implicit in MHO_Source's original per-material unwrap,
     plus every material-boundary edge - then running a real Unwrap,
     which produces far more coherent, less fragmented islands than
     Smart UV Project (which ignores seams entirely) or a geometric
     sharp-angle threshold (which badly over-fragments low-poly
     curved surfaces). Cycles then bakes Diffuse (D), Normal (N),
     Spec Mask (SM), and Spec Color (SC) - sourced from MHO_Source,
     written into Atlas - into one shared set of textures at their
     own chosen resolutions (default 2048 each). The four PNGs per
     object (named "<object>_D.png" etc.) are saved into a "textures"
     subfolder next to the .blend, and a single merged material is
     assigned to each new "<object>_Atlas" object - the source
     objects are left untouched. "Bake to Atlas (Reduced)" does the
     same on a reduced-polycount copy: flat areas planar-dissolved
     (optional), then collapsed to the Quality fraction of the
     original triangles, and every channel is baked high-to-low
     (selected-to-active) from the original onto it, so the removed
     detail lands in the Normal map; ray distances come from the
     measured high/low gap. Saved as "<object>_Reduced_D.png" etc. on
     a "<object>_Reduced_Atlas" object. "Bake Top-Down (Flat)" instead bakes
     every selected mesh together, as seen straight down from above,
     onto one single-face quad fitted to their X/Y bounds (a ground
     plane): selected-to-active from a quad just above the highest
     point, rays cast straight down. Same four channels, saved as
     "<active>_TopDown_D.png" etc., sized to the quad's aspect (short
     side rounded up to a power of two); Diffuse alpha is transparent
     wherever there's no geometry below. The quad ends up at the
     lowest point with the merged material, and its world X/Y extents
     are stored as custom properties on it.
  10. Weight Smooth: runs Vertex Group Smooth across every vertex
      group on the active mesh, any time - not tied to a Weight
      Transfer. With "Selected Vertices Only" on, only vertices
      currently selected (in whatever mode - selection persists
      across Edit/Object Mode) are affected; otherwise the whole
      mesh is smoothed. "Smooth Active Vertex Group" does the same
      but only on whichever single group is highlighted in the
      Vertex Groups list, instead of every group at once.
  11. VGroup Mirror: this game's bone convention puts the L/R side
      marker in the middle of the name (e.g. "g_r_shoulder"), and
      Blender's built-in X-Mirror weight painting/Symmetrize tools
      are hardcoded to the local X axis - which turned out not to
      match this rig's actual mirror axis (Y) reliably even after
      attempting a temporary re-orientation. Two tools:
      (a) "Rename for Mirror" / "Revert Names" - renames matching
      vertex groups to end in ".L"/".R" (e.g. "g_r_shoulder" ->
      "g_shoulder.R"; center "g_c_" groups and unmarked groups like
      "g_cape" are left alone), and optionally turns on Blender's X
      Mirror toggle, locks the deforming armature to its "Root" NLA
      track's rest pose, and rotates the mesh DATA around Z - all
      exactly reversible, but the rotation/X-Mirror part is OFF by
      default now since it didn't prove reliable for this rig.
      (b) Two ways to actually mirror the weights once the axis is
      known, plus two diagnostics to find that axis and a couple of
      housekeeping buttons. "Diagnose (Weights)" compares the average
      position of each .L group's vertices against its .R pair
      (reports all three axes, not just its own pick, since a small
      natural asymmetry can otherwise look like a false winner) - but
      this is only as reliable as the .R side's current data.
      "Diagnose (Geometry)" is independent of vertex group data
      entirely: it reflects a sample of the mesh's own vertices
      around each axis and measures how well they land back on real
      geometry, so it stays reliable even if the .L/.R groups are
      empty, mismatched, or scrambled from a previous wrong-axis run
      - prefer this one. "Mirror All Groups" is the mirror method:
      duplicates the mesh, rebuilds one side as a clean geometric
      mirror with Blender's own Mirror modifier, then projects every
      vertex group back onto the original with a Data Transfer
      modifier (Nearest Face Interpolated) - smoothly blended, not
      blocky; the temporary duplicate is deleted automatically.
      "Mirror Active Group" does the same but restricted to just the
      matched pair the active vertex group belongs to. Which
      physical side gets kept for the mirror step is decided by
      checking the average position of the source group's weighted
      vertices - "Invert Source Side" flips that decision, as a
      diagnostic override for the rare case where the heuristic
      picks the wrong side on a particular mesh. "Wipe Destination
      Side" clears the current direction's destination groups
      without copying anything - handy to reset before re-testing
      with a different axis. "Wipe Active Group" does the same but
      for just whichever single group is highlighted in the Vertex
      Groups list. "Clear Console" clears the System Console window
      and brings it to the front (Windows only) between test runs.

USE:
  Open the 3D Viewport sidebar (press N), find the "MHO Actions" tab.
"""

import bpy
import os
import re
import json
import math
import datetime
from bpy.props import StringProperty, BoolProperty, PointerProperty, FloatProperty, IntProperty, EnumProperty
from bpy.types import Operator, Panel, PropertyGroup

# Keep this in sync with blender_manifest.toml's version every release -
# shown in the MHO Prepare Viewport panel so it's easy to confirm which
# build is actually installed (vs. a stale cached zip).
MHO_ADDON_VERSION = "1.52.0"


# ---------------------------------------------------------------------
# FBX -> Actions: core logic
# ---------------------------------------------------------------------

def find_fbx_files(folder):
    if not os.path.isdir(folder):
        return []
    return [
        os.path.join(folder, f)
        for f in sorted(os.listdir(folder))
        if f.lower().endswith(".fbx")
    ]


def import_fbx_and_get_new_objects(filepath):
    before = set(bpy.context.scene.objects)
    bpy.ops.import_scene.fbx(filepath=filepath)
    after = set(bpy.context.scene.objects)
    return list(after - before)


def find_action_on_objects(objects):
    armatures = [o for o in objects if o.type == "ARMATURE"]
    candidates = armatures + [o for o in objects if o not in armatures]
    for obj in candidates:
        if obj.animation_data and obj.animation_data.action:
            return obj.animation_data.action
    return None


def cleanup_imported_objects(objects):
    mesh_data = set()
    armature_data = set()
    for obj in objects:
        if obj.type == "MESH" and obj.data:
            mesh_data.add(obj.data)
        elif obj.type == "ARMATURE" and obj.data:
            armature_data.add(obj.data)
    for obj in objects:
        bpy.data.objects.remove(obj, do_unlink=True)
    for md in mesh_data:
        if md.users == 0:
            bpy.data.meshes.remove(md)
    for ad in armature_data:
        if ad.users == 0:
            bpy.data.armatures.remove(ad)


def purge_orphan_data():
    try:
        bpy.ops.outliner.orphans_purge(do_recursive=True)
    except RuntimeError:
        pass


def process_fbx_file(filepath, allow_duplicate_names, log):
    action_name = os.path.splitext(os.path.basename(filepath))[0]

    if not allow_duplicate_names and action_name in bpy.data.actions:
        log.append(f"SKIP  (action '{action_name}' already exists): {os.path.basename(filepath)}")
        return None

    imported_objects = import_fbx_and_get_new_objects(filepath)
    if not imported_objects:
        log.append(f"WARN  import produced no objects: {os.path.basename(filepath)}")
        return None

    action = find_action_on_objects(imported_objects)
    if action is None:
        log.append(f"WARN  no action found on imported rig: {os.path.basename(filepath)}")
        cleanup_imported_objects(imported_objects)
        return None

    action.name = action_name
    action.use_fake_user = True
    cleanup_imported_objects(imported_objects)

    log.append(f"OK    {os.path.basename(filepath)}  ->  action '{action.name}'")
    return action


# ---------------------------------------------------------------------
# Actions -> NLA: core logic
# ---------------------------------------------------------------------

def append_actions_from_library(filepath):
    """Appends every Action from the given .blend file into this file.
    Returns the list of appended Action datablocks (already-local copies)."""
    before_names = set(a.name for a in bpy.data.actions)

    with bpy.data.libraries.load(filepath, link=False) as (data_from, data_to):
        data_to.actions = list(data_from.actions)

    appended = []
    for act in bpy.data.actions:
        if act.name not in before_names:
            appended.append(act)
            act.use_fake_user = True
    return appended


def action_already_on_armature(armature_obj, action):
    """True if any NLA track on this armature already has a strip using this action."""
    anim_data = armature_obj.animation_data
    if not anim_data:
        return False
    for track in anim_data.nla_tracks:
        for strip in track.strips:
            if strip.action == action:
                return True
    return False


def push_actions_to_nla(armature_obj, actions, skip_existing, log):
    anim_data = armature_obj.animation_data
    if anim_data is None:
        anim_data = armature_obj.animation_data_create()

    # Make sure we're not leaving an active action sitting un-pushed;
    # pushdown always operates on NLA tracks/strips, not the active slot.
    added = 0
    skipped = 0

    for action in actions:
        if skip_existing and action_already_on_armature(armature_obj, action):
            log.append(f"SKIP  (already on NLA): {action.name}")
            skipped += 1
            continue

        track = anim_data.nla_tracks.new()
        track.name = action.name

        start_frame = action.frame_range[0] if action.frame_range else 1.0
        strip = track.strips.new(name=action.name, start=int(start_frame), action=action)
        strip.name = action.name

        log.append(f"OK    pushed '{action.name}' onto NLA track '{track.name}'")
        added += 1

    return added, skipped


def resolve_nla_target_armature(context):
    """Shared by Actions -> NLA and Add Root Pose Track: use the picked
    armature if set, else fall back to the active object if it's an
    armature. Returns None if neither is available."""
    props = context.scene.mho_props
    armature_obj = props.target_armature
    if armature_obj is None:
        active = context.active_object
        if active is not None and active.type == "ARMATURE":
            armature_obj = active
    if armature_obj is not None and armature_obj.type == "ARMATURE":
        return armature_obj
    return None


def armature_needs_root_track(armature_obj):
    """True if this armature has no NLA tracks yet - the situation the
    Add Root Pose Track button exists to fix before other actions get
    pushed down and there's no longer a clean, empty starting point."""
    if armature_obj is None:
        return False
    anim_data = armature_obj.animation_data
    if anim_data is None:
        return True
    return len(anim_data.nla_tracks) == 0


def create_root_pose_track(armature_obj):
    """Reset every pose bone to its neutral (identity) transform, key
    that pose once at frame 1 in a new 'Root' action, and push it down
    as a 'Root' NLA track - a clean, known-good starting point before
    other actions get appended."""

    anim_data = armature_obj.animation_data
    if anim_data is None:
        anim_data = armature_obj.animation_data_create()

    root_action = bpy.data.actions.new(name="Root")
    root_action.use_fake_user = True
    anim_data.action = root_action

    for pb in armature_obj.pose.bones:
        pb.location = (0.0, 0.0, 0.0)
        pb.scale = (1.0, 1.0, 1.0)
        if pb.rotation_mode == "QUATERNION":
            pb.rotation_quaternion = (1.0, 0.0, 0.0, 0.0)
            pb.keyframe_insert(data_path="rotation_quaternion", frame=1)
        elif pb.rotation_mode == "AXIS_ANGLE":
            pb.rotation_axis_angle = (0.0, 0.0, 1.0, 0.0)
            pb.keyframe_insert(data_path="rotation_axis_angle", frame=1)
        else:
            pb.rotation_euler = (0.0, 0.0, 0.0)
            pb.keyframe_insert(data_path="rotation_euler", frame=1)
        pb.keyframe_insert(data_path="location", frame=1)
        pb.keyframe_insert(data_path="scale", frame=1)

    # Pushdown pattern used everywhere else in this file: the strip
    # references the action directly, so the active action slot can be
    # cleared afterwards rather than left sitting on the object.
    anim_data.action = None

    track = anim_data.nla_tracks.new()
    track.name = "Root"
    strip = track.strips.new(name="Root", start=1, action=root_action)
    strip.name = "Root"

    return root_action, track


# ---------------------------------------------------------------------
# Weight Transfer: core logic
# ---------------------------------------------------------------------

def strip_target(target_obj):
    """Remove all vertex groups and any Armature modifiers from target."""
    target_obj.vertex_groups.clear()
    for mod in list(target_obj.modifiers):
        if mod.type == "ARMATURE":
            target_obj.modifiers.remove(mod)


def transfer_weights(context, source_obj, target_obj, ray_radius):
    # Selection state matters for data_transfer: source selected (not
    # active), target selected AND active.
    for obj in context.selected_objects:
        obj.select_set(False)
    source_obj.select_set(True)
    target_obj.select_set(True)
    context.view_layer.objects.active = target_obj

    # Matches the manual workflow: Transfer Weights only reliably writes
    # vertex groups when the target is in Weight Paint mode, not Object Mode.
    mode_result = bpy.ops.object.mode_set(mode="WEIGHT_PAINT")
    if "FINISHED" not in mode_result:
        bpy.ops.object.mode_set(mode="OBJECT")
        raise RuntimeError(
            f"Couldn't enter Weight Paint mode on '{target_obj.name}' "
            f"(mode_set returned {mode_result})"
        )

    try:
        result = bpy.ops.object.data_transfer(
            use_reverse_transfer=True,           # selected(source) -> active(target); default direction is the opposite
            data_type="VGROUP_WEIGHTS",
            use_create=True,
            vert_mapping="POLYINTERP_NEAREST",   # Nearest Face Interpolated
            use_object_transform=True,
            use_max_distance=False,
            ray_radius=ray_radius,
            # NOTE: use_reverse_transfer swaps which enum set src/dst accept -
            # with it on, src takes ACTIVE/NAME/INDEX and dst takes ACTIVE/ALL/etc.
            layers_select_src="NAME",            # match onto target by name
            layers_select_dst="ALL",             # affect every vertex group on target
            mix_mode="REPLACE",
            mix_factor=1.0,
        )
    finally:
        bpy.ops.object.mode_set(mode="OBJECT")

    if "FINISHED" not in result:
        raise RuntimeError(f"data_transfer operator returned {result} instead of FINISHED")


def smooth_target_weights(context, target_obj, factor, repeat):
    # vertex_group_smooth's poll requires Edit Mode (or Weight Paint mode
    # with vertex selection) - it fails silently-ish in Object Mode.
    context.view_layer.objects.active = target_obj
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.object.vertex_group_smooth(
        group_select_mode="ALL",
        factor=factor,
        repeat=repeat,
        expand=0.0,
    )
    bpy.ops.object.mode_set(mode="OBJECT")


def smooth_all_vertex_groups(context, obj, factor, repeat, selected_only, only_active=False):
    """Standalone weight-smooth, usable on any mesh at any time (not
    just right after a Weight Transfer). If selected_only is True, only
    the vertices already selected (mesh selection state persists across
    mode switches, so this works whether called from Edit or Object
    Mode) are affected; otherwise every vertex is selected first. If
    only_active is True, only the currently active vertex group (the
    one highlighted in the Vertex Groups list) is smoothed, instead of
    every group. Restores whatever mode the object was actually in
    beforehand (e.g. Weight Paint) rather than always dropping back to
    Object Mode."""

    context.view_layer.objects.active = obj
    original_mode = obj.mode

    if original_mode != "EDIT":
        bpy.ops.object.mode_set(mode="EDIT")

    if not selected_only:
        bpy.ops.mesh.select_all(action="SELECT")

    bpy.ops.object.vertex_group_smooth(
        group_select_mode="ACTIVE" if only_active else "ALL",
        factor=factor,
        repeat=repeat,
        expand=0.0,
    )

    if original_mode != "EDIT":
        bpy.ops.object.mode_set(mode=original_mode)


# ---------------------------------------------------------------------
# VGroup Mirror Names: core logic
# ---------------------------------------------------------------------

_MHO_VGROUP_RENAME_KEY = "mho_vgroup_rename_map"


def vgroup_mirror_name(name):
    """Given a raw vertex group name using this game's bone convention
    (a 2-char 'g_' prefix, then an optional l_/r_/c_ side marker, e.g.
    'g_r_shoulder'), return the Blender-mirror-friendly renamed version
    with the side marker moved to a '.L'/'.R' suffix (e.g.
    'g_shoulder.R') - which is what Blender's X-Mirror weight painting
    and Symmetrize tools require, since they only recognize the L/R
    marker at the very end of the name. Returns None for anything that
    doesn't need moving: center 'g_c_' groups, groups with no l_/r_/c_
    marker at all (e.g. 'g_cape'), and anything not starting with 'g_'."""

    m = re.match(r"^g_(l_|r_)(.+)$", name)
    if not m:
        return None
    marker, rest = m.group(1), m.group(2)
    side = "L" if marker == "l_" else "R"
    return f"g_{rest}.{side}"


def find_deforming_armature(obj):
    """The armature driving obj's deformation: whichever Armature
    modifier's target, or the parent if it's an armature. Returns None
    if neither is found."""
    for mod in obj.modifiers:
        if mod.type == "ARMATURE" and mod.object is not None:
            return mod.object
    if obj.parent is not None and obj.parent.type == "ARMATURE":
        return obj.parent
    return None


def rotate_mesh_data(obj, degrees):
    """Rotate obj's mesh DATA (not the object's transform) around Z by
    degrees, baked directly into the vertex coordinates via Edit Mode.
    Reversible exactly by calling again with -degrees. No-op if degrees
    is 0."""
    if degrees == 0:
        return
    if bpy.context.mode != "OBJECT":
        bpy.ops.object.mode_set(mode="OBJECT")
    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.transform.rotate(value=math.radians(degrees), orient_axis="Z", orient_type="GLOBAL")
    bpy.ops.object.mode_set(mode="OBJECT")


def lock_armature_to_root(armature_obj):
    """Mute every NLA track on armature_obj except one named 'Root' and
    jump to frame 1, so the armature shows its neutral/rest pose.
    Returns (original_mutes, original_frame, had_root) for exact
    restoration later; original_mutes is {} and had_root is False if
    there's no animation data or no 'Root' track (nothing is changed
    in that case)."""

    original_frame = bpy.context.scene.frame_current
    anim_data = armature_obj.animation_data
    if anim_data is None:
        return {}, original_frame, False

    had_root = any(t.name == "Root" for t in anim_data.nla_tracks)
    if not had_root:
        return {}, original_frame, False

    original_mutes = {t.name: t.mute for t in anim_data.nla_tracks}
    for t in anim_data.nla_tracks:
        t.mute = t.name != "Root"

    bpy.context.scene.frame_set(1)
    return original_mutes, original_frame, True


def restore_armature_nla(armature_obj, original_mutes, original_frame):
    """Undo lock_armature_to_root exactly."""
    anim_data = armature_obj.animation_data
    if anim_data is not None:
        for t in anim_data.nla_tracks:
            if t.name in original_mutes:
                t.mute = original_mutes[t.name]
    bpy.context.scene.frame_set(original_frame)


# ---------------------------------------------------------------------
# Mirror Weights (Custom): position-based, works on any local axis.
# Built because Blender's own X-Mirror weight painting turned out not
# to work reliably on this rig even after a temporary re-orientation -
# this bypasses it entirely, finding each vertex's true mirror
# counterpart by 3D position rather than relying on Blender's
# hardcoded X assumption.
# ---------------------------------------------------------------------

def find_lr_group_pairs(obj):
    """Return [(l_name, r_name), ...] for every vertex group pair where
    both '<base>.L' and '<base>.R' exist."""
    names = {vg.name for vg in obj.vertex_groups}
    pairs = []
    for name in names:
        if name.endswith(".L"):
            r_name = name[:-2] + ".R"
            if r_name in names:
                pairs.append((name, r_name))
    return pairs


def find_duplicate_vgroup_names(obj):
    """Blender does NOT enforce unique vertex group names (unlike
    materials/objects). Return a sorted list of any name that appears
    more than once - a stray duplicate left over from an earlier
    rename/revert cycle can silently shadow the group that actually
    holds weight data, since name-based lookup (obj.vertex_groups[name])
    only ever returns the first match."""
    from collections import Counter

    counts = Counter(vg.name for vg in obj.vertex_groups)
    return sorted(name for name, n in counts.items() if n > 1)


def detect_mirror_axis(obj, pairs):
    """Compute the centroid of all weighted vertices in each .L group
    vs its .R pair, across all pairs, and return (best_axis, diffs,
    l_centroid, r_centroid, per_pair_counts) where diffs is
    [x_diff, y_diff, z_diff] (l_centroid - r_centroid on each axis, so
    the caller can see ALL three rather than just whichever one this
    function's own "biggest difference" heuristic happened to pick -
    that heuristic can be misled by a small natural asymmetry on the
    wrong axis if the true mirror axis's separation happens to be
    smaller in absolute terms for this particular set of vertices).
    Returns (None, per_pair_counts) if no pair has any weighted
    vertices. per_pair_counts is [(l_name, r_name, l_count, r_count),
    ...] so the caller can report exactly which side/pair is empty."""
    import mathutils

    mesh = obj.data
    l_sum = mathutils.Vector((0.0, 0.0, 0.0))
    r_sum = mathutils.Vector((0.0, 0.0, 0.0))
    l_count = 0
    r_count = 0
    per_pair_counts = []

    for l_name, r_name in pairs:
        l_idx = obj.vertex_groups[l_name].index
        r_idx = obj.vertex_groups[r_name].index
        pair_l_count = 0
        pair_r_count = 0
        for v in mesh.vertices:
            for g in v.groups:
                if g.group == l_idx and g.weight > 0.0:
                    l_sum += v.co
                    l_count += 1
                    pair_l_count += 1
                elif g.group == r_idx and g.weight > 0.0:
                    r_sum += v.co
                    r_count += 1
                    pair_r_count += 1
        per_pair_counts.append((l_name, r_name, pair_l_count, pair_r_count))

    if l_count == 0 or r_count == 0:
        return None, per_pair_counts

    l_centroid = l_sum / l_count
    r_centroid = r_sum / r_count
    diffs = [l_centroid[i] - r_centroid[i] for i in range(3)]
    best_axis = max(range(3), key=lambda i: abs(diffs[i]))
    return (best_axis, diffs, l_centroid, r_centroid), per_pair_counts


def diagnose_symmetry_by_geometry(obj, sample_size=3000):
    """For each axis (X, Y, Z), reflect a sample of the mesh's own
    vertices around the mesh's bounding-box center on that axis, and
    measure how close each reflected point lands to an ACTUAL vertex
    elsewhere on the mesh (nearest-neighbor distance). A genuinely
    symmetric mesh will have a near-zero average distance on its TRUE
    mirror axis and much larger average distances on the wrong ones.

    Unlike detect_mirror_axis, this never looks at vertex group weight
    data at all - it's purely geometric, so it's immune to whatever
    state the .L/.R groups happen to be in (including corrupted by a
    previous wrong-axis mirror run). Returns [(axis, center, avg_dist),
    ...] for X, Y, Z, in that order."""
    import mathutils
    import random

    mesh = obj.data
    verts = mesh.vertices
    n = len(verts)
    if n == 0:
        raise RuntimeError("Mesh has no vertices")

    sample_indices = random.sample(range(n), sample_size) if n > sample_size else range(n)

    kd = mathutils.kdtree.KDTree(n)
    for i, v in enumerate(verts):
        kd.insert(v.co, i)
    kd.balance()

    results = []
    for axis in range(3):
        axis_values = [v.co[axis] for v in verts]
        center = (min(axis_values) + max(axis_values)) / 2.0

        total_dist = 0.0
        count = 0
        for i in sample_indices:
            co = verts[i].co.copy()
            co[axis] = 2.0 * center - co[axis]
            _co_found, _idx_found, dist = kd.find(co)
            if dist is not None:
                total_dist += dist
                count += 1

        avg_dist = (total_dist / count) if count else float("inf")
        results.append((axis, center, avg_dist))

    return results


def clear_vertex_group_weights(obj, group):
    """Remove every vertex currently assigned to `group` (a VertexGroup
    on obj), fully emptying it without deleting the group itself.
    Returns how many vertices were cleared."""
    mesh = obj.data
    indices = [v.index for v in mesh.vertices if any(g.group == group.index for g in v.groups)]
    if indices:
        group.remove(indices)
    return len(indices)


def _side_sign(obj, group_names, axis_index, center):
    """Whether the combined weighted vertices of every group in
    group_names sit, on average, above (+1) or below (-1) center on
    axis_index. Aggregates across ALL matched groups on the source
    side (not just one) so a single sparse/edge-case group can't skew
    the result. Returns (sign, total_count)."""
    group_indices = {obj.vertex_groups[name].index for name in group_names}
    total = 0.0
    count = 0
    for v in obj.data.vertices:
        for g in v.groups:
            if g.group in group_indices and g.weight > 0.0:
                total += v.co[axis_index]
                count += 1
                break
    if count == 0:
        return 1.0, 0
    return (1.0 if (total / count) >= center else -1.0), count


def symmetrize_weights_data_transfer(
    context, obj, axis_index, direction, use_clip=True, invert_side=False, only_group_pair=None
):
    """Blender-native approach, avoiding the blocky results of nearest-
    single-vertex matching: duplicate obj, delete the side being
    regenerated, add a Mirror modifier (clipped, centered on the mesh's
    own bounding-box center on axis_index) and apply it to rebuild that
    side as a geometrically and topologically clean mirror, then use a
    Data Transfer modifier (Nearest Face Interpolated) to project
    vertex group weights from that clean reference back onto the
    original (asymmetric) mesh - smoothly interpolated from the nearest
    face rather than snapped from a single nearest vertex. The source
    side's own weights come back through the projection essentially
    unchanged (same geometry, so the nearest face is itself); only the
    regenerated side actually changes. invert_side flips which physical
    side the sign heuristic below decides to keep - a diagnostic
    override for the rare case that heuristic picks the wrong side on a
    particular mesh. only_group_pair, if given as an (l_name, r_name)
    tuple, restricts the whole operation to just that one matched pair
    (both the sign heuristic and the actual Data Transfer, via the
    modifier's named-layer source-selection) instead of every matched
    pair on the mesh. Returns a one-line log list. Raises RuntimeError
    if no matched .L/.R pairs exist, if only_group_pair isn't one of
    them, or if the chosen source side has no weighted vertices to work
    from."""
    import mathutils

    mesh = obj.data
    axis_values = [v.co[axis_index] for v in mesh.vertices]
    center = (min(axis_values) + max(axis_values)) / 2.0

    all_pairs = find_lr_group_pairs(obj)
    if not all_pairs:
        raise RuntimeError("No matched .L/.R vertex group pairs found - run Rename for Mirror first")

    if only_group_pair is not None:
        if only_group_pair not in all_pairs:
            raise RuntimeError(
                f"'{only_group_pair[0]}' / '{only_group_pair[1]}' isn't a matched .L/.R pair"
            )
        pairs = [only_group_pair]
    else:
        pairs = all_pairs

    src_suffix = "L" if direction == "L_TO_R" else "R"
    src_group_names = [l_name if src_suffix == "L" else r_name for l_name, r_name in pairs]
    src_sign, src_vert_count = _side_sign(obj, src_group_names, axis_index, center)
    if src_vert_count == 0:
        raise RuntimeError(
            f"None of the .{src_suffix} groups ({', '.join(src_group_names)}) have any "
            "weighted vertices to use as the source side"
        )

    if invert_side:
        src_sign = -src_sign

    print(
        f"OK    source side: .{src_suffix} ({src_vert_count} weighted vert(s) across "
        f"{len(src_group_names)} group(s)), sign={src_sign:+.0f}"
        f"{' (inverted)' if invert_side else ''}, axis "
        f"{'XYZ'[axis_index]} center={center:.4f}"
    )

    # --- 1. Duplicate ---
    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    context.view_layer.objects.active = obj
    bpy.ops.object.duplicate(linked=False)
    ref_obj = context.view_layer.objects.active
    ref_obj.name = f"{obj.name}_SymRef"

    # Strip every modifier the duplicate inherited (an Armature modifier,
    # almost certainly, on a rigged character). This reference only
    # needs base geometry + vertex group data - if left in place, the
    # Mirror modifier we add next would sit AFTER Armature in the stack,
    # so applying it would bake in the current POSED/deformed shape
    # instead of the clean rest geometry (and Blender warns about this:
    # "Applied modifier was not first"). On a mesh that's just had half
    # its vertices deleted, that can produce genuinely degenerate
    # geometry - which is what caused the "0 faces" error afterward.
    for mod in list(ref_obj.modifiers):
        ref_obj.modifiers.remove(mod)

    # Turn off X mirror EDITING (mesh.use_mirror_x) on the duplicate,
    # regardless of what the original mesh currently has set. If
    # "Rename for Mirror" enabled this (and it's still on because
    # Revert Names hasn't been clicked yet), the duplicate inherits it
    # too - and with mirror editing active, deleting our selected verts
    # would ALSO auto-delete their symmetric counterparts live, which is
    # almost certainly why deleting a couple hundred selected vertices
    # wiped the entire mesh instead of leaving the other half intact.
    ref_obj.data.use_mirror_x = False

    # --- 2. Delete the non-source side on the duplicate ---
    # Done directly via bmesh rather than bpy.ops.mesh.delete(), so this
    # is completely unaffected by any Edit Mode UI setting that could
    # cascade the deletion beyond exactly the vertices selected below
    # (mirror editing, multi-object edit sync, proportional editing,
    # etc.) - bmesh operates purely on the mesh data, ignoring all of
    # that entirely.
    import bmesh

    total_verts = len(ref_obj.data.vertices)
    bm = bmesh.new()
    bm.from_mesh(ref_obj.data)
    bm.verts.ensure_lookup_table()

    verts_to_delete = []
    for bv in bm.verts:
        signed = 1.0 if bv.co[axis_index] >= center else -1.0
        if signed != src_sign:
            verts_to_delete.append(bv)

    delete_count = len(verts_to_delete)
    print(f"OK    deleting {delete_count} of {total_verts} vertex/verts (keeping the .{src_suffix} side)")

    bmesh.ops.delete(bm, geom=verts_to_delete, context="VERTS")

    bm.to_mesh(ref_obj.data)
    bm.free()
    ref_obj.data.update()

    remaining = len(ref_obj.data.vertices)
    print(f"OK    {remaining} vertex/verts remain on the reference after deletion")

    if remaining == 0:
        bpy.data.objects.remove(ref_obj, do_unlink=True)
        raise RuntimeError(
            f"Deleting the non-source side removed the ENTIRE mesh (0 vertices left) - "
            f"the sign/center calculation likely picked the wrong side. Source side was "
            f".{src_suffix}, sign={src_sign:+.0f}, center={center:.4f} on axis {'XYZ'[axis_index]}"
        )

    # --- 3. Re-origin the duplicate to the mirror plane, add + apply Mirror ---
    cursor_orig = context.scene.cursor.location.copy()
    local_center = mathutils.Vector((0.0, 0.0, 0.0))
    local_center[axis_index] = center
    context.scene.cursor.location = ref_obj.matrix_world @ local_center
    bpy.ops.object.origin_set(type="ORIGIN_CURSOR")
    context.scene.cursor.location = cursor_orig

    mirror_mod = ref_obj.modifiers.new(name="MHO_TempMirror", type="MIRROR")
    mirror_mod.use_axis = [axis_index == 0, axis_index == 1, axis_index == 2]
    mirror_mod.use_clip = use_clip
    mirror_mod.use_mirror_vertex_groups = True
    bpy.ops.object.modifier_apply(modifier=mirror_mod.name)

    print(
        f"OK    reference mesh after mirror: {len(ref_obj.data.vertices)} vert(s), "
        f"{len(ref_obj.data.polygons)} face(s)"
    )

    if len(ref_obj.data.polygons) == 0:
        bpy.data.objects.remove(ref_obj, do_unlink=True)
        raise RuntimeError(
            "Reference mesh ended up with 0 faces after mirroring - the source side "
            "(the half that was kept) may itself be empty or degenerate"
        )

    # --- 4. Data Transfer on the ORIGINAL, sourced from the reference ---
    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    context.view_layer.objects.active = obj
    dt_mod = obj.modifiers.new(name="MHO_TempDataTransfer", type="DATA_TRANSFER")
    dt_mod.object = ref_obj
    dt_mod.use_vert_data = True
    dt_mod.data_types_verts = {"VGROUP_WEIGHTS"}
    dt_mod.vert_mapping = "POLYINTERP_NEAREST"

    if only_group_pair is not None:
        # layers_vgroup_select_src is a dynamic enum: 'ALL' plus the
        # literal name of every vertex group on the source (reference)
        # object - so restricting the transfer to one group is just a
        # matter of setting this to that group's exact name, no need to
        # touch the reference's active vertex group at all.
        l_name, r_name = only_group_pair
        dst_name = r_name if direction == "L_TO_R" else l_name
        if dst_name in ref_obj.vertex_groups:
            dt_mod.layers_vgroup_select_src = dst_name
        else:
            dt_mod.layers_vgroup_select_src = "ALL"
    else:
        dt_mod.layers_vgroup_select_src = "ALL"

    # Force it to the top of obj's own modifier stack (Armature almost
    # certainly sits there otherwise) so it samples against the clean
    # rest mesh rather than the current posed/deformed result.
    bpy.ops.object.modifier_move_to_index(modifier=dt_mod.name, index=0)
    bpy.ops.object.modifier_apply(modifier=dt_mod.name)

    # --- 5. Clean up the reference object ---
    bpy.data.objects.remove(ref_obj, do_unlink=True)
    purge_orphan_data()

    scope_note = f", group pair '{only_group_pair[0]}'/'{only_group_pair[1]}'" if only_group_pair else ""
    return [
        f"OK    symmetrized via Data Transfer (Nearest Face Interpolated), "
        f"source side .{src_suffix}, axis {'XYZ'[axis_index]}, plane={center:.4f}{scope_note}"
    ]


def mirror_weights_custom(obj, axis_index, direction):
    """For every matched .L/.R vertex group pair, REPLACE the entire
    destination group with weights copied from the source side onto
    each source vertex's nearest counterpart - by position, reflected
    across the given local axis. direction is 'L_TO_R' or 'R_TO_L'.
    Returns (pairs_processed, vertices_copied, log); raises
    RuntimeError if no matched pairs exist.

    The destination group is fully cleared before repopulating it, so
    this is idempotent - re-running it (e.g. after switching to the
    correct axis) always gives a clean result instead of a previous
    run's stale/wrong assignments lingering alongside the new ones.
    That also means any weight data already on the destination side
    that this run doesn't recreate is genuinely gone, not preserved.

    Reflection happens around the mesh's own bounding-box center on
    that axis, NOT around 0 - a character rarely sits exactly at the
    world origin, and reflecting around 0 for a mesh centered well away
    from it sends every mirrored position somewhere nowhere near the
    actual geometry, so the nearest-neighbor search would just snap to
    whatever unrelated vertex happens to be closest to that wrong point."""
    import mathutils

    mesh = obj.data
    pairs = find_lr_group_pairs(obj)
    if not pairs:
        raise RuntimeError("No matched .L/.R vertex group pairs found - run Rename for Mirror first")

    if not mesh.vertices:
        raise RuntimeError("Mesh has no vertices")
    axis_values = [v.co[axis_index] for v in mesh.vertices]
    center = (min(axis_values) + max(axis_values)) / 2.0

    kd = mathutils.kdtree.KDTree(len(mesh.vertices))
    for i, v in enumerate(mesh.vertices):
        kd.insert(v.co, i)
    kd.balance()

    log = [f"OK    mirror plane: axis {'XYZ'[axis_index]} = {center:.4f} (bounding box center)"]
    total_copied = 0

    for l_name, r_name in pairs:
        src_name, dst_name = (l_name, r_name) if direction == "L_TO_R" else (r_name, l_name)
        src_group = obj.vertex_groups[src_name]
        dst_group = obj.vertex_groups[dst_name]

        # Clear every vertex currently in the destination group first.
        # Without this, a previous run (possibly on a wrong axis) would
        # leave its stale/incorrect assignments sitting alongside this
        # run's new ones - this makes the operation idempotent, so
        # re-running it (e.g. after fixing the axis) always gives a
        # clean result instead of accumulating old and new data together.
        clear_vertex_group_weights(obj, dst_group)

        copied = 0
        for v in mesh.vertices:
            src_weight = None
            for g in v.groups:
                if g.group == src_group.index:
                    src_weight = g.weight
                    break
            if src_weight is None or src_weight <= 0.0:
                continue

            mirrored_co = v.co.copy()
            mirrored_co[axis_index] = 2.0 * center - mirrored_co[axis_index]

            _co_found, idx_found, _dist = kd.find(mirrored_co)
            if idx_found is None:
                continue

            dst_group.add([idx_found], src_weight, "REPLACE")
            copied += 1

        total_copied += copied
        log.append(f"OK    {src_name} -> {dst_name}: {copied} vertex weight(s) copied")

    return len(pairs), total_copied, log


def add_armature_modifier(target_obj, source_obj):
    """Copy the Armature modifier from source onto target, pointing at
    the same armature object. Returns (ok, message)."""
    src_mod = next((m for m in source_obj.modifiers if m.type == "ARMATURE"), None)
    if not src_mod:
        return False, f"Source '{source_obj.name}' has no Armature modifier to copy."
    if not src_mod.object:
        return False, "Source's Armature modifier has no armature object assigned."

    armature_obj = src_mod.object
    new_mod = target_obj.modifiers.new(name=src_mod.name, type="ARMATURE")
    new_mod.object = armature_obj
    new_mod.use_vertex_groups = src_mod.use_vertex_groups
    new_mod.use_bone_envelopes = src_mod.use_bone_envelopes
    new_mod.use_deform_preserve_volume = src_mod.use_deform_preserve_volume
    new_mod.use_multi_modifier = src_mod.use_multi_modifier

    # Put it at the top of the modifier stack, matching typical rig setups.
    try:
        bpy.ops.object.modifier_move_to_index(modifier=new_mod.name, index=0)
    except RuntimeError:
        pass  # non-fatal if the stack only has this one modifier

    return True, armature_obj.name


def sort_vertex_groups_by_bone_hierarchy(context, target_obj):
    """Sort target's vertex groups to match its armature's bone hierarchy.
    Requires an Armature modifier (or armature parent) to read the
    hierarchy from - call this after add_armature_modifier()."""
    context.view_layer.objects.active = target_obj
    bpy.ops.object.vertex_group_sort(sort_type="BONE_HIERARCHY")


def set_weight_paint_overlay(context, opacity, zero_weights):
    """Set the 3D Viewport's Weight Paint overlay opacity and Zero
    Weights display mode. opacity is 0-1; zero_weights is 'NONE',
    'ACTIVE', or 'ALL'."""
    space = context.space_data
    if space is not None and space.type == "VIEW_3D":
        space.overlay.weight_paint_mode_opacity = opacity
    context.scene.tool_settings.vertex_group_user = zero_weights


def set_viewport_shading(context, shading_type):
    """Set the 3D Viewport's shading mode ('WIREFRAME', 'SOLID',
    'MATERIAL', or 'RENDERED'). Returns True if a VIEW_3D space was
    found and set, False otherwise (e.g. called from a non-3D-viewport
    context, such as the Properties editor sidebar)."""
    space = context.space_data
    if space is not None and space.type == "VIEW_3D":
        space.shading.type = shading_type
        return True
    return False


# ---------------------------------------------------------------------
# Properties
# ---------------------------------------------------------------------

def poll_armature(self, obj):
    return obj.type == "ARMATURE"


def poll_mesh(self, obj):
    return obj.type == "MESH"


class MHO_Props(PropertyGroup):
    # FBX -> Actions
    input_dir: StringProperty(
        name="FBX Folder",
        description="Folder containing the animated FBX files exported from MHModelEditor",
        subtype="DIR_PATH",
    )
    output_blend: StringProperty(
        name="Output .blend",
        description="Where to save the resulting action library (leave blank to skip saving)",
        subtype="FILE_PATH",
    )
    allow_duplicate_names: BoolProperty(
        name="Allow Duplicate Names",
        description="If off, FBX files whose action name already exists in this file are skipped instead of auto-renamed",
        default=False,
    )

    # Actions -> NLA
    target_armature: PointerProperty(
        name="Armature",
        description="Armature to push the appended actions onto as NLA strips",
        type=bpy.types.Object,
        poll=poll_armature,
    )
    actions_library: StringProperty(
        name="Actions Library",
        description="Action library .blend file to append actions from (e.g. the one saved by FBX to Actions)",
        subtype="FILE_PATH",
    )
    skip_existing_nla: BoolProperty(
        name="Skip Already-Added Actions",
        description="Don't create a new NLA track for an action that's already on a strip on this armature",
        default=True,
    )

    # Armature Stick Display
    armature_stick_scene_only: BoolProperty(
        name="Current Scene Only",
        description="Only affect armatures in the active scene, rather than every armature "
                    "data-block in the .blend file",
        default=True,
    )

    # Weight Transfer
    wt_source_obj: PointerProperty(
        name="Source",
        description="Mesh to copy weights FROM",
        type=bpy.types.Object,
        poll=poll_mesh,
    )
    wt_target_obj: PointerProperty(
        name="Target",
        description="Mesh to copy weights TO - its existing vertex groups and Armature modifier(s) will be removed first",
        type=bpy.types.Object,
        poll=poll_mesh,
    )
    wt_ray_radius_mm: FloatProperty(
        name="Ray Radius (mm)",
        default=5.0,
        min=0.0,
        description="Search radius for nearest-face matching, in millimeters (assumes 1 Blender unit = 1 meter)",
    )
    wt_do_smooth: BoolProperty(
        name="Smooth After Transfer",
        default=True,
        description="Run Vertex Group Smooth on the target after the transfer, to blend across seams",
    )
    wt_smooth_factor: FloatProperty(
        name="Smooth Factor",
        default=0.5,
        min=0.0,
        max=1.0,
        description="Strength of each smoothing pass",
    )
    wt_smooth_repeat: IntProperty(
        name="Smooth Iterations",
        default=5,
        min=1,
        max=50,
        description="Number of smoothing passes to run",
    )
    wt_add_armature_mod: BoolProperty(
        name="Add Armature Modifier After Transfer",
        default=True,
        description="After transferring weights, add an Armature modifier to the target pointing at the same armature as the source",
    )
    wt_sort_by_bone_hierarchy: BoolProperty(
        name="Sort Vertex Groups by Bone Hierarchy",
        default=True,
        description="After everything else, sort the target's vertex groups to match its armature's bone hierarchy (requires the Armature modifier step above, or an existing armature parent/modifier)",
    )

    # Weight Smooth (standalone - usable any time, not just right after a transfer)
    ws_smooth_factor: FloatProperty(
        name="Smooth Factor",
        default=0.5,
        min=0.0,
        max=1.0,
        description="Strength of each smoothing pass",
    )
    ws_smooth_repeat: IntProperty(
        name="Smooth Iterations",
        default=5,
        min=1,
        max=50,
        description="Number of smoothing passes to run",
    )
    ws_selected_verts_only: BoolProperty(
        name="Selected Vertices Only",
        default=False,
        description="Only smooth vertex groups on vertices currently selected in Edit Mode, "
                    "instead of the whole mesh",
    )

    # VGroup Mirror Names
    vg_axis_correction_degrees: FloatProperty(
        name="Axis Correction (ZÂ°)",
        default=0.0,
        description="Only needed for Blender's built-in live X-Mirror painting, which turned "
                    "out not to work reliably for this rig (see Mirror Weights (Custom) below "
                    "instead) - temporarily rotates the mesh DATA by this many degrees around Z "
                    "(reversed exactly by Revert Names). Leave at 0 unless you have a specific "
                    "reason to try live X-Mirror painting again",
    )
    vg_lock_rest_pose: BoolProperty(
        name="Lock Armature to Rest Pose (via Root)",
        default=True,
        description="While renamed, mute every NLA track except 'Root' on the deforming "
                    "armature and jump to frame 1, so the character is in a clean neutral "
                    "pose. Restored exactly by Revert Names. Requires an existing Root track "
                    "(Actions -> NLA panel) - skipped with a warning if none is found",
    )

    # Offset
    zo_axis: EnumProperty(
        name="Axis",
        description="World-space axis to shift the bone(s) directly under 'root' along - "
                    "pick whichever one actually corresponds to scene-vertical for this "
                    "armature, since that can vary by rig/import convention",
        items=[
            ("X", "X", "Offset along world X"),
            ("Y", "Y", "Offset along world Y"),
            ("Z", "Z", "Offset along world Z"),
        ],
        default="Z",
    )
    zo_offset_amount: FloatProperty(
        name="Offset",
        default=0.0,
        description="Amount to shift the bone(s) directly under 'root' along the chosen "
                    "world-space axis (in this armature's own units) - negative/positive "
                    "moves it the two ways along that axis",
    )
    zo_blend_type: EnumProperty(
        name="Blend Type",
        description="NLA strip blend mode for the Offset track - how it combines with "
                    "whatever animation is on the track(s) below it",
        items=[
            ("ADD", "Add", "Classic additive blending"),
            ("COMBINE", "Combine", "Newer, more correct additive blending for rotation/scale "
                                    "(equivalent to Add for a pure positional offset)"),
            ("REPLACE", "Replace", "Replace instead of blend - rarely what you want here"),
        ],
        default="ADD",
    )

    # Mirror Weights (Custom) - position-based, works on any axis
    mw_mirror_axis: EnumProperty(
        name="Mirror Axis",
        description="Local axis to reflect across when finding each vertex's mirror "
                    "counterpart by position",
        items=[
            ("X", "X", "Mirror across local X"),
            ("Y", "Y", "Mirror across local Y"),
            ("Z", "Z", "Mirror across local Z"),
        ],
        default="Y",
    )
    mw_direction: EnumProperty(
        name="Direction",
        description="Which side's weights get copied onto the other",
        items=[
            ("L_TO_R", "L \u2192 R", "Copy weights from .L groups onto their .R counterparts"),
            ("R_TO_L", "R \u2192 L", "Copy weights from .R groups onto their .L counterparts"),
        ],
        default="L_TO_R",
    )
    mw_use_clipping: BoolProperty(
        name="Use Clipping",
        description="Clip the Mirror modifier's seam vertices to the mirror plane exactly, "
                    "so the symmetrized reference has no gap or overlap down the center",
        default=True,
    )
    mw_invert_source_side: BoolProperty(
        name="Invert Source Side",
        description="Symmetrize picks which physical side to keep (and mirror from) by "
                    "checking the average position of the source group's weighted vertices - "
                    "if that heuristic ever picks the wrong side on a particular mesh (result "
                    "looks flipped/wrong), enable this to invert it and re-run, as a way to "
                    "track down whether that's actually what's happening",
        default=False,
    )

    # MFF Model Prep
    mp_scale_factor: FloatProperty(
        name="Scale Factor",
        description="Multiplied onto the joined object's current scale on all axes",
        default=55.0,
    )
    mp_rotate_z_degrees: FloatProperty(
        name="Rotate Z (degrees)",
        description="Added onto the joined object's current Z rotation, before Apply Transforms",
        default=90.0,
    )
    mp_merge_distance: FloatProperty(
        name="Merge Distance",
        description="Merge By Distance threshold used to weld overlapping vertices after the transform is applied",
        default=0.0001,
        min=0.0,
        precision=6,
    )

    # Symmetrical Sculpt Adjust
    sculpt_symmetry_axis: EnumProperty(
        name="Symmetry Axis",
        description="Which single axis to enable sculpt mirror symmetry on - the other two are turned off",
        items=[
            ("X", "X", "Mirror on X only"),
            ("Y", "Y", "Mirror on Y only"),
            ("Z", "Z", "Mirror on Z only"),
        ],
        default="Y",
    )

    # Texture Baker
    _TB_SIZE_ITEMS = [
        ("1024", "1024", "1024 x 1024"),
        ("2048", "2048", "2048 x 2048"),
        ("4096", "4096", "4096 x 4096"),
    ]
    tb_diffuse_size: EnumProperty(
        name="Diffuse Size",
        description="Resolution of the baked Diffuse atlas",
        items=_TB_SIZE_ITEMS,
        default="2048",
    )
    tb_normal_size: EnumProperty(
        name="Normal Size",
        description="Resolution of the baked Normal atlas",
        items=_TB_SIZE_ITEMS,
        default="2048",
    )
    tb_specmask_size: EnumProperty(
        name="Spec Mask Size",
        description="Resolution of the baked Spec Mask atlas",
        items=_TB_SIZE_ITEMS,
        default="2048",
    )
    tb_speccolor_size: EnumProperty(
        name="Spec Color Size",
        description="Resolution of the baked Spec Color atlas",
        items=_TB_SIZE_ITEMS,
        default="2048",
    )
    tb_reduce_quality: FloatProperty(
        name="Quality",
        description="Reduced bake: target triangle count as a fraction of the original "
                    "(0.25 = about a quarter of the triangles). The detail removed is "
                    "baked into the Normal map from the original mesh",
        min=0.01,
        max=1.0,
        default=0.25,
        subtype="FACTOR",
    )
    tb_reduce_dissolve_flat: BoolProperty(
        name="Dissolve Flat Areas",
        description="Reduced bake: before collapsing, merge nearly-flat regions (within 5 "
                    "degrees, not across material boundaries) into larger faces - removes "
                    "triangles from floors, walls and panels at almost no visual cost",
        default=True,
    )
    tb_selected_faces_only: BoolProperty(
        name="Selected Faces Only",
        description="Bake only the currently selected faces of each selected mesh, instead of "
                    "the complete objects",
        default=False,
    )


# ---------------------------------------------------------------------
# FBX -> Actions: operator
# ---------------------------------------------------------------------

class MHO_OT_import_fbx_to_actions(Operator):
    bl_idname = "mho.import_fbx_to_actions"
    bl_label = "Import FBXs to Actions"
    bl_description = "Batch-import every FBX in the folder and convert each into an Action"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        props = context.scene.mho_props
        input_dir = bpy.path.abspath(props.input_dir)
        output_blend = bpy.path.abspath(props.output_blend) if props.output_blend else None

        fbx_files = find_fbx_files(input_dir)
        if not fbx_files:
            self.report({"ERROR"}, f"No .fbx files found in: {input_dir}")
            return {"CANCELLED"}

        log = []
        created = []
        skipped = []

        for filepath in fbx_files:
            action = process_fbx_file(filepath, props.allow_duplicate_names, log)
            if action is not None:
                created.append(action)
            else:
                skipped.append(filepath)

        purge_orphan_data()

        for line in log:
            print(line)

        if output_blend:
            os.makedirs(os.path.dirname(output_blend), exist_ok=True)
            bpy.ops.wm.save_as_mainfile(filepath=output_blend)
            print(f"Saved action library to: {output_blend}")

        msg = f"Created {len(created)} action(s)"
        if skipped:
            msg += f", skipped {len(skipped)} (see console)"
        self.report({"INFO"}, msg)
        return {"FINISHED"}


# ---------------------------------------------------------------------
# Actions -> NLA: operator
# ---------------------------------------------------------------------

class MHO_OT_append_actions_to_nla(Operator):
    bl_idname = "mho.append_actions_to_nla"
    bl_label = "Append Actions to NLA"
    bl_description = (
        "Append every Action from the library .blend into this file and push each "
        "one down onto the selected armature as its own NLA track"
    )
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        props = context.scene.mho_props

        armature_obj = resolve_nla_target_armature(context)
        if armature_obj is None:
            self.report({"ERROR"}, "Pick an armature (or select one in the viewport) first")
            return {"CANCELLED"}

        library_path = bpy.path.abspath(props.actions_library)
        if not library_path or not os.path.isfile(library_path):
            self.report({"ERROR"}, f"Actions library not found: {library_path}")
            return {"CANCELLED"}

        appended_actions = append_actions_from_library(library_path)
        if not appended_actions:
            self.report({"WARNING"}, "No actions found in that library file")
            return {"CANCELLED"}

        log = []
        added, skipped = push_actions_to_nla(
            armature_obj, appended_actions, props.skip_existing_nla, log
        )

        purge_orphan_data()

        for line in log:
            print(line)

        msg = f"Pushed {added} action(s) onto '{armature_obj.name}' as NLA tracks"
        if skipped:
            msg += f", skipped {skipped} already present"
        self.report({"INFO"}, msg)
        return {"FINISHED"}


class MHO_OT_add_root_pose_track(Operator):
    """Set the armature to its neutral pose, key it once at frame 1,
    and push that down as a starting 'Root' NLA track"""

    bl_idname = "mho.add_root_pose_track"
    bl_label = "Add Root Pose Track"
    bl_description = (
        "Set the armature to its neutral/rest pose, key it once at frame 1, and push "
        "that down as a 'Root' NLA track - a clean starting point before appending "
        "other actions"
    )
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context):
        return resolve_nla_target_armature(context) is not None

    def execute(self, context):
        armature_obj = resolve_nla_target_armature(context)
        if armature_obj is None:
            self.report({"ERROR"}, "Pick an armature (or select one in the viewport) first")
            return {"CANCELLED"}

        create_root_pose_track(armature_obj)

        self.report({"INFO"}, f"Created 'Root' NLA track on '{armature_obj.name}'")
        return {"FINISHED"}


_MHO_NLA_ISOLATE_KEY = "mho_nla_isolate_state"


class MHO_OT_toggle_nla_root(Operator):
    """Toggle: mute every NLA track except 'Root' for a clean rest
    pose, remembering which tracks were active - or, if already
    isolated, restore them exactly. Single operator (not two separate
    ones) so it works correctly from a Quick Favorites shortcut
    regardless of which state it's currently in"""

    bl_idname = "mho.toggle_nla_root"
    bl_label = "Toggle NLA to Root"
    bl_description = (
        "Toggle: mute every NLA track except 'Root' so the armature shows its neutral rest "
        "pose (remembering which tracks were active and the current frame) - or, if already "
        "isolated, restore them exactly"
    )
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context):
        return resolve_nla_target_armature(context) is not None

    def execute(self, context):
        armature_obj = resolve_nla_target_armature(context)
        if armature_obj is None:
            self.report({"ERROR"}, "Pick an armature (or select one in the viewport) first")
            return {"CANCELLED"}

        if _MHO_NLA_ISOLATE_KEY in armature_obj:
            try:
                state = json.loads(armature_obj[_MHO_NLA_ISOLATE_KEY])
            except (KeyError, ValueError):
                self.report({"ERROR"}, "Couldn't read the stored NLA state")
                return {"CANCELLED"}

            restore_armature_nla(armature_obj, state.get("mutes", {}), state.get("frame", 1))
            del armature_obj[_MHO_NLA_ISOLATE_KEY]
            self.report({"INFO"}, f"Restored '{armature_obj.name}' NLA track states")
            return {"FINISHED"}

        mutes, frame, had_root = lock_armature_to_root(armature_obj)
        if not had_root:
            self.report(
                {"ERROR"},
                f"No 'Root' NLA track on '{armature_obj.name}' (Add Root Pose Track above can create one)",
            )
            return {"CANCELLED"}

        armature_obj[_MHO_NLA_ISOLATE_KEY] = json.dumps({"mutes": mutes, "frame": frame})
        self.report({"INFO"}, f"Isolated '{armature_obj.name}' to its Root rest pose")
        return {"FINISHED"}


class MHO_OT_create_z_offset_track(Operator):
    """Build (or update) an 'Offset' action that shifts the bone(s)
    directly under "root" along a chosen world-space axis - reaching
    through any '_offset'-suffixed pass-through bone in that tier to
    its own children instead of keying the '_offset' bone itself - and
    push it onto a new NLA track at the top of the stack with additive
    blending - corrects a flying/hover animation that sits too high,
    low, or off to one side, without touching the animation itself"""

    bl_idname = "mho.create_z_offset_track"
    bl_label = "Create Offset Track"
    bl_description = (
        "Build (or update) an 'Offset' action that shifts the bone(s) directly under "
        "'root' along the chosen world-space axis (for any '_offset'-suffixed bone in "
        "that tier, its own children are targeted instead, one level deeper) - their "
        "children follow automatically via forward kinematics - and push it onto a new "
        "NLA track at the top of the stack with additive blending, so it offsets "
        "whatever animation plays on the tracks below it. Re-running this updates the "
        "same track/action in place"
    )
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context):
        return resolve_nla_target_armature(context) is not None

    def execute(self, context):
        import mathutils

        props = context.scene.mho_props
        armature_obj = resolve_nla_target_armature(context)
        if armature_obj is None:
            self.report({"ERROR"}, "Pick an armature (or select one in the viewport) first")
            return {"CANCELLED"}

        axis_index = "XYZ".index(props.zo_axis)
        offset_amount = props.zo_offset_amount
        blend_type = props.zo_blend_type

        # Only the direct children of "root" actually need to move -
        # forward kinematics automatically carries every bone below
        # them along for free. Offsetting EVERY bone (an earlier
        # version of this tool did that) compounds the shift once per
        # level of hierarchy depth instead of translating the character
        # as one rigid whole, which is what was distorting the mesh.
        root_bone = None
        for pb in armature_obj.pose.bones:
            if pb.name.lower() == "root":
                root_bone = pb
                break

        if root_bone is not None:
            root_children = [pb for pb in armature_obj.pose.bones if pb.parent == root_bone]
            if not root_children:
                self.report(
                    {"ERROR"},
                    f"'root' has no direct child bones on '{armature_obj.name}' - nothing to offset",
                )
                return {"CANCELLED"}
        else:
            root_children = [pb for pb in armature_obj.pose.bones if pb.parent is None]
            if not root_children:
                self.report({"ERROR"}, f"'{armature_obj.name}' has no bones to offset")
                return {"CANCELLED"}
            self.report(
                {"WARNING"},
                f"No bone literally named 'root' found on '{armature_obj.name}' - using the "
                "top-level bone(s) instead",
            )

        # A '_offset'-suffixed bone in this tier is itself a pass-through
        # helper, not something that should be keyed directly - reach
        # through it to its own children instead (those are the real
        # motion bones one level down). Any non-'_offset' bone in this
        # tier is targeted directly, as before.
        target_bones = []
        for pb in root_children:
            if pb.name.lower().endswith("_offset"):
                target_bones.extend(pb.children)
            else:
                target_bones.append(pb)

        if not target_bones:
            self.report(
                {"ERROR"},
                f"'{armature_obj.name}' has no bones to offset once '_offset' bones are "
                "resolved to their children - nothing to offset",
            )
            return {"CANCELLED"}

        anim_data = armature_obj.animation_data
        if anim_data is None:
            anim_data = armature_obj.animation_data_create()

        # Remove any existing 'Offset' track first (so the old action
        # below isn't still referenced by a live strip when we delete
        # it), then always delete and recreate the action itself rather
        # than trying to clear its existing keyframes in place -
        # Blender 4.4+'s layered Action data model doesn't expose a
        # simple top-level '.fcurves' to clear directly, but the normal
        # keyframe_insert() API below handles creating a fresh action's
        # layers/slots/channels correctly on its own either way.
        for t in list(anim_data.nla_tracks):
            if t.name == "Offset":
                anim_data.nla_tracks.remove(t)

        old_action = bpy.data.actions.get("Offset")
        if old_action is not None:
            bpy.data.actions.remove(old_action, do_unlink=True)

        action = bpy.data.actions.new(name="Offset")
        action.use_fake_user = True

        # Reset EVERY pose bone to identity first, so the world-space
        # matrix math below is computed from a guaranteed-clean rest
        # pose rather than whatever arbitrary frame/pose happens to
        # currently be displayed - an offset is only meaningful (and
        # non-distorting) relative to true rest.
        for pb in armature_obj.pose.bones:
            pb.location = (0.0, 0.0, 0.0)
            pb.scale = (1.0, 1.0, 1.0)
            if pb.rotation_mode == "QUATERNION":
                pb.rotation_quaternion = (1.0, 0.0, 0.0, 0.0)
            elif pb.rotation_mode == "AXIS_ANGLE":
                pb.rotation_axis_angle = (0.0, 0.0, 1.0, 0.0)
            else:
                pb.rotation_euler = (0.0, 0.0, 0.0)
        context.view_layer.update()

        # Shift each target bone by the offset in true WORLD/scene
        # space along the chosen axis (not raw armature-local space,
        # and not raw local .location) via its matrix, so the result
        # is correct regardless of any rotation on the bone chain OR
        # on the armature OBJECT itself (very common after an FBX
        # Y-up/Z-up import conversion) - Blender derives the correct
        # local location/rotation/scale automatically from this
        # assignment. The axis picker exists specifically so you can
        # find, by trial, whichever axis actually corresponds to
        # scene-vertical (or whatever direction you need) for a given
        # armature, rather than assuming Z always is one.
        world_vec = mathutils.Vector((0.0, 0.0, 0.0))
        world_vec[axis_index] = offset_amount
        local_offset = armature_obj.matrix_world.to_3x3().inverted() @ world_vec
        translation = mathutils.Matrix.Translation(local_offset)
        for pb in target_bones:
            pb.matrix = translation @ pb.matrix

        original_action = anim_data.action
        anim_data.action = action
        for pb in target_bones:
            pb.keyframe_insert(data_path="location", frame=1)
        anim_data.action = original_action

        track = anim_data.nla_tracks.new()
        track.name = "Offset"

        frame_end = max(context.scene.frame_end, 250)
        strip = track.strips.new(name="Offset", start=1, action=action)
        strip.name = "Offset"
        strip.frame_end = frame_end
        strip.blend_type = blend_type
        strip.extrapolation = "HOLD"

        self.report(
            {"INFO"},
            f"Offset track ready on '{armature_obj.name}': {offset_amount:+.3f} on axis "
            f"{props.zo_axis} across {len(target_bones)} bone(s) directly under 'root', "
            f"blend={blend_type}",
        )
        return {"FINISHED"}


# ---------------------------------------------------------------------
# Prepare Viewport: operator
# ---------------------------------------------------------------------

class MHO_OT_prepare_viewport(Operator):
    """Set every armature's viewport display type to Stick, set the
    3D Viewport's Weight Paint overlay opacity/Zero Weights display,
    and switch the viewport to Material Preview shading"""
    bl_idname = "mho.prepare_viewport"
    bl_label = "Prepare Viewport"
    bl_description = (
        "Set all armatures to Stick display, set the Weight Paint overlay "
        "opacity to 0.8 with Zero Weights display set to Active, and switch "
        "the viewport to Material Preview shading"
    )
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        scene_only = context.scene.mho_props.armature_stick_scene_only
        count = 0

        if scene_only:
            seen_data = set()
            for obj in context.scene.objects:
                if obj.type != "ARMATURE":
                    continue
                arm_data = obj.data
                if arm_data is None or arm_data.name in seen_data:
                    continue
                seen_data.add(arm_data.name)
                if arm_data.display_type != "STICK":
                    arm_data.display_type = "STICK"
                    count += 1
        else:
            for arm_data in bpy.data.armatures:
                if arm_data.display_type != "STICK":
                    arm_data.display_type = "STICK"
                    count += 1

        set_weight_paint_overlay(context, opacity=0.8, zero_weights="ACTIVE")
        shading_set = set_viewport_shading(context, "MATERIAL")

        stick_note = f"{count} armature(s) set to Stick" if count else "armatures already Stick"
        msg = f"Viewport prepared: {stick_note}, Weight Paint overlay 0.8/Active"
        if shading_set:
            msg += ", shading set to Material Preview"
        else:
            self.report({"WARNING"}, "Couldn't set viewport shading - no 3D Viewport context found")
        self.report({"INFO"}, msg)

        return {"FINISHED"}


class MHO_OT_render_pose_snapshot(Operator):
    """Render the active camera at a fixed 300x420, with depth of
    field and motion blur forced off, and save it as a timestamped
    PNG next to the current .blend file"""
    bl_idname = "mho.render_pose_snapshot"
    bl_label = "Render Pose Snapshot"
    bl_description = (
        "Render the active camera at 300x420 with depth of field and motion blur "
        "disabled, and save it as 'Pose_<timestamp>.png' next to the current .blend "
        "file. All render settings touched are restored afterward"
    )
    bl_options = {"REGISTER"}

    @classmethod
    def poll(cls, context):
        return bool(bpy.data.filepath) and context.scene.camera is not None

    def execute(self, context):
        if not bpy.data.filepath:
            self.report({"ERROR"}, "Save the .blend file first - the snapshot saves next to it")
            return {"CANCELLED"}

        camera_obj = context.scene.camera
        if camera_obj is None:
            self.report({"ERROR"}, "No active camera set for this scene")
            return {"CANCELLED"}

        scene = context.scene
        render = scene.render

        # Remember everything we're about to touch so it can all be put
        # back exactly, regardless of success or failure below.
        orig_res_x = render.resolution_x
        orig_res_y = render.resolution_y
        orig_res_percent = render.resolution_percentage
        orig_file_format = render.image_settings.file_format
        orig_color_mode = render.image_settings.color_mode
        orig_filepath = render.filepath
        orig_use_motion_blur = render.use_motion_blur

        cam_data = camera_obj.data
        orig_use_dof = cam_data.dof.use_dof

        blend_dir = os.path.dirname(bpy.data.filepath)
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        out_path = os.path.join(blend_dir, f"Pose_{timestamp}.png")

        try:
            render.resolution_x = 300
            render.resolution_y = 420
            render.resolution_percentage = 100
            render.image_settings.file_format = "PNG"
            render.use_motion_blur = False
            cam_data.dof.use_dof = False
            render.filepath = out_path

            bpy.ops.render.render(write_still=True)
        except RuntimeError as exc:
            self.report({"ERROR"}, f"Render failed: {exc}")
            return {"CANCELLED"}
        finally:
            render.resolution_x = orig_res_x
            render.resolution_y = orig_res_y
            render.resolution_percentage = orig_res_percent
            render.image_settings.file_format = orig_file_format
            render.image_settings.color_mode = orig_color_mode
            render.filepath = orig_filepath
            render.use_motion_blur = orig_use_motion_blur
            cam_data.dof.use_dof = orig_use_dof

        self.report({"INFO"}, f"Saved pose snapshot: {os.path.basename(out_path)}")
        return {"FINISHED"}


# ---------------------------------------------------------------------
# Weight Transfer: operator
# ---------------------------------------------------------------------

class MHO_OT_transfer_weights(Operator):
    bl_idname = "mho.transfer_weights"
    bl_label = "Transfer Weights"
    bl_description = "Strip target's vertex groups/armature modifier, then transfer weights from source (nearest face interpolated, by name)"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        props = context.scene.mho_props
        source_obj = props.wt_source_obj
        target_obj = props.wt_target_obj

        if not source_obj or not target_obj:
            self.report({"ERROR"}, "Pick both a Source and a Target mesh.")
            return {"CANCELLED"}
        if source_obj.type != "MESH" or target_obj.type != "MESH":
            self.report({"ERROR"}, "Source and Target must both be mesh objects.")
            return {"CANCELLED"}
        if source_obj == target_obj:
            self.report({"ERROR"}, "Source and Target can't be the same object.")
            return {"CANCELLED"}
        if len(source_obj.vertex_groups) == 0:
            self.report({"ERROR"}, f"Source object '{source_obj.name}' has no vertex groups to transfer.")
            return {"CANCELLED"}

        strip_target(target_obj)

        ray_radius = props.wt_ray_radius_mm / 1000.0  # mm -> Blender units (meters at default scale)

        try:
            transfer_weights(context, source_obj, target_obj, ray_radius)
        except RuntimeError as e:
            self.report({"ERROR"}, str(e))
            return {"CANCELLED"}

        if len(target_obj.vertex_groups) == 0:
            self.report(
                {"ERROR"},
                "data_transfer reported success but the target still has 0 vertex groups. "
                "Check the system console (Window > Toggle System Console) for any warnings it printed."
            )
            return {"CANCELLED"}

        if props.wt_do_smooth:
            smooth_target_weights(context, target_obj, props.wt_smooth_factor, props.wt_smooth_repeat)

        armature_note = ""
        armature_linked = False
        if props.wt_add_armature_mod:
            ok, msg = add_armature_modifier(target_obj, source_obj)
            if ok:
                armature_note = f", armature '{msg}' linked"
                armature_linked = True
            else:
                # Non-fatal - weights already transferred successfully.
                self.report({"WARNING"}, msg)

        sort_note = ""
        if props.wt_sort_by_bone_hierarchy:
            if armature_linked:
                try:
                    sort_vertex_groups_by_bone_hierarchy(context, target_obj)
                    sort_note = ", sorted by bone hierarchy"
                except RuntimeError as e:
                    self.report({"WARNING"}, f"Couldn't sort vertex groups by bone hierarchy: {e}")
            else:
                self.report(
                    {"WARNING"},
                    "Skipped sorting by bone hierarchy - no armature was linked "
                    "(enable 'Add Armature Modifier After Transfer', or link one manually first)."
                )

        self.report(
            {"INFO"},
            f"Transferred weights: '{source_obj.name}' -> '{target_obj.name}'"
            + (" (smoothed)" if props.wt_do_smooth else "")
            + armature_note
            + sort_note
        )
        return {"FINISHED"}


class MHO_OT_smooth_vertex_weights(Operator):
    """Run Vertex Group Smooth across every vertex group on the active
    mesh, any time - not just right after a Weight Transfer"""

    bl_idname = "mho.smooth_vertex_weights"
    bl_label = "Smooth All Vertex Groups"
    bl_description = (
        "Run Vertex Group Smooth across every vertex group on the active mesh. With "
        "'Selected Vertices Only' on, only vertices currently selected are affected; "
        "otherwise the whole mesh is smoothed"
    )
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        return obj is not None and obj.type == "MESH" and len(obj.vertex_groups) > 0

    def execute(self, context):
        props = context.scene.mho_props
        obj = context.active_object

        if not obj.vertex_groups:
            self.report({"ERROR"}, f"'{obj.name}' has no vertex groups")
            return {"CANCELLED"}

        if props.ws_selected_verts_only and not any(v.select for v in obj.data.vertices):
            self.report(
                {"ERROR"},
                "No vertices selected - turn off 'Selected Vertices Only' or select some first",
            )
            return {"CANCELLED"}

        smooth_all_vertex_groups(
            context, obj, props.ws_smooth_factor, props.ws_smooth_repeat, props.ws_selected_verts_only
        )

        scope = "selected vertices" if props.ws_selected_verts_only else "the whole mesh"
        self.report(
            {"INFO"},
            f"Smoothed {len(obj.vertex_groups)} vertex group(s) on '{obj.name}' ({scope})",
        )
        return {"FINISHED"}


class MHO_OT_smooth_active_vertex_group(Operator):
    """Run Vertex Group Smooth on just the active vertex group (the one
    highlighted in the Vertex Groups list), any time"""

    bl_idname = "mho.smooth_active_vertex_group"
    bl_label = "Smooth Active Vertex Group"
    bl_description = (
        "Run Vertex Group Smooth on just the active vertex group (the one highlighted in "
        "the Vertex Groups list). With 'Selected Vertices Only' on, only vertices currently "
        "selected are affected; otherwise the whole mesh is smoothed"
    )
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        return obj is not None and obj.type == "MESH" and obj.vertex_groups.active is not None

    def execute(self, context):
        props = context.scene.mho_props
        obj = context.active_object

        active_group = obj.vertex_groups.active
        if active_group is None:
            self.report({"ERROR"}, f"'{obj.name}' has no active vertex group")
            return {"CANCELLED"}

        if props.ws_selected_verts_only and not any(v.select for v in obj.data.vertices):
            self.report(
                {"ERROR"},
                "No vertices selected - turn off 'Selected Vertices Only' or select some first",
            )
            return {"CANCELLED"}

        smooth_all_vertex_groups(
            context,
            obj,
            props.ws_smooth_factor,
            props.ws_smooth_repeat,
            props.ws_selected_verts_only,
            only_active=True,
        )

        scope = "selected vertices" if props.ws_selected_verts_only else "the whole mesh"
        self.report(
            {"INFO"},
            f"Smoothed '{active_group.name}' on '{obj.name}' ({scope})",
        )
        return {"FINISHED"}


class MHO_OT_rename_vgroups_for_mirror(Operator):
    """Set up the active mesh for X-Mirror weight painting / Symmetrize:
    rename L/R vertex groups to end in .L/.R, turn on Blender's X
    Mirror toggle, lock the deforming armature to its Root rest pose,
    and (since this game's armatures put the mirror axis on Y, not
    Blender's fixed X) temporarily rotate the mesh data so left/right
    lines up with X"""

    bl_idname = "mho.rename_vgroups_for_mirror"
    bl_label = "Rename for Mirror"
    bl_description = (
        "Rename this object's L/R vertex groups to end in .L/.R (e.g. 'g_r_shoulder' -> "
        "'g_shoulder.R'), turn on Blender's X Mirror toggle, lock the deforming armature "
        "to its Root rest pose, and rotate the mesh data so left/right lines up with "
        "Blender's fixed X-Mirror axis. Press 'Revert Names' afterward to put everything "
        "back exactly"
    )
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        return (
            obj is not None
            and obj.type == "MESH"
            and len(obj.vertex_groups) > 0
            and _MHO_VGROUP_RENAME_KEY not in obj
        )

    def execute(self, context):
        props = context.scene.mho_props
        obj = context.active_object

        # Rotation (and mode_set/select_all in general) requires Object
        # Mode - force it regardless of what mode the user is currently
        # in (Weight Paint is the common one here) so this never fails
        # partway through with a "context is incorrect" error.
        if context.mode != "OBJECT":
            bpy.ops.object.mode_set(mode="OBJECT")

        state = {
            "vgroups": {},
            "rotation_degrees": 0.0,
            "armature_name": None,
            "nla_mutes": {},
            "original_frame": context.scene.frame_current,
            "had_root": False,
            "prev_use_mirror_x": obj.data.use_mirror_x,
        }

        # --- 1. Rename L/R vertex groups ---
        for vg in obj.vertex_groups:
            new_name = vgroup_mirror_name(vg.name)
            if new_name is None or new_name == vg.name:
                continue
            if obj.vertex_groups.get(new_name) is not None:
                self.report({"WARNING"}, f"Skipped '{vg.name}' - '{new_name}' already exists")
                continue
            state["vgroups"][new_name] = vg.name
            vg.name = new_name

        if not state["vgroups"]:
            self.report({"WARNING"}, "No vertex groups matched the g_l_/g_r_ naming pattern")
            return {"CANCELLED"}

        # --- 2. Lock the deforming armature to its Root rest pose ---
        if props.vg_lock_rest_pose:
            armature_obj = find_deforming_armature(obj)
            if armature_obj is None:
                self.report({"WARNING"}, "No deforming armature found - skipped rest-pose lock")
            else:
                mutes, orig_frame, had_root = lock_armature_to_root(armature_obj)
                if had_root:
                    state["armature_name"] = armature_obj.name
                    state["nla_mutes"] = mutes
                    state["original_frame"] = orig_frame
                    state["had_root"] = True
                else:
                    self.report(
                        {"WARNING"},
                        f"No 'Root' NLA track on '{armature_obj.name}' - skipped rest-pose lock "
                        "(Actions -> NLA panel can add one)",
                    )

        # --- 3. Rotate the mesh DATA so left/right lines up with X ---
        degrees = props.vg_axis_correction_degrees
        if degrees != 0:
            rotate_mesh_data(obj, degrees)
            state["rotation_degrees"] = degrees

        # --- 4. Turn on Blender's own X-Mirror toggle ---
        # Renaming to .L/.R only makes Blender CAPABLE of finding the
        # pairs - live mirrored painting also needs this switched on.
        obj.data.use_mirror_x = True

        obj[_MHO_VGROUP_RENAME_KEY] = json.dumps(state)

        msg = f"Renamed {len(state['vgroups'])} vertex group(s) for mirroring, enabled X Mirror"
        if state["rotation_degrees"]:
            msg += f", rotated mesh data {state['rotation_degrees']}\u00b0"
        if state["had_root"]:
            msg += ", locked to Root rest pose"
        self.report({"INFO"}, msg)
        return {"FINISHED"}


class MHO_OT_revert_vgroup_names(Operator):
    """Undo Rename for Mirror exactly: restore vertex group names,
    un-rotate the mesh data, and restore the armature's NLA track
    mute states and current frame"""

    bl_idname = "mho.revert_vgroup_names"
    bl_label = "Revert Names"
    bl_description = (
        "Undo Rename for Mirror: put vertex group names back to match the armature's "
        "actual bone names, un-rotate the mesh data, and restore the armature's NLA "
        "track states"
    )
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        return obj is not None and obj.type == "MESH" and _MHO_VGROUP_RENAME_KEY in obj

    def execute(self, context):
        obj = context.active_object

        if context.mode != "OBJECT":
            bpy.ops.object.mode_set(mode="OBJECT")

        try:
            state = json.loads(obj[_MHO_VGROUP_RENAME_KEY])
        except (KeyError, ValueError):
            self.report({"ERROR"}, "Couldn't read the stored rename mapping")
            return {"CANCELLED"}

        # --- 1. Un-rotate the mesh data first (exact reverse) ---
        degrees = state.get("rotation_degrees", 0.0)
        if degrees:
            rotate_mesh_data(obj, -degrees)

        # --- 2. Restore vertex group names ---
        mapping = state.get("vgroups", {})
        reverted = 0
        for new_name, old_name in mapping.items():
            vg = obj.vertex_groups.get(new_name)
            if vg is None:
                self.report({"WARNING"}, f"'{new_name}' not found - may have been renamed again since")
                continue
            vg.name = old_name
            reverted += 1

        # --- 3. Restore the armature's NLA track states ---
        if state.get("had_root") and state.get("armature_name"):
            armature_obj = bpy.data.objects.get(state["armature_name"])
            if armature_obj is not None:
                restore_armature_nla(armature_obj, state.get("nla_mutes", {}), state.get("original_frame", 1))
            else:
                self.report({"WARNING"}, f"Armature '{state['armature_name']}' not found - couldn't restore NLA state")

        # --- 4. Restore the X-Mirror toggle to whatever it was before ---
        obj.data.use_mirror_x = state.get("prev_use_mirror_x", False)

        del obj[_MHO_VGROUP_RENAME_KEY]
        self.report({"INFO"}, f"Reverted {reverted} vertex group name(s)")
        return {"FINISHED"}


class MHO_OT_diagnose_mirror_axis(Operator):
    """Report which local axis (and sign) actually separates a mesh's
    .L/.R vertex group pairs, based on real vertex positions"""

    bl_idname = "mho.diagnose_mirror_axis"
    bl_label = "Diagnose Mirror Axis"
    bl_description = (
        "Compute the average position of each .L vertex group's weighted vertices vs its "
        ".R pair, and report which local axis (X/Y/Z) actually separates them"
    )
    bl_options = {"REGISTER"}

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        return obj is not None and obj.type == "MESH"

    def execute(self, context):
        obj = context.active_object

        dupes = find_duplicate_vgroup_names(obj)
        if dupes:
            self.report(
                {"ERROR"},
                f"Duplicate vertex group name(s) found: {', '.join(dupes)} - Blender allows "
                "this, but it means name-based lookup can silently grab the wrong (possibly "
                "empty) one. Rename or merge the duplicates first, then try again.",
            )
            return {"CANCELLED"}

        pairs = find_lr_group_pairs(obj)
        if not pairs:
            self.report(
                {"ERROR"},
                "No matched .L/.R vertex group pairs found - run Rename for Mirror first",
            )
            return {"CANCELLED"}

        result, per_pair_counts = detect_mirror_axis(obj, pairs)

        for line in (
            f"OK    {l_name} / {r_name}: L={l_cnt} weighted vert(s), R={r_cnt} weighted vert(s)"
            for l_name, r_name, l_cnt, r_cnt in per_pair_counts
        ):
            print(line)

        if result is None:
            empty_sides = []
            for l_name, r_name, l_cnt, r_cnt in per_pair_counts:
                if l_cnt == 0:
                    empty_sides.append(l_name)
                if r_cnt == 0:
                    empty_sides.append(r_name)
            self.report(
                {"ERROR"},
                f"No weighted vertices found on: {', '.join(empty_sides)} - see the System "
                "Console (Window > Toggle System Console) for the full per-pair breakdown",
            )
            return {"CANCELLED"}

        best_axis, diffs, l_centroid, r_centroid = result
        axis_names = "XYZ"

        print("OK    Centroid difference (L - R) by axis:")
        for i in range(3):
            marker = " <- picked" if i == best_axis else ""
            print(
                f"OK      {axis_names[i]}: L={l_centroid[i]:.3f}  R={r_centroid[i]:.3f}  "
                f"diff={diffs[i]:.3f}{marker}"
            )

        self.report(
            {"INFO"},
            f"X diff={diffs[0]:.2f}, Y diff={diffs[1]:.2f}, Z diff={diffs[2]:.2f} across "
            f"{len(pairs)} pair(s) - picked {axis_names[best_axis]} (largest), but check the "
            "System Console for all three before trusting it: a small natural asymmetry can "
            "outrank the true mirror axis if that axis's own separation happens to be even "
            "smaller for this particular set of vertices",
        )
        return {"FINISHED"}


class MHO_OT_diagnose_mirror_axis_geometry(Operator):
    """Determine the true mirror axis from the mesh's own geometry,
    independent of vertex group weight data entirely"""

    bl_idname = "mho.diagnose_mirror_axis_geometry"
    bl_label = "Diagnose Mirror Axis (Geometry)"
    bl_description = (
        "Reflect a sample of the mesh's own vertices around each axis and measure how well "
        "they land back on real geometry - the axis with the smallest mismatch is the true "
        "mirror axis. Doesn't look at vertex group data at all, so it's reliable even if the "
        ".L/.R groups are currently empty, mismatched, or scrambled from a previous run"
    )
    bl_options = {"REGISTER"}

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        return obj is not None and obj.type == "MESH"

    def execute(self, context):
        obj = context.active_object

        try:
            results = diagnose_symmetry_by_geometry(obj)
        except RuntimeError as exc:
            self.report({"ERROR"}, str(exc))
            return {"CANCELLED"}

        best_axis = min(range(3), key=lambda i: results[i][2])
        axis_names = "XYZ"

        print("OK    Geometric symmetry mismatch by axis (lower = better match):")
        for axis, center, avg_dist in results:
            marker = " <- picked (lowest mismatch)" if axis == best_axis else ""
            print(f"OK      {axis_names[axis]}: center={center:.4f}  avg mismatch={avg_dist:.5f}{marker}")

        self.report(
            {"INFO"},
            f"X mismatch={results[0][2]:.4f}, Y mismatch={results[1][2]:.4f}, "
            f"Z mismatch={results[2][2]:.4f} - true mirror axis is most likely "
            f"{axis_names[best_axis]} (lowest mismatch) - full breakdown printed to console",
        )
        return {"FINISHED"}


class MHO_OT_clear_console(Operator):
    """Open the System Console window if it isn't already open, clear
    it, and bring it to the front"""

    bl_idname = "mho.clear_console"
    bl_label = "Clear Console"
    bl_description = (
        "Open the System Console window if it isn't already open, clear it, and bring it "
        "to the front (Windows only)"
    )
    bl_options = {"REGISTER"}

    def execute(self, context):
        if os.name == "nt":
            try:
                import ctypes

                hwnd = ctypes.windll.kernel32.GetConsoleWindow()
                if not hwnd:
                    # No console currently attached - open one via
                    # Blender's own toggle rather than a blind call,
                    # since console_toggle() flips whatever state it's
                    # currently in (calling it while already open would
                    # close it instead of opening it).
                    bpy.ops.wm.console_toggle()
                    hwnd = ctypes.windll.kernel32.GetConsoleWindow()
                if hwnd:
                    ctypes.windll.user32.SetForegroundWindow(hwnd)
            except Exception:
                pass

        os.system("cls" if os.name == "nt" else "clear")

        self.report({"INFO"}, "Console cleared")
        return {"FINISHED"}


class MHO_OT_wipe_vgroup_side(Operator):
    """Fully clear every destination-side vertex group among matched
    .L/.R pairs, without copying anything - useful to reset before
    re-testing with a different axis"""

    bl_idname = "mho.wipe_vgroup_side"
    bl_label = "Wipe Destination Side"
    bl_description = (
        "Clear every vertex weight from the destination side of each matched .L/.R group "
        "pair - .R if Direction is L -> R, .L if R -> L - without copying anything. Useful "
        "to reset cleanly before re-testing a mirror with a different axis"
    )
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        return obj is not None and obj.type == "MESH"

    def execute(self, context):
        props = context.scene.mho_props
        obj = context.active_object

        dupes = find_duplicate_vgroup_names(obj)
        if dupes:
            self.report(
                {"ERROR"},
                f"Duplicate vertex group name(s) found: {', '.join(dupes)} - rename or merge "
                "the duplicates first, then try again",
            )
            return {"CANCELLED"}

        pairs = find_lr_group_pairs(obj)
        if not pairs:
            self.report(
                {"ERROR"},
                "No matched .L/.R vertex group pairs found - run Rename for Mirror first",
            )
            return {"CANCELLED"}

        direction = props.mw_direction
        side = "R" if direction == "L_TO_R" else "L"
        total_cleared = 0

        for l_name, r_name in pairs:
            dst_name = r_name if direction == "L_TO_R" else l_name
            dst_group = obj.vertex_groups[dst_name]
            cleared = clear_vertex_group_weights(obj, dst_group)
            total_cleared += cleared
            print(f"OK    wiped {dst_name}: {cleared} vertex weight(s) removed")

        self.report(
            {"INFO"},
            f"Wiped {total_cleared} vertex weight(s) across {len(pairs)} .{side} group(s)",
        )
        return {"FINISHED"}


class MHO_OT_wipe_active_group(Operator):
    """Fully clear every vertex weight from the active vertex group
    (the one highlighted in the Vertex Groups list), without touching
    any other group"""

    bl_idname = "mho.wipe_active_group"
    bl_label = "Wipe Active Group"
    bl_description = (
        "Clear every vertex weight from the active vertex group (the one highlighted in "
        "the Vertex Groups list), without touching any other group"
    )
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        return obj is not None and obj.type == "MESH" and obj.vertex_groups.active is not None

    def execute(self, context):
        obj = context.active_object
        active_group = obj.vertex_groups.active
        if active_group is None:
            self.report({"ERROR"}, f"'{obj.name}' has no active vertex group")
            return {"CANCELLED"}

        cleared = clear_vertex_group_weights(obj, active_group)
        print(f"OK    wiped {active_group.name}: {cleared} vertex weight(s) removed")

        self.report(
            {"INFO"},
            f"Wiped {cleared} vertex weight(s) from '{active_group.name}'",
        )
        return {"FINISHED"}


class MHO_OT_symmetrize_weights_data_transfer(Operator):
    """Symmetrize every matched vertex group pair using Blender's own
    Mirror + Data Transfer modifiers - smoothly interpolated, not the
    blocky nearest-single-vertex result Mirror Weights (Custom) can
    produce"""

    bl_idname = "mho.symmetrize_weights_data_transfer"
    bl_label = "Mirror All Groups"
    bl_description = (
        "Duplicate the mesh, rebuild one side as a clean geometric mirror (Mirror modifier), "
        "then project every vertex group's weights from that clean reference back onto the "
        "original mesh (Data Transfer, Nearest Face Interpolated) - smoothly interpolated "
        "rather than snapped from a single nearest vertex. The temporary reference object is "
        "deleted automatically afterward"
    )
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        return obj is not None and obj.type == "MESH"

    def execute(self, context):
        props = context.scene.mho_props
        obj = context.active_object

        original_mode = obj.mode
        if original_mode != "OBJECT":
            bpy.ops.object.mode_set(mode="OBJECT")

        dupes = find_duplicate_vgroup_names(obj)
        if dupes:
            self.report(
                {"ERROR"},
                f"Duplicate vertex group name(s) found: {', '.join(dupes)} - rename or merge "
                "the duplicates first, then try again",
            )
            if original_mode != "OBJECT":
                bpy.ops.object.mode_set(mode=original_mode)
            return {"CANCELLED"}

        axis_index = "XYZ".index(props.mw_mirror_axis)

        try:
            log = symmetrize_weights_data_transfer(
                context, obj, axis_index, props.mw_direction, props.mw_use_clipping,
                props.mw_invert_source_side
            )
        except RuntimeError as exc:
            self.report({"ERROR"}, str(exc))
            if original_mode != "OBJECT":
                bpy.ops.object.mode_set(mode=original_mode)
            return {"CANCELLED"}

        for line in log:
            print(line)

        if original_mode != "OBJECT":
            context.view_layer.objects.active = obj
            bpy.ops.object.mode_set(mode=original_mode)

        self.report({"INFO"}, log[0].replace("OK    ", ""))
        return {"FINISHED"}


class MHO_OT_mirror_active_group(Operator):
    """Symmetrize just the matched .L/.R pair the active vertex group
    belongs to, using the same Mirror + Data Transfer approach as
    Mirror All Groups"""

    bl_idname = "mho.mirror_active_group"
    bl_label = "Mirror Active Group"
    bl_description = (
        "Same as Mirror All Groups, but restricted to just the matched .L/.R pair the "
        "active vertex group (the one highlighted in the Vertex Groups list) belongs to"
    )
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        return obj is not None and obj.type == "MESH" and obj.vertex_groups.active is not None

    def execute(self, context):
        props = context.scene.mho_props
        obj = context.active_object

        active_group = obj.vertex_groups.active
        if active_group is None:
            self.report({"ERROR"}, f"'{obj.name}' has no active vertex group")
            return {"CANCELLED"}

        original_mode = obj.mode
        if original_mode != "OBJECT":
            bpy.ops.object.mode_set(mode="OBJECT")

        dupes = find_duplicate_vgroup_names(obj)
        if dupes:
            self.report(
                {"ERROR"},
                f"Duplicate vertex group name(s) found: {', '.join(dupes)} - rename or merge "
                "the duplicates first, then try again",
            )
            if original_mode != "OBJECT":
                bpy.ops.object.mode_set(mode=original_mode)
            return {"CANCELLED"}

        active_name = active_group.name
        target_pair = None
        for l_name, r_name in find_lr_group_pairs(obj):
            if active_name in (l_name, r_name):
                target_pair = (l_name, r_name)
                break

        if target_pair is None:
            self.report(
                {"ERROR"},
                f"'{active_name}' isn't part of a matched .L/.R pair - run Rename for Mirror first",
            )
            if original_mode != "OBJECT":
                bpy.ops.object.mode_set(mode=original_mode)
            return {"CANCELLED"}

        axis_index = "XYZ".index(props.mw_mirror_axis)

        try:
            log = symmetrize_weights_data_transfer(
                context, obj, axis_index, props.mw_direction, props.mw_use_clipping,
                props.mw_invert_source_side, only_group_pair=target_pair,
            )
        except RuntimeError as exc:
            self.report({"ERROR"}, str(exc))
            if original_mode != "OBJECT":
                bpy.ops.object.mode_set(mode=original_mode)
            return {"CANCELLED"}

        for line in log:
            print(line)

        if original_mode != "OBJECT":
            context.view_layer.objects.active = obj
            bpy.ops.object.mode_set(mode=original_mode)

        self.report({"INFO"}, log[0].replace("OK    ", ""))
        return {"FINISHED"}


class MHO_OT_mirror_weights_custom(Operator):
    """Copy vertex group weights across L/R pairs directly by position
    (reflected across a chosen local axis), bypassing Blender's X-only
    mirror entirely"""

    bl_idname = "mho.mirror_weights_custom"
    bl_label = "Mirror Weights (Custom)"
    bl_description = (
        "For every matched .L/.R vertex group pair, REPLACE the entire destination side "
        "with weights copied from the nearest source vertex (by position, reflected across "
        "the chosen axis) - clears old destination data first, so this is safe to re-run "
        "after changing the axis, but any destination data not recreated is genuinely gone"
    )
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        return obj is not None and obj.type == "MESH"

    def execute(self, context):
        props = context.scene.mho_props
        obj = context.active_object

        dupes = find_duplicate_vgroup_names(obj)
        if dupes:
            self.report(
                {"ERROR"},
                f"Duplicate vertex group name(s) found: {', '.join(dupes)} - rename or merge "
                "the duplicates first, then try again",
            )
            return {"CANCELLED"}

        axis_index = "XYZ".index(props.mw_mirror_axis)

        try:
            pair_count, copied, log = mirror_weights_custom(obj, axis_index, props.mw_direction)
        except RuntimeError as exc:
            self.report({"ERROR"}, str(exc))
            return {"CANCELLED"}

        for line in log:
            print(line)

        plane_note = log[0].replace("OK    ", "") if log else ""
        self.report(
            {"INFO"},
            f"Mirrored {copied} vertex weight(s) across {pair_count} group pair(s) "
            f"({plane_note})",
        )
        return {"FINISHED"}


# ---------------------------------------------------------------------
# MFF Model Prep: operator
# ---------------------------------------------------------------------

class MHO_OT_model_prep_scale_rotate(Operator):
    """Scale up, rotate 90 on Z, and apply transforms on each selected
    mesh individually - without joining them - so the parts are large
    enough to see and pick from for the join step"""

    bl_idname = "mho.model_prep_scale_rotate"
    bl_label = "Scale & Rotate"
    bl_description = (
        "Scale up, rotate on Z, and apply transforms on each selected "
        "mesh individually (no join yet), so tiny imported parts "
        "become visible enough to pick which ones to join next"
    )
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context):
        return any(o.type == "MESH" for o in context.selected_objects)

    def execute(self, context):
        import math
        import mathutils

        props = context.scene.mho_props
        scale_factor = props.mp_scale_factor
        rotate_z_degrees = props.mp_rotate_z_degrees

        mesh_objs = [o for o in context.selected_objects if o.type == "MESH"]
        if not mesh_objs:
            self.report({"ERROR"}, "No mesh objects selected")
            return {"CANCELLED"}

        # --- 1. Scale each mesh individually ---
        for o in mesh_objs:
            o.scale = (
                o.scale[0] * scale_factor,
                o.scale[1] * scale_factor,
                o.scale[2] * scale_factor,
            )

        # matrix_world is cached and only recomputed on a depsgraph
        # update - without this, reading it in the next loop would
        # return the pre-scale matrix and the rotation step below would
        # silently overwrite the scale change we just made.
        context.view_layer.update()

        # --- 2. Rotate each mesh individually ---
        # These parts are still parented at this point (unparenting now
        # happens later, in Join & Merge), so rotation is done in world
        # space via matrix_world - not the local rotation_euler - to
        # guarantee it always turns around true global Z regardless of
        # the parent's own orientation (e.g. an FBX-import root that's
        # rotated -90 on X for the Z-up/Y-up conversion).
        world_z_rotation = mathutils.Matrix.Rotation(math.radians(rotate_z_degrees), 4, "Z")
        for o in mesh_objs:
            o.matrix_world = world_z_rotation @ o.matrix_world

        # --- 3. Apply transforms (loc/rot/scale) on all of them at once ---
        bpy.ops.object.select_all(action="DESELECT")
        for o in mesh_objs:
            o.select_set(True)
        context.view_layer.objects.active = mesh_objs[0]
        bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)

        self.report(
            {"INFO"},
            f"Scaled x{scale_factor} and rotated {rotate_z_degrees}Â° on "
            f"{len(mesh_objs)} mesh(es). Select which parts to join next.",
        )
        return {"FINISHED"}


class MHO_OT_model_prep_join_merge(Operator):
    """Join the selected meshes into one object, unparent it, weld
    overlapping verts, and strip any custom split normals so shading
    rebuilds clean"""

    bl_idname = "mho.model_prep_join_merge"
    bl_label = "Join & Merge"
    bl_description = (
        "Join the selected meshes into one object, unparent it, merge "
        "vertices by distance, and strip custom split normals"
    )
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context):
        return any(o.type == "MESH" for o in context.selected_objects)

    def execute(self, context):
        props = context.scene.mho_props
        merge_distance = props.mp_merge_distance

        mesh_objs = [o for o in context.selected_objects if o.type == "MESH"]
        if not mesh_objs:
            self.report({"ERROR"}, "No mesh objects selected")
            return {"CANCELLED"}

        # --- 1. Join into one mesh ---
        bpy.ops.object.select_all(action="DESELECT")
        for o in mesh_objs:
            o.select_set(True)
        context.view_layer.objects.active = mesh_objs[0]

        if len(mesh_objs) > 1:
            bpy.ops.object.join()

        obj = context.view_layer.objects.active

        # --- 2. Unparent (keep transform) ---
        if obj.parent is not None:
            bpy.ops.object.select_all(action="DESELECT")
            obj.select_set(True)
            context.view_layer.objects.active = obj
            bpy.ops.object.parent_clear(type="CLEAR_KEEP_TRANSFORM")

        # --- 3. Merge vertices by distance ---
        bpy.ops.object.mode_set(mode="EDIT")
        bpy.ops.mesh.select_all(action="SELECT")
        bpy.ops.mesh.remove_doubles(threshold=merge_distance)
        bpy.ops.object.mode_set(mode="OBJECT")

        # --- 4. Strip custom split normals ---
        bpy.ops.mesh.customdata_custom_splitnormals_clear()

        self.report(
            {"INFO"},
            f"Join & merge complete on '{obj.name}' (merge distance {merge_distance})",
        )
        return {"FINISHED"}


class MHO_OT_symmetrical_sculpt_adjust(Operator):
    """Enter Sculpt Mode on the active mesh, switch to the Elastic
    Grab tool, and set sculpt symmetry to the chosen single axis"""
    bl_idname = "mho.symmetrical_sculpt_adjust"
    bl_label = "Symmetrical Sculpt Adjust"
    bl_description = (
        "Enter Sculpt Mode on the selected mesh, switch to the Elastic "
        "Grab tool, and set sculpt symmetry to the chosen axis only"
    )
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context):
        return context.active_object is not None and context.active_object.type == "MESH"

    def execute(self, context):
        obj = context.active_object
        axis = context.scene.mho_props.sculpt_symmetry_axis

        if context.mode != "SCULPT":
            mode_result = bpy.ops.object.mode_set(mode="SCULPT")
            if "FINISHED" not in mode_result:
                self.report(
                    {"ERROR"},
                    f"Couldn't enter Sculpt Mode on '{obj.name}' (mode_set returned {mode_result})",
                )
                return {"CANCELLED"}

        # Set symmetry first so it always applies, even if the brush
        # switch below fails for any reason. In this Blender version the
        # sculpt-mode symmetry header buttons are bound to the Object's
        # use_mesh_mirror_x/y/z properties (not the older Sculpt.use_symmetry_y),
        # confirmed via the header button's own copied data path.
        # Only the chosen axis is turned on; the other two are explicitly
        # turned off, so the result is always "single axis only"
        # regardless of prior state.
        obj_name = obj.name
        obj.use_mesh_mirror_x = (axis == "X")
        obj.use_mesh_mirror_y = (axis == "Y")
        obj.use_mesh_mirror_z = (axis == "Z")

        # Also set the legacy Sculpt properties for good measure - harmless
        # if unused, but some tools/scripts may still read them.
        try:
            sculpt = context.scene.tool_settings.sculpt
            sculpt.use_symmetry_x = (axis == "X")
            sculpt.use_symmetry_y = (axis == "Y")
            sculpt.use_symmetry_z = (axis == "Z")
        except Exception:
            pass

        # Safety net: on some Blender builds, entering Sculpt Mode for the
        # first time in a session finishes initializing tool state slightly
        # after this operator returns, which can revert the lines above.
        # Re-apply once on the next event-loop tick so it sticks regardless.
        def _reapply_symmetry_axis():
            try:
                ob = bpy.data.objects.get(obj_name)
                if ob is not None:
                    ob.use_mesh_mirror_x = (axis == "X")
                    ob.use_mesh_mirror_y = (axis == "Y")
                    ob.use_mesh_mirror_z = (axis == "Z")
            except Exception:
                pass
            return None

        bpy.app.timers.register(_reapply_symmetry_axis, first_interval=0.1)

        # Blender 4.3+ moved sculpt brushes to an asset-based system.
        # ToolSettings.sculpt.brush is now read-only - brushes have to be
        # activated through brush.asset_activate, referencing them by
        # their asset-library path rather than assigned directly.
        # A brush that's already local to this .blend (e.g. because it's
        # been used before) lives under the LOCAL library as "Brush/<name>";
        # otherwise it comes from Blender's bundled Essentials library at
        # this fixed sub-path.
        brush_names = ("Elastic Grab", "Elastic Deform")

        # If the active brush is already one of these, skip the switch
        # attempts entirely - they're a known no-op here and just spam
        # the console with "No asset found" errors.
        current_brush = context.tool_settings.sculpt.brush
        current_name = current_brush.name if current_brush else None

        switched = False
        method_note = ""

        if current_name in brush_names:
            switched = True
            method_note = f"brush already '{current_name}'"
        else:
            # Confirmed via bpy.context.tool_settings.sculpt.brush_asset_reference
            # on this Blender build: the Essentials mesh-sculpt brushes live in
            # "essentials_brushes-mesh_sculpt.blend", not "essentials_brushes.blend".
            activate_attempts = []
            for name in brush_names:
                activate_attempts.append(("LOCAL", "", f"Brush/{name}"))
                activate_attempts.append(
                    ("ESSENTIALS", "", f"brushes/essentials_brushes-mesh_sculpt.blend/Brush/{name}")
                )
                activate_attempts.append(
                    ("ESSENTIALS", "", f"brushes/essentials_brushes.blend/Brush/{name}")
                )

            for library_type, library_id, relative_id in activate_attempts:
                try:
                    result = bpy.ops.brush.asset_activate(
                        asset_library_type=library_type,
                        asset_library_identifier=library_id,
                        relative_asset_identifier=relative_id,
                    )
                except Exception:
                    continue
                if "FINISHED" in result:
                    switched = True
                    method_note = f"brush '{relative_id}' ({library_type})"
                    break

        if not switched:
            self.report(
                {"INFO"},
                f"Sculpting '{obj.name}': symmetry Y-only (couldn't switch to Elastic Grab/Elastic Deform brush)",
            )
        else:
            self.report(
                {"INFO"},
                f"Sculpting '{obj.name}': switched to {method_note}, symmetry Y-only",
            )

        return {"FINISHED"}


# ---------------------------------------------------------------------
# Shader Slot Maps: core logic
# ---------------------------------------------------------------------

def _ssm_get_or_create_node(nodes, node_type, name, location=(0, 0)):
    node = nodes.get(name)
    if node is None:
        node = nodes.new(node_type)
        node.name = name
        node.location = location
    return node


def _ssm_find_principled_bsdf(nodes):
    for n in nodes:
        if n.type == "BSDF_PRINCIPLED":
            return n
    return None


def _ssm_autodetect_images(mat):
    """If the ssm_* pickers are still unset but this material's node
    tree already has images wired into the matching sockets (e.g. an
    imported mesh that came in with textures already hooked up), pull
    those images into the ssm_* properties so the panel shows them
    instead of a blank 'Open' box. Only fills in properties that are
    still empty. Must be called from an operator, not from a Panel's
    draw() - Blender doesn't allow writing to ID data-blocks (like a
    Material property) from inside draw(). Returns a list naming which
    slots were newly filled in, e.g. ["diffuse", "normal"]."""

    found = []

    if not mat.use_nodes or mat.node_tree is None:
        return found

    nodes = mat.node_tree.nodes
    bsdf = _ssm_find_principled_bsdf(nodes)
    if bsdf is None:
        return found

    used_images = set()

    if not mat.ssm_diffuse_image:
        base_color_input = bsdf.inputs.get("Base Color")
        if base_color_input is not None and base_color_input.is_linked:
            src_node = base_color_input.links[0].from_node
            if src_node.type == "TEX_IMAGE" and src_node.image:
                mat.ssm_diffuse_image = src_node.image
                used_images.add(src_node.image)
                found.append("diffuse")

    if not mat.ssm_normal_image:
        normal_input = bsdf.inputs.get("Normal")
        if normal_input is not None and normal_input.is_linked:
            norm_map_node = normal_input.links[0].from_node
            if norm_map_node.type == "NORMAL_MAP":
                color_input = norm_map_node.inputs.get("Color")
                if color_input is not None and color_input.is_linked:
                    tex_node = color_input.links[0].from_node
                    if tex_node.type == "TEX_IMAGE" and tex_node.image:
                        mat.ssm_normal_image = tex_node.image
                        used_images.add(tex_node.image)
                        found.append("normal")

    if not mat.ssm_specular_image:
        # Look for an image feeding a Separate RGB/Color node that in
        # turn feeds Roughness or Metallic - the shape our own Apply
        # operator builds, and the common shape for an imported mask.
        for input_name in ("Roughness", "Metallic"):
            inp = bsdf.inputs.get(input_name)
            if inp is not None and inp.is_linked:
                sep_node = inp.links[0].from_node
                if sep_node.type in ("SEPARATE_COLOR", "SEPRGB") and sep_node.inputs:
                    color_input = sep_node.inputs[0]
                    if color_input.is_linked:
                        tex_node = color_input.links[0].from_node
                        if (
                            tex_node.type == "TEX_IMAGE"
                            and tex_node.image
                            and tex_node.image not in used_images
                        ):
                            mat.ssm_specular_image = tex_node.image
                            found.append("spec mask")
                            break

    if not mat.ssm_speccolor_image:
        spec_tint_input = bsdf.inputs.get("Specular Tint")
        if spec_tint_input is not None and spec_tint_input.is_linked:
            src_node = spec_tint_input.links[0].from_node
            if (
                src_node.type == "TEX_IMAGE"
                and src_node.image
                and src_node.image not in used_images
            ):
                mat.ssm_speccolor_image = src_node.image
                found.append("spec color")

    return found


def apply_shader_slot_maps(mat):
    """Build or update the node setup for `mat` using whichever
    ssm_* images are currently assigned. Safe to call repeatedly -
    existing SlotMap_* nodes are reused rather than duplicated."""

    if not mat.use_nodes:
        mat.use_nodes = True

    nodes = mat.node_tree.nodes
    links = mat.node_tree.links

    bsdf = _ssm_find_principled_bsdf(nodes)
    if bsdf is None:
        bsdf = nodes.new("ShaderNodeBsdfPrincipled")
        bsdf.location = (200, 300)

    # --- Diffuse -> Base Color ---
    if mat.ssm_diffuse_image:
        diff_tex = _ssm_get_or_create_node(
            nodes, "ShaderNodeTexImage", "SlotMap_Diffuse", location=(-800, 400)
        )
        diff_tex.image = mat.ssm_diffuse_image
        diff_tex.image.colorspace_settings.name = "sRGB"
        links.new(diff_tex.outputs["Color"], bsdf.inputs["Base Color"])

    # --- Normal -> Normal Map node -> Normal ---
    if mat.ssm_normal_image:
        norm_tex = _ssm_get_or_create_node(
            nodes, "ShaderNodeTexImage", "SlotMap_Normal", location=(-800, 100)
        )
        norm_tex.image = mat.ssm_normal_image
        norm_tex.image.colorspace_settings.name = "Non-Color"

        norm_map = _ssm_get_or_create_node(
            nodes, "ShaderNodeNormalMap", "SlotMap_NormalMap", location=(-400, 100)
        )
        links.new(norm_tex.outputs["Color"], norm_map.inputs["Color"])
        links.new(norm_map.outputs["Normal"], bsdf.inputs["Normal"])

    # --- Spec mask -> Separate RGB/Color -> Roughness / Metallic / IOR ---
    if mat.ssm_specular_image:
        spec_tex = _ssm_get_or_create_node(
            nodes, "ShaderNodeTexImage", "SlotMap_SpecMask", location=(-800, -200)
        )
        spec_tex.image = mat.ssm_specular_image
        spec_tex.image.colorspace_settings.name = "Non-Color"

        if bpy.app.version >= (4, 0, 0):
            sep = _ssm_get_or_create_node(
                nodes, "ShaderNodeSeparateColor", "SlotMap_Separate", location=(-400, -200)
            )
            sep.mode = "RGB"
            links.new(spec_tex.outputs["Color"], sep.inputs["Color"])
            r_out, g_out, b_out = sep.outputs["Red"], sep.outputs["Green"], sep.outputs["Blue"]
        else:
            sep = _ssm_get_or_create_node(
                nodes, "ShaderNodeSeparateRGB", "SlotMap_Separate", location=(-400, -200)
            )
            links.new(spec_tex.outputs["Color"], sep.inputs["Image"])
            r_out, g_out, b_out = sep.outputs["R"], sep.outputs["G"], sep.outputs["B"]

        # Red channel is scaled by -0.5 (clamped) before Roughness.
        invert_r = _ssm_get_or_create_node(
            nodes, "ShaderNodeMath", "SlotMap_RoughnessInvert", location=(-200, -300)
        )
        invert_r.operation = "MULTIPLY"
        invert_r.use_clamp = True
        invert_r.inputs[1].default_value = -0.5
        links.new(r_out, invert_r.inputs[0])
        links.new(invert_r.outputs["Value"], bsdf.inputs["Roughness"])

        # Green channel is scaled by 0.5 (clamped) before Metallic.
        scale_g = _ssm_get_or_create_node(
            nodes, "ShaderNodeMath", "SlotMap_MetallicScale", location=(-200, -450)
        )
        scale_g.operation = "MULTIPLY"
        scale_g.use_clamp = True
        scale_g.inputs[1].default_value = 0.5
        links.new(g_out, scale_g.inputs[0])
        links.new(scale_g.outputs["Value"], bsdf.inputs["Metallic"])

        # Blender 4.0+ renamed the old "Specular" slider to "Specular
        # IOR Level" (distinct from the "IOR" socket, which is glass/
        # transmission IOR). Fall back to "Specular" on older Blender.
        spec_level_input = bsdf.inputs.get("Specular IOR Level")
        if spec_level_input is None:
            spec_level_input = bsdf.inputs.get("Specular")
        if spec_level_input is not None:
            links.new(b_out, spec_level_input)

    # --- Spec color -> Specular Tint ---
    if mat.ssm_speccolor_image:
        spec_color_tex = _ssm_get_or_create_node(
            nodes, "ShaderNodeTexImage", "SlotMap_SpecColor", location=(-800, -600)
        )
        spec_color_tex.image = mat.ssm_speccolor_image
        spec_color_tex.image.colorspace_settings.name = "sRGB"
        spec_tint_input = bsdf.inputs.get("Specular Tint")
        if spec_tint_input is not None:
            links.new(spec_color_tex.outputs["Color"], spec_tint_input)


# ---------------------------------------------------------------------
# Shader Slot Maps: operators
# ---------------------------------------------------------------------

class MHO_OT_apply_shader_slot_maps(Operator):
    """Build/update the node setup for one material using its assigned
    diffuse/normal/spec-mask images"""
    bl_idname = "mho.apply_shader_slot_maps"
    bl_label = "Apply Shader Slot Maps"
    bl_description = "Build/update the node setup for this material using its assigned images"
    bl_options = {"REGISTER", "UNDO"}

    material_name: StringProperty()

    def execute(self, context):
        mat = bpy.data.materials.get(self.material_name)
        if mat is None:
            self.report({"ERROR"}, f"Material '{self.material_name}' not found")
            return {"CANCELLED"}

        apply_shader_slot_maps(mat)
        return {"FINISHED"}


class MHO_OT_apply_shader_slot_maps_all(Operator):
    """Build/update node setups for every material slot on the active
    object that has at least one image assigned"""
    bl_idname = "mho.apply_shader_slot_maps_all"
    bl_label = "Apply Maps to All Slots"
    bl_description = (
        "Build/update node setups for every material slot on the active "
        "object that has at least one image assigned"
    )
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context):
        return context.active_object is not None

    def execute(self, context):
        obj = context.active_object
        if obj is None:
            self.report({"ERROR"}, "No active object")
            return {"CANCELLED"}

        applied = 0
        for slot in obj.material_slots:
            mat = slot.material
            if mat is None:
                continue
            if (
                mat.ssm_diffuse_image
                or mat.ssm_normal_image
                or mat.ssm_specular_image
                or mat.ssm_speccolor_image
            ):
                apply_shader_slot_maps(mat)
                applied += 1

        self.report({"INFO"}, f"Applied maps to {applied} material(s)")
        return {"FINISHED"}


class MHO_OT_detect_shader_slot_maps(Operator):
    """Scan one material's existing node tree and populate any blank
    ssm_* pickers from images already wired into the matching sockets"""
    bl_idname = "mho.detect_shader_slot_maps"
    bl_label = "Detect Shader Slot Maps"
    bl_description = (
        "Scan this material's node tree and fill in any blank Diffuse/Normal/"
        "Spec Mask pickers from images already wired into the matching sockets"
    )
    bl_options = {"REGISTER", "UNDO"}

    material_name: StringProperty()

    def execute(self, context):
        mat = bpy.data.materials.get(self.material_name)
        if mat is None:
            self.report({"ERROR"}, f"Material '{self.material_name}' not found")
            return {"CANCELLED"}

        found = _ssm_autodetect_images(mat)
        if found:
            self.report({"INFO"}, f"'{mat.name}': found {', '.join(found)}")
        else:
            self.report({"INFO"}, f"'{mat.name}': nothing new detected")
        return {"FINISHED"}


class MHO_OT_detect_shader_slot_maps_all(Operator):
    """Run Detect Shader Slot Maps across every material slot on the
    active object"""
    bl_idname = "mho.detect_shader_slot_maps_all"
    bl_label = "Detect Maps on All Slots"
    bl_description = "Scan every material slot on the active object and fill in blank pickers from existing node wiring"
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context):
        return context.active_object is not None

    def execute(self, context):
        obj = context.active_object
        if obj is None:
            self.report({"ERROR"}, "No active object")
            return {"CANCELLED"}

        scanned = 0
        total_found = 0
        for slot in obj.material_slots:
            mat = slot.material
            if mat is None:
                continue
            scanned += 1
            total_found += len(_ssm_autodetect_images(mat))

        self.report({"INFO"}, f"Scanned {scanned} material(s), found {total_found} image(s)")
        return {"FINISHED"}


# ---------------------------------------------------------------------
# Export for Game: core logic
# ---------------------------------------------------------------------

def _mho_expand_selection_to_hierarchy(context, seed_objects):
    """Given a starting set of objects, select the full connected
    hierarchy - every ancestor and every descendant - so exporting the
    selection includes the whole rig (armature + meshes + any empties)
    even if only one piece of it was originally selected."""

    expanded = set()
    stack = list(seed_objects)
    while stack:
        obj = stack.pop()
        if obj in expanded:
            continue
        expanded.add(obj)
        # Walk up to parents.
        if obj.parent is not None:
            stack.append(obj.parent)
        # Walk down to children.
        for child in obj.children:
            stack.append(child)

    bpy.ops.object.select_all(action="DESELECT")
    for obj in expanded:
        obj.select_set(True)

    return expanded


def _mho_game_fbx_export_kwargs():
    """Shared FBX export settings used by both Export for Game and
    Batch Export Animations, so the two always stay in sync."""
    return dict(
        check_existing=False,
        filter_glob="*.fbx",
        use_selection=True,
        use_visible=False,
        use_active_collection=False,
        object_types={"EMPTY", "CAMERA", "LIGHT", "ARMATURE", "MESH", "OTHER"},
        use_custom_props=False,
        global_scale=1.0,
        apply_unit_scale=True,
        apply_scale_options="FBX_SCALE_NONE",  # "All Local"
        use_space_transform=True,
        bake_space_transform=True,  # "Apply Transform"
        axis_forward="-Z",
        axis_up="Y",
        bake_anim=True,
        bake_anim_use_all_bones=True,
        bake_anim_use_nla_strips=False,
        bake_anim_use_all_actions=False,
        bake_anim_force_startend_keying=True,
        bake_anim_step=1.0,
        bake_anim_simplify_factor=1.0,
        path_mode="AUTO",
        batch_mode="OFF",
    )


class MHO_OT_export_for_game(Operator):
    """Select the full hierarchy of the current selection and export it
    to an FBX file next to the current .blend, using game-ready FBX
    export settings"""

    bl_idname = "mho.export_for_game"
    bl_label = "Export for Game"
    bl_description = (
        "Expand the current selection to its full armature/mesh hierarchy and export "
        "an FBX file, saved in the same folder as this .blend, using game-ready settings"
    )
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context):
        return bool(context.selected_objects) and bool(bpy.data.filepath)

    def execute(self, context):
        if not context.selected_objects:
            self.report({"ERROR"}, "Nothing selected")
            return {"CANCELLED"}

        if not bpy.data.filepath:
            self.report({"ERROR"}, "Save this .blend file first - the FBX exports next to it")
            return {"CANCELLED"}

        blend_dir = os.path.dirname(bpy.data.filepath)
        blend_name = os.path.splitext(os.path.basename(bpy.data.filepath))[0]
        export_path = os.path.join(blend_dir, blend_name + ".fbx")

        original_selection = list(context.selected_objects)
        original_active = context.view_layer.objects.active

        hierarchy = _mho_expand_selection_to_hierarchy(context, original_selection)
        if original_active is not None and original_active in hierarchy:
            context.view_layer.objects.active = original_active

        try:
            bpy.ops.export_scene.fbx(filepath=export_path, **_mho_game_fbx_export_kwargs())
        except AttributeError:
            self.report(
                {"ERROR"},
                "FBX export isn't available - enable the built-in "
                "'Import-Export: FBX format' addon in Blender's preferences",
            )
            return {"CANCELLED"}
        finally:
            # Restore whatever was selected/active before we expanded it.
            bpy.ops.object.select_all(action="DESELECT")
            for obj in original_selection:
                obj.select_set(True)
            if original_active is not None:
                context.view_layer.objects.active = original_active

        self.report({"INFO"}, f"Exported {len(hierarchy)} object(s) to '{export_path}'")
        return {"FINISHED"}


def batch_export_animations(context, armature_obj, output_dir):
    """For every NLA track on armature_obj except ones named 'Offset'
    or 'Root' (case-insensitive), export a separate FBX named after
    that track into output_dir.

    Relies on standard NLA Replace blending: every individual clip
    track normally uses Replace, so whichever unmuted track sits
    HIGHEST in the stack completely overrides every track below it for
    any bone it touches. Starting from every track unmuted and then
    muting tracks one at a time from the top down therefore reveals
    each clip "in turn" without needing anything fancier. 'Offset'
    (additive) and 'Root' (the base rest pose, effectively the
    lowest/fallback layer) are never muted, so they stay layered
    under/over every exported clip exactly as they normally would
    during regular playback - they're just never themselves exported
    as a named file.

    Each clip is exported using only its own strip's frame range (not
    the whole scene range), so a short clip doesn't get padded out to
    the length of the longest one. Every track's original mute state
    and the scene's original frame_start/frame_end are restored
    afterward, in a finally block, regardless of success or failure.

    Returns (saved_paths, log). Raises RuntimeError if there's no
    animation data or no exportable tracks."""

    anim_data = armature_obj.animation_data
    if anim_data is None or not anim_data.nla_tracks:
        raise RuntimeError(f"'{armature_obj.name}' has no NLA tracks")

    # nla_tracks list order is bottom-to-top (index 0 = bottom of the
    # stack, last index = top) - matches how every other NLA-track tool
    # in this addon already builds tracks (new tracks always append at
    # the end/top). Reversed() therefore walks top-to-bottom.
    tracks = list(anim_data.nla_tracks)
    original_mutes = [(t, t.mute) for t in tracks]
    original_frame_start = context.scene.frame_start
    original_frame_end = context.scene.frame_end

    export_targets = [t for t in reversed(tracks) if t.name.lower() not in ("offset", "root")]
    if not export_targets:
        raise RuntimeError(
            f"No exportable animation tracks found on '{armature_obj.name}' "
            "(only Offset/Root present)"
        )

    for t in tracks:
        t.mute = False

    saved_paths = []
    log = []

    try:
        for track in export_targets:
            if not track.strips:
                log.append(f"SKIP  '{track.name}': no strips")
                track.mute = True
                continue

            strip_start = min(s.frame_start for s in track.strips)
            strip_end = max(s.frame_end for s in track.strips)
            context.scene.frame_start = int(strip_start)
            context.scene.frame_end = int(strip_end)

            filepath = os.path.join(output_dir, f"{track.name}.fbx")
            try:
                bpy.ops.export_scene.fbx(filepath=filepath, **_mho_game_fbx_export_kwargs())
            except AttributeError:
                raise RuntimeError(
                    "FBX export isn't available - enable the built-in "
                    "'Import-Export: FBX format' addon in Blender's preferences"
                )

            saved_paths.append(filepath)
            log.append(
                f"OK    exported '{track.name}' ({int(strip_start)}-{int(strip_end)}) -> '{filepath}'"
            )

            track.mute = True
    finally:
        for t, mute in original_mutes:
            t.mute = mute
        context.scene.frame_start = original_frame_start
        context.scene.frame_end = original_frame_end

    return saved_paths, log


class MHO_OT_batch_export_animations(Operator):
    """Export a separate FBX for every NLA animation track on the
    target armature (skipping 'Offset' and 'Root'), named after each
    track, into a 'Blend_anims' subfolder next to the .blend"""

    bl_idname = "mho.batch_export_animations"
    bl_label = "Batch Export Animations"
    bl_description = (
        "Export a separate FBX for every NLA animation track on the target armature "
        "(skipping 'Offset' and 'Root'), named after each track, into a 'Blend_anims' "
        "subfolder next to the .blend - same game-ready settings as Export for Game. "
        "All NLA track mute states and the scene frame range are restored afterward"
    )
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context):
        return resolve_nla_target_armature(context) is not None and bool(bpy.data.filepath)

    def execute(self, context):
        armature_obj = resolve_nla_target_armature(context)
        if armature_obj is None:
            self.report({"ERROR"}, "Pick an armature (or select one in the viewport) first")
            return {"CANCELLED"}

        if not bpy.data.filepath:
            self.report({"ERROR"}, "Save this .blend file first - the FBXs export next to it")
            return {"CANCELLED"}

        output_dir = os.path.join(os.path.dirname(bpy.data.filepath), "Blend_anims")
        os.makedirs(output_dir, exist_ok=True)

        seed_objects = list(context.selected_objects) if context.selected_objects else [armature_obj]
        original_selection = list(context.selected_objects)
        original_active = context.view_layer.objects.active

        hierarchy = _mho_expand_selection_to_hierarchy(context, seed_objects)
        if original_active is not None and original_active in hierarchy:
            context.view_layer.objects.active = original_active
        elif armature_obj in hierarchy:
            context.view_layer.objects.active = armature_obj

        try:
            saved_paths, log = batch_export_animations(context, armature_obj, output_dir)
        except RuntimeError as exc:
            self.report({"ERROR"}, str(exc))
            bpy.ops.object.select_all(action="DESELECT")
            for obj in original_selection:
                obj.select_set(True)
            if original_active is not None:
                context.view_layer.objects.active = original_active
            return {"CANCELLED"}

        for line in log:
            print(line)

        bpy.ops.object.select_all(action="DESELECT")
        for obj in original_selection:
            obj.select_set(True)
        if original_active is not None:
            context.view_layer.objects.active = original_active

        self.report({"INFO"}, f"Exported {len(saved_paths)} animation(s) to '{output_dir}'")
        return {"FINISHED"}


# ---------------------------------------------------------------------
# Texture Baker: core logic
# ---------------------------------------------------------------------

_TB_SSM_ATTR = {
    "diffuse": "ssm_diffuse_image",
    "normal": "ssm_normal_image",
    "specmask": "ssm_specular_image",
    "speccolor": "ssm_speccolor_image",
}
_TB_LABEL = {
    "diffuse": "D",
    "normal": "N",
    "specmask": "SM",
    "speccolor": "SC",
}
_TB_OUTPUT_SUBFOLDER = "textures"
_TB_COLORSPACE = {
    "diffuse": "sRGB",
    "normal": "Non-Color",
    "specmask": "Non-Color",
    "speccolor": "sRGB",
}


def _tb_duplicate_and_join(context, source_objs, selected_faces_only):
    """Duplicate every source mesh object, optionally trim each duplicate
    down to only its originally-selected faces, then join all duplicates
    into a single new mesh object. Returns the joined object, or None if
    nothing ended up with any geometry."""

    bpy.ops.object.select_all(action="DESELECT")
    for obj in source_objs:
        obj.select_set(True)
    context.view_layer.objects.active = source_objs[0]

    bpy.ops.object.duplicate(linked=False)
    duplicates = list(context.selected_objects)

    if selected_faces_only:
        kept = []
        for dup in duplicates:
            if not any(p.select for p in dup.data.polygons):
                # Nothing was selected on the source this came from -
                # drop this duplicate rather than joining empty/
                # irrelevant geometry in.
                bpy.data.objects.remove(dup, do_unlink=True)
                continue

            bpy.ops.object.select_all(action="DESELECT")
            dup.select_set(True)
            context.view_layer.objects.active = dup
            bpy.ops.object.mode_set(mode="EDIT")
            bpy.ops.mesh.select_all(action="INVERT")
            bpy.ops.mesh.delete(type="FACE")
            bpy.ops.object.mode_set(mode="OBJECT")
            kept.append(dup)
        duplicates = kept

    if not duplicates:
        return None

    # Normalize UV layer 0's name across every duplicate to the same
    # value (and drop any extra UV maps beyond it). Blender's Join
    # matches UV layers by name, so if the sources had differently-
    # named UV maps (e.g. "UVMap" vs "UV0"), joining them as-is creates
    # several partially-populated layers instead of one clean merged
    # one - which is what caused the original multiple-UV-layers issue.
    for dup in duplicates:
        uv_layers = dup.data.uv_layers
        if len(uv_layers) == 0:
            continue
        uv_layers[0].name = "MHO_Source"
        for uv in list(uv_layers)[1:]:
            uv_layers.remove(uv)

    bpy.ops.object.select_all(action="DESELECT")
    for dup in duplicates:
        dup.select_set(True)
    context.view_layer.objects.active = duplicates[0]

    if len(duplicates) > 1:
        bpy.ops.object.join()

    return context.view_layer.objects.active


def _tb_auto_seam(target_obj):
    """Mark UV seams automatically. Primarily by reusing the island
    boundaries already present in the original 'MHO_Source' UV - the
    unwrap decisions whoever built the source materials already made
    are a far better seam source for organic/low-poly game meshes than
    a geometric sharp-angle threshold. (A sharp-angle threshold badly
    over-fragments this kind of content: low-poly curved surfaces
    routinely exceed any reasonable angle on nearly every edge even
    where the surface reads as smooth, which is what caused the
    'almost every face is its own island' result from that approach.)
    Also seams every edge where the two adjacent faces belong to
    different materials, as a supplement for any boundary the original
    UV happened not to have. Must be called in Edit Mode with the
    object as active and its UV layers holding 'MHO_Source' and
    'Atlas' - leaves 'Atlas' as the active UV layer when done."""

    import bmesh

    uv_layers = target_obj.data.uv_layers
    source_uv = uv_layers.get("MHO_Source")
    atlas_uv = uv_layers.get("Atlas")

    bpy.ops.mesh.select_all(action="SELECT")

    if source_uv is not None:
        uv_layers.active = source_uv
        bpy.ops.uv.seams_from_islands(mark_seams=True, mark_sharp=False)

    bm = bmesh.from_edit_mesh(target_obj.data)
    bm.faces.ensure_lookup_table()
    for edge in bm.edges:
        if len(edge.link_faces) == 2:
            f1, f2 = edge.link_faces
            if f1.material_index != f2.material_index:
                edge.seam = True
    bmesh.update_edit_mesh(target_obj.data)

    if atlas_uv is not None:
        uv_layers.active = atlas_uv

    bpy.ops.mesh.select_all(action="DESELECT")


def _tb_build_atlas_uv(context, target_obj, margin):
    """Add a fresh non-overlapping 'Atlas' UV layout, kept alongside the
    original 'MHO_Source' UV layer (from _tb_duplicate_and_join) rather
    than replacing it. The two serve different purposes during baking
    and must NOT both point at the same layer:
    - 'Atlas' is set as the ACTIVE UV - this is what Blender uses to
      decide *where* baked pixels get written (bake target placement).
    - 'MHO_Source' is set as ACTIVE RENDER - this is what an Image
      Texture node with no explicit UV input falls back to for
      *sampling* (source lookup), which is exactly the temporary
      TB_Source nodes used to read each material's original texture
      during the Diffuse/SpecMask/SpecColor bake passes. If the atlas
      layer were used for sampling instead, those small source images
      would be read using nonsensical atlas-space coordinates instead
      of their own original layout - scrambling the result.

    Unwrapping uses automatic seam marking (_tb_auto_seam) followed by
    a real Unwrap, rather than Smart UV Project - Smart UV Project
    ignores seams entirely and splits islands purely on face-angle
    deviation, which tends to fragment what should be one continuous
    surface into far more islands than necessary."""

    uv_layers = target_obj.data.uv_layers

    source_uv = uv_layers.get("MHO_Source")
    if source_uv is not None:
        source_uv.active_render = True

    # Defensive: drop any stray extra layers beyond the two we expect
    # (shouldn't normally happen given the per-duplicate normalization
    # in _tb_duplicate_and_join, but keeps things unambiguous if it does).
    for uv in list(uv_layers):
        if uv.name not in ("MHO_Source", "Atlas"):
            uv_layers.remove(uv)

    atlas_uv = uv_layers.get("Atlas")
    if atlas_uv is None:
        atlas_uv = uv_layers.new(name="Atlas")
    uv_layers.active = atlas_uv

    bpy.ops.object.select_all(action="DESELECT")
    target_obj.select_set(True)
    context.view_layer.objects.active = target_obj
    bpy.ops.object.mode_set(mode="EDIT")

    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.mesh.mark_seam(clear=True)  # start from a clean slate each run

    _tb_auto_seam(target_obj)

    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.uv.unwrap(method="ANGLE_BASED", margin=0.0)
    bpy.ops.uv.select_all(action="SELECT")
    bpy.ops.uv.pack_islands(margin=margin, rotate=True)
    bpy.ops.object.mode_set(mode="OBJECT")


def _tb_make_single_user_materials(target_obj):
    """Replace every material slot on target_obj with an independent
    copy, so the temporary bake node-hacking below can never leak into
    the original scene's materials (the duplicated meshes may still be
    sharing those datablocks, depending on Blender's duplicate settings)."""

    for i, slot in enumerate(target_obj.material_slots):
        if slot.material is not None:
            target_obj.material_slots[i].material = slot.material.copy()


def _tb_new_atlas_image(name, size, channel, height=None, alpha=False):
    img = bpy.data.images.new(
        name=name, width=size, height=size if height is None else height, alpha=alpha
    )
    img.colorspace_settings.name = _TB_COLORSPACE[channel]
    return img


def _tb_add_target_nodes(obj, image):
    """Add a temporary, active 'TB_Target' Image Texture node pointing at
    image to every material on obj - this is where Cycles writes the
    bake. Returns [(mat, node), ...] for _tb_remove_temp_nodes."""

    temp_nodes = []
    for mat in {s.material for s in obj.material_slots if s.material}:
        if not mat.use_nodes:
            mat.use_nodes = True
        nodes = mat.node_tree.nodes
        target_node = nodes.new("ShaderNodeTexImage")
        target_node.name = "TB_Target"
        target_node.image = image
        for n in nodes:
            n.select = False
        target_node.select = True
        nodes.active = target_node
        temp_nodes.append((mat, target_node))
    return temp_nodes


def _tb_base_color_source(mat):
    """Fallback Diffuse source for a material with no ssm_diffuse_image
    (e.g. straight out of FBX import): the first Image Texture found
    upstream of the Principled BSDF's Base Color, else that socket's
    plain colour value. Returns (image or None, rgba or None)."""

    bsdf = _ssm_find_principled_bsdf(mat.node_tree.nodes)
    if bsdf is None:
        return None, None
    base = bsdf.inputs["Base Color"]
    if not base.is_linked:
        return None, tuple(base.default_value)

    stack = [base.links[0].from_node]
    seen = set()
    while stack:
        node = stack.pop()
        if node.name in seen:
            continue
        seen.add(node.name)
        if node.type == "TEX_IMAGE" and node.image is not None:
            return node.image, None
        for inp in node.inputs:
            stack.extend(link.from_node for link in inp.links)
    return None, None


def _tb_add_emit_overrides(obj, channel):
    """Wire a temporary Emission shader into the active output of every
    material on obj, fed by that material's ssm_* source image for this
    channel. With no ssm_* image, Diffuse falls back to whatever feeds
    the Principled Base Color (_tb_base_color_source); anything else
    emits black. (The Emission node's own default colour is WHITE, so
    it must always be set explicitly.) Only ever call this on
    single-user material copies - it replaces the Surface link.
    Returns [(mat, node), ...] for _tb_remove_temp_nodes."""

    ssm_attr = _TB_SSM_ATTR[channel]
    temp_nodes = []

    for mat in {s.material for s in obj.material_slots if s.material}:
        if not mat.use_nodes:
            mat.use_nodes = True
        nodes = mat.node_tree.nodes
        links = mat.node_tree.links

        output_node = None
        for n in nodes:
            if n.type == "OUTPUT_MATERIAL" and n.is_active_output:
                output_node = n
                break
        if output_node is None:
            output_node = nodes.new("ShaderNodeOutputMaterial")

        emission = nodes.new("ShaderNodeEmission")
        emission.name = "TB_Emission"
        links.new(emission.outputs["Emission"], output_node.inputs["Surface"])
        temp_nodes.append((mat, emission))

        src_image = getattr(mat, ssm_attr)
        src_color = (0.0, 0.0, 0.0, 1.0)
        if src_image is None and channel == "diffuse":
            src_image, fallback_color = _tb_base_color_source(mat)
            if fallback_color is not None:
                src_color = fallback_color
        emission.inputs["Color"].default_value = src_color

        if src_image is not None:
            source_node = nodes.new("ShaderNodeTexImage")
            source_node.name = "TB_Source"
            source_node.image = src_image
            links.new(source_node.outputs["Color"], emission.inputs["Color"])
            temp_nodes.append((mat, source_node))

    return temp_nodes


def _tb_add_coverage_overrides(obj):
    """Like _tb_add_emit_overrides, but every material emits plain white -
    baking this gives a mask of where the geometry is at all. Only ever
    call this on single-user material copies."""

    temp_nodes = []
    for mat in {s.material for s in obj.material_slots if s.material}:
        if not mat.use_nodes:
            mat.use_nodes = True
        nodes = mat.node_tree.nodes

        output_node = None
        for n in nodes:
            if n.type == "OUTPUT_MATERIAL" and n.is_active_output:
                output_node = n
                break
        if output_node is None:
            output_node = nodes.new("ShaderNodeOutputMaterial")

        emission = nodes.new("ShaderNodeEmission")
        emission.name = "TB_Coverage"
        emission.inputs["Color"].default_value = (1.0, 1.0, 1.0, 1.0)
        mat.node_tree.links.new(emission.outputs["Emission"], output_node.inputs["Surface"])
        temp_nodes.append((mat, emission))
    return temp_nodes


def _tb_remove_temp_nodes(temp_nodes):
    for mat, node in temp_nodes:
        mat.node_tree.nodes.remove(node)


def _tb_bake_normal_channel(target_obj, image, margin):
    """Bake real tangent-space normals through each material's existing,
    unmodified Normal Map setup - no node overrides needed for this one."""

    temp_nodes = _tb_add_target_nodes(target_obj, image)

    bpy.ops.object.bake(
        type="NORMAL",
        margin=margin,
        margin_type="EXTEND",
        use_selected_to_active=False,
        normal_space="TANGENT",
        normal_r="POS_X",
        normal_g="POS_Y",
        normal_b="POS_Z",
        target="IMAGE_TEXTURES",
        save_mode="INTERNAL",
        use_clear=True,
    )

    _tb_remove_temp_nodes(temp_nodes)


def _tb_bake_emit_channel(target_obj, image, channel, margin):
    """Bake a raw texel copy of each material's respective ssm_* source
    image via a temporary Emission override (see _tb_add_emit_overrides
    for the Diffuse fallback; anything else with no image bakes black)."""

    temp_nodes = _tb_add_emit_overrides(target_obj, channel)
    temp_nodes += _tb_add_target_nodes(target_obj, image)

    bpy.ops.object.bake(
        type="EMIT",
        margin=margin,
        margin_type="EXTEND",
        use_selected_to_active=False,
        target="IMAGE_TEXTURES",
        save_mode="INTERNAL",
        use_clear=True,
    )

    _tb_remove_temp_nodes(temp_nodes)


def _tb_triangle_count(mesh):
    return sum(len(p.vertices) - 2 for p in mesh.polygons)


def _tb_make_reduced_copy(context, high_obj, quality, dissolve_flat, log):
    """Build a low-poly copy of high_obj (same transform, materials and
    UV layers, modifiers baked in) for a high-to-low bake. Optionally
    planar-dissolves nearly-flat regions first (5 degrees, never across
    material boundaries), then - only if still above target - collapses
    edges down to quality x the original triangle count. Each Decimate
    modifier is added and applied on its own, so it's always the first
    (only) modifier when applied."""

    depsgraph = context.evaluated_depsgraph_get()
    mesh = bpy.data.meshes.new_from_object(
        high_obj.evaluated_get(depsgraph), preserve_all_data_layers=True, depsgraph=depsgraph
    )
    low = bpy.data.objects.new(f"{high_obj.name}_low", mesh)
    low.matrix_world = high_obj.matrix_world.copy()
    high_obj.users_collection[0].objects.link(low)

    bpy.ops.object.select_all(action="DESELECT")
    low.select_set(True)
    context.view_layer.objects.active = low

    before = _tb_triangle_count(mesh)
    target = max(12, int(before * quality))

    if dissolve_flat:
        mod = low.modifiers.new("TB_Planar", "DECIMATE")
        mod.decimate_type = "DISSOLVE"
        mod.angle_limit = math.radians(5.0)
        mod.delimit = {"MATERIAL"}
        bpy.ops.object.modifier_apply(modifier=mod.name)

    after_planar = _tb_triangle_count(low.data)
    if after_planar > target:
        mod = low.modifiers.new("TB_Collapse", "DECIMATE")
        mod.decimate_type = "COLLAPSE"
        mod.ratio = target / after_planar
        bpy.ops.object.modifier_apply(modifier=mod.name)

    after = _tb_triangle_count(low.data)
    log.append(
        f"OK    reduced {before} -> {after} tris ({100.0 * after / max(before, 1):.1f}%, "
        f"target {target}{', flat areas dissolved first' if dissolve_flat else ''})"
    )
    return low


def _tb_world_bvh(context, obj):
    """(BVHTree, world-space vertex list) for obj's evaluated mesh."""

    from mathutils.bvhtree import BVHTree

    evaluated = obj.evaluated_get(context.evaluated_depsgraph_get())
    mesh = evaluated.to_mesh()
    try:
        mw = evaluated.matrix_world
        verts = [mw @ v.co for v in mesh.vertices]
        polys = [tuple(p.vertices) for p in mesh.polygons]
    finally:
        evaluated.to_mesh_clear()
    return BVHTree.FromPolygons(verts, polys), verts


def _tb_cage_settings(context, high_obj, low_obj):
    """Measure how far the reduced mesh drifted from the original (the
    largest nearest-surface distance, sampled both ways, in world units)
    and derive selected-to-active ray settings from it: rays start that
    far (plus a little) outside the low mesh and may travel the same
    distance past it inward, so they always reach the original surface
    without reaching across to unrelated geometry further away.
    Returns (cage_extrusion, max_ray_distance, measured_distance)."""

    high_bvh, high_verts = _tb_world_bvh(context, high_obj)
    low_bvh, low_verts = _tb_world_bvh(context, low_obj)

    def max_gap(points, bvh, limit=20000):
        step = max(1, len(points) // limit)
        worst = 0.0
        for co in points[::step]:
            hit = bvh.find_nearest(co)
            if hit[0] is not None:
                worst = max(worst, hit[3])
        return worst

    gap = max(max_gap(high_verts, low_bvh), max_gap(low_verts, high_bvh))

    lo = [min(v[i] for v in high_verts) for i in range(3)]
    hi = [max(v[i] for v in high_verts) for i in range(3)]
    eps = max(math.dist(lo, hi) * 0.001, 1e-4)

    extrusion = gap * 1.1 + eps
    return extrusion, extrusion * 2.0 + eps, gap


def _tb_bake_selected_to_active(source_obj, target_obj, channel, image, ray_kwargs):
    """One selected-to-active bake pass from source_obj's materials into
    image on target_obj (both must already be selected, target active).
    channel "normal" bakes tangent-space normals through the source's
    real shading; anything else bakes an emit copy of that channel."""

    temp_nodes = _tb_add_target_nodes(target_obj, image)
    if channel == "normal":
        bpy.ops.object.bake(
            type="NORMAL",
            normal_space="TANGENT",
            normal_r="POS_X",
            normal_g="POS_Y",
            normal_b="POS_Z",
            **ray_kwargs,
        )
    else:
        temp_nodes += _tb_add_emit_overrides(source_obj, channel)
        bpy.ops.object.bake(type="EMIT", **ray_kwargs)
    _tb_remove_temp_nodes(temp_nodes)


def texture_bake_run(context, source_objs, props, base_name, output_dir, reduce=False):
    """Full pipeline for one atlas: duplicate (and join, if source_objs
    has more than one entry - the caller currently always passes a
    single-object list, one call per selected mesh), build an atlas UV,
    bake the four channels, save PNGs into output_dir, and assign one
    fresh merged material (built via the same apply_shader_slot_maps
    logic Shader Slot Maps uses everywhere else). Returns (target_obj,
    saved_paths, log), or raises RuntimeError with a user-facing
    message on failure.

    With reduce=True it's a high-to-low bake instead: the welded
    duplicate stays as the untouched high-poly bake source, a reduced
    copy of it (_tb_make_reduced_copy, props.tb_reduce_*) gets the
    atlas UV, and every channel bakes selected-to-active from high onto
    low - so the detail removed by the reduction lands in the Normal
    map. Ray distances come from the measured high/low gap
    (_tb_cage_settings). The high duplicate is deleted afterwards."""

    log = []
    margin = 8

    target_obj = _tb_duplicate_and_join(context, source_objs, props.tb_selected_faces_only)
    if target_obj is None:
        raise RuntimeError("No faces to bake (nothing selected on the source meshes?)")

    target_obj.name = f"{base_name}_Atlas"
    target_obj.data.name = f"{base_name}_Atlas"

    # Weld duplicate/unwelded verts along seams before unwrapping. Without
    # this, any disconnected geometry (very common straight out of FBX
    # import) fragments Smart UV Project into a huge number of tiny
    # micro-islands instead of a handful of large ones - which is what
    # produces a scattered "polka dot" bake instead of coherent regions.
    bpy.ops.object.select_all(action="DESELECT")
    target_obj.select_set(True)
    context.view_layer.objects.active = target_obj
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.mesh.remove_doubles(threshold=props.mp_merge_distance)
    bpy.ops.object.mode_set(mode="OBJECT")

    high_obj = None
    bake_mat = None
    if reduce:
        high_obj = target_obj
        high_obj.name = f"{base_name}_TB_High"
        # Single-user BEFORE the copy, so the low mesh (which only ever
        # gets the temporary bake material below) can't share them.
        _tb_make_single_user_materials(high_obj)
        try:
            target_obj = _tb_make_reduced_copy(
                context, high_obj, props.tb_reduce_quality, props.tb_reduce_dissolve_flat, log
            )
        except Exception:
            _tb_remove_object_and_mesh(high_obj)
            raise
        target_obj.name = f"{base_name}_Atlas"
        target_obj.data.name = f"{base_name}_Atlas"

    original_engine = context.scene.render.engine
    try:
        _tb_build_atlas_uv(context, target_obj, margin=0.02)

        if reduce:
            # With selected-to-active only the target's image node matters,
            # so one temporary material holds it (the atlas seams above
            # already used the per-material boundaries).
            bake_mat = bpy.data.materials.new(name="TB_Reduced_Bake")
            bake_mat.use_nodes = True
            target_obj.data.materials.clear()
            target_obj.data.materials.append(bake_mat)
            for poly in target_obj.data.polygons:
                poly.material_index = 0

            extrusion, max_ray, gap = _tb_cage_settings(context, high_obj, target_obj)
            log.append(f"OK    high/low gap {gap:.4f} -> cage {extrusion:.4f}, max ray {max_ray:.4f}")
            ray_kwargs = dict(
                use_selected_to_active=True,
                use_cage=False,
                cage_extrusion=extrusion,
                max_ray_distance=max_ray,
                margin=margin,
                margin_type="EXTEND",
                target="IMAGE_TEXTURES",
                save_mode="INTERNAL",
                use_clear=True,
            )
        else:
            _tb_make_single_user_materials(target_obj)

        context.scene.render.engine = "CYCLES"

        bpy.ops.object.select_all(action="DESELECT")
        target_obj.select_set(True)
        if reduce:
            high_obj.select_set(True)
        context.view_layer.objects.active = target_obj

        sizes = {
            "diffuse": int(props.tb_diffuse_size),
            "normal": int(props.tb_normal_size),
            "specmask": int(props.tb_specmask_size),
            "speccolor": int(props.tb_speccolor_size),
        }

        images = {}
        # Normal first - it needs each material's real, unmodified
        # Normal Map setup still in place before the raw-copy channels
        # below start overriding material outputs.
        for channel in ("normal", "diffuse", "specmask", "speccolor"):
            size = sizes[channel]
            img = _tb_new_atlas_image(f"{base_name}_{_TB_LABEL[channel]}", size, channel)
            if reduce:
                _tb_bake_selected_to_active(high_obj, target_obj, channel, img, ray_kwargs)
            elif channel == "normal":
                _tb_bake_normal_channel(target_obj, img, margin)
            else:
                _tb_bake_emit_channel(target_obj, img, channel, margin)
            images[channel] = img
            log.append(f"OK    baked {_TB_LABEL[channel]} at {size}x{size}")
    finally:
        context.scene.render.engine = original_engine
        if high_obj is not None:
            _tb_remove_object_and_mesh(high_obj)
        if bake_mat is not None:
            target_obj.data.materials.clear()
            bpy.data.materials.remove(bake_mat)

    saved_paths = []
    for channel, img in images.items():
        # Build the filename from the intended name, not img.name - if an
        # image of that name already exists, Blender suffixes ".001".
        path = os.path.join(output_dir, f"{base_name}_{_TB_LABEL[channel]}.png")
        img.filepath_raw = path
        img.file_format = "PNG"
        img.save()
        saved_paths.append(path)
        log.append(f"OK    saved '{path}'")

    merged_mat = bpy.data.materials.new(name=f"{base_name}_Merged")
    merged_mat.ssm_diffuse_image = images.get("diffuse")
    merged_mat.ssm_normal_image = images.get("normal")
    merged_mat.ssm_specular_image = images.get("specmask")
    merged_mat.ssm_speccolor_image = images.get("speccolor")
    apply_shader_slot_maps(merged_mat)

    target_obj.data.materials.clear()
    target_obj.data.materials.append(merged_mat)
    for poly in target_obj.data.polygons:
        poly.material_index = 0

    # Housekeeping: MHO_Source was only needed to sample the original
    # per-material textures during baking. The merged material reads
    # from the new baked atlas images with no explicit UV Map node
    # (falling back to whatever is active_render), so drop MHO_Source
    # now and make Atlas the object's only, active-render UV.
    uv_layers = target_obj.data.uv_layers
    source_uv = uv_layers.get("MHO_Source")
    if source_uv is not None:
        uv_layers.remove(source_uv)
    atlas_uv = uv_layers.get("Atlas")
    if atlas_uv is not None:
        atlas_uv.active_render = True

    purge_orphan_data()

    log.append(f"OK    merged material '{merged_mat.name}' assigned to '{target_obj.name}'")

    return target_obj, saved_paths, log


def _tb_remove_object_and_mesh(obj):
    mesh = obj.data
    bpy.data.objects.remove(obj, do_unlink=True)
    if mesh is not None and mesh.users == 0:
        bpy.data.meshes.remove(mesh)


def _tb_world_bounds(context, obj):
    """World-space (min, max) corners of obj's evaluated bounding box."""

    from mathutils import Vector

    evaluated = obj.evaluated_get(context.evaluated_depsgraph_get())
    corners = [evaluated.matrix_world @ Vector(c) for c in evaluated.bound_box]
    lo = Vector((min(c.x for c in corners), min(c.y for c in corners), min(c.z for c in corners)))
    hi = Vector((max(c.x for c in corners), max(c.y for c in corners), max(c.z for c in corners)))
    return lo, hi


def _tb_new_top_down_plane(name, center_x, center_y, z, size_x, size_y, collection):
    """A single rectangular quad, normal +Z, centred on (center_x,
    center_y) at height z, with UV (0,0) at its min-X/min-Y corner and
    (1,1) at its max-X/max-Y corner - so the baked image reads as a
    plain top-down map (image up = world +Y)."""

    hx, hy = size_x / 2.0, size_y / 2.0
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(
        [(-hx, -hy, 0.0), (hx, -hy, 0.0), (hx, hy, 0.0), (-hx, hy, 0.0)],
        [],
        [(0, 1, 2, 3)],
    )
    uv_layer = mesh.uv_layers.new(name="UVMap")
    for loop, uv in zip(mesh.loops, ((0, 0), (1, 0), (1, 1), (0, 1))):
        uv_layer.data[loop.index].uv = uv
    mesh.update()

    obj = bpy.data.objects.new(name, mesh)
    obj.location = (center_x, center_y, z)
    collection.objects.link(obj)
    return obj


def _tb_top_down_image_dims(size, size_x, size_y):
    """(width, height) for a top-down image over a size_x by size_y area:
    the longer side gets the chosen size, the shorter side is scaled to
    match and rounded UP to a power of two (game textures must be), so
    texels are never coarser than the chosen size along either axis."""

    long_side = max(size_x, size_y)
    short_px = size * min(size_x, size_y) / long_side
    pow2 = 4
    while pow2 < short_px and pow2 < size:
        pow2 *= 2
    return (size, pow2) if size_x >= size_y else (pow2, size)


def _tb_apply_coverage_alpha(image, coverage):
    """Replace image's alpha with coverage's red channel (same size)."""

    import numpy as np

    count = image.size[0] * image.size[1] * 4
    pixels = np.empty(count, dtype=np.float32)
    image.pixels.foreach_get(pixels)
    mask = np.empty(count, dtype=np.float32)
    coverage.pixels.foreach_get(mask)
    pixels[3::4] = mask[0::4]
    image.pixels.foreach_set(pixels)
    image.update()


def texture_bake_top_down_run(context, source_objs, props, base_name, output_dir):
    """Orthographic top-down bake of every source mesh together onto one
    flat quad - a single-face ground plane standing in for a whole area.

    The sources are duplicated and joined (optionally trimmed to their
    selected faces), and their materials made single-user, exactly as
    the atlas bake does. A quad matching the joined footprint's exact
    X/Y bounds is placed just above the highest point, and Cycles bakes
    selected-to-active from it: with zero cage extrusion, each ray
    starts on the quad and travels straight down (-Z), so every texel
    records the first surface it hits from above. Image sizes follow
    the quad's aspect (_tb_top_down_image_dims).

    An extra coverage pass (every source emitting white, no margin)
    marks which texels hit geometry at all; it becomes the Diffuse
    image's alpha, so empty areas are transparent. Diffuse's colour
    still bleeds out by the bake margin under the transparent edge,
    which keeps mipmaps from fringing dark.

    Afterwards the quad drops to the lowest point of the sources, gets
    one merged material (via apply_shader_slot_maps, with Diffuse alpha
    wired to the BSDF), and records its world X/Y extents as custom
    properties; the joined duplicate is deleted. Returns (plane_obj,
    saved_paths, log), or raises RuntimeError with a user-facing
    message on failure."""

    log = []
    margin = 8

    source_dup = _tb_duplicate_and_join(context, source_objs, props.tb_selected_faces_only)
    if source_dup is None or len(source_dup.data.polygons) == 0:
        if source_dup is not None:
            _tb_remove_object_and_mesh(source_dup)
        raise RuntimeError("No faces to bake (nothing selected on the source meshes?)")

    plane = None
    bake_mat = None
    original_engine = context.scene.render.engine
    succeeded = False
    try:
        source_uv = source_dup.data.uv_layers.get("MHO_Source")
        if source_uv is not None:
            source_uv.active_render = True
        _tb_make_single_user_materials(source_dup)
        if len(source_dup.material_slots) == 0:
            # The emit/coverage overrides live in materials - with none at
            # all, nothing would emit and the whole bake would come out
            # empty. A blank one still bakes coverage (and black colour).
            source_dup.data.materials.append(bpy.data.materials.new(name="TB_Blank"))

        lo, hi = _tb_world_bounds(context, source_dup)
        size_x, size_y = hi.x - lo.x, hi.y - lo.y
        if size_x <= 0.0 or size_y <= 0.0:
            raise RuntimeError("Selection has no area from above (zero X or Y size)")
        center_x = (lo.x + hi.x) / 2.0
        center_y = (lo.y + hi.y) / 2.0
        height = hi.z - lo.z
        pad = max(size_x, size_y, height) * 0.01 + 0.001

        plane = _tb_new_top_down_plane(
            f"{base_name}", center_x, center_y, hi.z + pad, size_x, size_y,
            source_objs[0].users_collection[0],
        )
        # Temporary material only to hold the TB_Target node - with
        # selected-to-active, the target's own shading is never sampled.
        bake_mat = bpy.data.materials.new(name="TB_TopDown_Bake")
        bake_mat.use_nodes = True
        plane.data.materials.append(bake_mat)

        context.scene.render.engine = "CYCLES"
        bpy.ops.object.select_all(action="DESELECT")
        source_dup.select_set(True)
        plane.select_set(True)
        context.view_layer.objects.active = plane

        ray_kwargs = dict(
            use_selected_to_active=True,
            use_cage=False,
            cage_extrusion=0.0,
            max_ray_distance=height + 2.0 * pad,
            margin=margin,
            margin_type="EXTEND",
            target="IMAGE_TEXTURES",
            save_mode="INTERNAL",
            use_clear=True,
        )

        dims = {
            channel: _tb_top_down_image_dims(int(getattr(props, prop)), size_x, size_y)
            for channel, prop in (
                ("diffuse", "tb_diffuse_size"),
                ("normal", "tb_normal_size"),
                ("specmask", "tb_specmask_size"),
                ("speccolor", "tb_speccolor_size"),
            )
        }
        images = {}

        # Normal first, while the sources' real Normal Map setups are
        # still intact (the emit passes below override their outputs).
        for channel in ("normal", "diffuse", "specmask", "speccolor"):
            w, h = dims[channel]
            img = _tb_new_atlas_image(
                f"{base_name}_{_TB_LABEL[channel]}", w, channel, height=h,
                alpha=(channel == "diffuse"),
            )
            _tb_bake_selected_to_active(source_dup, plane, channel, img, ray_kwargs)
            images[channel] = img
            log.append(f"OK    baked top-down {_TB_LABEL[channel]} at {w}x{h}")

        # Coverage mask -> Diffuse alpha. No margin here: texels that
        # missed the geometry must stay exactly 0.
        w, h = dims["diffuse"]
        coverage = bpy.data.images.new(name="TB_Coverage", width=w, height=h, alpha=False)
        temp_nodes = _tb_add_coverage_overrides(source_dup)
        temp_nodes += _tb_add_target_nodes(plane, coverage)
        bpy.ops.object.bake(type="EMIT", **dict(ray_kwargs, margin=0))
        _tb_remove_temp_nodes(temp_nodes)
        _tb_apply_coverage_alpha(images["diffuse"], coverage)
        bpy.data.images.remove(coverage)
        log.append("OK    Diffuse alpha = top-down coverage (empty areas transparent)")

        succeeded = True
    finally:
        context.scene.render.engine = original_engine
        _tb_remove_object_and_mesh(source_dup)
        if bake_mat is not None:
            bpy.data.materials.remove(bake_mat)
        if not succeeded and plane is not None:
            _tb_remove_object_and_mesh(plane)

    saved_paths = []
    for channel, img in images.items():
        # Build the filename from the intended name, not img.name - if an
        # image of that name already exists, Blender suffixes ".001".
        path = os.path.join(output_dir, f"{base_name}_{_TB_LABEL[channel]}.png")
        img.filepath_raw = path
        img.file_format = "PNG"
        img.save()
        saved_paths.append(path)
        log.append(f"OK    saved '{path}'")

    merged_mat = bpy.data.materials.new(name=f"{base_name}_Merged")
    merged_mat.ssm_diffuse_image = images.get("diffuse")
    merged_mat.ssm_normal_image = images.get("normal")
    merged_mat.ssm_specular_image = images.get("specmask")
    merged_mat.ssm_speccolor_image = images.get("speccolor")
    apply_shader_slot_maps(merged_mat)
    # Show the cut-out in the viewport too: Diffuse alpha -> BSDF Alpha.
    diff_node = merged_mat.node_tree.nodes.get("SlotMap_Diffuse")
    bsdf = _ssm_find_principled_bsdf(merged_mat.node_tree.nodes)
    if diff_node is not None and bsdf is not None:
        merged_mat.node_tree.links.new(diff_node.outputs["Alpha"], bsdf.inputs["Alpha"])
    plane.data.materials.clear()
    plane.data.materials.append(merged_mat)

    # Sit the finished quad at the bottom of the baked area, like a ground
    # plane, and record exactly what area the image covers.
    plane.location.z = lo.z
    plane["mho_top_down_min_xy"] = (lo.x, lo.y)
    plane["mho_top_down_max_xy"] = (hi.x, hi.y)
    plane["mho_top_down_z_range"] = (lo.z, hi.z)

    purge_orphan_data()

    log.append(
        f"OK    '{plane.name}' covers X {lo.x:.3f}..{hi.x:.3f}, Y {lo.y:.3f}..{hi.y:.3f} "
        f"({size_x:.3f} x {size_y:.3f}), at Z {lo.z:.3f}"
    )
    return plane, saved_paths, log


# ---------------------------------------------------------------------
# Texture Baker: operator
# ---------------------------------------------------------------------

class MHO_OT_texture_bake(Operator):
    """Merge every material on each selected mesh object into its own
    atlas: duplicate each one separately, build a fresh non-overlapping
    UV layout, bake Diffuse/Normal/SpecMask/SpecColor to PNGs in a
    'textures' subfolder next to the .blend, and assign one merged
    material per object"""

    bl_idname = "mho.texture_bake"
    bl_label = "Bake to Atlas"
    bl_description = (
        "For each selected mesh object separately: duplicate it, build a fresh UV atlas, "
        "bake Diffuse/Normal/Spec Mask/Spec Color to PNGs in a 'textures' subfolder next "
        "to this .blend, and assign one merged material - the originals are left untouched"
    )
    bl_options = {"REGISTER", "UNDO"}

    reduce: BoolProperty(
        name="Reduce Polycount",
        description="High-to-low bake onto a reduced copy (see the Quality slider)",
        default=False,
        options={"SKIP_SAVE"},
    )

    @classmethod
    def description(cls, context, properties):
        if properties.reduce:
            return (
                "For each selected mesh object separately: make a reduced-polycount copy "
                "(flat areas dissolved, then collapsed to the Quality fraction of the original "
                "triangles), build a fresh UV atlas on it, and bake Diffuse/Normal/Spec Mask/"
                "Spec Color from the ORIGINAL mesh onto it - removed detail goes into the Normal "
                "map. PNGs go in a 'textures' subfolder next to this .blend as "
                "<object>_Reduced_D.png etc. - the originals are left untouched"
            )
        return cls.bl_description

    @classmethod
    def poll(cls, context):
        return bool(bpy.data.filepath) and any(
            o.type == "MESH" for o in context.selected_objects
        )

    def execute(self, context):
        if not bpy.data.filepath:
            self.report({"ERROR"}, "Save this .blend file first - the atlas PNGs export next to it")
            return {"CANCELLED"}

        if context.mode != "OBJECT":
            bpy.ops.object.mode_set(mode="OBJECT")

        source_objs = [o for o in context.selected_objects if o.type == "MESH"]
        if not source_objs:
            self.report({"ERROR"}, "No mesh objects selected")
            return {"CANCELLED"}

        props = context.scene.mho_props
        output_dir = os.path.join(os.path.dirname(bpy.data.filepath), _TB_OUTPUT_SUBFOLDER)
        os.makedirs(output_dir, exist_ok=True)

        target_objs = []
        total_saved = 0
        errors = []

        for obj in source_objs:
            try:
                base_name = f"{obj.name}_Reduced" if self.reduce else obj.name
                target_obj, saved_paths, log = texture_bake_run(
                    context, [obj], props, base_name, output_dir, reduce=self.reduce
                )
            except RuntimeError as exc:
                errors.append(f"{obj.name}: {exc}")
                continue

            for line in log:
                print(line)

            target_objs.append(target_obj)
            total_saved += len(saved_paths)

        if not target_objs:
            self.report({"ERROR"}, "; ".join(errors) if errors else "Nothing baked")
            return {"CANCELLED"}

        bpy.ops.object.select_all(action="DESELECT")
        for t in target_objs:
            t.select_set(True)
        context.view_layer.objects.active = target_objs[-1]

        msg = f"Baked {len(target_objs)} atlas object(s), {total_saved} texture(s) total, into '{output_dir}'"
        if errors:
            msg += f" ({len(errors)} skipped: {'; '.join(errors)})"
            self.report({"WARNING"}, msg)
        else:
            self.report({"INFO"}, msg)
        return {"FINISHED"}


class MHO_OT_texture_bake_top_down(Operator):
    """Bake a straight-down orthographic view of all selected meshes
    together onto one flat quad fitted to their bounds - a single-face
    ground plane, transparent wherever there's no geometry"""

    bl_idname = "mho.texture_bake_top_down"
    bl_label = "Bake Top-Down (Flat)"
    bl_description = (
        "Bake all selected meshes together as seen straight down from above onto one flat "
        "quad fitted to their X/Y bounds: Diffuse/Normal/Spec Mask/Spec Color PNGs go in a "
        "'textures' subfolder next to this .blend, with Diffuse alpha transparent wherever "
        "there's no geometry. The quad is left at the lowest point with the merged material, "
        "and its X/Y extents are stored as custom properties - the originals are left untouched"
    )
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context):
        return bool(bpy.data.filepath) and any(
            o.type == "MESH" for o in context.selected_objects
        )

    def execute(self, context):
        if not bpy.data.filepath:
            self.report({"ERROR"}, "Save this .blend file first - the baked PNGs export next to it")
            return {"CANCELLED"}

        # Leaving Edit Mode also syncs any face selection back to the mesh,
        # which "Selected Faces Only" reads.
        if context.mode != "OBJECT":
            bpy.ops.object.mode_set(mode="OBJECT")

        source_objs = [o for o in context.selected_objects if o.type == "MESH"]
        if not source_objs:
            self.report({"ERROR"}, "No mesh objects selected")
            return {"CANCELLED"}

        active = context.view_layer.objects.active
        name_obj = active if active in source_objs else source_objs[0]
        base_name = f"{name_obj.name}_TopDown"

        props = context.scene.mho_props
        output_dir = os.path.join(os.path.dirname(bpy.data.filepath), _TB_OUTPUT_SUBFOLDER)
        os.makedirs(output_dir, exist_ok=True)

        try:
            plane, saved_paths, log = texture_bake_top_down_run(
                context, source_objs, props, base_name, output_dir
            )
        except RuntimeError as exc:
            self.report({"ERROR"}, str(exc))
            return {"CANCELLED"}

        for line in log:
            print(line)

        bpy.ops.object.select_all(action="DESELECT")
        plane.select_set(True)
        context.view_layer.objects.active = plane

        lo_x, lo_y = plane["mho_top_down_min_xy"]
        hi_x, hi_y = plane["mho_top_down_max_xy"]
        self.report(
            {"INFO"},
            f"Baked '{plane.name}' from {len(source_objs)} object(s), {len(saved_paths)} "
            f"texture(s) into '{output_dir}' - covers X {lo_x:.3f}..{hi_x:.3f}, "
            f"Y {lo_y:.3f}..{hi_y:.3f}",
        )
        return {"FINISHED"}


# ---------------------------------------------------------------------
# Panel (sidebar UI) â€” all tools live in the "MHO Actions" tab
# ---------------------------------------------------------------------

class MHO_PT_fbx_to_actions_panel(Panel):
    bl_label = "MHO FBX to Actions"
    bl_idname = "MHO_PT_fbx_to_actions"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "MHO Actions"

    def draw(self, context):
        layout = self.layout
        props = context.scene.mho_props

        layout.prop(props, "input_dir")
        layout.prop(props, "output_blend")
        layout.prop(props, "allow_duplicate_names")
        layout.separator()
        layout.operator("mho.import_fbx_to_actions", icon="IMPORT")


class MHO_PT_actions_to_nla_panel(Panel):
    bl_label = "MHO Actions to NLA"
    bl_idname = "MHO_PT_actions_to_nla"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "MHO Actions"

    def draw(self, context):
        layout = self.layout
        props = context.scene.mho_props

        layout.prop(props, "target_armature")
        layout.prop(props, "actions_library")
        layout.prop(props, "skip_existing_nla")
        layout.separator()

        armature_obj = resolve_nla_target_armature(context)
        if armature_needs_root_track(armature_obj):
            box = layout.box()
            box.label(text="No NLA tracks yet on this armature", icon="INFO")
            box.operator("mho.add_root_pose_track", icon="ARMATURE_DATA")
            layout.separator()

        layout.operator("mho.append_actions_to_nla", icon="NLA_PUSHDOWN")

        layout.separator()
        box = layout.box()
        box.label(text="Isolate to Root Pose", icon="ARMATURE_DATA")
        if armature_obj is not None and _MHO_NLA_ISOLATE_KEY in armature_obj:
            box.label(text="Isolated to Root right now.", icon="INFO")
            box.operator("mho.toggle_nla_root", text="Restore NLA Tracks", icon="LOOP_BACK")
        else:
            box.label(text="Mutes every track but Root, for a clean rest pose")
            box.operator("mho.toggle_nla_root", text="Isolate to Root", icon="ARMATURE_DATA")

        layout.separator()
        box = layout.box()
        box.label(text="Offset", icon="TRIA_UP_BAR")
        box.label(text="Shifts the bone(s) directly under 'root'")
        box.row(align=True).prop(props, "zo_axis", expand=True)
        box.prop(props, "zo_offset_amount")
        box.prop(props, "zo_blend_type")
        box.operator("mho.create_z_offset_track", text="Create Offset Track", icon="TRIA_UP_BAR")


class MHO_PT_prepare_viewport_panel(Panel):
    bl_label = "MHO Prepare Viewport"
    bl_idname = "MHO_PT_prepare_viewport"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "MHO Actions"

    def draw(self, context):
        layout = self.layout
        props = context.scene.mho_props

        layout.prop(props, "armature_stick_scene_only")
        layout.separator()
        layout.operator("mho.prepare_viewport", icon="OVERLAY")

        layout.separator()
        layout.operator("mho.render_pose_snapshot", icon="RENDER_STILL")

        layout.separator()
        layout.label(text=f"Script Version: {MHO_ADDON_VERSION}", icon="INFO")


class MHO_PT_weight_transfer_panel(Panel):
    bl_label = "MHO Weight Transfer"
    bl_idname = "MHO_PT_weight_transfer"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "MHO Actions"

    def draw(self, context):
        layout = self.layout
        props = context.scene.mho_props

        layout.prop(props, "wt_source_obj")
        layout.prop(props, "wt_target_obj")

        layout.separator()
        layout.prop(props, "wt_ray_radius_mm")

        layout.separator()
        layout.prop(props, "wt_do_smooth")
        if props.wt_do_smooth:
            box = layout.box()
            box.prop(props, "wt_smooth_factor")
            box.prop(props, "wt_smooth_repeat")

        layout.separator()
        layout.prop(props, "wt_add_armature_mod")
        row = layout.row()
        row.enabled = props.wt_add_armature_mod
        row.prop(props, "wt_sort_by_bone_hierarchy")

        layout.separator()
        layout.operator("mho.transfer_weights", icon="MOD_DATA_TRANSFER")


class MHO_PT_weight_smooth_panel(Panel):
    bl_label = "MHO Weight Smooth"
    bl_idname = "MHO_PT_weight_smooth"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "MHO Actions"

    def draw(self, context):
        layout = self.layout
        props = context.scene.mho_props

        layout.prop(props, "ws_smooth_factor")
        layout.prop(props, "ws_smooth_repeat")
        layout.prop(props, "ws_selected_verts_only")

        layout.separator()
        row = layout.row(align=True)
        row.operator("mho.smooth_vertex_weights", text="Smooth All Groups", icon="MOD_SMOOTH")
        row.operator("mho.smooth_active_vertex_group", text="Smooth Active Group", icon="MOD_SMOOTH")


class MHO_PT_vgroup_mirror_panel(Panel):
    bl_label = "MHO VGroup Mirror"
    bl_idname = "MHO_PT_vgroup_mirror"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "MHO Actions"

    def draw(self, context):
        layout = self.layout
        props = context.scene.mho_props
        obj = context.active_object

        box = layout.box()
        box.label(text="Rename Vertex Groups", icon="GROUP_VERTEX")
        if obj is not None and _MHO_VGROUP_RENAME_KEY in obj:
            box.label(text="Renamed for mirroring right now.", icon="INFO")
            box.operator("mho.revert_vgroup_names", icon="LOOP_BACK")
        else:
            box.label(text="e.g. 'g_r_shoulder' -> 'g_shoulder.R'")
            box.prop(props, "vg_axis_correction_degrees")
            box.prop(props, "vg_lock_rest_pose")
            box.operator("mho.rename_vgroups_for_mirror", icon="MOD_MIRROR")

        layout.separator()

        box = layout.box()
        box.label(text="Mirror Weights", icon="MOD_MIRROR")
        box.row(align=True).prop(props, "mw_mirror_axis", expand=True)
        box.prop(props, "mw_direction")

        box.separator()
        row_opts = box.row(align=True)
        row_opts.prop(props, "mw_use_clipping")
        row_opts.prop(props, "mw_invert_source_side")
        row2 = box.row(align=True)
        row2.operator("mho.symmetrize_weights_data_transfer", text="Mirror All Groups", icon="MOD_DATA_TRANSFER")
        row2.operator("mho.mirror_active_group", text="Mirror Active Group", icon="MOD_DATA_TRANSFER")
        row3 = box.row(align=True)
        row3.operator("mho.wipe_vgroup_side", text="Wipe Destination Side", icon="TRASH")
        row3.operator("mho.wipe_active_group", text="Wipe Active Group", icon="TRASH")

        box.separator()
        row4 = box.row(align=True)
        row4.operator("mho.diagnose_mirror_axis", text="Diagnose (Weights)", icon="VIEWZOOM")
        row4.operator("mho.diagnose_mirror_axis_geometry", text="Diagnose (Geometry)", icon="MESH_DATA")
        box.operator("mho.clear_console", text="Clear Console", icon="CONSOLE")


class MHO_PT_model_prep_panel(Panel):
    bl_label = "MHO MFF Model Prep"
    bl_idname = "MHO_PT_model_prep"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "MHO Actions"

    def draw(self, context):
        layout = self.layout
        props = context.scene.mho_props

        box = layout.box()
        box.label(text="1. Scale & Rotate", icon="ORIENTATION_GLOBAL")
        box.prop(props, "mp_scale_factor")
        box.prop(props, "mp_rotate_z_degrees")
        box.operator("mho.model_prep_scale_rotate", icon="MOD_DISPLACE")

        layout.separator()

        box = layout.box()
        box.label(text="2. Join & Merge", icon="MESH_DATA")
        box.prop(props, "mp_merge_distance")
        box.operator("mho.model_prep_join_merge", icon="AUTOMERGE_ON")


class MHO_PT_symmetrical_sculpt_adjust_panel(Panel):
    bl_label = "MHO Symmetrical Sculpt Adjust"
    bl_idname = "MHO_PT_symmetrical_sculpt_adjust"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "MHO Actions"

    def draw(self, context):
        layout = self.layout
        layout.row(align=True).prop(context.scene.mho_props, "sculpt_symmetry_axis", expand=True)
        layout.operator("mho.symmetrical_sculpt_adjust", icon="SCULPTMODE_HLT")


class MHO_PT_shader_slot_maps_panel(Panel):
    bl_label = "MHO Shader Slot Maps"
    bl_idname = "MHO_PT_shader_slot_maps"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "MHO Actions"

    @classmethod
    def poll(cls, context):
        return context.active_object is not None and context.active_object.type == "MESH"

    def draw(self, context):
        layout = self.layout
        obj = context.active_object

        if not obj.material_slots:
            layout.label(text="No material slots on this object.")
            return

        for slot in obj.material_slots:
            mat = slot.material
            box = layout.box()
            if mat is None:
                box.label(text="(empty slot)", icon="ERROR")
                continue

            box.label(text=mat.name, icon="MATERIAL")
            col = box.column(align=True)

            row = col.split(factor=0.16, align=True)
            row.label(text="DIF")
            row.template_ID(mat, "ssm_diffuse_image", open="image.open")

            row = col.split(factor=0.16, align=True)
            row.label(text="NRM")
            row.template_ID(mat, "ssm_normal_image", open="image.open")

            row = col.split(factor=0.16, align=True)
            row.label(text="SMSK")
            row.template_ID(mat, "ssm_specular_image", open="image.open")

            row = col.split(factor=0.16, align=True)
            row.label(text="SCLR")
            row.template_ID(mat, "ssm_speccolor_image", open="image.open")

            row = box.row(align=True)
            op = row.operator("mho.detect_shader_slot_maps", text="Detect", icon="VIEWZOOM")
            op.material_name = mat.name
            op = row.operator("mho.apply_shader_slot_maps", text="Apply")
            op.material_name = mat.name

        layout.separator()
        row = layout.row(align=True)
        row.operator("mho.detect_shader_slot_maps_all", text="Detect All", icon="VIEWZOOM")
        row.operator("mho.apply_shader_slot_maps_all", text="Apply All", icon="MATERIAL")


class MHO_PT_export_for_game_panel(Panel):
    bl_label = "MHO Export for Game"
    bl_idname = "MHO_PT_export_for_game"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "MHO Actions"

    def draw(self, context):
        layout = self.layout

        if not bpy.data.filepath:
            layout.label(text="Save the .blend file first.", icon="ERROR")
        else:
            blend_name = os.path.splitext(os.path.basename(bpy.data.filepath))[0]
            layout.label(text=f"Exports to: {blend_name}.fbx", icon="EXPORT")

        layout.operator("mho.export_for_game", icon="EXPORT")

        layout.separator()
        box = layout.box()
        box.label(text="Batch Export Animations", icon="RENDER_ANIMATION")
        if not bpy.data.filepath:
            box.label(text="Save the .blend file first.", icon="ERROR")
        else:
            box.label(text="Exports to: Blend_anims/<track>.fbx", icon="EXPORT")
        box.label(text="Skips 'Offset' and 'Root' tracks")
        box.operator("mho.batch_export_animations", icon="RENDER_ANIMATION")


class MHO_PT_texture_bake_panel(Panel):
    bl_label = "MHO Texture Baker"
    bl_idname = "MHO_PT_texture_bake"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "MHO Actions"

    def draw(self, context):
        layout = self.layout
        props = context.scene.mho_props

        col = layout.column(align=True)
        col.prop(props, "tb_diffuse_size")
        col.prop(props, "tb_normal_size")
        col.prop(props, "tb_specmask_size")
        col.prop(props, "tb_speccolor_size")

        layout.prop(props, "tb_selected_faces_only")
        layout.separator()

        if not bpy.data.filepath:
            layout.label(text="Save the .blend file first.", icon="ERROR")
        else:
            layout.label(text=f"Saves to: {_TB_OUTPUT_SUBFOLDER}/", icon="EXPORT")

        layout.operator("mho.texture_bake", icon="RENDER_STILL")

        box = layout.box()
        col = box.column(align=True)
        col.prop(props, "tb_reduce_quality", slider=True)
        col.prop(props, "tb_reduce_dissolve_flat")
        op = box.operator("mho.texture_bake", text="Bake to Atlas (Reduced)", icon="MOD_DECIM")
        op.reduce = True

        layout.operator("mho.texture_bake_top_down", icon="VIEW_ORTHO")


# ---------------------------------------------------------------------
# Register
# ---------------------------------------------------------------------

classes = (
    MHO_Props,
    MHO_OT_import_fbx_to_actions,
    MHO_OT_append_actions_to_nla,
    MHO_OT_add_root_pose_track,
    MHO_OT_toggle_nla_root,
    MHO_OT_create_z_offset_track,
    MHO_OT_prepare_viewport,
    MHO_OT_render_pose_snapshot,
    MHO_OT_transfer_weights,
    MHO_OT_smooth_vertex_weights,
    MHO_OT_smooth_active_vertex_group,
    MHO_OT_rename_vgroups_for_mirror,
    MHO_OT_revert_vgroup_names,
    MHO_OT_diagnose_mirror_axis,
    MHO_OT_diagnose_mirror_axis_geometry,
    MHO_OT_clear_console,
    MHO_OT_wipe_vgroup_side,
    MHO_OT_wipe_active_group,
    MHO_OT_symmetrize_weights_data_transfer,
    MHO_OT_mirror_active_group,
    MHO_OT_mirror_weights_custom,
    MHO_OT_model_prep_scale_rotate,
    MHO_OT_model_prep_join_merge,
    MHO_OT_symmetrical_sculpt_adjust,
    MHO_OT_apply_shader_slot_maps,
    MHO_OT_apply_shader_slot_maps_all,
    MHO_OT_detect_shader_slot_maps,
    MHO_OT_detect_shader_slot_maps_all,
    MHO_OT_texture_bake,
    MHO_OT_texture_bake_top_down,
    MHO_OT_export_for_game,
    MHO_OT_batch_export_animations,
    MHO_PT_fbx_to_actions_panel,
    MHO_PT_actions_to_nla_panel,
    MHO_PT_prepare_viewport_panel,
    MHO_PT_weight_transfer_panel,
    MHO_PT_weight_smooth_panel,
    MHO_PT_vgroup_mirror_panel,
    MHO_PT_model_prep_panel,
    MHO_PT_symmetrical_sculpt_adjust_panel,
    MHO_PT_shader_slot_maps_panel,
    MHO_PT_texture_bake_panel,
    MHO_PT_export_for_game_panel,
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    bpy.types.Scene.mho_props = PointerProperty(type=MHO_Props)

    # Shader Slot Maps images live on the Material itself (per-slot),
    # not in the shared mho_props PropertyGroup, since each material
    # slot needs its own diffuse/normal/spec-mask assignment.
    bpy.types.Material.ssm_diffuse_image = PointerProperty(
        name="Diffuse",
        type=bpy.types.Image,
        description="Diffuse / base color image for this material",
    )
    bpy.types.Material.ssm_normal_image = PointerProperty(
        name="Normal",
        type=bpy.types.Image,
        description="Normal map image for this material (Non-Color)",
    )
    bpy.types.Material.ssm_specular_image = PointerProperty(
        name="Spec Mask",
        type=bpy.types.Image,
        description="Specular mask image: R=Roughness, G=Metallic, B=Specular IOR Level",
    )
    bpy.types.Material.ssm_speccolor_image = PointerProperty(
        name="Spec Color",
        type=bpy.types.Image,
        description="Specular tint color image for this material",
    )


def unregister():
    del bpy.types.Material.ssm_speccolor_image
    del bpy.types.Material.ssm_specular_image
    del bpy.types.Material.ssm_normal_image
    del bpy.types.Material.ssm_diffuse_image
    del bpy.types.Scene.mho_props
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
