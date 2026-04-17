# Calendar Management Custom - Tests

## How to run

### CLI (recommended)
Run Odoo with tests enabled and stop after init:

- Install module and run its tests:
  - `-i calendar_management_custom --test-enable --stop-after-init`

Example:
- `./odoo-bin -d <db> -i calendar_management_custom --test-enable --stop-after-init`

## What is covered
- Create event (basic fields + attendees)
- Validation: end_datetime must be strictly greater than start_datetime
- Default organizer: checks common organizer fields (`organizer_id` or `user_id`), otherwise skips
- Status transitions via `action_confirm()` and `action_done()` if present
- Write validation (invalid end time rejected)
- Unlink deletes the record
