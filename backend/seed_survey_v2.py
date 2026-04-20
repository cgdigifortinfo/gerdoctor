"""
Seed Survey v2 - Full restructure of the onboarding flow.

Creates 24 steps covering:
  1.  Stammdaten (base profile incl. birthdate + 4 new selects)
  2-5.  Antragstellung Approbation (decision -> upload | partner_selection -> milestone)
  6-9.  Fachsprachenpruefung
  10-13. Gleichwertigkeitspruefung
  14-17. Kenntnispruefung
  18-20. Jobangebote (decision -> partner_multiselection | -> milestone)
  21-24. Weiterbildung

Condition actions used:
  - hide:          step completely hidden from user + excluded from progress/ETA
  - block:         step locked (e.g. subsequent theme blocks require Antragstellung Approbation milestone=completed)
  - auto_complete: step auto-marks itself completed based on previous decision (upload path -> milestone done)

Run with: cd /app/backend && python seed_survey_v2.py
"""
import asyncio
import os
from datetime import datetime, timezone
from motor.motor_asyncio import AsyncIOMotorClient
from bson import ObjectId


LOGO = "https://static.prod-images.emergentagent.com/jobs/315e3c10-27eb-4e13-8f67-587e823053ba/images/6cecee740efb45c2d26aff2bfd6a5b584d1ce68a3f00e1ba82f41fa1f355c8b3.png"


def now_iso():
    return datetime.now(timezone.utc).isoformat()


# ---------- Field option catalogs ----------
ANERKENNUNGSSTATUS = [
    "Die Fachsprachenprüfung Medizin ist geplant",
    "Ich habe die Fachsprachenprüfung Medizin bestanden",
    "Ich habe die Berufserlaubnis beantragt",
    "Die Berufserlaubnis wurde mir erteilt",
    "Ich habe einen Termin zur Kenntnisprüfung (beantragt)",
    "Ich habe die Gleichwertigkeitsprüfung beantragt",
    "Ich bin in Deutschland approbiert",
]
BUNDESLAENDER = [
    "Baden-Württemberg", "Bayern", "Berlin", "Brandenburg", "Bremen",
    "Hamburg", "Hessen", "Mecklenburg-Vorpommern", "Niedersachsen",
    "Nordrhein-Westfalen", "Rheinland-Pfalz", "Saarland", "Sachsen",
    "Sachsen-Anhalt", "Schleswig-Holstein", "Thüringen",
]
FACHRICHTUNGEN = [
    "Allgemeinmedizin", "Anästhesie", "Arbeits- und Betriebsmedizin",
    "Augenheilkunde", "Chirurgie", "Dermatologie", "Endokrinologie",
    "Gastroenterologie", "Gynäkologie", "HNO", "Innere Medizin",
    "Kardiologie", "Kinder- und Jugendpsychiatrie", "Nephrologie",
    "Neurologie", "Onkologie", "Orthopädische Unfallchirurgie", "Pädiatrie",
    "Physikalische und Rehabilitative Medizin", "Pneumologie", "Psychiatrie",
    "Radiologie", "Thoraxchirurgie", "Urologie",
    "Allgemein- und Familienmedizin", "Ästhetische Medizin", "Flexibel",
    "Intensivmedizin", "Anästhesiologie", "Geriatrie", "Notfallmedizin",
    "Plastische Chirurgie", "Zahnmedizin", "Neurochirurgie", "Palliativmedizin",
]
DOC_TYPES = [
    "Approbationsurkunde", "Diplom", "Studiennachweis", "Identitätsnachweis",
    "Lebenslauf", "Sprachnachweis B2/C1", "Fachsprachenzertifikat",
    "Gleichwertigkeitsbescheid", "Kenntnisprüfungsbescheinigung",
    "Weiterbildungsnachweis", "Sonstiges",
]


# ---------- Helpers to build step templates ----------
def decision_step(order, title, description, outcome_upload=True, outcome_partner=True,
                  button_upload_label="Ja, ich möchte meine Dokumente hochladen",
                  button_partner_label="Nein, ich suche einen Partner der mir hilft",
                  block_cond=None, translations=None):
    """Generic decision step with 2 buttons (upload vs partner).

    If outcome_upload=False / outcome_partner=False one of the buttons is hidden.
    For Jobangebote we override labels (see build_block)."""
    options = []
    if outcome_upload:
        options.append({"value": "upload", "label": button_upload_label})
    if outcome_partner:
        options.append({"value": "partner", "label": button_partner_label})
    step = {
        "title": title, "description": description, "order": order,
        "step_type": "decision",
        "fields": [{"name": "decision", "field_type": "decision", "label": title,
                    "options": options}],
        "required_fields": ["decision"],
        "conditions": block_cond or [],
        "duration_value": 0, "duration_unit": "days",
        "is_active": True, "created_at": now_iso(),
    }
    if translations:
        step["translations"] = translations
    return step


def upload_step(order, title, description, decision_order, translations=None):
    """Upload step, visible only when the decision step at `decision_order` == 'upload'."""
    return {
        "title": title, "description": description, "order": order,
        "step_type": "form",
        "fields": [{"name": "documents", "field_type": "multiupload",
                    "label": "Dokumente", "options": DOC_TYPES, "required": True}],
        "required_uploads": [],
        "conditions": [{
            "action": "hide", "source_step_order": decision_order,
            "field": "decision", "operator": "not_equals", "value": "upload",
        }],
        "duration_value": 0, "duration_unit": "days",
        "is_active": True, "created_at": now_iso(),
        **({"translations": translations} if translations else {}),
    }


def partner_step(order, title, description, decision_order, filter_tag,
                 multi=False, translations=None):
    """Partner selection, visible only when decision_order.decision == 'partner' (or 'selbst' for Jobangebote)."""
    trigger_value = "partner" if not multi else "selbst"
    step_type = "partner_multiselection" if multi else "partner_selection"
    return {
        "title": title, "description": description, "order": order,
        "step_type": step_type, "filter_tag": filter_tag,
        "fields": [],
        "conditions": [{
            "action": "hide", "source_step_order": decision_order,
            "field": "decision", "operator": "not_equals", "value": trigger_value,
        }],
        "duration_value": 0, "duration_unit": "days",
        "is_active": True, "created_at": now_iso(),
        **({"translations": translations} if translations else {}),
    }


def milestone_step(order, title, description, decision_order, dur_value, dur_unit,
                   upload_order=None, translations=None,
                   pending_msg=None, complete_msg=None):
    """Milestone; auto-completes when the upload-step was really completed by the user.

    If upload_order is provided → condition: upload-step status == completed
    (meaning: user chose upload AND actually finished uploading the documents).
    If upload_order is None (Jobangebote case) → condition: decision-step data.decision == 'selbst'
    (user decided to search themselves — no upload needed)."""
    if upload_order is not None:
        conditions = [{
            "action": "auto_complete", "source_step_order": upload_order,
            "field": "", "operator": "status_is", "value": "completed",
        }]
    else:
        conditions = [{
            "action": "auto_complete", "source_step_order": decision_order,
            "field": "decision", "operator": "equals", "value": "selbst",
        }]
    return {
        "title": title, "description": description, "order": order,
        "step_type": "milestone", "fields": [],
        "conditions": conditions,
        "duration_value": dur_value, "duration_unit": dur_unit,
        "email_on_leave": True, "is_active": True, "created_at": now_iso(),
        "pending_message": pending_msg or "Dieser Schritt wird von Ihrem Partner bearbeitet.",
        "complete_message": complete_msg or "Abgeschlossen!",
        **({"translations": translations} if translations else {}),
    }


def build_block(base_order, block_name, filter_tag, dur_value, dur_unit,
                include_upload=True, include_partner=True, partner_multi=False,
                partner_trigger_value="partner",
                decision_description=None,
                block_prev_milestone_order=None):
    """Build a 4-step block (decision, upload, partner, milestone).

    - include_upload=False removes the upload step (e.g. Jobangebote)
    - block_prev_milestone_order: if set, adds block condition on the decision step
      so user can only open it once that milestone is completed.
    """
    steps = []
    decision_order = base_order

    block_cond = []
    if block_prev_milestone_order is not None:
        block_cond.append({
            "action": "block", "source_step_order": block_prev_milestone_order,
            "field": "", "operator": "status_not", "value": "completed",
            "message": "Bitte schließen Sie zuerst die Antragstellung Approbation ab.",
        })

    # Decision step
    if partner_multi:
        # Jobangebote: different labels
        steps.append(decision_step(
            decision_order,
            title=block_name,
            description=decision_description or f"{block_name}: Möchten Sie selbst suchen oder einen Partner nutzen?",
            outcome_upload=False, outcome_partner=False,
            block_cond=block_cond,
        ))
        # override fields with custom buttons (selbst / partner_nutzen)
        steps[-1]["fields"] = [{"name": "decision", "field_type": "decision",
                                 "label": block_name,
                                 "options": [
                                     {"value": "selbst", "label": "Ich möchte selbst suchen"},
                                     {"value": "partner_nutzen", "label": "Ich möchte einen Partner nutzen"},
                                 ]}]
    else:
        steps.append(decision_step(
            decision_order,
            title=block_name,
            description=decision_description or f"Hast du bereits eine {block_name} oder bist du schon im Antragsverfahren?",
            block_cond=block_cond,
        ))

    next_order = base_order + 1

    if include_upload and not partner_multi:
        steps.append(upload_step(next_order, f"Dokumente {block_name}",
                                  f"Laden Sie Ihre Dokumente für die {block_name} hoch.",
                                  decision_order=decision_order))
        next_order += 1

    if include_partner:
        steps.append(partner_step(next_order,
                                   f"Service {block_name}" if not partner_multi else f"Partner {block_name}",
                                   f"Wählen Sie Ihre(n) Partner für die {block_name}.",
                                   decision_order=decision_order,
                                   filter_tag=filter_tag, multi=partner_multi))
        next_order += 1

    # Milestone
    milestone_order = next_order
    if partner_multi:
        # Jobangebote – no upload, auto_complete when decision=='selbst'
        steps.append(milestone_step(milestone_order, f"Übersicht {block_name}",
                                     f"Übersicht und Status Ihrer {block_name}.",
                                     decision_order=decision_order,
                                     dur_value=dur_value, dur_unit=dur_unit,
                                     upload_order=None))
    else:
        upload_order = decision_order + 1 if include_upload else None
        steps.append(milestone_step(milestone_order, f"Übersicht {block_name}",
                                     f"Übersicht und Status Ihrer {block_name}.",
                                     decision_order=decision_order,
                                     dur_value=dur_value, dur_unit=dur_unit,
                                     upload_order=upload_order))
    return steps


def build_all_steps():
    """Build the complete list of 24 steps."""
    all_steps = []

    # Step 1: Stammdaten
    all_steps.append({
        "title": "Persönliche Daten",
        "description": "Füllen Sie Ihre persönlichen Informationen aus.",
        "order": 1, "step_type": "form",
        "fields": [
            {"name": "first_name", "field_type": "text", "label": "Vorname",
             "placeholder": "Ihr Vorname", "required": True},
            {"name": "name", "field_type": "text", "label": "Nachname",
             "placeholder": "Ihr Nachname", "required": True},
            {"name": "date_of_birth", "field_type": "date", "label": "Geburtsdatum",
             "required": True},
            {"name": "phone", "field_type": "phone", "label": "Telefon",
             "placeholder": "+49 (0) 123 456 789", "required": True},
            {"name": "address", "field_type": "text", "label": "Adresse",
             "placeholder": "Straße und Hausnummer", "required": True},
            {"name": "anerkennungsstatus", "field_type": "selectbox",
             "label": "Anerkennungsstatus", "options": ANERKENNUNGSSTATUS, "required": True},
            {"name": "anerkennungsverfahren_bundesland", "field_type": "selectbox",
             "label": "Anerkennungsverfahren im Bundesland",
             "options": BUNDESLAENDER, "required": True},
            {"name": "fachrichtung_praktiziert", "field_type": "selectbox",
             "label": "Fachrichtung (bereits praktiziert)",
             "options": FACHRICHTUNGEN, "required": True},
            {"name": "fachrichtung_gewuenscht", "field_type": "selectbox",
             "label": "Fachrichtung (gewünscht)",
             "options": FACHRICHTUNGEN, "required": True},
            # keep legacy field_of_study for partner dashboards
            {"name": "field_of_study", "field_type": "selectbox",
             "label": "Fachgebiet (Übersicht)",
             "options": FACHRICHTUNGEN, "required": False},
        ],
        "required_fields": ["first_name", "name", "date_of_birth", "phone", "address",
                             "anerkennungsstatus", "anerkennungsverfahren_bundesland",
                             "fachrichtung_praktiziert", "fachrichtung_gewuenscht"],
        "field_mappings": [
            # map "fachrichtung_praktiziert" into "field_of_study" for partner visibility
            {"source_step_order": 1, "source_field": "fachrichtung_praktiziert",
             "target_field": "field_of_study"}
        ],
        "duration_value": 0, "duration_unit": "days",
        "is_active": True, "created_at": now_iso(),
    })

    # Block 1: Antragstellung Approbation (steps 2-5)
    all_steps.extend(build_block(
        base_order=2, block_name="Antragstellung Approbation",
        filter_tag="Antragstellung Approbation",
        dur_value=4, dur_unit="weeks",
    ))
    # Gate subsequent blocks on the Antragstellung milestone = order 5
    approbation_milestone_order = 5

    # Block 2: Fachsprachenprüfung (steps 6-9)
    all_steps.extend(build_block(
        base_order=6, block_name="Fachsprachenprüfung",
        filter_tag="Fachsprachenprüfung", dur_value=2, dur_unit="months",
        block_prev_milestone_order=approbation_milestone_order,
    ))

    # Block 3: Gleichwertigkeitsprüfung (steps 10-13)
    all_steps.extend(build_block(
        base_order=10, block_name="Gleichwertigkeitsprüfung",
        filter_tag="Gleichwertigkeitsprüfung", dur_value=3, dur_unit="months",
        block_prev_milestone_order=approbation_milestone_order,
    ))

    # Block 4: Kenntnisprüfung (steps 14-17)
    all_steps.extend(build_block(
        base_order=14, block_name="Kenntnisprüfung",
        filter_tag="Kenntnisprüfung", dur_value=3, dur_unit="months",
        block_prev_milestone_order=approbation_milestone_order,
    ))

    # Block 5: Jobangebote (steps 18-20) - no upload, multi partner
    all_steps.extend(build_block(
        base_order=18, block_name="Jobangebote",
        filter_tag="Jobangebote", dur_value=4, dur_unit="weeks",
        include_upload=False, partner_multi=True,
        decision_description="Möchten Sie selbst nach Jobangeboten suchen oder einen Partner damit beauftragen?",
        block_prev_milestone_order=approbation_milestone_order,
    ))

    # Block 6: Weiterbildung (steps 21-24)
    all_steps.extend(build_block(
        base_order=21, block_name="Weiterbildung",
        filter_tag="Weiterbildung", dur_value=6, dur_unit="months",
        block_prev_milestone_order=approbation_milestone_order,
    ))

    return all_steps


async def seed_partners(db):
    """Ensure partners exist for each filter_tag used above."""
    needed = [
        # (name, tag, description)
        ("FIA Academy", "Fachsprachenprüfung",
         "FIA Academy - Vorbereitung Fachsprachenprüfung Medizin"),
        ("FaMed", "Fachsprachenprüfung",
         "FaMed - Fachsprachenprüfung Medizin"),
        ("IQB Prüfungszentrum", "Gleichwertigkeitsprüfung",
         "IQB - Prüfungen und Vorbereitung Gleichwertigkeitsprüfung"),
        ("MedAkademie Berlin", "Gleichwertigkeitsprüfung",
         "MedAkademie Berlin - Intensiv-Vorbereitung"),
        ("ILS2", "Kenntnisprüfung",
         "ILS - Vorbereitung Kenntnisprüfung"),
        ("HC&S", "Kenntnisprüfung",
         "HC&S - Kenntnisprüfung Coaching"),
        ("ILS3", "Weiterbildung",
         "ILS - Weiterbildung Medizin"),
        ("Lingoda", "Weiterbildung",
         "Lingoda - Sprach- und Weiterbildung"),
        ("InterPers Jobs", "Jobangebote",
         "InterPers Personalvermittlung für Ärzte"),
        ("MedJob24", "Jobangebote",
         "MedJob24 - Jobvermittlung Medizin"),
        ("PraxisConnect Jobs", "Jobangebote",
         "PraxisConnect - direkter Draht zu Praxen"),
        ("ILS", "Antragstellung Approbation",
         "ILS - Antragstellung & Approbationsverfahren"),
        ("digiFORT Experts", "Antragstellung Approbation",
         "digiFORT Experts - Approbation-Antrag digital"),
        ("HABS e.V.", "Antragstellung Approbation",
         "HABS e.V. - Hilfsverein Approbation & Berufsstart"),
    ]
    for (name, tag, desc) in needed:
        # find existing partner by name
        existing = await db.partners.find_one({"name": name})
        if existing:
            tags = set(existing.get("tags") or [])
            tags.add(tag)
            await db.partners.update_one(
                {"_id": existing["_id"]},
                {"$set": {"tags": list(tags),
                           "is_active": True}},
            )
            print(f"  • Partner '{name}' - tags ergänzt: {tag}")
        else:
            await db.partners.insert_one({
                "name": name, "description": desc,
                "category": tag, "tags": [tag],
                "logo_url": LOGO, "is_active": True,
                "created_at": now_iso(),
            })
            print(f"  ✓ Partner '{name}' angelegt (tag: {tag})")


async def create_progress_for_users(db, step_docs):
    """Delete all progress + partner_submissions, then create fresh pending progress entries for every user."""
    users = await db.users.find({"role": "user"}).to_list(1000)
    await db.user_progress.delete_many({})
    await db.progress_history.delete_many({})
    await db.partner_submissions.delete_many({})
    print(f"  • Cleared progress for all users ({len(users)} users)")
    for u in users:
        uid = str(u["_id"])
        docs = []
        for s in step_docs:
            docs.append({
                "user_id": uid, "step_id": str(s["_id"]),
                "status": "pending", "data": {}, "created_at": now_iso(),
            })
        if docs:
            await db.user_progress.insert_many(docs)
    print(f"  ✓ Fresh pending progress records created for {len(users)} users")


async def seed_demo_data(db, step_docs_by_order):
    """Create plausible demo data so Admin/Partner dashboards look alive."""
    # helper to set progress with data
    async def set_prog(user_id, order, status, data=None):
        step = step_docs_by_order.get(order)
        if not step:
            return
        now = now_iso()
        fields = {"status": status, "data": data or {}, "updated_at": now,
                   "started_at": now}
        if status == "completed":
            fields["completed_at"] = now
        await db.user_progress.update_one(
            {"user_id": user_id, "step_id": str(step["_id"])},
            {"$set": fields}, upsert=True,
        )

    demos = [
        ("dr.schmidt@gerdoctor.de", {
            "stammdaten": {"first_name": "Jan", "name": "Schmidt",
                            "date_of_birth": "1988-04-12", "phone": "+49 170 1234567",
                            "address": "Hauptstraße 10, Berlin",
                            "anerkennungsstatus": "Ich habe die Berufserlaubnis beantragt",
                            "anerkennungsverfahren_bundesland": "Berlin",
                            "fachrichtung_praktiziert": "Innere Medizin",
                            "fachrichtung_gewuenscht": "Kardiologie",
                            "field_of_study": "Innere Medizin"},
            "decisions": {2: "upload", 6: "partner"},
            "completed_up_to_order": 9,  # through Fachsprachen partner done + milestone auto-waiting
        }),
        ("dr.yilmaz@gerdoctor.de", {
            "stammdaten": {"first_name": "Elif", "name": "Yılmaz",
                            "date_of_birth": "1990-09-01", "phone": "+49 171 2345678",
                            "address": "Bahnhofstr. 5, München",
                            "anerkennungsstatus": "Die Fachsprachenprüfung Medizin ist geplant",
                            "anerkennungsverfahren_bundesland": "Bayern",
                            "fachrichtung_praktiziert": "Pädiatrie",
                            "fachrichtung_gewuenscht": "Pädiatrie",
                            "field_of_study": "Pädiatrie"},
            "decisions": {2: "partner"},
            "completed_up_to_order": 5,
        }),
        ("dr.chen@gerdoctor.de", {
            "stammdaten": {"first_name": "Wei", "name": "Chen",
                            "date_of_birth": "1985-11-22", "phone": "+49 172 3456789",
                            "address": "Marktplatz 3, Hamburg",
                            "anerkennungsstatus": "Ich habe die Gleichwertigkeitsprüfung beantragt",
                            "anerkennungsverfahren_bundesland": "Hamburg",
                            "fachrichtung_praktiziert": "Chirurgie",
                            "fachrichtung_gewuenscht": "Plastische Chirurgie",
                            "field_of_study": "Chirurgie"},
            "decisions": {2: "upload", 6: "upload", 10: "partner"},
            "completed_up_to_order": 13,
        }),
        ("dr.kumar@gerdoctor.de", {
            "stammdaten": {"first_name": "Rajesh", "name": "Kumar",
                            "date_of_birth": "1992-01-15", "phone": "+49 173 4567890",
                            "address": "Goethestr. 7, Frankfurt",
                            "anerkennungsstatus": "Die Fachsprachenprüfung Medizin ist geplant",
                            "anerkennungsverfahren_bundesland": "Hessen",
                            "fachrichtung_praktiziert": "Allgemeinmedizin",
                            "fachrichtung_gewuenscht": "Allgemeinmedizin",
                            "field_of_study": "Allgemeinmedizin"},
            "decisions": {},
            "completed_up_to_order": 1,
        }),
        ("dr.silva@gerdoctor.de", {
            "stammdaten": {"first_name": "Maria", "name": "Silva",
                            "date_of_birth": "1987-06-30", "phone": "+49 174 5678901",
                            "address": "Rheinstr. 11, Köln",
                            "anerkennungsstatus": "Die Berufserlaubnis wurde mir erteilt",
                            "anerkennungsverfahren_bundesland": "Nordrhein-Westfalen",
                            "fachrichtung_praktiziert": "Dermatologie",
                            "fachrichtung_gewuenscht": "Ästhetische Medizin",
                            "field_of_study": "Dermatologie"},
            "decisions": {2: "partner", 6: "partner"},
            "completed_up_to_order": 8,
        }),
    ]

    for email, plan in demos:
        user = await db.users.find_one({"email": email})
        if not user:
            print(f"  • Demo user {email} not found, skipping")
            continue
        uid = str(user["_id"])

        # Stammdaten
        await set_prog(uid, 1, "completed", plan["stammdaten"])

        # complete blocks up to completed_up_to_order
        upto = plan["completed_up_to_order"]
        decisions = plan["decisions"]

        # iterate orders and complete based on block structure
        for order in range(2, upto + 1):
            step = step_docs_by_order.get(order)
            if not step:
                continue
            if step["step_type"] == "decision":
                # user has made a decision for this block
                dec = decisions.get(order)
                if dec:
                    await set_prog(uid, order, "completed", {"decision": dec})
            elif step["step_type"] == "form":
                # upload step - only reachable if the decision was "upload"
                # find decision step (most recent decision step before this)
                await set_prog(uid, order, "completed", {
                    "documents": [
                        {"file_id": "demo-file", "document_type": "Diplom", "filename": "diplom.pdf"},
                        {"file_id": "demo-file-2", "document_type": "Lebenslauf", "filename": "cv.pdf"},
                    ]
                })
            elif step["step_type"] in ("partner_selection", "partner_multiselection"):
                await set_prog(uid, order, "completed", {
                    "selected_partner_name": "Demo Partner",
                })
            elif step["step_type"] == "milestone":
                await set_prog(uid, order, "completed")

    print(f"  ✓ Demo progress created for {len(demos)} demo users")


async def run():
    client = AsyncIOMotorClient(os.environ.get("MONGO_URL", "mongodb://localhost:27017"))
    db = client[os.environ.get("DB_NAME", "test_database")]

    print("=== WIPING EXISTING STEPS ===")
    r = await db.steps.delete_many({})
    print(f"  • Deleted {r.deleted_count} existing steps")

    print("\n=== INSERTING NEW STEPS ===")
    steps = build_all_steps()
    result = await db.steps.insert_many(steps)
    print(f"  ✓ Inserted {len(result.inserted_ids)} new steps")

    # Load them back with ObjectIds
    step_docs = await db.steps.find({}).sort("order", 1).to_list(200)
    step_docs_by_order = {s["order"]: s for s in step_docs}

    print("\n=== SEEDING PARTNERS ===")
    await seed_partners(db)

    print("\n=== RESETTING USER PROGRESS ===")
    await create_progress_for_users(db, step_docs)

    print("\n=== SEEDING DEMO DATA ===")
    await seed_demo_data(db, step_docs_by_order)

    print("\n=== FINAL STEP LIST ===")
    for s in step_docs:
        flags = []
        conds = s.get("conditions") or []
        for c in conds:
            flags.append(f"{c.get('action')}({c.get('source_step_order')})")
        flag_str = f" [{', '.join(flags)}]" if flags else ""
        print(f"  {s['order']:2d}. {s['title']:45s} | type={s.get('step_type',''):22s} | tag={s.get('filter_tag',''):30s}{flag_str}")

    client.close()
    print("\n✓ Done.")


if __name__ == "__main__":
    asyncio.run(run())
