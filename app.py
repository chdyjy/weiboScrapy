from flask import Flask, render_template, request, jsonify, flash
from flask_wtf import FlaskForm
from wtforms import Form, StringField, validators
from wtforms.validators import DataRequired
from flask import json
import os
import crawler

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY') or 'a_very_secret_key_for_development_only'


class SearchForm(Form):
    search_input = StringField('Search Input', [validators.Length(min=1)])
    cookie = StringField('Cookie', [validators.Length(min=1)])


@app.route('/', methods=['GET'])
def index():
    form = SearchForm()
    return render_template('index.html', form=form)


@app.route('/get_hot_search_list', methods=['POST'])
def get_hot_search_list():
    try:
        user_cookie = request.json.get('userCookie', None)

        if not user_cookie:
            return jsonify({'error': 'No cookie provided'}), 400

        # Assuming your crawler method accepts the cookie as an argument
        hot_search_list = crawler.get_hot_search_list(user_cookie)

        return jsonify(hot_search_list)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/fetch_data', methods=['POST'])
def fetch_data():
    data = request.get_json()
    if not data:
        return jsonify({'error': 'No data provided'}), 400

    form = SearchForm(data=data)
    if form.validate():
        try:
            raw_result = crawler.extract_hot_search_data(cookie=form.cookie.data, search_text=form.search_input.data)
            result = json.dumps(raw_result, ensure_ascii=False)
            # result = raw_result.encode().decode('unicode_escape')
            return result
        except Exception as e:
            return jsonify({'error': str(e)}), 500
    else:
        return jsonify({'error': 'Validation failed'}), 400

if __name__ == '__main__':
    app.run(debug=True, port=os.getenv("PORT", default=5000), host='0.0.0.0')
