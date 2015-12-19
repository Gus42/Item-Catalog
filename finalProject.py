from flask import Flask, render_template, request, redirect, jsonify, url_for, flash
from sqlalchemy import create_engine, asc
from sqlalchemy.orm import sessionmaker
from database_setup import Base, User, Category, Item
from flask import session as login_session
import random
import string
from oauth2client.client import flow_from_clientsecrets
from oauth2client.client import FlowExchangeError
import httplib2
import json
from flask import make_response
import requests

app = Flask(__name__)

CLIENT_ID = json.loads(open('client_secrets.json', 'r').read())['web']['client_id']

# Connect to the database catalog.db
engine = create_engine('sqlite:///catalog.db')
Base.metadata.bind = engine
DBSession = sessionmaker(bind=engine)
session = DBSession()

@app.route('/login')
def showLogin():
    '''
    Create a state for the connection of an user and show login.html
    '''
    state = ''.join(random.choice(string.ascii_uppercase + string.digits) for x in xrange(32))
    login_session['state'] = state
    return render_template('login.html', STATE=state)


@app.route('/fbconnect', methods=['POST'])
def fbconnect():
    '''
    Connect a user with facebook account
    '''
    if request.args.get('state') != login_session['state']:
        response = make_response(json.dumps('Invalid state parameter.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response
    access_token = request.data
    print "access token received %s " % access_token

    app_id = json.loads(open('fb_client_secrets.json', 'r').read())[
        'web']['app_id']
    app_secret = json.loads(
        open('fb_client_secrets.json', 'r').read())['web']['app_secret']
    url = 'https://graph.facebook.com/oauth/access_token?grant_type=fb_exchange_token&client_id=%s&client_secret=%s&fb_exchange_token=%s' % (
        app_id, app_secret, access_token)
    h = httplib2.Http()
    result = h.request(url, 'GET')[1]

    # Use token to get user info from API
    userinfo_url = "https://graph.facebook.com/v2.4/me"
    # strip expire tag from access token
    token = result.split("&")[0]


    url = 'https://graph.facebook.com/v2.4/me?%s&fields=name,id,email' % token
    h = httplib2.Http()
    result = h.request(url, 'GET')[1]
    # print "url sent for API access:%s"% url
    # print "API JSON result: %s" % result
    data = json.loads(result)
    login_session['provider'] = 'facebook'
    login_session['username'] = data["name"]
    login_session['email'] = data["email"]
    login_session['facebook_id'] = data["id"]

    # The token must be stored in the login_session in order to properly logout, let's strip out the information before the equals sign in our token
    stored_token = token.split("=")[1]
    login_session['access_token'] = stored_token

    # Get user picture
    url = 'https://graph.facebook.com/v2.4/me/picture?%s&redirect=0&height=200&width=200' % token
    h = httplib2.Http()
    result = h.request(url, 'GET')[1]
    data = json.loads(result)

    login_session['picture'] = data["data"]["url"]

    # see if user exists
    user_id = getUserID(login_session['email'])
    if not user_id:
        user_id = createUser(login_session)
    login_session['user_id'] = user_id

    output = ''
    output += '<h1>Welcome, '
    output += login_session['username']

    output += '!</h1>'
    output += '<img src="'
    output += login_session['picture']
    output += ' " style = "width: 300px; height: 300px;border-radius: 150px;-webkit-border-radius: 150px;-moz-border-radius: 150px;"> '

    flash("Now logged in as %s" % login_session['username'])
    return output


@app.route('/fbdisconnect')
def fbdisconnect():
    '''
    Revoke the token of a connected user, for a facebook account
    '''
    facebook_id = login_session['facebook_id']
    # The access token must me included to successfully logout
    access_token = login_session['access_token']
    url = 'https://graph.facebook.com/%s/permissions?access_token=%s' % (facebook_id,access_token)
    h = httplib2.Http()
    result = h.request(url, 'DELETE')[1]
    return "you have been logged out"


@app.route('/gconnect', methods=['POST'])
def gconnect():
    '''
    Connect a user with google account
    '''
    # Validate state token
    if request.args.get('state') != login_session['state']:
        response = make_response(json.dumps('Invalid state parameter.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response
    # Obtain authorization code
    code = request.data

    try:
        # Upgrade the authorization code into a credentials object
        oauth_flow = flow_from_clientsecrets('client_secrets.json', scope='')
        oauth_flow.redirect_uri = 'postmessage'
        credentials = oauth_flow.step2_exchange(code)
    except FlowExchangeError:
        response = make_response(
            json.dumps('Failed to upgrade the authorization code.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Check that the access token is valid.
    access_token = credentials.access_token
    url = ('https://www.googleapis.com/oauth2/v1/tokeninfo?access_token=%s'
           % access_token)
    h = httplib2.Http()
    result = json.loads(h.request(url, 'GET')[1])
    # If there was an error in the access token info, abort.
    if result.get('error') is not None:
        response = make_response(json.dumps(result.get('error')), 500)
        response.headers['Content-Type'] = 'application/json'

    # Verify that the access token is used for the intended user.
    gplus_id = credentials.id_token['sub']
    if result['user_id'] != gplus_id:
        response = make_response(
            json.dumps("Token's user ID doesn't match given user ID."), 401)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Verify that the access token is valid for this app.
    if result['issued_to'] != CLIENT_ID:
        response = make_response(
            json.dumps("Token's client ID does not match app's."), 401)
        print "Token's client ID does not match app's."
        response.headers['Content-Type'] = 'application/json'
        return response

    stored_credentials = login_session.get('credentials')
    stored_gplus_id = login_session.get('gplus_id')
    if stored_credentials is not None and gplus_id == stored_gplus_id:
        response = make_response(json.dumps('Current user is already connected.'),
                                 200)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Store the access token in the session for later use.
    login_session['credentials'] = credentials
    login_session['gplus_id'] = gplus_id

    # Get user info
    userinfo_url = "https://www.googleapis.com/oauth2/v1/userinfo"
    params = {'access_token': credentials.access_token, 'alt': 'json'}
    answer = requests.get(userinfo_url, params=params)

    data = answer.json()

    login_session['username'] = data['name']
    login_session['picture'] = data['picture']
    login_session['email'] = data['email']
    # ADD PROVIDER TO LOGIN SESSION
    login_session['provider'] = 'google'

    # see if user exists, if it doesn't make a new one
    user_id = getUserID(data["email"])
    if not user_id:
        user_id = createUser(login_session)
    login_session['user_id'] = user_id

    output = ''
    output += '<h1>Welcome, '
    output += login_session['username']
    output += '!</h1>'
    output += '<img src="'
    output += login_session['picture']
    output += ' " style = "width: 300px; height: 300px;border-radius: 150px;-webkit-border-radius: 150px;-moz-border-radius: 150px;"> '
    flash("you are now logged in as %s" % login_session['username'])
    print "done!"
    return output

# User Helper Functions


def createUser(login_session):
    '''
    Create a new user with name,email and picture.
    Store the new user in the database.
    '''
    newUser = User(name=login_session['username'], email=login_session[
                   'email'], picture=login_session['picture'])
    session.add(newUser)
    session.commit()
    user = session.query(User).filter_by(email=login_session['email']).one()
    return user.id


def getUserInfo(user_id):
    '''
    return user info given his id
    '''
    user = session.query(User).filter_by(id=user_id).one()
    return user


def getUserID(email):
    '''
    return user id given his email
    '''
    try:
        user = session.query(User).filter_by(email=email).one()
        return user.id
    except:
        return None

@app.route('/gdisconnect')
def gdisconnect():
    '''
    Revoke the token of a connected user, for a google account
    '''
    # Only disconnect a connected user.
    credentials = login_session.get('credentials')
    if credentials is None:
        response = make_response(
            json.dumps('Current user not connected.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response
    access_token = credentials.access_token
    url = 'https://accounts.google.com/o/oauth2/revoke?token=%s' % access_token
    h = httplib2.Http()
    result = h.request(url, 'GET')[0]
    if result['status'] != '200':
        # For whatever reason, the given token was invalid.
        response = make_response(
            json.dumps('Failed to revoke token for given user.', 400))
        response.headers['Content-Type'] = 'application/json'
        return response

# --------------------------------------------------------------------------------------------------------


@app.route('/catalog/JSON')
def categoriesJSON():
    '''
    It shows JSON object of the catalog
    '''
    categories = session.query(Category).all()
    return jsonify(Categories=[i.serialize for i in categories])

@app.route('/catalog/<int:category_id>/items/JSON')
def itemsJSON(category_id):
    '''
    It shows JSON object of the selected category
    '''
    category = session.query(Category).filter_by(id=category_id).one()
    items = session.query(Item).filter_by(category_id=category_id).all()
    return jsonify(Item=[i.serialize for i in items])

@app.route('/catalog/<int:category_id>/items/<int:item_id>/JSON')
def itemJSON(category_id, item_id):
    '''
    It shows JSON object of the selected item
    '''
    item = session.query(Item).filter_by(id=item_id).one()
    return jsonify(Item=item.serialize)

# Show the catalog
@app.route("/")
@app.route("/catalog")
def showCatalog():
    '''
    It shows catalog.html if the user is logged
    otherwise shows to publicCatalog.html
    '''
    categories = session.query(Category).order_by(asc(Category.name))
    if 'username' not in login_session:
        return render_template('publicCatalog.html', categories=categories)
    else:
        return render_template('catalog.html', categories=categories)

@app.route("/catalog/new",
           methods=['GET', 'POST'])
def newCategory():
    '''
    if GET: go to newCategory.html
    if POST: create the new category
    '''
    if 'username' not in login_session:
        return redirect('/login')
    if request.method == 'POST':
        newCategory = Category(
            name=request.form['name'], user_id=login_session['user_id'])
        session.add(newCategory)
        session.commit()
        flash("A new category, Dude!")
        return redirect(url_for('showCatalog'))
    else:
        return render_template('newCategory.html')

@app.route("/catalog/<int:category_id>/edit",
           methods=['GET', 'POST'])
def editCategory(category_id):
    '''
    if GET: go to editCategory.html of the selected category
    if POST: edit the selected category
    '''
    category = session.query(Category).filter_by(id=category_id).one()
    if 'username' not in login_session:
        return redirect('/login')
    if category.user_id != login_session['user_id']:
        return "<script>function myFunction() {alert('You are not authorized to edit this category. Please create your own category in order to edit.');}</script><body onload='myFunction()''>"
    if request.method == 'POST':
        if request.form['name']:
            category.name = request.form['name']
        session.add(category)
        session.commit()
        flash("The category is changed")
        return redirect(url_for('showCatalog'))
    else:
        return render_template(
            'editCategory.html', category_id=category_id, category=category)

@app.route("/catalog/<int:category_id>/delete",
           methods=['GET', 'POST'])
def deleteCategory(category_id):
    '''
    if GET: go to deleteCategory.html of the selected category
    if POST: delete the selected category
    '''
    category = session.query(Category).filter_by(id=category_id).one()
    if 'username' not in login_session:
        return redirect('/login')
    if category.user_id != login_session['user_id']:
        return "<script>function myFunction() {alert('You are not authorized to delete this category. Please create your own category in order to delete.');}</script><body onload='myFunction()''>"
    if request.method == 'POST':
        session.delete(category)
        session.commit()
        flash("The category is gone forever")
        return redirect(url_for('showCatalog'))
    else:
        return render_template(
            'deleteCategory.html', category_id=category_id, category=category)


@app.route('/catalog/<int:category_id>')
@app.route('/catalog/<int:category_id>/items')
def showItems(category_id):
    '''
    showItems use the category_id to select the right category and its items,
    and it shows them using the template: items.html for an authorized user
    and publicCategory.html for a user not logged in.
    '''
    category = session.query(Category).filter_by(id=category_id).one()
    creator = getUserInfo(category.user_id)
    items = session.query(Item).filter_by(category_id=category_id)
    if 'username' not in login_session or creator.id != login_session['user_id']:
        return render_template('publicCategory.html', items=items, category=category, creator=creator)
    else:
        return render_template('items.html', category=category, items=items, category_id=category_id)

@app.route("/catalog/<int:category_id>/items/new",
           methods=['GET', 'POST'])
def newItem(category_id):
    '''
    if GET: go to newItem.html
    if POST: create the new item
    '''
    if 'username' not in login_session:
        return redirect('/login')
    category = session.query(Category).filter_by(id=category_id).one()
    if login_session['user_id'] != category.user_id:
        return "<script>function myFunction() {alert('You are not authorized to add items to this category. Please create your own category in order to add items.');}</script><body onload='myFunction()''>"
    if request.method == 'POST':
        newItem = Item(name=request.form['name'],
                       description=request.form['description'],
                       category_id=category_id)
        session.add(newItem)
        session.commit()
        flash("A new Item, Dude!")
        return redirect(url_for('showItems', category_id=category_id))
    else:
        return render_template('newItem.html', category_id=category_id)

@app.route("/catalog/<int:category_id>/items/<int:item_id>/edit",
           methods=['GET', 'POST'])
def editItem(category_id,item_id):
    '''
    if GET: go to editItem.html of the selected item
    if POST: edit the selected item
    '''
    if 'username' not in login_session:
        return redirect('/login')
    item = session.query(Item).filter_by(id=item_id).one()
    category = session.query(Category).filter_by(id=category_id).one()
    if login_session['user_id'] != category.user_id:
        return "<script>function myFunction() {alert('You are not authorized to edit items to this cayegory. Please create your own category in order to edit items.');}</script><body onload='myFunction()''>"
    if request.method == 'POST':
        if request.form['name']:
            item.name = request.form['name']
        if request.form['description']:
            item.description = request.form['description']
        session.add(item)
        session.commit()
        flash("Item is changed")
        return redirect(url_for('showItems', category_id=category_id))
    else:
        return render_template(
            'editItem.html', category_id=category_id, item_id=item_id, item=item)

@app.route("/catalog/<int:category_id>/items/<int:item_id>/delete",
           methods=['GET', 'POST'])
def deleteItem(category_id,item_id):
    '''
    if GET: go to deleteItem.html of the selected item
    if POST: delete the selected item
    '''
    if 'username' not in login_session:
        return redirect('/login')
    category = session.query(Category).filter_by(id=category_id).one()
    item = session.query(Item).filter_by(id=item_id).one()
    if login_session['user_id'] != category.user_id:
        return "<script>function myFunction() {alert('You are not authorized to delete items to this category. Please create your own category in order to delete items.');}</script><body onload='myFunction()''>"
    if request.method == 'POST':
        session.delete(item)
        session.commit()
        flash("The item is gone forever")
        return redirect(url_for('showItems', category_id=category_id))
    else:
        return render_template(
            'deleteItem.html', category_id=category_id, item_id=item_id, item=item)

@app.route('/disconnect')
def disconnect():
    '''
    Disconnect the user based on provider (google or facebook)
    Delete login_session data and redirect to /catalog
    '''
    if 'provider' in login_session:
        if login_session['provider'] == 'google':
            gdisconnect()
            del login_session['gplus_id']
            del login_session['credentials']
        if login_session['provider'] == 'facebook':
            fbdisconnect()
            del login_session['facebook_id']
        del login_session['username']
        del login_session['email']
        del login_session['picture']
        del login_session['user_id']
        del login_session['provider']
        flash("You have successfully been logged out.")
        return redirect(url_for('showCatalog'))
    else:
        flash("You were not logged in")
        return redirect(url_for('showCatalog'))


if __name__ == "__main__":
    app.secret_key = 'asdeggio'
    app.debug = True
    app.run(host = '0.0.0.0', port = 5000)
