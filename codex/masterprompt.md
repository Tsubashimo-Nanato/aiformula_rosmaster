# ROSMASTER Codex Master Prompt

You are working in the Windows workspace:

`E:\Mess\Projects\Programming\aiformula\ROSMASTER`

This directory is the repository root. Treat it as the only writable workspace.

## Hard Boundaries

- You may create, edit, move, or delete files only inside `E:\Mess\Projects\Programming\aiformula\ROSMASTER`.
- You may read files outside this root when needed for context, dependency discovery, or documentation lookup.
- Do not write generated files, caches, temporary artifacts, logs, or test outputs outside this root.
- Before any recursive delete or move, resolve the absolute path and confirm it is inside the workspace root.
- Do not use destructive git commands such as `git reset --hard`, `git clean -fd`, or `git checkout -- <file>` unless the user explicitly asks for that exact operation.

## Operating Style

- Inspect the existing project before making assumptions.
- Prefer `rg` and `rg --files` for search and file discovery.
- Keep changes scoped to the user's request.
- Preserve existing conventions, naming, formatting, and architecture once a codebase exists.
- Do not revert user changes unless the user explicitly asks.
- Use `apply_patch` for manual file edits.
- Use PowerShell-native commands for Windows filesystem operations.
- Avoid shell pipelines that compose unsafe path strings for deletion or moving.

## Communication

- Give concise progress updates while working.
- Explain what context you are gathering and why.
- Before editing files, state what you are about to change.
- In final responses, summarize the changed files, verification performed, and any remaining risks or untested areas.
- Use absolute clickable file paths when referencing local files.

## Verification

- Run the narrowest meaningful checks for the change.
- Prefer existing project scripts, tests, linters, or build commands when they are available.
- If no verification command exists yet, state that clearly.
- If a command fails because of missing dependencies or environment setup, report the exact blocker and the next practical step.

## Repository Defaults

- Keep generated artifacts under explicit project folders such as `codex`, `docs`, `scripts`, `tests`, `build`, or tool-specific directories inside the workspace.
- Keep prompts and agent instructions in `codex/`.
- Prefer Markdown for human-readable planning, prompt, and documentation files.
- Keep files ASCII unless the target file already uses another encoding or non-ASCII content is required.

## Project Context

The end goal is to adapt the ROSMASTER robot into a development and testing platform for the AI Formula / Sophia robot stack.

- The ROSMASTER robot is the Jetson-based Yahboom ROSMASTER system reachable as `jetson@192.168.0.38` when it is on the same network.
- The Sophia reference robot source is mirrored from `E:\Mess\Projects\Programming\aiformula\aiformula_sophia`.
- The two robots are mechanically different. The live ROSMASTER should now be treated as a Yahboom R2-style platform with front steering and two rear drive motors, controlled through `Rosmaster_Lib` and `/dev/myserial`; Sophia is a differential two-drive-wheel AI Formula platform driven by CAN.
- Current ROSMASTER adaptation rule: lock the front steering servos at neutral and command the rear motors with differential-drive `linear.x`/`angular.z` semantics through `/aiformula_control/game_pad/cmd_vel`.
- Current USB controller mapping: hold `R2` as the deadman, use left-stick vertical for forward/back, and use right-stick horizontal for differential yaw.
- Preferred robot-side launch wrapper: `/home/jetson/workspace/ros2_ws/src/aiformula/launchers/shellscript/launch_all_nodes.sh`. It sources ROS 2, Yahboom, and adapter setup files before launching. RViz is on by default; pass `use_rviz:=false` for headless SSH.
- Do not assume Sophia motor, CAN, ZED X, VectorNav, or rear potentiometer hardware exists on ROSMASTER.
- Prefer compatibility wrappers and topic adapters over changing Sophia algorithms in place. The first target is to make ROSMASTER publish and consume the ROS topics Sophia software expects.
- Keep all mirrored source snapshots read-only in spirit. Do adaptation work in local overlay packages or documentation under this workspace unless the user explicitly asks for a different layout.
- The ROSMASTER factory image is backed up elsewhere, but do not modify the live robot over SSH unless the user explicitly asks for live deployment or live cleanup.

## Important Local References

- `codex/jetson_robot_inspection.md`: hardware and software inspection of the ROSMASTER robot.
- `codex/aiformula_sophia_inspection.md`: source inspection of the Sophia AI Formula robot.
- `codex/rosmaster_aiformula_adaptation_roadmap.md`: current migration strategy and staged implementation plan.
- `codex/live_rosmaster_deployment_log.md`: live Jetson deployment, build, launch, actuator, RViz, and boot cleanup results.
- `mirrors/rosmaster_robot/`: local reference snapshot copied from the ROSMASTER Jetson.
- `mirrors/aiformula_sophia/`: local reference snapshot copied from the Sophia repository.
- `workspace/ros2_ws/src/aiformula/`: deployment-shaped ROS 2 adapter workspace mirrored to `/home/jetson/workspace/ros2_ws/src/aiformula` on the ROSMASTER robot.

## Current Instruction File

This file is the master prompt for future Codex work in this workspace. When starting work here, read and follow it before making changes.
