from flask import Flask, render_template, request, session, redirect, url_for
from sqlalchemy import create_engine
from werkzeug.security import generate_password_hash, check_password_hash

tweeter = Flask(__name__)
tweeter.config["SECRET_KEY"] = "group 3 is cool!"
engine = create_engine("sqlite:///tweeter.db")


@tweeter.route("/")
def index():
    tweets = []
    if "username" in session:
        query = f"""
        SELECT DISTINCT u.id, u.picture, u.username, t.tweet
        FROM tweets t
        INNER JOIN users u ON t.user_id=u.id
        INNER JOIN follows f ON f.followee_id=u.id
        WHERE (f.follower_id = {session['user_id']}) OR 
        (u.id = {session['user_id']}) 
        ORDER BY t.id DESC
        """

        with engine.connect() as connection:
            tweets = connection.execute(query).fetchall()

    return render_template("index.html", tweets=tweets)


@tweeter.route("/register")
def register():
    return render_template("register.html")


@tweeter.route("/register", methods=["POST"])
def handle_register():
    username=request.form["username"]
    password=request.form["password"]
    picture=request.form["picture"]

    hashed_password = generate_password_hash(password)

    insert_query = f"""
    INSERT INTO users(username, picture, password)
    VALUES ('{username}', '{picture}', '{hashed_password}')
    """

    with engine.connect() as connection:
        connection.execute(insert_query)

        return redirect(url_for("index"))


@tweeter.route("/users")
def users():
    if "user_id" not in session:
        return render_template("403.html"), 403    
    else:
        query = f"""
        SELECT id, username, picture
        FROM users
        WHERE id != {session['user_id']}
        """

        follows = f"""
        SELECT followee_id
        FROM follows 
        WHERE follower_id = {session['user_id']}
        """

        with engine.connect() as connection:
            users = connection.execute(query)
            following = connection.execute(follows)

            ids = []

            for row in following:
                for field in row:
                    ids.append(field)

            return render_template("users.html", users=users, ids=ids)


@tweeter.route("/users/<user_id>")
def user_detail(user_id):
    query = f"""
    SELECT id, username, picture
    FROM users
    where id={user_id}
    """

    tweets_query = f"""
    SELECT tweet
    FROM tweets
    WHERE user_id={user_id}
    """

    with engine.connect() as connection:
        user = connection.execute(query).fetchone()
        tweets = connection.execute(tweets_query).fetchall()

        if user:
            return render_template("user_detail.html", user=user, tweets=tweets)
        else:
            return render_template("404.html"), 404


@tweeter.route("/login")
def login():
    return render_template("login.html")

@tweeter.route("/login", methods=["POST"])
def handle_login():
    username=request.form["username"]
    password=request.form["password"]

    login_query = f"""
    SELECT password, id
    FROM users
    WHERE username='{username}'
    """

    with engine.connect() as connection:
        user = connection.execute(login_query).fetchone()

        if user and check_password_hash(user[0], password):
            session["user_id"] = user[1]
            session["username"] = username
            return redirect(url_for("index"))
        else:
            return render_template("404.html"), 404


@tweeter.route("/logout")
def logout():
    session.pop("username")
    session.pop("user_id")

    return redirect(url_for("index"))


@tweeter.route("/tweet", methods=["POST"])
def handle_tweet():
    tweet=request.form["tweet"]

    insert_query = f"""
    INSERT INTO tweets(tweet, user_id)
    VALUES ('{tweet}', {session['user_id']})
    """

    with engine.connect() as connection:
        connection.execute(insert_query)

        return redirect(url_for("index"))


@tweeter.route("/follow/<followee>")
def follow(followee):
    if "user_id" not in session:
        return render_template("403.html"), 403    
    else:
        follower = session["user_id"]

        insert_query = f"""
        INSERT INTO follows(follower_id, followee_id)
        VALUES ({follower}, {followee})
        """

        with engine.connect() as connection:
            connection.execute(insert_query)

            return redirect(url_for("index"))


@tweeter.route("/unfollow/<followee>")
def unfollow(followee):
    if "user_id" not in session:
        return render_template("403.html"), 403

    else:
        unfollow_query = f"""
        DELETE FROM follows
        WHERE follower_id={session["user_id"]} AND followee_id={followee}
        """
        with engine.connect() as connection:
            connection.execute(unfollow_query)

            return redirect(url_for("users"))


@tweeter.route("/messages")
def messages():
    if "user_id" not in session:
        return render_template("403.html"), 403    
    else:
        follower = session["user_id"]
        follow_query = f"""
        SELECT follows.followee_id, users.username , users.picture
        FROM follows 
        INNER JOIN users 
        ON follows.followee_id=users.id
        WHERE follows.follower_id={follower}"""
        with engine.connect() as connection:
            followees = connection.execute(follow_query)

            return render_template("messanger.html", followees=followees)


@tweeter.route("/messages/<followee_id>")
def private_messages(followee_id):
    if "user_id" not in session:
        return render_template("403.html"), 403    
    else:
        follower = session["user_id"]
        
        messages_query = f"""
        SELECT m.text, u.id, u.username, u.picture  
        FROM messages m
        INNER JOIN users u
        ON m.from_id = u.id 
        WHERE (m.from_id={follower} AND m.to_id={followee_id})
        OR (m.to_id={follower} AND m.from_id={followee_id})
        ORDER BY m.id"""

        with engine.connect() as connection:
            messages = connection.execute(messages_query)

            return render_template("private_message.html", messages = messages, followee_id = followee_id)


@tweeter.route("/messages/<followee_id>", methods=["POST"])
def write_message(followee_id):
    if "user_id" not in session:
        return render_template("403.html"), 403    
    else:
        message=request.form["message"]

        send_message_query = f"""
        INSERT INTO messages(text, from_id, to_id)
        VALUES ('{message}', {session['user_id']}, {followee_id})
        """

        with engine.connect() as connection:
            connection.execute(send_message_query)

            return redirect(url_for("private_messages", followee_id = followee_id))


@tweeter.route('/search', methods=["POST"])
def search():
    if "user_id" not in session:
        return render_template("403.html"), 403
    else:
        searched = request.form["searched"]

        query = f"""
        SELECT t.user_id, t.tweet, u.username, u.picture
        FROM tweets t
        INNER JOIN users u
        ON t.user_id = u.id
        WHERE tweet LIKE '%{searched}%'
        """

        with engine.connect() as connection:
            tweets = connection.execute(query).fetchall()

        return render_template("search.html", searched=searched, tweets=tweets)


tweeter.run(debug=True)