import sqlite3
from sqlite3 import Connection

import pandas as pd
from flasgger import Swagger
from flask import Flask, request
from tensorflow.keras.saving import load_model

model = load_model('../model/model.keras')
# Коэффициент, при котором достигается получение результата
THRESHOLD = 0.9
COLUMNS = ['Энергия',
           'Белок',
           'Общие липиды (жиры)',
           'Углеводы',
           'Пищевые волокна',
           'Общие сахара',
           'Натрий, Na']

app = Flask(__name__)
swagger = Swagger(app)


def db_connect() -> Connection:
    return sqlite3.connect("db.sqlite")


def create_table() -> None:
    connect = db_connect()
    cursor = connect.cursor()

    cursor.execute(
        '''
                CREATE TABLE IF NOT EXISTS food_data (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    energy REAL NOT NULL,
                    protein REAL NOT NULL,
                    fats REAL NOT NULL,
                    carbohydrates REAL NOT NULL,
                    fiber REAL NOT NULL,
                    sugars REAL NOT NULL,
                    sodium_na REAL NOT NULL,
                    health_score INTEGER NOT NULL
                )
        '''
    )
    connect.commit()
    connect.close()


def get_data(df: pd.DataFrame):
    connect = db_connect()
    cursor = connect.cursor()

    data = (
        df['Энергия'][0],
        df['Белок'][0],
        df['Общие липиды (жиры)'][0],
        df['Углеводы'][0],
        df['Пищевые волокна'][0],
        df['Общие сахара'][0],
        df['Натрий, Na'][0]
    )
    cursor.execute(
        '''
            SELECT food_data.health_score
            FROM food_data
            WHERE energy = ? AND protein = ? AND fats = ? AND carbohydrates = ?
            AND fiber = ? AND sugars = ? AND sodium_na = ?
        ''', data
    )
    result = cursor.fetchone()
    connect.close()
    return result


def get_score(df: pd.DataFrame) -> int:
    x = df.values
    prediction = model.predict(df.values)
    score = (prediction < THRESHOLD).astype(int).flatten()[0]

    connect = db_connect()
    cursor = connect.cursor()
    cursor.execute(
        '''
            INSERT INTO food_data (
                energy, 
                protein, 
                fats, 
                carbohydrates, 
                fiber,
                sugars, 
                sodium_na,
                health_score
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            df['Энергия'][0],
            df['Белок'][0],
            df['Общие липиды (жиры)'][0],
            df['Углеводы'][0],
            df['Пищевые волокна'][0],
            df['Общие сахара'][0],
            df['Натрий, Na'][0],
            int(score)
        )
    )
    connect.commit()
    connect.close()
    return int(score)


@app.route('/', methods=['POST'])
def get_health():
    """
    Получение оценки продукта
    ---
    parameters:
      - name: body
        in: body
        description: Продукт для оценки
        required: true
        schema:
          type: object
          properties:
            Энергия:
              type: number
              example: 100.0
            Белок:
              type: number
              example: 5.0
            Общие липиды (жиры):
              type: number
              example: 2.0
            Углеводы:
              type: number
              example: 20.0
            Пищевые волокна:
              type: number
              example: 3.0
            Общие сахара:
              type: number
              example: 10.0
            Натрий, Na:
              type: number
              example: 0.5
    responses:
      200:
        description: Оценка продукта
        schema:
          type: object
          properties:
            result:
              type: string
              description: Сообщение о безопасности продукта
              example: Продукт безопасен для употребления!
    """
    data = request.get_json()
    df = pd.DataFrame([data])
    df = df.reindex(columns=COLUMNS, fill_value=0)

    score = get_data(df)
    if score:
        score = score[0]
    else:
        score = get_score(df)
    msg = 'Продукт небезопасно употреблять!'
    if int(score) == 1:
        msg = 'Продукт безопасен для употребления!!'
    response = {
        'result': msg
    }
    return response


if __name__ == '__main__':
    create_table()
    app.run(debug=True)
