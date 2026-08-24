class ErroDominio(Exception):
    """Base para erros de regra de negocio, mapeados para respostas HTTP na API."""

    codigo = "erro_dominio"
    status_http = 400


class RecursoNaoEncontrado(ErroDominio):
    codigo = "recurso_nao_encontrado"
    status_http = 404


class AlunoJaMatriculado(ErroDominio):
    codigo = "aluno_ja_matriculado"
    status_http = 409


class MatriculaNaoEncontrada(RecursoNaoEncontrado):
    codigo = "matricula_nao_encontrada"
