import os
import sys
import random

try:
    import tiktoken_ext.openai_public  # Required for PyInstaller to bundle tiktoken encodings (cl100k_base, etc.)
except ImportError:
    pass
import time
import socket
import threading
import webbrowser
import subprocess

# Ensure project root directory is in sys.path
base_dir = os.path.dirname(os.path.abspath(__file__))
if base_dir not in sys.path:
    sys.path.insert(0, base_dir)

from src.app import app


def wait_and_open_browser(port):
    """Polls until server port is listening, then opens the browser."""
    url = f"http://localhost:{port}/"
    start_time = time.time()
    server_ready = False
    while time.time() - start_time < 15:
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=0.5):
                server_ready = True
                break
        except (OSError, ConnectionRefusedError):
            time.sleep(0.2)

    if not server_ready:
        print(f"Warning: Server did not respond on port {port} within timeout.")
        return

    if sys.platform in ("win32", "darwin"):
        print(f"Opening browser to {url}")
        webbrowser.open_new_tab(url)
    elif sys.platform.startswith("linux"):
        if "WSL_DISTRO_NAME" in os.environ or "WSL_LAUNCH_GUID" in os.environ:
            print(f"Opening browser in Windows to {url} (via wslview)")
            try:
                subprocess.run(["wslview", url], check=True)
            except FileNotFoundError:
                print("wslview not found. Please install it or open the URL manually.")
                print(f"Please open your web browser and navigate to {url}")
            except subprocess.CalledProcessError as e:
                print(f"Error opening browser via wslview: {e}")
                print(f"Please open your web browser and navigate to {url}")
        else:
            print(f"Opening browser to {url}")
            webbrowser.open_new_tab(url)
    else:
        print(f"Unsupported platform: {sys.platform}. Please open your web browser and navigate to {url}")


def main():
    port = random.randint(5001, 5015)
    os.environ['FLASK_RUN_PORT'] = str(port)

    # Launch browser only after server socket is actively accepting connections
    threading.Thread(target=wait_and_open_browser, args=(port,), daemon=True).start()

    debug_mode = os.environ.get('FLASK_DEBUG', 'false').lower() in ('true', '1')
    print(f"Starting Flask application on port {port}...")
    app.run(debug=debug_mode, host='0.0.0.0', port=port, use_reloader=False)


if __name__ == "__main__":
    import multiprocessing
    multiprocessing.freeze_support()
    main()
