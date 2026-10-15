# inference

Callers use `swap_faces`, not FaceFusion internals. No `app.db` import. No DB transaction held across the swap. Missing CUDA fails the job and writes no file.
