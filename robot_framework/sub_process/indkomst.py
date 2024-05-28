"""This module handles actions in KMD Indkomst."""

import subprocess
from datetime import datetime, timedelta

import uiautomation as auto

from robot_framework import config


def kill_indkomst():
    """Kill the KMD Indkomst and KMD Logon processes."""
    subprocess.call(["taskkill", "/f", "/im", "KMD.AY.Indkomstgrundlag.UI.Application.exe"])
    subprocess.call(["taskkill", "/f", "/im", "KMD.YH.Security.Logon.Desktop.exe"])


def open_indkomst(username: str, password: str):
    """Open and login to KMD Indkomst.

    Args:
        username: Username for KMD Indkomst.
        password: Password for KMD Indkomst.
    """
    subprocess.Popen(r"C:\Program Files (x86)\KMD\KMD.AY.Indkomstgrundlag\KMD.AY.Indkomstgrundlag.UI.Application.exe", cwd=r"C:\Program Files (x86)\KMD\KMD.AY.Indkomstgrundlag")

    logon = auto.WindowControl(Name="KMD Logon - Brugernavn og kodeord", searchDepth=1)
    logon.Exists()

    logon.EditControl(AutomationId="UserPwTextBoxUserName").GetValuePattern().SetValue(username)
    logon.EditControl(AutomationId="UserPwPasswordBoxPassword").GetValuePattern().SetValue(password)
    logon.ButtonControl(AutomationId="UserPwLogonButton").Click(simulateMove=False)


def search_indkomst(cpr: str) -> bool:
    """Checks the income of the given person.

    Args:
        cpr: The cpr number of the person to check.

    Raises:
        RuntimeError: If KMD Indkomst can't be found.

    Returns:
        True if the person has income.
    """
    indkomst_window = auto.WindowControl(RegexName="KMDIndkomst.*", AutomationId="GrundbilledeForm", searchDepth=1)

    if not indkomst_window.Exists():
        raise RuntimeError("Couldn't find KMD Indkomst")

    person_edit = indkomst_window.PaneControl(AutomationId="sagsPersonCPRMaskedTextBox").EditControl(AutomationId="maskedTextBoxEx")
    person_edit.SendKeys(cpr)

    # Search and open eIndkomst
    indkomst_window.ButtonControl(AutomationId="btnOK").GetInvokePattern().Invoke()
    indkomst_window.SendKeys("{ctrl}e")

    # Enter dates
    dialog = indkomst_window.WindowControl(AutomationId="VisMereDialog")

    from_date_value = (datetime.today()-timedelta(days=config.INCOME_DAYS)).strftime("%d-%m-%Y")
    from_date = dialog.PaneControl(AutomationId="fraDatoDateSelectorControl").EditControl()
    from_date.GetValuePattern().SetValue(from_date_value)

    to_date_value = datetime.today().strftime("%d-%m-%Y")
    to_date = dialog.PaneControl(AutomationId="tilDatoDateSelectorControl").EditControl()
    to_date.GetValuePattern().SetValue(to_date_value)

    # Search
    dialog.ButtonControl(AutomationId="btnSearch").GetInvokePattern().Invoke()

    # Check main income
    table = indkomst_window.TabControl().TableControl(AutomationId="listGridView", foundIndex=2)
    table.SendKeys("{Ctrl}{Down}{Ctrl}c")
    has_income = _check_income_in_clipboard()

    # Exit
    indkomst_window.MenuItemControl(Name="Skift person", searchDepth=2).Click(simulateMove=False)

    return has_income


def _check_income_in_clipboard() -> bool:
    """Check the income that is currently copied on the clipboard.

    Returns:
        True if the income is greater than the minimum value.
    """
    income_text = auto.GetClipboardText().split()[-1]
    income_text = income_text.replace(".", "")
    income_text = income_text.replace(",", ".")
    return float(income_text) > config.MIN_INCOME
