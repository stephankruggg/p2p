# p2p

## Requisitos
1. No diretório do projeto, é necessário criar um diretório que conterá os arquivos de cada peer. Por padrão esse diretório é o `example/`.
2. No diretório `example/`, é necessário haver um diretório para cada peer, cujo nome é o ID do peer. Por exemplo, para o peer 0 o diretório que conterá suas informações é o `example/0/`.
3. Para que um peer possa executar são necessários dois arquivos em seu diretório: `example/<id>/config.txt` e `example/<id>/topologia.txt`. O primeiro possui informações do endereço e porta UDP de cada peer, além da velocidade máxima para a transferência TCP. Já o segundo possui informações dos vizinhos de cada peer.
4. Para que o peer realize uma busca, é necessário que haja um arquivo em seu diretório responsável por prover os metadados do arquivo a ser buscado. Este arquivo deve possuir a extensão `.p2p` e conter as seguintes informações: nome do arquivo a ser buscado, número de chunks em que ele está dividido e o TTL para as requisições UDP. Por exemplo: `example/0/image.p2p`.

## Configurações
O programa possui um arquivo de configurações: `src/utils/constants.py`. Nele é possível:
- Configurar qual o nome do diretório que guarda o diretório do peer. Padrão: `example`.
- Configurar qual o número base da porta do servidor TCP de um peer. Padrão: `4000`.
- Configurar qual o número base da porta do cliente UDP que realizará o forwarding das mensagens de flooding. Padrão: `4100`.
- Configurar qual o número base da porta do cliente UDP que realizará o flooding. Padrão: `5000`.
- Configurar o número máximo de threads de clientes TCP que um peer pode executar ao mesmo tempo. Padrão: `2`.
- Configurar qual o timeout em segundos do cliente UDP de flooding. Padrão: `20`.

## Execução
Para executar, abra um terminal e execute o comando:
``` bash
make run ID=<peer-id>
```

Por exemplo:
``` bash
make run ID=0
```

Após o início da execução, cada peer pode realizar a busca por um arquivo, bastando o usuário prover qual o nome do arquivo de metadados. Por exemplo:
``` bash
image.p2p
```

## Limpeza
Para remover os arquivos bytecode compilados, abra um terminal e execute o comando:
``` bash
make clean
```
