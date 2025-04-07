import requests
from flask import current_app
from datetime import datetime
from .models import Transacao
from sqlalchemy import exc

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


def calcular_saldo_usd_usuario(user_id):
    """
    Calcula o saldo em USD para um usuário com base em suas transações
    """
    try:
        transacoes = Transacao.query.filter_by(user_id=user_id).all()
        
        saldo_usd = 0
        
        for transacao in transacoes:
            if transacao.tipo == 'compra':
                saldo_usd += transacao.quantidade_usd
            else:  # venda
                saldo_usd -= transacao.quantidade_usd
        
        return saldo_usd
    except exc.SQLAlchemyError as e:
        current_app.logger.error(f"Erro ao calcular saldo: {str(e)}")
        return None


def validar_transacao_compra(user_id, valor_brl):
    """
    Valida se uma transação de compra pode ser realizada
    """
    # Para compra em BRL, a única validação é se o valor é positivo
    if valor_brl <= 0:
        return False, "O valor da compra deve ser maior que zero"
    
    return True, None


def validar_transacao_venda(user_id, quantidade_usd):
    """
    Valida se uma transação de venda pode ser realizada
    """
    # Validação básica
    if quantidade_usd <= 0:
        return False, "A quantidade de USD deve ser maior que zero"
    
    # Verifica se o usuário tem saldo suficiente
    saldo_usd = calcular_saldo_usd_usuario(user_id)
    if saldo_usd is None:
        return False, "Erro ao verificar saldo do usuário"
    
    if saldo_usd < quantidade_usd:
        return False, f"Saldo insuficiente. Saldo atual: {saldo_usd} USD"
    
    return True, None