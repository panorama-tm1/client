"""CSS styles for the application."""

APP_STYLES = '''
<script src="https://cdn.tailwindcss.com"></script>
<style>
    * { font-family: "Inter", -apple-system, system-ui, sans-serif; }
    body { background: #0a0a0a !important; overflow: hidden; }
    .q-field--outlined .q-field__control:before {
        border: 1px solid #262626 !important;
        border-radius: 6px !important;
    }
    .q-field--outlined.q-field--focused .q-field__control:before {
        border-color: #525252 !important;
    }
    .q-field--dark .q-field__control {
        background: transparent !important;
        border-radius: 6px !important;
    }
    .q-field__native, .q-field__input { color: #e5e5e5 !important; font-size: 13px !important; }
    .q-btn { text-transform: none !important; }
    .q-toggle__inner--truthy { color: #e5e5e5 !important; }
    .q-select__dropdown-icon { display: none !important; }
    .q-field__append { display: none !important; }
</style>
'''

FILE_ICON_SVG = '''<svg xmlns="http://www.w3.org/2000/svg" width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" class="text-neutral-400"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path><polyline points="14 2 14 8 20 8"></polyline><line x1="16" y1="13" x2="8" y2="13"></line><line x1="16" y1="17" x2="8" y2="17"></line><polyline points="10 9 9 9 8 9"></polyline></svg>'''
