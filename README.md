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
- Memória visual
- Eventos surpresa com multiplicador
- Ranking por categoria e Top 3
- Temporadas manuais com encerramento e abertura de nova temporada somente pelo painel Admin
- Premiação separada para 1º/2º/3º, com histórico preservado
- Histórico de temporadas
- Mensagens de acerto variadas
- Anti-spam básico para respostas/jogos
- Resposta automática curta para "como funciona?", marcando o membro
- Painel privado `/admin` com usuários/pontos, envio administrativo de pontos e histórico de movimentações

As migrações do banco são aditivas: os dados existentes não são apagados.


## Temporadas e pontos — regra atual

- A temporada **não é encerrada automaticamente no domingo**.
- O administrador encerra a temporada pelo botão **🏆 Encerrar e iniciar nova semana** no painel privado.
- Ao encerrar, o ranking final e os prêmios são publicados no grupo e uma nova temporada é aberta.
- Os pontos da temporada anterior permanecem no banco e no histórico.
- A mudança de calendário não troca a temporada ativa sozinha.
- Cada alteração de pontos passa a ser registrada em `points_ledger`, com saldo anterior implícito, saldo resultante, motivo, administrador (quando aplicável) e horário.
- O painel **👥 Usuários / Pontos** permite consultar membros, saldo atual, total acumulado, temporadas anteriores e enviar pontos.
