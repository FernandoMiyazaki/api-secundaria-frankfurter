from datetime import datetime
from .extensions import db


class Cotacao(db.Model):
    __tablename__ = 'cotacoes'

    id = db.Column(db.Integer, primary_key=True)
    base = db.Column(db.String(3), nullable=False)
    moeda = db.Column(db.String(3), nullable=False)
    valor = db.Column(db.Float, nullable=False)
    data = db.Column(db.Date, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<Cotacao {self.base}/{self.moeda} - {self.data}>"
        
    def to_dict(self):
        return {
            "amount": 1.0,
            "base": self.base,
            "date": self.data.strftime('%Y-%m-%d'),
            "rates": {
                self.moeda: self.valor
            }
        }