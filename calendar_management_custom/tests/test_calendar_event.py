# -*- coding: utf-8 -*-

from odoo.tests.common import TransactionCase
from odoo.exceptions import ValidationError


class TestCalendarManagementCustomEvent(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Event = cls.env['calendar.management.event']

        # Use existing demo/admin user as organizer reference
        cls.user = cls.env.user

        # Create a couple of partners to use as attendees
        cls.partner_1 = cls.env['res.partner'].create({'name': 'Attendee 1', 'email': 'attendee1@example.com'})
        cls.partner_2 = cls.env['res.partner'].create({'name': 'Attendee 2', 'email': 'attendee2@example.com'})

    def _base_vals(self, **overrides):
        vals = {
            'name': 'Test Event',
            'description': 'Test Description',
            'start_datetime': '2026-01-01 10:00:00',
            'end_datetime': '2026-01-01 11:00:00',
            'location': 'Test Location',
            'attendee_ids': [(6, 0, [self.partner_1.id, self.partner_2.id])],
        }
        vals.update(overrides)
        return vals

    def test_create_event_success(self):
        event = self.Event.create(self._base_vals())
        self.assertTrue(event, 'Event should be created')
        self.assertEqual(event.name, 'Test Event')
        self.assertEqual(set(event.attendee_ids.ids), {self.partner_1.id, self.partner_2.id})

    def test_end_must_be_greater_than_start(self):
        with self.assertRaises(ValidationError):
            self.Event.create(self._base_vals(end_datetime='2026-01-01 09:00:00'))

        with self.assertRaises(ValidationError):
            self.Event.create(self._base_vals(end_datetime='2026-01-01 10:00:00'))

    def test_default_organizer_is_current_user(self):
        event = self.Event.create(self._base_vals(name='Organizer Default Test'))

        # We don't assume the exact field name; check common patterns.
        # If your model uses a different organizer field, adjust this assertion.
        organizer_field = None
        for candidate in ('organizer_id', 'user_id'):
            if candidate in event._fields:
                organizer_field = candidate
                break

        if not organizer_field:
            self.skipTest("Organizer field not found (expected 'organizer_id' or 'user_id').")

        self.assertEqual(event[organizer_field], self.user, 'Organizer should default to current user')

    def test_status_actions_confirm_done(self):
        event = self.Event.create(self._base_vals(name='Status Action Test'))

        # If status default is draft, this should move it to confirmed
        if hasattr(event, 'action_confirm'):
            event.action_confirm()
            self.assertEqual(event.status, 'confirmed')
        else:
            self.skipTest('action_confirm not implemented on model')

        if hasattr(event, 'action_done'):
            event.action_done()
            self.assertEqual(event.status, 'done')
        else:
            self.skipTest('action_done not implemented on model')

    def test_write_updates_and_validation(self):
        event = self.Event.create(self._base_vals(name='Write Validation Test'))

        # Valid update
        event.write({'end_datetime': '2026-01-01 12:00:00'})
        self.assertEqual(str(event.end_datetime), '2026-01-01 12:00:00')

        # Invalid update should raise
        with self.assertRaises(ValidationError):
            event.write({'end_datetime': '2026-01-01 09:00:00'})

    def test_unlink_deletes_event(self):
        event = self.Event.create(self._base_vals(name='Unlink Test'))
        event_id = event.id
        event.unlink()
        self.assertFalse(self.Event.browse(event_id).exists(), 'Event should be deleted')
