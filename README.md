# logger

Biblioteca criada para geração simplificada de logs e reutilização em outros projetos, utilizando a biblioteca nativa `logging` do Python.

## Instalação

```bash
pip install git+https://github.com/JoaoLuisRichterFilho/logger.git@vX.X.X
```

## Uso

```python
import logger

logger.initialize("logs", detailed=True)
logger.definir_id_execucao("123ABC")
logger.debug("Detalhe útil durante o desenvolvimento")
logger.info("Execução iniciada")
logger.warning("Uma condição inesperada foi encontrada")
logger.error("Não foi possível concluir a operação")
logger.definir_id_execucao(None)  # limpa o ID para os próximos logs
```

`logger.initialize("logs", detailed=False)` recebe a pasta de destino e
inicializa o singleton. Com `detailed=True`, cada mensagem inclui o módulo e a
função que geraram o log, separados por ponto e vírgula, antes do texto da
mensagem (por exemplo: `test_logger;minha_funcao; Minha msg`). O valor padrão é
`False`. Quando a chamada vem diretamente do nível do módulo, sem uma função,
apenas o nome do módulo é exibido antes da mensagem. Rechamadas com a mesma
pasta podem ativar ou desativar esse modo; uma pasta diferente gera
`RuntimeError`. Os métodos também estão disponíveis por meio da instância
retornada por `initialize`, se necessário.

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
