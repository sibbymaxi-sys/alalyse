# error_manager.py
from mv3d_definitions import SCS_FAULT_CODES
from error_definitions import ERROR_DEFINITIONS, check_for_error as check_generic_error

def get_error_details(error_code, log_line=""):
    """
    Sucht zuerst in der offiziellen SCS-Fehlerliste nach einem Code.
    Wenn nichts gefunden wird, wird die allgemeinere error_definitions.py als Fallback durchsucht.
    """
    # 1. Versuche, den spezifischen Fehlercode in der offiziellen Liste zu finden
    if isinstance(error_code, int) and error_code in SCS_FAULT_CODES:
        # Wir nehmen den Text aus der offiziellen Liste
        error_text = SCS_FAULT_CODES[error_code]
        # Wir suchen nach einer detaillierteren Beschreibung in der allgemeinen Liste
        description, action = check_generic_error(error_text)
        return error_text, description, action

    # 2. Wenn kein Code gefunden wurde, nutze die allgemeine Funktion als Fallback
    #    Diese durchsucht den gesamten Log-Text nach Schlüsselwörtern.
    if not log_line:
        log_line = str(error_code) # Stelle sicher, dass wir einen String haben

    description, action = check_generic_error(log_line)
    
    # Wenn die Fallback-Suche erfolgreich war, aber der Code unbekannt ist
    if description != "Allgemeiner System-Fehler":
        return "N/A", description, action
        
    # 3. Wenn nirgendwo etwas gefunden wurde
    return "Unbekannter Fehlercode", "Keine Definition gefunden", "Manuelle Analyse erforderlich."