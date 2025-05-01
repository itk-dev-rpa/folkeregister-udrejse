"""This module is responsible for interaction with KMD Nova."""

import uuid
from datetime import datetime, timedelta

from itk_dev_shared_components.kmd_nova import nova_cases, nova_tasks, nova_notes
from itk_dev_shared_components.kmd_nova.authentication import NovaAccess
from itk_dev_shared_components.kmd_nova.nova_objects import NovaCase, CaseParty, Caseworker, Department, Task
from itk_dev_shared_components.kmd_nova import cpr as nova_cpr

from robot_framework import config
from robot_framework.sub_process.database import Person
from robot_framework.sub_process import skat_webservice


def add_case(candidate: Person, nova_access: NovaAccess):
    """Add a case and a task to KMD Nova on the given person.

    Args:
        candidate: The person to add the case to.
        nova_access: The NovaAccess object used to authenticate.
    """
    party = CaseParty(
        role="Primær",
        identification_type="CprNummer",
        identification=candidate.cpr,
        name=nova_cpr.get_address_by_cpr(candidate.cpr, nova_access)['name']
    )

    caseworker = Caseworker(
        name='Rpabruger Rpa16 - MÅ IKKE SLETTES',
        ident='AZRPA16',
        uuid='02b35232-9fc4-4e95-aab7-fa9d0e1910cc'
    )

    department = Department(
        id=70403,
        name="Folkeregister og Sygesikring",
        user_key="4BFOLKEREG"
    )

    security_unit = Department(
        id=818485,
        name="Borgerservice",
        user_key="4BBORGER"
    )

    case_uuid = str(uuid.uuid4())

    today = datetime.today()
    end_month, end_year = skat_webservice.subtract_months(today.month, today.year, 1)
    start_month, start_year = skat_webservice.subtract_months(today.month, today.year, config.INCOME_MONTHS)

    description = "\n".join([
        f'Ingen indkomst i perioden: {start_month:02}/{start_year} - {end_month:02}/{end_year}',
        f"Adresse: {candidate.address}",
        f"Antal bebore på adressen: {candidate.address_count}"
    ])

    case = NovaCase(
        uuid=case_uuid,
        title="Udrejsekontrol",
        case_date=datetime.now(),
        progress_state="Opstaaet",
        case_parties=[party],
        kle_number="23.05.00",
        proceeding_facet="G01",
        sensitivity="Fortrolige",
        caseworker=caseworker,
        responsible_department=department,
        security_unit=security_unit,
    )

    task = Task(
        uuid=str(uuid.uuid4()),
        title="Udrejsekontrol",
        description=description,
        caseworker=caseworker,
        status_code="N",
        deadline=None
    )

    nova_cases.add_case(case, nova_access)
    nova_tasks.attach_task_to_case(case.uuid, task, nova_access)

    # Add journal note to case
    note_text = "\n".join([
        "Sagen er automatisk oprettet af Udrejserobotten, da borgeren opfyldte følgende kriterier:",
        "Seneste indrejsedato er mere end 18 måneder siden.",
        f"Ingen indkomst i perioden: {start_month:02}/{start_year} - {end_month:02}/{end_year}"
    ])
    nova_notes.add_text_note(case.uuid, note_title="Oprettet af robot", note_text=note_text, caseworker=caseworker, approved=True, nova_access=nova_access)
