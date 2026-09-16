# PIT DIVERSÃO — Etapa 1

Bot independente do PIT BONUS para entretenimento e interação em grupos do Telegram.

## O que esta etapa possui

- conexão com Telegram usando aiogram;
- `/start`;
- cadastro automático de usuários;
- cadastro automático de grupos;
- relação grupo/usuário;
- configuração independente por grupo;
- `/bil` para consultar o status;
- `/interagir` para ativar/desativar a interação (somente administrador);
- SQLite com WAL;
- `.env` para o token;
- estrutura modular preparada para os próximos sistemas.

## Instalação

Recomendado: Python 3.11 ou superior.

```bash
python -m venv .venv
```

Windows:

```bash
.venv\\Scripts\\activate
```

Depois:

```bash
pip install -r requirements.txt
```

## Configuração

Copie `.env.example` para `.env` e coloque o token do NOVO bot criado no BotFather.

Exemplo:

```env
BOT_TOKEN=SEU_TOKEN_AQUI
BOT_NAME=PIT DIVERSÃO
DATABASE_PATH=data/pit_diversao.db
```

Nunca publique o `.env`.

## Executar

```bash
python main.py
```

## Teste

1. Inicie o bot com `/start`.
2. Adicione o bot a um grupo.
3. Envie `/start` no grupo.
4. Envie `/bil`.
5. Como administrador, envie `/interagir` para alternar o sistema.
6. Envie `/bil` novamente para conferir o status.

## Próxima etapa

Depois de testar esta base, vamos adicionar o primeiro sistema real de competição:

- perguntas automáticas;
- primeiro acerto vence;
- pontos por acerto;
- pontuação semanal por grupo;
- ranking semanal;
- estrutura para encerramento no domingo.

Os desafios de futebol, filmes, música, Brasil, charadas, matemática, imagens etc. e as mensagens automáticas de bom dia/boa noite entram depois da base ser validada.
