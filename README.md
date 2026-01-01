# images_to_mp4
A simple GUI tool (PyQt5) to add any number of images via drag & drop or file selection and create an MP4 video from them. (Multi language: EN/DE/FR/ESP/RU)
<br><br>
<img width="764" height="592" alt="grafik" src="https://github.com/user-attachments/assets/095cf031-5f01-4651-a6ef-fb30d91be03a" />
<br><br>
Requirements:<br>
    pip install PyQt5 Pillow opencv-python numpy<br>
<br><br>
Features:<br>
- Drag & Drop images and folders (non-recursive)
- Add files / add folder via dialogs
- Reorder by dragging inside the list
- Remove selected / clear list
- Output size + frame interval (ms) settings
- EXIF auto-rotate support
- Center-fit with black padding (keeps aspect ratio)
- Progress bar + status text + cancel button
- Multi-language UI switcher via radio buttons:
  German, English, French, Spanish, Russian
