from app import app, db, models, mail
from app.models import *
from flask import request, render_template, redirect, url_for
from flask.ext.paginate import Pagination
from attrdict import AttrDict
from urllib import quote_plus
import requests, json, re, datetime
from flask.ext.mail import Message


import string

RESULTS_PER_PAGE = 25

@app.route('/', methods=['GET','POST'])
@app.route('/search', methods=['GET','POST'])
def search():
    if request.method == 'POST':
        search_value = request.form.getlist('search')[0]
        original_search_value = search_value
        search_value = quote_plus(search_value)
        #print search_value

        if (len(request.form.getlist('page')) > 0):
            result = query(search_value, int(request.form.getlist('page')[0]))
        else:
            result = query(search_value)

        if is_EIN(search_value):
            org = result['organization']
            # redirect
            ein = parse_EIN(search_value)
            return redirect(url_for('ein_results', ein=ein))

        else:
            filings = result['filings']
            num_results = result['total_results']

            #print 'Search yielded ' + str(num_results) + ' result(s).'

            results_for_html = []
            for i in range(0, len(filings)):
                org = filings[i]['organization']
                result_for_html = {
                    'name': org['name'].title(),
                    'ein': org['ein'],
                    'city': org['city'].title(),
                    'state': org['state'],
                    'tax_prd': filings[i]['tax_prd']
                }
                added_already = False
                for i in range(0, len(results_for_html)):
                    if (results_for_html[i]['ein'] == result_for_html['ein']):
                        added_already = True
                        break
                if (not added_already):
                    results_for_html.append(result_for_html)

            if (len(request.form.getlist('page')) > 0):
                page = int(request.form.getlist('page')[0])
            else:
                page = 1
            pagination = Pagination(page=page, total=num_results, search=False,
                                    per_page=RESULTS_PER_PAGE)

            return render_template('index.html', results=results_for_html,
                                    pagination=pagination,
                                    no_result=len(results_for_html) == 0,
                                    search_value=original_search_value)

    return render_template('index.html')

# if search value is EIN, use Organization Method
# else, use Search Method
def query(search_value, page=0):
    # use pattern matching to check if search value is EIN or org name
    if is_EIN(search_value):
        #print "is EIN"
        query = 'https://projects.propublica.org/nonprofits/api/v1/organizations/'
        result = requests.get(query + search_value + '.json?page=' + str(page)).content

    else:
        query = 'https://projects.propublica.org/nonprofits/api/v1/search.json?q='
        # TODO error checking
        result = requests.get(query + search_value + '&page=' + str(page)).content

    result = json.loads(result) # convert to json obj
    return result

# TODO ? - what if they search for a number that happens to be an ein?
def is_EIN(search_value):
    # TODO double check error logic
    # 1. strip non-alphanumeric, check is number and length <= 9
    # remove all non-alphanumeric characters
    check_val = parse_EIN(search_value)
    if (not check_val.isdigit()) or (len(check_val) > 9):
        return False

    # 2. check if ein is valid using API request
    #return is_valid_EIN(check_val)
    if not is_valid_EIN(check_val):
        return False

    return True

def parse_EIN(search_value):
    ein = re.sub(r'[^a-zA-Z0-9]','', search_value)

    # pad with leading 0's if len < 9
    if len(ein) < 9:
        ein = ein.zfill(9)

    return ein

# may become deprecated if the Propublica API changes the way they handle 
# invalid EIN get requests
def is_valid_EIN(ein):
    query = 'https://projects.propublica.org/nonprofits/api/v1/organizations/'
    result = requests.get(query + ein + '.json').content

    # check if result is html page rather than valid json object
    if result.split('\n', 1)[0] == '<!DOCTYPE html>':
        return False
    return True

def get_filing_data(filing_array):
    filing_data = {'profndraising':0, 'totexpns':0}
    for filing in filing_array:
        try:
            filing_data['profndraising'] = filing['profndraising']
            filing_data['totexpns'] = filing['totexpns']
        except KeyError:
            print 'Invalid key: profndraising, totexpns'
    return filing_data

def get_pdf_url(result):
    max_year = 0
    pdf_url = ""
    try:
        filings = result['filings_with_data']
        for filing in filings:
            if filing['tax_prd'] > max_year:
                max_year = filing['tax_prd']
                pdf_url = filing['pdf_url']
    except KeyError:
        print 'Invalid Key: get_pdf_url() filings_with_data'
    try:
        filings = result['filings_without_data']
        for filing in filings:
            if filing['tax_prd'] > max_year:
                max_year = filing['tax_prd']
                pdf_url = filing['pdf_url']
    except KeyError:
        print 'Invalid Key: get_pdf_url() filings_without_data'

    return pdf_url

def populate_results_data(result, result_data, ein):
    try:
        org = result['organization']
        try:
            name = org['name']
            name = name.lower()
            name = string.capwords(name)
            result_data['name'] = name
        except KeyError:
            print 'Invalid key: name'
        try:
            result_data['ntee_code'] = org['ntee_code']
        except KeyError:
            print 'Invalid key: ntee_code'
        try:
            result_data['state'] = org['state']
        except KeyError:
            print 'Invalid key: state'
        try:
            result_data['revenue'] = org['revenue_amount']
        except KeyError:
            print 'Invalid key: revenue_amount'
        try:
            #result_data['nccs_url'] = org['nccs_url']
            result_data['nccs_url'] = "http://nccsweb.urban.org/communityplatform/nccs/organization/profile/id/" + ein + "/"
        except KeyError:
            print 'Invalid key: nccs_url'
        try:
            #result_data['guidestar_url'] = org['guidestar_url']
            result_data['guidestar_url'] = "https://www.guidestar.org/organizations/"+ str(ein)[0:2]+"-" + str(ein)[2:]+"/.aspx"
        except KeyError:
            print 'Invalid key: guidestar_url'
        try:
            result_data['filing_data'] = get_filing_data(result['filings_with_data'])
        except KeyError:
            print 'Invalid key: filings_with_data'
        try:
            result_data['pdf_url'] = get_pdf_url(result)
        except KeyError:
            print 'Invalid key: pdf_url'
    except KeyError:
        print 'Invalid key: organization'
    
        return


@app.route('/results')
def results():
    return render_template('results.html', result_data={'name':'New (custom) nonprofit',
                                                        'state':'US',
                                                        'ntee_code': 'None',
                                                        'revenue':0})


# TODO ? should i convert ein to <int:ein> ?
@app.route('/results/<ein>')
def ein_results(ein):
    #print ein
    
    result = query(ein)

    result_data = {
        'name':'', 
        'ntee_code':0, 
        'state':'', 
        'revenue':0, 
        'nccs_url':'', 
        'guidestar_url':'', 
        'pdf_url':'',
        'filing_data':{},
        'savings':0,
        'current_percentile':0,
        'uac_percentile':0,
        'overhead':0}

    populate_results_data(result, result_data, ein)

    # compare the DC nonprofits to those from Maryland
    if (result_data['state'] == 'DC'):
        result_data['state'] = 'MD'

    return render_template('results.html', result_data=result_data, ein=ein)

@app.route('/calculate', methods=['POST'])
def calculate():
    print request.form.getlist('total_revenue')
    print request.form
    total_rev = float(request.form.getlist('total_revenue')[0])
    print 'POST: calculating percentiles'
    this_nonprofit_expense_literal = {}
    this_nonprofit_expense_percent = {}
    # converts all expenses into percentages and puts into dict by category name
    field_names = ['pension_plan_contributions', 'othremplyeebene',
                   'feesforsrvcmgmt', 'legalfees', 'accountingfees',
                   'feesforsrvclobby', 'profndraising', 'feesforsrvcinvstmgmt',
                   'feesforsrvcothr', 'advrtpromo', 'officexpns', 'infotech',
                   'interestamt', 'insurance', 'total_expense', 'total_revenue']
    for name in field_names:
        this_nonprofit_expense_literal[name] = float(request.form.getlist(name)[0])
        this_nonprofit_expense_percent[name] = float(request.form.getlist(name)[0]) / max(total_rev, 0.000001)*100
        if (name == 'total_expense'):
            this_nonprofit_expense_percent['totalefficiency'] = float(request.form.getlist(name)[0]) / max(total_rev, 0.000001)*100

    print this_nonprofit_expense_literal
    print this_nonprofit_expense_percent
    state_id = request.form.getlist('state_id')[0]
    if (state_id == 'US'):
        state_id = '00'
    ntee_id = request.form.getlist('ntee_id')[0]
    if (ntee_id == 'All'):
        ntee_id = '0'
    revenue_id = request.form.getlist('revenue_id')[0]
    query_bucket_id = state_id + '_' + ntee_id + '_' + revenue_id
    print 'query_bucket_id: ' + query_bucket_id
    table_row = models.Bucket.query.filter_by(bucket_id=query_bucket_id).first()
    if (not table_row):
        return jsonify({ 'no_such_bucket': True })
    this_nonprofit_ranking_data = table_row.get_all_percentiles(this_nonprofit_expense_percent)
    other_nonprofit_data = table_row.get_other_nonprofit_data()
    print other_nonprofit_data
    return jsonify({
            'this_nonprofit_expense_literal': this_nonprofit_expense_literal,
            'this_nonprofit_expense_percent': this_nonprofit_expense_percent,
            'this_nonprofit_rankings': this_nonprofit_ranking_data,
            'other_nonprofits_expense_percent': other_nonprofit_data['expense_percents'],
            'other_nonprofits_rankings': other_nonprofit_data['rankings']
        })

@app.route('/contact', methods=['POST'])
def contact():
    print request.form
    print request.values
    client_name = request.form['name']
    client_org = request.form['org']
    client_email = request.form['email']
    client_phone = request.form['phone']
    client_image = request.form['image']
    print client_name
    print client_org
    print client_email
    print client_phone
    print client_image

    msgUAC = Message("Nonprofit Overhead Analyzer: new prospect",
        sender="armatoka@gmail.com",
                  recipients=['armatoka@gmail.com', 'tdevor@uac.org', 'aprabhakaran@uac.org'])
    msgUAC.html = ("<p>Hello,</p><p>A new prospect requested a report on the Nonprofit Overhead Analyzer. Here are the details:<br>Name: "
    + client_name + "<br>Organization: " + client_org + "<br>Email: "
    + client_email + "<br>Phone: " + client_phone
    + "<br>Please see the CSV file attached for the prospect's financials.</p><p>This is an automatically-generated message. Please do not reply.<br>Have a good day!</p>")
    
    # create the CSV
    current_time = datetime.datetime.now().strftime("%c")
    csv_data='Expense type, Amount\n'
    field_names = ['name', 'org', 'email', 'phone', 'pension_plan_contributions',
                   'othremplyeebene', 'feesforsrvcmgmt', 'legalfees', 'accountingfees',
                   'feesforsrvclobby', 'profndraising', 'feesforsrvcinvstmgmt',
                   'feesforsrvcothr', 'advrtpromo', 'officexpns', 'infotech',
                   'interestamt', 'insurance', 'total_expense', 'total_revenue']

    for name in field_names:
        csv_data += name + ',' + request.values[name] + '\n'

    # attach the client financial data in the CSV
    msgUAC.attach(data=csv_data,
               content_type="text/plain",
               filename='Nonprofit Overhead Analyzer prospect data from ' + current_time + '.csv')

    mail.send(msgUAC)
    return "200"

    # return render_template('results.html', 
    #     name=result_data['name'],
    #     ntee_code=result_data['ntee_code'],
    #     state=result_data['state'],
    #     revenue=result_data['revenue'],
    #     nccs_url=result_data['nccs_url'],
    #     guidestar_url=result_data['guidestar_url'],
    #     savings=0,
    #     current_percentile=0,
    #     uac_percentile=0,
    #     overhead=0)

    # return render_template('results.html', 
    #     name=result_data['name'],
    #     ntee_code=result_data['ntee_code'],
    #     state=result_data['state'],
    #     revenue=result_data['revenue'],
    #     nccs_url=result_data['nccs_url'],
    #     guidestar_url=result_data['guidestar_url'],
    #     savings=0,
    #     current_percentile=0,
    #     uac_percentile=0,
    #     overhead=0)

#@app.route('/results/') # ? results/123456789
