"""Reusable UI components."""

from nicegui import ui


def radio_option(label: str, active: bool, on_click) -> None:
    """Render a styled radio option."""
    border = 'border-neutral-500' if active else 'border-neutral-800'
    with ui.row().classes(f'w-full items-center p-2.5 rounded border {border} cursor-pointer mb-1.5').on('click', on_click):
        ring = 'border-neutral-300' if active else 'border-neutral-600'
        with ui.element('div').classes(f'w-3 h-3 rounded-full border-[1.5px] {ring} flex items-center justify-center mr-2'):
            if active:
                ui.element('div').classes('w-1.5 h-1.5 rounded-full bg-neutral-300')
        ui.label(label).classes('text-[12px] text-neutral-300')


def labeled_input(label: str, value: str = '', password: bool = False, classes: str = 'w-full'):
    """Create a labeled input field."""
    with ui.column().classes(f'{classes} gap-0.5'):
        ui.label(label).classes('text-[11px] text-neutral-500')
        if password:
            inp = ui.input(value=value, password=True, password_toggle_button=True)
        else:
            inp = ui.input(value=value)
        inp.classes('w-full').props('dense outlined dark')
        return inp


def progress_bar(steps: int, current: int) -> None:
    """Render step progress bar."""
    with ui.row().classes('w-full mb-4 gap-1'):
        for i in range(steps):
            color = 'bg-neutral-300' if i <= current else 'bg-neutral-800'
            ui.element('div').classes(f'flex-1 h-[2px] rounded-full {color}')


def step_header(step: int, name: str) -> None:
    """Render step header with number and name."""
    ui.label(f'{step + 1}/5 · {name}').classes('text-[11px] text-neutral-500 mb-3')
