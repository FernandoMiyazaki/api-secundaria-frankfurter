import requests
from flask import current_app
from datetime import datetime

def consultar_cotacao_frankfurt(base='USD', moeda='BRL'):
    """
    Consulta a API externa do Frankfurter para obter a cotação atual
    """
    try:
        url = f"{current_app.config['FRANKFURTER_EXTERNAL_API']}/latest?base={base}&symbols={moeda}"
        response = requests.get(url)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        current_app.logger.error(f"Erro ao consultar Frankfurter: {str(e)}")
        return None
    except ValueError as e:
        current_app.logger.error(f"Erro ao processar resposta do Frankfurter: {str(e)}")
        return None


def parse_cotacao_data(data):
    """
    Converte o resultado da API para o formato do nosso banco de dados
    """
    if not data:
        return None
    
    try:
        base = data.get('base')
        date_str = data.get('date')
        if not base or not date_str:
            return None
        
        rates = data.get('rates', {})
        result = []
        
        for moeda, valor in rates.items():
            data_obj = datetime.strptime(date_str, '%Y-%m-%d').date()
            result.append({
                'base': base,
                'moeda': moeda,
                'valor': valor,
                'data': data_obj
            })
        
        return result
    except Exception as e:
        current_app.logger.error(f"Erro ao processar dados de cotação: {str(e)}")
        return None


def converter_valor(valor, cotacao, operacao='compra'):
    """
    Converte valores entre moedas
    operacao: 'compra' (BRL para USD) ou 'venda' (USD para BRL)
    """
    if operacao == 'compra':
        # Converte BRL para USD
        return valor / cotacao
    else:
        # Converte USD para BRL
        return valor * cotacao