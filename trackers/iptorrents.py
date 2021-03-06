import datetime
import logging

import config
import db
import radarr
import utils

cfg = config.init()

############################################################
# Tracker Configuration
############################################################
name = "IPTorrents"
irc_host = "irc.iptorrents.com"
irc_port = 6697
irc_channel = "#ipt.announce"
irc_tls = True
irc_tls_verify = False

# these are loaded by init
auth_key = None
torrent_pass = None

logger = logging.getLogger(name.upper())
logger.setLevel(logging.DEBUG)


############################################################
# Tracker Framework (all trackers must follow)
############################################################
# Parse announcement message
@db.db_session
def parse(announcement):
    global name

    if '[Movie/' not in announcement:
        return
    decolored = utils.strip_irc_color_codes(announcement)

    # extract required information from announcement
    torrent_title = utils.substr(decolored, '] ', ' - http', True)
    torrent_id = utils.get_id(decolored, 0)

    # pass announcement to radarr
    if torrent_id is not None and torrent_title is not None:
        download_link = get_torrent_link(torrent_id, utils.replace_spaces(torrent_title, '.'))

        announced = db.Announced(date=datetime.datetime.now(), title=utils.replace_spaces(torrent_title, '.'),
                                 indexer=name, torrent=download_link)
        approved = radarr.wanted(torrent_title, download_link, name)
        if approved:
            logger.debug("Radarr approved release: %s", torrent_title)
            snatched = db.Snatched(date=datetime.datetime.now(), title=utils.replace_spaces(torrent_title, '.'),
                                   indexer=name, torrent=download_link)
        else:
            logger.debug("Radarr rejected release: %s", torrent_title)


# Generate torrent link
def get_torrent_link(torrent_id, torrent_name):
    torrent_link = "https://iptorrents.com/download.php/{}/{}.torrent?torrent_pass={}".format(torrent_id,
                                                                                              torrent_name,
                                                                                              torrent_pass)
    return torrent_link


# Initialize tracker
def init():
    global auth_key, torrent_pass

    auth_key = cfg["{}.auth_key".format(name.lower())]
    torrent_pass = cfg["{}.torrent_pass".format(name.lower())]

    # check torrent_pass was supplied
    if not torrent_pass:
        return False

    return True
