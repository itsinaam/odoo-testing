# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class CalendarManagementEvent(models.Model):
    _name = 'calendar.management.event'
    _description = 'Calendar Management Event'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'start_datetime desc, id desc'

    name = fields.Char(string='Event Title', required=True, tracking=True)
    description = fields.Text(string='Description')

    start_datetime = fields.Datetime(string='Start Date & Time', required=True, tracking=True)
    end_datetime = fields.Datetime(string='End Date & Time', required=True, tracking=True)

    attendee_ids = fields.Many2many(
        'res.partner',
        'calendar_mgmt_event_partner_rel',
        'event_id',
        'partner_id',
        string='Attendees',
    )

    location = fields.Char(string='Location')

    status = fields.Selection(
        [
            ('draft', 'Draft'),
            ('confirmed', 'Confirmed'),
            ('done', 'Done'),
            ('cancelled', 'Cancelled'),
        ],
        string='Status',
        default='draft',
        required=True,
        tracking=True,
    )

    organizer_id = fields.Many2one(
        'res.users',
        string='Organizer',
        default=lambda self: self.env.user,
        required=True,
        tracking=True,
    )

    # Used by calendar view for color coding
    color = fields.Integer(string='Color Index', compute='_compute_color', store=True)

    # Reminder configuration
    reminder_enabled = fields.Boolean(string='Reminder Enabled', default=False, tracking=True)
    reminder_minutes = fields.Integer(
        string='Reminder (minutes before)',
        default=30,
        help='How many minutes before the start time to send a reminder.',
    )
    reminder_type = fields.Selection(
        [
            ('internal', 'Internal Notification'),
            ('email', 'Email'),
            ('both', 'Both'),
        ],
        string='Reminder Type',
        default='internal',
        required=True,
    )
    reminder_sent = fields.Boolean(string='Reminder Sent', default=False, copy=False)

    @api.depends('status')
    def _compute_color(self):
        # Keep it simple and deterministic; Odoo calendar uses integer color indexes.
        mapping = {
            'draft': 3,       # yellow-ish
            'confirmed': 10,  # blue-ish
            'done': 7,        # green-ish
            'cancelled': 1,   # red-ish
        }
        for rec in self:
            rec.color = mapping.get(rec.status, 0)

    @api.constrains('start_datetime', 'end_datetime')
    def _check_dates(self):
        for rec in self:
            if rec.start_datetime and rec.end_datetime and rec.end_datetime <= rec.start_datetime:
                raise ValidationError(_('End Date & Time must be greater than Start Date & Time.'))

    def action_confirm(self):
        self.write({'status': 'confirmed'})

    def action_done(self):
        self.write({'status': 'done'})

    def action_cancel(self):
        self.write({'status': 'cancelled'})

    def action_set_draft(self):
        self.write({'status': 'draft'})

    def _send_internal_reminder(self):
        """Send an internal notification to organizer and attendees."""
        for rec in self:
            partners = rec.attendee_ids
            if rec.organizer_id and rec.organizer_id.partner_id:
                partners |= rec.organizer_id.partner_id
            partners = partners.filtered(lambda p: p.active)

            if not partners:
                continue

            body = _(
                'Reminder: <b>%(title)s</b><br/>'
                'When: %(start)s → %(end)s<br/>'
                'Location: %(location)s',
                title=rec.name,
                start=fields.Datetime.to_string(rec.start_datetime) if rec.start_datetime else '',
                end=fields.Datetime.to_string(rec.end_datetime) if rec.end_datetime else '',
                location=rec.location or _('Not available'),
            )

            rec.message_post(
                body=body,
                partner_ids=partners.ids,
                message_type='notification',
                subtype_xmlid='mail.mt_note',
            )

    def _send_email_reminder(self):
        """Send an email reminder using mail.thread's message_post (creates mail.mail)."""
        for rec in self:
            partners = rec.attendee_ids
            if rec.organizer_id and rec.organizer_id.partner_id:
                partners |= rec.organizer_id.partner_id
            partners = partners.filtered(lambda p: p.email)

            if not partners:
                continue

            subject = _('Event Reminder: %s') % (rec.name,)
            body = _(
                '<p>This is a reminder for the event <b>%(title)s</b>.</p>'
                '<ul>'
                '<li><b>Start:</b> %(start)s</li>'
                '<li><b>End:</b> %(end)s</li>'
                '<li><b>Location:</b> %(location)s</li>'
                '</ul>',
                title=rec.name,
                start=fields.Datetime.to_string(rec.start_datetime) if rec.start_datetime else '',
                end=fields.Datetime.to_string(rec.end_datetime) if rec.end_datetime else '',
                location=rec.location or _('Not available'),
            )

            rec.message_post(
                subject=subject,
                body=body,
                partner_ids=partners.ids,
                message_type='email',
                subtype_xmlid='mail.mt_note',
            )

    @api.model
    def _cron_send_event_reminders(self):
        """Cron: send reminders for upcoming events.

        Rules:
        - Only for reminder_enabled events
        - Only if not reminder_sent
        - Only for events not cancelled/done
        - Trigger when now >= (start - reminder_minutes)
        """
        now = fields.Datetime.now()

        events = self.search([
            ('reminder_enabled', '=', True),
            ('reminder_sent', '=', False),
            ('status', 'not in', ['done', 'cancelled']),
            ('start_datetime', '!=', False),
        ])

        to_mark_sent = self.browse()
        for rec in events:
            reminder_dt = rec.start_datetime - fields.DateTime.timedelta(minutes=rec.reminder_minutes or 0)
            if now >= reminder_dt:
                if rec.reminder_type in ('internal', 'both'):
                    rec._send_internal_reminder()
                if rec.reminder_type in ('email', 'both'):
                    rec._send_email_reminder()
                to_mark_sent |= rec

        if to_mark_sent:
            to_mark_sent.write({'reminder_sent': True})
