import os
import zipfile
import shutil
from datetime import datetime
import litellm
import json
import html
import base64
from flask import Blueprint, render_template, request, redirect, url_for, flash, send_file, current_app # Import current_app
from src.system import get_project_root, DATA_DIR, delete_all_temporary_files
from src.prefs import load_preferences
from src.wrestlers import add_wrestler
from src.static_site_generator import generate_static_site, STATIC_SITE_ZIP_DIR_NAME # Import new functions and constants

tools_bp = Blueprint('tools', __name__, url_prefix='/tools')

@tools_bp.route('/')
def tools_main():
    """Renders the main tools dashboard page."""
    # Get list of existing static site zip files
    zip_storage_path = os.path.join(get_project_root(), STATIC_SITE_ZIP_DIR_NAME)
    static_site_zips = []
    if os.path.exists(zip_storage_path):
        static_site_zips = sorted([f for f in os.listdir(zip_storage_path) if f.endswith('.zip')], reverse=True)
    return render_template('tools/main.html', static_site_zips=static_site_zips)

@tools_bp.route('/backup')
def backup_restore():
    """Renders the backup and restore section within the tools dashboard."""
    return render_template('tools/main.html', active_tool='backup_restore')

@tools_bp.route('/ai-roster-generator')
def ai_roster_generator_form():
    """Renders the AI Roster Generator input form."""
    return render_template('tools/roster_generator.html')

@tools_bp.route('/generate-roster', methods=['POST'])
def generate_roster():
    """
    Generates a roster of wrestlers using AI based on user input and displays them for review.
    """
    roster_prompt = request.form.get('roster_prompt')
    content_mode = request.form.get('content_mode')
    max_wrestlers = min(int(request.form.get('max_wrestlers', 10)), 30) # Cap at 30

    if not roster_prompt:
        flash("Roster prompt cannot be empty.", "danger")
        return redirect(url_for('tools.ai_roster_generator_form'))

    try:
        # Load AI preferences
        prefs = load_preferences()
        model_provider = prefs.get('ai_provider') # Corrected key
        model_name = prefs.get('ai_model')        # Corrected key
        
        api_key = None
        if model_provider == "Google":
            api_key = prefs.get('google_api_key')
            os.environ["GEMINI_API_KEY"] = api_key # Set environment variable for litellm
        elif model_provider == "OpenAI":
            api_key = prefs.get('openai_api_key')
            os.environ["OPENAI_API_KEY"] = api_key # Set environment variable for litellm
        # Add other providers and their respective environment variables if necessary

        if not all([model_provider, model_name, api_key]):
            flash("AI model preferences are not fully configured. Please check your preferences.", "danger")
            return redirect(url_for('tools.ai_roster_generator_form'))

        system_prompt = f"""
        You are an expert wrestling booker and creative writer. Your task is to generate a list of {max_wrestlers} professional wrestlers based on the user's prompt.
        The output MUST be a single, valid JSON object with a top-level key "wrestlers" containing an array of wrestler objects.
        Each wrestler object MUST strictly adhere to the following schema, which only includes the creative elements:
        {{
          "Name": "STRING (e.g., Ric Flair) - Must be unique and creative.",
          "nickname": "STRING (e.g., 'The Nature Boy') - Can be empty if no nickname.",
          "location": "STRING (e.g., 'Charlotte, North Carolina' or 'Parts Unknown')",
          "Alignment": "STRING (MUST be one of: 'Babyface', 'Heel', 'Tweener')",
          "Wrestling_Styles": "ARRAY OF STRINGS (List 1-3 appropriate styles, e.g., ['Technical', 'Brawler', 'High-Flyer'])",
          "Moves": "ARRAY OF STRINGS (List 3-5 signature moves. Use generic names only for non-finishers. MUST include one clear finisher name)",
          "Finisher": "STRING (The name of the finisher move, must match one item in 'Moves')",
          "Height": "STRING (e.g., '5 ft. 1 in.' or '185 cm')",
          "Weight": "STRING (e.g., '243 lbs.')",
          "DOB": "DATE (e.g. '1972-07-04') - Must be a valid date in YYYY-MM-DD format."
        }}
        Ensure all fields are populated with creative and realistic data relevant to the prompt.
        The 'Name' field must be unique for each wrestler.
        """

        # --- Fix 1: Dynamically Modify System Prompt for Real-World Grounding ---
        if content_mode == 'real_world':
            # This is the CRITICAL instruction to force tool use
            system_prompt += f"""
            
            *** CRITICAL REAL-WORLD INSTRUCTION ***
            You are in REAL-WORLD mode. You MUST use the Google Search grounding tool to find the real names, 
            heights, weights, birthdates, and move sets of historical or active wrestlers matching the user's prompt. 
            Do NOT invent any data for this mode. Use the information found via search exclusively.
            """
            user_prompt = f"Using your search tool, generate {max_wrestlers} REAL-WORLD wrestlers. Creative prompt: '{roster_prompt}'"

        else:
            # Revert to standard fictional prompt for clarity
            user_prompt = f"Generate {max_wrestlers} FICTIONAL wrestlers. Creative prompt: '{roster_prompt}'"
        
        # Grounding logic
        tools = []
        if content_mode == 'real_world':
            tools = [{"google_search": {}}]

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]

        # Construct the model string in the format litellm expects (e.g., "gemini/gemini-1.5-flash")
        litellm_model_string = ""
        if model_provider == "Google":
            litellm_model_string = f"gemini/{model_name}"
        elif model_provider == "OpenAI":
            litellm_model_string = f"openai/{model_name}"
        # Add other providers if necessary

        if not litellm_model_string:
            flash("Unsupported AI provider configured.", "danger")
            return redirect(url_for('tools.ai_roster_generator_form'))

        response = litellm.completion(
            model=litellm_model_string,
            messages=messages,
            tools=tools,
            response_format={"type": "json_object"}, # Instruct API to return JSON
            temperature=0.7 # A bit of creativity
        )

        # Extract content from the response
        ai_content = response.choices[0].message.content
        
        # Parse the JSON response
        generated_data = json.loads(ai_content)
        generated_roster_raw = generated_data.get('wrestlers', [])

        
        for wrestler_data in generated_roster_raw:
            # --- START FIX: Key Capitalization and Normalization ---
            # Now ADD the capitalized key without removing the lowercase one.
            # This satisfies both the HTML template (which uses lowercase keys for display)
            # and the database commit (which uses capitalized keys).
            
            # 1. Normalize 'location' to 'Location'
            if 'location' in wrestler_data:
                wrestler_data['Location'] = wrestler_data['location'] # ADD capitalized key
            
            # 2. Normalize 'nickname' to 'Nickname'
            if 'nickname' in wrestler_data:
                wrestler_data['Nickname'] = wrestler_data['nickname'] # ADD capitalized key
            # --- END FIX ---
            
            # Set Belt, Status, and Stats defaults (previous fix)
            if 'Status' not in wrestler_data:
                wrestler_data['Status'] = 'Inactive' 
            if 'Belt' not in wrestler_data:
                wrestler_data['Belt'] = '' 
            if 'Team' not in wrestler_data:
                wrestler_data['Team'] = ''

            # Initialize all match record fields if missing
            for key in ['Singles_Wins', 'Singles_Losses', 'Singles_Draws', 'Tag_Wins', 'Tag_Losses', 'Tag_Draws']:
                if key not in wrestler_data:
                    wrestler_data[key] = '0'
        

        # Prepare roster for template: original data for display, encoded data for form submission
        generated_roster_for_template = []
        for wrestler_data in generated_roster_raw:
            # Convert dict to JSON string, then Base64 encode it
            encoded_wrestler = base64.b64encode(json.dumps(wrestler_data).encode('utf-8')).decode('utf-8')
            generated_roster_for_template.append({
                'display_data': wrestler_data,
                'encoded_data': encoded_wrestler
            })

        if not generated_roster_for_template:
            flash("AI generated an empty roster or invalid structure. Please try again.", "warning")
            return redirect(url_for('tools.ai_roster_generator_form'))

        # --- Fix 2: Extract Grounding Sources (Even if unused right now, it's necessary for inspection) ---
        search_sources = []
        try:
            # litellm response structure may vary, check for standard grounding metadata
            if response.get('usage', {}).get('grounding_metadata'):
                search_sources = response['usage']['grounding_metadata'].get('grounding_attributions', [])
        except AttributeError:
            # Handle cases where the response structure is unexpected
            pass 

        # Render the review page
        return render_template('tools/roster_generator.html', 
                               generated_roster=generated_roster_for_template, 
                               search_sources=search_sources)

    except json.JSONDecodeError as e:
        flash(f"AI response was not valid JSON. Error: {e}. Raw response: {ai_content[:500]}...", "danger")
        return redirect(url_for('tools.ai_roster_generator_form'))
    except litellm.exceptions.APIError as e:
        flash(f"AI API Error: {e}. Please check your API key and model configuration.", "danger")
        return redirect(url_for('tools.ai_roster_generator_form'))
    except Exception as e:
        flash(f"An unexpected error occurred: {e}", "danger")
        return redirect(url_for('tools.ai_roster_generator_form'))

@tools_bp.route('/commit-roster', methods=['POST'])
def commit_roster():
    """
    Commits selected wrestlers from the generated roster to the database.
    """
    selected_wrestlers_json = request.form.getlist('selected_wrestlers[]')
    
    if not selected_wrestlers_json:
        flash("No wrestlers were selected to commit.", "warning")
        return redirect(url_for('tools.ai_roster_generator_form'))

    successful_adds = 0
    failed_adds = 0
    for wrestler_json_str_encoded in selected_wrestlers_json:
        try:
            # Base64 decode the string, then decode from bytes to utf-8 string, then parse JSON
            decoded_json_bytes = base64.b64decode(wrestler_json_str_encoded)
            wrestler_data = json.loads(decoded_json_bytes.decode('utf-8'))
            if add_wrestler(wrestler_data):
                successful_adds += 1
            else:
                failed_adds += 1
                flash(f"Failed to add wrestler '{wrestler_data.get('Name', 'Unknown')}' (possibly duplicate name).", "warning")
        except (json.JSONDecodeError, base64.binascii.Error) as e:
            failed_adds += 1
            flash(f"Failed to parse wrestler data (JSON or Base64 error): {e} for data: {wrestler_json_str_encoded[:50]}...", "danger")
        except Exception as e:
            failed_adds += 1
            flash(f"Error adding wrestler: {e} for data: {wrestler_json_str_encoded[:50]}...", "danger")

    if successful_adds > 0:
        flash(f"Successfully added {successful_adds} wrestler(s) to the roster!", "success")
    if failed_adds > 0:
        flash(f"{failed_adds} wrestler(s) could not be added.", "warning")

    return redirect(url_for('wrestlers.list_wrestlers'))

@tools_bp.route('/backup_data', methods=['GET'])
def backup_data():
    """Handles the backup of all league data."""
    try:
        root_path = get_project_root()
        data_path = os.path.join(root_path, DATA_DIR)
        
        if not os.path.exists(data_path):
            flash("No data directory found to backup.", "danger")
            return redirect(url_for('tools.backup_restore'))

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_filename = f"slamsim_backup_{timestamp}" # No .zip extension here for make_archive
        
        # Create the zip archive
        # shutil.make_archive(base_name, format, root_dir, base_dir)
        # base_name: The name of the archive file to create, including the path, but without the .zip extension.
        # format: The archive format, e.g., 'zip'.
        # root_dir: The directory from which to start archiving.
        # base_dir: The directory that will be archived.
        archive_path = shutil.make_archive(
            os.path.join(root_path, backup_filename), # Archive will be created in root_path
            'zip',
            root_path, # Start archiving from the project root
            DATA_DIR    # Archive the 'data' directory relative to root_path
        )

        flash("League data backed up successfully!", "success")
        return send_file(archive_path, as_attachment=True, download_name=os.path.basename(archive_path))

    except Exception as e:
        flash(f"Error creating backup: {e}", "danger")
        return redirect(url_for('tools.backup_restore'))

@tools_bp.route('/restore_data', methods=['POST'])
def restore_data():
    """Handles the restoration of league data from a backup file."""
    if 'backup_file' not in request.files:
        flash('No file part', 'danger')
        return redirect(url_for('tools.backup_restore'))
    
    file = request.files['backup_file']
    if file.filename == '':
        flash('No selected file', 'danger')
        return redirect(url_for('tools.backup_restore'))

    if file and file.filename.endswith('.zip'):
        root_path = get_project_root()
        data_path = os.path.join(root_path, DATA_DIR)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        old_data_path = f"{data_path}_old_{timestamp}"
        temp_zip_path = os.path.join(root_path, f"temp_restore_{timestamp}.zip") # Unique temp name

        try:
            # 1. Save the uploaded zip file temporarily
            file.save(temp_zip_path)

            # 2. Rename existing data directory as a safeguard
            if os.path.exists(data_path):
                shutil.move(data_path, old_data_path)
                flash(f"Existing data moved to '{os.path.basename(old_data_path)}' as a safeguard.", "info")
            
            # 3. Create a new, empty data directory
            os.makedirs(data_path, exist_ok=True)
            
            # 4. Unzip the contents of the uploaded file into the new data directory
            with zipfile.ZipFile(temp_zip_path, 'r') as zip_ref:
                # Check if the zip contains a 'data/' directory at its root
                # If so, extract to root_path so 'data/' is created correctly
                namelist = zip_ref.namelist()
                if any(name.startswith(f'{DATA_DIR}/') for name in namelist):
                    zip_ref.extractall(root_path)
                else:
                    # Otherwise, extract directly into the new data_path
                    zip_ref.extractall(data_path)

            # 5. Clean up temporary files and old data directory
            os.remove(temp_zip_path)
            if os.path.exists(old_data_path):
                shutil.rmtree(old_data_path) # Remove the old data directory after successful restore
            
            # 6. Clear any temporary files generated by the application
            delete_all_temporary_files()

            flash('League data restored successfully!', 'success')
            return redirect(url_for('booker.dashboard'))

        except zipfile.BadZipFile:
            flash('Invalid backup file. Please upload a valid .zip file.', 'danger')
            # Attempt to revert if extraction failed due to bad zip
            if os.path.exists(data_path):
                shutil.rmtree(data_path) # Remove the incomplete new data dir
            if os.path.exists(old_data_path):
                shutil.move(old_data_path, data_path) # Restore old data
                flash("Attempted to restore previous data due to invalid backup file.", "info")
        except Exception as e:
            flash(f'Error restoring data: {e}. Please check the "{os.path.basename(old_data_path)}" directory for manual recovery.', 'danger')
            # If any other error, ensure old data is preserved and new (potentially corrupt) data is removed
            if os.path.exists(data_path):
                shutil.rmtree(data_path) # Remove the incomplete new data dir
            if os.path.exists(old_data_path) and not os.path.exists(data_path): # Only move back if data_path is truly gone
                shutil.move(old_data_path, data_path) # Restore old data
                flash("Attempted to restore previous data due to restoration error.", "info")
        finally:
            if os.path.exists(temp_zip_path):
                os.remove(temp_zip_path)
    else:
        flash('Invalid file type. Please upload a .zip file.', 'danger')
    
    return redirect(url_for('tools.backup_restore'))

@tools_bp.route('/generate_static_site', methods=['POST'])
def generate_static_site_route():
    """Triggers the generation of a static Fan Mode site."""
    try:
        # Pass the current Flask app instance to the generator function
        zip_file_path = generate_static_site(current_app)
        zip_filename = os.path.basename(zip_file_path)
        download_url = url_for('tools.download_static_site', filename=zip_filename)
        flash(f"Static Fan Mode site generated successfully! You can download it <a href='{download_url}' class='alert-link'>{zip_filename}</a>.", "success")
        return redirect(url_for('tools.tools_main'))
    except Exception as e:
        flash(f"Error generating static site: {e}", "danger")
        return redirect(url_for('tools.tools_main'))

@tools_bp.route('/download_static_site/<filename>')
def download_static_site(filename):
    """Allows downloading of previously generated static site zip files."""
    zip_storage_path = os.path.join(get_project_root(), STATIC_SITE_ZIP_DIR_NAME)
    file_path = os.path.join(zip_storage_path, filename)
    if os.path.exists(file_path) and filename.endswith('.zip'):
        return send_file(file_path, as_attachment=True, download_name=filename)
    else:
        flash("File not found or invalid.", "danger")
        return redirect(url_for('tools.tools_main'))

@tools_bp.route('/delete_static_site_zip/<filename>', methods=['POST'])
def delete_static_site_zip(filename):
    """Deletes a generated static site zip file."""
    zip_storage_path = os.path.join(get_project_root(), STATIC_SITE_ZIP_DIR_NAME)
    file_path = os.path.join(zip_storage_path, filename)
    if os.path.exists(file_path) and filename.endswith('.zip'):
        try:
            os.remove(file_path)
            flash(f"Deleted '{filename}'.", "success")
        except OSError as e:
            flash(f"Error deleting file: {e}", "danger")
    else:
        flash("File not found or invalid.", "danger")
    return redirect(url_for('tools.tools_main'))
