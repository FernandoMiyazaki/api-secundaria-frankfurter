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


@ns_cotacao.route('/')
class CotacaoResource(Resource):
    @ns_cotacao.doc('get_cotacao')
    @ns_cotacao.response(200, 'Sucesso', cotacao_model)
    @ns_cotacao.response(500, 'Erro ao consultar cotação')
    def get(self):
        """Obtém a cotação atual do USD em BRL (sem persistir)"""
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
        
        # Retorna os dados sem persistir
        return cotacao_data
    
    @ns_cotacao.doc('add_cotacao')
    @ns_cotacao.response(201, 'Cotação adicionada', cotacao_model)
    @ns_cotacao.response(500, 'Erro ao consultar ou salvar cotação')
    def post(self):
        """Adiciona a cotação atual do USD em BRL no banco de dados"""
        # Consulta a API externa
        cotacao_data = consultar_cotacao_frankfurt()
        if not cotacao_data:
            return {'message': 'Erro ao consultar cotação externa'}, 500
        
        # Processa os dados
        dados_cotacao = parse_cotacao_data(cotacao_data)
        if not dados_cotacao:
            return {'message': 'Erro ao processar dados de cotação'}, 500
        
        # Salva no banco de dados
        try:
            for dado in dados_cotacao:
                nova_cotacao = Cotacao(
                    base=dado['base'],
                    moeda=dado['moeda'],
                    valor=dado['valor'],
                    data=dado['data']
                )
                db.session.add(nova_cotacao)
            
            db.session.commit()
            return cotacao_data, 201
        except Exception as e:
            db.session.rollback()
            api.logger.error(f"Erro ao salvar cotação: {str(e)}")
            return {'message': f'Erro ao salvar cotação: {str(e)}'}, 500


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