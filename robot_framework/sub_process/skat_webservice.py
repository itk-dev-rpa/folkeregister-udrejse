"""This module is responsible for interaction with the SKAT SOAP webservice."""

import json
import uuid
from datetime import datetime

from OpenOrchestrator.orchestrator_connection.connection import OrchestratorConnection
from python_skat_webservice.soap_signer import SOAPSigner
from python_skat_webservice.common import CallerInfo
from python_skat_webservice import indkomst_oplysning_person_hent
from lxml import etree
import hvac

from robot_framework import config


FIELD_IDS = [
    "100000000000000057", # A-indkomst, hvoraf der betales AM-bidrag 
    "100000000000000058", # A-indkomst hvoraf der ikke betales AM-bidrag
    "100000000000000070", # B-indkomst, hvoraf der betales AM-bidrag
    "100000000000000071" # B-indkomst, hvoraf der ikke betales AM-bidrag
]


def setup_webservice(orchestrator_connection: OrchestratorConnection) -> tuple[CallerInfo, SOAPSigner]:
    """Setup access to the SKAT webservice.
    Get certificates from the vault and caller info from Orchestrator.

    Args:
        orchestrator_connection: The connection to Orchestrator.

    Returns:
        A tuple of CallerInfo and SOAPSigner objects used in calling the webservice.
    """
    # Access Keyvault
    vault_auth = orchestrator_connection.get_credential(config.KEYVAULT_CREDENTIALS)
    vault_uri = orchestrator_connection.get_constant(config.KEYVAULT_URI).value

    vault_client = hvac.Client(vault_uri)
    vault_client.auth.approle.login(role_id=vault_auth.username, secret_id=vault_auth.password)

    # Get certificate
    read_response = vault_client.secrets.kv.v2.read_secret_version(mount_point='rpa', path=config.KEYVAULT_PATH, raise_on_deleted_version=True)
    certificate: str = read_response['data']['data']['cert']
    key: str = read_response['data']['data']['key']

    signer = SOAPSigner(certificate.encode(), key.encode())

    skat_info = orchestrator_connection.get_constant(config.SKAT_WEBSERVICE)
    caller_info = CallerInfo(**json.loads(skat_info.value))

    return caller_info, signer


def check_income(cpr: str, caller_info: CallerInfo, signer: SOAPSigner) -> bool:
    """Checks the income of the given person.

    Args:
        cpr: The cpr number of the person to check.
        caller_info: The CallerInfo object used in the webservice call.
        signer: The SOAPSigner object used in the webservice call.

    Returns:
        True if the person has an income greater than the income threshold.
    """

    today = datetime.today()
    end_month, end_year = subtract_months(today.month, today.year, 1)
    start_month, start_year = subtract_months(today.month, today.year, config.INCOME_MONTHS)

    month_from = f"{start_year}{start_month:02}"
    month_to = f"{end_year}{end_month:02}"

    xml_result = indkomst_oplysning_person_hent.search_income(
        cpr=cpr,
        month_from=month_from,
        month_to=month_to,
        transaction_id=str(uuid.uuid4()),
        caller_info=caller_info,
        soap_signer=signer
    )

    income = handle_xml(xml_result)

    return income > config.MIN_INCOME


def handle_xml(xml_result: str) -> float:
    """Read an xml response from the SKAT IndkomstOplysningPersonHent
    and sum the fields given in FIELD_IDS.

    Args:
        xml_result: The xml response.

    Returns:
        The sum of the fields' values.
    """
    root = etree.fromstring(xml_result.encode())

    namespaces = {
        "ns1": "http://rep.oio.dk/skat.dk/eindkomst/",
        "b1": "http://rep.oio.dk/skat.dk/eindkomst/class/blanket/xml/schemas/20071202/",
        "b2": "http://rep.oio.dk/skat.dk/eindkomst/class/blanketfelt/xml/schemas/20071202/",
        "b3": "http://rep.oio.dk/skat.dk/eindkomst/class/feltenhedtype/xml/schemas/20071202/",
        "b4": "http://rep.oio.dk/skat.dk/eindkomst/class/angivelsefelt/xml/schemas/20071202/"
    }

    sum = 0

    for field_id in FIELD_IDS:
        fields = root.xpath(
            f"//ns1:AngivelseFeltIndholdStruktur[ns1:BlanketFeltEnhedStruktur/b2:BlanketFeltNummerIdentifikator='{field_id}']",
            namespaces=namespaces
        )
        for f in fields:
            value_text = f.find('b4:AngivelseFeltIndholdTekst', namespaces).text
            sum += float(value_text)

    return sum



def subtract_months(month: int, year: int, delta: int) -> tuple[int, int]:
    """Given a month (1-12) and a year, returns the month and year 'delta' months in the past.

    Args:
        month: The current month (1 to 12).
        year: The current year.
        delta: The amount of months to subtract.

    Returns:
        A tuple (new_month, new_year).
    """
    total_months = year * 12 + month
    new_total_months = total_months - delta

    new_year = new_total_months // 12
    new_month = new_total_months % 12
    if new_month == 0:
        new_month = 12
        new_year -= 1

    return new_month, new_year
