# PIT DIVERSÃO — API + VISUAIS PROFISSIONAIS

- Perguntas locais em massa removidas.
- Open Trivia DB removido.
- Perguntas agora são obtidas sob demanda de uma API de quizzes em português.
- O bot usa apenas uma pergunta por vez e evita repetir as últimas questões do grupo.
- Desafios visuais foram refeitos com imagens grandes em 1080×720, layout profissional, efeitos de luz, contraste e desfoque leve.
- Tipos visuais: número, contagem, encontre o diferente, cor e sequência.
- As respostas dos desafios visuais são sempre por botões.
- O primeiro acerto recebe os pontos e o desafio é encerrado.
- Bom dia/boa noite continuam usando PITBULL PRIME.
- INTERAGIR AGORA permanece somente no painel administrativo privado.
- Horários aceitam `08:30`, `8:30`, `08.30` e `8.30`.

## Atualização

Não apague `data/pit_diversao.db` ao atualizar. O banco principal contém usuários,
grupos, pontos, histórico e configurações.

A API de perguntas usada nesta versão:
`https://www.codesnippets.dev.br/public/api/quizzes/v1/questions`

A integração é tolerante a diferentes nomes de campos JSON e exige alternativas
para que o desafio continue funcionando com os botões do Telegram.


## Sistemas incluídos nesta versão
- XP e níveis
- Combos e bônus
- Conquistas
- Missões diárias
- Baú diário
- Batalha 1x1
- Memória visual
- Eventos surpresa com multiplicador
- Ranking por categoria e Top 3
- Temporadas semanais com premiação separada para 1º/2º/3º
- Histórico de temporadas
- Mensagens de acerto variadas
- Anti-spam básico para respostas/jogos
- Resposta automática curta para "como funciona?", marcando o membro
- Configuração dos sistemas pelo painel privado `/admin`

As migrações do banco são aditivas: os dados existentes não são apagados.
