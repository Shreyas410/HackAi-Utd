from flask import Flask, render_template, request
from mlmodel import Ratings
from webScraping import WebScraping

# import pickle

app = Flask(__name__)

CourseInfo = {
    'totalCourses': 0,
    'courses': []
}

@app.route('/')
def index():
    return render_template('index1.html')
@app.route('/index')
def index1():
    return render_template('index.html')

@app.route('/analysis',methods=['GET','POST'])
def analysis():
    if request.method == 'GET':
        return render_template('analysisForm.html')
    
    if request.method == 'POST':
        link = request.form.get('link')
      
        site = request.form.get('platform')
        CourseInfo['totalCourses'] = 1
        CourseInfo['courses'].clear() 
        CourseInfo['courses'].append(WebScraping(link,site))
        CourseInfo['courses'][0]['rating'] = Ratings(CourseInfo['courses'][0]['comments'])
        CourseInfo['courses'][0]['platform'] = site
        CourseInfo['courses'][0]['link'] = link
        return render_template('analysisReport.html',CourseInfo=CourseInfo)

@app.route('/multipleAnalysis',methods=['GET','POST'])
def multipleAnalysis():
    if request.method == 'GET':
        return render_template('analysisForm.html')
    if request.method == 'POST':
        if request.form.get('platform'):
            link = request.form.get('link')
            site = request.form.get('platform')
            CourseInfo['totalCourses'] += 1
            v=CourseInfo['courses'].append(WebScraping(link,site))
            CourseInfo['courses'][-1]['rating'] = Ratings(CourseInfo['courses'][-1]['comments'])
            CourseInfo['courses'][-1]['platform'] = site
            CourseInfo['courses'][-1]['link'] = link
        return render_template('multipleAnalysisReport.html',CourseInfo=CourseInfo)

@app.route('/aboutus')
def aboutus():
    return render_template('aboutUs.html')

@app.route('/anim')
def aboutus1():
    return render_template('index1.html')

if __name__ == "__main__":
    app.run(debug=True)