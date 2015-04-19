from app import app
from flask import request, render_template, redirect, url_for
from flask.ext.paginate import Pagination
from attrdict import AttrDict
from urllib import quote_plus
import requests, json, re

import string

RESULTS_PER_PAGE = 25

@app.route('/', methods=['GET','POST'])
@app.route('/#search', methods=['GET','POST'])
def search():
    if request.method == 'POST':
        search_value = request.form.getlist('search')[0]
        search_value = quote_plus(search_value)
        print search_value # value of the search query

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

            print 'Search yielded ' + str(num_results) + ' result(s).'

            results_for_html = []
            for i in range(0, min(RESULTS_PER_PAGE,num_results)-1):
                org = filings[i]['organization']
                result_for_html = {
                    'name': org['name'],
                    'ein': org['ein'],
                    'city': org['city'],
                    'state': org['state'],
                    'tax_prd': filings[i]['tax_prd']
                }
                results_for_html.append(result_for_html)

                # print - delete me when ur done
                print org['name']
                print org['ein']
                print org['city']
                print org['state']
                print filings[i]['tax_prd']
                print ''

            print len(results_for_html) == 0
            if (len(request.form.getlist('page')) > 0):
                page = int(request.form.getlist('page')[0])
            else:
                page = 1
            pagination = Pagination(page=page, total=num_results, search=False,
                                    per_page=RESULTS_PER_PAGE)

            return render_template('index.html', results=results_for_html,
                                    pagination=pagination,
                                    no_result=len(results_for_html) == 0,
                                    search_value=search_value)

    return render_template('index.html')

# if search value is EIN, use Organization Method
# else, use Search Method
def query(search_value, page=0):
    # use pattern matching to check if search value is EIN or org name
    if is_EIN(search_value):
        #print "is EIN"
        query = 'https://projects.propublica.org/nonprofits/api/v1/organizations/'
        result = requests.get(query + search_value + '.json?page=' + page).content

    else:
        query = 'https://projects.propublica.org/nonprofits/api/v1/search.json?q='
        # TODO error checking
        result = requests.get(query + search_value).content

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

@app.route('/results')
def results():
    return render_template('results.html')

# TODO ? should i convert ein to <int:ein> ?
@app.route('/results/<ein>')
def ein_results(ein):
    print ein

    states = ["AL - Alabama", "AK - Alaska", "AZ - Arizona", "AR - Arkansas", "CA - California", "CO - Colorado", "CT - Connecticut", "DE - Delaware", "FL - Florida", "GA - Georgia", "HI - Hawaii", "ID - Idaho", "IL - Illinois", "IN - Indiana", "IA - Iowa", "KS - Kansas", "KY - Kentucky", "LA - Louisiana", "ME - Maine", "MD - Maryland", "MA - Massachusetts", "MI - Michigan", "MN - Minnesota", "MS - Mississippi", "MO - Missouri", "MT - Montana", "NE - Nebraska", "NV - Nevada", "NH - New Hampshire", "NJ - New Jersey", "NM - New Mexico", "NY - New York", "NC - North Carolina", "ND - North Dakota", "OH - Ohio", "OK - Oklahoma", "OR - Oregon", "PA - Pennsylvania", "RI - Rhode Island", "SC - South Carolina", "SD - South Dakota", "TN - Tennessee", "TX - Texas", "UT - Utah", "VT - Vermont", "VA - Virginia", "WA - Washington", "WV - West Virginia", "WI - Wisconsin", "WY - Wyoming"]

    abbrevs = ["AL", "AK", "AZ", "AR", "CA", "CO", "CT", "DE", "FL", "GA", "HI", "ID", "IL", "IN", "IA", "KS", "KY", "LA", "ME", "MD", "MA", "MI", "MN", "MS", "MO", "MT", "NE", "NV", "NH", "NJ", "NM", "NY", "NC", "ND", "OH", "OK", "OR", "PA", "RI", "SC", "SD", "TN", "UT", "VT", "VA", "WA", "WV", "WI", "WY" ]
    
    result = query(ein)

   
    org = result['organization']
    print org
    name = org['name']
    ntee_code = org['ntee_code']
    state = org['state']
    revenue = org['revenue_amount']

    name = name.lower()
    name = string.capwords(name)
    print name

    return render_template('results.html', 
        name=name, 
        savings=2021, 
        current_percentile=50, 
        uac_percentile=75,
        ntee_code=ntee_code,
        state=state,
        revenue=revenue,
        overhead=000000)

#@app.route('/results/') # ? results/123456789

