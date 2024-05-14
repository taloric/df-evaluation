class EvaluationException(Exception):
    message = None
    status = None

    def __init__(self, message, status='FAIL'):
        Exception.__init__(self)
        self.message = message
        self.status = status

    def __str__(self):
        return 'Error (%s): %s' % (self.status, self.message)


class RunnerCodeNotExist(EvaluationException):
    pass


class BadRequestException(EvaluationException):
    pass


class InternalServerErrorException(EvaluationException):
    pass
