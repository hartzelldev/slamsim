import subprocess
import os
import webbrowser
import time
import sys # Import sys

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

    print(f"Starting Flask application from {app_script_path} with PYTHONPATH={env['PYTHONPATH']}...")
    
    # Start the Flask app as a non-blocking process
    process = subprocess.Popen(['python', app_script_path], env=env) # Pass the modified environment
    
    # Give the server a moment to start up
    time.sleep(1) 
    
    # Open the index page in a new browser tab
    print("Opening browser to http://127.0.0.1:5000/")
    webbrowser.open_new_tab('http://127.0.0.1:5000/')
    try:
        process.wait() # Wait for the Flask app to be terminated
    except KeyboardInterrupt:
        print("\nCtrl+C detected. Terminating Flask application...")
        process.terminate() # Send SIGTERM to the Flask process
        process.wait()      # Wait for the process to actually terminate
        print("Flask application terminated.")

if __name__ == "__main__":
    main()
