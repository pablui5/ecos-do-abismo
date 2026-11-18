# Missões — O Selo dos Nomes

Depois de criar ou carregar um grupo, abra **Missões → Iniciar missão principal**.
Na sala online, o Mestre inicia a campanha e conduz as viagens e a decisão final.
Os jogadores podem aceitar missões secundárias e interagir com objetivos usando
seus próprios protagonistas. A campanha pertence ao grupo inteiro.

## Missão principal

O sino de Valdenegro carrega as vozes de pessoas desaparecidas. A Irmã Alina
encarrega o grupo de recuperar seus nomes antes que o Arauto rompa o selo.

| Etapa | Local | Objetivo | Moedas por herói |
| --- | --- | --- | --- |
| Os nomes que restaram | Valdenegro | Ler o registro da escriba | 5 |
| O sino sem voz | Valdenegro | Vencer dois invasores e examinar o sino | 10 |
| A última chama | Floresta dos Enforcados | Vencer dois guardiões e recuperar a lanterna | 15 |
| O juramento quebrado | Castelo da Última Vigília | Vencer três sentinelas e abrir o relicário | 20 |
| O preço de lembrar | Cripta do Selo | Vencer o Arauto e decidir o destino do selo | 40 |

O diário apresenta a etapa atual, localização, requisitos, recompensa e descobertas.
**Mostrar no mapa** centraliza a câmera no objetivo. Anéis dourados indicam a
missão principal; anéis azuis indicam as secundárias aceitas. Mova um protagonista
até uma casa do marcador e use **Interagir com o objetivo** no diário.
Entregas e viagens só acontecem fora de combate. O registro inicial pode ser
alcançado sem despertar os inimigos.

Depois do Arauto, o Mestre escolhe com o grupo entre selar a passagem, libertar
os ecos ou manter a vigília. Cada escolha registra seu próprio encerramento.
São desfechos narrativos; não geram campanhas posteriores automaticamente.

## Missões secundárias

- **Nenhum nome esquecido:** recuperar os nomes no memorial de Valdenegro após
  vencer dois invasores; 10 moedas por herói.
- **Luz para o peregrino:** reacender o marco na floresta; 15 moedas por herói.
- **A promessa da guarda:** recuperar o estandarte após vencer três sentinelas;
  20 moedas por herói.

As secundárias podem ser concluídas depois da missão principal. Cada etapa e
missão paga uma única vez. As recompensas somam 135 moedas por herói se todas
forem concluídas, além dos saques normais do combate.

## Persistência e autoridade

`public/campaign.js` contém o catálogo e as transições offline. O servidor lê
esse mesmo catálogo em `server/missions.py`, valida objetivos usando o último
estado da simulação do Mestre e calcula a recompensa sem aceitar valores do
cliente. A revisão do diário rejeita pedidos repetidos ou desatualizados.
Somente o Mestre pode iniciar, avançar diretamente ou escolher um final.
Pedidos de interação de jogadores passam pela verificação de propriedade
existente e pela simulação do Mestre.

O progresso, as descobertas e o final ficam salvos no navegador para o grupo
local e no banco para a sala online. Retomar uma sala como Mestre restaura o
último estado do encontro disponível. A retomada local e as viagens iniciam
novamente os encontros do cenário; etapas já concluídas e suas recompensas
permanecem concluídas. Uma campanha nova começa com um grupo novo; não há
botão para apagar o diário de uma sala em andamento.

Os novos ambientes são cenários procedurais jogáveis. Não constituem produção
artística final, e esta entrega não altera o estado provisório dos protagonistas.

## Validação

```sh
node --test tests/direction.test.cjs tests/campaign.test.cjs
python -m unittest discover -s tests -p 'test_*.py' -v
node tests/world-smoke.cjs /caminho/three-r128.cjs
node tests/model-smoke.cjs /caminho/three-r128.cjs
```

Os testes verificam as cinco etapas e três finais, recompensas únicas, permissões,
proximidade, consciência, combate, guardiões, secundárias e persistência da sala.
O teste de cenários percorre três ciclos pelos quatro mapas, verifica descarte
dos objetos anteriores, transformações finitas e caminhos até os oito objetivos.

Revisão manual: iniciar campanha, ler o registro, conferir a descoberta, recarregar
e continuar, aceitar secundária como jogador, acompanhar o diário no Mestre,
viajar com duas sessões e retomar a sala. Testes de regra não substituem uma
campanha completa de equilíbrio com jogadores.
