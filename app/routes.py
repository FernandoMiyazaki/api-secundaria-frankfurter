from flask import Blueprint, request
from flask_restx import Resource, fields
from datetime import date
from .extensions import db, api
from .models import Cotacao, Transacao
from .utils import (
    consultar_cotacao_frankfurt, 
    parse_cotacao_data, 
    converter_valor,
    calcular_saldo_usd_usuario,
    validar_transacao_compra,
    validar_transacao_venda
)

# Blueprint
main = Blueprint('main', __name__)

# Namespace
ns_cotacao = api.namespace('cotacao', description='Operações relacionadas a cotações')
ns_transacoes = api.namespace('transacoes', description='Operações relacionadas a transações')

# Models
cotacao_model = api.model('Cotacao', {
    'amount': fields.Float(description='Valor base'),
    'base': fields.String(description='Moeda base'),
    'date': fields.String(description='Data da cotação'),
    'rates': fields.Raw(description='Taxas de conversão')
})

transacao_model = api.model('Transacao', {
    'id': fields.Integer(readonly=True, description='ID da transação'),
    'user_id': fields.Integer(required=True, description='ID do usuário'),
    'tipo': fields.String(required=True, description='Tipo da transação (compra/venda)'),
    'quantidade_usd': fields.Float(description='Quantidade em USD'),
    'valor_brl': fields.Float(description='Valor em BRL'),
    'cotacao': fields.Float(readonly=True, description='Cotação usada'),
    'data_transacao': fields.DateTime(readonly=True, description='Data e hora da transação')
})

saldo_model = api.model('Saldo', {
    'saldo_usd': fields.Float(description='Saldo em USD do usuário')
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


@ns_transacoes.route('/compra')
class CompraTransacao(Resource):
    @ns_transacoes.doc('comprar_dolar',
                      params={
                          'user_id': 'ID do usuário',
                          'valor_brl': 'Valor em BRL para compra de USD'
                      })
    @ns_transacoes.marshal_with(transacao_model, code=201)
    def post(self):
        """Registra uma compra de dólares"""
        # Obtém os dados dos parâmetros
        user_id = request.args.get('user_id')
        valor_brl_str = request.args.get('valor_brl')
        
        # Verifica se os campos obrigatórios estão presentes
        if not user_id:
            return {'message': 'Campo obrigatório ausente: user_id'}, 400
        if not valor_brl_str:
            return {'message': 'Campo obrigatório ausente: valor_brl'}, 400
        
        try:
            user_id = int(user_id)
            valor_brl = float(valor_brl_str)
        except ValueError:
            return {'message': 'Formato inválido para user_id ou valor_brl'}, 400
        
        # Valida a transação
        valido, mensagem = validar_transacao_compra(user_id, valor_brl)
        if not valido:
            return {'message': mensagem}, 400
        
        # Obtém a cotação atual do dólar
        cotacao_data = consultar_cotacao_frankfurt()
        if not cotacao_data:
            return {'message': 'Erro ao obter cotação do dólar'}, 500
        
        cotacao = cotacao_data['rates']['BRL']
        quantidade_usd = valor_brl / cotacao
        
        try:
            nova_transacao = Transacao(
                user_id=user_id,
                tipo='compra',
                quantidade_usd=quantidade_usd,
                valor_brl=valor_brl,
                cotacao=cotacao
            )
            
            db.session.add(nova_transacao)
            db.session.commit()
            
            return nova_transacao, 201
        except Exception as e:
            db.session.rollback()
            return {'message': f'Erro ao registrar compra: {str(e)}'}, 400


@ns_transacoes.route('/venda')
class VendaTransacao(Resource):
    @ns_transacoes.doc('vender_dolar',
                     params={
                         'user_id': 'ID do usuário',
                         'quantidade_usd': 'Quantidade em USD para vender'
                     })
    @ns_transacoes.marshal_with(transacao_model, code=201)
    def post(self):
        """Registra uma venda de dólares"""
        # Obtém os dados dos parâmetros
        user_id = request.args.get('user_id')
        quantidade_usd_str = request.args.get('quantidade_usd')
        
        # Verifica se os campos obrigatórios estão presentes
        if not user_id:
            return {'message': 'Campo obrigatório ausente: user_id'}, 400
        if not quantidade_usd_str:
            return {'message': 'Campo obrigatório ausente: quantidade_usd'}, 400
        
        try:
            user_id = int(user_id)
            quantidade_usd = float(quantidade_usd_str)
        except ValueError:
            return {'message': 'Formato inválido para user_id ou quantidade_usd'}, 400
        
        # Valida a transação
        valido, mensagem = validar_transacao_venda(user_id, quantidade_usd)
        if not valido:
            return {'message': mensagem}, 400
        
        # Obtém a cotação atual do dólar
        cotacao_data = consultar_cotacao_frankfurt()
        if not cotacao_data:
            return {'message': 'Erro ao obter cotação do dólar'}, 500
        
        cotacao = cotacao_data['rates']['BRL']
        valor_brl = quantidade_usd * cotacao
        
        try:
            nova_transacao = Transacao(
                user_id=user_id,
                tipo='venda',
                quantidade_usd=quantidade_usd,
                valor_brl=valor_brl,
                cotacao=cotacao
            )
            
            db.session.add(nova_transacao)
            db.session.commit()
            
            return nova_transacao, 201
        except Exception as e:
            db.session.rollback()
            return {'message': f'Erro ao registrar venda: {str(e)}'}, 400


@ns_transacoes.route('/<int:id>')
@ns_transacoes.response(404, 'Transação não encontrada')
@ns_transacoes.param('id', 'ID da transação')
class TransacaoResource(Resource):
    @ns_transacoes.doc('get_transaction')
    @ns_transacoes.marshal_with(transacao_model)
    def get(self, id):
        """Obtém os dados de uma transação específica"""
        transacao = Transacao.query.get_or_404(id)
        return transacao


@ns_transacoes.route('/usuario/<int:user_id>')
@ns_transacoes.param('user_id', 'ID do usuário')
class TransacoesUsuarioResource(Resource):
    @ns_transacoes.doc('get_user_transactions')
    @ns_transacoes.marshal_list_with(transacao_model)
    def get(self, user_id):
        """Obtém todas as transações de um usuário"""
        transacoes = Transacao.query.filter_by(user_id=user_id).all()
        return transacoes


@ns_transacoes.route('/usuario/<int:user_id>/saldo')
@ns_transacoes.param('user_id', 'ID do usuário')
class SaldoUsuarioResource(Resource):
    @ns_transacoes.doc('get_user_balance')
    @ns_transacoes.marshal_with(saldo_model)
    def get(self, user_id):
        """Obtém o saldo em USD do usuário"""
        saldo_usd = calcular_saldo_usd_usuario(user_id)
        if saldo_usd is None:
            return {'message': 'Erro ao calcular saldo'}, 500
        return {"saldo_usd": saldo_usd}