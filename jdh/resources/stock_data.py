# Installed packages
from flask import request
import yfinance as yf
import redis

# Local
from utils.symbols import symbols
import models as m

# Built in packages
from datetime import date
import os
import json

r = redis.Redis.from_url(os.getenv('REDIS_URL'))

def get(symbol=None):

    if not symbol:
        symbol=request.get_json()['symbol']

    if r.exists(symbol):
        print(f'Leyendo desde cache datos: {r.memory_usage(symbol)}', flush=True)
        data = json.loads(r.get(symbol))
    else:
        print('Consultando datos', flush=True)
        data = yf.Ticker(symbol).history(period="D1", start=str(date(2021, 5, 1)), end = str(date.today()))
        close_values = data.Close.to_list()
        labels=[str(date).replace(' 00:00:00', '') for date in data.index]
        data = dict(data=close_values, labels=labels, symbol=symbol)
        r.set(symbol, json.dumps(data))
        r.expire(symbol, 60*60*12)

    return data # {'symbol': symbol, 'data':close_values, 'labels':labels}


def restore(key):
    # 1) Reiniciar datos cacheados
    for symbol in symbols:
        if r.exists(symbol):
            r.delete(symbol)
    for cuenta in m.Cuenta.query.all():
    # 2) Iterar sobre cuentas
        balance = 0
        beneficio = 0
        for grafico in cuenta.graficos.all():
        # 2.1) Iterar sobre sus gráficos
            valor_actual = get(grafico.simbolo)['data'][-1]
            for posicion in grafico.posiciones.all():
            # 2.1.1) Iterar sobre sus posiciones
                if not posicion.cerrado:
                # 2.1.2) Si posición está abierta:
                    # Acutalizar balance
                    actual = posicion.volumen*valor_actual
                    balance += actual
                    beneficio += posicion.volumen*(valor_actual - posicion.valor_compra )
        # Actualizar balance
        cuenta.balance = balance
        cuenta.beneficio = beneficio
        #cuenta.update(dict(
        #    balance=balance,
        #    beneficio=(beneficio + cuenta.patrimonio) if beneficio else 0
        #))
        m.db.session.commit()

    return {'status': 1}
