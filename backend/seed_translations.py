"""Seed English translations for all steps and CMS sections."""
import asyncio, os
from motor.motor_asyncio import AsyncIOMotorClient

STEP_TRANSLATIONS = {
    "Persönliche Daten": {
        "en": {"title": "Personal Information", "description": "Fill in your personal information"}
    },
    "Antragstellung Approbation": {
        "en": {"title": "Application for Medical License", "description": "Choose a partner for your license application"}
    },
    "Uebersicht Antragstellung Approbation": {
        "en": {"title": "Application Overview", "description": "Status of your license application"}
    },
    "FaMed": {
        "en": {"title": "FaMed - Medical Language Exam", "description": "Information about the Medical Language Exam (FaMed). More details at: https://famed-test.de/"}
    },
    "Gleichwertigkeitspruefung": {
        "en": {"title": "Equivalence Assessment", "description": "Choose a partner for your equivalence assessment"}
    },
    "Uebersicht Gleichwertigkeitspruefung": {
        "en": {"title": "Equivalence Assessment Overview", "description": "Overview and status of your equivalence assessment"}
    },
    "Service Kenntnisprüfung": {
        "en": {"title": "Knowledge Examination Service", "description": "Choose a partner for your knowledge examination"}
    },
    "Meilenstein Kenntnisprüfung": {
        "en": {"title": "Knowledge Examination Milestone", "description": "Status of your knowledge examination"}
    },
    "Service Weiterbildung": {
        "en": {"title": "Continuing Education Service", "description": "Choose a partner for your continuing education"}
    },
    "Meilenstein Job finden": {
        "en": {"title": "Job Search Milestone", "description": "We can help you find a position!"}
    },
    "Jobangebote": {
        "en": {"title": "Job Offers", "description": "Browse and select from available positions"}
    },
    "Du hast dich nun beworben!": {
        "en": {"title": "Application Submitted!", "description": "Congratulations! You have successfully applied."}
    },
}

CMS_TRANSLATIONS = {
    "home": {
        "en": {
            "hero_title": "IHCA - Your Personal Path to Becoming a Medical Specialist in Germany",
            "hero_subtitle": "From preparation to starting your career, we provide comprehensive support",
            "hero_cta": "Get Started"
        }
    },
    "about": {
        "en": {
            "title": "About Us",
            "description": "Get your license to practice medicine in Germany.",
            "mission": "The easy way to your German medical license"
        }
    },
    "partners": {
        "en": {
            "title": "Our Partners Support You",
            "description": "Work with industry-leading partners to achieve your goals."
        }
    }
}

async def run():
    client = AsyncIOMotorClient(os.environ.get("MONGO_URL", "mongodb://localhost:27017"))
    db = client[os.environ.get("DB_NAME", "test_database")]

    print("=== SEEDING STEP TRANSLATIONS ===")
    steps = await db.steps.find({"is_active": True}).to_list(100)
    for s in steps:
        title = s["title"]
        if title in STEP_TRANSLATIONS:
            existing_trans = s.get("translations", {})
            merged = {**existing_trans, **STEP_TRANSLATIONS[title]}
            await db.steps.update_one({"_id": s["_id"]}, {"$set": {"translations": merged}})
            print(f'  {title} -> EN: {merged["en"]["title"]}')
        else:
            print(f'  {title} -> NO TRANSLATION DEFINED')

    print("\n=== SEEDING CMS TRANSLATIONS ===")
    for section, trans in CMS_TRANSLATIONS.items():
        cms = await db.cms_content.find_one({"section": section})
        if cms:
            existing_trans = cms.get("translations", {})
            merged = {**existing_trans, **trans}
            await db.cms_content.update_one({"_id": cms["_id"]}, {"$set": {"translations": merged}})
            print(f'  {section} -> EN added')
        else:
            print(f'  {section} -> NOT FOUND')

    # Also add field label translations for Step 1
    step1 = await db.steps.find_one({"order": 1, "is_active": True})
    if step1:
        fields = step1.get("fields", [])
        field_trans = {
            "name": "Last Name", "first_name": "First Name", "phone": "Phone",
            "address": "Address", "field_of_study": "Specialty", "documents": "Documents"
        }
        trans = step1.get("translations", {})
        trans.setdefault("en", {})
        trans["en"]["field_labels"] = field_trans
        await db.steps.update_one({"_id": step1["_id"]}, {"$set": {"translations": trans}})
        print("  Step 1 field labels translated")

    client.close()
    print("\nDone!")

asyncio.run(run())
