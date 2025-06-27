from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from .db import get_db

auth = Blueprint('auth', __name__)

@auth.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        db = get_db()
        user = db.execute(
            'SELECT * FROM usuarios WHERE username = ? AND password = ?',
            (username, password)
        ).fetchone()

        if user:
            session['usuario'] = user['username']
            return redirect(url_for('main.index'))
        else:
            flash('Usuario o contraseña incorrectos')
            return redirect(url_for('auth.login'))

    return render_template('login.html')

@auth.route('/logout')
def logout():
    session.pop('usuario', None)
    return redirect(url_for('auth.login'))
