# MHO Actions — Handoff Context for Claude Code

## What this is
A single-file Blender extension (`mho_fbx_to_actions/__init__.py` +
`blender_manifest.toml`) called **"MHO Actions"**, built for a game-modding
pipeline (Marvel Heroes Omega project, character `drstrange_classicvu`).
Targets Blender 5.0+, developed/tested on **Blender 5.1**.
Current version: **1.53.0**. Installed via drag-drop onto Blender or
Get Extensions > Install from Disk.

There is no build step, no external deps, no tests directory — it's one
Python file registered as a Blender addon (`bpy` extension, metadata in
`blender_manifest.toml` rather than a legacy `bl_info` dict). Edit
`mho_fbx_to_actions/__init__.py` directly, then run `python package.py`
to produce the installable package at
`dist/mho_fbx_to_actions-<version>.zip` (it refuses to build if the
`__init__.py` and manifest versions disagree). `dist/` is git-ignored.

## Rig conventions (matters for any bone-hierarchy logic)
- Bone naming: `g_` prefix, `g_l_`/`g_r_` for left/right, `g_c_` for
  center, plain names for unpaired bones (e.g. `g_cape1`).
- Top-of-hierarchy bone is always literally named **`root`**.
- Some rigs have a pass-through tier of bones directly under `root`
  whose names end in **`_offset`** — these are not real motion bones
  and should never be keyed directly; the real motion bones are their
  children, one level further down.

## Panels/tools (in build order)
1. **FBX to Actions** — batch-import FBX exports, convert to Actions,
   save to an action library `.blend`.
2. **Actions to NLA** — append actions, push to NLA tracks.
   - *Add Root Pose Track*: creates a `Root` track (neutral pose keyed
     at frame 1) if none exists.
   - *Isolate to Root* (Quick-Favorites-safe toggle): mutes all tracks
     but Root, remembers/restores prior mute state.
   - *Offset*: X/Y/Z axis + amount; creates/updates an `Offset` NLA
     track at the top of the stack, additive blend. Targets are the
     direct children of `root` — **except** any child whose name ends
     in `_offset`, in which case its own children are targeted instead
     (one level deeper). See "Recent changes" below — this took two
     iterations to get right. World-space math via
     `matrix_world.to_3x3().inverted()`.
   - *Batch Export Animations*: exports one FBX per NLA track to
     `Blend_anims/`, skipping `Offset`/`Root`. Unmutes everything then
     mutes top-down one at a time (standard NLA Replace blending —
     highest unmuted track wins). Each clip's frame range is trimmed to
     its own strip's range before export. All mute states + scene frame
     range restored in a `finally` block.
3. **Prepare Viewport** — stick display, weight-paint overlay, material
   preview shading. Also hosts **Render Pose Snapshot** (new in 1.49.x,
   see below). Shows `Script Version: X.X.X`.
4. **Weight Transfer** — source→target transfer, smooth, armature
   modifier, sort groups by bone hierarchy.
5. **Weight Smooth** — Smooth All / Smooth Active Group, Selected-
   Vertices-Only option, preserves current mode.
6. **VGroup Mirror** (the big one):
   - *Rename for Mirror / Revert Names*: `g_l_X`/`g_r_X` ↔ `X.L`/`X.R`.
   - *Diagnose (Weights)* vs *Diagnose (Geometry)* — Geometry is the
     reliable one.
   - *Mirror All / Mirror Active Group* (recommended method): duplicate
     mesh → strip modifiers from duplicate → Mirror modifier builds
     clean geometric half → Data Transfer (Nearest Face Interpolated)
     projects weights back. *Invert Source Side* toggle for when the
     side-heuristic guesses wrong.
   - *Wipe Destination Side / Wipe Active Group*.
   - Old KDTree "Mirror Weights (Custom)" is deprecated/hidden (still
     registered, not in UI).
   - *Clear Console* (Windows only).
7. **MFF Model Prep** — Scale & Rotate, then Join & Merge.
8. **Symmetrical Sculpt Adjust** — X/Y/Z toggle + sculpt setup.
9. **Shader Slot Maps** — Diffuse/Normal/SpecMask/SpecColor per
   material, Detect/Apply.
10. **Export for Game** — full-hierarchy FBX export, game-ready
    settings, shared via `_mho_game_fbx_export_kwargs()` with Batch
    Export Animations.
11. **Texture Baker** — per-object/per-selected-faces atlas baking,
    smart UV unwrap, Data Transfer projection.
    - *Bake to Atlas (Reduced)* (1.52.0): same operator as Bake to Atlas
      with `reduce=True`. The welded duplicate stays as the high-poly
      bake source; a copy built with `new_from_object` (modifiers baked
      in) is planar-dissolved (5°, `delimit={"MATERIAL"}`, toggle
      `tb_reduce_dissolve_flat`) then Decimate-Collapsed to
      `tb_reduce_quality` × original tris (only if still above target).
      Atlas UV goes on the low copy (seams computed while it still has
      per-material slots), then it gets a single temp bake material and
      all four channels bake selected-to-active high → low. Cage
      extrusion / max ray distance come from the measured high↔low
      nearest-surface gap (BVH, world space, both directions). Output
      `<object>_Reduced_*.png` on `<object>_Reduced_Atlas`.
    - Emit-channel sources (1.53.0, all bakes), in priority order:
      (1) what's actually connected in the material's graph, read at the
      rendering Principled BSDF (the first one upstream of the active
      output, so through Mix Shaders): Base Color → Diffuse, Specular
      Tint → Spec Color, and for Spec Mask the colour going INTO the
      Separate Color node behind Roughness/Metallic/Specular (the
      individual remapped sockets can't be reassembled into a mask);
      (2) the `ssm_*` image; (3) Diffuse = Base Color value, others
      **black**. Normal bakes the real shading; if a material's Normal
      is unconnected but it has `ssm_normal_image`, that's wired in
      through a temp Normal Map node for the bake. The Emission node
      defaults to white - always set its colour (this caused an
      all-white Diffuse bug before 1.51.1).
    - Testing gotcha: an in-memory (generated, unsaved) image loses its
      pixel edits whenever its colour space changes - fill test images'
      pixels after node setup and `pack()` them.
    - *Bake Top-Down (Flat)* (1.50.0, reworked 1.51.0): bakes all selected
      meshes together, seen straight down, onto one single-face quad
      fitted to their exact X/Y bounds (Kurt's workflow: import the zone
      ground mesh, bake, import the quad into the game as a simple
      one-face ground plane). Selected-to-active from a quad just above
      the top, zero cage extrusion, so rays go straight down (-Z). Same
      four channels as the atlas bake, saved as `<active>_TopDown_D.png`
      etc.; the long side uses the chosen size, the short side is scaled
      and rounded UP to a power of two. An extra no-margin coverage pass
      (all sources emit white) becomes the **Diffuse alpha**, so empty
      areas are transparent while colour still bleeds under the edge
      (margin). The quad ends at the lowest point with the merged
      material (Diffuse alpha wired to BSDF Alpha); custom props
      `mho_top_down_min_xy` / `_max_xy` / `_z_range` record the covered
      area (UV 0,0 = min X/Y corner, image up = +Y).

## Recent changes (this session, chronological)
- **Batch Export Animations frame-range fix — attempted, then reverted.**
  Tried adding `use_scene_range=True` to the FBX export call so the
  exporter would respect the per-strip `scene.frame_start/frame_end`
  already being set. User reported it didn't work and asked to roll
  back; rolled back cleanly, confirmed byte-identical to the pre-change
  file. **This is still an open bug** — exported clip length can
  desync from the NLA track/strip the file is named after. The
  `use_scene_range=True` approach was tried and rejected; a different
  fix is needed (possibilities not yet explored: `bake_anim_step`
  interaction, whether the issue is actually in the NLA-mute-per-track
  loop leaving stale baked keys outside the strip range, or something
  about how Blender 5.1's layered Action model computes bake range).
  Do not re-attempt `use_scene_range=True` without new information —
  user already tested and rejected it once.
- **Offset tool `_offset` bone handling — two iterations:**
  1st pass (wrong): excluded `_offset`-suffixed bones from the target
  list entirely.
  2nd pass (correct, current behavior): for each direct child of
  `root`, if its name ends in `_offset` (case-insensitive), reach
  through it and target *its* children instead (one level deeper);
  otherwise target the bone directly. `root` itself is never a target
  in either case.
- **New: Render Pose Snapshot** (`MHO_OT_render_pose_snapshot`, in the
  Prepare Viewport panel). Renders the active camera at a fixed
  **300×420** (changed once from an initial 420×420 per user request),
  with camera depth-of-field and scene motion blur force-disabled for
  the render only, saves as `Pose_<timestamp>.png` next to the current
  `.blend` file, and restores every render/camera setting touched
  afterward in a `finally` block. Polls disabled (greyed out) if the
  file isn't saved yet or there's no active scene camera.

## Key technical gotchas (learned the hard way — don't relearn these)
- **Panels can't write to ID data in `draw()`** — must be in an
  operator.
- **Blender 5.1's layered Action model**: `Action.fcurves` no longer
  exists directly — delete+recreate actions rather than clearing
  fcurves; `keyframe_insert()` still works fine.
- **`bpy.ops.mesh.delete()` respects mirror-editing**
  (`mesh.use_mirror_x`) and can cascade-delete far more than intended —
  use `bmesh` directly to bypass Edit Mode UI settings.
- **Applying a non-first modifier** gives wrong results silently (+ a
  warning) — strip other modifiers first, or use
  `modifier_move_to_index`.
- **`layers_vgroup_select_src`** on Data Transfer is a dynamic enum:
  `'ALL'` + exact vertex group names — not `'ACTIVE'`.
- **Offsetting every bone compounds through hierarchy** and distorts
  mesh — only move top-of-chain bones (now: excluding `_offset`
  pass-throughs, targeting their children instead), let FK propagate.
- **Armature object's own rotation** (common from FBX Y-up/Z-up
  import) means armature-space ≠ world-space — always convert via
  `matrix_world` for "true world axis" operations.
- **NLA track list**: index 0 = bottom/base, last index = top; new
  tracks always append at top.
- **NLA Add/Combine blending** is relative to true rest — reset pose to
  identity before computing additive offsets.
- **Icon names must be validated** against real Blender enums (caught
  `OUTLINER_DATA_GROUP_VERTEX` → should be `GROUP_VERTEX`).
- **File-path conventions**: every feature that writes output derives
  its path from `bpy.data.filepath` (the current `.blend`'s location),
  guards with `if not bpy.data.filepath: report error, return
  {"CANCELLED"}`, and restores any scene/render/object settings it
  changed in a `finally` block. Follow this pattern for any new
  export/render feature.

## Open items / not yet resolved
- **Batch Export Animations frame-range mismatch is still unfixed**
  (see above) — the one attempted fix was reverted at the user's
  request because it didn't solve it.
- User plans to eventually wrap all top-level panels into one
  collapsible parent sub-panel once workflow order is finalized —
  trades drag-reordering for one-click collapse-all (sub-panels keep
  individual collapse too). Waiting on user's go-ahead + final order;
  "MHO" prefix would drop from sub-panel titles at that point.
- Mirror sign-heuristic occasionally picks the wrong side —
  `Invert Source Side` is the manual workaround; no automatic robust
  fix built (tabled, too many false positives).
- Smoothing after Symmetrize can bleed across the mirror seam
  (Blender's smooth has no seam awareness) — discussed, not built.
- The Offset tool's world-space axis fix and axis picker should be
  retested against the corrected `_offset`-bone-handling logic above,
  to confirm both changes work together correctly on the live rig.

## Working conventions to keep
- Every new operator: `bl_idname` prefixed `mho.`, `bl_label`,
  `bl_description` (user-facing, more detail than the label),
  `bl_options` including `{"REGISTER", "UNDO"}` unless the operation
  can't sensibly be undone (e.g. file export/render — use `{"REGISTER"}`
  only).
- Any operator that temporarily changes scene/render/object state:
  save originals up front, wrap the risky work in `try/finally`,
  restore in `finally` unconditionally.
- Register new operator classes in the `classes = (...)` tuple near the
  end of the file, near their logical siblings.
- Bump `MHO_ADDON_VERSION` (near the top of `__init__.py`) and
  `version` in `blender_manifest.toml` together, on every change.
  `python package.py` refuses to build if they disagree.
- Files are UTF-8 **without a BOM**. Windows PowerShell 5.1's
  `Set-Content -Encoding utf8` adds one - edit with the Edit tool or
  Bash `sed` instead.
- Blender 5.1 is installed at
  `C:\Program Files\Blender Foundation\Blender 5.1\blender.exe`, so
  changes can be tested headless: `blender -b --factory-startup
  --python test.py`, where the script does `sys.path.insert(0,
  r"C:\Dev\MHO-Blender-Addon")`, imports `mho_fbx_to_actions`, calls
  `register()` after `wm.read_factory_settings`, and saves the scene to
  a scratch `.blend` first (the output-writing tools need
  `bpy.data.filepath`).
