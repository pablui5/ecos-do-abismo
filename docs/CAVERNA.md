# Caverna do Selo

A cripta e a ponte agora ficam dentro de uma gruta contínua. A formação usa
rochas deformadas com faixas minerais, paredes laterais e de fundo, estalactites
e estalagmites. A fundação sob a cripta é irregular, substituindo a caixa e o
cone anteriores. As ilhas flutuantes com árvores e os cristais azuis intensos
foram removidos desse ambiente.

O piso ganhou fissuras, musgo e poças irregulares com ondulações lentas. Cascalho,
uma roda quebrada, uma lanterna e uma corda contam a passagem de outra expedição.
Os objetos elevados ficam fora das casas jogáveis. A malha do mapa, os inimigos,
os objetivos e as regras de movimento continuam iguais.

A luz ambiente ficou mais neutra, com menos azul emissivo nas lajes e nas
balaustradas. As tochas e o santuário conservam seus pontos de luz. A parede da
caverna voltada para a câmera fica quase transparente para liberar a visão dos
personagens. O teto central permanece aberto para a câmera tática.

`public/cavern.js` agrupa as formações repetidas em `InstancedMesh`, com uma
semente local que não consome dados de combate. Qualidade baixa oculta cascalho,
fissuras, musgo, veios menores e ondulações. Efeitos reduzidos deixam as ondas
estáticas. Recursos das instâncias são descartados ao trocar de cenário.

Validação: análise do JavaScript, testes das missões e três ciclos pelos quatro
cenários. A verificação geométrica inclui matrizes das instâncias, descarte da
cena anterior, caminhos até todos os objetivos e fundação inteiramente abaixo
do piso. Revisão visual da caverna em qualidade média/baixa, opções de movimento
reduzido, câmera tática e deslocamento de um protagonista. Não é uma medição de
FPS em dispositivos de referência.
