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
            body = rec._build_event_reminder_email_body()

            rec.message_post(
                subject=subject,
                body=body,
                partner_ids=partners.ids,
                message_type='email',
                subtype_xmlid='mail.mt_note',
            )

    def _build_event_reminder_email_body(self):
        """Build the HTML body for reminder emails.

        Also includes a short summary of recent chatter/input messages when available.
        """
        self.ensure_one()

        summary = self._get_recent_messages_summary(max_messages=10, max_chars=400)
        summary_html = ''
        if summary:
            summary_html = _(
                '<p><b>Recent notes summary:</b> %(summary)s</p>',
                summary=summary,
            )

        return _(
            '<p>This is a reminder for the event <b>%(title)s</b>.</p>'
            '<ul>'
            '<li><b>Start:</b> %(start)s</li>'
            '<li><b>End:</b> %(end)s</li>'
            '<li><b>Location:</b> %(location)s</li>'
            '</ul>'
            '%(summary_html)s',
            title=self.name,
            start=fields.Datetime.to_string(self.start_datetime) if self.start_datetime else '',
            end=fields.Datetime.to_string(self.end_datetime) if self.end_datetime else '',
            location=self.location or _('Not available'),
            summary_html=summary_html,
        )

    def _get_recent_messages_summary(self, max_messages=10, max_chars=400):
        """Summarize recent chatter/input messages for this event.

        This is a lightweight, deterministic summarizer (no external AI calls):
        - takes the last `max_messages` messages
        - extracts plain text
        - de-duplicates lines
        - truncates to `max_chars`

        Returns an empty string if no usable content is available.
        """
        self.ensure_one()

        # message_ids is available because the model inherits mail.thread in this module.
        messages = self.message_ids.sorted('date')[-max_messages:]
        if not messages:
            return ''

        parts = []
        for msg in messages:
            # Prefer body (HTML) but fall back to subject.
            text = (msg.body or '')
            text = self.env['mail.render.mixin']._render_template_inline(text, {}) if False else text
            # Convert HTML to text using Odoo helper.
            text = self.env['ir.qweb']._get_text(text) if hasattr(self.env['ir.qweb'], '_get_text') else text
            text = (text or '').strip()
            if not text:
                text = (msg.subject or '').strip()
            if text:
                parts.append(text)

        if not parts:
            return ''

        # De-duplicate while preserving order.
        seen = set()
        deduped = []
        for p in parts:
            key = ' '.join(p.split())
            if key and key not in seen:
                seen.add(key)
                deduped.append(key)

        summary = ' | '.join(deduped)
        if len(summary) > max_chars:
            summary = summary[: max_chars - 1].rstrip() + '…'
        return summary

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
