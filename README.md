# images_to_mp4
Ein einfaches GUI-Tool (PyQt5) um beliebig viele Bilder per Drag &amp; Drop oder Dateiauswahl hinzuzufügen und daraus ein MP4-Video zu erstellen.
<br><br>
<img width="706" height="519" alt="imagesToMp4" src="https://github.com/user-attachments/assets/2088f2cd-71e0-4263-980d-6fecf58b7739" />
<br><br>
Benötigte Pakete:<br>
    pip install PyQt5 Pillow opencv-python<br>
<br><br>
Funktionen:<br>
- Drag & Drop von Bildern in die Listenansicht<br>
- Bilder per Dateidialog hinzufügen<br>
- Reihenfolge änderbar (Drag within list)<br>
- Einstellbar: Bildwechsel-Intervall in ms (default 40ms)<br>
- Einstellbar: Ausgabegröße (default 512x512)<br>
- Lanczos-Resampling beim Skalieren (Pillow Image.LANCZOS)<br>
- Save-Dialog um MP4 zu speichern<br>
- Fortschrittsanzeige<br>
