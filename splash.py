from nicegui import ui, app


class SplashScreen:
    """Animated splash screen with living network background using Vanta.js"""

    def build(self):
        ui.add_head_html('''
            <script src="https://cdnjs.cloudflare.com/ajax/libs/three.js/r134/three.min.js"></script>
            <script src="https://cdn.jsdelivr.net/npm/vanta@latest/dist/vanta.net.min.js"></script>
            <style>
                @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600&display=swap');
                * { font-family: "Inter", -apple-system, system-ui, sans-serif; }
                body { margin: 0; overflow: hidden; background: #0a0a0a !important; transition: opacity 0.5s ease; }
                body.fade-out { opacity: 0; }

                #vanta-bg {
                    position: fixed;
                    top: 0; left: 0;
                    width: 100vw; height: 100vh;
                    z-index: 0;
                }

                .splash-content {
                    position: fixed;
                    top: 0; left: 0;
                    width: 100vw; height: 100vh;
                    display: flex;
                    flex-direction: column;
                    align-items: center;
                    justify-content: center;
                    z-index: 10;
                }

                .welcome-title {
                    font-size: 4rem;
                    font-weight: 300;
                    color: #ffffff;
                    letter-spacing: 0.4em;
                    text-transform: uppercase;
                    opacity: 0;
                    animation: fadeInUp 1.5s ease-out 0.5s forwards;
                    text-shadow: 0 0 20px rgba(100,150,255,0.2);
                }

                .enter-btn {
                    margin-top: 4rem;
                    padding: 1rem 4rem;
                    font-size: 0.75rem;
                    font-weight: 500;
                    letter-spacing: 0.3em;
                    color: #fff;
                    background: rgba(255,255,255,0.05);
                    border: 1px solid rgba(255,255,255,0.2);
                    border-radius: 50px;
                    cursor: pointer;
                    opacity: 0;
                    animation: fadeInUp 1.5s ease-out 1.5s forwards;
                    transition: all 0.4s ease;
                    text-transform: uppercase;
                    backdrop-filter: blur(10px);
                }

                .enter-btn:hover {
                    background: rgba(255,255,255,0.15);
                    border-color: rgba(255,255,255,0.4);
                    transform: scale(1.05);
                    box-shadow: 0 0 15px rgba(100,150,255,0.2);
                }

                @keyframes fadeInUp {
                    from {
                        opacity: 0;
                        transform: translateY(40px);
                    }
                    to {
                        opacity: 1;
                        transform: translateY(0);
                    }
                }

                .fade-out {
                    animation: fadeOut 0.6s ease-out forwards;
                }

                @keyframes fadeOut {
                    from {
                        opacity: 1;
                    }
                    to {
                        opacity: 0;
                    }
                }
            </style>
        ''')

        # Vanta.js background container
        ui.html(sanitize=False, content='<div id="vanta-bg"></div>')

        # Splash content
        with ui.element('div').classes('splash-content'):
            ui.html(sanitize=False, content='<h1 class="welcome-title">Panorama</h1>')
            ui.html(sanitize=False, content='<button class="enter-btn" onclick="document.body.classList.add(\'fade-out\'); setTimeout(() => window.location.href=\'/app\', 500)">Enter</button>')

        # Quit button
        ui.button('Quit', on_click=self._quit).style('''
            position: fixed;
            bottom: 2rem;
            right: 2rem;
            padding: 0.5rem 1.5rem;
            font-size: 0.65rem;
            font-weight: 500;
            letter-spacing: 0.2em;
            color: rgba(255,255,255,0.5);
            background: rgba(20,20,20,0.8);
            border: 1px solid rgba(255,255,255,0.1);
            border-radius: 4px;
            text-transform: uppercase;
            z-index: 20;
        ''').props('flat')

        # Initialize Vanta.js NET effect - creates animated living network
        ui.run_javascript('''
            setTimeout(() => {
                VANTA.NET({
                    el: "#vanta-bg",
                    mouseControls: false,
                    touchControls: false,
                    gyroControls: false,
                    minHeight: 200.00,
                    minWidth: 200.00,
                    scale: 1.00,
                    scaleMobile: 1.00,
                    color: 0x4a8eff,
                    backgroundColor: 0x0a0a0a,
                    points: 14.00,
                    maxDistance: 25.00,
                    spacing: 16.00,
                    showDots: true
                });
            }, 100);
        ''')

    def _quit(self):
        """Quit the application."""
        app.shutdown()
