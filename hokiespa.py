from pyquery import PyQuery
import requests
from datetime import timedelta, datetime

class Constants:
    postURL = "https://banweb.banner.vt.edu/ssb/prod/HZSKVTSC.P_ProcRequest"
    getURL = "https://banweb.banner.vt.edu/ssb/prod/HZSKVTSC.P_DispRequest"
    getCommentsURL = "https://banweb.banner.vt.edu/ssb/prod/HZSKVTSC.P_ProcComments?"

class MeetingTime(object):
    def __init__(self):
        self.days = self.begin = self.end = self.location = None

class Course(object):
    def __init__(self):
        self.crse = self.subject_code = self.id = self.title = self.exam = None
        self.instructor = self.type = self.capacity = self.comments = None
        self.meeting_times = []

def getSubjects():
    resp = requests.get(Constants.getURL)
    PQ = PyQuery(resp.content)
    subjects = [v.text.split(" - ")[0] for v in PQ("select").eq(3).children()[1:]]

    return subjects

def getCourseIds(subjectCode, year, term, onlyOpen = False):
    html = pullSubjectPage(subjectCode, year, term, onlyOpen)
    return extractCourseIds(html)

def getCourseIdsAndCRSEs(subjectCode, year, term, onlyOpen = False):
    html = pullSubjectPage(subjectCode, year, term, onlyOpen)
    return extractCourseIdsAndCRSEs(html)

def getCourses(subjectCode, year, term, onlyOpen = False):
    shtml = pullSubjectPage(subjectCode, year, term, onlyOpen)
    idcrses = extractCourseIdsAndCRSEs(shtml)
    for id,crse in idcrses:
        chtml = pullCourseCommentsPage(id, crse, subjectCode, year, term)
        yield extractCourse(chtml)

def pullSubjectPage(subjectCode, year, term, onlyOpen = False):
    if (onlyOpen):
        switch = "on"
    else:
        switch = ""
    data = {"CAMPUS" : 0, "TERMYEAR" : year+term, "SUBJ_CODE" : subjectCode, "open_only" : switch, "CORE_CODE" : "AR%", "PRINT_FRIEND" : "Y"}
    resp = requests.post(Constants.postURL, data)
    return resp.content

def pullCourseCommentsPage(courseId, crse, subjectCode, year, term):
    reqString = Constants.getCommentsURL + ("CRN=%s&TERM=%s&YEAR=%s&SUBJ=%s&CRSE=%s" %
                        (courseId, term, year, subjectCode, crse))
    resp = requests.get(reqString)
    return resp.content

def extractCourseIdsAndCRSEs(rawHTML):
    PQ = PyQuery(rawHTML)
    rows = PQ.find("table").eq(0).children()
    def getIdAndCRSE(index):
        id = rows.eq(index).children().eq(0).text()
        crse = rows.eq(index).children().eq(1).text()
        if id and id.isdigit():
            return (id, crse.split('-')[1])
        else:
            return None
    for i in xrange(1, len(rows)):
        v = getIdAndCRSE(i)
        if v:
            yield v


def extractCourseIds(rawHTML):
    for _id, _ in extractCourseIdsAndCRSEs(rawHTML):
        yield _id

def extractCourse(commentsHTML):
    c = Course()
    table = PyQuery(commentsHTML).find("table.plaintable").children()

    c.id = table.eq(0).text().split()[-1]
    c.subject_code, c.crse = table.eq(1).text().split()[0].split('-')
    c.title = ' '.join(table.eq(1).text().split()[1:])
    c.description = table.eq(2).children().eq(1).text()

    if c.description == "Description Not Found":
        c.description = None

    mtimesPQ = table.eq(3).children().eq(1).children().children()

    if mtimesPQ.eq(1).children().length > 2:
        mtime = MeetingTime()
        mtime.days      = mtimesPQ.eq(1).children().eq(1).text().split()
        mtime.begin     = mtimesPQ.eq(1).children().eq(2).text()
        mtime.end       = mtimesPQ.eq(1).children().eq(3).text()
        mtime.location  = mtimesPQ.eq(1).children().eq(4).text()
        c.exam          = mtimesPQ.eq(1).children().eq(5).text()

        if mtime.days == ['(ARR)']:
            mtime.days = None
            mtime.begin = None
            c.exam = mtime.location
            mtime.location = mtime.end
            mtime.end = None

        c.meeting_times.append(mtime)


        for i in xrange(mtimesPQ.length - 2):   # get additional times
            mtime = MeetingTime()
            mtime.days      = mtimesPQ.eq(i).children().eq(5).text().split()
            mtime.begin     = mtimesPQ.eq(i).children().eq(6).text()
            mtime.end       = mtimesPQ.eq(i).children().eq(7).text()
            mtime.location  = mtimesPQ.eq(i).children().eq(8).text()
            c.meeting_times.append(mtime)

    sectionInfoPQ = table.eq(4).find("table").children().eq(2).children()
    c.instructor = sectionInfoPQ.eq(0).text()
    c.type  = sectionInfoPQ.eq(1).text()
    c.status = sectionInfoPQ.eq(2).text()
    c.capacity = sectionInfoPQ.eq(3).text()

    comments = table.eq(5).children().eq(1).text()
    if comments == 'None':
        c.comments = None
    else:
        c.comments = comments

    return c


