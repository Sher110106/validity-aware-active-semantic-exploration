# Human control surface

Only these sidecar controls are permitted: `paused`, `stop`, monotonically
increasing `resume_generation`, exact `approved_hashes`, and conservative
attempt/disk/stall/runtime floors. Unknown keys or changed approved hashes
pause without taking a resource action. `stop=true` is terminal for the
controller instance. Connectivity loss and unknown spend are automatic stops.
