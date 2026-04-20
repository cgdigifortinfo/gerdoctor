import { createContext, useContext, useState, useEffect } from 'react';

const translations = {
  en: {
    // Nav
    nav_home: 'Home', nav_about: 'About Us', nav_partners: 'Partners', nav_login: 'Login',
    // Hero
    hero_overline: 'Your Partner Network',
    hero_title_default: 'Transform Your Business Journey',
    hero_subtitle_default: 'A guided experience to connect you with the right partners and accelerate your growth.',
    hero_cta_default: 'Get Started', hero_learn_more: 'Learn More', hero_stat: 'Successful Partnerships',
    // Features
    feat_onboarding_title: 'Guided Onboarding', feat_onboarding_desc: 'Step-by-step process to complete your profile and find the perfect partner match.',
    feat_network_title: 'Partner Network', feat_network_desc: 'Access our curated network of industry-leading partners across multiple sectors.',
    feat_tracking_title: 'Progress Tracking', feat_tracking_desc: 'Monitor your journey with real-time progress updates and status notifications.',
    // About
    about_overline: 'Who We Are', about_title_default: 'About Us',
    about_desc_default: 'We help businesses connect with the right partners through a streamlined onboarding process.',
    about_mission_default: 'Our mission is to simplify business partnerships and create meaningful connections.',
    // Partners section
    partners_overline: 'Our Network', partners_title_default: 'Our Partners',
    partners_desc_default: 'Work with industry-leading partners to achieve your goals.',
    // CTA
    cta_title: 'Ready to Start Your Journey?', cta_desc: 'Join hundreds of businesses that have found their perfect partners through our platform.', cta_btn: 'Create Your Account',
    // Footer
    footer_copy: '2026 GERdoctor. All rights reserved.',
    // Auth
    auth_welcome_back: 'Welcome back', auth_sign_in_subtitle: 'Sign in to continue your journey',
    auth_email: 'Email', auth_password: 'Password', auth_forgot: 'Forgot password?',
    auth_sign_in: 'Sign In', auth_signing_in: 'Signing in...',
    auth_no_account: "Don't have an account?", auth_create_one: 'Create one',
    auth_create_account: 'Create your account', auth_create_subtitle: 'Start your journey with us today',
    auth_full_name: 'Full Name', auth_confirm_password: 'Confirm Password',
    auth_creating: 'Creating account...', auth_create_btn: 'Create Account',
    auth_have_account: 'Already have an account?', auth_sign_in_link: 'Sign in',
    auth_back_home: 'Back to Home', auth_back_login: 'Back to Login',
    auth_reset_title: 'Reset your password', auth_reset_subtitle: "Enter your email and we'll send you a reset link.",
    auth_send_reset: 'Send Reset Link', auth_check_email: 'Check your email', auth_return_login: 'Return to Login',
    // User Dashboard
    dash_your_progress: 'Your Progress', dash_complete: 'Complete', dash_welcome: 'Welcome',
    dash_save_progress: 'Save Progress', dash_complete_continue: 'Complete & Continue', dash_saving: 'Saving...',
    dash_confirm_selection: 'Confirm Selection & Continue', dash_review_info: 'Review Your Information',
    dash_finalize: 'Finalize Journey', dash_finalizing: 'Finalizing...',
    dash_prev_step: 'Previous Step', dash_completed: 'Completed', dash_in_progress: 'In Progress',
    dash_visit_website: 'Visit Website', dash_selected_partner: 'Selected Partner', dash_select_partner: 'Please select a partner',
    dash_estimated_completion: 'Estimated Completion', dash_history: 'History', dash_no_history: 'No activities yet. Start with the first step!',
    dash_step: 'Step', dash_no_data: 'No data entered', dash_no_partners: 'No partners available',
    dash_select_multiple: 'You can select multiple partners.', dash_partners_selected: 'partners selected',
    dash_skip: 'Skip', dash_next: 'Next', dash_all_done: 'All done!',
    dash_waiting: 'Waiting for completion...', dash_partner_processing: 'This step is being processed by your partner.',
    dash_blocked: 'This step is locked.',
    // Notification prefs
    notif_title: 'Notification Preferences', notif_desc: 'Choose when you receive email notifications about your progress.',
    notif_step_enter: 'Step Entry', notif_step_enter_desc: 'Receive email when starting a new step',
    notif_step_edit: 'Step Edit', notif_step_edit_desc: 'Receive email when saving progress on a step',
    notif_step_leave: 'Step Completion', notif_step_leave_desc: 'Receive email when completing a step',
    notif_save: 'Save Preferences', notif_saved: 'Saved',
    // Admin
    admin_label: 'Admin', admin_dashboard: 'Dashboard', admin_users: 'Users', admin_steps: 'Steps',
    admin_partners: 'Partners', admin_cms: 'CMS', admin_audit: 'Audit Log', admin_settings: 'Settings',
    admin_total_users: 'Total Users', admin_active_partners: 'Active Partners',
    admin_submissions: 'Submissions', admin_new_7days: 'New (7 days)',
    admin_user_dist: 'User Distribution', admin_regular_users: 'Regular Users',
    admin_partner_users: 'Partner Users', admin_admins: 'Admins',
    admin_step_completion: 'Step Completion Rates',
    admin_user_mgmt: 'User Management', admin_search_placeholder: 'Search by name or email...',
    admin_all_roles: 'All Roles', admin_export_csv: 'Export CSV', admin_create_user: 'Create User',
    admin_selected: 'selected', admin_apply_role: 'Apply Role', admin_clear: 'Clear',
    admin_no_users: 'No users found', admin_step_mgmt: 'Step Management', admin_add_step: 'Add Step',
    admin_edit: 'Edit', admin_delete: 'Delete', admin_partner_mgmt: 'Partner Management',
    admin_add_partner: 'Add Partner', admin_link_user: 'Link User', admin_save_changes: 'Save Changes',
    admin_view: 'View', admin_progress: 'Progress', admin_forecast: 'Forecast',
    admin_impersonate: 'Impersonate', admin_stop_impersonate: 'Exit',
    admin_user_detail: 'User Details', admin_site_settings: 'Site Settings',
    admin_logo_config: 'Logo Configuration', admin_logo_bold: 'Bold Part', admin_logo_light: 'Light Part',
    admin_logo_preview: 'Preview', admin_general: 'General', admin_contact_email: 'Contact Email',
    admin_primary_color: 'Primary Color', admin_footer_text: 'Footer Text', admin_meta_desc: 'Meta Description',
    admin_save_settings: 'Save Settings', admin_saving: 'Saving...',
    // Step editor
    step_create: 'Create Step', step_edit: 'Edit Step', step_basic: 'Basic', step_type_settings: 'Type Settings',
    step_fields: 'Fields', step_requirements: 'Requirements', step_mappings: 'Mappings',
    step_conditions: 'Conditions', step_notifications: 'Notifications',
    step_title: 'Title', step_description: 'Description', step_order: 'Order', step_type: 'Type',
    step_active: 'Active', step_skippable: 'Skippable', step_skip_label: 'Skip Label',
    step_duration: 'Step Duration', step_duration_desc: 'How long does this step take? 0 = instant.',
    step_duration_value: 'Value', step_duration_unit: 'Unit',
    step_type_form: 'Form', step_type_partner: 'Partner Selection', step_type_partner_multi: 'Partner Multi-Selection',
    step_type_milestone: 'Milestone', step_type_display: 'Display',
    step_filter_tag: 'Filter Tag', step_pending_msg: 'Pending Message', step_complete_msg: 'Complete Message',
    step_action_label: 'Button Text', step_add_field: 'Add Field', step_form_fields: 'Form Fields',
    step_instant: 'Instant', step_days: 'Days', step_weeks: 'Weeks', step_months: 'Months', step_years: 'Years',
    // Partner editor
    partner_edit: 'Edit Partner', partner_create: 'Add Partner', partner_name: 'Name',
    partner_description: 'Description', partner_logo_url: 'Logo URL', partner_website: 'Website',
    partner_contact_email: 'Contact Email', partner_category: 'Category', partner_tags: 'Tags (comma-separated)',
    partner_linked_users: 'Partner Users (Role "Partner")',
    partner_linked_users_desc: 'Select users who get Partner role and access to the Partner Dashboard.',
    partner_search_users: 'Search users...', partner_no_users: 'No users available', partner_no_results: 'No results',
    // Partner Dashboard
    partner_label: 'Partner', partner_submissions: 'Submissions', partner_profile: 'Profile',
    partner_not_linked: 'Account Not Linked',
    partner_not_linked_desc: 'Your account is not yet linked to a partner organization. Please contact an administrator.',
    partner_my_users: 'My Users', partner_other_users: 'Other Users',
    partner_my_users_desc: 'Users who selected your organization', partner_other_users_desc: 'Users who did not select your organization',
    partner_no_entries: 'No entries found', partner_entries: 'entries',
    partner_filter: 'Filter', partner_filter_fachgebiet: 'Specialty', partner_filter_all: 'All',
    partner_filter_forecast_from: 'Forecast from', partner_filter_forecast_to: 'Forecast to',
    partner_filter_reset: 'Reset', partner_no_access: 'This user has not submitted to your organization. Detailed step data is not available.',
    partner_step_progress: 'Step Progress', partner_complete_step: 'Complete', partner_approve_step: 'Approve', partner_your_step: 'Your Step',
    // Create User Dialog
    create_user_title: 'Create User', create_user_name: 'Name', create_user_email: 'Email',
    create_user_password: 'Password', create_user_role: 'Role', create_user_partner: 'Assign Partner (optional)',
    create_user_no_partner: 'No Partner', create_user_submit: 'Create', create_user_success: 'User created',
    // Common
    loading: 'Loading...', active: 'Active', inactive: 'Inactive', cancel: 'Cancel', save: 'Save',
    name: 'Name', email: 'Email', role: 'Role', status: 'Status', actions: 'Actions', joined: 'Joined',
    user: 'User', admin: 'Admin', partner: 'Partner',
    pending: 'Pending', completed: 'Completed', in_progress: 'In Progress',
    date: 'Date', download: 'Download', details: 'Details', close: 'Close',
  },
  de: {
    // Nav
    nav_home: 'Startseite', nav_about: 'Über uns', nav_partners: 'Partner', nav_login: 'Anmelden',
    // Hero
    hero_overline: 'Ihr Partner-Netzwerk',
    hero_title_default: 'Transformieren Sie Ihre Geschäftsreise',
    hero_subtitle_default: 'Ein geführtes Erlebnis, um Sie mit den richtigen Partnern zu verbinden und Ihr Wachstum zu beschleunigen.',
    hero_cta_default: 'Jetzt starten', hero_learn_more: 'Mehr erfahren', hero_stat: 'Erfolgreiche Partnerschaften',
    // Features
    feat_onboarding_title: 'Geführtes Onboarding', feat_onboarding_desc: 'Schritt-für-Schritt-Prozess, um Ihr Profil zu vervollständigen und den perfekten Partner zu finden.',
    feat_network_title: 'Partner-Netzwerk', feat_network_desc: 'Zugang zu unserem kuratierten Netzwerk branchenführender Partner in verschiedenen Sektoren.',
    feat_tracking_title: 'Fortschrittsverfolgung', feat_tracking_desc: 'Überwachen Sie Ihre Reise mit Echtzeit-Fortschrittsaktualisierungen und Status-Benachrichtigungen.',
    // About
    about_overline: 'Wer wir sind', about_title_default: 'Über uns',
    about_desc_default: 'Wir helfen Unternehmen, sich mit den richtigen Partnern durch einen optimierten Onboarding-Prozess zu verbinden.',
    about_mission_default: 'Unsere Mission ist es, Geschäftspartnerschaften zu vereinfachen und sinnvolle Verbindungen zu schaffen.',
    // Partners section
    partners_overline: 'Unser Netzwerk', partners_title_default: 'Unsere Partner',
    partners_desc_default: 'Arbeiten Sie mit branchenführenden Partnern zusammen, um Ihre Ziele zu erreichen.',
    // CTA
    cta_title: 'Bereit, Ihre Reise zu beginnen?', cta_desc: 'Schließen Sie sich Hunderten von Unternehmen an, die ihre perfekten Partner über unsere Plattform gefunden haben.', cta_btn: 'Konto erstellen',
    // Footer
    footer_copy: '2026 GERdoctor. Alle Rechte vorbehalten.',
    // Auth
    auth_welcome_back: 'Willkommen zurück', auth_sign_in_subtitle: 'Melden Sie sich an, um Ihre Reise fortzusetzen',
    auth_email: 'E-Mail', auth_password: 'Passwort', auth_forgot: 'Passwort vergessen?',
    auth_sign_in: 'Anmelden', auth_signing_in: 'Anmeldung...',
    auth_no_account: 'Noch kein Konto?', auth_create_one: 'Erstellen',
    auth_create_account: 'Konto erstellen', auth_create_subtitle: 'Beginnen Sie noch heute Ihre Reise mit uns',
    auth_full_name: 'Vollständiger Name', auth_confirm_password: 'Passwort bestätigen',
    auth_creating: 'Konto wird erstellt...', auth_create_btn: 'Konto erstellen',
    auth_have_account: 'Bereits ein Konto?', auth_sign_in_link: 'Anmelden',
    auth_back_home: 'Zurück zur Startseite', auth_back_login: 'Zurück zur Anmeldung',
    auth_reset_title: 'Passwort zurücksetzen', auth_reset_subtitle: 'Geben Sie Ihre E-Mail ein und wir senden Ihnen einen Link zum Zurücksetzen.',
    auth_send_reset: 'Link senden', auth_check_email: 'Prüfen Sie Ihre E-Mail', auth_return_login: 'Zurück zur Anmeldung',
    // User Dashboard
    dash_your_progress: 'Ihr Fortschritt', dash_complete: 'Abgeschlossen', dash_welcome: 'Willkommen',
    dash_save_progress: 'Fortschritt speichern', dash_complete_continue: 'Abschließen & Weiter', dash_saving: 'Speichern...',
    dash_confirm_selection: 'Auswahl bestätigen & Weiter', dash_review_info: 'Überprüfen Sie Ihre Informationen',
    dash_finalize: 'Reise abschließen', dash_finalizing: 'Wird abgeschlossen...',
    dash_prev_step: 'Vorheriger Schritt', dash_completed: 'Abgeschlossen', dash_in_progress: 'In Bearbeitung',
    dash_visit_website: 'Website besuchen', dash_selected_partner: 'Ausgewählter Partner', dash_select_partner: 'Bitte wählen Sie einen Partner',
    dash_estimated_completion: 'Voraussichtlicher Abschluss', dash_history: 'Verlauf', dash_no_history: 'Noch keine Aktivitäten vorhanden. Starten Sie mit dem ersten Schritt!',
    dash_step: 'Schritt', dash_no_data: 'Keine Daten eingegeben', dash_no_partners: 'Keine Partner verfügbar',
    dash_select_multiple: 'Sie können mehrere Partner auswählen.', dash_partners_selected: 'Partner ausgewählt',
    dash_skip: 'Überspringen', dash_next: 'Weiter', dash_all_done: 'Alles erledigt!',
    dash_waiting: 'Warten auf Abschluss...', dash_partner_processing: 'Dieser Schritt wird von Ihrem Partner bearbeitet.',
    dash_blocked: 'Dieser Schritt ist gesperrt.',
    // Notification prefs
    notif_title: 'Benachrichtigungseinstellungen', notif_desc: 'Wählen Sie, wann Sie E-Mail-Benachrichtigungen über Ihren Fortschritt erhalten.',
    notif_step_enter: 'Schritt-Eintritt', notif_step_enter_desc: 'E-Mail erhalten, wenn ein neuer Schritt begonnen wird',
    notif_step_edit: 'Schritt-Bearbeitung', notif_step_edit_desc: 'E-Mail erhalten, wenn Fortschritt in einem Schritt gespeichert wird',
    notif_step_leave: 'Schritt-Abschluss', notif_step_leave_desc: 'E-Mail erhalten, wenn ein Schritt abgeschlossen wird',
    notif_save: 'Einstellungen speichern', notif_saved: 'Gespeichert',
    // Admin
    admin_label: 'Admin', admin_dashboard: 'Dashboard', admin_users: 'Benutzer', admin_steps: 'Schritte',
    admin_partners: 'Partner', admin_cms: 'CMS', admin_audit: 'Audit-Protokoll', admin_settings: 'Einstellungen',
    admin_total_users: 'Benutzer gesamt', admin_active_partners: 'Aktive Partner',
    admin_submissions: 'Einreichungen', admin_new_7days: 'Neu (7 Tage)',
    admin_user_dist: 'Benutzerverteilung', admin_regular_users: 'Reguläre Benutzer',
    admin_partner_users: 'Partner-Benutzer', admin_admins: 'Administratoren',
    admin_step_completion: 'Schritt-Abschlussraten',
    admin_user_mgmt: 'Benutzerverwaltung', admin_search_placeholder: 'Nach Name oder E-Mail suchen...',
    admin_all_roles: 'Alle Rollen', admin_export_csv: 'CSV Export', admin_create_user: 'Benutzer anlegen',
    admin_selected: 'ausgewählt', admin_apply_role: 'Rolle anwenden', admin_clear: 'Löschen',
    admin_no_users: 'Keine Benutzer gefunden', admin_step_mgmt: 'Schrittverwaltung', admin_add_step: 'Schritt hinzufügen',
    admin_edit: 'Bearbeiten', admin_delete: 'Löschen', admin_partner_mgmt: 'Partnerverwaltung',
    admin_add_partner: 'Partner hinzufügen', admin_link_user: 'Benutzer verknüpfen', admin_save_changes: 'Änderungen speichern',
    admin_view: 'Ansehen', admin_progress: 'Fortschritt', admin_forecast: 'Prognose',
    admin_impersonate: 'Anmelden als', admin_stop_impersonate: 'Beenden',
    admin_user_detail: 'Benutzerdetails', admin_site_settings: 'Seiteneinstellungen',
    admin_logo_config: 'Logo-Konfiguration', admin_logo_bold: 'Fetter Teil', admin_logo_light: 'Leichter Teil',
    admin_logo_preview: 'Vorschau', admin_general: 'Allgemein', admin_contact_email: 'Kontakt-E-Mail',
    admin_primary_color: 'Primärfarbe', admin_footer_text: 'Fußzeilentext', admin_meta_desc: 'Meta-Beschreibung',
    admin_save_settings: 'Einstellungen speichern', admin_saving: 'Speichern...',
    // Step editor
    step_create: 'Schritt erstellen', step_edit: 'Schritt bearbeiten', step_basic: 'Grunddaten', step_type_settings: 'Typ-Einstellungen',
    step_fields: 'Felder', step_requirements: 'Anforderungen', step_mappings: 'Mappings',
    step_conditions: 'Bedingungen', step_notifications: 'Benachrichtigungen',
    step_title: 'Titel', step_description: 'Beschreibung', step_order: 'Reihenfolge', step_type: 'Typ',
    step_active: 'Aktiv', step_skippable: 'Überspringbar', step_skip_label: 'Überspringen-Text',
    step_duration: 'Dauer dieses Schritts', step_duration_desc: 'Wie lange dauert dieser Schritt? 0 = sofort abschließbar.',
    step_duration_value: 'Wert', step_duration_unit: 'Einheit',
    step_type_form: 'Formular', step_type_partner: 'Partner-Auswahl', step_type_partner_multi: 'Partner-Mehrfachauswahl',
    step_type_milestone: 'Meilenstein', step_type_display: 'Anzeige',
    step_filter_tag: 'Filter-Tag', step_pending_msg: 'Ausstehend-Nachricht', step_complete_msg: 'Abgeschlossen-Nachricht',
    step_action_label: 'Button-Text', step_add_field: 'Feld hinzufügen', step_form_fields: 'Formularfelder',
    step_instant: 'Sofort', step_days: 'Tage', step_weeks: 'Wochen', step_months: 'Monate', step_years: 'Jahre',
    // Partner editor
    partner_edit: 'Partner bearbeiten', partner_create: 'Partner hinzufügen', partner_name: 'Name',
    partner_description: 'Beschreibung', partner_logo_url: 'Logo-URL', partner_website: 'Website',
    partner_contact_email: 'Kontakt-E-Mail', partner_category: 'Kategorie', partner_tags: 'Tags (kommagetrennt)',
    partner_linked_users: 'Partner-Nutzer (Rolle "Partner")',
    partner_linked_users_desc: 'Wählen Sie Nutzer aus, die als Partner-Admins Zugriff auf das Partner-Dashboard erhalten.',
    partner_search_users: 'Nutzer suchen...', partner_no_users: 'Keine Nutzer verfügbar', partner_no_results: 'Keine Treffer',
    // Partner Dashboard
    partner_label: 'Partner', partner_submissions: 'Einreichungen', partner_profile: 'Profil',
    partner_not_linked: 'Konto nicht verknüpft',
    partner_not_linked_desc: 'Ihr Konto ist noch nicht mit einer Partnerorganisation verknüpft. Bitte kontaktieren Sie einen Administrator.',
    partner_my_users: 'Meine Nutzer', partner_other_users: 'Andere Nutzer',
    partner_my_users_desc: 'Nutzer, die Ihre Organisation gewählt haben', partner_other_users_desc: 'Nutzer, die Ihre Organisation nicht gewählt haben',
    partner_no_entries: 'Keine Einträge gefunden', partner_entries: 'Einträge',
    partner_filter: 'Filter', partner_filter_fachgebiet: 'Fachgebiet', partner_filter_all: 'Alle',
    partner_filter_forecast_from: 'Prognose von', partner_filter_forecast_to: 'Prognose bis',
    partner_filter_reset: 'Zurücksetzen', partner_no_access: 'Dieser Nutzer hat noch keinen Antrag bei Ihnen eingereicht. Detaillierte Schrittdaten sind daher nicht verfügbar.',
    partner_step_progress: 'Schrittfortschritt', partner_complete_step: 'Abschliessen', partner_approve_step: 'Freigeben', partner_your_step: 'Ihr Schritt',
    // Create User Dialog
    create_user_title: 'Benutzer anlegen', create_user_name: 'Name', create_user_email: 'E-Mail',
    create_user_password: 'Passwort', create_user_role: 'Rolle', create_user_partner: 'Partner zuweisen (optional)',
    create_user_no_partner: 'Kein Partner', create_user_submit: 'Erstellen', create_user_success: 'Benutzer erstellt',
    // Common
    loading: 'Laden...', active: 'Aktiv', inactive: 'Inaktiv', cancel: 'Abbrechen', save: 'Speichern',
    name: 'Name', email: 'E-Mail', role: 'Rolle', status: 'Status', actions: 'Aktionen', joined: 'Beigetreten',
    user: 'Benutzer', admin: 'Admin', partner: 'Partner',
    pending: 'Ausstehend', completed: 'Abgeschlossen', in_progress: 'In Bearbeitung',
    date: 'Datum', download: 'Herunterladen', details: 'Details', close: 'Schließen',
  }
};

const LanguageContext = createContext(null);

export function LanguageProvider({ children }) {
  const [lang, setLang] = useState(() => localStorage.getItem('gj_lang') || 'en');

  useEffect(() => {
    localStorage.setItem('gj_lang', lang);
    document.documentElement.lang = lang;
  }, [lang]);

  const t = (key) => translations[lang]?.[key] || translations.en[key] || key;

  // Localize DB content: localize(item, 'title') -> returns translated title or fallback to default
  const localize = (item, field) => {
    if (!item) return '';
    if (lang !== 'de' && item.translations?.[lang]?.[field]) {
      return item.translations[lang][field];
    }
    return item[field] || '';
  };

  // Localize CMS: localizeCms(cmsContent, 'hero_title', translations) 
  const localizeCms = (content, field, cmsTrans) => {
    if (!content) return '';
    if (lang !== 'de' && cmsTrans?.[lang]?.[field]) {
      return cmsTrans[lang][field];
    }
    return content[field] || '';
  };

  const toggleLang = () => setLang(prev => prev === 'en' ? 'de' : 'en');

  return (
    <LanguageContext.Provider value={{ lang, setLang, t, toggleLang, localize, localizeCms }}>
      {children}
    </LanguageContext.Provider>
  );
}

export function useLanguage() {
  const ctx = useContext(LanguageContext);
  if (!ctx) throw new Error('useLanguage must be used within LanguageProvider');
  return ctx;
}
