# Build Instructions for yt-downloader-exe

This document provides step-by-step instructions on how to build an executable file for the YouTube Downloader application from the source code.

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

## Prerequisites

Before you begin, ensure you have the following installed on your system:

- Python 3.6 or higher
- pip (Python package installer)
- PyInstaller or cx_Freeze (for creating executables)

## Step 1: Clone the Repository

If you haven't already, clone the repository to your local machine:

```bash
git clone <repository-url>
cd UD
```

## Step 2: Install Dependencies

Install the required dependencies listed in `requirements.txt`:

```bash
pip install -r requirements.txt
```

## Step 3: Build the Executable

### 1. Download and Prepare FFmpeg Binaries

- Download static builds of `ffmpeg` and `ffprobe` for your OS:
  - [ffmpeg.org/download.html](https://ffmpeg.org/download.html)
  - [gyan.dev/ffmpeg/builds/](https://www.gyan.dev/ffmpeg/builds/)
- Extract `ffmpeg.exe` and `ffprobe.exe` (Windows) or the corresponding binaries for your OS.
- Place both binaries in your project, e.g., `UD/src/ffmpeg.exe` and `UD/src/ffprobe.exe`.

### 2. Using PyInstaller

To create an executable with PyInstaller and bundle FFmpeg and your application icon:

**If you are using PowerShell (the default terminal in Windows), do NOT use the backslash `\` for line continuation.**  
Instead, write the command all on one line, like this:

```powershell
python -m PyInstaller --onefile --windowed src/UD3.py --icon=src/UD.ico --add-binary "src/ffmpeg.exe;." --add-binary "src/ffprobe.exe;."
```

- `--icon=src/UD.ico` sets the application icon (make sure `UD.ico` is in the `src` folder).
- On Linux/Mac, use `:` instead of `;` in `--add-binary` (e.g., `src/ffmpeg:./`).

**Notes:**
- `--onefile`: Bundles everything into a single executable.
- `--windowed`: Hides the console window (for GUI apps).
- `--icon`: Sets the application icon.
- `--add-binary`: Bundles the FFmpeg binaries with your app.

The executable will be created in the `dist` directory.

### 3. Using cx_Freeze

If you prefer cx_Freeze, create a `setup.py` in the `UD` directory and specify the icon:

```python
# filepath: UD/setup.py
from cx_Freeze import setup, Executable

setup(
    name="yt-downloader",
    version="1.0",
    description="YouTube Downloader Application",
    executables=[Executable("src/UD3.py", base="Win32GUI", icon="src/UD.ico")],
    options={
        "build_exe": {
            "include_files": [
                ("src/ffmpeg.exe", "ffmpeg.exe"),
                ("src/ffprobe.exe", "ffprobe.exe"),
                ("src/UD.ico", "UD.ico"),
            ]
        }
    }
)
```

Then build with:

```bash
python setup.py build
```

The executable will be in the `build` directory.

## Step 4: Running the Executable

- Go to the `dist` (PyInstaller) or `build` (cx_Freeze) directory.
- Run the generated executable.
- The program will automatically use the bundled `ffmpeg` and `ffprobe` if present in the same directory as the executable.

## Additional Notes

- Ensure you have permission to run executables on your system.
- For troubleshooting, refer to the [PyInstaller](https://pyinstaller.org/) or [cx_Freeze](https://cx-freeze.readthedocs.io/) documentation.
