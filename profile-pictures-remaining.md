# Profile Pictures - Remaining Actions

## Done (POC)

- Profile picture fields on Colleague model (BinaryField, hash, content_type)
- Hash-based image serving view with security headers
- Avatar display in all 4 locations (placement table, assignment panel, colleague panel, user table)
- `download_profile_pictures` command (randomuser.me)
- `assign_profile_pictures` command (for `just setup`)
- `load_full_data` assigns pictures from `profile_pictures/` folder

## Remaining

### Upload & Processing

- [ ] Add Pillow dependency for image resize/re-encoding on upload
- [ ] Create profile page ("Mijn profiel") with photo upload
- [ ] Validate uploaded files (JPEG/PNG only, max 5MB)
- [ ] Re-encode via Pillow to 128x128 JPEG/WebP (strips embedded scripts)
- [ ] Link user name in menubar to profile page

### Security & Production

- [ ] Serve images from separate (sub)domain to isolate from session cookies
  - Option A: Signed URLs (time-limited HMAC) — for sensitive content
  - Option B: No auth, rely on unguessable hashes — sufficient for profile pictures
- [ ] Decide on `Cache-Control: public` vs `private` based on auth approach

### Other

- [ ] DPIA/AVG review for storing profile photos
- [ ] Tests for upload flow, image validation, resize, and serving
