# yt-downloader-exe

## Overview
yt-downloader-exe is a Python-based application that allows users to download videos and audio from YouTube. The application features a user-friendly graphical interface built with PyQt5, making it accessible for users of all technical levels.

## Project Structure

```
UD/
├── src/
│   └── UD3.py
├── requirements.txt
├── README.md
├── build_instructions.md
└── ... (other files)
```

## Features
- Download videos and audio from YouTube using yt-dlp.
- Option to embed thumbnails in audio files.
- Selectable output formats and codecs for video and audio.
- Intuitive GUI for easy navigation and usage.

## Installation
To install the necessary dependencies, run the following command in your terminal from the `UD` directory:

```
pip install -r requirements.txt
```

## Usage
1. Run the application by executing the main script located in the `src` directory:
   ```
   python src/UD3.py
   ```
2. Enter the YouTube URL you wish to download.
3. Choose the desired output format and codec.
4. Select the save directory for your downloaded files.
5. Click the "Download" button to start the download process.

## Building the Executable
For instructions on how to build the executable file from the source code, please refer to the `build_instructions.md` file in the `UD` folder.

## Contributing
Contributions are welcome! Please feel free to submit issues or pull requests to enhance the functionality of the application.

## License
This project is licensed under the MIT License. See the LICENSE file for more details.
