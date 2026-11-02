"""Germany seed taxonomy for the document matrix (architecture §4).

Codes are language-neutral and never renamed; `de`/`en` are display texts only.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass

TAXONOMY_NAMESPACE = uuid.UUID("44444444-4444-4444-4444-444444444400")


def term_id(code: str) -> uuid.UUID:
    return uuid.uuid5(TAXONOMY_NAMESPACE, code)


@dataclass(frozen=True)
class Term:
    code: str
    name_i18n: dict[str, str]
    description_i18n: dict[str, str]
    icon: str
    sort_order: int

    @property
    def id(self) -> uuid.UUID:
        return term_id(self.code)


def _terms(rows: list[tuple[str, str, str, str, str, str]]) -> tuple[Term, ...]:
    return tuple(
        Term(code, {"de": name_de, "en": name_en}, {"de": desc_de, "en": desc_en}, icon, order)
        for order, (code, name_de, name_en, desc_de, desc_en, icon) in enumerate(rows, start=1)
    )


DOMAINS = _terms(
    [
        (
            "identity-civil-status",
            "Identität & Personenstand",
            "Identity & civil status",
            "Ausweise, Urkunden und Personenstandsnachweise.",
            "ID documents, certificates and civil status records.",
            "id-card",
        ),
        (
            "housing",
            "Wohnen",
            "Housing",
            "Wohnsitz, Miete und Eigentum.",
            "Residence, renting and property.",
            "home",
        ),
        (
            "vehicles-mobility",
            "Fahrzeuge & Mobilität",
            "Vehicles & mobility",
            "Auto, Motorrad, Boot und Führerscheine.",
            "Car, motorbike, boat and licences.",
            "car",
        ),
        (
            "work-employment",
            "Arbeit & Beruf",
            "Work & employment",
            "Arbeitsverhältnis, Arbeitslosigkeit und Berufsnachweise.",
            "Employment, unemployment and professional credentials.",
            "briefcase",
        ),
        (
            "family-children",
            "Familie & Kinder",
            "Family & children",
            "Kinder, Elternschaft und Familienleistungen.",
            "Children, parenthood and family benefits.",
            "users",
        ),
        (
            "education",
            "Bildung",
            "Education",
            "Schule, Ausbildung und Studium.",
            "School, vocational training and university.",
            "graduation-cap",
        ),
        (
            "health-insurance",
            "Gesundheit & Versicherung",
            "Health & insurance",
            "Krankenversicherung, Pflege und Gesundheitsnachweise.",
            "Health insurance, care and medical records.",
            "heart-pulse",
        ),
        (
            "taxes-finance",
            "Steuern & Finanzen",
            "Taxes & finance",
            "Steuererklärung, Steuer-ID und Bankangelegenheiten.",
            "Tax returns, tax ID and banking matters.",
            "landmark",
        ),
        (
            "residence-migration",
            "Aufenthalt & Migration",
            "Residence & migration",
            "Aufenthaltstitel, Visa und Einbürgerung.",
            "Residence permits, visas and naturalisation.",
            "globe",
        ),
        (
            "retirement-old-age",
            "Rente & Alter",
            "Retirement & old age",
            "Rentenanträge und Leistungen im Alter.",
            "Pension applications and old-age benefits.",
            "sunset",
        ),
        (
            "self-employment-business",
            "Selbstständigkeit & Gewerbe",
            "Self-employment & business",
            "Gewerbeanmeldung, Freiberuf und Unternehmensgründung.",
            "Trade registration, freelancing and starting a business.",
            "store",
        ),
        (
            "social-benefits",
            "Soziales & Leistungen",
            "Social benefits",
            "Bürgergeld, Wohngeld und weitere Sozialleistungen.",
            "Citizen's income, housing benefit and other social benefits.",
            "hand-heart",
        ),
        (
            "law-justice",
            "Recht & Justiz",
            "Law & justice",
            "Führungszeugnis, Vollmachten und Gerichtsverfahren.",
            "Certificates of good conduct, powers of attorney and court matters.",
            "scale",
        ),
    ]
)

SITUATIONS = _terms(
    [
        (
            "moving-house",
            "Umzug",
            "Moving house",
            "Ummelden und Wohnsitz wechseln.",
            "Registering a new address.",
            "truck",
        ),
        (
            "birth-of-child",
            "Geburt eines Kindes",
            "Birth of a child",
            "Nachweise und Anträge rund um die Geburt.",
            "Certificates and applications around a birth.",
            "baby",
        ),
        (
            "marriage",
            "Heirat / Lebenspartnerschaft",
            "Marriage / civil partnership",
            "Eheschließung oder Lebenspartnerschaft anmelden.",
            "Registering a marriage or civil partnership.",
            "heart",
        ),
        (
            "separation-divorce",
            "Trennung & Scheidung",
            "Separation & divorce",
            "Trennung, Scheidung und deren Folgen.",
            "Separation, divorce and their consequences.",
            "split",
        ),
        (
            "death-of-relative",
            "Todesfall",
            "Death of a relative",
            "Sterbeurkunde, Erbe und Nachlass.",
            "Death certificate, inheritance and estate.",
            "flower",
        ),
        (
            "job-loss",
            "Jobverlust",
            "Losing a job",
            "Arbeitslosmeldung und Leistungen bei Arbeitslosigkeit.",
            "Registering as unemployed and unemployment benefits.",
            "door-open",
        ),
        (
            "new-job",
            "Berufseinstieg / Jobwechsel",
            "Starting or changing jobs",
            "Nachweise für Berufseinstieg und neue Arbeitgeber.",
            "Paperwork for a first job or a new employer.",
            "briefcase",
        ),
        (
            "going-self-employed",
            "Selbstständig machen",
            "Going self-employed",
            "Gewerbe anmelden und Selbstständigkeit starten.",
            "Registering a business and starting self-employment.",
            "rocket",
        ),
        (
            "studying",
            "Studium",
            "Studying",
            "Einschreibung, BAföG und Studiennachweise.",
            "Enrolment, student finance and study records.",
            "graduation-cap",
        ),
        (
            "starting-school",
            "Einschulung",
            "Starting school",
            "Schulanmeldung und Schuleingangsuntersuchung.",
            "School registration and school entry examination.",
            "backpack",
        ),
        (
            "renting-home",
            "Wohnung mieten",
            "Renting a home",
            "Mietvertrag, Kaution und Vermieterbestätigungen.",
            "Rental contract, deposit and landlord confirmations.",
            "key",
        ),
        (
            "buying-property",
            "Immobilie kaufen / bauen",
            "Buying or building property",
            "Kauf, Baugenehmigung und Grundbuch.",
            "Purchase, building permit and land register.",
            "building",
        ),
        (
            "buying-vehicle",
            "Fahrzeug kaufen / zulassen",
            "Buying and registering a vehicle",
            "Zulassung, Versicherung und Kennzeichen.",
            "Registration, insurance and number plates.",
            "car",
        ),
        (
            "getting-licence",
            "Führerschein / Bootsschein erwerben",
            "Getting a driving or boating licence",
            "Fahrerlaubnis und Sportbootführerschein.",
            "Driving licence and boating licence.",
            "badge-check",
        ),
        (
            "immigration",
            "Zuzug nach Deutschland",
            "Moving to Germany",
            "Anmeldung, Aufenthalt und erste Behördengänge.",
            "Registration, residence and first visits to authorities.",
            "plane-landing",
        ),
        (
            "naturalisation",
            "Einbürgerung",
            "Naturalisation",
            "Antrag auf die deutsche Staatsangehörigkeit.",
            "Applying for German citizenship.",
            "flag",
        ),
        (
            "illness-care",
            "Krankheit / Pflegebedürftigkeit",
            "Illness / care needs",
            "Krankengeld, Pflegegrad und Schwerbehinderung.",
            "Sick pay, care level and disability status.",
            "stethoscope",
        ),
        (
            "retirement",
            "Renteneintritt",
            "Retirement",
            "Rentenantrag und Übergang in den Ruhestand.",
            "Pension application and transition to retirement.",
            "sunset",
        ),
    ]
)

SITUATION_GROUPS = _terms(
    [
        (
            "family-relationships",
            "Familie & Beziehungen",
            "Family & relationships",
            "Heirat, Trennung, Geburt und Todesfall in der Familie.",
            "Marriage, separation, birth and bereavement in the family.",
            "users",
        ),
        (
            "home-housing",
            "Wohnen & Umzug",
            "Home & housing",
            "Umzug, Mietwohnung und Immobilienkauf.",
            "Moving house, renting and buying property.",
            "home",
        ),
        (
            "work-career",
            "Arbeit & Karriere",
            "Work & career",
            "Jobwechsel, Jobverlust und Selbstständigkeit.",
            "Changing jobs, losing a job and going self-employed.",
            "briefcase",
        ),
        (
            "education",
            "Bildung",
            "Education",
            "Studium und Schuleintritt.",
            "Studying and starting school.",
            "graduation-cap",
        ),
        (
            "vehicles-travel",
            "Fahrzeuge & Mobilität",
            "Vehicles & travel",
            "Fahrzeugkauf und Führerschein.",
            "Buying a vehicle and getting a licence.",
            "car",
        ),
        (
            "residence-migration",
            "Aufenthalt & Migration",
            "Residence & migration",
            "Zuzug nach Deutschland und Einbürgerung.",
            "Moving to Germany and naturalisation.",
            "globe",
        ),
        (
            "health-care",
            "Gesundheit & Pflege",
            "Health & care",
            "Krankheit und Pflegebedürftigkeit.",
            "Illness and care needs.",
            "stethoscope",
        ),
        (
            "retirement",
            "Renteneintritt",
            "Retirement",
            "Übergang in den Ruhestand.",
            "Transition into retirement.",
            "sunset",
        ),
    ]
)

# life situation code -> situation-group code (architecture §4); a pure partition of SITUATIONS.
SITUATION_GROUP_CODES: dict[str, str] = {
    "marriage": "family-relationships",
    "separation-divorce": "family-relationships",
    "birth-of-child": "family-relationships",
    "death-of-relative": "family-relationships",
    "moving-house": "home-housing",
    "renting-home": "home-housing",
    "buying-property": "home-housing",
    "new-job": "work-career",
    "job-loss": "work-career",
    "going-self-employed": "work-career",
    "studying": "education",
    "starting-school": "education",
    "buying-vehicle": "vehicles-travel",
    "getting-licence": "vehicles-travel",
    "immigration": "residence-migration",
    "naturalisation": "residence-migration",
    "illness-care": "health-care",
    "retirement": "retirement",
}
