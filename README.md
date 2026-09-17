# PIT DIVERSÃO

Bot de entretenimento e competição semanal para grupos do Telegram.

## Incluído
- Cadastro de usuários/grupos e configuração por grupo
- /pit
- Desafios manuais e automáticos
- Primeiro acerto recebe pontos
- Ranking semanal e fechamento no domingo
- Prêmio semanal configurável pelo admin
- Bom dia/boa noite automáticos
- Categorias: conhecimentos gerais, futebol, filmes/séries, música, Brasil, matemática, charadas e verdadeiro/falso
- Quiz, dado, moeda, par/ímpar, PPP (pedra/papel/tesoura), forca e palavra embaralhada
- Perfil, seguidores, /quem e reações por emoji
- Giveaway simples, feedback e anúncios
- SQLite com WAL e módulos separados
- Preparado para trocar SQLite por PostgreSQL futuramente

## Instalação
1. Copie `.env.example` para `.env`.
2. Coloque o token do PIT DIVERSÃO em `BOT_TOKEN`.
3. `pip install -r requirements.txt`
4. `python main.py`

## Comandos
/start /pit /ajuda /desafio /ranking /meuspontos /perfil /quem /seguir /parar /seguidores /piada /sorte /conselho /horoscopo /quiz /dado /caraoucoroa /parouimpar /ppp /matematica /embaralhada /verdadeirooufalso /forca /feedback /giveaway

## Admin
/admin /interagir /premio /bomdia_on /bomdia_off /boanoite_on /boanoite_off /novo_desafio /limpardesafio /anunciar /fecharsemana

O bot não movimenta dinheiro. O texto do prêmio é apenas informativo e o pagamento/banca é responsabilidade do administrador.
## 💾 Persistência e backups

Os dados importantes ficam no banco SQLite em `data/pit_diversao.db`, que é
separado do código-fonte e está no `.gitignore`. Isso evita que um novo
deploy substitua o banco por um arquivo vazio.

O bot também:
- cria um backup ao iniciar;
- cria backups automáticos a cada 6 horas;
- mantém os últimos 30 snapshots;
- verifica a integridade do banco;
- tenta restaurar automaticamente o último backup válido se o banco principal
  estiver ausente ou corrompido;
- oferece `/backup` para o administrador receber uma cópia do banco no Telegram.

### Importante sobre segurança dos dados

O backup local protege contra alterações/redeploys comuns, mas uma cópia
somente dentro do servidor não é uma garantia contra perda total do servidor.
Para proteção máxima, mantenha também uma cópia externa do banco ou migre
futuramente para PostgreSQL persistente. O código do bot permanece no GitHub;
os dados dos usuários não são enviados ao GitHub.
## 🖼️ Desafios visuais

O comando `/imagem` cria um desafio em que o bot envia uma imagem com um
número e nove botões de resposta. O primeiro membro que clicar na resposta
correta recebe os pontos. Respostas erradas não encerram a rodada.

O comando `/adivinha` cria uma rodada de adivinhação por texto. Para os
desafios automáticos, o bot alterna entre perguntas normais e, em parte das
rodadas, desafios visuais.

Em todos esses desafios, a vitória é registrada atomicamente no banco:
somente o primeiro acerto válido recebe os pontos.

## Atualização: /pit e desafios automáticos

- `/pit` é o comando usado pelo administrador para ligar a interação no grupo.
- O antigo `/bil` foi removido.
- O bot gera desafios automaticamente; o administrador não precisa cadastrar cada desafio.
- Os desafios podem ser de conhecimentos gerais, futebol, Brasil, filmes/séries, música, matemática, charadas e verdadeiro/falso.
- Os desafios visuais são gerados localmente pelo próprio bot usando Pillow, sem precisar de uma API de imagens.
- Há desafios visuais de número, contagem de formas e encontrar o diferente, com botões para resposta.
- O primeiro acerto recebe os pontos e o resultado fica salvo no SQLite.


## Migração segura V3
A inicialização adiciona colunas ausentes de forma aditiva. Não apaga nem recria as tabelas existentes.


## Painel administrativo privado
O painel `/admin` funciona somente no privado do bot. Configure no `.env`:
`ADMIN_IDS=SEU_ID_TELEGRAM`
Para vários administradores: `ADMIN_IDS=123,456,789`.

No painel há botões para grupos, ativação, bom dia, boa noite, prêmio semanal, encerramento de desafio e fechamento da semana.

## Desafios automáticos
Com a interação ativa, o bot gera um novo desafio automaticamente a cada 25 minutos (nos minutos 00, 25 e 50 de cada hora), desde que não exista outro desafio ativo.
