# Photon Counter

Real-time photon counting software for the FLIR BFS-U3-04S2M-C camera using EMVA 1288 calibrated conversion parameters.

![Photon Count Monitor](assets/gui.png)

## Getting Started

### Prerequisites
- [uv](https://github.com/astral-sh/uv) package manager
- Homebrew (for macOS dependencies)
- [Spinnaker SDK](https://www.flir.com/products/spinnaker-sdk/) (version 4.1.0.172 or compatible)

### Installation

1. Install Spinnaker SDK:
   - Download and install the Spinnaker SDK from FLIR/Teledyne's website
   - Set the required environment variable by adding this to your shell profile (`~/.zshrc` or `~/.bash_profile`):
   ```bash
   export SPINNAKER_GENTL64_CTI=/Applications/Spinnaker/lib/spinnaker-gentl/Spinnaker_GenTL.cti
   ```
   - Reload your shell configuration:
   ```bash
   source ~/.zshrc  # or source ~/.bash_profile
   ```

2. Install system dependencies:
```bash
brew install pkg-config libomp libusb ffmpeg@2.8
```

3. Create a virtual environment with Python 3.10:
```bash
uv venv --python 3.10
```

4. Activate the virtual environment:
```bash
source .venv/bin/activate
```

5. Install Python dependencies:
```bash
uv pip install -r requirements.txt
```
