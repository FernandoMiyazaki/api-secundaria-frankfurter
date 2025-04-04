# API Secundária Frankfurter - Sistema de Câmbio

Esta API secundária é responsável pelo gerenciamento de cotações e transações financeiras no Sistema de Câmbio. Ela implementa todas as regras de negócio relacionadas a operações financeiras, incluindo consulta de cotações, conversões entre moedas e cálculo de saldos.

## Responsabilidades

- Consultar cotações de moedas via serviço externo Frankfurter
- Gerenciar transações de compra e venda de dólares
- Calcular e validar saldo de usuários
- Implementar regras de negócio financeiras
- Realizar conversões entre diferentes moedas

## Instruções de Instalação

### Pré-requisitos
- Docker e Docker Compose
- Python 3.11 ou superior (para desenvolvimento local)
- Git

### Passos para instalação

1. Clone o repositório:
```bash
git clone https://github.com/FernandoMiyazaki/api-secundaria-frankfurter.git
```

2. Certifique-se de que o seguinte arquivo está presente:

- `api-secundaria-frankfurter/.env`

3. Usando Docker (recomendado):
```bash
# A API Frankfurter é iniciada como parte do docker-compose
# a partir da pasta da API Principal
cd ../api-principal-corretora
docker-compose up -d
```

4. Para desenvolvimento local (opcional):
```bash
# Crie e ative um ambiente virtual
python -m venv venv
source venv/bin/activate  # No Windows: venv\Scripts\activate

# Instale as dependências
pip install -r requirements.txt

# Execute a aplicação
python run.py
```

## Endpoints

### Cotações
- `GET /cotacao` - Obtém a cotação atual do USD em BRL
- `POST /cotacao` - Adiciona uma cotação ao banco de dados
- `GET /cotacao/historico` - Obtém o histórico de cotações

### Transações
- `POST /transacoes/compra` - Registra uma compra de dólares
- `POST /transacoes/venda` - Registra uma venda de dólares
- `GET /transacoes/{id}` - Obtém uma transação específica
- `GET /transacoes/usuario/{user_id}` - Lista todas as transações de um usuário
- `GET /transacoes/usuario/{user_id}/saldo` - Calcula e retorna o saldo em USD do usuário

## Regras de Negócio Implementadas
- Conversão precisa entre moedas usando taxas atualizadas
- Cálculo de saldo do usuário baseado no histórico de transações
- Validação de saldo suficiente para transações de venda
- Validação de valores positivos para transações

## Tecnologias Utilizadas
- Flask
- SQLAlchemy
- PostgreSQL
- Flask-RESTx para documentação Swagger
- Requests para chamadas HTTP

## Acessando a Documentação da API
- Swagger UI: http://localhost:5002/swagger

## Modelo de Dados

### Tabela `cotacoes`
- `id`: Chave primária
- `base`: Moeda base (ex: USD)
- `moeda`: Moeda de destino (ex: BRL)
- `valor`: Taxa de conversão
- `data`: Data da cotação
- `created_at`: Data/hora de criação
- Restrição única para combinação de base, moeda e data

### Tabela `transacoes`
- `id`: Chave primária
- `user_id`: ID do usuário (referência externa)
- `tipo`: Tipo da transação ('compra' ou 'venda')
- `quantidade_usd`: Quantidade em dólares
- `valor_brl`: Valor em reais
- `cotacao`: Taxa de conversão usada
- `data_transacao`: Data/hora da transação