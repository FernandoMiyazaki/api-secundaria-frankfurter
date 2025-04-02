from flask import Blueprint, request, jsonify
from flask_restx import Resource, fields
from datetime import datetime, date
from .extensions import db, api
from .models import Cotacao
from .utils import consultar_cotacao_frankfurt, parse_cotacao_data, converter_valor

# Blueprint
main = Blueprint('main', __name__)

# Namespace
ns_cotacao = api.namespace('cotacao', description='Operações relacionadas a cotações')

# Models
cotacao_model = api.model('Cotacao', {
    'amount': fields.Float(description='Valor base'),
    'base': fields.String(description='Moeda base'),
    'date': fields.String(description='Data da cotação'),
    'rates': fields.Raw(description='Taxas de conversão')
})

conversao_model = api.model('Conversao', {
    'base': fields.String(description='Moeda base', required=True),
    'moeda': fields.String(description='Moeda de destino', required=True),
    'valor': fields.Float(description='Valor a ser convertido', required=True)
})

resultado_conversao_model = api.model('ResultadoConversao', {
    'valor_original': fields.Float(description='Valor original'),
    'moeda_original': fields.String(description='Moeda original'),
    'valor_convertido': fields.Float(description='Valor convertido'),
    'moeda_destino': fields.String(description='Moeda de destino'),
    'cotacao': fields.Float(description='Cotação utilizada'),
    'data': fields.String(description='Data da cotação')
})


@ns_cotacao.route('/')
class CotacaoResource(Resource):
    @ns_cotacao.doc('get_cotacao')
    @ns_cotacao.response(200, 'Sucesso', cotacao_model)
    @ns_cotacao.response(500, 'Erro ao consultar cotação')
    def get(self):
        """Obtém a cotação atual do USD em BRL"""
        # Verifica se já temos a cotação de hoje
        hoje = date.today()
        cotacao_hoje = Cotacao.query.filter_by(
            base='USD', moeda='BRL', data=hoje
        ).first()
        
        if cotacao_hoje:
            return cotacao_hoje.to_dict()
        
        # Se não tiver, consulta a API externa
        cotacao_data = consultar_cotacao_frankfurt()
        if not cotacao_data:
            return {'message': 'Erro ao consultar cotação externa'}, 500
        
        # Processa os dados e salva no banco
        dados_cotacao = parse_cotacao_data(cotacao_data)
        if not dados_cotacao:
            return {'message': 'Erro ao processar dados de cotação'}, 500
        
        try:
            for dado in dados_cotacao:
                cotacao = Cotacao(
                    base=dado['base'],
                    moeda=dado['moeda'],
                    valor=dado['valor'],
                    data=dado['data']
                )
                db.session.merge(cotacao)
            
            db.session.commit()
            return cotacao_data
        except Exception as e:
            db.session.rollback()
            api.logger.error(f"Erro ao salvar cotação: {str(e)}")
            # Retorna a cotação mesmo se não conseguiu salvar
            return cotacao_data


@ns_cotacao.route('/converter')
class ConversaoResource(Resource):
    @ns_cotacao.doc('converter_valor')
    @ns_cotacao.expect(conversao_model)
    @ns_cotacao.response(200, 'Sucesso', resultado_conversao_model)
    @ns_cotacao.response(400, 'Dados inválidos')
    @ns_cotacao.response(500, 'Erro ao converter valor')
    def post(self):
        """Converte um valor entre moedas"""
        data = request.json
        
        # Verifica se os campos obrigatórios estão presentes
        if not data or 'base' not in data or 'moeda' not in data or 'valor' not in data:
            return {'message': 'Dados inválidos'}, 400
        
        base = data['base']
        moeda = data['moeda']
        valor = float(data['valor'])
        
        # Verifica se o valor é positivo
        if valor <= 0:
            return {'message': 'O valor deve ser maior que zero'}, 400
        
        # Verifica se já temos a cotação de hoje
        hoje = date.today()
        cotacao_hoje = Cotacao.query.filter_by(
            base=base, moeda=moeda, data=hoje
        ).first()
        
        if not cotacao_hoje:
            # Se não tiver, consulta a API externa
            cotacao_data = consultar_cotacao_frankfurt(base, moeda)
            if not cotacao_data:
                return {'message': 'Erro ao consultar cotação externa'}, 500
            
            # Processa os dados e salva no banco
            dados_cotacao = parse_cotacao_data(cotacao_data)
            if not dados_cotacao:
                return {'message': 'Erro ao processar dados de cotação'}, 500
            
            try:
                for dado in dados_cotacao:
                    cotacao = Cotacao(
                        base=dado['base'],
                        moeda=dado['moeda'],
                        valor=dado['valor'],
                        data=dado['data']
                    )
                    db.session.merge(cotacao)
                
                db.session.commit()
                
                # Pega a taxa de conversão
                taxa = cotacao_data['rates'][moeda]
            except Exception as e:
                db.session.rollback()
                api.logger.error(f"Erro ao salvar cotação: {str(e)}")
                # Continua com a conversão mesmo se não conseguiu salvar
                taxa = cotacao_data['rates'][moeda]
        else:
            taxa = cotacao_hoje.valor
        
        # Realiza a conversão
        valor_convertido = valor * taxa
        
        return {
            'valor_original': valor,
            'moeda_original': base,
            'valor_convertido': valor_convertido,
            'moeda_destino': moeda,
            'cotacao': taxa,
            'data': hoje.strftime('%Y-%m-%d')
        }


@ns_cotacao.route('/historico')
class HistoricoResource(Resource):
    @ns_cotacao.doc('get_historico')
    @ns_cotacao.response(200, 'Sucesso')
    def get(self):
        """Obtém o histórico de cotações"""
        cotacoes = Cotacao.query.order_by(Cotacao.data.desc()).all()
        
        resultado = []
        for cotacao in cotacoes:
            resultado.append({
                'base': cotacao.base,
                'moeda': cotacao.moeda,
                'valor': cotacao.valor,
                'data': cotacao.data.strftime('%Y-%m-%d')
            })
        
        return resultado