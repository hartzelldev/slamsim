import os
from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app
from werkzeug.utils import secure_filename
from dotenv import load_dotenv, set_key # Import dotenv functions
from src.prefs import load_preferences, save_preferences, load_fan_home_custom_text, save_fan_home_custom_text
from src.wrestlers import reset_all_wrestler_records
from src.tagteams import reset_all_tagteam_records, recalculate_all_tagteam_weights
from src.system import delete_all_temporary_files, get_league_logo_path, LEAGUE_LOGO_FILENAME, INCLUDES_DIR
from src.date_utils import get_current_working_date

# Load environment variables from .env file
load_dotenv()

prefs_bp = Blueprint('prefs', __name__, url_prefix='/prefs')

AVAILABLE_MODELS = {
    "Google": ["gemini-2.5-pro", "gemini-2.5-flash"],
    "OpenAI": ["gpt-5.0", "gpt-4.0", "gpt-3.5"]
}

@prefs_bp.route('/preferences', methods=['GET', 'POST'])
def general_prefs():
    prefs = load_preferences() # Load prefs from data/prefs.json

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

    return render_template('booker/prefs.html', prefs=prefs, league_logo_url=league_logo_url, available_models=AVAILABLE_MODELS, current_game_date=current_game_date, fan_home_custom_text=fan_home_custom_text, google_key_is_set=google_key_is_set, openai_key_is_set=openai_key_is_set)

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

