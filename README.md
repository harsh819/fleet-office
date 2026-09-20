# Office Deployment Tool

A GUI wrapper around Microsoft's official **Office Deployment Tool (ODT)**.
Turns the manual two-command CMD process into a one-click app with a progress
bar and success/failure messages.

## Folder setup (required before running)

`OfficeInstaller.exe` can be run from anywhere (Desktop, Downloads, a USB
stick, an RMM push, etc.) — it does **not** need to sit next to `setup.exe`.
Instead it always reads from a fixed location:

```
C:\MS Office\
├── setup.exe                <- official Microsoft ODT, download from Microsoft
└── configuration.xml        <- your deployment config
```

The app creates `C:\MS Office` automatically on first run (after elevating),
but **you must place `setup.exe` and `configuration.xml` there yourself**
before clicking Start — if either file is missing, the Start button stays
disabled and the app tells you what's missing and where it's looking.

Get the official ODT `setup.exe` here (always download fresh from Microsoft,
don't reuse an old copy): https://www.microsoft.com/en-us/download/details.aspx?id=49117

Generate `configuration.xml` with Microsoft's official config generator:
https://config.office.com/

## Running it directly (for testing)

```
python office_installer.py
```

It will prompt for admin rights automatically (UAC popup) if not already
elevated.

## Packaging into a single .exe for distribution

```
pip install pyinstaller
pyinstaller --onefile --noconsole --uac-admin --name "OfficeInstaller" office_installer.py
```

- `--uac-admin` embeds a manifest so Windows shows the UAC prompt
  automatically on double-click (no console flash).
- `--noconsole` hides the terminal window.
- Output lands in `dist/OfficeInstaller.exe`.

On each target PC, `setup.exe` and `configuration.xml` must be placed in
`C:\MS Office`. `OfficeInstaller.exe` itself can be distributed and run from
anywhere (it's not tied to that folder).

## What happens when a user runs it

1. App checks for admin rights; requests elevation via UAC if needed.
2. App creates `C:\MS Office` if it doesn't exist yet, then checks
   `setup.exe` and `configuration.xml` are present there — if not,
   the Start button is disabled and it tells you what's missing.
3. User clicks **Start Installation**.
4. Runs `setup.exe /download configuration.xml` — progress bar advances.
5. Runs `setup.exe /configure configuration.xml` — this is the step where
   the native Microsoft Office installer UI briefly appears; that's
   Microsoft's own installer, not a bug.
6. On success: popup says **"Microsoft Office Installed Successfully"**.
7. On failure at any step: popup with an error message, and a
   `office_installer_error.log` file is written next to the app with the
   raw ODT output for troubleshooting.

## Customizing for different presets (product idea)

To turn this into more than a one-off tool, you could:
- Ship multiple `configuration.xml` presets (e.g. "Office Home", "Office
  Business", "Apps only: Word+Excel") and add a dropdown in the GUI to pick
  one before Start.
- Add a small settings screen to let IT admins swap which config is active
  without editing XML by hand.
- Bundle a "silent mode" flag for fully unattended rollout via a login
  script or RMM tool, with the GUI reserved for one-off manual runs.

## Notes

- This tool only ever calls Microsoft's own `setup.exe` with standard ODT
  flags (`/download`, `/configure`). It does not modify licensing, activation,
  or Windows/Office files itself — all of that is handled by Microsoft's
  installer.
- Requires a valid Office license/subscription tied to the `configuration.xml`
  you provide (e.g. via your Microsoft 365 tenant) for the install to
  actually activate correctly after setup.