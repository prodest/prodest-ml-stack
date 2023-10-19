from hashlib import sha256
from time import time
from numpy import random


def gerar_hash():
    """
    Gera um hash SHA-256.
        :return: Hash SHA-256 gerado.
    """
    # Gera chave aleatória para incluir no texto a ser passado para gerar o hash
    lst_key_shuffled = list("eyJhbGciOiJIUzM4NCIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4gRG9lIGx")
    random.shuffle(lst_key_shuffled)
    key_shuffled = "".join(lst_key_shuffled)

    h = sha256()
    text = str(time()) + str(random.rand()) + key_shuffled + str(random.rand())
    h.update(text.encode('utf-8'))
    return h.hexdigest()


if __name__ == "__main__":
    arq = None

    # Gera a URL que substituirá o signup
    try:
        arq = open("/tmp/url_signup.txt", 'w')
    except PermissionError:
        print(f"\nErro ao criar o arquivo '/tmp/url_signup.txt'. Permissão de escrita negada!\n")
        exit(1)

    arq.write(f"signup_new={gerar_hash()}eyJhbciOIsInR5CIpXVCJ9eyzdW{gerar_hash()}IOiITczNDk3MTk0MzcxOTczNCIsIm5hWU"
              f"IERvZSBhbG\n")
    arq.close()
