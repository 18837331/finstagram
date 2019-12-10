from flask import Flask, render_template, request, session, redirect, url_for, send_file
import os
import uuid
import hashlib
import pymysql.cursors
from functools import wraps
import time

app = Flask(__name__)
app.secret_key = "super secret key"
IMAGES_DIR = os.path.join(os.getcwd(), "images")

connection = pymysql.connect(host="localhost",
                             user="root",
                             password="bowen",
                             db="finstagram",
                             charset="utf8mb4",
                             port=3306,
                             cursorclass=pymysql.cursors.DictCursor,
                             autocommit=True)


def login_required(f):
    @wraps(f)
    def dec(*args, **kwargs):
        if not "username" in session:
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return dec


@app.route("/")
def index():
    if "username" in session:
        return redirect(url_for("home"))
    return render_template("index.html")


@app.route("/home")
@login_required
def home():
    return render_template("home.html", username=session["username"])


@app.route("/upload", methods=["GET"])
@login_required
def upload():
    return render_template("upload.html")


@app.route("/images", methods=["GET"])
@login_required
def images():
    query = "select * from photo where allFollowers=True and photoPoster in (select username_followed from follow where username_follower=%s)"
    with connection.cursor() as cursor:
        cursor.execute(query,session["username"])
    data = cursor.fetchall()
    query2="select * from photo where photoID in (select photoID from sharedwith where (groupOwner,groupName) in (select owner_username , groupName from belongto where member_username=%s))"
    with connection.cursor() as cursor:
        cursor.execute(query2,session["username"])
    data2 = cursor.fetchall()

    return render_template("images.html", images=data, images2=data2)


@app.route("/view", methods=["GET","POST"])
@login_required
def view():
    ID = request.args['image']
    query ="select * from person inner join photo on photo.photoPoster=person.username where photoID=%s"
    query2="select * from tagged inner join person on tagged.username= person.username where photoID=%s and tagstatus=True"
    with connection.cursor() as cursor:
        cursor.execute(query,ID)
    data = cursor.fetchone()
    likes="select * from likes inner join person on likes.username= person.username where photoID=%s"
    with connection.cursor() as cursor:
        cursor.execute(likes,ID)
        data2 = cursor.fetchall()

    with connection.cursor() as cursor:
        cursor.execute(query2,ID)
        data3 = cursor.fetchall()

    return render_template("imgDetails.html",image=data, taggs=data3, likes=data2)


@app.route("/image/<image_name>", methods=["GET"])
def image(image_name):
    image_location = os.path.join(IMAGES_DIR, image_name)
    if os.path.isfile(image_location):
        return send_file(image_location, mimetype="image/jpg")


@app.route("/login", methods=["GET"])
def login():
    return render_template("login.html")


@app.route("/register", methods=["GET"])
def register():
    return render_template("register.html")


@app.route("/loginAuth", methods=["POST"])
def loginAuth():
    if request.form:
        requestData = request.form
        username = requestData["username"]
        plaintextPasword = requestData["password"]
        hashedPassword = hashlib.sha256(plaintextPasword.encode("utf-8")).hexdigest()

        with connection.cursor() as cursor:
            query = "SELECT * FROM person WHERE username = %s AND password = %s"
            cursor.execute(query, (username, hashedPassword))
        data = cursor.fetchone()
        if data:
            session["username"] = username
            return redirect(url_for("home"))

        error = "Incorrect username or password."
        return render_template("login.html", error=error)

    error = "An unknown error has occurred. Please try again."
    return render_template("login.html", error=error)


@app.route("/registerAuth", methods=["POST"])
def registerAuth():
    if request.form:
        requestData = request.form
        username = requestData["username"]
        plaintextPasword = requestData["password"]
        hashedPassword = hashlib.sha256(plaintextPasword.encode("utf-8")).hexdigest()
        firstName = requestData["fname"]
        lastName = requestData["lname"]
        try:
            with connection.cursor() as cursor:
                query = "INSERT INTO person (username, password, firstName, lastName) VALUES (%s, %s, %s, %s)"
                cursor.execute(query, (username, hashedPassword, firstName, lastName))
        except pymysql.err.IntegrityError:
            error = "%s is already taken." % (username)
            return render_template('register.html', error=error)

        return redirect(url_for("login"))

    error = "An error has occurred. Please try again."
    return render_template("register.html", error=error)


@app.route("/logout", methods=["GET"])
def logout():
    session.pop("username")
    return redirect("/")


@app.route("/uploadImage", methods=["POST"])
@login_required
def upload_image():
    if request.files:
        image_file = request.files.get("imageToUpload", "")
        image_name = image_file.filename
        filepath = os.path.join(IMAGES_DIR, image_name)
        image_file.save(filepath)
        caption=request.form["caption"]
        all_followers=request.form["options"]
        groupName=request.form["share"]
        query = "INSERT INTO `Photo`(`postingdate`, `filepath`, `allFollowers`, `caption`, `photoPoster`) VALUES (%s,%s,%s,%s,%s);"
        with connection.cursor() as cursor:
            cursor.execute(query, (time.strftime('%Y-%m-%d %H:%M:%S'), image_name, all_followers,caption,session['username']))
        message = "Image has been successfully uploaded."
        query2= "select max(photoID) as photoID from photo"
        with connection.cursor() as cursor:
            cursor.execute(query2)
        ID=cursor.fetchone()
        photoID=ID["photoID"]
        query3= "insert into sharedwith value(%s,%s,%s)"
        with connection.cursor() as cursor:
            cursor.execute(query3,(session['username'],groupName,photoID))
        return render_template("upload.html", message=message)
    else:
        message = "Failed to upload image."
        return render_template("upload.html", message=message)




@app.route("/follow", methods=["GET"])
@login_required
def follow():
    self = session["username"]
    with connection.cursor() as cursor:
        query = 'SELECT DISTINCT username FROM Person where username not in (select username_followed from follow where username_follower=%s)'
        cursor.execute(query,self )
        data = cursor.fetchall()
        cursor.close()
        return render_template('follow.html', user_list=data)


@app.route('/add', methods=["GET", "POST"])
@login_required
def add():
    username=request.args['user']
    query="INSERT INTO `Follow`(`username_followed`, `username_follower`, `followstatus`) VALUES (%s,%s,False)"
    with connection.cursor() as cursor:
        self=session['username']
        cursor.execute(query,(username, self))
    message = "follow succeed"
    return render_template("home.html", username=session["username"])


@app.route('/manageFollow', methods=["GET", "POST"])
@login_required
def show():
    self=session["username"]
    query="select username_follower from follow where username_followed=%s and followstatus=false"
    with connection.cursor() as cursor:
        cursor.execute(query, self)
        data = cursor.fetchall()
        cursor.close()
    return render_template('manageFollow.html', user_list=data)


@app.route('/accept', methods=["GET", "POST"])
@login_required
def accept():
    query="UPDATE follow SET followstatus=True WHERE username_followed=%s and username_follower=%s;"
    query2="delete from follow where username_followed=%s and username_follower=%s"
    self=session['username']
    followed = request.args['user']
    with connection.cursor() as cursor:
        if request.args['choice']=="accept":
            cursor.execute(query,(self,followed))
        else:
            cursor.execute(query2, (self, followed))
    return render_template("home.html",username=session["username"])


@app.route('/friendfroup', methods=["GET", "POST"])
@login_required
def friendgroup():
    return render_template("friendfroup.html", username=session["username"])


@app.route('/create', methods=["GET", "POST"])
@login_required
def create():
    return render_template("createFriendgroup.html")


@app.route('/createf', methods=["POST","GET"])
@login_required
def createf():
    if request.method == 'POST':
        requestData = request.form
        groupname = requestData.get("groupname")
        description = requestData.get("description")
        self = session['username']
        with connection.cursor() as cursor:
            query = "INSERT INTO `Friendgroup`(`groupOwner`, `groupName`, `description`) VALUES (%s,%s,%s);"
            cursor.execute(query, (self, groupname, description))
        query2 = "INSERT INTO `BelongTo`(`member_username`, `owner_username`, `groupName`) VALUES (%s,%s,%s);"
        with connection.cursor() as cursor:
            cursor.execute(query2, (self, self, groupname))
        return render_template("friendfroup.html", username=session["username"])


@app.route("/manageChoice", methods=["GET"])
@login_required
def manageChoice():
    with connection.cursor() as cursor:
        query = 'SELECT DISTINCT groupname FROM Friendgroup where groupOwner=%s'
        self = session['username']
        cursor.execute(query,self)
        data = cursor.fetchall()
        cursor.close()
        return render_template('manageFriendgroup.html', friendgroup_list=data)


@app.route("/manage2", methods=["GET"])
@login_required
def manage2():
    self = session['username']
    name = request.args['group']
    query="select member_username as username from BelongTo where owner_username=%s and groupName=%s"
    query2="select username from person where username not in (select member_username from BelongTo where owner_username=%s and groupName=%s)"
    choice=request.args['choice']
    session["choice"]=choice
    session["group"]=name
    with connection.cursor() as cursor:
        if choice=="delete":
            cursor.execute(query, (self, name))
            data = cursor.fetchall()
            str="remove"
        else:
            cursor.execute(query2,(self, name))
            data = cursor.fetchall()
            str="add"

    return render_template("manage3.html",members=data,choice=str, group=name)


@app.route("/manage3", methods=["GET"])
@login_required
def manage3():
    name = session['group']
    self = session['username']
    target = request.args['name']
    choice =session['choice']
    query2 = "INSERT INTO `BelongTo`(`member_username`, `owner_username`, `groupName`) VALUES (%s,%s,%s);"
    query = "DELETE from BelongTo where member_username=%s and groupName=%s and owner_username=%s"
    with connection.cursor() as cursor:
        if choice=="delete":
            cursor.execute(query, (target, name ,self))
        else:
            cursor.execute(query2,(target, self, name))

    session.pop("group")
    session.pop("choice")
    return render_template("friendfroup.html")


if __name__ == "__main__":
    if not os.path.isdir("images"):
        os.mkdir(IMAGES_DIR)
    app.run()
