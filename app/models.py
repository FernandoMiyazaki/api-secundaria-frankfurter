from datetime import datetime, timedelta
from .extensions import db


class Cotacao(db.Model):
    __tablename__ = 'cotacoes'
    
    id = db.Column(db.Integer, primary_key=True)
    base = db.Column(db.String(3), nullable=False)
    moeda = db.Column(db.String(3), nullable=False)
    valor = db.Column(db.Float, nullable=False)
    data = db.Column(db.Date, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Adiciona restrição única para combinação de base, moeda e data
    __table_args__ = (
        db.UniqueConstraint('base', 'moeda', 'data', name='uix_cotacao_base_moeda_data'),
    )

    def __repr__(self):
        return f"<Cotacao {self.base}/{self.moeda} - {self.data}>"
        
    def to_dict(self):
        # Converte o timestamp de UTC para UTC-3
        created_at_local = self.created_at - timedelta(hours=3)
        
        return {
            "amount": 1.0,
            "base": self.base,
            "date": self.data.strftime('%Y-%m-%d'),
            "created_at": created_at_local.strftime('%Y-%m-%d %H:%M:%S'),
            "rates": {
                self.moeda: self.valor
            }
        }


class Transacao(db.Model):
    __tablename__ = 'transacoes'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, nullable=False)
    tipo = db.Column(db.String(10), nullable=False)  # 'compra' ou 'venda'
    quantidade_usd = db.Column(db.Float, nullable=False)
    valor_brl = db.Column(db.Float, nullable=False)
    cotacao = db.Column(db.Float, nullable=False)
    data_transacao = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<Transacao {self.id} - {self.tipo}>"
    
    def to_dict(self):
        """
        Retorna uma representação da transação em forma de dicionário para serialização
        """
        return {
            'id': self.id,
            'user_id': self.user_id,
            'tipo': self.tipo,
            'quantidade_usd': self.quantidade_usd,
            'valor_brl': self.valor_brl,
            'cotacao': self.cotacao,
            'data_transacao': self.data_transacao.strftime('%Y-%m-%d %H:%M:%S') if self.data_transacao else None
        }