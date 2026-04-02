import subprocess
import os
import webbrowser
import time
import sys
import random

def main():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    app_script_path = os.path.join(base_dir, 'src', 'app.py')
    
    # Construct the PYTHONPATH for the subprocess
    # This ensures the project root (base_dir) is in the Python path for the Flask app
    env = os.environ.copy()
    current_python_path = env.get('PYTHONPATH', '')
    
    # Prepend the project's base directory to PYTHONPATH
    if current_python_path:
        env['PYTHONPATH'] = f"{base_dir}{os.pathsep}{current_python_path}"
    else:
        env['PYTHONPATH'] = base_dir

    # Generate a random port between 5001 and 5015
    port = random.randint(5001, 5015)
    url = f"http://localhost:{port}/"

    print(f"Starting Flask application from {app_script_path} with PYTHONPATH={env['PYTHONPATH']}...")
    
    # Start the Flask app as a non-blocking process
    # Pass the selected port to the Flask app via an environment variable
    env['FLASK_RUN_PORT'] = str(port)
    process = subprocess.Popen(['python', app_script_path], env=env) # Pass the modified environment
    
    # Give the server a moment to start up
    time.sleep(1) 
    
    # Open the index page in a new browser tab
    if sys.platform == "win32":
        # On Windows, launch the browser directly
        print(f"Opening browser to {url}")
        webbrowser.open_new_tab(url)
    elif sys.platform == "darwin":
        # On macOS, launch the browser directly
        print(f"Opening browser to {url}")
        webbrowser.open_new_tab(url)
    elif sys.platform.startswith("linux"): # Includes WSL and other Linux environments
        # Check if running in WSL
        if "WSL_DISTRO_NAME" in os.environ or "WSL_LAUNCH_GUID" in os.environ:
            # In WSL, use wslview to open the browser on the Windows host
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
            # On native Linux, launch the browser directly
            print(f"Opening browser to {url}")
            webbrowser.open_new_tab(url)
    else:
        print(f"Unsupported platform: {sys.platform}. Please open your web browser and navigate to {url}")
    try:
        process.wait() # Wait for the Flask app to be terminated
    except KeyboardInterrupt:
        print("\nCtrl+C detected. Terminating Flask application...")
        process.terminate() # Send SIGTERM to the Flask process
        process.wait()      # Wait for the process to actually terminate
        print("Flask application terminated.")

if __name__ == "__main__":
    main()
