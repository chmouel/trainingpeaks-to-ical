# -*- coding: utf-8 -*-
# Author: Chmouel Boudjnah <chmouel@chmouel.com>
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.
import datetime
import humanfriendly
import json
import glob
import os
import ics
import dateutil.parser
import dateutil.relativedelta
import locale
import subprocess

import tp

import sys

reload(sys)
sys.setdefaultencoding('utf8')

TITLE = "Toursnman2019"
DEBUT = '30 December 2018'
PERIOD_MONTHS = 7
GARMIN_EXPORT_PATH = "/tmp/" + TITLE + "-Training"
REMOTEW = "http://chmouel.com" + GARMIN_EXPORT_PATH

VALUES = {
    1: 'Swim',
    2: 'Bike',
    3: 'Run',
    7: 'Rest',
    9: 'Strength',
    10: 'Instructions',
    100: 'Other'
}

def main(content, tpcnx):
    ret = json.loads(content)

    #calendar = ics.Calendar()
    events = []
    for current in ret:
        dt = dateutil.parser.parse(current['workoutDay'])
        dd = dateutil.parser.parse(DEBUT)
        if not dt > dd:
            continue

        if not current['workoutTypeValueId'] in VALUES:
            continue

        event = ics.Event()
        if current['title']:
            event.name = current['title']
        else:
            event.name = ""
        event.description = ""
        if current['totalTimePlanned']:
            event.name += " " + humanfriendly.format_timespan(
                current['totalTimePlanned'] * (60 * 60))
            event.duration = datetime.timedelta(
                seconds=current['totalTimePlanned'] * (60 * 60))

        if current['description']:
            event.description = current['description'].replace('\r', '\n')

        if current['coachComments']:
            event.description += "\n\nCommentaire du Coach:\n"
            event.description += current['coachComments'].replace('\r', '\n')

        if current['structure']:
            title = current['title']
            fitfile = dt.strftime("%Y-%m-%d")
            if title:
                suffix = bytes(current['title'].replace(" ", "")[:10])
                fitfile += "_" + suffix
            fitfile += ".fit"
            localfitfile = os.path.join(GARMIN_EXPORT_PATH, fitfile)

            if not os.path.exists(localfitfile):
                r = tpcnx.session.get(
                    'https://tpapi.trainingpeaks.com/fitness/v1/athletes/' +
                    str(tpcnx.athlete_id) + '/workouts/' +
                    str(current['workoutId']) + '/fordevice/fit',
                    stream=True
                )
                if r.status_code == 200:
                    with open(localfitfile, 'wb') as f:
                        for chunk in r:
                            f.write(chunk)

            if event.description:
                event.description += "\n\nFichier pour Garmin:\n"
                event.description += REMOTEW + "/" + fitfile

        event.begin = dt.replace(hour=6, minute=00)
        events.append(event)

    output = str(ics.Calendar(events=events))
    open(os.path.join(GARMIN_EXPORT_PATH, TITLE + "-Training.ics"), 'w').write(output)
    print "Wrote: " + os.path.join(GARMIN_EXPORT_PATH, TITLE + "-Training.ics")
    os.system("rsync -avuz %s chmouel.com:/home/www/chmouel.com/tmp/" %
              (GARMIN_EXPORT_PATH))
    print (REMOTEW + "/" + TITLE + "-Training.ics")

if __name__ == '__main__':
    username = 'chmouel'
    password = subprocess.Popen(
        ["security", "find-generic-password", "-a",
         "chmouel", "-s", "trainingpeaks", "-w"],
        stdout=subprocess.PIPE
    ).communicate()[0].strip()

    if not os.path.exists(GARMIN_EXPORT_PATH):
        os.makedirs(GARMIN_EXPORT_PATH)
    back = dateutil.parser.parse(DEBUT)
    front = (back + dateutil.relativedelta.relativedelta(months=+6))
    front = front.strftime("%Y-%m-%d")
    back = back.strftime("%Y-%m-%d")
    tpconnect = tp.TPconnect(username, password)
    content = tpconnect.get_workouts(dateoptions={'back': back, 'front': front})
    main(content, tpcnx=tpconnect)
