"""Canonical default email-template definitions."""

DEFAULT_TEMPLATES = {'header': {'category': 'layout',
            'subject': '',
            'body_html': '<div style="background:#114f55;padding:20px 24px;">\n'
                         '  <a href="{{app_url}}" '
                         'style="color:#ffffff;font-size:22px;font-weight:700;text-decoration:none;letter-spacing:0.5px;">\n'
                         '    IHCA\n'
                         '  </a>\n'
                         '  <div style="color:#b8dfe3;font-size:13px;margin-top:4px;">international health connect '
                         'association</div>\n'
                         '</div>\n'
                         '<div style="padding:24px;font-family:Arial,sans-serif;color:#0f172a;line-height:1.55;">',
            'description': 'Kopfzeile (Logo & Branding) — wird vor jeder Mail eingefügt'},
 'footer': {'category': 'layout',
            'subject': '',
            'body_html': '</div>\n'
                         '<div style="background:#f1f5f9;padding:18px '
                         '24px;font-family:Arial,sans-serif;font-size:12px;color:#64748b;border-top:1px solid '
                         '#cbd5e1;">\n'
                         '  <p style="margin:0 0 8px 0;">Mit freundlichen Grüßen,<br/><strong '
                         'style="color:#114f55;">Ihr IHCA-Team</strong></p>\n'
                         '  <p style="margin:0;">\n'
                         '    <a href="{{app_url}}" style="color:#114f55;text-decoration:none;">ihca.de</a>\n'
                         '    · <a href="{{app_url}}/impressum" style="color:#64748b;">Impressum</a>\n'
                         '    · <a href="{{app_url}}/datenschutz" style="color:#64748b;">Datenschutz</a>\n'
                         '  </p>\n'
                         '</div>',
            'description': 'Fußzeile (Grußformel, Rechtslinks) — wird nach jeder Mail eingefügt'},
 'partner_new_submission': {'category': 'partner',
                            'subject': 'Neue Anmeldung von {{user_name}} für {{partner_name}}',
                            'body_html': '<h2 style="color:#114f55;margin:0 0 16px 0;">Neue Anmeldung</h2>\n'
                                         '<p>Hallo,</p>\n'
                                         '<p>ein neuer Arzt hat sich bei <strong>{{partner_name}}</strong> für Ihren '
                                         'Service registriert und wartet auf Ihre Rückmeldung.</p>\n'
                                         '\n'
                                         '<table cellpadding="8" cellspacing="0" '
                                         'style="border-collapse:collapse;margin:16px '
                                         '0;background:#f8fafc;border-radius:4px;">\n'
                                         '  <tr><td '
                                         'style="color:#64748b;">Name</td><td><strong>{{user_name}}</strong></td></tr>\n'
                                         '  <tr><td style="color:#64748b;">E-Mail</td><td><a '
                                         'href="mailto:{{user_email}}" '
                                         'style="color:#114f55;">{{user_email}}</a></td></tr>\n'
                                         '  <tr><td '
                                         'style="color:#64748b;">Fachrichtung</td><td>{{field_of_study}}</td></tr>\n'
                                         '  <tr><td '
                                         'style="color:#64748b;">Bundesland</td><td>{{bundesland}}</td></tr>\n'
                                         '</table>\n'
                                         '\n'
                                         '<p style="margin:24px 0;">\n'
                                         '  <a href="{{open_user_link}}"\n'
                                         '     style="background:#114f55;color:#ffffff;padding:12px '
                                         '24px;text-decoration:none;border-radius:4px;font-weight:600;display:inline-block;">\n'
                                         '    Anmeldung im Dashboard öffnen\n'
                                         '  </a>\n'
                                         '</p>\n'
                                         '<p style="color:#64748b;font-size:13px;">Klicken Sie auf den Button, um '
                                         'direkt zu den Details des Arztes zu springen — dort können Sie den Nachweis '
                                         'hochladen und den Meilenstein freischalten.</p>',
                            'description': 'An Partner bei neuer User-Anmeldung (partner_select / '
                                           'partner_multiselect)'},
 'user_awaiting_partner': {'category': 'user',
                           'subject': 'Ihre Anmeldung bei {{partner_name}} wurde versendet',
                           'body_html': '<h2 style="color:#114f55;margin:0 0 16px 0;">Vielen Dank, '
                                        '{{user_name}}!</h2>\n'
                                        '<p>Ihre Anmeldung bei <strong>{{partner_name}}</strong> wurde erfolgreich '
                                        'übermittelt.</p>\n'
                                        '\n'
                                        '<div style="background:#fef3c7;border-left:4px solid #f59e0b;padding:14px '
                                        '18px;margin:18px 0;border-radius:2px;">\n'
                                        '  <strong style="color:#92400e;">Wie geht es weiter?</strong><br/>\n'
                                        '  <span style="color:#78350f;">Der Partner prüft Ihre Anfrage und wird sich '
                                        'in Kürze bei Ihnen melden. Sobald Ihr Meilenstein bearbeitet wurde, erhalten '
                                        'Sie automatisch eine Bestätigungsmail.</span>\n'
                                        '</div>\n'
                                        '\n'
                                        '<p>Sie können den aktuellen Status jederzeit in Ihrem Dashboard '
                                        'einsehen:</p>\n'
                                        '<p style="margin:20px 0;">\n'
                                        '  <a href="{{app_url}}/dashboard"\n'
                                        '     style="background:#114f55;color:#ffffff;padding:12px '
                                        '24px;text-decoration:none;border-radius:4px;font-weight:600;display:inline-block;">\n'
                                        '    Zum Dashboard\n'
                                        '  </a>\n'
                                        '</p>',
                           'description': 'An User nach Partner-Anmeldung (Wartezeit-Info)'},
 'user_milestone_completed': {'category': 'user',
                              'subject': '{{partner_name}} hat Ihren Meilenstein abgeschlossen',
                              'body_html': '<h2 style="color:#059669;margin:0 0 16px 0;">Gute Nachrichten, '
                                           '{{user_name}}!</h2>\n'
                                           '<p><strong>{{partner_name}}</strong> hat Ihren Meilenstein '
                                           '<em>"{{milestone_title}}"</em> für Sie abgeschlossen.</p>\n'
                                           '\n'
                                           '<div style="background:#d1fae5;border-left:4px solid #059669;padding:14px '
                                           '18px;margin:18px 0;border-radius:2px;">\n'
                                           '  <strong style="color:#065f46;">Was bedeutet das?</strong><br/>\n'
                                           '  <span style="color:#064e3b;">Sie können jetzt mit dem nächsten Schritt '
                                           'auf Ihrer Reise zur deutschen Approbation fortfahren. Der Fortschritt in '
                                           'Ihrem Dashboard wurde automatisch aktualisiert.</span>\n'
                                           '</div>\n'
                                           '\n'
                                           '<p style="margin:20px 0;">\n'
                                           '  <a href="{{app_url}}/dashboard"\n'
                                           '     style="background:#114f55;color:#ffffff;padding:12px '
                                           '24px;text-decoration:none;border-radius:4px;font-weight:600;display:inline-block;">\n'
                                           '    Nächsten Schritt ansehen\n'
                                           '  </a>\n'
                                           '</p>',
                              'description': 'An User wenn Partner den Meilenstein freischaltet'},
 'user_partner_step_rejected': {'category': 'user',
                                'subject': '{{partner_name}} benötigt eine Korrektur bei {{step_title}}',
                                'body_html': '<h2 style="color:#b45309;margin:0 0 16px 0;">Bitte prüfen Sie Ihre Angaben, {{user_name}}</h2>\n'
                                             '<p><strong>{{partner_name}}</strong> konnte den Schritt <em>"{{step_title}}"</em> noch nicht freigeben.</p>\n'
                                             '<div style="background:#fef3c7;border-left:4px solid #d97706;padding:14px 18px;margin:18px 0;border-radius:2px;">\n'
                                             '  <strong style="color:#92400e;">Rückmeldung des Partners</strong><br/>\n'
                                             '  <span style="color:#78350f;">{{rejection_reason}}</span>\n'
                                             '</div>\n'
                                             '<p>Ihr Prozess wurde zum Schritt <strong>{{reopened_step_title}}</strong> zurückgesetzt. Bitte ergänzen oder korrigieren Sie dort die benötigten Angaben.</p>\n'
                                             '<p style="margin:20px 0;">\n'
                                             '  <a href="{{app_url}}/dashboard" style="background:#114f55;color:#ffffff;padding:12px 24px;text-decoration:none;border-radius:4px;font-weight:600;display:inline-block;">\n'
                                             '    Schritt im Dashboard öffnen\n'
                                             '  </a>\n'
                                             '</p>',
                                'description': 'An User wenn ein Partner einen Step ablehnt und den Prozess zurücksetzt'},
 'user_step_entered': {'category': 'step',
                       'subject': 'Schritt gestartet: {{step_title}}',
                       'body_html': '<h2 style="color:#114f55;margin:0 0 16px 0;">Hallo {{user_name}},</h2>\n'
                                    '<p>Sie haben den Schritt <strong>{{step_title}}</strong> auf Ihrer Reise zur '
                                    'deutschen Approbation begonnen.</p>\n'
                                    '\n'
                                    '<div style="background:#e0f2fe;border-left:4px solid #0284c7;padding:14px '
                                    '18px;margin:18px 0;border-radius:2px;">\n'
                                    '  <strong style="color:#075985;">Schritt {{step_order}} von '
                                    '{{total_steps}}</strong><br/>\n'
                                    '  <span style="color:#0c4a6e;">{{step_description}}</span>\n'
                                    '</div>\n'
                                    '\n'
                                    '<p style="margin:20px 0;">\n'
                                    '  <a href="{{app_url}}/dashboard"\n'
                                    '     style="background:#114f55;color:#ffffff;padding:12px '
                                    '24px;text-decoration:none;border-radius:4px;font-weight:600;display:inline-block;">\n'
                                    '    Schritt im Dashboard öffnen\n'
                                    '  </a>\n'
                                    '</p>',
                       'description': 'An User wenn ein Schritt neu gestartet wird (email_on_enter)'},
 'user_step_updated': {'category': 'step',
                       'subject': 'Schritt aktualisiert: {{step_title}}',
                       'body_html': '<h2 style="color:#114f55;margin:0 0 16px 0;">Hallo {{user_name}},</h2>\n'
                                    '<p>Ihr Fortschritt im Schritt <strong>{{step_title}}</strong> wurde '
                                    'aktualisiert.</p>\n'
                                    '<p style="color:#64748b;font-size:14px;">Sie können jederzeit in Ihrem Dashboard '
                                    'weiter\xadmachen oder bereits eingetragene Daten anpassen.</p>\n'
                                    '\n'
                                    '<p style="margin:20px 0;">\n'
                                    '  <a href="{{app_url}}/dashboard"\n'
                                    '     style="background:#114f55;color:#ffffff;padding:12px '
                                    '24px;text-decoration:none;border-radius:4px;font-weight:600;display:inline-block;">\n'
                                    '    Zum Dashboard\n'
                                    '  </a>\n'
                                    '</p>',
                       'description': 'An User wenn ein Schritt bearbeitet wird (email_on_edit)'},
 'user_step_completed': {'category': 'step',
                         'subject': 'Schritt abgeschlossen: {{step_title}}',
                         'body_html': '<h2 style="color:#059669;margin:0 0 16px 0;">Glückwunsch, {{user_name}}!</h2>\n'
                                      '<p>Sie haben den Schritt <strong>{{step_title}}</strong> erfolgreich '
                                      'abgeschlossen.</p>\n'
                                      '\n'
                                      '<div style="background:#d1fae5;border-left:4px solid #059669;padding:14px '
                                      '18px;margin:18px 0;border-radius:2px;">\n'
                                      '  <strong style="color:#065f46;">Weiter geht\'s!</strong><br/>\n'
                                      '  <span style="color:#064e3b;">Schauen Sie in Ihrem Dashboard nach, welcher '
                                      'Schritt als Nächstes auf Sie wartet.</span>\n'
                                      '</div>\n'
                                      '\n'
                                      '<p style="margin:20px 0;">\n'
                                      '  <a href="{{app_url}}/dashboard"\n'
                                      '     style="background:#114f55;color:#ffffff;padding:12px '
                                      '24px;text-decoration:none;border-radius:4px;font-weight:600;display:inline-block;">\n'
                                      '    Nächsten Schritt ansehen\n'
                                      '  </a>\n'
                                      '</p>',
                         'description': 'An User wenn ein Schritt abgeschlossen wird (email_on_leave)'},
 'user_next_step_unlocked': {'category': 'step',
                             'subject': 'Nächster Schritt freigeschaltet: {{step_title}}',
                             'body_html': '<h2 style="color:#114f55;margin:0 0 16px 0;">Weiter geht\'s, '
                                          '{{user_name}}!</h2>\n'
                                          '<p>{{partner_name}} hat Ihren vorherigen Meilenstein abgeschlossen — Ihr '
                                          'nächster Schritt <strong>{{step_title}}</strong> ist jetzt für Sie '
                                          'freigeschaltet.</p>\n'
                                          '\n'
                                          '<div style="background:#e0f2fe;border-left:4px solid #0284c7;padding:14px '
                                          '18px;margin:18px 0;border-radius:2px;">\n'
                                          '  <strong style="color:#075985;">Was kommt jetzt?</strong><br/>\n'
                                          '  <span style="color:#0c4a6e;">{{step_description}}</span>\n'
                                          '</div>\n'
                                          '\n'
                                          '<p style="margin:20px 0;">\n'
                                          '  <a href="{{app_url}}/dashboard"\n'
                                          '     style="background:#114f55;color:#ffffff;padding:12px '
                                          '24px;text-decoration:none;border-radius:4px;font-weight:600;display:inline-block;">\n'
                                          '    Zum Dashboard\n'
                                          '  </a>\n'
                                          '</p>',
                             'description': 'An User wenn Partner einen Meilenstein abschließt und dadurch der nächste '
                                            'Schritt freigegeben wird'},
 'user_password_reset': {'category': 'user',
                         'subject': 'Passwort zurücksetzen — IHCA',
                         'body_html': '<h2 style="color:#114f55;margin:0 0 16px 0;">Passwort zurücksetzen</h2>\n'
                                      '<p>Hallo,</p>\n'
                                      '<p>Sie (oder jemand in Ihrem Namen) hat angefordert, das Passwort Ihres '
                                      'IHCA-Kontos zurückzusetzen.</p>\n'
                                      '\n'
                                      '<p style="margin:24px 0;">\n'
                                      '  <a href="{{reset_link}}"\n'
                                      '     style="background:#114f55;color:#ffffff;padding:12px '
                                      '24px;text-decoration:none;border-radius:4px;font-weight:600;display:inline-block;">\n'
                                      '    Passwort jetzt zurücksetzen\n'
                                      '  </a>\n'
                                      '</p>\n'
                                      '\n'
                                      '<p style="color:#64748b;font-size:13px;">Dieser Link ist <strong>1 '
                                      'Stunde</strong> gültig. Sollten Sie keine Zurücksetzung angefordert haben, '
                                      'können Sie diese E-Mail einfach ignorieren.</p>',
                         'description': 'Passwort-Reset-Link per E-Mail'}}


# Browser/App notifications deliberately use shorter copy than email. They are
# stored on the same message definition so event handlers reference one stable
# template key while both channels remain independently editable.
DEFAULT_NOTIFICATION_CONTENT = {
    "partner_new_submission": {
        "notification_title": "Neue Anmeldung von {{user_name}}",
        "notification_body": "{{user_name}} interessiert sich für {{partner_name}}. Öffnen Sie die Anmeldung im Partner-Dashboard.",
    },
    "user_awaiting_partner": {
        "notification_title": "Anmeldung an {{partner_name}} gesendet",
        "notification_body": "Ihre Anfrage wurde übermittelt. Sie erhalten eine Nachricht, sobald der Partner den Vorgang bearbeitet hat.",
    },
    "user_milestone_completed": {
        "notification_title": "Meilenstein abgeschlossen",
        "notification_body": "{{partner_name}} hat „{{milestone_title}}“ abgeschlossen. Der nächste Schritt ist jetzt verfügbar.",
    },
    "user_partner_step_rejected": {
        "notification_title": "Korrektur für {{step_title}} erforderlich",
        "notification_body": "{{partner_name}}: {{rejection_reason}} Bitte bearbeiten Sie „{{reopened_step_title}}“ erneut.",
    },
    "user_step_entered": {
        "notification_title": "Neuer Schritt: {{step_title}}",
        "notification_body": "Schritt {{step_order}} ist jetzt für Sie verfügbar.",
    },
    "user_step_updated": {
        "notification_title": "{{step_title}} wurde aktualisiert",
        "notification_body": "Für diesen Schritt liegen neue Informationen vor. Öffnen Sie Ihr Dashboard für Details.",
    },
    "user_step_completed": {
        "notification_title": "Schritt abgeschlossen",
        "notification_body": "„{{step_title}}“ ist abgeschlossen. Sehen Sie jetzt nach, wie es weitergeht.",
    },
    "user_next_step_unlocked": {
        "notification_title": "Nächster Schritt freigeschaltet",
        "notification_body": "„{{step_title}}“ kann jetzt bearbeitet werden.",
    },
    "user_password_reset": {
        "notification_title": "Passwort-Zurücksetzung angefordert",
        "notification_body": "Für Ihr IHCA-Konto wurde eine Passwort-Zurücksetzung angefordert.",
    },
}

for _template_key, _notification in DEFAULT_NOTIFICATION_CONTENT.items():
    DEFAULT_TEMPLATES[_template_key].update(_notification)
