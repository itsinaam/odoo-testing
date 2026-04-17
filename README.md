# odoo-testing

## Added Module: calendar_management_custom

### Folder placement
Place the module at:
- `odoo-testing/calendar_management_custom/`

### Install
1. Restart Odoo server
2. Enable Developer Mode
3. Apps → Update Apps List
4. Search for **Calendar Management Custom** → Install

### Test checklist
- Create an event with Start/End; verify validation blocks End <= Start
- Verify organizer defaults to the current user
- Verify Tree/Form/Calendar views load from **Calendar Management → Events**
- Set status to Draft/Confirmed/Done/Cancelled and confirm calendar color changes
- Enable reminders and set minutes; wait for cron (runs every 5 minutes)
- Confirm internal notification appears in chatter; email is sent if attendees have emails
