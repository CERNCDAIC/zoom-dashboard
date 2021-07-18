import logging

from flask import Flask

from services.zoom import live_events, past_participants, add_registrant_onevent, list_registrants_onevent
from services.webinarmgmt import set_zoom_webinar,last_zoom_webinar, get_members_add_member, list_webinars, global_action
from utils.logger import setup_logs

app = Flask(__name__)

app.config['LOG_LEVEL'] = 'DEV'
setup_logs(app, 'zoom-dashboard', to_stdout=True, to_file=True)
logger = logging.getLogger('zoom-dashboard')


@app.route('/')
def hello_world():
    return 'Hello, World!'

#
# Add the Command Line commands
#
app.cli.add_command(live_events)
app.cli.add_command(past_participants)
app.cli.add_command(add_registrant_onevent)
app.cli.add_command(list_registrants_onevent)
app.cli.add_command(set_zoom_webinar)
app.cli.add_command(last_zoom_webinar)
app.cli.add_command(get_members_add_member)
app.cli.add_command(list_webinars)
app.cli.add_command(global_action)