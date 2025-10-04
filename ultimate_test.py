# ultimate_test.py
import sys
from PyQt5.QtWidgets import QApplication, QWidget, QLabel

print("TEST: Starte den ultimativen Test...")

try:
    app = QApplication(sys.argv)
    print("TEST: QApplication erstellt.")

    window = QWidget()
    window.setWindowTitle("Test-Fenster")
    window.setGeometry(200, 200, 300, 100)
    
    label = QLabel("Wenn Sie das sehen, funktioniert PyQt5!", parent=window)
    label.move(50, 40)
    
    print("TEST: Fenster erstellt. Zeige es jetzt an...")
    window.show()
    
    print("TEST: Starte die App-Schleife. Das Fenster sollte jetzt sichtbar sein.")
    sys.exit(app.exec_())

except Exception as e:
    print(f"TEST FEHLGESCHLAGEN: Ein Fehler ist aufgetreten: {e}")
    input("Drücken Sie Enter zum Beenden.")