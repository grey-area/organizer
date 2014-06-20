import os
import filecmp
import datetime
import shutil

def backup():
    if not os.path.exists('./backup'):
        os.makedirs('./backup')

    backups = sorted(os.listdir('./backup'))
    if len(backups) == 0:
        unchanged = False
    else:
        unchanged = filecmp.cmp('./tasks.db','./backup/' + backups[-1])

    if not unchanged:

        # If there are more than 30 backups, remove the earliest
        end = max(len(backups) - 30, 0)
        for b in backups[:end]:
            os.remove('./backup/' + b)

        # Make a new backup
        now = datetime.datetime.now()
        newFilename = ""
        if now.month < 10:
            newFilename += "0"
        newFilename += str(now.month)
        if now.day < 10:
            newFilename += "0"
        newFilename += str(now.day) + "-"
        if now.hour < 10:
            newFilename += "0"
        newFilename += str(now.hour) + ".db"

        shutil.copy('./tasks.db', './backup/' + newFilename)
