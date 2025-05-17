from flask import Flask, render_template, redirect, request, flash
from flask_login import LoginManager, login_user, logout_user, current_user, login_required
from data.users import User
from data.news import News
from data.db_session import global_init, create_session
from forms.user import RegisterForm, LoginForm
from news_api import NewsAggregator  # Правильный импорт
import logging  # Добавьте в начало файлов


app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key_here'
login_manager = LoginManager(app)
login_manager.login_view = 'login'
logger = logging.getLogger(__name__)
global_init("db/news.db")


@app.route("/")
def index():
    tag_filter = request.args.get('tag', '').strip()
    db_sess = create_session()

    query = db_sess.query(News)
    if tag_filter:
        query = query.filter(News.tags.ilike(f"%{tag_filter}%"))

    news_list = query.order_by(News.published_at.desc()).limit(100).all()
    return render_template("index.html", news=news_list, current_tag=tag_filter)

@app.route('/saved')
@login_required
def saved_articles():
    db_sess = create_session()
    saved_news = current_user.saved_articles
    return render_template("saved.html", saved=saved_news)


@app.route('/save/<int:news_id>')
@login_required
def save_article(news_id):
    db_sess = create_session()
    try:
        user = db_sess.merge(current_user._get_current_object())
        news = db_sess.get(News, news_id)

        if news and news not in user.saved_articles:
            user.saved_articles.append(news)
            db_sess.commit()
            flash('Статья сохранена', 'success')
        else:
            flash('Статья уже сохранена', 'warning')
    except Exception as e:
        db_sess.rollback()
        flash('Ошибка сохранения', 'danger')
        logger.error(f"Ошибка: {str(e)}")
    finally:
        db_sess.close()

    return redirect(request.referrer or '/')

@app.route('/unsave/<int:news_id>')
@login_required
def unsave_article(news_id):
    db_sess = create_session()
    try:
        user = db_sess.merge(current_user._get_current_object())
        news = db_sess.get(News, news_id)

        if news and news in user.saved_articles:
            user.saved_articles.remove(news)
            db_sess.commit()
            flash('Статья удалена', 'success')
        else:
            flash('Статья не найдена', 'warning')
    except Exception as e:
        db_sess.rollback()
        flash('Ошибка удаления', 'danger')
    finally:
        db_sess.close()

    return redirect(request.referrer or '/')



@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        db_sess = create_session()
        user = db_sess.query(User).filter(User.email == form.email.data).first()
        if user and user.check_password(form.password.data):
            login_user(user, remember=form.remember_me.data)
            return redirect("/")
        return render_template('login.html', message="Неверный email или пароль", form=form)
    return render_template('login.html', form=form)


@app.route('/register', methods=['GET', 'POST'])
def register():
    form = RegisterForm()
    if form.validate_on_submit():
        if form.password.data != form.password_again.data:
            return render_template('register.html', form=form, message="Пароли не совпадают")
        db_sess = create_session()
        if db_sess.query(User).filter(User.email == form.email.data).first():
            return render_template('register.html', form=form, message="Пользователь уже существует")
        user = User(name=form.name.data, email=form.email.data)
        user.set_password(form.password.data)
        db_sess.add(user)
        db_sess.commit()
        login_user(user)
        return redirect("/")
    return render_template('register.html', form=form)


@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect('/')


@login_manager.user_loader
def load_user(user_id):
    db_sess = create_session()
    return db_sess.get(User, user_id)


@app.cli.command("fetch-news")
def fetch_news_command():
    aggregator = NewsAggregator()
    aggregator.fetch_news()
    print("Новости загружены")

@app.errorhandler(500)
def internal_error(error):
    return render_template("500.html"), 500




if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)