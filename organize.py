#!/usr/bin/env python

import sqlite3 as lite
import os, sys, datetime, errno

import curses
import curses.textpad
import subprocess
import shutil
import urllib2
import cookielib
import locale # unicode
locale.setlocale(locale.LC_ALL,"")

import backup

# If the db doesn't exist, create it
if not os.path.isfile('./tasks.db'):
    with lite.connect('./tasks.db') as con:
        cur = con.cursor()

        cur.execute('CREATE TABLE Association (ID1 INT, ID2 INT);')
        cur.execute('CREATE TABLE Authors (Surname TEXT, Forename TEXT);')
        cur.execute('CREATE TABLE HasAuthor (EntryID INT, AuthorID INT);')
        cur.execute('CREATE TABLE Keywords (Keyword TEXT);')
        cur.execute('CREATE TABLE HasKeyword (EntryID INT, KeywordID INT);')
        cur.execute('CREATE TABLE Entries (Title TEXT, Priority INT, Done INT, Deadline TEXT, Notes TEXT, Type TEXT, Active INT, Printed INT, Bibtex TEXT, Location TEXT, CurrentLocation TEXT);')

stdscr = curses.initscr()
curses.start_color()
curses.use_default_colors()

curses.init_pair(1, curses.COLOR_BLACK, -1)
curses.init_pair(2, curses.COLOR_WHITE, curses.COLOR_RED)
if curses.can_change_color():
    curses.init_color(curses.COLOR_YELLOW, 500, 500, 500)
    curses.init_pair(3, curses.COLOR_YELLOW, -1)
else:
    curses.init_pair(3, curses.COLOR_WHITE, -1)
curses.init_pair(4, curses.COLOR_RED, -1)
s_normal = curses.color_pair(1)
s_red = curses.color_pair(4)
s_bold = curses.color_pair(1) | curses.A_BOLD
s_critical = curses.color_pair(2) | curses.A_BOLD
s_dim = curses.color_pair(3)

curses.noecho()
curses.cbreak()
stdscr.keypad(1)

# States
main      = 0
entryView = 1
listView  = 2

state  = [main]

def mkdir_p(path):
    try:
        os.makedirs(path)
    except OSError as exc: # Python >2.5
        if exc.errno == errno.EEXIST and os.path.isdir(path):
            pass
        else: raise

def changePDF(entryID):
    curses.echo()
    addstr("PDF location: ")
    pdfLocation = stdscr.getstr()
    curses.noecho()

    if pdfLocation is not "":
        if pdfLocation.startswith("http"):
            url = pdfLocation
            cj = cookielib.CookieJar()
            opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(cj))
            opener.addheaders.append(('Cookie', cj))
            request = urllib2.Request(url)
            pdf = opener.open(request)
            with open('resources/' + str(entryID) + '/paper.pdf','wb') as f:
                f.write(pdf.read())
            pdf.close()
            opener.close()
        else:
            if '/' not in pdfLocation:
                pdfLocation = '~/Downloads/' + pdfLocation
            if not pdfLocation.endswith(".pdf"):
                pdfLocation += ".pdf"
            shutil.copyfile(os.path.expanduser(pdfLocation), 'resources/' + str(entryID) + '/paper.pdf')

def addstr(string, style=s_normal):
    try:
        stdscr.addstr(string, style)
    except curses.error:
        pass

def nicify(string):
    return string.decode('utf-8').encode("ascii","ignore").replace("'","").replace('"','').replace("`","").replace("\\","")

def enc(string):
    return string.encode('utf-8')

def atoi(string):
    try:
        return int(string)
    except ValueError:
        return -1

def printDate(string):
    if string is "":
        return ""
    else:
        return string[6:10] + "/" + string[4:6] + "/" + string[0:4]

def remainingTime(dlineString):

    today = datetime.datetime.today()
    dline = datetime.datetime.strptime(dlineString,"%Y%m%d")

    timeToStr = ""
    timeTo = (dline-today).days
    critical = timeTo/7 < 2

    if abs(timeTo) < 7:
        frac = str((dline-today).seconds / 86400.0).split(".")[1][0]
        timeToStr = str(timeTo) + "." + frac + " days"
    else:
        frac = str((timeTo/7.0 - timeTo/7)).split(".")[1][0]
        timeToStr = str(timeTo/7) + "." + frac + " weeks"

    return timeToStr, critical

def printRemainingTime(dlineString):
    if dlineString is not "":
        (timeToStr, critical) = remainingTime(dlineString)
        style = s_normal
        if critical:
            style = s_red
        addstr("  @" + timeToStr, style)

def maketextbox(value=""):
    nw = curses.newwin(50,100,1,1)
    #txtbox = curses.textpad.Textbox(stdscr,insert_mode=True)
    txtbox = curses.textpad.Textbox(nw)
    #stdscr.attron(0)
    #curses.textpad.rectangle(stdscr,1,1,30,80)
    #stdscr.attroff(0)
 
    nw.addstr(0,0,value,s_normal)
    nw.attron(s_normal)
    stdscr.refresh()
    return txtbox


entryID = 0
entryType = "Papers"
listStart = 0
showFinished = False
listSearch = ""

def reset():
    global listStart, showFinished, listSearch
    listStart = 0
    showFinished = False
    listSearch = ""

fullBreak = False
clearString = ""

while not fullBreak:
    backup.backup()

    with lite.connect('tasks.db') as con:
        cur = con.cursor()

        while True:
            stdscr.clear()
            addstr(clearString)
            clearString = ""

            if state[-1] == main:

                options = ['`','1','2','3','4','5','6','7','8','9','0','-','=']
                optionNames = ["Paper","Book","Research","Writing & Presentations","Teaching","Outreach","Quick"]

                addstr("Active:\n")
                cur.execute("SELECT ROWID, Type, Title FROM Entries WHERE Active=1 ORDER BY Priority DESC;")
                entries = cur.fetchall()
                for i,entry in enumerate(entries[0:3]):
                    addstr("[" + options[i] + "] - " + enc(entry[1]) + ": " + enc(entry[2])[:55] + "\n")
                addstr("\n")

                addstr("Deadlines:\n")
                cur.execute("SELECT ROWID, Type, Title, Deadline FROM Entries WHERE Done=0 AND Deadline<>'' ORDER BY Deadline ASC;")
                entries2 = cur.fetchall()
                for i,entry in enumerate(entries2[0:3]):
                    addstr("[" + options[i+3] + "] - " + enc(entry[1]) + ": " + enc(entry[2])[:55])
                    printRemainingTime(enc(entry[3]))
                    addstr("\n")
                addstr("\n")

                for i,optionName in enumerate(optionNames):
                    addstr("[" + options[i+6] + "] - " + optionName + "\n")
                addstr("\n[E] - Exit\n")

                stdscr.refresh()
                c = stdscr.getch()



                if c == 27:
                    fullBreak = True
                    break
                elif chr(c) in options:
                    optionIndex = options.index(chr(c))

                    if optionIndex < 3:
                        if optionIndex < len(entries):
                            entryID = entries[optionIndex][0]
                            state.append(entryView)
                    elif optionIndex < 6:
                        if optionIndex-3 < len(entries2):
                            entryID = entries2[optionIndex-3][0]
                            state.append(entryView)
                    else:
                        entryType = optionNames[optionIndex-6]
                        state.append(listView)
                        reset()

            elif state[-1] == entryView:

                cur.execute("SELECT ROWID,Title,Active,Type,Printed,Location,CurrentLocation,Priority,Done,Deadline,Bibtex,Notes FROM Entries WHERE ROWID=" + str(entryID)+";")
                entry = cur.fetchone()
                addstr(enc(entry[1]) + "\t[" + enc(entry[3]) + "]\t\t")
                if entry[2]:
                    addstr("*ACTIVE*", s_critical)
                addstr("\n")

                cur.execute("SELECT Authors.Surname, Authors.Forename FROM Authors, HasAuthor WHERE HasAuthor.EntryID=" + str(entry[0]) + " AND HasAuthor.AuthorID=Authors.ROWID;")
                authors = cur.fetchall()
                first = True
                for author in authors:
                    if not first:
                        addstr(", ")
                    first = False
                    addstr(enc(author[1]) + " " + enc(author[0]) )
                if len(authors) > 0:
                    addstr("\n")
                addstr("\n")

                if str(entry[3]) == "Paper" or str(entry[3]) == "Book":
                    addstr("BiBTeX: " + enc(entry[10]) + "\n")
                if str(entry[3]) == "Paper":
                    if entry[4]:
                        addstr("Location: " + enc(entry[5]) + "\t Current location: " + enc(entry[6]) + "\n\n")
                    else:
                        addstr("Not printed\n\n")
                if entry[8]:
                    addstr("Finished")
                else:
                    addstr("Priority: " + str(entry[7]) + "\t\tDeadline: " + printDate(enc(entry[9])) )
                    printRemainingTime(enc(entry[9]))
                addstr("\n\n")

                addstr("Notes:\n")
                with open('resources/' + str(entryID) + '/notes.md','r') as f:
                    for i,line in enumerate(f):
                        addstr(line)
                        if i>10:
                            break
                addstr("\n")


                options = ["Toggle finished"]
                if not entry[8]:
                    options += ["Toggle active", "Set deadline"]
                options.append("Set title")
                options.append("Set priority")
                if str(entry[3]) == "Paper":
                    options.append("Toggle printed")
                    if entry[4] == 1:
                        options.append("Set location")
                        options.append("Set current location")
                options.append("Edit notes")
                if str(entry[3]) == "Writing & Presentations" or str(entry[3]) == "Research":
                    options.append("Edit associations")
                    options.append("Compile associated notes")
                options.append("Delete entry")

                if str(entry[3]) == "Paper" or str(entry[3]) == "Book":
                    addstr("Keywords: ")
                    cur.execute("SELECT Keywords.Keyword FROM Keywords, HasKeyword WHERE HasKeyword.EntryID=" + str(entry[0]) + " AND HasKeyword.KeywordID=Keywords.ROWID;")
                    keywords = cur.fetchall()
                    first = True
                    for keyword in keywords:
                        if not first:
                            addstr(", ")
                        first = False
                        addstr( enc(keyword[0]) )
                    addstr("\n\n")

                for i, option in enumerate(options):
                    addstr("[" + str(i+1) + "] - " + option + "\n")

                if str(entry[3]) == "Paper" or str(entry[3]) == "Book":
                    addstr("\n[p] - Change PDF\n")
                    if os.path.isfile('resources/' + str(entryID) + '/paper.pdf'):
                        addstr("[v] - View PDF\n")

                addstr("\n[0] - Back\n")
                addstr("[E] - Exit\n\n")

                stdscr.refresh()

                c = stdscr.getch()
                if c == ord("0"):
                    state.pop()
                    break
                elif c == 27:
                    fullBreak = True
                    break
                elif c == ord("p"):
                    changePDF(entryID)
                elif c == ord("v"):
                    subprocess.Popen(["evince", "./resources/" + str(entryID) + "/paper.pdf"])
                elif c>=49 and c<49+len(options):
                    option = options[c-49]
                    if option == "Toggle finished":
                        f = int(not(entry[8]))
                        cur.execute("UPDATE Entries SET Done=" + str(f) + ", Active=0 WHERE ROWID=" + str(entryID) + ";")
                        clearString = "Set entry to "
                        if not f:
                            clearString += "not "
                        clearString += "finished.\n"
                    elif option == "Toggle active":
                        a = int(not(entry[2]))
                        cur.execute("UPDATE Entries SET Active=" + str(a) + " WHERE ROWID=" + str(entryID) + ";")
                        clearString = "Set entry to "
                        if not a:
                            clearString += "in"
                        clearString += "active.\n"

                    elif option == "Set title":
                        curses.echo()
                        addstr("New title: ")
                        newTitle = stdscr.getstr()
                        curses.noecho()
                        if newTitle is not "":
                            cur.execute("UPDATE Entries SET Title='" + newTitle + "' WHERE ROWID=" + str(entryID) + ";")
                            clearString += "Set title to " + newTitle + ".\n"

                    elif option == "Set location":
                        curses.echo()
                        addstr("New location: ")
                        newLocation = stdscr.getstr()
                        curses.noecho()
                        cur.execute("UPDATE Entries SET Location='" + newLocation + "' WHERE ROWID=" + str(entryID) + ";")
                        clearString += "Set location to " + newLocation + ".\n"

                    elif option == "Set current location":
                        curses.echo()
                        addstr("New current location: ")
                        newLocation = stdscr.getstr()
                        curses.noecho()
                        cur.execute("UPDATE Entries SET CurrentLocation='" + newLocation + "' WHERE ROWID=" + str(entryID) + ";")
                        clearString += "Set current location to " + newLocation + ".\n"


                    elif option == "Set priority":
                        curses.echo()
                        newPriority = ""
                        while atoi(newPriority)>10 or atoi(newPriority)<0:
                            addstr("New priority: ")
                            newPriority = stdscr.getstr()
                            if newPriority is "":
                                break
                        curses.noecho()

                        if newPriority is not "":
                            cur.execute("UPDATE Entries SET Priority=" + newPriority + " WHERE ROWID=" + str(entryID) + ";")
                            clearString += "Set priority to " + newPriority + ".\n"

                    elif option == "Set deadline":
                        addstr("New deadline: ")
                        newDeadline = ""
                        while True:
                            c = stdscr.getch()
                            if len(newDeadline) < 10 and c>=48 and c<=57:
                                addstr(chr(c))
                                newDeadline += chr(c)
                                if len(newDeadline) == 2 or len(newDeadline) == 5:
                                    addstr("/")
                                    newDeadline += "/"
                            if c==10:
                                currentDate = datetime.date.today()
                                if len(newDeadline) == 3:
                                    month = str(currentDate.month)
                                    if len(month) == 1:
                                        month = "0" + month
                                    newDeadline += month + "/"
                                if len(newDeadline) == 6:
                                    newDeadline += str(currentDate.year)
                                if len(newDeadline) == 10:
                                    date = newDeadline.split("/")
                                    try:
                                        datetime.datetime(year = int(date[2]), month = int(date[1]), day = int(date[0]))
                                        clearString += "Set deadline to " + newDeadline + ".\n"
                                        cur.execute("UPDATE Entries SET Deadline='" + date[2] + date[1] + date[0] + "' WHERE ROWID=" + str(entryID) + ";")
                                        break
                                    except ValueError:
                                        newDeadline = ""
                                        addstr("\nNew deadline: ")
                                else:
                                    cur.execute("UPDATE Entries SET Deadline='' WHERE ROWID=" + str(entryID) + ";")
                                    break



                    elif option == "Toggle printed":
                        p = int(not(entry[4]))
                        cur.execute("UPDATE Entries SET Printed=" + str(p) + " WHERE ROWID=" + str(entryID) + ";")
                        clearString = "Set entry to "
                        if not p:
                            clearString += "not "
                        clearString += "printed.\n"
                    elif option == "Edit notes":
                        subprocess.Popen(["emacs", "./resources/" + str(entryID) + "/notes.md"])
                        clearString = "Updated notes.\n"

                    elif option == "Edit associations":
                        cur.execute("SELECT ID2 FROM Association WHERE ID1=" + str(entryID) + ";")
                        associated = set([e[0] for e in cur.fetchall()])
                        newAssociated = set(associated)

                        localListSearch = ""
                        localListStart = 0

                        cur.execute("SELECT ROWID, Title, Priority FROM Entries WHERE Type='Paper' OR Type='Book' ORDER BY Priority DESC;")
                        entriesUnfiltered = cur.fetchall()
                        authors = []
                        keywords = []
                        for e in entriesUnfiltered:
                            sqlString = "SELECT Authors.Surname, Authors.Forename FROM Authors, HasAuthor WHERE HasAuthor.EntryID="
                            sqlString += str(e[0])
                            sqlString += " AND HasAuthor.AuthorID=Authors.ROWID;"
                            cur.execute(sqlString)
                            authors.append(cur.fetchall())
                        for e in entriesUnfiltered:
                            sqlString = "SELECT Keywords.Keyword FROM Keywords, HasKeyword WHERE HasKeyword.EntryID="
                            sqlString += str(e[0])
                            sqlString += " AND HasKeyword.KeywordID=Keywords.ROWID;"
                            cur.execute(sqlString)
                            keywords.append(cur.fetchall())
                        authors = [reduce(lambda x,y: x+y[0]+y[1], e, "") for e in authors]
                        keywords = [reduce(lambda x,y: x+y[0], e, "") for e in keywords]


                        while True:
                            stdscr.clear()
                            addstr(str(entry[1]) + "\nEdit associations\n\n")

                            listSearchList = localListSearch.lower().replace("| ","|").replace(" |","|").split("|")
                            entries = [e[0] for e in zip(entriesUnfiltered, authors, keywords) if any([l in e[0][1].lower() for l in listSearchList]) or any([l in e[1].lower() for l in listSearchList]) or any([l in e[2].lower() for l in listSearchList])  ]
                            if localListSearch is not "":
                                addstr("Filter: \"" + localListSearch + "\"\n\n")

                            if localListStart > 0:
                                addstr(" :\n :\n")
                            for i,e in enumerate(entries[localListStart:localListStart+9]):
                                style = s_normal
                                if e[0] in newAssociated:
                                    style = s_bold
                                addstr("[" + str(i+1) + "] - " + str(e[2]) + " " + enc(e[1])[:60], style)
                                addstr("\n")
                            if len(entries) - listStart > 9:
                                addstr(" :\n :\n")
                            addstr("\n")

                            addstr("[^] - Up  [v] - Down")
                            addstr("  [f] - Filter  [Ret] - Done\n\n")

                            stdscr.refresh()
                            c = stdscr.getch()

                            if c==curses.KEY_UP:
                                if localListStart > 0:
                                    localListStart -= 9
                            elif c==curses.KEY_DOWN:
                                if len(entries) - localListStart > 9:
                                    localListStart += 9
                            elif c==ord("f"):
                                addstr("Filter: ")
                                curses.echo()
                                localListSearch = stdscr.getstr()
                                curses.noecho()
                            elif c>=49 and c<=57 and c-49+localListStart < len(entries):
                                toggleID = entries[c-49+localListStart][0]
                                if toggleID in newAssociated:
                                    newAssociated.remove(toggleID)
                                else:
                                    newAssociated.add(toggleID)
                            elif c==10:
                                added = newAssociated - associated
                                removed = associated - newAssociated
                                for assocID in added:
                                    cur.execute("INSERT INTO Association VALUES (" + str(entry[0]) + "," + str(assocID) + ");")
                                for assocID in removed:
                                    cur.execute("DELETE FROM Association WHERE ID1=" + str(entry[0]) + " AND ID2=" + str(assocID) + ";")
                                clearString = "Edited associations.\n"
                                break
                        break # save after adding associations

                    elif option == "Compile associated notes":
                        pass

                    elif option == "Delete entry":
                        curses.echo()
                        addstr("Delete? yes/[no]: ")
                        ans = stdscr.getstr()
                        curses.noecho()
                        if ans == "yes":
                            cur.execute("DELETE FROM Entries WHERE ROWID=" + str(entryID) + ";")
                            state.pop()
                            break


            elif state[-1] == listView:
                addstr(entryType + "\n\n")

                sqlString = "SELECT ROWID, Title, Priority, Active, Done, Deadline FROM Entries WHERE Type='" + entryType + "'"
                if not showFinished:
                    sqlString += " AND Done = 0 "
                sqlString += "ORDER BY Active Desc, Priority DESC;"
                cur.execute(sqlString)
                entries = cur.fetchall()
                authors = []
                keywords = []
                for e in entries:

                    sqlString = "SELECT Authors.Surname, Authors.Forename FROM Authors, HasAuthor WHERE HasAuthor.EntryID="
                    sqlString += str(e[0])
                    sqlString += " AND HasAuthor.AuthorID=Authors.ROWID;"
                    cur.execute(sqlString)
                    authors.append(cur.fetchall())
                for e in entries:
                    sqlString = "SELECT Keywords.Keyword FROM Keywords, HasKeyword WHERE HasKeyword.EntryID="
                    sqlString += str(e[0])
                    sqlString += " AND HasKeyword.KeywordID=Keywords.ROWID;"
                    cur.execute(sqlString)
                    keywords.append(cur.fetchall())
                authors = [reduce(lambda x,y: x+y[0]+y[1], entry, "") for entry in authors]
                keywords = [reduce(lambda x,y: x+y[0], entry, "") for entry in keywords]
                #entries = [e[0] for e in zip(entries, authors, keywords) if listSearch.lower() in e[0][1].lower() or listSearch.lower() in e[1].lower() or listSearch.lower() in e[2].lower()]

                listSearchList = listSearch.lower().replace("| ","|").replace(" |","|").split("|")
                entries = [e[0] for e in zip(entries, authors, keywords) if any([l in e[0][1].lower() for l in listSearchList]) or any([l in e[1].lower() for l in listSearchList]) or any([l in e[2].lower() for l in listSearchList])  ]


                #entries = [e for e in cur.fetchall() if listSearch.lower() in e[1].lower()]

                if listSearch is not "":
                    addstr("Filter: \"" + listSearch + "\"\n\n")

                if listStart > 0:
                    addstr(" :\n :\n")
                for i,entry in enumerate(entries[listStart:listStart+9]):
                    style = s_normal
                    if entry[3]:
                        style = s_bold
                    if entry[4]:
                        style = s_dim
                    addstr("[" + str(i+1) + "] - " + str(entry[2]) + " " + enc(entry[1])[:60], style)
                    printRemainingTime(enc(entry[5]))
                    addstr("\n")

                if len(entries) - listStart > 9:
                    addstr(" :\n :\n")
                addstr("\n")

                addstr("[^] - Up  [v] - Down  [s] - Toggle show finished")
                if entryType is not "Paper" and entryType is not "Book":
                    addstr("  [a] - Add entry")
                else:
                    addstr("  [a] - Add from BiBTeX")
                addstr("  [f] - Filter")
                addstr("\n\n")
                addstr("[0] - Back\n[E] - Exit\n\n")

                stdscr.refresh()
                c = stdscr.getch()

                if c==27:
                    fullBreak = True
                    break
                elif c==ord("0"):
                    state.pop()
                    break
                elif c==curses.KEY_UP:
                    if listStart > 0:
                        listStart -= 9
                elif c==curses.KEY_DOWN:
                    if len(entries) - listStart > 9:
                        listStart += 9
                elif c>=49 and c<=57 and c-49+listStart < len(entries):
                    entryID = entries[c-49+listStart][0]
                    state.append(entryView)
                elif c==ord("s"):
                    showFinished = not showFinished
                elif c==ord("f"):
                    addstr("Filter: ")
                    curses.echo()
                    listSearch = stdscr.getstr()
                    curses.noecho()
                elif c==ord("a") and entryType is not "Paper" and entryType is not "Book":
                    addstr("Add entry\n\nTitle: ")
                    curses.echo()
                    title = stdscr.getstr()
                    priority = ""
                    while atoi(priority)>10 or atoi(priority)<0:
                        addstr("Priority: ")
                        priority = stdscr.getstr()
                    curses.noecho()
                    clearString = "Added entry.\n"
                    cur.execute("INSERT INTO Entries (Title, Priority, Type, Active, Done, Deadline, Notes) VALUES ('" + title + "', " + priority + ", '" + entryType + "', 0, 0, '', '')")

                    newEntryID = cur.lastrowid
                    mkdir_p('resources/' + str(newEntryID))
                    with open('resources/' + str(newEntryID) + '/notes.md','w') as f:
                        pass

                    break
                elif c==ord("a"):
                    cur.execute("SELECT Bibtex FROM Entries")
                    extantKeys = set([b[0] for b in cur.fetchall()])
                    bibEntries = (open('../texinputs/sr.bib', 'r').read()).split('@')
                    newEntries = []
                    for bibEntry in bibEntries[1:]:

                        newEntry = {}
                        lines = bibEntry.split('\n')

                        first = lines[0].split('{')
                        newEntry['Bibtex'] = first[1][:-1]
                        if newEntry['Bibtex'] not in extantKeys:
                            newEntry['Type'] = "Paper"
                            if first[0]=="book":
                                newEntry['Type'] = "Book"
                            for line in lines[1:]:
                                attribute = line.split('=')
                                if len(attribute) == 2:
                                    key = attribute[0].replace(" ", "")
                                    value = attribute[1].replace("{", "").replace("}", "")
                                    if value[-1] == ',':
                                        value = value[:-1]
                                    if key == "title":
                                        newEntry['Title'] = nicify(value)
                                    elif key == "author":
                                        authors = value.split(" and ")
                                        authors = [{"Surname":nicify(author.split(", ")[0]), "Forename":nicify(author.split(", ")[1])} for author in authors if len(author.split(", "))==2]
                                        newEntry["Authors"] = authors

                            newEntries.append(newEntry)

                    stop = False
                    for entry in newEntries:

                        if stop:
                            break

                        addState = 0
                        addListStart = 0
                        entry['Keywords'] = set()
                        entry['Location'] = ""
                        entry['CurrentLocation'] = ""

                        newEntryID = -1

                        while True:
                            stdscr.clear()
                            addstr("Adding from BiBTeX\n\n")
                            addstr("Title: " + entry['Title'] + " (" + entry['Type'] + ")" + "\n")
                            if len(entry['Authors']) > 0:
                                addstr("First author: " + entry['Authors'][0]['Forename'] + " " + entry['Authors'][0]['Surname'] + "\n")
                            addstr("\n")

                            if addState==0:
                                curses.echo()
                                newPriority = ""
                                while atoi(newPriority)>10 or atoi(newPriority)<0:
                                    addstr("New priority: ")
                                    newPriority = stdscr.getstr()
                                    if newPriority == "":
                                        break
                                curses.noecho()
                                if newPriority == "":
                                    stop = True
                                    break
                                entry['Priority'] = atoi(newPriority)
                                addState = 1
                                if entry['Type'] == "Book":
                                    addState = 4
                                    entry['Printed'] = 0
                            elif addState==1:
                                addstr("Printed? y/[n]:")
                                c = stdscr.getch()
                                if c == ord("y"):
                                    entry['Printed'] = 1
                                    addState = 2
                                else:
                                    entry['Printed'] = 0
                                    addState = 4
                            elif addState==2:
                                curses.echo()
                                addstr("Location: ")
                                newLocation = stdscr.getstr()
                                curses.noecho()
                                entry['Location'] = newLocation
                                addState = 3
                            elif addState==3:
                                curses.echo()
                                addstr("Current location: ")
                                newLocation = stdscr.getstr()
                                curses.noecho()
                                entry['CurrentLocation'] = newLocation
                                addState = 4
                            elif addState==4:

                                addstr("Add keywords\n\n")

                                cur.execute("SELECT Keywords.Keyword, COUNT(KeywordID) AS KeywordCount FROM Keywords LEFT JOIN HasKeyword ON Keywords.ROWID = HasKeyword.KeywordID GROUP BY Keywords.ROWID ORDER BY KeywordCount DESC")
                                orderedKeywords = cur.fetchall();

                                if addListStart > 0:
                                    addstr(" :\n :\n")
                                for i,keyword in enumerate(orderedKeywords[addListStart:addListStart+9]):
                                    style = s_normal
                                    if keyword[0] in entry['Keywords']:
                                        style = s_bold

                                    addstr("[" + str(i+1) + "] - " + str(keyword[0]) + "\n", style)
                                if len(orderedKeywords) - addListStart > 9:
                                    addstr(" :\n :\n")
                                addstr("\n")

                                addstr("[^] - Up  [v] - Down  [a] - Add keyword  [Ret] - Done\n\n")

                                stdscr.refresh()
                                c = stdscr.getch()

                                if c==curses.KEY_UP:
                                    if addListStart > 0:
                                        addListStart -= 9
                                elif c==curses.KEY_DOWN:
                                    if len(orderedKeywords) - addListStart > 9:
                                        addListStart += 9
                                elif c>=49 and c<=57:
                                    toAdd = orderedKeywords[c-49+addListStart][0]
                                    if toAdd in entry['Keywords']:
                                        entry['Keywords'].remove(toAdd)
                                    else:
                                        entry['Keywords'].add(toAdd)
                                elif c==ord("a"):
                                    addstr("New keyword: ")
                                    newKeyword = ""
                                    curses.echo()
                                    newKeyword = stdscr.getstr()
                                    curses.noecho()
                                    if newKeyword is not "":
                                        entry['Keywords'].add(newKeyword)
                                elif c==10:
                                    addListStart = 0
                                    addState=5

                            elif addState==5:

                                sqlString = "INSERT INTO Entries (Title, Priority, Done, Deadline, Notes, Type, Active, Printed, Location, CurrentLocation, Bibtex) VALUES ('"
                                sqlString += entry['Title'] + "', "            # Title
                                sqlString += str(entry['Priority']) + ", 0, '" # Priority, and Done=0
                                sqlString += "', '"                            # Deadline
                                sqlString += "', '"                            # Notes
                                sqlString += entry['Type'] + "', "             # Type
                                sqlString += "0, "                             # Active
                                sqlString += str(entry['Printed']) + ", '"     # Printed
                                sqlString += entry['Location'] + "', '"        # Location
                                sqlString += entry['CurrentLocation'] + "', '" # Current Location
                                sqlString += entry['Bibtex'] + "');"           # Bibtex
                                cur.execute(sqlString)

                                newEntryID = cur.lastrowid
                                mkdir_p('resources/' + str(newEntryID))
                                with open('resources/' + str(newEntryID) + '/notes.md','w') as f:
                                    pass

                                for author in entry['Authors']:

                                    # If we don't already have an author of that name, add it
                                    sqlString = "SELECT ROWID FROM Authors WHERE Surname = '"
                                    sqlString += author['Surname'] + "' AND Forename = '"
                                    sqlString += author['Forename'] + "';"
                                    cur.execute(sqlString)
                                    result = cur.fetchone()
                                    authorID = 0
                                    if result == None:
                                        sqlString = "INSERT INTO Authors VALUES ('"
                                        sqlString += author['Surname'] + "', '"
                                        sqlString += author['Forename'] + "');"
                                        cur.execute(sqlString)
                                        authorID = cur.lastrowid
                                    else:
                                        authorID = result[0]
                                    # Add the paper-author connection in the HasAuthor table
                                    sqlString = "INSERT INTO HasAuthor VALUES ("
                                    sqlString += str(newEntryID) + ", " + str(authorID) + ");"
                                    cur.execute(sqlString)

                                for keyword in entry['Keywords']:
                                    # If we don't already have a keyword of that name, add it
                                    sqlString = "SELECT ROWID FROM Keywords WHERE Keyword = '"
                                    sqlString += keyword + "';"
                                    cur.execute(sqlString)
                                    result = cur.fetchone()
                                    keywordID = 0
                                    if result == None:
                                        sqlString = "INSERT INTO Keywords VALUES ('"
                                        sqlString += keyword + "');"
                                        cur.execute(sqlString)
                                        keywordID = cur.lastrowid
                                    else:
                                        keywordID = result[0]
                                    # Add the entry-keyword connection in the HasKeyword table
                                    sqlString = "INSERT INTO HasKeyword VALUES ("
                                    sqlString += str(newEntryID) + ", " + str(keywordID) + ");"
                                    cur.execute(sqlString)

                                addState = 6

                            elif addState==6:
                                changePDF(newEntryID)

                                break

                    break # Save after adding from bibtex


curses.nocbreak(); stdscr.keypad(0); curses.echo()
curses.endwin()
