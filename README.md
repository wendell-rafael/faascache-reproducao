# Reprodução e evolução experimental do FaasCache

Reprodução por simulação de Fuerst e Sharma, "FaasCache: Keeping Serverless Computing Alive with Greedy-Dual Caching" (ASPLOS '21, DOI [10.1145/3445814.3446757](https://doi.org/10.1145/3445814.3446757)), e avaliação de uma variação da política Greedy-Dual (GD_C). Projeto da disciplina Provisionamento e Operação de Infraestruturas (UFCG).

## Conteúdo

| Caminho | O que é |
|---|---|
| `artigo/` | Fonte LaTeX, figuras e PDF do artigo. |
| `detalhamento_formato_turma.md` | Detalhamento do projeto (questões de pesquisa e experimentos). |
| `experimentos/reproducao.py`, `rodar.sh` | E1 e E2: sete políticas em 20 tamanhos de memória. |
| `experimentos/hist_variantes.py`, `rodar_hist.sh` | E3: hipóteses para a divergência de HIST. |
| `experimentos/piloto_politicas.py`, `rodar_gd_c.sh` | E4: piloto (10 e 15 GB) e avaliação de GD_C nos 18 tamanhos restantes. |
| `experimentos/avaliacao_gd_c.md` | Critérios de avaliação de GD_C, definidos antes de rodar a avaliação. |
| `experimentos/analisar.py`, `analisar_gd_c.py` | Tabelas e figuras a partir dos JSON de resultado. |
| `experimentos/resultados*/` | Um JSON por simulação (política, memória). |
| `experimentos/analise/` | CSV, resumo e figuras usados no artigo. |
| `experimentos/diagnostico/` | Logs das rodadas de diagnóstico de GD e HIST. |

## Como reproduzir

1. Baixe o artefato dos autores no Zenodo ([10.5281/zenodo.4321766](https://doi.org/10.5281/zenodo.4321766), arquivo `FaasCacheData.zip`) e coloque em `experimentos/artefato/`:
   - `split/` (simulador, com `LambdaScheduler.py`);
   - `392-b.pckl` (trace de 392 funções);
   - `392-pckls/` (resultados pré-computados, usados na comparação).

   O artefato não está neste repositório porque é de terceiros.
2. Construa a imagem:
   ```bash
   docker build -t faascache-smoke experimentos
   ```
3. Rode as simulações. Cada script grava um JSON por simulação e pula os já gravados, então pode ser retomado:
   ```bash
   experimentos/rodar.sh
   experimentos/rodar_gd_c.sh
   ```
   Cada simulação levou até cerca de 96 minutos, com 10 em paralelo, numa máquina de 12 núcleos e 31 GB de RAM.

**Segurança:** os arquivos `.pckl` executam código ao serem carregados. Os scripts rodam o simulador em contêiner sem rede, sem capabilities e com o artefato montado só para leitura. Mantenha essas opções.

## Licença

Código deste repositório sob licença MIT. O simulador e o trace pertencem aos autores do FaasCache e seguem a licença do artefato original.
