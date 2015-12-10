from flask import Flask, render_template, request, redirect, url_for, jsonify
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from database_setup import Base, Restaurant, MenuItem

app = Flask(__name__)

# Connect to the database restaurant.db
engine = create_engine('sqlite:///restaurantmenu.db')
Base.metadata.bind = engine
DBSession = sessionmaker(bind=engine)
session = DBSession()

# Show all my restaurants
@app.route("/")
@app.route("/restaurants")
def showRestaurants():
   return render_template('restaurants.html', restaurants = restaurants)

@app.route("/restaurant/new")
def newRestaurants():
    return render_template('newRestaurant.html', restaurants = restaurants)

@app.route("/restaurant/<int:restaurant_id>/edit")
def editRestaurants(restaurant_id):
    # return "edit restauran %s" % restaurant_id
    return render_template('editRestaurant.html', restaurant = restaurants[restaurant_id-1])

@app.route("/restaurant/<int:restaurant_id>/delete")
def deleteRestaurants(restaurant_id):
    return render_template('deleteRestaurant.html', restaurant = restaurants[restaurant_id-1])

# Show the menu of the restaurant n(restaurant_id)
@app.route('/restaurant/<int:restaurant_id>')
@app.route('/restaurant/<int:restaurant_id>/menu')
def showMenu(restaurant_id):
    restaurant = session.query(Restaurant).filter_by(id=restaurant_id).one()
    items = session.query(MenuItem).filter_by(restaurant_id=restaurant_id)
    return render_template(
        'menu.html', restaurant=restaurant, items=items, restaurant_id=restaurant_id)

@app.route("/restaurant/<int:restaurant_id>/menu/new")
def newMenuItem(restaurant_id):
    # return "New Item for restauran %s" % restaurant_id
    return render_template('newMenuItem.html', items = items)

@app.route("/restaurant/<int:restaurant_id>/menu/<int:menu_id>/edit",
           methods=['GET', 'POST'])
def editMenuItem(restaurant_id,menu_id):
    item = session.query(MenuItem).filter_by(id=menu_id).one()
    if request.method == 'POST':
        # TODO: edit
        return
    else:
        return render_template(
            'editMenuItem.html', restaurant_id=restaurant_id, menu_id=menu_id, item=item)

@app.route("/restaurant/<int:restaurant_id>/menu/<int:menu_id>/delete",
           methods=['GET', 'POST'])
def deleteMenuItem(restaurant_id,menu_id):
    item = session.query(MenuItem).filter_by(id=menu_id).one()
    if request.method == 'POST':
        # TODO: delete
        return
    else:
        return render_template(
            'deleteMenuItem.html', restaurant_id=restaurant_id, menu_id=menu_id, item=item)

if __name__ == "__main__":
    app.debug = True
    app.run(host = '0.0.0.0', port = 5000)

