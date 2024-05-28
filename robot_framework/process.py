"""This module contains the main process of the robot."""

import os
import json
from datetime import datetime
import re

import pyodbc
from OpenOrchestrator.orchestrator_connection.connection import OrchestratorConnection
from itk_dev_shared_components.kmd_nova.authentication import NovaAccess
from itk_dev_shared_components.graph import authentication as graph_authentication
from itk_dev_shared_components.graph import mail as graph_mail
from itk_dev_shared_components.smtp import smtp_util

from robot_framework.sub_process import indkomst, database, nova
from robot_framework import config


def process(orchestrator_connection: OrchestratorConnection) -> None:
    """Do the primary process of the robot."""
    orchestrator_connection.log_trace("Running process.")

    graph_creds = orchestrator_connection.get_credential(config.GRAPH_API)
    graph_access = graph_authentication.authorize_by_username_password(graph_creds.username, **json.loads(graph_creds.password))

    mails = graph_mail.get_emails_from_folder("itk-rpa@mkb.aarhus.dk", "Indbakke/Udrejsekontrol", graph_access)
    mails = [mail for mail in mails if mail.sender == 'noreply@aarhus.dk' and mail.subject == 'RPA - Udrejsekontrol (fra Selvbetjening.aarhuskommune.dk)']
    mails.sort(key=lambda m: datetime.fromisoformat(m.received_time))

    if not mails:
        orchestrator_connection.log_info("No emails in queue.")
        return

    for mail in mails:
        email_text = mail.get_text()
        sender_email = re.findall("BrugerE-mail: (.+?)AZ-ident", email_text)[0]
        sender_ident = re.findall("AZ-ident: (.+?)Antal", email_text)[0]
        requested_count = int(re.findall(r"Antal ønskede sager(\d+)", email_text)[0])

        approved_senders = json.loads(orchestrator_connection.process_arguments)["approved_senders"]

        if sender_ident not in approved_senders:
            orchestrator_connection.log_info(f"Request denied for: {sender_email} - {sender_ident}")
            smtp_util.send_email(sender_email, "itk-rpa@mkb.aarhus.dk", "Anmodning afvist", "Din anmodning til Udrejsekontrol er blevet afvist, da du ikke er på listen af godkendte medarbejdere.", smtp_server=config.SMTP_SERVER, smtp_port=config.SMTP_PORT)
            graph_mail.delete_email(mail, graph_access)
        else:
            found_count, handled_count = find_cases(requested_count, orchestrator_connection)
            orchestrator_connection.log_info(f"{found_count} new cases created in Nova. {handled_count} people checked.")
            smtp_util.send_email(sender_email, "itk-rpa@mkb.aarhus.dk", "Udrejse sager oprettet", f"Din anmodning til Udrejsekontrol er blevet behandlet.\nDer er blevet gennemsøgt {handled_count} personer og oprettet {found_count} nye sager i KMD Nova.", smtp_server=config.SMTP_SERVER, smtp_port=config.SMTP_PORT)
            graph_mail.delete_email(mail, graph_access)
            return


def find_cases(requested_count: int, orchestrator_connection: OrchestratorConnection) -> tuple[int, int]:
    """Search through a list of possible candidates and create cases in Nova for the relevant ones.

    Args:
        requested_count: The number of cases to aim for.
        orchestrator_connection: The connection to Orchestrator.

    Returns:
        The number of created cases and the number of checked candidates.
    """
    nova_creds = orchestrator_connection.get_credential(config.NOVA_API)
    nova_access = NovaAccess(nova_creds.username, nova_creds.password)

    udrejse_conn = pyodbc.connect("Server=SRVSQLHOTEL03;Database=MKB-ITK-RPA;Trusted_Connection=Yes;Driver={ODBC Driver 17 for SQL Server}")

    candidates = database.get_candidate_list(orchestrator_connection, udrejse_conn)

    handled_count = 0
    found_count = 0

    for candidate in candidates:
        if handled_count >= config.MAX_HANDLED_CASES or found_count >= requested_count:
            break

        has_income = indkomst.search_indkomst(candidate.cpr)

        if not has_income:
            orchestrator_connection.log_info(f"Creating case in Nova on {candidate.cpr}")
            nova.add_case(candidate, nova_access)
            found_count += 1

        database.update_person(udrejse_conn, candidate, has_income)

        handled_count += 1

    return found_count, handled_count


if __name__ == '__main__':
    conn_string = os.getenv("OpenOrchestratorConnString")
    crypto_key = os.getenv("OpenOrchestratorKey")
    oc = OrchestratorConnection("Udrejse Test", conn_string, crypto_key, '{"approved_senders": ["az68933"]}')
    process(oc)
