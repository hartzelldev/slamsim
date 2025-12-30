import os
from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app
from werkzeug.utils import secure_filename
from src.prefs import load_preferences, save_preferences
from src.wrestlers import reset_all_wrestler_records
from src.tagteams import reset_all_tagteam_records, recalculate_all_tagteam_weights # Import new function
from src.system import delete_all_temporary_files, get_league_logo_path, LEAGUE_LOGO_FILENAME, INCLUDES_DIR
from src.date_utils import get_current_working_date # Import the new utility

prefs_bp = Blueprint('prefs', __name__, url_prefix='/prefs')

AVAILABLE_MODELS = {
    "Google": ["gemini-2.5-pro", "gemini-2.5-flash"],
    "OpenAI": ["gpt-5.0", "gpt-4.0", "gpt-3.5"]
}

@prefs_bp.route('/preferences', methods=['GET', 'POST'])
def general_prefs():
    prefs = load_preferences() # Load prefs at the beginning to use for both GET and POST

    if request.method == 'POST':
        league_name = request.form.get('league_name', '').strip()
        league_short = request.form.get('league_short', '').strip()
        fan_mode_show_logo = 'fan_mode_show_logo' in request.form # Checkbox returns 'on' if checked, else not in form
        fan_mode_header_name_display = request.form.get('fan_mode_header_name_display', 'Full Name')
        fan_mode_show_records = 'fan_mode_show_records' in request.form
        fan_mode_show_profile_records = 'fan_mode_show_profile_records' in request.form # New preference
        fan_mode_show_contract_info = 'fan_mode_show_contract_info' in request.form # New preference
        fan_mode_roster_sort_order = request.form.get('fan_mode_roster_sort_order', 'Alphabetical')
        fan_mode_show_future_events = 'fan_mode_show_future_events' in request.form
        fan_mode_show_non_match_headers = 'fan_mode_show_non_match_headers' in request.form
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
        google_api_key = request.form.get('google_api_key', '')
        openai_api_key = request.form.get('openai_api_key', '')

        # New Game Date preferences
        game_date_mode = request.form.get('game_date_mode', 'real-time')
        # game_date itself is updated by events/news, not directly here.
        
        # New Weight Unit preference
        weight_unit = request.form.get('weight_unit', 'lbs.')

        updated_prefs = {
            "league_name": league_name,
            "league_short": league_short,
            "fan_mode_show_logo": fan_mode_show_logo,
            "fan_mode_header_name_display": fan_mode_header_name_display,
            "fan_mode_show_records": fan_mode_show_records,
            "fan_mode_show_profile_records": fan_mode_show_profile_records, # New preference
            "fan_mode_show_contract_info": fan_mode_show_contract_info, # New preference
            "fan_mode_roster_sort_order": fan_mode_roster_sort_order,
            "fan_mode_show_future_events": fan_mode_show_future_events,
            "fan_mode_show_non_match_headers": fan_mode_show_non_match_headers,
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
            "google_api_key": google_api_key,
            "openai_api_key": openai_api_key,
            "game_date_mode": game_date_mode, # Save new preference
            "game_date": prefs.get("game_date"), # Preserve existing game_date, it's updated elsewhere
            "weight_unit": weight_unit # Save new weight unit preference
        }
        save_preferences(updated_prefs)

        # Handle logo upload
        if 'league_logo' in request.files:
            file = request.files['league_logo']
            if file.filename != '':
                # Ensure the includes directory exists
                os.makedirs(os.path.join(current_app.root_path, INCLUDES_DIR), exist_ok=True)
                
                # Use the predefined filename for the logo
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
    
    # Check if logo exists to display it
    league_logo_url = None
    if os.path.exists(get_league_logo_path()):
        # Use url_for('static', filename=...) to correctly generate URL for static files
        # The INCLUDES_DIR is relative to the static folder if configured that way,
        # or we might need a custom static endpoint if includes is outside static.
        # For now, assuming 'includes' is directly accessible via static.
        league_logo_url = url_for('static', filename=f'{INCLUDES_DIR}/{LEAGUE_LOGO_FILENAME}')

    current_game_date = get_current_working_date().isoformat() # Get the current working date for display

    return render_template('booker/prefs.html', prefs=prefs, league_logo_url=league_logo_url, available_models=AVAILABLE_MODELS, current_game_date=current_game_date)

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

