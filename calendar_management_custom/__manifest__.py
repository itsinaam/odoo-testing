# -*- coding: utf-8 -*-
{
    'name': 'Calendar Management Custom',
    'version': '19.0',
    'category': 'Productivity',
    'summary': 'Custom calendar management system with events, reminders, status-based colors, and message summarization',
    'description': """
Calendar Management Custom
==========================
A simple calendar management system providing:
- CRUD for custom events
- Tree/Form/Calendar/Search views
- Status workflow (Draft/Confirmed/Done/Cancelled)
- Validation: end datetime must be after start datetime
- Status-based color coding in calendar
- Reminder notifications (internal + optional email)
- Organizer defaults to current user
- NEW: Summarize chatter/input messages into a concise summary
""",
    'author': 'Your Company',
    'website': 'https://www.yourcompany.com',
    'depends': ['base', 'mail'],
    'data': [
        'security/ir.model.access.csv',
        'data/ir_cron.xml',
        'views/calendar_event_views.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
