# parser.py

def parse_chunk(chunk_of_lines):
    """
    Analysiert einen Teil (Chunk) von Log-Zeilen.
    Diese Funktion wird von jedem CPU-Kern einzeln ausgeführt.
    
    Args:
        chunk_of_lines (list): Eine Liste von Tupeln, wobei jedes Tupel
                               (Zeilennummer, Zeileninhalt) ist.

    Returns:
        list: Eine Liste der gefundenen Fehler in diesem Chunk.
    """
    errors_found = []
    # Hier kommt deine eigentliche Analyse-Logik pro Zeile.
    # Wir suchen zur Demonstration nach Zeilen, die das Wort "ERROR" enthalten.
    for line_number, line_content in chunk_of_lines:
        if "ERROR" in line_content:
            # Wir speichern den Fehler mit Zeilennummer und Inhalt
            error_message = f"Zeile {line_number}: {line_content.strip()}"
            errors_found.append(error_message)
            
    return errors_found