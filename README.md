# logger

Uma biblioteca pequena para padronizar logs de execução com o módulo nativo
`logging` do Python.

## Instalação

```bash
pip install git+https://github.com/JoaoLuisRichterFilho/logger.git
```

## Uso

```python
import logger

logger.initialize("logs")
logger.definir_id_execucao("123ABC")
logger.debug("Detalhe útil durante o desenvolvimento")
logger.info("Execução iniciada")
logger.warning("Uma condição inesperada foi encontrada")
logger.error("Não foi possível concluir a operação")
logger.definir_id_execucao(None)  # limpa o ID para os próximos logs
```

`logger.initialize("logs")` recebe a pasta de destino e inicializa o singleton.
Uma nova inicialização com a mesma pasta retorna a mesma instância; tentar usar
outra pasta gera `RuntimeError`. Os métodos também estão disponíveis por meio
da instância retornada por `initialize`, se necessário.

Todos os níveis são exibidos no console. `info`, `warning` e `error` também são
gravados em arquivo; `debug` não é gravado. As cores no console são azul para
`info`, amarelo para `warning` e vermelho para `error`; `debug` não recebe cor.
O rótulo do nível ocupa uma coluna fixa, alinhando o início das mensagens.
`definir_id_execucao("123ABC")` adiciona o ID entre colchetes após o nível em
todos os logs seguintes; ele permanece ativo até chamar
`definir_id_execucao(None)`.

O arquivo do dia é criado na primeira mensagem gravável, com nome
`AAAA-MM-DD_HH-MM-SS.log`. Se o processo continuar após a virada do dia, um
novo arquivo com o mesmo padrão é criado no primeiro log gravável daquele dia.
