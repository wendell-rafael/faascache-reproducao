# Avaliação de GD_C: critérios definidos antes da rodada (05/11/2026)

- Política: GD_C, `Clock + (soma das frequências dos clones / número de clones) * custo / tamanho`, sem parâmetros ajustados.
- Escolha: feita após piloto em 10 e 15 GB. Esses tamanhos ficam fora da avaliação.
- Avaliação: 18 tamanhos restantes da grade do artefato (1, 5, 7, 12, 14, 16, 18, 20, 22, 26, 30, 34, 40, 46, 50, 60, 70 e 80 GB), mesmo trace, sem alterar a fórmula depois de ver resultados.
- Métricas: aumento no tempo de execução (principal), % de cold starts e descartes.
- Comparações: GD publicado, TTL, LRU e GD do artefato, por tamanho, com contagem de vitórias, empates e derrotas.
- Limite: trace único e simulação determinística, portanto sem intervalo de confiança; tamanhos da mesma grade não são amostras independentes.
