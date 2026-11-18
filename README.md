# Ecos do Abismo

RPG de mesa virtual em 3D, de fantasia sombria, jogável no navegador. Tem Mestre, jogadores, fichas, dados e combate por turnos numa cripta ligada por uma ponte sobre o abismo.

## Como jogar

- **No navegador, sozinho ou em grupo no mesmo aparelho:** abra `public/index.html`. Tudo funciona, menos o modo online.
- **Online:** abra o endereço do servidor e clique em **Online**.
  - Quem cria a sala é o Mestre e recebe um código de 6 caracteres.
  - Os outros entram com esse código e escolhem um herói.

## Rodar o servidor no seu PC

É preciso ter o Python 3.10 ou mais novo. Não precisa instalar nada: sem a variável `DATABASE_URL`, o servidor usa SQLite em `data/ecos.db`.

```powershell
python server/app.py
```

Depois abra <http://localhost:8000>. Para outra porta, defina a variável `PORT`.

## Hospedar no Render

O arquivo `render.yaml` descreve:

- um serviço web gratuito em Python;
- um banco PostgreSQL gratuito, ligado ao serviço pela variável `DATABASE_URL`.

No plano gratuito, o serviço adormece quando ninguém usa e leva uns 30 segundos para acordar. O PostgreSQL gratuito do Render expira depois de 30 dias, a menos que você troque de plano.

## Como o multijogador funciona

- **Mestre:** o navegador do Mestre roda a simulação do combate (monstros, regras e efeitos).
- **Dados:** o servidor gera uma sequência de números aleatórios e entrega ao Mestre. Cada rolagem informada é conferida contra essa sequência, e as que não batem aparecem como "não validada" no histórico. As rolagens livres (`2d6+3`) são feitas no próprio servidor. Rolagens secretas do Mestre só chegam ao Mestre.
- **Jogadores:** recebem o estado da mesa cerca de 8 vezes por segundo e veem os mesmos efeitos visuais. No turno do próprio herói, mandam as ações para o Mestre, que as executa.
- **Inventário:** o servidor é a autoridade. Equipar fora de combate, comprar, vender, usar o baú e trocar entre jogadores passam por ele. As trocas só acontecem com a confirmação dos dois lados, e o servidor confere de novo se os itens ainda estão com os donos, para não duplicar nem perder nada.
- **Salvamento:** as salas ficam no banco. Se o servidor reiniciar, basta voltar com o código.

## Estrutura

- `public/index.html`: o jogo inteiro (Three.js r128 via cdnjs).
- `server/app.py`: servidor HTTP e WebSocket em Python, só com a biblioteca padrão.
- `server/db.py`: armazenamento em PostgreSQL ou SQLite.
- `render.yaml`: blueprint do Render.

## Estado do projeto

**Pronto:**
- cripta, ponte e santuário em 3D;
- 3 classes, 4 tipos de inimigo e um chefe;
- regras de dados, ação bônus e reação, cobertura e condições;
- 120 armas em 12 famílias, com modelos 3D gerados por código;
- maestrias, inventário com dois conjuntos, mascate, baú e trocas;
- dados com expressões e rolagens secretas;
- salas online com banco de dados.
- diário compartilhado, missão principal de cinco etapas, três secundárias e três finais;
- vilarejo, floresta e castelo procedurais, com viagens conduzidas pelo Mestre.

**Próximas etapas:**
- as outras 21 classes, com especializações, e o editor de classes;
- ampliar a campanha para 10 missões;
- simulações de equilíbrio.

Modelos 3D esculpidos dependem de arquivos `.glb` externos.

## Direção de terror e protagonistas

A implementação parcial da direção 16 está descrita em [docs/DIRECAO-16.md](docs/DIRECAO-16.md), com recursos, regras de tensão, testes e pendências de produção 3D. Os modelos procedurais **não são protagonistas finalizados**.

Para começar **O Selo dos Nomes**, crie/carregue o grupo e abra **Missões → Iniciar missão principal**. Objetivos, recompensas, viagens, finais e regras de salvamento estão em [docs/MISSOES.md](docs/MISSOES.md).
