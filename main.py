"""Panorama - TM1 Data Fetcher Application."""

import sys
from nicegui import ui

from splash import SplashScreen
from ui.wizard import TM1Wizard


splash = SplashScreen()
wizard = TM1Wizard()


@ui.page('/')
def welcome():
    """Splash screen page."""
    splash.build()


@ui.page('/app')
def main():
    """Main wizard page."""
    wizard.build()


if __name__ in {"__main__", "__mp_main__"}:
    DEV = '--dev' in sys.argv
    ui.run(
        title='Panorama',
        dark=True,
        native=not DEV,
        window_size=(1280, 720),
        reload=DEV,
        port=8080 if DEV else None
    )
