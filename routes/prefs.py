import os
import json # Import json
from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app
from werkzeug.utils import secure_filename
from dotenv import load_dotenv, set_key # Import dotenv functions
from src.prefs import load_preferences, save_preferences, load_fan_home_custom_text, save_fan_home_custom_text
from src.wrestlers import reset_all_wrestler_records
from src.tagteams import reset_all_tagteam_records, recalculate_all_tagteam_weights
from src.system import delete_all_temporary_files, get_league_logo_path, LEAGUE_LOGO_FILENAME, INCLUDES_DIR, get_project_root
from src.date_utils import get_current_working_date

# Load environment variables from .env file
load_dotenv()

prefs_bp = Blueprint('prefs', __name__, url_prefix='/prefs')

API_PROVIDERS_FILE_RELATIVE_TO_ROOT = 'includes/api_providers.json'

def _get_api_providers_file_path():
    """Constructs the absolute path to the API providers configuration file."""
    return os.path.join(get_project_root(), API_PROVIDERS_FILE_RELATIVE_TO_ROOT)

def _load_raw_api_providers_config():
    """Loads the raw API providers configuration as a list of dictionaries."""
    file_path = _get_api_providers_file_path()
    if os.path.exists(file_path):
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                raw_config = json.load(f).get('providers', [])
                return raw_config
        except json.JSONDecodeError:
            print(f"Error decoding JSON from {file_path}. Returning empty list.")
            return []
    return []

def _save_api_providers_config(providers_list):
    """Saves the API providers configuration to the JSON file."""
    file_path = _get_api_providers_file_path()
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump({"providers": providers_list}, f, indent=4)

def _load_api_providers_config():
    """Loads the API providers and models from the JSON configuration file, transformed for template use."""
    raw_config = _load_raw_api_providers_config()
    providers_dict = {}
    for provider in raw_config:
        providers_dict[provider['name']] = provider['models']
    return providers_dict

@prefs_bp.route('/preferences', methods=['GET', 'POST'])
def general_prefs():
    prefs = load_preferences() # Load prefs from data/prefs.json
    all_available_models = _load_api_providers_config() # Load from JSON config

    # Check if API keys are set in environment variables
    google_key_is_set = bool(os.getenv('SLAMSIM_GOOGLE_KEY'))
    openai_key_is_set = bool(os.getenv('SLAMSIM_OPENAI_KEY')) # Check SLAMSIM_OPENAI_KEY

    # Set default values for preferences if they are not already set
    prefs.setdefault('league_name', 'My Awesome League')
    prefs.setdefault('league_short', 'MAL')
    prefs.setdefault('fan_mode_show_logo', False)
    prefs.setdefault('fan_mode_header_name_display', 'Full Name')
    prefs.setdefault('fan_mode_show_records', False)
    prefs.setdefault('fan_mode_show_profile_records', False)
    prefs.setdefault('fan_mode_show_contract_info', False)
    prefs.setdefault('fan_mode_roster_sort_order', 'Alphabetical')
    prefs.setdefault('fan_mode_roster_record_type', 'Singles')
    prefs.setdefault('fan_mode_show_future_events', False)
    prefs.setdefault('fan_mode_show_non_match_headers', False)
    prefs.setdefault('fan_mode_show_event_card', True) # New preference
    prefs.setdefault('fan_mode_show_quick_results', False)
    prefs.setdefault('fan_mode_home_show_champions', False)
    prefs.setdefault('fan_mode_home_show_news', 'Show Links Only')
    prefs.setdefault('fan_mode_home_number_news', 5)
    prefs.setdefault('fan_mode_home_show_recent_events', False)
    prefs.setdefault('fan_mode_home_number_events', 5)
    prefs.setdefault('fan_mode_injured_wrestler_display', 'Show Normally')
    prefs.setdefault('fan_mode_suspended_roster_display', 'Show Normally')
    prefs.setdefault('ai_provider', '')
    prefs.setdefault('ai_model', '')
    prefs.setdefault('game_date_mode', 'real-time')
    prefs.setdefault('game_date', get_current_working_date().isoformat()) # Ensure game_date has a default
    prefs.setdefault('weight_unit', 'lbs.')

    fan_home_custom_text = load_fan_home_custom_text()

    if request.method == 'POST':
        # When processing POST, retrieve values from form, using current prefs as fallback for non-submitted fields
        league_name = request.form.get('league_name', prefs.get('league_name', '')).strip()
        league_short = request.form.get('league_short', '').strip()
        fan_mode_show_logo = 'fan_mode_show_logo' in request.form
        fan_mode_header_name_display = request.form.get('fan_mode_header_name_display', 'Full Name')
        fan_mode_show_records = 'fan_mode_show_records' in request.form
        fan_mode_show_profile_records = 'fan_mode_show_profile_records' in request.form
        fan_mode_show_contract_info = 'fan_mode_show_contract_info' in request.form
        fan_mode_roster_sort_order = request.form.get('fan_mode_roster_sort_order', 'Alphabetical')
        fan_mode_roster_record_type = request.form.get('fan_mode_roster_record_type', 'Singles')
        fan_mode_show_future_events = 'fan_mode_show_future_events' in request.form
        fan_mode_show_non_match_headers = 'fan_mode_show_non_match_headers' in request.form
        fan_mode_show_event_card = 'fan_mode_show_event_card' in request.form # New preference
        fan_mode_show_quick_results = 'fan_mode_show_quick_results' in request.form
        fan_mode_home_show_champions = 'fan_mode_home_show_champions' in request.form
        fan_mode_home_show_news = request.form.get('fan_mode_home_show_news', 'Show Links Only')
        fan_mode_home_number_news = int(request.form.get('fan_mode_home_number_news', 5))
        fan_mode_home_show_recent_events = 'fan_mode_home_show_recent_events' in request.form
        fan_mode_home_number_events = int(request.form.get('fan_mode_home_number_events', 5))

        fan_mode_injured_wrestler_display = request.form.get('fan_mode_injured_wrestler_display', 'Show Normally')
        fan_mode_suspended_roster_display = request.form.get('fan_mode_suspended_roster_display', 'Show Normally')

        ai_provider = request.form.get('ai_provider', '')
        ai_model = request.form.get('ai_model', '')
        
        # Get API keys from form, but do not store them in updated_prefs for prefs.json
        google_api_key_from_form = request.form.get('google_api_key', '')
        openai_api_key_from_form = request.form.get('openai_api_key', '')

        game_date_mode = request.form.get('game_date_mode', 'real-time')
        weight_unit = request.form.get('weight_unit', 'lbs.')

        new_fan_home_custom_text = request.form.get('fan_home_custom_text', '')

        updated_prefs = {
            "league_name": league_name,
            "league_short": league_short,
            "fan_mode_show_logo": fan_mode_show_logo,
            "fan_mode_header_name_display": fan_mode_header_name_display,
            "fan_mode_show_records": fan_mode_show_records,
            "fan_mode_show_profile_records": fan_mode_show_profile_records,
            "fan_mode_show_contract_info": fan_mode_show_contract_info,
            "fan_mode_roster_sort_order": fan_mode_roster_sort_order,
            "fan_mode_roster_record_type": fan_mode_roster_record_type,
            "fan_mode_show_future_events": fan_mode_show_future_events,
            "fan_mode_show_non_match_headers": fan_mode_show_non_match_headers,
            "fan_mode_show_event_card": fan_mode_show_event_card, # New preference
            "fan_mode_show_quick_results": fan_mode_show_quick_results,
            "fan_mode_home_show_champions": fan_mode_home_show_champions,
            "fan_mode_home_show_news": fan_mode_home_show_news,
            "fan_mode_home_number_news": fan_mode_home_number_news,
            "fan_mode_home_show_recent_events": fan_mode_home_show_recent_events,
            "fan_mode_home_number_events": fan_mode_home_number_events,
            "fan_mode_injured_wrestler_display": fan_mode_injured_wrestler_display,
            "fan_mode_suspended_roster_display": fan_mode_suspended_roster_display,
            "ai_provider": ai_provider,
            "ai_model": ai_model,
            # API keys are no longer stored in prefs.json
            "game_date_mode": game_date_mode,
            "game_date": prefs.get("game_date"),
            "weight_unit": weight_unit
        }
        save_preferences(updated_prefs)
        save_fan_home_custom_text(new_fan_home_custom_text)

        # Update API keys in .env file only if provided in the form
        if google_api_key_from_form:
            set_key('.env', 'SLAMSIM_GOOGLE_KEY', google_api_key_from_form)
        if openai_api_key_from_form:
            set_key('.env', 'SLAMSIM_OPENAI_KEY', openai_api_key_from_form) # Set SLAMSIM_OPENAI_KEY

        # Handle logo upload
        if 'league_logo' in request.files:
            file = request.files['league_logo']
            if file.filename != '':
                os.makedirs(os.path.join(current_app.root_path, INCLUDES_DIR), exist_ok=True)
                filename = secure_filename(LEAGUE_LOGO_FILENAME)
                file_path = os.path.join(current_app.root_path, INCLUDES_DIR, filename)
                file.save(file_path)
                flash('League logo uploaded successfully!', 'success')
            
        # Handle logo deletion
        if request.form.get('delete_logo') == 'on':
            logo_path = get_league_logo_path()
            if os.path.exists(logo_path):
                os.remove(logo_path)
                flash('League logo deleted successfully!', 'success')

        flash('Preferences updated successfully!', 'success')
        return redirect(url_for('prefs.general_prefs'))
    
    league_logo_url = None
    if os.path.exists(get_league_logo_path()):
        league_logo_url = url_for('static', filename=f'{INCLUDES_DIR}/{LEAGUE_LOGO_FILENAME}')

    current_game_date = get_current_working_date().isoformat()

    return render_template('booker/prefs.html', prefs=prefs, league_logo_url=league_logo_url, available_models=all_available_models, current_game_date=current_game_date, fan_home_custom_text=fan_home_custom_text, google_key_is_set=google_key_is_set, openai_key_is_set=openai_key_is_set)

@prefs_bp.route('/api_providers', methods=['GET'])
def manage_api_providers():
    providers = _load_raw_api_providers_config()
    return render_template('booker/manage_api_providers.html', providers=providers)

@prefs_bp.route('/api_providers/add_provider', methods=['POST'])
def add_api_provider():
    provider_name = request.form.get('provider_name').strip()
    if not provider_name:
        flash('Provider name cannot be empty.', 'danger')
        return redirect(url_for('prefs.manage_api_providers'))

    providers = _load_raw_api_providers_config()
    if any(p['name'].lower() == provider_name.lower() for p in providers):
        flash(f'Provider "{provider_name}" already exists.', 'danger')
        return redirect(url_for('prefs.manage_api_providers'))

    providers.append({"name": provider_name, "models": []})
    _save_api_providers_config(providers)
    flash(f'Provider "{provider_name}" added successfully!', 'success')
    return redirect(url_for('prefs.manage_api_providers'))

@prefs_bp.route('/api_providers/add_model/<string:provider_name>', methods=['POST'])
def add_api_model(provider_name):
    model_id = request.form.get('model_id').strip()
    model_name = request.form.get('model_name').strip()

    if not model_id or not model_name:
        flash('Model ID and Name cannot be empty.', 'danger')
        return redirect(url_for('prefs.manage_api_providers'))

    providers = _load_raw_api_providers_config()
    for provider in providers:
        if provider['name'] == provider_name:
            if any(m['id'].lower() == model_id.lower() for m in provider['models']):
                flash(f'Model ID "{model_id}" already exists for {provider_name}.', 'danger')
                return redirect(url_for('prefs.manage_api_providers'))
            provider['models'].append({"id": model_id, "name": model_name})
            _save_api_providers_config(providers)
            flash(f'Model "{model_name}" added to {provider_name} successfully!', 'success')
            return redirect(url_for('prefs.manage_api_providers'))
    
    flash(f'Provider "{provider_name}" not found.', 'danger')
    return redirect(url_for('prefs.manage_api_providers'))

@prefs_bp.route('/api_providers/edit_provider/<string:original_provider_name>', methods=['POST'])
def edit_api_provider(original_provider_name):
    new_provider_name = request.form.get('new_provider_name').strip()
    if not new_provider_name:
        flash('Provider name cannot be empty.', 'danger')
        return redirect(url_for('prefs.manage_api_providers'))

    providers = _load_raw_api_providers_config()
    found = False
    for provider in providers:
        if provider['name'] == original_provider_name:
            if any(p['name'].lower() == new_provider_name.lower() for p in providers if p['name'] != original_provider_name):
                flash(f'Provider "{new_provider_name}" already exists.', 'danger')
                return redirect(url_for('prefs.manage_api_providers'))
            provider['name'] = new_provider_name
            found = True
            break
    
    if found:
        _save_api_providers_config(providers)
        flash(f'Provider "{original_provider_name}" updated to "{new_provider_name}" successfully!', 'success')
    else:
        flash(f'Provider "{original_provider_name}" not found.', 'danger')
    return redirect(url_for('prefs.manage_api_providers'))

@prefs_bp.route('/api_providers/edit_model/<string:provider_name>/<string:original_model_id>', methods=['POST'])
def edit_api_model(provider_name, original_model_id):
    new_model_id = request.form.get('new_model_id').strip()
    new_model_name = request.form.get('new_model_name').strip()

    if not new_model_id or not new_model_name:
        flash('Model ID and Name cannot be empty.', 'danger')
        return redirect(url_for('prefs.manage_api_providers'))

    providers = _load_raw_api_providers_config()
    found_provider = False
    found_model = False
    for provider in providers:
        if provider['name'] == provider_name:
            found_provider = True
            for model in provider['models']:
                if model['id'] == original_model_id:
                    if any(m['id'].lower() == new_model_id.lower() for m in provider['models'] if m['id'] != original_model_id):
                        flash(f'Model ID "{new_model_id}" already exists for {provider_name}.', 'danger')
                        return redirect(url_for('prefs.manage_api_providers'))
                    model['id'] = new_model_id
                    model['name'] = new_model_name
                    found_model = True
                    break
            break
    
    if found_provider and found_model:
        _save_api_providers_config(providers)
        flash(f'Model "{original_model_id}" updated to "{new_model_id}" for {provider_name} successfully!', 'success')
    else:
        flash(f'Model "{original_model_id}" not found for provider "{provider_name}".', 'danger')
    return redirect(url_for('prefs.manage_api_providers'))

@prefs_bp.route('/api_providers/delete_provider/<string:provider_name>', methods=['POST'])
def delete_api_provider(provider_name):
    providers = _load_raw_api_providers_config()
    original_len = len(providers)
    providers = [p for p in providers if p['name'] != provider_name]
    
    if len(providers) < original_len:
        _save_api_providers_config(providers)
        flash(f'Provider "{provider_name}" deleted successfully!', 'success')
    else:
        flash(f'Provider "{provider_name}" not found.', 'danger')
    return redirect(url_for('prefs.manage_api_providers'))

@prefs_bp.route('/api_providers/delete_model/<string:provider_name>/<string:model_id>', methods=['POST'])
def delete_api_model(provider_name, model_id):
    providers = _load_raw_api_providers_config()
    found_provider = False
    found_model = False
    for provider in providers:
        if provider['name'] == provider_name:
            found_provider = True
            original_len = len(provider['models'])
            provider['models'] = [m for m in provider['models'] if m['id'] != model_id]
            if len(provider['models']) < original_len:
                found_model = True
            break
    
    if found_provider and found_model:
        _save_api_providers_config(providers)
        flash(f'Model "{model_id}" deleted from {provider_name} successfully!', 'success')
    else:
        flash(f'Model "{model_id}" not found for provider "{provider_name}".', 'danger')
    return redirect(url_for('prefs.manage_api_providers'))

@prefs_bp.route('/reset-records', methods=['POST'])
def reset_records():
    """Handles the resetting of all wrestler and tag team records."""
    if request.form.get('confirmation') == 'RESET':
        reset_all_wrestler_records()
        reset_all_tagteam_records()
        flash('All wrestler and tag team win/loss records have been reset to 0.', 'success')
    else:
        flash('Confirmation text was incorrect. Records were not reset.', 'danger')
    return redirect(url_for('prefs.general_prefs'))

@prefs_bp.route('/clear-temp-files', methods=['POST'])
def clear_temp_files():
    """Handles the deletion of all temporary files."""
    if request.form.get('confirmation') == 'CLEAR':
        if delete_all_temporary_files():
            flash('All temporary files (segment summaries) have been deleted.', 'success')
        else:
            flash('An error occurred while clearing temporary files.', 'danger')
    else:
        flash('Confirmation text was incorrect. Temporary files were not cleared.', 'danger')
    return redirect(url_for('prefs.general_prefs'))

@prefs_bp.route('/recalculate-tagteam-weights', methods=['POST'])
def recalculate_tagteam_weights_route():
    """Handles the recalculation of all tag team weights."""
    updated_count = recalculate_all_tagteam_weights()
    if updated_count > 0:
        flash(f'Successfully recalculated weights for {updated_count} tag teams.', 'success')
    else:
        flash('No tag team weights needed recalculation.', 'info')
    return redirect(url_for('prefs.general_prefs'))

