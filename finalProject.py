from flask import Flask, render_template, request, redirect, url_for, jsonify, flash
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from database_setup import Base, Restaurant, MenuItem

app = Flask(__name__)

# Connect to the database restaurant.db
engine = create_engine('sqlite:///restaurantmenu.db')
Base.metadata.bind = engine
DBSession = sessionmaker(bind=engine)
session = DBSession()

@app.route('/restaurants/JSON')
def restaurantJSON():
    restaurants = session.query(Restaurant).all()
    return jsonify(Restaurants=[i.serialize for i in restaurants])

@app.route('/restaurant/<int:restaurant_id>/menu/JSON')
def restaurantMenuJSON(restaurant_id):
    restaurant = session.query(Restaurant).filter_by(id=restaurant_id).one()
    items = session.query(MenuItem).filter_by(restaurant_id=restaurant_id).all()
    return jsonify(MenuItems=[i.serialize for i in items])


# ADD JSON ENDPOINT HERE
@app.route('/restaurant/<int:restaurant_id>/menu/<int:menu_id>/JSON')
def menuItemJSON(restaurant_id, menu_id):
    menuItem = session.query(MenuItem).filter_by(id=menu_id).one()
    return jsonify(MenuItem=menuItem.serialize)

# Show all my restaurants
@app.route("/")
@app.route("/restaurants")
def showRestaurants():
    restaurants = session.query(Restaurant).all()
    print restaurants
    return render_template('restaurants.html', restaurants=restaurants)

@app.route("/restaurant/new",
           methods=['GET', 'POST'])
def newRestaurants():
    if request.method == 'POST':
        newRestaurant = Restaurant(name=request.form['name'])
        session.add(newRestaurant)
        session.commit()
        flash("A new Restaurant, Dude!")
        return redirect(url_for('showRestaurants'))
    else:
        return render_template('newRestaurant.html')

@app.route("/restaurant/<int:restaurant_id>/edit",
           methods=['GET', 'POST'])
def editRestaurants(restaurant_id):
    restaurant = session.query(Restaurant).filter_by(id=restaurant_id).one()
    if request.method == 'POST':
        if request.form['name']:
            restaurant.name = request.form['name']
        session.add(restaurant)
        session.commit()
        flash("Restaurant is changed")
        return redirect(url_for('showRestaurants'))
    else:
        return render_template(
            'editRestaurant.html', restaurant_id=restaurant_id, restaurant=restaurant)

@app.route("/restaurant/<int:restaurant_id>/delete",
           methods=['GET', 'POST'])
def deleteRestaurants(restaurant_id):
    restaurant = session.query(Restaurant).filter_by(id=restaurant_id).one()
    if request.method == 'POST':
        session.delete(restaurant)
        session.commit()
        flash("The restaurant is gone forever")
        return redirect(url_for('showRestaurants'))
    else:
        return render_template(
            'deleteRestaurant.html', restaurant_id=restaurant_id, restaurant=restaurant)


@app.route('/restaurant/<int:restaurant_id>')
@app.route('/restaurant/<int:restaurant_id>/menu')
def showMenu(restaurant_id):
    '''
    showMenu use the restaurant_id to select the right restaurant and its menu,
    and it shows them using the template: menu.html
    '''
    restaurant = session.query(Restaurant).filter_by(id=restaurant_id).one()
    items = session.query(MenuItem).filter_by(restaurant_id=restaurant_id)
    return render_template(
        'menu.html', restaurant=restaurant, items=items, restaurant_id=restaurant_id)

@app.route("/restaurant/<int:restaurant_id>/menu/new",
           methods=['GET', 'POST'])
def newMenuItem(restaurant_id):
    if request.method == 'POST':
        newItem = MenuItem(name=request.form['name'],
                           description=request.form['description'],
                           price=request.form['price'],
                           course=request.form['course'],
                           restaurant_id=restaurant_id)
        session.add(newItem)
        session.commit()
        flash("A new Item, Dude!")
        return redirect(url_for('showMenu', restaurant_id=restaurant_id))
    else:
        return render_template('newMenuItem.html', restaurant_id=restaurant_id)

@app.route("/restaurant/<int:restaurant_id>/menu/<int:menu_id>/edit",
           methods=['GET', 'POST'])
def editMenuItem(restaurant_id,menu_id):
    item = session.query(MenuItem).filter_by(id=menu_id).one()
    if request.method == 'POST':
        if request.form['name']:
            item.name = request.form['name']
        if request.form['description']:
            item.description = request.form['description']
        if request.form['price']:
            item.price = request.form['price']
        if request.form['course']:
            item.course = request.form['course']
        session.add(item)
        session.commit()
        flash("Item is changed")
        return redirect(url_for('showMenu', restaurant_id=restaurant_id))
    else:
        return render_template(
            'editMenuItem.html', restaurant_id=restaurant_id, menu_id=menu_id, item=item)

@app.route("/restaurant/<int:restaurant_id>/menu/<int:menu_id>/delete",
           methods=['GET', 'POST'])
def deleteMenuItem(restaurant_id,menu_id):
    item = session.query(MenuItem).filter_by(id=menu_id).one()
    if request.method == 'POST':
        session.delete(item)
        session.commit()
        flash("The item is gone forever")
        return redirect(url_for('showMenu', restaurant_id=restaurant_id))
    else:
        return render_template(
            'deleteMenuItem.html', restaurant_id=restaurant_id, menu_id=menu_id, item=item)

if __name__ == "__main__":
    app.secret_key = 'asdeggio'
    app.debug = True
    app.run(host = '0.0.0.0', port = 5000)

